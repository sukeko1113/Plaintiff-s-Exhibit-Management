# -*- coding: utf-8 -*-
"""
個別マスタ一覧サービス。

個別マスタ フォルダ内の docx を列挙して、(番号, ファイル名) の一覧を返す。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.kogo_normalizer import KogoNumber, detect_number
from app.merge_service import MASTER_DIRNAME, ensure_folders


@dataclass
class MasterEntry:
    filename: str
    normalized_marker: Optional[str]
    # SPEC §7.1.4 準拠の正規化キー(個別マスタ生成時に §7.1.4 形式が保証されている前提)。
    # detect_number 成功時のみ値を持ち、番号不明時は None。
    # 将来 §7.1.4 違反ファイル名を検出するバリデーション機能を追加する場合は別 PR で対応。
    normalized_key: Optional[str]
    main: Optional[int]
    branch: Optional[int]
    size_bytes: int


@dataclass
class MasterListing:
    master_dir: Path
    entries: List[MasterEntry]
    warnings: List[str]


def list_master(root_folder: Path) -> MasterListing:
    """個別マスタ内の docx を番号順に列挙。"""
    root = ensure_folders(Path(root_folder))
    master_dir = root / MASTER_DIRNAME

    entries: List[MasterEntry] = []
    warnings: List[str] = []

    for path in sorted(master_dir.glob("*.docx")):
        if path.name.startswith("~$"):
            continue
        try:
            kogo: Optional[KogoNumber] = detect_number(path)
        except ValueError as e:
            warnings.append(str(e))
            kogo = None

        entries.append(MasterEntry(
            filename=path.name,
            normalized_marker=kogo.normalized_marker if kogo else None,
            normalized_key=path.stem if kogo else None,
            main=kogo.main if kogo else None,
            branch=kogo.branch if kogo else None,
            size_bytes=path.stat().st_size,
        ))

    entries.sort(key=lambda e: (
        0 if e.main is not None else 1,
        e.main if e.main is not None else 0,
        e.branch if e.branch is not None else 0,
        e.filename,
    ))

    return MasterListing(master_dir=master_dir, entries=entries, warnings=warnings)
