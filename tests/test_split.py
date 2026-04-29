# -*- coding: utf-8 -*-
"""
分解（split）機能のテスト。

結合 → 分解 → 再結合 のラウンドトリップで検証する。
"""

from __future__ import annotations

from pathlib import Path

from app.merge_service import (
    MASTER_DIRNAME,
    OUTPUT_DIRNAME,
    OUTPUT_FILENAME,
    ensure_folders,
    merge_kogo,
)
from app.kogo_normalizer import KogoNumber
from app.split_evidence_docx import split_docx
from app.split_service import split_kogo

from tests.conftest import collect_markers, make_kogo_docx


def _make_combined(root: Path, ids: list[int]) -> Path:
    """
    指定の主番号で `個別マスタ` を作り、merge_kogo で結合 docx を生成して
    そのパスを返す。ファイル名は分解後と一致させるため全角3桁ゼロ埋め。
    """
    ensure_folders(root)
    master = root / MASTER_DIRNAME
    for i in ids:
        stem = KogoNumber(i).normalized_filename_stem
        make_kogo_docx(master / f"{stem}.docx", f"【甲第{i}号証】")
    outcome = merge_kogo(root)
    return outcome.output_path


# ---------------------------------------------------------------------------
# split_docx 直接呼び出し
# ---------------------------------------------------------------------------

def test_split_docx_round_trip(tmp_path: Path) -> None:
    root = tmp_path / "case_a"
    combined = _make_combined(root, [1, 2, 3])

    out_dir = tmp_path / "split_out"
    produced = split_docx(combined, out_dir, verbose=False)

    assert len(produced) == 3
    names = sorted(p.name for p in produced)
    assert names == ["甲第００１号証.docx", "甲第００２号証.docx", "甲第００３号証.docx"]

    for p in produced:
        markers = collect_markers(p)
        assert len(markers) >= 1


def test_split_docx_branch_numbers(tmp_path: Path) -> None:
    """枝番付きマーカーも分解できる。"""
    root = tmp_path / "case_b"
    ensure_folders(root)
    master = root / MASTER_DIRNAME
    make_kogo_docx(master / "甲第０１２号証その１.docx", "【甲第０１２号証その１】")
    make_kogo_docx(master / "甲第０１２号証その２.docx", "【甲第０１２号証その２】")
    combined = merge_kogo(root).output_path

    out_dir = tmp_path / "split_branch_out"
    produced = split_docx(combined, out_dir, verbose=False)
    names = sorted(p.name for p in produced)
    assert names == ["甲第０１２号証その１.docx", "甲第０１２号証その２.docx"]


def test_split_docx_no_marker_raises(tmp_path: Path) -> None:
    """マーカーが無い docx は ValueError。"""
    from docx import Document

    bad = tmp_path / "no_marker.docx"
    doc = Document()
    doc.add_paragraph("これはマーカーを含まない普通の文書。")
    doc.save(str(bad))

    out_dir = tmp_path / "out"
    try:
        split_docx(bad, out_dir, verbose=False)
    except ValueError:
        return
    raise AssertionError("ValueError が送出されるべき")


# ---------------------------------------------------------------------------
# split_service: 個別マスタ統合
# ---------------------------------------------------------------------------

def test_split_kogo_writes_to_master(tmp_path: Path) -> None:
    root = tmp_path / "case_c"
    _make_combined(root, [1, 2, 3])

    # 結合済みファイルを別フォルダにコピーして、個別マスタは空に戻す
    master = root / MASTER_DIRNAME
    for f in master.glob("*.docx"):
        f.unlink()

    outcome = split_kogo(root)
    assert outcome.output_dir == master
    assert sorted(outcome.created_files) == [
        "甲第００１号証.docx",
        "甲第００２号証.docx",
        "甲第００３号証.docx",
    ]
    assert outcome.overwritten_files == []
    # 実際にファイルが存在する
    for name in outcome.created_files:
        assert (master / name).exists()


def test_split_kogo_overwrite_flag(tmp_path: Path) -> None:
    root = tmp_path / "case_d"
    _make_combined(root, [1, 2])

    master = root / MASTER_DIRNAME
    # 既存のマスタはそのまま (上書きされる側)
    outcome = split_kogo(root, overwrite=True)
    assert sorted(outcome.overwritten_files) == ["甲第００１号証.docx", "甲第００２号証.docx"]
    assert outcome.created_files == []


def test_split_kogo_no_overwrite_skips(tmp_path: Path) -> None:
    root = tmp_path / "case_e"
    _make_combined(root, [1])

    outcome = split_kogo(root, overwrite=False)
    # 既存ファイル(甲第００１号証.docx) と同名なのでスキップ
    assert outcome.created_files == []
    assert outcome.overwritten_files == []
    assert any("既存" in w for w in outcome.warnings)


def test_split_kogo_missing_input_raises(tmp_path: Path) -> None:
    root = tmp_path / "case_f"
    ensure_folders(root)
    # 結合 docx を生成しない
    try:
        split_kogo(root)
    except FileNotFoundError:
        return
    raise AssertionError("FileNotFoundError が送出されるべき")


# ---------------------------------------------------------------------------
# 結合→分解→再結合 のラウンドトリップで内容が保持される
# ---------------------------------------------------------------------------

def test_round_trip_merge_split_merge(tmp_path: Path) -> None:
    root = tmp_path / "case_g"
    _make_combined(root, [1, 2, 3])

    # 既存マスタを削除し、結合 docx から分解
    master = root / MASTER_DIRNAME
    for f in master.glob("*.docx"):
        f.unlink()
    split_kogo(root)

    # 分解後の個別マスタを使って再度結合
    # 既存 結合甲号証 をバックアップして比較対象を確保
    output_path = root / OUTPUT_DIRNAME / OUTPUT_FILENAME
    output_path.unlink()  # 旧結合をいったん削除して新規作成させる
    new_outcome = merge_kogo(root)

    # 再結合のマーカー順が昇順
    markers = collect_markers(new_outcome.output_path)
    assert markers[0] == "【甲第００１号証】"
    assert "【甲第００２号証】" in markers
    assert "【甲第００３号証】" in markers
