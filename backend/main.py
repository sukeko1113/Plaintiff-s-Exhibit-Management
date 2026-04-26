"""FastAPI エントリポイント。

推奨起動: python -m uvicorn backend.main:app --port 8765 --reload  (プロジェクトルートで実行)
互換起動: cd backend && python -m uvicorn main:app --port 8765 --reload
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router as api_router


app = FastAPI(title='甲号証管理アプリ', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router)


@app.get('/')
def root() -> dict:
    return {'app': '甲号証管理アプリ', 'version': '0.1.0'}
