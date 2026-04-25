"""API リクエスト／レスポンスの Pydantic モデル。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    root_path: str


class SetupResponse(BaseModel):
    ok: bool
    messages: List[str]


class SplitRequest(BaseModel):
    root_path: str
    combined_file: str = Field(..., description='結合甲号証フォルダ内のファイル名 or 絶対パス')
    force_overwrite: bool = False


class ExtractedItem(BaseModel):
    label: str
    filename: str


class SplitResponse(BaseModel):
    ok: bool
    needs_confirmation: bool = False
    extracted: List[ExtractedItem] = []
    message: Optional[str] = None


class ListOpenRequest(BaseModel):
    root_path: str


class OkResponse(BaseModel):
    ok: bool
    message: Optional[str] = None


class ListAutoCreateRequest(BaseModel):
    root_path: str
    source: str = Field('master', pattern=r'^(master|combined)$')
    combined_filename: Optional[str] = None


class LabelsResponse(BaseModel):
    ok: bool
    labels: List[str]
    count: int


class ListParseRequest(BaseModel):
    root_path: str


class CombineRequest(BaseModel):
    root_path: str
    output_filename: str
    include_evidence_table: bool = False


class CombineResponse(BaseModel):
    ok: bool
    output_path: str
    missing: List[str]
    used: List[str]


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
    output_filename: str
    table_data: List[EvidenceTableRow] = []


class MasterListResponse(BaseModel):
    ok: bool
    is_empty: bool
    files: List[dict]


class MasterClearRequest(BaseModel):
    root_path: str


class CombinedFilesRequest(BaseModel):
    root_path: str


class CombinedFilesResponse(BaseModel):
    ok: bool
    files: List[str]
