# 甲号証管理システム (Plaintiff's Exhibit Management)

民事訴訟における原告側の甲号証(書証)を、Word ファイル(`.docx`)ベースで効率的に管理するためのローカル Web アプリケーションです。
弁護士・パラリーガル等の実務担当者が、ローカル PC 上の訴訟記録フォルダを起点に、個別マスタの結合・結合済みファイルの分解までをワンストップで行えることを目的としています。

ブラウザ UI から操作しますが、サーバはローカルホスト(`127.0.0.1`)のみで起動するため、データは PC 外に出ません。

---

## 主な機能

`app/main.py` で定義されている API を起点に、以下の機能を提供します。

- **ルートフォルダ設定**
  - 訴訟ごとのルートフォルダ(絶対パス)を保存・読み出し (`GET/POST /api/settings`)
- **フォルダ構成の自動セットアップ**
  - ルート直下に「個別マスタ」フォルダ「結合甲号証」フォルダが無ければ自動生成 (`POST /api/setup`)
- **結合(マージ)**
  - 「個別マスタ」フォルダ内の各甲号証 `.docx` を正規化ファイル名の辞書順で `docxcompose` を用いて 1 つの Word ファイルに結合 (`POST /api/merge`)
  - 個別マスタに規約外のファイルがある場合は事前バリデーションで弾き、HTTP 409 を返してユーザーにファイル名の修正を促す
- **分解(スプリット)**
  - 結合済みの甲号証 `.docx` を、甲号証番号(甲第◯号証/甲◯)単位で個別ファイルに分解 (`POST /api/split`)
  - 上書き挙動はリクエストで指定可能
- **個別マスタ一覧**
  - 「個別マスタ」フォルダ内の `.docx` を一覧化し、甲号証番号(本枝番号)を正規化して返却 (`GET /api/master`)
- **シングルページ UI**
  - `app/static/index.html` から成る 1 画面 UI を `GET /` で配信

> **【廃止のお知らせ】** 以前のバージョンで生成していた「甲号証リスト.docx」と、それを使った結合順序定義機能・リスト編集機能 (`POST /api/open-list`) は廃止されました。結合順序は個別マスタのファイル名(辞書順)で決まります。既存ルートに「甲号証リスト.docx」が残っている場合、アプリ側からは一切触りませんので、必要に応じて手動で削除してください(`POST /api/setup` 実行時に廃止案内を返します)。

> 詳細仕様は `SPEC.md`(リポジトリに存在する場合)を参照してください。

---

## 技術スタック

### バックエンド (Python)
- [FastAPI](https://fastapi.tiangolo.com/) — Web フレームワーク
- [uvicorn](https://www.uvicorn.org/) — ASGI サーバ
- [python-docx](https://python-docx.readthedocs.io/) — Word (`.docx`) の読み書き
- [docxcompose](https://pypi.org/project/docxcompose/) — `.docx` の結合
- [pydantic](https://docs.pydantic.dev/) — リクエスト/レスポンスのスキーマ
- [pytest](https://docs.pytest.org/) — テスト

### フロントエンド
- 単一の HTML ファイル(`app/static/index.html`、Tailwind CDN + Lucide アイコン)

### 出力形式
- Markdown / Word (`.docx`)

依存関係は `requirements.txt` に集約されています。

---

## 必要な環境

- **OS**: Windows 10 / 11 を主対象としています
  - 同梱の `start.bat` は Windows 用バッチファイルです
  - macOS / Linux でも起動自体は可能
- **Python**: 3.10 以上を推奨
  - `start.bat` は `py -3` または `python` を自動検出します
  - インストール時は **「Add python.exe to PATH」** を必ず有効にしてください
- **ブラウザ**: 最新の Chrome / Edge / Firefox など
- **ディスク**: 仮想環境(`.venv`)と依存パッケージのため数百 MB 程度の空き容量

---

## 起動手順

### Windows (推奨: `start.bat`)

1. 本リポジトリを任意のフォルダに配置します。
2. エクスプローラーで `start.bat` をダブルクリックします。
3. 初回起動時、`start.bat` が以下を自動で実行します。
   - Python の検出(`py -3` → `python` の順)
   - 仮想環境 `.venv` の作成
   - `requirements.txt` に基づく依存パッケージのインストール
   - `uvicorn` によるサーバ起動(`http://127.0.0.1:8000/`)
4. ブラウザで `http://127.0.0.1:8000/` を開いて UI を操作します。
5. 終了するには、起動中のコンソールウィンドウで **Ctrl+C** を押してください。

> `.venv` と依存関係は 2 回目以降の起動では再利用されるため、起動時間は短くなります。
> 依存パッケージを更新したい場合は、`.venv` フォルダを削除してから `start.bat` を再実行してください。

### 手動起動 (macOS / Linux / 開発者向け)

```bash
# 仮想環境を作成
python3 -m venv .venv
source .venv/bin/activate          # Windows の場合は .venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 起動
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

ブラウザで `http://127.0.0.1:8000/` を開きます。

### テストの実行

```bash
pytest
```

`pytest.ini` の設定に従い、`tests/` 配下のテスト(71 件)が実行されます。

---

## ディレクトリ構成

```
.
├── app/
│   ├── main.py              # FastAPI エントリポイント
│   ├── settings.py          # ルートフォルダ等の設定永続化
│   ├── master_service.py    # 個別マスタ一覧
│   ├── merge_service.py     # 結合処理
│   ├── split_service.py     # 分解処理
│   ├── kogo_normalizer.py   # 甲号証番号の正規化
│   ├── merge_kogo_shoko.py  # 結合ロジック実装
│   ├── split_evidence_docx.py # 分解ロジック実装
│   └── static/index.html    # シングルページ UI
├── tests/                   # pytest テスト一式
├── requirements.txt
├── pytest.ini
├── start.bat                # Windows 用 ワンクリック起動スクリプト
├── CLAUDE.md                # プロジェクトルール
└── README.md
```

---

## 注意事項

- 本アプリは**ローカル専用**で、インターネット側には公開しないでください(`127.0.0.1` のみで bind しています)。
- 実際の訴訟データは Google Drive 等の本番フォルダ側で管理し、リポジトリには**訴訟データ・サンプルデータをコミットしない**でください。
- UI(JSX 構造・className・レイアウト・配色・余白)および既存 API は維持対象です。変更が必要な場合は `CLAUDE.md` のルールに従い、事前にユーザー承認を得てください。
