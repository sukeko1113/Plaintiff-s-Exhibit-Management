"""API ルート定義（仕様 §12）。"""

from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.api.schemas import (
    CaseParseRequest,
    CaseParseResponse,
    CombineRequest,
    CombineResponse,
    EvidencePackRequest,
    EvidencePackResponse,
    FileEntry,
    FileListResponse,
    ListBuildFromCombinedRequest,
    ListBuildFromMasterRequest,
    ListBuildResponse,
    ListOpenRequest,
    ListOpenResponse,
    MasterTableResponse,
    SetupRequest,
    SetupResponse,
    SplitRequest,
    SplitResponse,
)
from backend.core import (
    backup,
    case_parser,
    combiner,
    folder_setup,
    list_builder,
    splitter,
    table_builder,
)


router = APIRouter(prefix='/api')

MASTER_FOLDER = '個別マスタ'
COMBINED_FOLDER = '結合甲号証'
LIST_FILENAME = '甲号証リスト.docx'


# -------------------------------------------------------------------
# 共通ヘルパ
# -------------------------------------------------------------------

def _root(root_path: str) -> Path:
    p = folder_setup.normalize_root_path(root_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail={
            'error': 'FileNotFoundError',
            'message': 'ルートフォルダが存在しません',
            'detail': str(p),
        })
    if not p.is_dir():
        raise HTTPException(status_code=400, detail={
            'error': 'NotADirectoryError',
            'message': 'ディレクトリではありません',
            'detail': str(p),
        })
    return p


def _resolve_under_root(root: Path, candidate: str) -> Path:
    """ユーザ指定の相対 or 絶対パスを Path に解決する。

    candidate が絶対パスならそのまま、相対なら root を起点に解決。
    """
    p = Path(candidate)
    if not p.is_absolute():
        p = root / p
    return p


def _list_docx_files(folder: Path) -> list[FileEntry]:
    if not folder.is_dir():
        return []
    entries: list[FileEntry] = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() != '.docx':
            continue
        if f.name.startswith('~$'):
            continue
        entries.append(FileEntry(
            name=f.name,
            path=str(f),
            size=f.stat().st_size,
        ))
    return entries


def _open_with_default_app(path: Path) -> bool:
    """OS 既定アプリでファイルを開く。失敗時 False。"""
    try:
        if platform.system() == 'Windows':
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif platform.system() == 'Darwin':
            subprocess.Popen(['open', str(path)])
        else:
            subprocess.Popen(['xdg-open', str(path)])
        return True
    except OSError:
        return False


# -------------------------------------------------------------------
# /api/setup
# -------------------------------------------------------------------

@router.post('/setup', response_model=SetupResponse)
def api_setup(req: SetupRequest) -> SetupResponse:
    try:
        root = folder_setup.normalize_root_path(req.root_path)
        result = folder_setup.setup_root(root)
        return SetupResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail={
            'error': 'FileNotFoundError', 'message': str(e), 'detail': req.root_path,
        })
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail={
            'error': 'NotADirectoryError', 'message': str(e), 'detail': req.root_path,
        })


# -------------------------------------------------------------------
# /api/master/list, /api/combined/list
# -------------------------------------------------------------------

@router.get('/master/list', response_model=FileListResponse)
def api_master_list(root_path: str) -> FileListResponse:
    root = _root(root_path)
    folder = root / MASTER_FOLDER
    return FileListResponse(folder=str(folder), files=_list_docx_files(folder))


@router.get('/combined/list', response_model=FileListResponse)
def api_combined_list(root_path: str) -> FileListResponse:
    root = _root(root_path)
    folder = root / COMBINED_FOLDER
    return FileListResponse(folder=str(folder), files=_list_docx_files(folder))


# -------------------------------------------------------------------
# /api/split
# -------------------------------------------------------------------

