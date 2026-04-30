# -*- coding: utf-8 -*-
"""
証拠説明書メタデータ(metadata.json)の読み書きサービス。

ルートフォルダ配下の `証拠説明書/metadata.json` を扱う。
SPEC.md §10.4 の永続化方式に準拠。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict


logger = logging.getLogger(__name__)


METADATA_DIRNAME = "証拠説明書"
METADATA_FILENAME = "metadata.json"
ALLOWED_SOURCES = {"user", "ai_then_user"}
JST = timezone(timedelta(hours=9))


def _empty_metadata() -> Dict[str, Any]:
    return {"version": 1, "entries": {}}


def get_metadata_dir(root_folder: Path) -> Path:
    """ルートフォルダ配下の「証拠説明書」フォルダのパスを返す(作成はしない)。"""
    return Path(root_folder) / METADATA_DIRNAME


def load_metadata(root_folder: Path) -> Dict[str, Any]:
    """metadata.json を読み込んで dict として返す。

    ファイルが無い場合・JSON パースに失敗した場合・構造が不正な場合は
    `{"version": 1, "entries": {}}` を返す。既存ファイルは破壊しない。
    """
    path = get_metadata_dir(root_folder) / METADATA_FILENAME
    if not path.exists():
        return _empty_metadata()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("metadata.json の読込に失敗: %s (%s)", path, e)
        return _empty_metadata()

    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        logger.warning("metadata.json の構造が不正: %s", path)
        return _empty_metadata()
    return data


def save_metadata_entry(
    root_folder: Path, normalized_key: str, entry: Dict[str, Any]
) -> Dict[str, Any]:
    """1 行分のメタデータを metadata.json に保存する。

    `updated_at` は JST の現在時刻を ISO8601 形式で自動付与する。
    親フォルダ(「証拠説明書」)が無ければ作成する。
    `source` が許可値以外の場合は `ValueError` を送出する。
    """
    source = entry.get("source")
    if source not in ALLOWED_SOURCES:
        raise ValueError(
            f"source は {sorted(ALLOWED_SOURCES)} のいずれかである必要があります: {source!r}"
        )

    data = load_metadata(root_folder)
    if not isinstance(data.get("entries"), dict):
        data = _empty_metadata()
    data.setdefault("version", 1)

    new_entry: Dict[str, Any] = {
        "title": entry.get("title", ""),
        "created_date": entry.get("created_date", ""),
        "author": entry.get("author", ""),
        "purpose": entry.get("purpose", ""),
        "source": source,
        "updated_at": datetime.now(JST).isoformat(timespec="seconds"),
    }
    data["entries"][normalized_key] = new_entry

    metadata_dir = get_metadata_dir(root_folder)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    path = metadata_dir / METADATA_FILENAME
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("metadata.json を保存: %s (%s)", path, normalized_key)
    return new_entry
