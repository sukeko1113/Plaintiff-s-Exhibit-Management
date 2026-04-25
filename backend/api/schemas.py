"""API リクエスト／レスポンスの Pydantic モデル（v02）。"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    root_path: str


class SetupResponse(BaseModel):
    ok: bool
    messages: List[str]
    summary: Dict[str, int] = {}


class SplitRequest(BaseModel):
    root_path: str
    combined_file: str = Field(..., description='結合甲号証フォルダ内のファイル名 or 絶対パス')
    force_overwrite: bool = False
    dry_run: bool = False


class ExtractedItem(BaseModel):
    label: str
    filename: str


class SplitResponse(BaseModel):
    ok: bool
    needs_confirmation: bool = False
    dry_run: bool = False
    extracted: List[ExtractedItem] = []
    preview_labels: List[str] = []
    backup_path: Optional[str] = None
    message: Optional[str] = None


class ListOpenRequest(BaseModel):
    root_path: str


class OkResponse(BaseModel):
    ok: bool
    message: Optional[str] = None


class ListAutoCreateRequest(BaseModel):
    root_path: str
    source: str = Field('master', pattern=r'^(master|combined)$')
    combined_file: Optional[str] = None
    dry_run: bool = False


class IgnoredLineSchema(BaseModel):
    line: int
    text: str


class ListAutoCreateResponse(BaseModel):
    ok: bool
    count: int
    labels: List[str]
    backup_path: Optional[str] = None
    dry_run: bool = False


class ListParseRequest(BaseModel):
    root_path: str


class ListParseResponse(BaseModel):
    ok: bool
    labels: List[str]
    count: int
    ignored_lines: List[IgnoredLineSchema] = []


class CombineRequest(BaseModel):
    root_path: str
    output_filename: Optional[str] = None
    include_evidence_table: bool = False
    dry_run: bool = False


class CombineResponse(BaseModel):
    ok: bool
    output_path: str
    missing: List[str]
    used: List[str]
    combined_count: int = 0
    dry_run: bool = False
    backup_path: Optional[str] = None


class CaseParseRequest(BaseModel):
    case_file: str


class CaseLabelsResponse(BaseModel):
    ok: bool
    labels: List[str]


class EvidenceTableRow(BaseModel):
    label: str
    title: str = ''
    date: str = ''
    author: str = ''
    purpose: str = ''


class CaseBuildRequest(BaseModel):
    root_path: str
    case_file: str
    output_filename: Optional[str] = None
    table_data: List[EvidenceTableRow] = []
    dry_run: bool = False
    force_continue: bool = False


class MasterListResponse(BaseModel):
    ok: bool
    is_empty: bool
    files: List[dict]
    duplicates: List[dict] = []


class MasterClearRequest(BaseModel):
    root_path: str
    dry_run: bool = False


class MasterClearResponse(BaseModel):
    ok: bool
    message: Optional[str] = None
    removed_count: int = 0
    backup_path: Optional[str] = None
    dry_run: bool = False


class CombinedFilesRequest(BaseModel):
    root_path: str


class CombinedFileEntry(BaseModel):
    filename: str
    size: int
    modified_at: str


class CombinedFilesResponse(BaseModel):
    ok: bool
    files: List[CombinedFileEntry]


class OpenBackupRequest(BaseModel):
    root_path: str