@router.post('/split', response_model=SplitResponse)
def api_split(req: SplitRequest) -> SplitResponse:
    root = _root(req.root_path)
    src = _resolve_under_root(root, req.combined_file)
    if not src.is_file():
        raise HTTPException(status_code=404, detail={
            'error': 'FileNotFoundError',
            'message': '結合甲号証ファイルが見つかりません',
            'detail': str(src),
        })

    master_dir = root / MASTER_FOLDER
    master_dir.mkdir(exist_ok=True)

    if req.dry_run:
        preview = splitter.split_combined_to_master(src, master_dir, dry_run=True)
        existing = [p.name for p in master_dir.glob('*.docx')]
        warning = '個別マスタが空ではありません' if existing else None
        return SplitResponse(
            preview_files=[p.name for p in preview],
            existing_files_in_target=existing,
            warning=warning,
        )

    backup_path = None
    existing = [p for p in master_dir.glob('*.docx')]
    if existing and req.overwrite:
        bdir = backup.backup_paths(root, [master_dir])
        backup_path = str(bdir) if bdir else None
        for p in existing:
            p.unlink()

    try:
        produced = splitter.split_combined_to_master(
            src, master_dir, overwrite=req.overwrite,
        )
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail={
            'error': 'FileExistsError',
            'message': str(e),
            'detail': str(master_dir),
        })

    return SplitResponse(
        produced_files=[p.name for p in produced],
        backup_path=backup_path,
    )


# -------------------------------------------------------------------
# /api/combine
# -------------------------------------------------------------------

@router.post('/combine', response_model=CombineResponse)
def api_combine(req: CombineRequest) -> CombineResponse:
    root = _root(req.root_path)
    master_dir = root / MASTER_FOLDER
    if not master_dir.is_dir():
        raise HTTPException(status_code=404, detail={
            'error': 'FileNotFoundError',
            'message': '個別マスタフォルダがありません',
            'detail': str(master_dir),
        })

    files = sorted(master_dir.glob('*.docx'))
    files = [f for f in files if not f.name.startswith('~$')]
    if not files:
        raise HTTPException(status_code=400, detail={
            'error': 'EmptyMaster',
            'message': '個別マスタに結合対象がありません',
            'detail': str(master_dir),
        })

    if req.dry_run:
        return CombineResponse(
            preview_files=[f.name for f in files],
            source_count=len(files),
        )

    out_dir = root / COMBINED_FOLDER
    out_dir.mkdir(exist_ok=True)
    name = req.output_filename or f'結合甲号証_{datetime.now().strftime("%Y%m%d-%H%M%S")}.docx'
    out_path = out_dir / name

    combiner.combine_to_evidence_pack(
        files, out_path,
        add_summary_table=req.add_summary_table,
        metadata_map=req.metadata_map,
    )
    return CombineResponse(
        output_file=str(out_path),
        source_count=len(files),
    )


# -------------------------------------------------------------------
# /api/list/*
# -------------------------------------------------------------------

@router.post('/list/from-master', response_model=ListBuildResponse)
def api_list_from_master(req: ListBuildFromMasterRequest) -> ListBuildResponse:
    root = _root(req.root_path)
    master_dir = root / MASTER_FOLDER
    list_path = root / LIST_FILENAME
    labels = list_builder.build_from_master(master_dir)

    if req.dry_run:
        return ListBuildResponse(list_path=str(list_path), labels=labels)

    backup_path = None
    if list_path.exists():
        bdir = backup.backup_paths(root, [list_path])
        backup_path = str(bdir) if bdir else None

    list_builder.write_list(list_path, labels)
    return ListBuildResponse(
        list_path=str(list_path),
        labels=labels,
        backup_path=backup_path,
    )


@router.post('/list/from-combined', response_model=ListBuildResponse)
def api_list_from_combined(req: ListBuildFromCombinedRequest) -> ListBuildResponse:
    root = _root(req.root_path)
    combined_paths = [_resolve_under_root(root, c) for c in req.combined_files]
    for p in combined_paths:
        if not p.is_file():
            raise HTTPException(status_code=404, detail={
                'error': 'FileNotFoundError',
                'message': '結合甲号証ファイルが見つかりません',
                'detail': str(p),
            })

    list_path = root / LIST_FILENAME
    labels = list_builder.build_from_combined(combined_paths)

    if req.dry_run:
        return ListBuildResponse(list_path=str(list_path), labels=labels)

    backup_path = None
    if list_path.exists():
        bdir = backup.backup_paths(root, [list_path])
        backup_path = str(bdir) if bdir else None

    list_builder.write_list(list_path, labels)
    return ListBuildResponse(
        list_path=str(list_path),
        labels=labels,
        backup_path=backup_path,
    )


