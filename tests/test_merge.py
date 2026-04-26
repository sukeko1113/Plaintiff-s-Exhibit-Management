# -*- coding: utf-8 -*-
"""
甲号証 結合機能のテスト (T1〜T11)
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
    LIST_FILENAME,
    MASTER_DIRNAME,
    OUTPUT_DIRNAME,
    OUTPUT_FILENAME,
    ensure_folders,
    merge_kogo,
    read_kogo_list,
)

from tests.conftest import (
    collect_markers,
    has_pagebreak,
    make_kogo_docx,
    make_list_docx,
    make_list_docx_with_table,
)


# ---------------------------------------------------------------------------
# 番号正規化のユニットテスト（T7 を含む）
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
# T10: フォルダ自動生成
# ---------------------------------------------------------------------------

def test_t10_ensure_folders_creates_structure(root_folder: Path) -> None:
    """T10: フォルダがない状態で起動 → 必要なフォルダ・空のリストファイルが自動生成される。"""
    assert not root_folder.exists()

    ensure_folders(root_folder)

    assert (root_folder / MASTER_DIRNAME).is_dir()
    assert (root_folder / OUTPUT_DIRNAME).is_dir()
    assert (root_folder / LIST_FILENAME).is_file()

    # 空のリストとして読み込める
    keys, warnings = read_kogo_list(root_folder / LIST_FILENAME)
    assert keys == set()
    assert warnings == []


# ---------------------------------------------------------------------------
# T1: リストが存在しない（ensure_folders 前提なので、リストファイルを削除して検証）
# ---------------------------------------------------------------------------

def test_t1_no_list_merges_all_master(root_folder: Path) -> None:
    """T1: リスト不在 → 個別マスタ全件を結合。"""
    ensure_folders(root_folder)
    # 空のリストファイルを意図的に削除して「不在」状態にする
    (root_folder / LIST_FILENAME).unlink()

    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")
    make_kogo_docx(master / "甲第００３号証.docx", "【甲第３号証】")

    # ensure_folders を merge_kogo 内で再実行して空リストが作られるが、
    # 空 → list_used=False となり全件結合になる
    outcome = merge_kogo(root_folder)

    assert outcome.list_used is False
    assert len(outcome.merged_files) == 3
    assert outcome.missing_in_master == []
    assert outcome.output_path.exists()


# ---------------------------------------------------------------------------
# T2: リストが空（段落はあるが番号なし）
# ---------------------------------------------------------------------------

def test_t2_empty_list_merges_all_master(root_folder: Path) -> None:
    """T2: 段落はあるが番号は無い → 個別マスタ全件を結合。"""
    ensure_folders(root_folder)
    make_list_docx(
        root_folder / LIST_FILENAME,
        ["甲号証リスト", "ここに番号を書きます", "メモ: なし"],
    )

    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")

    outcome = merge_kogo(root_folder)

    assert outcome.list_used is False
    assert len(outcome.merged_files) == 2


# ---------------------------------------------------------------------------
# T3: リストに3件、個別マスタに10件 → リストの3件のみ結合
# ---------------------------------------------------------------------------

def test_t3_list_subset_selects_only_listed(root_folder: Path) -> None:
    ensure_folders(root_folder)
    make_list_docx(
        root_folder / LIST_FILENAME,
        ["甲第２号証", "甲第５号証", "甲第９号証"],
    )

    master = root_folder / MASTER_DIRNAME
    for i in range(1, 11):
        make_kogo_docx(master / f"甲第{i:03d}号証.docx", f"【甲第{i}号証】")

    outcome = merge_kogo(root_folder)

    assert outcome.list_used is True
    assert len(outcome.merged_files) == 3
    assert outcome.missing_in_master == []
    # 結合後のマーカーが昇順
    markers = collect_markers(outcome.output_path)
    expected = [
        KogoNumber(2).normalized_marker,
        KogoNumber(5).normalized_marker,
        KogoNumber(9).normalized_marker,
    ]
    # collect_markers は本文を全部走査するので、最初の3件が昇順であることを確認
    assert markers[: len(expected)] == expected


# ---------------------------------------------------------------------------
# T4: リストに「甲第 1号証」、マスタに「甲第００１号証.docx」 → マッチ
# ---------------------------------------------------------------------------

def test_t4_halfwidth_list_matches_zenkaku_master(root_folder: Path) -> None:
    ensure_folders(root_folder)
    make_list_docx(root_folder / LIST_FILENAME, ["甲第 1号証"])

    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第００１号証】")

    outcome = merge_kogo(root_folder)

    assert outcome.list_used is True
    assert outcome.merged_files == ["甲第００１号証.docx"]
    assert outcome.missing_in_master == []


# ---------------------------------------------------------------------------
# T5: 枝番指定 → 枝番ありのファイルだけ選ばれる（その２は除外）
# ---------------------------------------------------------------------------

def test_t5_branch_number_selection(root_folder: Path) -> None:
    ensure_folders(root_folder)
    make_list_docx(root_folder / LIST_FILENAME, ["甲第０１２号証その１"])

    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第０１２号証その１.docx", "【甲第０１２号証その１】")
    make_kogo_docx(master / "甲第０１２号証その２.docx", "【甲第０１２号証その２】")
    make_kogo_docx(master / "甲第０１２号証.docx", "【甲第０１２号証】")

    outcome = merge_kogo(root_folder)

    assert outcome.list_used is True
    assert outcome.merged_files == ["甲第０１２号証その１.docx"]


# ---------------------------------------------------------------------------
# T6: リスト掲載・マスタ不在 → missing_in_master に正規化マーカーで記録
# ---------------------------------------------------------------------------

def test_t6_missing_in_master_recorded(root_folder: Path) -> None:
    ensure_folders(root_folder)
    make_list_docx(root_folder / LIST_FILENAME, ["甲第１号証", "甲第２号証", "甲第３号証"])

    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    # 甲第２号証 は意図的に作成しない
    make_kogo_docx(master / "甲第００３号証.docx", "【甲第３号証】")

    outcome = merge_kogo(root_folder)

    assert outcome.list_used is True
    assert outcome.merged_files == ["甲第００１号証.docx", "甲第００３号証.docx"]
    assert outcome.missing_in_master == ["【甲第００２号証】"]


# ---------------------------------------------------------------------------
# T7: 全角・半角の混在表記 → 全て同じ番号として正規化される
# ---------------------------------------------------------------------------

def test_t7_mixed_width_normalized_same(root_folder: Path) -> None:
    ensure_folders(root_folder)
    # 同じ番号(=1)の複数表記 + 重複だけのリスト
    make_list_docx(
        root_folder / LIST_FILENAME,
        ["甲第１号証", "甲第 1号証", "甲第０1号証", "甲01号証", "甲第1号証"],
    )

    keys, warnings = read_kogo_list(root_folder / LIST_FILENAME)
    assert keys == {(1, None)}  # 全て同一
    # T11 と関連: 重複の警告も出る
    assert any("重複" in w for w in warnings)

    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")

    outcome = merge_kogo(root_folder)
    assert outcome.merged_files == ["甲第００１号証.docx"]
    # 重複警告が伝播していること
    assert any("重複" in w for w in outcome.warnings)


# ---------------------------------------------------------------------------
# T8: 結合後 docx を開いてマーカーが昇順
# ---------------------------------------------------------------------------

def test_t8_merged_markers_sorted(root_folder: Path) -> None:
    ensure_folders(root_folder)
    make_list_docx(
        root_folder / LIST_FILENAME,
        ["甲第３号証", "甲第１号証", "甲第２号証"],  # わざと逆順
    )

    master = root_folder / MASTER_DIRNAME
    for i in (1, 2, 3):
        make_kogo_docx(master / f"甲第{i:03d}号証.docx", f"【甲第{i}号証】")

    outcome = merge_kogo(root_folder)
    markers = collect_markers(outcome.output_path)
    expected = [
        KogoNumber(1).normalized_marker,
        KogoNumber(2).normalized_marker,
        KogoNumber(3).normalized_marker,
    ]
    assert markers[: len(expected)] == expected


# ---------------------------------------------------------------------------
# T9: 結合後 docx で各甲号証が新ページ先頭から始まる（最終ファイル除く）
# ---------------------------------------------------------------------------

def test_t9_pagebreak_between_files(root_folder: Path) -> None:
    ensure_folders(root_folder)
    make_list_docx(root_folder / LIST_FILENAME, ["甲第１号証", "甲第２号証", "甲第３号証"])

    master = root_folder / MASTER_DIRNAME
    for i in (1, 2, 3):
        make_kogo_docx(master / f"甲第{i:03d}号証.docx", f"【甲第{i}号証】")

    outcome = merge_kogo(root_folder)
    # 3 ファイル → 区切りは 2 箇所（最後には付かない）
    assert has_pagebreak(outcome.output_path, expected_count=2)


# ---------------------------------------------------------------------------
# T11: 同じ番号の重複（リスト or マスタ）→ 警告を出すが処理は継続
# ---------------------------------------------------------------------------

def test_t11_duplicate_in_list_warns_but_continues(root_folder: Path) -> None:
    ensure_folders(root_folder)
    make_list_docx(root_folder / LIST_FILENAME, ["甲第１号証", "甲第１号証", "甲第２号証"])

    master = root_folder / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")

    outcome = merge_kogo(root_folder)
    assert outcome.list_used is True
    assert outcome.merged_files == ["甲第００１号証.docx", "甲第００２号証.docx"]
    assert any("重複" in w for w in outcome.warnings)


def test_t11_duplicate_in_master_warns_but_continues(tmp_path: Path) -> None:
    """マスタ側に同じ番号が2ファイルある場合も警告 + 処理継続。"""
    root = tmp_path / "case2"
    ensure_folders(root)

    master = root / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００１号証_別.docx", "【甲第１号証】")

    outcome = merge_kogo(root)
    # 重複を検出して片方だけ採用
    assert len(outcome.merged_files) == 1
    assert any("重複" in w for w in outcome.warnings)


# ---------------------------------------------------------------------------
# 補助: read_kogo_list の表セル対応
# ---------------------------------------------------------------------------

def test_read_list_from_table_cells(root_folder: Path) -> None:
    ensure_folders(root_folder)
    make_list_docx_with_table(
        root_folder / LIST_FILENAME,
        ["甲第１号証", "甲第２号証", "甲第０１２号証その１"],
    )

    keys, warnings = read_kogo_list(root_folder / LIST_FILENAME)
    assert keys == {(1, None), (2, None), (12, 1)}


# ---------------------------------------------------------------------------
# 補助: detect_number はファイル名・本文を両方判定
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
