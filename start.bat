@echo off
setlocal
cd /d "%~dp0"

REM ---------- Python 検出 ----------
set "PYTHON_CMD="
where py >nul 2>&1 && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
  where python >nul 2>&1 && set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
  echo.
  echo [エラー] Python が PATH に見つかりません。
  echo  Python 3.10 以上をインストールし、インストール時に
  echo  「Add python.exe to PATH」にチェックを入れてください。
  echo  https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)
echo [情報] Python: %PYTHON_CMD%

REM ---------- 仮想環境作成 (初回のみ) ----------
if not exist ".venv\Scripts\python.exe" (
  echo [初回セットアップ] 仮想環境を作成しています...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo.
    echo [エラー] 仮想環境の作成に失敗しました。
    pause
    exit /b 1
  )
)

REM ---------- 依存パッケージのインストール ----------
echo [情報] 依存パッケージを確認しています...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo.
  echo [エラー] 依存パッケージのインストールに失敗しました。
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  甲号証管理システムを起動します
echo  ブラウザで http://127.0.0.1:8000/ を開いてください
echo  終了するには Ctrl+C を押してください
echo ============================================================
echo.

REM ---------- サーバー起動 ----------
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

REM ---------- サーバーが落ちたら原因確認のため一時停止 ----------
echo.
echo サーバーが終了しました (exit code = %errorlevel%).
pause

endlocal