@router.post('/list/open', response_model=ListOpenResponse)
def api_list_open(req: ListOpenRequest) -> ListOpenResponse:
    root = _root(req.root_path)
    list_path = root / LIST_FILENAME
    if not list_path.exists():
        # 空ファイルを作ってから開く
        from docx import Document
        Document().save(str(list_path))
    opened = _open_with_default_app(list_path)
    return ListOpenResponse(list_path=str(list_path), opened=opened)


# -------------------------------------------------------------------
# /api/case/parse
# -------------------------------------------------------------------

@router.post('/case/parse', response_model=CaseParseResponse)
def api_case_parse(req: CaseParseRequest) -> CaseParseResponse:
    p = Path(req.case_file)
    if not p.is_file():
        raise HTTPException(status_code=404, detail={
            'error': 'FileNotFoundError',
            'message': '案件ファイルが見つかりません',
            'detail': str(p),
        })
    labels = case_parser.extract_koshou_from_case(p)
    return CaseParseResponse(case_file=str(p), labels=labels)


# -------------------------------------------------------------------
# /api/evidence-pack
# -------------------------------------------------------------------

@router.post('/evidence-pack', response_model=EvidencePackResponse)
def api_evidence_pack(req: EvidencePackRequest) -> EvidencePackResponse:
    root = _root(req.root_path)
    case = Path(req.case_file)
    if not case.is_file():
        raise HTTPException(status_code=404, detail={
            'error': 'FileNotFoundError',
            'message': '案件ファイルが見つかりません',
            'detail': str(case),
        })
    master_dir = root / MASTER_FOLDER
    if not master_dir.is_dir():
        raise HTTPException(status_code=404, detail={
            'error': 'FileNotFoundError',
            'message': '個別マスタフォルダがありません',
            'detail': str(master_dir),
        })

    used_labels = case_parser.extract_koshou_from_case(case)
    available = {p.stem: p for p in master_dir.glob('*.docx')}
    files: list[Path] = []
    missing: list[str] = []
    for label in used_labels:
        f = available.get(label)
        if f is None:
            missing.append(label)
        else:
            files.append(f)

    if req.dry_run:
        return EvidencePackResponse(
            used_labels=used_labels,
            missing_labels=missing,
        )

    if not files:
        raise HTTPException(status_code=400, detail={
            'error': 'NoMatchingFiles',
            'message': '案件ファイルに対応する個別マスタが見つかりません',
            'detail': f'案件ラベル: {used_labels}, 不足: {missing}',
        })

    out_dir = root / COMBINED_FOLDER
    out_dir.mkdir(exist_ok=True)
    name = f'結合甲号証_{datetime.now().strftime("%Y%m%d-%H%M%S")}.docx'
    out_path = out_dir / name

    combiner.combine_to_evidence_pack(
        files, out_path,
        add_summary_table=req.add_summary_table,
        metadata_map=req.metadata_map,
    )
    return EvidencePackResponse(
        output_file=str(out_path),
        used_labels=used_labels,
        missing_labels=missing,
    )


# -------------------------------------------------------------------
# /api/master/table
# -------------------------------------------------------------------

@router.get('/master/table', response_model=MasterTableResponse)
def api_master_table(root_path: str) -> MasterTableResponse:
    root = _root(root_path)
    master_dir = root / MASTER_FOLDER
    if not master_dir.is_dir():
        return MasterTableResponse(rows=[])
    files = sorted(master_dir.glob('*.docx'))
    files = [f for f in files if not f.name.startswith('~$')]
    rows = table_builder.preview_metadata(files)
    return MasterTableResponse(rows=rows)
