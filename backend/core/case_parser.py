"""案件ファイル（申立書等）解析（仕様 §10）。

本文 + 表中から「甲第〇〇号証」表記を抽出し、正規化・重複排除・ソートして返す。
乙号証等は無視（本仕様の対象は甲号証のみ）。
"""

from __future__ import annotations

from pathlib import Path

from docx import Document

from .normalizer import KOSHOU_PATTERN, koshou_sort_key, normalize_koshou


def extract_koshou_from_case(case_docx: Path) -> list[str]:
    """案件ファイルから使用甲号証を抽出（重複排除・ソート済み）。"""
    case_docx = Path(case_docx)
    if not case_docx.is_file():
        raise FileNotFoundError(f'案件ファイルがありません: {case_docx}')

    doc = Document(str(case_docx))
    texts: list[str] = []
    for p in doc.paragraphs:
        texts.append(p.text)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    texts.append(p.text)

    full_text = '\n'.join(texts)
    seen: set[str] = set()
    found: list[str] = []
    for m in KOSHOU_PATTERN.finditer(full_text):
        norm = normalize_koshou(m.group(0))
        if norm and norm not in seen:
            seen.add(norm)
            found.append(norm)
    return sorted(found, key=koshou_sort_key)
