"""結合甲号証 → 個別マスタ への分解（仕様書 §6, §7.2）。

「甲号証の単位」は、`【甲第xxx号証】` 等の正規化ラベルとしてマッチする段落から、
次の同種ラベル段落の直前までとする（改ページや sectPr の有無は問わない）。

安全性のために、元ファイルを丸ごとコピーしてから「自分の担当範囲外の段落」を
削除する方式を採用する。これによりスタイル・ヘッダ・フッタ・画像参照が壊れにくい。
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from docx import Document

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


def find_split_points(doc: Document) -> List[SplitPoint]:
    """結合ファイルを走査して、各甲号証の開始段落と正規化ラベルを返す。

    判定ルール: 段落のテキスト全体が ``normalize_koshou_strict`` にマッチした
    場合、その段落を 1 つの甲号証の開始位置とする。次のマッチ段落の直前までが
    その甲号証の範囲となる。
    """
    points: List[SplitPoint] = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue
        normalized = normalize_koshou_strict(text)
        if normalized is None:
            continue
        points.append(SplitPoint(paragraph_index=i, label=normalized))
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
            '【甲第〇〇号証】等のラベル段落が含まれているか確認してください。'
        )

    extracted: List[ExtractedFile] = []
    for i, point in enumerate(points):
        end_index = points[i + 1].paragraph_index if i + 1 < len(points) else None
        filename = label_to_filename(point.label)
        dst = output_dir / filename
        _slice_document(combined_path, dst, point.paragraph_index, end_index)
        extracted.append(ExtractedFile(label=point.label, filename=filename))

    return extracted
