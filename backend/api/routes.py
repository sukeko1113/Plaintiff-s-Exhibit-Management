"""REST API ルート定義（仕様書 §7）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from ..core import folder_setup, list_builder
from ..core.case_parser import extract_labels_from_case_file
from ..core.combiner import combine_files
from ..core.splitter import split_combined_file
from ..core.table_builder import build_evidence_table_doc, merge_rows
from .schemas import (
    CaseBuildRequest,
    CaseLabelsResponse,
    CaseParseRequest,
    CombineRequest,
    CombineResponse,
    CombinedFilesRequest,
    CombinedFilesResponse,
    ExtractedItem,
    LabelsResponse,
    ListAutoCreateRequest,
    ListOpenRequest,
    ListParseRequest,
    MasterClearRequest,
    MasterListResponse,
    OkResponse,
    SetupRequest,
    SetupResponse,
    SplitRequest,
    SplitResponse,
)

router = APIRouter(prefix='/api')


def _resolve_combined(root_path: str, name_or_path: str) -> Path:
    p = Path(name_or_path)
    if p.is_absolute() and p.exists():
        return p
    return folder_setup.get_combined_dir(root_path) / name_or_path


@router.post('/setup', response_model=SetupResponse)
def api_setup(req: SetupRequest) -> SetupResponse:
    try:
        result = folder_setup.setup_root_folder(req.root_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (NotADirectoryError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SetupResponse(ok=result.ok, messages=result.messages)


@router.post('/master/list', response_model=MasterListResponse)
def api_master_list(req: SetupRequest) -> MasterListResponse:
    master = folder_setup.get_master_dir(req.root_path)
    if not master.exists():
        return MasterListResponse(ok=True, is_empty=True, files=[])
    files: List[dict] = []
    for path in sorted(master.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.suffix.lower() != '.docx':
            continue
        if path.name.endswith('.bak.docx'):
            continue
        from ..core.normalizer import filename_to_label
        label = filename_to_label(path.name) or path.stem
        files.append({
            'label': label,
            'filename': path.name,
            'size': path.stat().st_size,
        })
    return MasterListResponse(ok=True, is_empty=len(files) == 0, files=files)


@router.post('/master/clear', response_model=OkResponse)
def api_master_clear(req: MasterClearRequest) -> OkResponse:
    master = folder_setup.get_master_dir(req.root_path)
    if not master.exists():
        return OkResponse(ok=True, message='個別マスタは存在しません。')
    removed = 0
    for path in master.iterdir():
        if path.is_file():
            try:
                path.unlink()
                removed += 1
            except PermissionError as e:
                raise HTTPException(
                    status_code=409,
                    detail=f'ファイルが他のアプリで開かれています: {path.name}（{e}）',
                )
    return OkResponse(ok=True, message=f'{removed} 件のファイルを削除しました。')


@router.post('/combined/list', response_model=CombinedFilesResponse)
def api_combined_list(req: CombinedFilesRequest) -> CombinedFilesResponse:
    files = folder_setup.list_combined_files(req.root_path)
    return CombinedFilesResponse(ok=True, files=files)


@router.post('/split', response_model=SplitResponse)
def api_split(req: SplitRequest) -> SplitResponse:
    combined_path = _resolve_combined(req.root_path, req.combined_file)
    if not combined_path.exists():
        raise HTTPException(status_code=404, detail=f'結合甲号証ファイルが見つかりません: {combined_path}')

    master = folder_setup.get_master_dir(req.root_path)
    master.mkdir(parents=True, exist_ok=True)
    has_existing = any(
        p.is_file() and p.suffix.lower() == '.docx' and not p.name.endswith('.bak.docx')
        for p in master.iterdir()
    )
    if has_existing and not req.force_overwrite:
        return SplitResponse(
            ok=True,
            needs_confirmation=True,
            extracted=[],
            message='個別マスタが空ではありません。確認後 force_overwrite=true で再実行してください。',
        )

    if has_existing:
        for p in master.iterdir():
            if p.is_file() and not p.name.endswith('.bak.docx'):
                try:
                    p.unlink()
                except PermissionError as e:
                    raise HTTPException(
                        status_code=409,
                        detail=f'ファイルが他のアプリで開かれています: {p.name}（{e}）',
                    )

    try:
        extracted = split_combined_file(combined_path, master)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=f'ファイルが他のアプリで開かれています: {e}')

    return SplitResponse(
        ok=True,
        needs_confirmation=False,
        extracted=[ExtractedItem(label=e.label, filename=e.filename) for e in extracted],
    )


@router.post('/list/open', response_model=OkResponse)
def api_list_open(req: ListOpenRequest) -> OkResponse:
    list_path = folder_setup.get_list_path(req.root_path)
    if not list_path.exists():
        raise HTTPException(status_code=404, detail=f'甲号証リスト.docx が見つかりません: {list_path}')
    try:
        if sys.platform == 'win32':
            os.startfile(str(list_path))  # type: ignore[attr-defined]
        elif sys.platform == 'darwin':
            os.system(f'open "{list_path}"')
        else:
            os.system(f'xdg-open "{list_path}"')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Word の起動に失敗しました: {e}')
    return OkResponse(ok=True)


@router.post('/list/auto-create', response_model=LabelsResponse)
def api_list_auto_create(req: ListAutoCreateRequest) -> LabelsResponse:
    try:
        if req.source == 'master':
            labels = list_builder.auto_create_from_master(req.root_path)
        else:
            if not req.combined_filename:
                raise HTTPException(
                    status_code=400,
                    detail='source=combined の場合は combined_filename を指定してください。',
                )
            labels = list_builder.auto_create_from_combined(req.root_path, req.combined_filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return LabelsResponse(ok=True, labels=labels, count=len(labels))


@router.post('/list/parse', response_model=LabelsResponse)
def api_list_parse(req: ListParseRequest) -> LabelsResponse:
    labels = list_builder.parse_list_file(req.root_path)
    return LabelsResponse(ok=True, labels=labels, count=len(labels))


@router.post('/combine', response_model=CombineResponse)
def api_combine(req: CombineRequest) -> CombineResponse:
    labels = list_builder.parse_list_file(req.root_path)
    if not labels:
        raise HTTPException(
            status_code=400,
            detail='甲号証リストが空、または有効なラベルが含まれていません。',
        )

    master_dir = folder_setup.get_master_dir(req.root_path)
    output_path = folder_setup.get_combined_dir(req.root_path) / req.output_filename
    folder_setup.backup_file(output_path)

    head_doc_path = None
    if req.include_evidence_table:
        rows = merge_rows(labels, master_dir, overrides=None)
        head_doc_path = output_path.parent / f'.{output_path.stem}_head.docx'
        build_evidence_table_doc(rows, head_doc_path)

    try:
        result = combine_files(master_dir, labels, output_path, head_doc=head_doc_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        if head_doc_path is not None and head_doc_path.exists():
            try:
                head_doc_path.unlink()
            except OSError:
                pass

    return CombineResponse(
        ok=True,
        output_path=str(result.output_path),
        missing=result.missing,
        used=result.used,
    )


@router.post('/case/parse', response_model=CaseLabelsResponse)
def api_case_parse(req: CaseParseRequest) -> CaseLabelsResponse:
    try:
        labels = extract_labels_from_case_file(req.case_file)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CaseLabelsResponse(ok=True, labels=labels)


@router.post('/case/build-combined', response_model=CombineResponse)
def api_case_build_combined(req: CaseBuildRequest) -> CombineResponse:
    try:
        labels = extract_labels_from_case_file(req.case_file)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not labels:
        raise HTTPException(status_code=422, detail='案件ファイルから甲号証ラベルを抽出できませんでした。')

    master_dir = folder_setup.get_master_dir(req.root_path)
    overrides = [row.model_dump() for row in req.table_data] if req.table_data else None
    rows = merge_rows(labels, master_dir, overrides=overrides)

    output_path = folder_setup.get_combined_dir(req.root_path) / req.output_filename
    folder_setup.backup_file(output_path)

    head_doc_path = output_path.parent / f'.{output_path.stem}_head.docx'
    build_evidence_table_doc(rows, head_doc_path)

    try:
        result = combine_files(master_dir, labels, output_path, head_doc=head_doc_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        if head_doc_path.exists():
            try:
                head_doc_path.unlink()
            except OSError:
                pass

    return CombineResponse(
        ok=True,
        output_path=str(result.output_path),
        missing=result.missing,
        used=result.used,
    )
