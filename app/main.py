# -*- coding: utf-8 -*-
"""
甲号証管理アプリ FastAPI エントリポイント。

提供エンドポイント:
- GET  /                : UI (シングルページ)
- GET  /api/settings    : 保存済みルートフォルダ
- POST /api/settings    : ルートフォルダを保存
- POST /api/setup       : ルートを保存 + フォルダ構成を確認/生成
- POST /api/merge       : 結合
- POST /api/split       : 分解
- GET  /api/master      : 個別マスタ一覧
- GET  /api/metadata           : 証拠説明書 metadata.json を返却 (routers/metadata_router.py)
- PUT  /api/metadata/{key}     : 1 行分のメタデータを保存 (同上)
- POST /api/master/open        : 個別マスタファイルを既定アプリで開く (同上)
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from pathlib import Path
from typing import Any, Iterator, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.master_service import list_master
from app.merge_service import (
    DEPRECATED_LIST_FILENAME,
    MASTER_DIRNAME,
    OUTPUT_DIRNAME,
    InvalidMasterFilesError,
    ensure_folders,
    merge_kogo,
)
from app.routers import metadata_router
from app.settings import AppSettings, load_settings, save_settings
from app.split_service import split_kogo


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="甲号証管理システム")

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(metadata_router.router)


# ---------------------------------------------------------------------------
# Pydantic モデル
# ---------------------------------------------------------------------------

class RootFolderRequest(BaseModel):
    root_folder: str = Field(..., description="ルートフォルダの絶対パス")


class SettingsModel(BaseModel):
    root_folder: Optional[str] = None


class SetupResult(BaseModel):
    root_folder: str
    messages: List[str]


class MergeResult(BaseModel):
    output_path: str
    merged_files: List[str]
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
    normalized_key: Optional[str]
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

def _require_existing_root(root_folder: str) -> Path:
    """既存ルートを必須とする (merge/split/master 用)。"""
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
        return HTMLResponse("<h1>甲号証管理システム</h1>")
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
# フォルダ構成確認 (ルートを保存 + 必要なフォルダを生成)
# ---------------------------------------------------------------------------

@app.post("/api/setup", response_model=SetupResult)
def setup_endpoint(req: RootFolderRequest) -> SetupResult:
    root = Path(req.root_folder).expanduser()

    master_dir = root / MASTER_DIRNAME
    output_dir = root / OUTPUT_DIRNAME
    deprecated_list_path = root / DEPRECATED_LIST_FILENAME

    master_existed = master_dir.exists()
    output_existed = output_dir.exists()
    deprecated_list_existed = deprecated_list_path.exists()

    try:
        ensure_folders(root)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"フォルダの作成に失敗しました: {e}")

    save_settings(AppSettings(root_folder=str(root)))

    messages: List[str] = [
        f"ルートフォルダを設定しました: {root}",
        "「個別マスタ」フォルダを" + ("確認しました。" if master_existed else "新規作成しました。"),
        "「結合甲号証」フォルダを" + ("確認しました。" if output_existed else "新規作成しました。"),
    ]
    if deprecated_list_existed:
        messages.append(
            "「甲号証リスト.docx」は廃止されました。必要に応じて手動で削除してください。"
        )

    return SetupResult(root_folder=str(root), messages=messages)


# ---------------------------------------------------------------------------
# 結合 (Server-Sent Events で進捗通知)
# ---------------------------------------------------------------------------

def _sse_format(event_type: str, data: dict) -> str:
    """1 件の SSE イベントを `event:` + `data:` の形式に整形する。"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _run_merge_with_progress(
    root: Path, q: "queue.Queue[Optional[tuple]]"
) -> None:
    """別スレッドで merge を実行し、進捗・完了・エラーをキューに流す。"""
    def push_progress(message: str) -> None:
        q.put(("progress", {"message": message}))

    try:
        outcome = merge_kogo(root, on_progress=push_progress)
        q.put(
            (
                "done",
                {
                    "output_path": str(outcome.output_path),
                    "merged_files": outcome.merged_files,
                    "warnings": outcome.warnings,
                },
            )
        )
    except InvalidMasterFilesError as e:
        q.put(
            (
                "invalid",
                {
                    "error": "InvalidMasterFiles",
                    "message": "個別マスタに規約外のファイルがあるため、結合を中止しました",
                    "issues": [
                        {
                            "filename": i.filename,
                            "reason": i.reason,
                            "suggested_rename": i.suggested_rename,
                        }
                        for i in e.issues
                    ],
                },
            )
        )
    except Exception as e:  # pragma: no cover - 想定外
        q.put(("error", {"message": f"結合中にエラーが発生しました: {e}"}))
    finally:
        q.put(None)  # ストリーム終了マーカー


@app.post("/api/merge")
def merge_endpoint(req: RootFolderRequest) -> Any:
    """
    Server-Sent Events で進捗を返却する。

    イベント種別:
    - `progress`: 進捗メッセージ (`{"message": "..."}`)
    - `done`: 正常終了 (`MergeResult` 相当)
    - `invalid`: 規約外ファイル検出 (`{error, message, issues[]}`)
    - `error`: 想定外エラー
    """
    root = _require_existing_root(req.root_folder)

    q: "queue.Queue[Optional[tuple]]" = queue.Queue()
    thread = threading.Thread(
        target=_run_merge_with_progress, args=(root, q), daemon=True
    )
    thread.start()

    def event_stream() -> Iterator[str]:
        while True:
            item = q.get()
            if item is None:
                break
            event_type, data = item
            yield _sse_format(event_type, data)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# 分解
# ---------------------------------------------------------------------------

@app.post("/api/split", response_model=SplitResult)
def split_endpoint(req: SplitRequest) -> SplitResult:
    root = _require_existing_root(req.root_folder)
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
    root = _require_existing_root(root_folder)
    listing = list_master(root)
    return MasterListingModel(
        master_dir=str(listing.master_dir),
        entries=[MasterEntryModel(**e.__dict__) for e in listing.entries],
        warnings=listing.warnings,
    )
