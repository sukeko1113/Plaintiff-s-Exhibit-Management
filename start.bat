@echo off
chcp 65001 > nul
echo ===================================================
echo  甲号証管理アプリを起動します
echo ===================================================
echo  Backend  : http://localhost:8765
echo  Frontend : http://localhost:5173
echo ===================================================

cd /d "%~dp0"

start "Koshou Backend" cmd /k "cd backend && python -m uvicorn main:app --port 8765 --reload"
start "Koshou Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 3 > nul
start http://localhost:5173

echo.
echo  起動しました。終了するには各ターミナルで Ctrl+C を押してください。
