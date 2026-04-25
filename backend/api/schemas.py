"""API リクエスト／レスポンス用 Pydantic スキーマ（仕様 §12）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    root_path: str = Field(..., description='ルートフォルダの絶対パス（Windows 形式可）')


class SetupResponse(BaseModel):
    root: str
    created: list[str]
    existed: list[str]


class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: str | None = None
