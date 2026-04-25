"""REST API ルート定義（仕様書 v02 §7）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from ..core import folder_setup, list_builder
from ..core.backup import backup_paths
from ..core.case_parser import extract_labels_from_case_file
from ..core.combiner import auto_filename, combine_files, ensure_docx_extension
from ..core.normalizer import filename_to_label
from ..core.splitter import preview_split, split_combined_file
from ..core.table_builder import build_evidence_table_doc, merge_rows
from .schemas import (
    CaseBuildRequest,
    CaseLabelsResponse,
    CaseParseRequest,
    CombineRequest,
    CombineResponse,
    CombinedFileEntry,
    CombinedFilesRequest,
    CombinedFilesResponse,
    ExtractedItem,
    IgnoredLineSchema,
    ListAutoCreateRequest,
    ListAutoCreateResponse,
    ListOpenRequest,
    ListParseRequest,
    ListParseResponse,
    MasterClearRequest,
    MasterClearResponse,
    MasterListResponse,
    OkResponse,
    OpenBackupRequest,
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


def _rel_to_root(root_path: str, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(Path(root_path)))
    except ValueError:
        return str(path)


@router.post('/setup', response_model=SetupResponse)
def api_setup(req: SetupRequest) -> SetupResponse:
    try:
        result = folder_setup.setup_root_folder(req.root_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (NotADirectoryError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SetupResponse(ok=result.ok, messages=result.messages, summary=result.summary)


@router.post('/master/list', response_model=MasterListResponse)
def api_master_list(req: SetupRequest) -> MasterListResponse:
    master = folder_setup.get_master_dir(req.root_path)
    if not master.exists():
        return MasterListResponse(ok=True, is_empty=True, files=[], duplicates=[])

    files: List[dict] = []
    label_to_files: dict[str, list[str]] = {}
    for path in sorted(master.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.suffix.lower() != '.docx':
            continue
        if path.name.endswith('.bak.docx'):
            continue
        label = filename_to_label(path.name) or path.stem
        files.append(
            {'label': label, 'filename': path.name, 'size': path.stat().st_size}
        )
        label_to_files.setdefault(label, []).append(path.name)

    duplicates = [
        {'label': lbl, 'filenames': names}
        for lbl, names in label_to_files.items()
        if len(names) > 1
    ]
    return MasterListResponse(
        ok=True, is_empty=len(files) == 0, files=files, duplicates=duplicates
    )


@router.post('/master/clear', response_model=MasterClearResponse)
def api_master_clear(req: MasterClearRequest) -> MasterClearResponse:
    master = folder_setup.get_master_dir(req.root_path)
    if not master.exists():
        return MasterClearResponse(
            ok=True, message='個別マスタは存在しません。', removed_count=0,
            dry_run=req.dry_run,
        )
    targets = [
        p for p in master.iterdir()
        if p.is_file() and p.suffix.lower() == '.docx' and not p.name.endswith('.bak.docx')
    ]
    if req.dry_run:
        return MasterClearResponse(
            ok=True,
            dry_run=True,
            removed_count=len(targets),
            message=f'{len(targets)} 件のファイルを削除予定です。',
        )

    backup = backup_paths(req.root_path, [master]) if targets else None
    removed = 0
    for path in targets:
        try:
            path.unlink()
            removed += 1
        except PermissionError as e:
            raise HTTPException(
                status_code=409,
                detail=f'ファイルが他のアプリで開かれています: {path.name}（{e}）',
            )
    return MasterClearResponse(
        ok=True,
        removed_count=removed,
        backup_path=_rel_to_root(req.root_path, backup),
        message=f'{removed} 件のファイルを削除しました。',
    )


@router.post('/combined/list', response_model=CombinedFilesResponse)
def api_combined_list(req: CombinedFilesRequest) -> CombinedFilesResponse:
    files = folder_setup.list_combined_files_detailed(req.root_path)
    return CombinedFilesResponse(
        ok=True,
        files=[CombinedFileEntry(**f) for f in files],
    )


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

    if req.dry_run:
        try:
            preview = preview_split(combined_path)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        return SplitResponse(
            ok=True, dry_run=True, preview_labels=preview,
            message=f'{len(preview)} 件の甲号証が抽出される予定です。',
        )

    if has_existing and not req.force_overwrite:
        return SplitResponse(
            ok=True, needs_confirmation=True, extracted=[],
            message='個別マスタが空ではありません。force_overwrite=true で再実行してください。',
        )

    backup_generation = None
    if has_existing:
        backup_generation = backup_paths(req.root_path, [master])
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
        extracted=[ExtractedItem(label=e.label, filename=e.filename) for e in extracted],
        backup_path=_rel_to_root(req.root_path, backup_generation),
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


@router.post('/list/auto-create', response_model=ListAutoCreateResponse)
def api_list_auto_create(req: ListAutoCreateRequest) -> ListAutoCreateResponse:
    try:
        if req.source == 'master':
            labels = list_builder.labels_from_master(req.root_path)
            if req.dry_run:
                return ListAutoCreateResponse(
                    ok=True, count=len(labels), labels=labels, dry_run=True,
                )
            labels, backup = list_builder.auto_create_from_master(req.root_path)
            return ListAutoCreateResponse(
                ok=True, count=len(labels), labels=labels,
                backup_path=_rel_to_root(req.root_path, backup),
            )

        if not req.combined_file:
            raise HTTPException(
                status_code=400,
                detail='source=combined の場合は combined_file を指定してください。',
            )
        combined_path = folder_setup.get_combined_dir(req.root_path) / req.combined_file
        if not combined_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f'結合甲号証ファイルが見つかりません: {combined_path}',
            )
        if req.dry_run:
            labels = list_builder.labels_from_combined_file(combined_path)
            return ListAutoCreateResponse(
                ok=True, count=len(labels), labels=labels, dry_run=True,
            )
        labels, backup = list_builder.auto_create_from_combined(req.root_path, req.combined_file)
        return ListAutoCreateResponse(
            ok=True, count=len(labels), labels=labels,
            backup_path=_rel_to_root(req.root_path, backup),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post('/list/parse', response_model=ListParseResponse)
def api_list_parse(req: ListParseRequest) -> ListParseResponse:
    parsed = list_builder.parse_list_file(req.root_path)
    return ListParseResponse(
        ok=True,
        labels=parsed.labels,
        count=len(parsed.labels),
        ignored_lines=[IgnoredLineSchema(line=i.line, text=i.text) for i in parsed.ignored_lines],
    )


def _resolve_combine_output(root_path: str, output_filename: str | None, kind: str) -> Path:
    combined_dir = folder_setup.get_combined_dir(root_path)
    if output_filename and output_filename.strip():
        name = ensure_docx_extension(output_filename.strip())
    else:
        root_name = Path(root_path).name
        name = auto_filename(root_name, kind)
    return combined_dir / name


@router.post('/combine', response_model=CombineResponse)
def api_combine(req: CombineRequest) -> CombineResponse:
    parsed = list_builder.parse_list_file(req.root_path)
    labels = parsed.labels
    if not labels:
        raise HTTPException(
            status_code=400,
            detail='甲号証リストが空、または有効なラベルが含まれていません。',
        )

    master_dir = folder_setup.get_master_dir(req.root_path)
    output_path = _resolve_combine_output(req.root_path, req.output_filename, '結合')

    if req.dry_run:
        missing = [
            lbl for lbl in labels
            if not (master_dir / f'{lbl}.docx').exists()
        ]
        used = [lbl for lbl in labels if lbl not in missing]
        return CombineResponse(
            ok=True, dry_run=True,
            output_path=str(output_path), missing=missing, used=used,
            combined_count=len(used),
        )

    backup = None
    if output_path.exists():
        backup = backup_paths(req.root_path, [output_path])

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
        combined_count=len(result.used),
        backup_path=_rel_to_root(req.root_path, backup),
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
    missing = [lbl for lbl in labels if not (master_dir / f'{lbl}.docx').exists()]
    if missing and not req.force_continue and not req.dry_run:
        raise HTTPException(
            status_code=422,
            detail=f'対応する個別マスタが見つかりません: {", ".join(missing)}（force_continue=true で続行可）',
        )

    overrides = [row.model_dump() for row in req.table_data] if req.table_data else None
    rows = merge_rows(labels, master_dir, overrides=overrides)

    output_path = _resolve_combine_output(req.root_path, req.output_filename, '完成')
    if req.dry_run:
        return CombineResponse(
            ok=True, dry_run=True,
            output_path=str(output_path), missing=missing, used=[lbl for lbl in labels if lbl not in missing],
            combined_count=len(labels) - len(missing),
        )

    backup = None
    if output_path.exists():
        backup = backup_paths(req.root_path, [output_path])

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
        combined_count=len(result.used),
        backup_path=_rel_to_root(req.root_path, backup),
    )


@router.post('/backup/open', response_model=OkResponse)
def api_open_backup(req: OpenBackupRequest) -> OkResponse:
    backup_dir = folder_setup.get_backup_dir(req.root_path)
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == 'win32':
            os.startfile(str(backup_dir))  # type: ignore[attr-defined]
        elif sys.platform == 'darwin':
            os.system(f'open "{backup_dir}"')
        else:
            os.system(f'xdg-open "{backup_dir}"')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'_backup の起動に失敗しました: {e}')
    return OkResponse(ok=True)
