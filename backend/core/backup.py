"""バックアップ世代管理（仕様書 v02 §4.6）。

破壊的操作の前にファイル／ディレクトリを `<root>/_backup/YYYYMMDD-HHMMSS/...` へ退避する。
最新 ``MAX_GENERATIONS`` 件のみ保持し、それ以上古い世代は自動削除する。
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

BACKUP_DIR = '_backup'
MAX_GENERATIONS = 10
_TIMESTAMP_RE = re.compile(r'^\d{8}-\d{6}$')


def _now_stamp() -> str:
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def get_backup_root(root_path: str | Path) -> Path:
    return Path(root_path) / BACKUP_DIR


def ensure_backup_root(root_path: str | Path) -> Path:
    backup = get_backup_root(root_path)
    backup.mkdir(parents=True, exist_ok=True)
    return backup


def list_generations(root_path: str | Path) -> List[Path]:
    """新しい順に並んだバックアップ世代ディレクトリを返す。"""
    backup = get_backup_root(root_path)
    if not backup.exists():
        return []
    gens = [p for p in backup.iterdir() if p.is_dir() and _TIMESTAMP_RE.match(p.name)]
    gens.sort(key=lambda p: p.name, reverse=True)
    return gens


def prune_old_generations(root_path: str | Path, keep: int = MAX_GENERATIONS) -> int:
    """``keep`` 世代を超えた古い世代を削除して、削除件数を返す。"""
    gens = list_generations(root_path)
    removed = 0
    for old in gens[keep:]:
        shutil.rmtree(old, ignore_errors=True)
        removed += 1
    return removed


def _new_generation(root_path: str | Path) -> Path:
    backup = ensure_backup_root(root_path)
    stamp = _now_stamp()
    target = backup / stamp
    counter = 1
    while target.exists():
        counter += 1
        target = backup / f'{stamp}-{counter}'
    target.mkdir(parents=True, exist_ok=False)
    return target


def backup_paths(root_path: str | Path, sources: List[Path]) -> Path | None:
    """指定された複数のパス（ファイル or ディレクトリ）を 1 世代にまとめて退避する。

    退避先のルート（世代ディレクトリ）を返す。退避対象が 1 つも存在しなければ None。
    """
    existing = [p for p in sources if p.exists()]
    if not existing:
        return None

    generation = _new_generation(root_path)
    root = Path(root_path)

    for src in existing:
        try:
            rel = src.relative_to(root)
        except ValueError:
            rel = Path(src.name)
        dst = generation / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    prune_old_generations(root_path)
    return generation
