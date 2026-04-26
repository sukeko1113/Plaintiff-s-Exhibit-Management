# -*- coding: utf-8 -*-
"""
甲号証管理アプリ FastAPI エントリポイント。

提供エンドポイント:
- GET  /                : UI (タブ式: 結合 / 分解 / マスタ一覧)
- GET  /api/settings    : 保存済みルートフォルダ
- POST /api/settings    : ルートフォルダを保存
- POST /api/merge       : 結合
- POST /api/split       : 分解
- GET  /api/master      : 個別マスタ一覧
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.master_service import list_master
from app.merge_service import merge_kogo
from app.settings import AppSettings, load_settings, save_settings
from app.split_service import split_kogo


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="甲号証管理アプリ")

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Pydantic モデル
# ---------------------------------------------------------------------------

class RootFolderRequest(BaseModel):
    root_folder: str = Field(..., description="ルートフォルダの絶対パス")


class SettingsModel(BaseModel):
    root_folder: Optional[str] = None


class MergeResult(BaseModel):
    output_path: str
    merged_files: List[str]
    list_used: bool
    missing_in_master: List[str]
    warnings: List[str]


class SplitRequest(BaseModel):
    root_folder: str
    input_path: Optional[str] = None
    overwrite: bool = True


class SplitResult(BaseModel):
    output_dir: str
    created_files: List[str]
    overwritten_files: List[str]
    warnings: List[str]


class MasterEntryModel(BaseModel):
    filename: str
    normalized_marker: Optional[str]
    main: Optional[int]
    branch: Optional[int]
    size_bytes: int


class MasterListingModel(BaseModel):
    master_dir: str
    entries: List[MasterEntryModel]
    warnings: List[str]


# ---------------------------------------------------------------------------
# 共通ヘルパ
# ---------------------------------------------------------------------------

def _validate_root(root_folder: str) -> Path:
    root = Path(root_folder)
    if not root.exists():
        raise HTTPException(status_code=400, detail=f"ルートフォルダが存在しません: {root}")
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"ルートフォルダがディレクトリではありません: {root}")
    return root


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>甲号証管理アプリ</h1>")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

@app.get("/api/settings", response_model=SettingsModel)
def get_settings() -> SettingsModel:
    s = load_settings()
    return SettingsModel(root_folder=s.root_folder)


@app.post("/api/settings", response_model=SettingsModel)
def post_settings(req: SettingsModel) -> SettingsModel:
    save_settings(AppSettings(root_folder=req.root_folder))
    return req


# ---------------------------------------------------------------------------
# 結合
# ---------------------------------------------------------------------------

@app.post("/api/merge", response_model=MergeResult)
def merge_endpoint(req: RootFolderRequest) -> MergeResult:
    root = _validate_root(req.root_folder)
    outcome = merge_kogo(root)
    return MergeResult(
        output_path=str(outcome.output_path),
        merged_files=outcome.merged_files,
        list_used=outcome.list_used,
        missing_in_master=outcome.missing_in_master,
        warnings=outcome.warnings,
    )


# ---------------------------------------------------------------------------
# 分解
# ---------------------------------------------------------------------------

@app.post("/api/split", response_model=SplitResult)
def split_endpoint(req: SplitRequest) -> SplitResult:
    root = _validate_root(req.root_folder)
    input_path = Path(req.input_path) if req.input_path else None
    try:
        outcome = split_kogo(root, input_path=input_path, overwrite=req.overwrite)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SplitResult(
        output_dir=str(outcome.output_dir),
        created_files=outcome.created_files,
        overwritten_files=outcome.overwritten_files,
        warnings=outcome.warnings,
    )


# ---------------------------------------------------------------------------
# 個別マスタ一覧
# ---------------------------------------------------------------------------

@app.get("/api/master", response_model=MasterListingModel)
def master_endpoint(root_folder: str) -> MasterListingModel:
    root = _validate_root(root_folder)
    listing = list_master(root)
    return MasterListingModel(
        master_dir=str(listing.master_dir),
        entries=[MasterEntryModel(**e.__dict__) for e in listing.entries],
        warnings=listing.warnings,
    )
