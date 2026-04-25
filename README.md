# 甲号証管理アプリ

訴訟用の甲号証（原告側証拠書類）を Word ファイル単位で管理し、結合・分解・一覧表作成を半自動化するローカル Web アプリ。

詳細仕様は `SPEC.md` を、実装進捗は `PROGRESS.md` を参照。

## 動作環境

- Windows 10/11
- Python 3.10+
- Node.js 18+

## 初回セットアップ

```cmd
cd backend
pip install -r requirements.txt
cd ..\frontend
npm install
```

## 起動

`start.bat` をダブルクリック（Windows）。

ブラウザが自動で `http://localhost:5173` を開く。バックエンドは `http://localhost:8765`。

## テスト

```cmd
python -m pytest backend/tests/ -v
```

## ポート

| 用途       | ポート |
| ---------- | ------ |
| バックエンド | 8765   |
| フロントエンド | 5173   |

ポート競合時は `backend/main.py` 起動コマンドの `--port` と `frontend/vite.config.js` の `server.port` を変更。

## ディレクトリ

```
koshou-kanri/
├── backend/      FastAPI + python-docx + docxcompose
├── frontend/     React + Vite + Tailwind CSS
├── SPEC.md       仕様書
└── PROGRESS.md   実装進捗
```
