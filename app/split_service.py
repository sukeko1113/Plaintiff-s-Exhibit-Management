# -*- coding: utf-8 -*-
"""
甲号証 分解サービス。

ルートフォルダ直下の `結合甲号証/結合甲号証.docx` を読み、マーカーごとに
分割して `個別マスタ/` 配下に正規化済みファイル名で保存する。
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from app.merge_service import MASTER_DIRNAME, OUTPUT_DIRNAME, OUTPUT_FILENAME, ensure_folders
from app.split_evidence_docx import split_docx


logger = logging.getLogger(__name__)


@dataclass
class SplitOutcome:
    """分解処理の結果。"""

    output_dir: Path
    created_files: List[str] = field(default_factory=list)
    overwritten_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def split_kogo(
    root_folder: Path,
    input_path: Optional[Path] = None,
    overwrite: bool = True,
) -> SplitOutcome:
    """
    結合 docx を分解して 個別マスタ に保存する。

    Parameters
    ----------
    root_folder : ルートフォルダ
    input_path : 結合元 docx。None なら `<root>/結合甲号証/結合甲号証.docx`。
    overwrite : 同名ファイルが個別マスタにある場合に上書きするか。
        False の場合は警告に記録してスキップする。
    """
    root = ensure_folders(Path(root_folder))
    if input_path is None:
        input_path = root / OUTPUT_DIRNAME / OUTPUT_FILENAME
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"分解元ファイルが存在しません: {input_path}")

    master_dir = root / MASTER_DIRNAME
    warnings: List[str] = []

    workdir = Path(tempfile.mkdtemp(prefix="kogo_split_"))
    try:
        produced = split_docx(input_path, workdir, verbose=False)

        created: List[str] = []
        overwritten: List[str] = []

        for src in produced:
            dst = master_dir / src.name
            if dst.exists():
                if not overwrite:
                    warnings.append(f"既存のためスキップ: {dst.name}")
                    continue
                overwritten.append(dst.name)
            else:
                created.append(dst.name)
            shutil.move(str(src), str(dst))

        return SplitOutcome(
            output_dir=master_dir,
            created_files=created,
            overwritten_files=overwritten,
            warnings=warnings,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
