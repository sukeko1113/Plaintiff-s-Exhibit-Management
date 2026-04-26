# -*- coding: utf-8 -*-
"""
FastAPI エンドポイントのスモークテスト。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.merge_service import MASTER_DIRNAME, ensure_folders

from tests.conftest import make_kogo_docx


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # 設定ファイルを一時ディレクトリに隔離
    monkeypatch.setenv("KOGO_KANRI_SETTINGS_PATH", str(tmp_path / "settings.json"))
    return TestClient(app)


def test_index_returns_html(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "甲号証管理アプリ" in r.text


def test_settings_round_trip(client: TestClient, tmp_path: Path) -> None:
    target = str(tmp_path / "case")

    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["root_folder"] is None

    r = client.post("/api/settings", json={"root_folder": target})
    assert r.status_code == 200

    r = client.get("/api/settings")
    assert r.json()["root_folder"] == target


def test_merge_endpoint_validates_root(client: TestClient) -> None:
    r = client.post("/api/merge", json={"root_folder": "/no/such/path/zzz"})
    assert r.status_code == 400


def test_merge_endpoint_happy_path(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "case"
    ensure_folders(root)
    master = root / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")

    r = client.post("/api/merge", json={"root_folder": str(root)})
    assert r.status_code == 200
    d = r.json()
    assert d["list_used"] is False
    assert sorted(d["merged_files"]) == ["甲第００１号証.docx", "甲第００２号証.docx"]
    assert Path(d["output_path"]).exists()


def test_split_endpoint_happy_path(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "case"
    ensure_folders(root)
    master = root / MASTER_DIRNAME
    make_kogo_docx(master / "甲第００１号証.docx", "【甲第１号証】")
    make_kogo_docx(master / "甲第００２号証.docx", "【甲第２号証】")
    # 結合してから分解する
    r = client.post("/api/merge", json={"root_folder": str(root)})
    assert r.status_code == 200

    # 既存マスタを削除して、分解で再生成させる
    for f in master.glob("*.docx"):
        f.unlink()

    r = client.post("/api/split", json={"root_folder": str(root), "overwrite": True})
    assert r.status_code == 200
    d = r.json()
    assert sorted(d["created_files"]) == ["甲第００１号証.docx", "甲第００２号証.docx"]


def test_split_endpoint_missing_input_returns_400(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "case"
    ensure_folders(root)
    r = client.post("/api/split", json={"root_folder": str(root)})
    assert r.status_code == 400


def test_master_endpoint_returns_listing(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "case"
    ensure_folders(root)
    make_kogo_docx(root / MASTER_DIRNAME / "甲第００３号証.docx", "【甲第３号証】")
    make_kogo_docx(root / MASTER_DIRNAME / "甲第００１号証.docx", "【甲第１号証】")

    r = client.get("/api/master", params={"root_folder": str(root)})
    assert r.status_code == 200
    d = r.json()
    mains = [e["main"] for e in d["entries"]]
    assert mains == [1, 3]
