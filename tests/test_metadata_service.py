# -*- coding: utf-8 -*-
"""
metadata_service のテスト。

SPEC.md §10.4 / §10.8 に準拠した最低6ケースを検証する。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.metadata_service import (
    METADATA_DIRNAME,
    METADATA_FILENAME,
    get_metadata_dir,
    load_metadata,
    save_metadata_entry,
)


ISO8601_JST_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$"
)


def test_load_returns_empty_when_file_missing(root_folder: Path) -> None:
    """ファイル不在時は空構造を返し、ファイル/フォルダを作成しない。"""
    assert not get_metadata_dir(root_folder).exists()

    data = load_metadata(root_folder)

    assert data == {"version": 1, "entries": {}}
    # 副作用としてファイル・フォルダを作成しないこと
    assert not get_metadata_dir(root_folder).exists()


def test_load_reads_valid_metadata(root_folder: Path) -> None:
    """正常な metadata.json を読み込める。"""
    metadata_dir = root_folder / METADATA_DIRNAME
    metadata_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "entries": {
            "甲第００１号証": {
                "title": "保護者説明会配布資料",
                "created_date": "令和○年○月○日",
                "author": "被告(○○株式会社)",
                "purpose": "被告が安全基準の報告を怠っていた事実",
                "updated_at": "2026-04-30T12:34:56+09:00",
                "source": "ai_then_user",
            }
        },
    }
    (metadata_dir / METADATA_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    data = load_metadata(root_folder)

    assert data == payload


def test_load_returns_empty_on_corrupt_json_without_destroying_file(
    root_folder: Path,
) -> None:
    """不正な JSON ファイルがある時、空 dict を返し既存ファイルは破壊されない。"""
    metadata_dir = root_folder / METADATA_DIRNAME
    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = metadata_dir / METADATA_FILENAME
    corrupt_text = "{ this is not valid json"
    metadata_path.write_text(corrupt_text, encoding="utf-8")

    data = load_metadata(root_folder)

    assert data == {"version": 1, "entries": {}}
    # 既存ファイルが書き換えられていないこと
    assert metadata_path.read_text(encoding="utf-8") == corrupt_text


def test_save_adds_new_entry_and_creates_parent_folder(root_folder: Path) -> None:
    """新規エントリ追加。親フォルダが無ければ自動作成される。"""
    assert not get_metadata_dir(root_folder).exists()

    entry = {
        "title": "保護者説明会配布資料",
        "created_date": "令和○年○月○日",
        "author": "被告(○○株式会社)",
        "purpose": "被告が安全基準の報告を怠っていた事実",
        "source": "user",
    }
    saved = save_metadata_entry(root_folder, "甲第００１号証", entry)

    # 親フォルダおよびファイルが作成されていること
    metadata_path = get_metadata_dir(root_folder) / METADATA_FILENAME
    assert metadata_path.exists()

    # updated_at が ISO8601(JST)で自動付与されていること
    assert ISO8601_JST_RE.match(saved["updated_at"])
    assert saved["title"] == entry["title"]
    assert saved["source"] == "user"

    # ディスク上の内容も確認
    on_disk = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert on_disk["version"] == 1
    assert on_disk["entries"]["甲第００１号証"] == saved


def test_save_overwrites_existing_entry_and_keeps_others(root_folder: Path) -> None:
    """既存エントリの上書き。同じファイル内の他エントリは保持される。"""
    metadata_dir = root_folder / METADATA_DIRNAME
    metadata_dir.mkdir(parents=True, exist_ok=True)
    initial = {
        "version": 1,
        "entries": {
            "甲第００１号証": {
                "title": "古いタイトル",
                "created_date": "",
                "author": "",
                "purpose": "",
                "updated_at": "2026-01-01T00:00:00+09:00",
                "source": "user",
            },
            "甲第００２号証": {
                "title": "保持されるべきエントリ",
                "created_date": "",
                "author": "",
                "purpose": "",
                "updated_at": "2026-01-02T00:00:00+09:00",
                "source": "ai_then_user",
            },
        },
    }
    (metadata_dir / METADATA_FILENAME).write_text(
        json.dumps(initial, ensure_ascii=False), encoding="utf-8"
    )

    updated = save_metadata_entry(
        root_folder,
        "甲第００１号証",
        {
            "title": "新しいタイトル",
            "created_date": "令和○年○月○日",
            "author": "原告",
            "purpose": "新しい立証趣旨",
            "source": "ai_then_user",
        },
    )

    on_disk = json.loads(
        (metadata_dir / METADATA_FILENAME).read_text(encoding="utf-8")
    )
    # 上書きされたエントリ
    assert on_disk["entries"]["甲第００１号証"]["title"] == "新しいタイトル"
    assert on_disk["entries"]["甲第００１号証"]["source"] == "ai_then_user"
    assert on_disk["entries"]["甲第００１号証"] == updated
    # 他エントリは保持されている
    assert on_disk["entries"]["甲第００２号証"] == initial["entries"]["甲第００２号証"]


def test_save_rejects_invalid_source(root_folder: Path) -> None:
    """source が許可値以外の時、ValueError を送出する。"""
    entry = {
        "title": "",
        "created_date": "",
        "author": "",
        "purpose": "",
        "source": "robot",  # 許可値外
    }
    with pytest.raises(ValueError):
        save_metadata_entry(root_folder, "甲第００１号証", entry)

    # ファイル・フォルダが作成されていないこと(検証は保存より前に行われる)
    assert not get_metadata_dir(root_folder).exists()
