# -*- coding: utf-8 -*-
"""
個別マスタの規約外ファイル保護フローの検証 (ハードストップ → 409)。

仕様:
- merge 実行時に個別マスタの docx を事前バリデーション
- 違反が 1 件でもあれば結合を中止し InvalidMasterFilesError を送出
- API 層は HTTP 409 + issues 配列を返す
- ファイルシステムには一切変更を加えない (リネームも削除もしない)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.merge_service import (
    MASTER_DIRNAME,
    OUTPUT_DIRNAME,
    OUTPUT_FILENAME,
    InvalidMasterFilesError,
    ensure_folders,
    merge_kogo,
    validate_master_files,
)

from tests.conftest import make_kogo_docx, parse_sse_events


# ---------------------------------------------------------------------------
# サービス層のテスト (validate_master_files / merge_kogo)
# ---------------------------------------------------------------------------

def test_invalid_filename_raises(root_folder: Path) -> None:
    """規約外ファイル名 (例: 甲1号証.docx) があると 409 相当の例外。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲1号証.docx", "【甲第１号証】")

    with pytest.raises(InvalidMasterFilesError) as ei:
        merge_kogo(root_folder)
    issues = ei.value.issues
    assert len(issues) == 1
    assert issues[0].filename == "甲1号証.docx"
    assert "正規化形式" in issues[0].reason
    assert issues[0].suggested_rename == "甲第００１号証.docx"


def test_unparseable_filename_raises(root_folder: Path) -> None:
    """番号抽出不可ファイル (例: メモ.docx) があると 409 相当。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "メモ.docx", "本文に番号なし", body="ただのメモ")

    with pytest.raises(InvalidMasterFilesError) as ei:
        merge_kogo(root_folder)
    issues = ei.value.issues
    assert len(issues) == 1
    assert issues[0].filename == "メモ.docx"
    assert "抽出できません" in issues[0].reason
    assert issues[0].suggested_rename is None


def test_duplicate_number_raises(root_folder: Path) -> None:
    """同一番号の重複 (canonical + non-canonical) で 409 相当。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")
    make_kogo_docx(master / "甲第００２号証 (1).docx", "【甲第２号証】")

    with pytest.raises(InvalidMasterFilesError) as ei:
        merge_kogo(root_folder)
    issues = ei.value.issues
    # 甲第００２号証 (1).docx が重複として報告される (suggested_rename=None)
    dup_issue = next(i for i in issues if i.filename == "甲第００２号証 (1).docx")
    assert "重複" in dup_issue.reason
    assert dup_issue.suggested_rename is None


def test_filesystem_unchanged_on_validation_error(root_folder: Path) -> None:
    """バリデーション失敗時、ファイルシステムには一切変更が加わらない。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲1号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "メモ.docx", "本文に番号なし", body="ただのメモ")

    before_files = sorted(p.name for p in master.iterdir())
    output_dir = root_folder / OUTPUT_DIRNAME
    before_output = sorted(p.name for p in output_dir.iterdir())

    with pytest.raises(InvalidMasterFilesError):
        merge_kogo(root_folder)

    after_files = sorted(p.name for p in master.iterdir())
    after_output = sorted(p.name for p in output_dir.iterdir())
    assert after_files == before_files, "個別マスタが変更されている"
    assert after_output == before_output, "結合甲号証フォルダが変更されている"
    # 結合結果は出力されない
    assert not (output_dir / OUTPUT_FILENAME).exists()


def test_suggested_rename_only_when_extractable(root_folder: Path) -> None:
    """suggested_rename は番号抽出可能なファイルにのみ付与される。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲1号証.docx", "【甲第１号証】")  # 抽出可
    make_kogo_docx(master / "メモ.docx", "本文無し", body="番号なし")  # 抽出不可

    pairs, issues = validate_master_files(master)
    assert pairs == []
    assert len(issues) == 2
    by_name = {i.filename: i for i in issues}
    assert by_name["甲1号証.docx"].suggested_rename == "甲第００１号証.docx"
    assert by_name["メモ.docx"].suggested_rename is None


def test_compliant_files_merge_normally(root_folder: Path) -> None:
    """規約準拠ファイルのみの場合は 409 にならず、正常に結合される。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")

    outcome = merge_kogo(root_folder)
    assert outcome.merged_files == ["甲第００１号証.docx", "甲第００２号証.docx"]
    assert outcome.output_path.exists()


# ---------------------------------------------------------------------------
# API 層のテスト (HTTP 409 レスポンス)
# ---------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("KOGO_KANRI_SETTINGS_PATH", str(tmp_path / "settings.json"))
    return TestClient(app)


def test_api_returns_invalid_event_with_issues(client: TestClient, tmp_path: Path) -> None:
    """規約外ファイルがあると /api/merge の SSE で `invalid` イベントが返る。"""
    root = tmp_path / "case"
    ensure_folders(root)
    master = root / MASTER_DIRNAME
    make_kogo_docx(master / "甲1号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "メモ.docx", "本文無し", body="番号なし")

    r = client.post("/api/merge", json={"root_folder": str(root)})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    events = parse_sse_events(r.text)
    invalid_events = [d for t, d in events if t == "invalid"]
    assert len(invalid_events) == 1
    d = invalid_events[0]
    assert d["error"] == "InvalidMasterFiles"
    assert "規約外" in d["message"]
    filenames = {i["filename"] for i in d["issues"]}
    assert filenames == {"甲1号証.docx", "メモ.docx"}
    # suggested_rename の付与状況を確認
    by_name = {i["filename"]: i for i in d["issues"]}
    assert by_name["甲1号証.docx"]["suggested_rename"] == "甲第００１号証.docx"
    assert by_name["メモ.docx"]["suggested_rename"] is None
    # done イベントは送出されない
    assert not any(t == "done" for t, _ in events)


def test_api_invalid_event_does_not_modify_filesystem(
    client: TestClient, tmp_path: Path
) -> None:
    """SSE で invalid イベントが返っても FS は不変。"""
    root = tmp_path / "case"
    ensure_folders(root)
    master = root / MASTER_DIRNAME
    make_kogo_docx(master / "甲1号証.docx", "【甲第１号証】")

    before = sorted(p.name for p in master.iterdir())
    r = client.post("/api/merge", json={"root_folder": str(root)})
    assert r.status_code == 200
    events = parse_sse_events(r.text)
    assert any(t == "invalid" for t, _ in events)
    after = sorted(p.name for p in master.iterdir())
    assert before == after
