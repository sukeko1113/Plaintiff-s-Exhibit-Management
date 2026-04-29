# -*- coding: utf-8 -*-
"""
結合時のソート規則検証 (リスト機能廃止後の新方式)。

仕様:
- 個別マスタ配下の docx を**正規化ファイル名で辞書順ソート**して結合
- 主番号順 / 枝番なしが枝番ありより先 / `~$` 一時ファイル除外
"""

from __future__ import annotations

from pathlib import Path

from app.merge_service import (
    MASTER_DIRNAME,
    ensure_folders,
    merge_kogo,
)

from tests.conftest import make_kogo_docx


def test_sort_main_number_ascending(root_folder: Path) -> None:
    """主番号順に並ぶ (甲第００１号証 → 甲第００２号証 → … → 甲第０１０号証)。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    # わざと作成順を逆にして、ソート結果が作成順に依存しないことを確認
    for i in [10, 5, 1, 7, 2, 3, 4, 6, 8, 9]:
        make_kogo_docx(master / f"甲第{i:03d}号証.docx".translate(
            str.maketrans("0123456789", "０１２３４５６７８９")
        ), f"【甲第{i}号証】")

    outcome = merge_kogo(root_folder)
    expected = [
        f"甲第{i:03d}号証.docx".translate(
            str.maketrans("0123456789", "０１２３４５６７８９")
        )
        for i in range(1, 11)
    ]
    assert outcome.merged_files == expected


def test_sort_no_branch_before_branch(root_folder: Path) -> None:
    """枝番なしが枝番ありより先に並ぶ。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    # わざと枝番付きを先に作成
    make_kogo_docx(master / "甲第００１号証その３.docx", "【甲第００１号証その３】")
    make_kogo_docx(master / "甲第００１号証その２.docx", "【甲第００１号証その２】")
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第００１号証】")

    outcome = merge_kogo(root_folder)
    assert outcome.merged_files == [
        "甲第００１号証.docx",
        "甲第００１号証その２.docx",
        "甲第００１号証その３.docx",
    ]


def test_sort_excludes_word_temp_files(root_folder: Path) -> None:
    """`~$` で始まる Word 一時ファイルは結合対象から除外される。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")
    # 一時ロックファイル相当 (空 docx を作成)
    (master / "~$甲第００１号証.docx").write_bytes(b"")

    outcome = merge_kogo(root_folder)
    assert outcome.merged_files == ["甲第００１号証.docx", "甲第００２号証.docx"]


def test_sort_main_number_with_branches_mixed(root_folder: Path) -> None:
    """主番号と枝番が混在しても正しく並ぶ。"""
    ensure_folders(root_folder)
    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")
    make_kogo_docx(master / "甲第００１号証その２.docx", "【甲第００１号証その２】")
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第００１号証】")

    outcome = merge_kogo(root_folder)
    # 主番号 1 (枝番なし) → 主番号 1 (その２) → 主番号 2 の順
    assert outcome.merged_files == [
        "甲第００１号証.docx",
        "甲第００１号証その２.docx",
        "甲第００２号証.docx",
    ]
