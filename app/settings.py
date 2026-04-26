# -*- coding: utf-8 -*-
"""
アプリ設定の保存・読み込み。

`%LOCALAPPDATA%/KogoKanri/settings.json` (Windows) または
`~/.kogo_kanri/settings.json` (それ以外) に保存する。
テスト時は環境変数 `KOGO_KANRI_SETTINGS_PATH` で上書き可能。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


@dataclass
class AppSettings:
    root_folder: Optional[str] = None


def settings_path() -> Path:
    """設定ファイルのパスを返す。環境変数による上書きをサポート。"""
    override = os.environ.get("KOGO_KANRI_SETTINGS_PATH")
    if override:
        return Path(override)

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "KogoKanri" / "settings.json"
    return Path.home() / ".kogo_kanri" / "settings.json"


def load_settings() -> AppSettings:
    path = settings_path()
    if not path.exists():
        return AppSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppSettings(root_folder=data.get("root_folder"))
    except Exception as e:
        logger.warning("設定ファイルの読込に失敗: %s (%s)", path, e)
        return AppSettings()


def save_settings(settings: AppSettings) -> Path:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("設定を保存しました: %s", path)
    return path
