# -*- coding: utf-8 -*-
"""
証拠説明書メタデータ関連の API ルーター。

SPEC.md §10.6.1 / §10.6.2 / §10.6.4 のエンドポイントを提供する。
- GET  /api/metadata               : metadata.json を返却
- PUT  /api/metadata/{key}         : 1 行分のメタデータを保存
- POST /api/master/open            : 個別マスタファイルを既定アプリで開く
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.merge_service import MASTER_DIRNAME
from app.metadata_service import load_metadata, save_metadata_entry


logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic モデル
# ---------------------------------------------------------------------------

class MetadataResponse(BaseModel):
    version: int
    entries: Dict[str, Any]


class MetadataEntryRequest(BaseModel):
    root_folder: str = Field(..., description="ルートフォルダの絶対パス")
    title: str = ""
    created_date: str = ""
    author: str = ""
    purpose: str = ""
    source: Literal["user", "ai_then_user"]


class MetadataEntryResponse(BaseModel):
    normalized_key: str
    title: str
    created_date: str
    author: str
    purpose: str
    source: str
    updated_at: str


class MasterOpenRequest(BaseModel):
    root_folder: str = Field(..., description="ルートフォルダの絶対パス")
    normalized_key: str = Field(..., description="正規化キー(例: 甲第００１号証)")


class MasterOpenResponse(BaseModel):
    opened: bool
    path: str


# ---------------------------------------------------------------------------
# 共通ヘルパ (循環 import を避けるため main.py の同等関数を再定義)
# ---------------------------------------------------------------------------

def _require_existing_root(root_folder: str) -> Path:
    root = Path(root_folder)
    if not root.exists():
        raise HTTPException(status_code=400, detail=f"ルートフォルダが存在しません: {root}")
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"ルートフォルダがディレクトリではありません: {root}")
    return root


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------

@router.get("/api/metadata", response_model=MetadataResponse)
def get_metadata(root_folder: str) -> MetadataResponse:
    root = _require_existing_root(root_folder)
    data = load_metadata(root)
    return MetadataResponse(
        version=int(data.get("version", 1)),
        entries=data.get("entries", {}),
    )


@router.put("/api/metadata/{normalized_key}", response_model=MetadataEntryResponse)
def put_metadata_entry(
    normalized_key: str, req: MetadataEntryRequest
) -> MetadataEntryResponse:
    root = _require_existing_root(req.root_folder)
    try:
        saved = save_metadata_entry(
            root,
            normalized_key,
            {
                "title": req.title,
                "created_date": req.created_date,
                "author": req.author,
                "purpose": req.purpose,
                "source": req.source,
            },
        )
    except ValueError as e:
        # source の Literal 検証は Pydantic が 422 で弾くため、ここに来るのは
        # 想定外のケース。念のため 422 を返す。
        raise HTTPException(status_code=422, detail=str(e))
    return MetadataEntryResponse(normalized_key=normalized_key, **saved)


@router.post("/api/master/open", response_model=MasterOpenResponse)
def post_master_open(req: MasterOpenRequest) -> MasterOpenResponse:
    root = _require_existing_root(req.root_folder)
    master_dir = root / MASTER_DIRNAME
    target = master_dir / f"{req.normalized_key}.docx"

    # パストラバーサル検証: 解決後のパスがルート配下に収まることを確認
    try:
        resolved_target = target.resolve()
        resolved_root = root.resolve()
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"パスの解決に失敗しました: {e}")

    if not resolved_target.is_relative_to(resolved_root):
        raise HTTPException(
            status_code=400,
            detail=f"normalized_key がルートフォルダ外を指しています: {req.normalized_key!r}",
        )

    if not resolved_target.exists():
        raise HTTPException(
            status_code=404,
            detail=f"個別マスタファイルが見つかりません: {resolved_target}",
        )

    path_str = str(resolved_target)
    try:
        if sys.platform.startswith("win"):
            os.startfile(path_str)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path_str], check=False)
        else:
            subprocess.run(["xdg-open", path_str], check=False)
    except Exception as e:  # pragma: no cover - OS 依存の実行系エラー
        raise HTTPException(status_code=500, detail=f"ファイルを開けませんでした: {e}")

    return MasterOpenResponse(opened=True, path=path_str)
