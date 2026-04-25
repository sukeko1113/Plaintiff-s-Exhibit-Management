@echo off
chcp 65001 >nul
cd /d %~dp0
echo === 甲号証管理アプリ 起動中 ===

REM バックエンド起動（別ウィンドウ）
start "Backend" cmd /k "cd /d %~dp0backend && (if not exist venv python -m venv venv) && call venv\Scripts\activate && pip install -r requirements.txt -q && cd .. && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765"

REM フロントエンド起動（別ウィンドウ）
start "Frontend" cmd /k "cd /d %~dp0frontend && (if not exist node_modules npm install) && npm run dev"

REM 5秒待ってブラウザを開く
timeout /t 5 /nobreak >nul
start http://localhost:5173
