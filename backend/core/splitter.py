"""結合甲号証 → 個別マスタ への分解（仕様書 §6, §7.2）。

安全性のために、元ファイルを丸ごとコピーしてから「自分の担当範囲外の段落」を
削除する方式を採用する。これによりスタイル・ヘッダ・フッタ・画像参照が壊れにくい。
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from docx import Document
from docx.oxml.ns import qn

from .normalizer import (
    label_to_filename,
    normalize_koshou_strict,
)


@dataclass
class SplitPoint:
    """各甲号証の開始位置情報。"""
    paragraph_index: int
    label: str


@dataclass
class ExtractedFile:
    label: str
    filename: str


def _has_page_break_before(para) -> bool:
    """段落自体が pageBreakBefore 設定を持つか、最初のラン直前の改ページを持つ。"""
    pPr = para._p.find(qn('w:pPr'))
    if pPr is not None and pPr.find(qn('w:pageBreakBefore')) is not None:
        return True
    for run in para.runs:
        for br in run._element.findall(qn('w:br')):
            if br.get(qn('w:type')) == 'page':
                return True
    return False


def _previous_para_ends_with_page_break(prev_para) -> bool:
    if prev_para is None:
        return False
    for run in prev_para.runs:
        for br in run._element.findall(qn('w:br')):
            if br.get(qn('w:type')) == 'page':
                return True
    pPr = prev_para._p.find(qn('w:pPr'))
    if pPr is not None and pPr.find(qn('w:sectPr')) is not None:
        return True
    return False


def find_split_points(doc: Document) -> List[SplitPoint]:
    """結合ファイルを走査して、各甲号証の開始段落と正規化ラベルを返す。"""
    paragraphs = doc.paragraphs
    points: List[SplitPoint] = []
    seen_first_label = False

    for i, para in enumerate(paragraphs):
        prev = paragraphs[i - 1] if i > 0 else None
        is_page_top = (
            i == 0
            or _has_page_break_before(para)
            or _previous_para_ends_with_page_break(prev)
        )
        if not is_page_top:
            continue

        target_index = i
        text = para.text.strip()
        if not text:
            j = i + 1
            while j < len(paragraphs) and not paragraphs[j].text.strip():
                j += 1
            if j >= len(paragraphs):
                break
            target_index = j
            text = paragraphs[j].text.strip()

        normalized = normalize_koshou_strict(text)
        if normalized is None:
            if seen_first_label:
                continue
            continue

        if points and points[-1].paragraph_index == target_index:
            continue
        points.append(SplitPoint(paragraph_index=target_index, label=normalized))
        seen_first_label = True

    return points


def _delete_paragraph_element(para) -> None:
    p = para._p
    parent = p.getparent()
    if parent is not None:
        parent.remove(p)


def _slice_document(src: Path, dst: Path, start_index: int, end_index: Optional[int]) -> None:
    """src を dst にコピーした上で、[start_index, end_index) 範囲外の段落を削除する。

    end_index が None なら末尾まで残す。
    """
    shutil.copyfile(src, dst)
    doc = Document(str(dst))
    paragraphs = list(doc.paragraphs)
    total = len(paragraphs)

    end = total if end_index is None else end_index

    for idx in range(total - 1, end - 1, -1):
        if idx >= total:
            continue
        _delete_paragraph_element(paragraphs[idx])

    for idx in range(start_index - 1, -1, -1):
        _delete_paragraph_element(paragraphs[idx])

    doc.save(str(dst))


def split_combined_file(combined_path: Path, output_dir: Path) -> List[ExtractedFile]:
    """結合甲号証ファイルを分解して個別ファイルとして保存する。

    既存ファイルがあれば上書きする（呼び出し側で必要に応じて事前にクリアする）。
    """
    if not combined_path.exists():
        raise FileNotFoundError(f'結合甲号証ファイルが見つかりません: {combined_path}')
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = Document(str(combined_path))
    points = find_split_points(doc)
    if not points:
        raise ValueError(
            '結合甲号証ファイルから甲号証の区切りを検出できませんでした。'
            '改ページの位置と先頭段落のラベル表記を確認してください。'
        )

    extracted: List[ExtractedFile] = []
    for i, point in enumerate(points):
        end_index = points[i + 1].paragraph_index if i + 1 < len(points) else None
        filename = label_to_filename(point.label)
        dst = output_dir / filename
        _slice_document(combined_path, dst, point.paragraph_index, end_index)
        extracted.append(ExtractedFile(label=point.label, filename=filename))

    return extracted
