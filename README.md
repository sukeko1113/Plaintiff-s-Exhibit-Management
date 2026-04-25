# 甲号証管理アプリ（v02）

訴訟用「甲号証（こうごうしょう）」を Word ファイル単位で管理し、結合・分解・一覧表作成を半自動化するローカル Web アプリです。

詳細仕様は [`SPEC.md`](./SPEC.md) を参照してください。

## v02 の主な変更点
- 分解ロジックを **`【甲第xxx号証】` マーカー優先**（フォールバックで括弧なし単独行）に変更
- 全破壊的 API に **dry-run** モードを追加
- **`_backup/YYYYMMDD-HHMMSS/` の世代管理**（最新 10 世代を自動保持）
- 結合甲号証ファイル名の自動生成、リスト初期コメント行、ヘッダ・フッタからの号証抽出など多数

## 構成
```
├── backend/   # FastAPI + python-docx + docxcompose
└── frontend/  # React + Vite + Tailwind CSS
```

## 起動方法（Windows）
`start.bat` をダブルクリックします。以下が自動で行われます。

1. `backend\venv` を作成し、`requirements.txt` の依存をインストール
2. プロジェクトルートで `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765`
3. `frontend` で `npm install`（初回）→ `npm run dev`
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

`backend/tests/generate_fixtures.py` を実行すると `backend/tests/fixtures/` 配下にサンプルファイル（bracketed / bare / case / list / master）が生成されます。
```bash
python -m backend.tests.generate_fixtures
```

## 使用方法
1. ブラウザでルートフォルダを入力（例: `I:\マイドライブ\令和8年（ワ）第131号`）→ **設定・構成確認**
2. 必要なフォルダ／ファイルが自動で作成されます
   - `甲号証リスト.docx`、`個別マスタ\`、`結合甲号証\`、`_backup\`
3. 既存の結合甲号証 → 個別マスタへの分解、または個別マスタ → 結合甲号証の作成、案件ファイル基準での自動作成が可能
4. 各操作の右にある **dry-run（試行モード）** チェックでファイルを変更せず予定だけ確認できます
5. 上書き時は `_backup/YYYYMMDD-HHMMSS/` に自動退避されます。手動復元は **_backup を開く** から

## 主要 API
| メソッド | パス | 機能 |
| --- | --- | --- |
| POST | `/api/setup` | ルートフォルダ初期化（サマリ付き） |
| POST | `/api/master/list` | 個別マスタ一覧（重複検出） |
| POST | `/api/master/clear` | 個別マスタを空にする（dry_run 対応） |
| POST | `/api/combined/list` | 結合甲号証ファイルの詳細一覧 |
| POST | `/api/split` | 結合 → 個別 分解（dry_run 対応） |
| POST | `/api/combine` | 個別 → 結合（自動ファイル名・dry_run 対応） |
| POST | `/api/list/open` | 甲号証リスト.docx を Word で開く |
| POST | `/api/list/auto-create` | 甲号証リストの自動作成（dry_run 対応） |
| POST | `/api/list/parse` | 甲号証リスト.docx の内容取得（無視行返却） |
| POST | `/api/case/parse` | 案件ファイルから号証抽出（ヘッダ・フッタ含む） |
| POST | `/api/case/build-combined` | 案件ベース結合 + 証拠説明書 |
| POST | `/api/backup/open` | `_backup` を Explorer で開く |

詳細は起動後 `http://127.0.0.1:8765/docs` で確認できます。

## 動作環境
- Windows 10 / 11
- Python 3.10 以降
- Node.js 18 以降

## ライセンス
社内利用想定のためライセンスは設定していません。
