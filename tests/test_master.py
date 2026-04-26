# -*- coding: utf-8 -*-
"""
個別マスタ一覧サービスのテスト。
"""

from __future__ import annotations

from pathlib import Path

from app.master_service import list_master
from app.merge_service import MASTER_DIRNAME, ensure_folders

from tests.conftest import make_kogo_docx


def test_list_master_empty(tmp_path: Path) -> None:
    root = tmp_path / "case"
    ensure_folders(root)
    listing = list_master(root)
    assert listing.entries == []
    assert listing.warnings == []


def test_list_master_sorted_by_number(tmp_path: Path) -> None:
    root = tmp_path / "case"
    ensure_folders(root)
    master = root / MASTER_DIRNAME
    make_kogo_docx(master / "甲第０１０号証.docx", "【甲第１０号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")
    make_kogo_docx(master / "甲第００５号証.docx", "【甲第５号証】")

    listing = list_master(root)
    mains = [e.main for e in listing.entries]
    assert mains == [2, 5, 10]
    markers = [e.normalized_marker for e in listing.entries]
    assert markers == ["【甲第００２号証】", "【甲第００５号証】", "【甲第０１０号証】"]


def test_list_master_skips_temp_files(tmp_path: Path) -> None:
    root = tmp_path / "case"
    ensure_folders(root)
    master = root / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    # Word の一時ファイル: ~$ で始まるファイルは除外される
    (master / "~$甲第００１号証.docx").write_bytes(b"junk")

    listing = list_master(root)
    assert [e.filename for e in listing.entries] == ["甲第００１号証.docx"]


def test_list_master_unrecognized_filename_warns(tmp_path: Path) -> None:
    root = tmp_path / "case"
    ensure_folders(root)
    master = root / MASTER_DIRNAME
    # 番号が抽出できない docx
    from docx import Document
    bad = master / "memo.docx"
    d = Document()
    d.add_paragraph("メモ")
    d.save(str(bad))

    listing = list_master(root)
    # 番号不明なエントリでも一覧には載る
    names = [e.filename for e in listing.entries]
    assert "memo.docx" in names
    bad_entry = next(e for e in listing.entries if e.filename == "memo.docx")
    assert bad_entry.normalized_marker is None
    assert bad_entry.main is None
    assert listing.warnings
