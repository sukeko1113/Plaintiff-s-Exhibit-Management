# -*- coding: utf-8 -*-
"""
甲号証 結合機能のテスト。

リスト機能廃止後の仕様:
- 個別マスタ配下の docx をファイル名辞書順で結合
- 規約外ファイルがあれば InvalidMasterFilesError を送出
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.kogo_normalizer import (
    KogoNumber,
    detect_number,
    extract_number_from_text,
    normalize_main_number,
    normalize_branch_number,
)
from app.merge_service import (
    MASTER_DIRNAME,
    OUTPUT_DIRNAME,
    OUTPUT_FILENAME,
    InvalidMasterFilesError,
    ensure_folders,
    merge_kogo,
)

from tests.conftest import (
    collect_markers,
    has_pagebreak,
    make_kogo_docx,
)


# ---------------------------------------------------------------------------
# 番号正規化のユニットテスト
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1", "００１"),
        ("01", "００１"),
        ("０1", "００１"),
        ("12", "０１２"),
        ("１２", "０１２"),
        ("123", "１２３"),
        ("1234", "１２３４"),
    ],
)
def test_normalize_main_number(raw: str, expected: str) -> None:
    assert normalize_main_number(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1", "１"),
        ("3", "３"),
        ("１０", "１０"),
    ],
)
def test_normalize_branch_number(raw: str, expected: str) -> None:
    assert normalize_branch_number(raw) == expected


@pytest.mark.parametrize(
    "text, expected_main, expected_branch",
    [
        ("【甲第１号証】", 1, None),
        ("【甲第 1号証】", 1, None),
        ("【甲第０1号証】", 1, None),
        ("甲01号証", 1, None),
        ("甲第1号証", 1, None),
        ("甲第 12号証", 12, None),
        ("【甲第０１２号証その１】", 12, 1),
        ("甲第０１２号証その3", 12, 3),
        ("甲２０号証", 20, None),
    ],
)
def test_extract_number_from_text(text: str, expected_main: int, expected_branch) -> None:
    kogo = extract_number_from_text(text)
    assert kogo is not None
    assert kogo.main == expected_main
    assert kogo.branch == expected_branch


# ---------------------------------------------------------------------------
# フォルダ自動生成
# ---------------------------------------------------------------------------

def test_ensure_folders_creates_structure(root_folder: Path) -> None:
    """ensure_folders で個別マスタ・結合甲号証フォルダが作成される。"""
    assert not root_folder.exists()

    ensure_folders(root_folder)

    assert (root_folder / MASTER_DIRNAME).is_dir()
    assert (root_folder / OUTPUT_DIRNAME).is_dir()
    # 甲号証リスト.docx は作成されない (廃止)
    assert not (root_folder / "甲号証リスト.docx").exists()


# ---------------------------------------------------------------------------
# 結合: 全件結合
# ---------------------------------------------------------------------------

def test_merge_all_master_files(root_folder: Path) -> None:
    """個別マスタ全件をファイル名辞書順で結合する。"""
    ensure_folders(root_folder)

    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")
    make_kogo_docx(master / "甲第００３号証.docx", "【甲第３号証】")

    outcome = merge_kogo(root_folder)

    assert len(outcome.merged_files) == 3
    assert outcome.merged_files == [
        "甲第００１号証.docx",
        "甲第００２号証.docx",
        "甲第００３号証.docx",
    ]
    assert outcome.output_path.exists()
    assert outcome.output_path.name == OUTPUT_FILENAME


def test_merge_empty_master(root_folder: Path) -> None:
    """個別マスタが空の場合、警告付きで空結果を返す。"""
    ensure_folders(root_folder)
    outcome = merge_kogo(root_folder)
    assert outcome.merged_files == []
    assert any("結合対象のファイルがありません" in w for w in outcome.warnings)


def test_merge_invokes_progress_callback(root_folder: Path) -> None:
    """on_progress コールバックが各フェーズで呼ばれる。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")

    messages: list[str] = []
    merge_kogo(root_folder, on_progress=messages.append)

    # バリデーション、準備、結合、保存の各フェーズが含まれる
    assert any("バリデーション" in m for m in messages)
    assert any("準備" in m for m in messages)
    assert any("結合" in m for m in messages)
    assert any("保存" in m for m in messages)
    # 各ファイル名がメッセージに登場する
    assert any("甲第００１号証" in m for m in messages)
    assert any("甲第００２号証" in m for m in messages)


# ---------------------------------------------------------------------------
# 結合後の本文マーカーが昇順
# ---------------------------------------------------------------------------

def test_merged_markers_sorted(root_folder: Path) -> None:
    """正規化ファイル名で辞書順 → 結合後の本文マーカーが昇順に並ぶ。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")
    make_kogo_docx(master / "甲第００３号証.docx", "【甲第３号証】")

    outcome = merge_kogo(root_folder)
    markers = collect_markers(outcome.output_path)
    expected = [
        KogoNumber(1).normalized_marker,
        KogoNumber(2).normalized_marker,
        KogoNumber(3).normalized_marker,
    ]
    assert markers[: len(expected)] == expected


# ---------------------------------------------------------------------------
# 結合後 docx で各甲号証が新ページ先頭から始まる（最終ファイル除く）
# ---------------------------------------------------------------------------

def test_pagebreak_between_files(root_folder: Path) -> None:
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")
    make_kogo_docx(master / "甲第００３号証.docx", "【甲第３号証】")

    outcome = merge_kogo(root_folder)
    # 3 ファイル → 区切りは 2 箇所（最後には付かない）
    assert has_pagebreak(outcome.output_path, expected_count=2)


# ---------------------------------------------------------------------------
# 重複検出: 同じ番号のファイルが 2 つあると 409 (バリデーションで弾く)
# ---------------------------------------------------------------------------

def test_duplicate_number_in_master_raises(root_folder: Path) -> None:
    """同じ (main, branch) のファイルが複数あれば InvalidMasterFilesError。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    # 規約外ファイル名: 通常はバリデーションで先に弾かれるが、別パスで重複検証も入る
    make_kogo_docx(master / "甲第００１号証_別.docx", "【甲第１号証】")

    with pytest.raises(InvalidMasterFilesError) as ei:
        merge_kogo(root_folder)
    # 規約外ファイル名側 (甲第００１号証_別.docx) が issues に含まれる
    issues = ei.value.issues
    assert any(i.filename == "甲第００１号証_別.docx" for i in issues)


# ---------------------------------------------------------------------------
# detect_number: ファイル名・本文を両方判定
# ---------------------------------------------------------------------------

def test_detect_number_prefers_body(tmp_path: Path) -> None:
    # ファイル名と本文で番号が違う場合、本文を優先
    p = tmp_path / "甲第００５号証.docx"
    make_kogo_docx(p, "【甲第１０号証】")
    kogo = detect_number(p)
    assert kogo.main == 10


def test_detect_number_falls_back_to_filename(tmp_path: Path) -> None:
    p = tmp_path / "甲第００７号証.docx"
    make_kogo_docx(p, "本文に番号なし", body="番号は未記載")
    kogo = detect_number(p)
    assert kogo.main == 7
