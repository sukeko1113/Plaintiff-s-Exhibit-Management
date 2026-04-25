"""FastAPI エントリポイント。

起動: cd backend && python -m uvicorn main:app --port 8765 --reload
"""

from __future__ import annotations

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
