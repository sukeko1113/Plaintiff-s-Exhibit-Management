"""バックアップ世代管理（仕様 §4.7）。

破壊的操作（削除・上書き）の前に対象を退避する。
退避先: <ルート>/_backup/<YYYYMMDD-HHMMSS>/<元のフォルダ名 or ファイル名>
最新 10 世代まで保持し、それ以前は古い順に自動削除。
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

BACKUP_DIR_NAME = '_backup'
MAX_GENERATIONS = 10

_TIMESTAMP_RE = re.compile(r'^\d{8}-\d{6}$')


def _timestamp() -> str:
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def backup_paths(
    root: Path,
    targets: list[Path],
    *,
    timestamp: str | None = None,
) -> Path | None:
    """`targets` を `<root>/_backup/<timestamp>/` 配下にコピーで退避し、
    退避先ディレクトリのパスを返す。`targets` が空・存在しない場合は None。

    呼び出し側は退避後に対象を削除・上書きする。
    """
    root = Path(root)
    existing = [Path(t) for t in targets if Path(t).exists()]
    if not existing:
        return None

    ts = timestamp or _timestamp()
    bdir = root / BACKUP_DIR_NAME / ts
    bdir.mkdir(parents=True, exist_ok=True)

    for src in existing:
        dst = bdir / src.name
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    rotate(root)
    return bdir


def rotate(root: Path, max_generations: int = MAX_GENERATIONS) -> list[Path]:
    """古い世代を削除して最新 `max_generations` 件だけ残す。削除した世代の一覧を返す。"""
    root = Path(root)
    base = root / BACKUP_DIR_NAME
    if not base.is_dir():
        return []

    generations = sorted(
        [p for p in base.iterdir() if p.is_dir() and _TIMESTAMP_RE.match(p.name)],
        key=lambda p: p.name,
    )
    if len(generations) <= max_generations:
        return []

    to_delete = generations[: len(generations) - max_generations]
    for g in to_delete:
        shutil.rmtree(g, ignore_errors=True)
    return to_delete


def list_generations(root: Path) -> list[Path]:
    """バックアップ世代を新しい順に返す。"""
    base = Path(root) / BACKUP_DIR_NAME
    if not base.is_dir():
        return []
    return sorted(
        [p for p in base.iterdir() if p.is_dir() and _TIMESTAMP_RE.match(p.name)],
        key=lambda p: p.name,
        reverse=True,
    )
