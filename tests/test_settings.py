# -*- coding: utf-8 -*-
"""
設定モジュールのテスト。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import settings as settings_mod
from app.settings import AppSettings, load_settings, save_settings, settings_path


@pytest.fixture
def settings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """環境変数で設定ファイルパスを上書き。"""
    p = tmp_path / "settings.json"
    monkeypatch.setenv("KOGO_KANRI_SETTINGS_PATH", str(p))
    return p


def test_settings_path_uses_env_override(settings_file: Path) -> None:
    assert settings_path() == settings_file


def test_load_returns_empty_when_missing(settings_file: Path) -> None:
    assert not settings_file.exists()
    s = load_settings()
    assert s.root_folder is None


def test_save_then_load_round_trip(settings_file: Path) -> None:
    save_settings(AppSettings(root_folder="C:/foo/bar"))
    loaded = load_settings()
    assert loaded.root_folder == "C:/foo/bar"


def test_load_handles_corrupt_file(settings_file: Path) -> None:
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text("not-json", encoding="utf-8")
    loaded = load_settings()
    # 壊れていてもクラッシュしない
    assert loaded.root_folder is None
