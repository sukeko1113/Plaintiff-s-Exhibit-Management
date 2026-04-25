"""甲号証リスト関連（仕様 §8）。

3 つの機能を提供:
1. 編集（OS 既定アプリで Word を開く） — `open_list` / API は os.startfile を呼ぶだけ
2. 個別マスタから自動生成 — `build_from_master`
3. 結合甲号証ファイルから自動生成 — `build_from_combined`

`read_list` はリスト .docx を解析して正規化済みラベルを返す。
"""

from __future__ import annotations

from pathlib import Path

from docx import Document

from .normalizer import koshou_sort_key, normalize_koshou
from .splitter import detect_sections


LIST_FILENAME = '甲号証リスト.docx'


def read_list(list_docx: Path) -> list[str]:
    """甲号証リスト.docx を読み、正規化済みラベルのリストを返す（重複排除・ソート済み）。"""
    doc = Document(str(list_docx))
    seen: set[str] = set()
    labels: list[str] = []
    for p in doc.paragraphs:
        norm = normalize_koshou(p.text)
        if norm and norm not in seen:
            labels.append(norm)
            seen.add(norm)
    return sorted(labels, key=koshou_sort_key)


def write_list(list_docx: Path, labels: list[str]) -> Path:
    """正規化済みラベルのリストを 1 段落 1 ラベルで .docx に書き出す（上書き）。"""
    list_docx = Path(list_docx)
    list_docx.parent.mkdir(parents=True, exist_ok=True)
    sorted_labels = sorted(set(labels), key=koshou_sort_key)
    doc = Document()
    for lbl in sorted_labels:
        doc.add_paragraph(lbl)
    doc.save(str(list_docx))
    return list_docx


def build_from_master(master_dir: Path) -> list[str]:
    """個別マスタフォルダ内のファイル名から正規化済みラベルを返す。

    .docx 以外、および正規化できないものはスキップ。
    """
    master_dir = Path(master_dir)
    if not master_dir.is_dir():
        raise NotADirectoryError(f'個別マスタフォルダがありません: {master_dir}')

    seen: set[str] = set()
    labels: list[str] = []
    for path in master_dir.iterdir():
        if path.suffix.lower() != '.docx':
            continue
        if path.name.startswith('~$'):  # Word の一時ファイル
            continue
        norm = normalize_koshou(path.stem)
        if norm and norm not in seen:
            labels.append(norm)
            seen.add(norm)
    return sorted(labels, key=koshou_sort_key)


def build_from_combined(combined_files: list[Path]) -> list[str]:
    """結合甲号証ファイル群からマーカーを抽出して正規化済みラベルを返す。"""
    seen: set[str] = set()
    labels: list[str] = []
    for f in combined_files:
        for label in detect_sections(Path(f)):
            if label not in seen:
                labels.append(label)
                seen.add(label)
    return sorted(labels, key=koshou_sort_key)
