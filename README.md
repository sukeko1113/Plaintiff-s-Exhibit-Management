# 甲号証管理アプリ

訴訟用「甲号証（こうごうしょう）」を Word ファイル単位で管理し、結合・分解・一覧表作成を半自動化するローカル Web アプリです。

詳細仕様は [`SPEC.md`](./SPEC.md) を参照してください。

## 構成

```
├── backend/   # FastAPI + python-docx + docxcompose
└── frontend/  # React + Vite + Tailwind CSS
```

## 起動方法（Windows）

`start.bat` をダブルクリックします。以下が自動で行われます。

1. `backend\venv` を作成し、`requirements.txt` の依存をインストール
2. `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765` でバックエンド起動
3. `frontend` で `npm install`（初回）→ `npm run dev` でフロントエンド起動
4. 5 秒後に `http://localhost:5173` をブラウザで開く

## 手動起動

### バックエンド
```bash
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cd ..
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

### フロントエンド
```bash
cd frontend
npm install
npm run dev
```

## テスト

```bash
python -m pytest backend/tests/ -v
```

`backend/tests/generate_fixtures.py` を実行すると `backend/tests/fixtures/` 配下にサンプルファイルが生成されます。

```bash
python -m backend.tests.generate_fixtures
```

## 使用方法

1. ブラウザで開いたら、ルートフォルダを入力（例: `I:\マイドライブ\令和8年（ワ）第131号`）→「設定・構成確認」を押下
2. 必要なフォルダ／ファイルが自動で作成されます
   - `甲号証リスト.docx`
   - `個別マスタ\`
   - `結合甲号証\`
3. 既存の結合甲号証 → 個別マスタへの分解、または個別マスタ → 結合甲号証の作成、および案件ファイル基準での自動作成が可能です

## 主要 API

| メソッド | パス | 機能 |
| --- | --- | --- |
| POST | `/api/setup` | ルートフォルダ初期化 |
| POST | `/api/master/list` | 個別マスタの一覧取得 |
| POST | `/api/master/clear` | 個別マスタを空にする |
| POST | `/api/combined/list` | 結合甲号証フォルダ内のファイル一覧 |
| POST | `/api/split` | 結合 → 個別 分解 |
| POST | `/api/combine` | 個別 → 結合 |
| POST | `/api/list/open` | 甲号証リスト.docx を Word で開く |
| POST | `/api/list/auto-create` | 甲号証リストの自動作成（master / combined） |
| POST | `/api/list/parse` | 甲号証リスト.docx の内容取得 |
| POST | `/api/case/parse` | 案件ファイルから号証抽出 |
| POST | `/api/case/build-combined` | 案件ファイル基準で結合 + 証拠説明書テーブル |

詳細は起動後に `http://127.0.0.1:8765/docs` で確認できます。

## 動作環境

- Windows 10 / 11
- Python 3.10 以降
- Node.js 18 以降

## ライセンス

社内利用想定のためライセンスは設定していません。
