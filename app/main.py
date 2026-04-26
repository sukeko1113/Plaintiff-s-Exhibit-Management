# -*- coding: utf-8 -*-
"""
甲号証管理アプリ FastAPI エントリポイント。

本タスクのスコープは「結合機能」のみ。他のエンドポイント（分割・個別マスタ
管理・甲号証リスト作成 UI 等）はここでは追加しない。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.merge_service import merge_kogo


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="甲号証管理アプリ - 結合機能")

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class MergeRequest(BaseModel):
    root_folder: str = Field(..., description="ルートフォルダの絶対パス")


class MergeResult(BaseModel):
    output_path: str
    merged_files: List[str]
    list_used: bool
    missing_in_master: List[str]
    warnings: List[str]


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>甲号証管理アプリ</h1>")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.post("/merge", response_model=MergeResult)
def merge_kogo_endpoint(req: MergeRequest) -> MergeResult:
    """
    甲号証を結合する。

    - `root_folder` 直下の `甲号証リスト.docx` を読み、対象を絞る
    - リストが空 / 不在なら `個別マスタ` 内の全 docx を結合
    """
    root = Path(req.root_folder)
    if not root.exists():
        raise HTTPException(status_code=400, detail=f"ルートフォルダが存在しません: {root}")
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"ルートフォルダがディレクトリではありません: {root}")

    outcome = merge_kogo(root)
    return MergeResult(
        output_path=str(outcome.output_path),
        merged_files=outcome.merged_files,
        list_used=outcome.list_used,
        missing_in_master=outcome.missing_in_master,
        warnings=outcome.warnings,
    )
