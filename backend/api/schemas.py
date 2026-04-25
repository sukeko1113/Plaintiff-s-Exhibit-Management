"""API リクエスト／レスポンス用 Pydantic スキーマ（仕様 §12）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---- /api/setup ----------------------------------------------------

class SetupRequest(BaseModel):
    root_path: str = Field(..., description='ルートフォルダの絶対パス（Windows 形式可）')


class SetupResponse(BaseModel):
    root: str
    created: list[str]
    existed: list[str]


# ---- /api/master/list, /api/combined/list --------------------------

class FileEntry(BaseModel):
    name: str
    path: str
    size: int


class FileListResponse(BaseModel):
    folder: str
    files: list[FileEntry]


# ---- /api/split ----------------------------------------------------

class SplitRequest(BaseModel):
    root_path: str
    combined_file: str = Field(..., description='ルートからの相対パス、または絶対パス')
    dry_run: bool = False
    overwrite: bool = False


class SplitResponse(BaseModel):
    produced_files: list[str] = []
    preview_files: list[str] = []
    existing_files_in_target: list[str] = []
    backup_path: str | None = None
    warning: str | None = None


# ---- /api/combine --------------------------------------------------

class CombineRequest(BaseModel):
    root_path: str
    output_filename: str | None = Field(
        default=None,
        description='省略時は 結合甲号証_<timestamp>.docx',
    )
    add_summary_table: bool = False
    metadata_map: dict[str, dict[str, str]] | None = None
    dry_run: bool = False


class CombineResponse(BaseModel):
    output_file: str | None = None
    preview_files: list[str] = []
    source_count: int


# ---- /api/list/* ---------------------------------------------------

class ListBuildResponse(BaseModel):
    list_path: str
    labels: list[str]
    backup_path: str | None = None


class ListBuildFromCombinedRequest(BaseModel):
    root_path: str
    combined_files: list[str]
    dry_run: bool = False


class ListBuildFromMasterRequest(BaseModel):
    root_path: str
    dry_run: bool = False


class ListOpenRequest(BaseModel):
    root_path: str


class ListOpenResponse(BaseModel):
    list_path: str
    opened: bool


# ---- /api/case/parse -----------------------------------------------

class CaseParseRequest(BaseModel):
    case_file: str = Field(..., description='案件 .docx の絶対パス')


class CaseParseResponse(BaseModel):
    case_file: str
    labels: list[str]


# ---- /api/evidence-pack -------------------------------------------

class EvidencePackRequest(BaseModel):
    root_path: str
    case_file: str
    add_summary_table: bool = True
    metadata_map: dict[str, dict[str, str]] | None = None
    dry_run: bool = False


class EvidencePackResponse(BaseModel):
    output_file: str | None = None
    used_labels: list[str] = []
    missing_labels: list[str] = []


# ---- /api/master/table ---------------------------------------------

class MasterTableResponse(BaseModel):
    rows: list[dict[str, Any]]


# ---- 共通 ----------------------------------------------------------

class ErrorPayload(BaseModel):
    error: str
    message: str
    detail: str | None = None
