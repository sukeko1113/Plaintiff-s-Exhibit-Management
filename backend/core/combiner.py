"""個別マスタ → 結合甲号証 への結合（仕様書 §7.6）。

docxcompose を使い、書式・画像・スタイルを保ったまま順に結合する。
2 つ目以降のファイルの先頭には改ページを挿入する。
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml.ns import qn
from docxcompose.composer import Composer

from .normalizer import label_to_filename


@dataclass
class CombineResult:
    output_path: Path
    missing: List[str]
    used: List[str]


def _has_leading_page_break(para) -> bool:
    for run in para.runs:
        for br in run._element.findall(qn('w:br')):
            if br.get(qn('w:type')) == 'page':
                return True
    return False


def _ensure_starts_with_page_break(path: Path) -> None:
    """ファイル先頭の最初の段落にページブレイクを挿入する。"""
    doc = Document(str(path))
    if not doc.paragraphs:
        para = doc.add_paragraph()
    else:
        para = doc.paragraphs[0]
    if _has_leading_page_break(para):
        return
    target_run = para.runs[0] if para.runs else para.add_run()
    target_run.add_break(WD_BREAK.PAGE)
    doc.save(str(path))


def combine_files(
    master_dir: Path,
    labels: List[str],
    output_path: Path,
    head_doc: Optional[Path] = None,
) -> CombineResult:
    """labels の順序で個別マスタを結合し、output_path に保存する。

    ``head_doc`` が指定されていれば、その文書を冒頭に置き、その後に各甲号証を続ける。
    各甲号証のコピーには先頭に改ページを挿入する。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    available: List[tuple[str, Path]] = []
    missing: List[str] = []
    for label in labels:
        candidate = master_dir / label_to_filename(label)
        if candidate.exists():
            available.append((label, candidate))
        else:
            missing.append(label)

    if not available and head_doc is None:
        raise ValueError('結合できる個別マスタファイルが 1 件もありません。')

    work_dir = output_path.parent / f'.{output_path.stem}_tmp'
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=False)

    used: List[str] = []
    try:
        if head_doc is not None:
            base_path = work_dir / 'head.docx'
            shutil.copyfile(head_doc, base_path)
            files_to_append = available
        else:
            first_label, first_src = available[0]
            base_path = work_dir / f'000_{first_label}.docx'
            shutil.copyfile(first_src, base_path)
            files_to_append = available[1:]
            used.append(first_label)

        base_doc = Document(str(base_path))
        composer = Composer(base_doc)

        for idx, (label, src) in enumerate(files_to_append, start=1):
            tmp = work_dir / f'{idx:03d}_{label}.docx'
            shutil.copyfile(src, tmp)
            _ensure_starts_with_page_break(tmp)
            composer.append(Document(str(tmp)))
            used.append(label)

        composer.save(str(output_path))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return CombineResult(output_path=output_path, missing=missing, used=used)
