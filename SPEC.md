# 甲号証管理システム 仕様書 (SPEC.md)

> 本ドキュメントは、リポジトリ `Plaintiff-s-Exhibit-Management` に格納されている実装(`app/` 配下)を読み取り、現状の動作を文書化したものです。
> 「あるべき姿」ではなく「現時点で実装されている内容」を記述しています。

---

## 1. プロジェクト概要

### 1.1 目的
日本の民事訴訟における原告側の証拠書類「甲号証」(Ko-number Evidence)を管理するためのローカル Web アプリケーション。Word(.docx)形式の証拠書類について、以下の作業を支援する。

- 個別の甲号証ファイル(個別マスタ)を一括して 1 つの Word ファイルに**結合**する
- 結合済みの甲号証ファイルを甲号証番号(甲第○号証/甲○)単位で**分解**して個別ファイルに分ける
- 「甲号証リスト.docx」をベースに、結合対象や順序を制御する
- 個別マスタ一覧を取得して甲号証番号を正規化表示する

### 1.2 想定ユーザー
弁護士・パラリーガル等、訴訟実務で甲号証ファイルを編集する担当者(個人ローカル端末で運用)。

### 1.3 運用形態
- ローカル PC 上で動作する Web アプリケーション(`http://127.0.0.1:8000/`)
- 訴訟データそのものは Google Drive 等の別フォルダに置き、本アプリはそのパスを「ルートフォルダ」として参照する
- 本リポジトリには訴訟データを含めない(`.gitignore` で除外)

---

## 2. システム構成

### 2.1 全体構成
- **バックエンド:** Python / FastAPI による REST API
- **フロントエンド:** シングルページの HTML(`app/static/index.html`)を `GET /` で配信
- **永続化:** ファイルシステムのみ。データベースは使用しない
  - アプリ設定(ルートフォルダパス)はローカルの設定ファイルに保存(詳細は後続セクションで記載)
  - 業務データはルートフォルダ配下に Word ファイルとして保存

### 2.2 ディレクトリ構成(リポジトリ)
Plaintiff-s-Exhibit-Management/ ├── app/ # バックエンド本体 │ ├── init.py │ ├── main.py # FastAPI エントリポイント │ ├── settings.py # アプリ設定の保存・読み込み │ ├── kogo_normalizer.py # 甲号証番号の正規化 │ ├── master_service.py # 個別マスタ一覧取得 │ ├── merge_service.py # 結合処理 │ ├── merge_kogo_shoko.py # 結合の補助処理 │ ├── split_service.py # 分解処理 │ ├── split_evidence_docx.py # 分解の本体処理 │ └── static/ │ └── index.html # フロントエンド UI(1 ファイル) ├── backend/ # 旧構成の名残(現在は実質未使用) │ ├── api/ │ └── core/vendor/ ├── tests/ # pytest テスト │ ├── conftest.py │ ├── test_api.py │ ├── test_master.py │ ├── test_merge.py │ ├── test_settings.py │ └── test_split.py ├── CLAUDE.md # Claude Code 向けルール ├── README.md # プロジェクト説明 ├── requirements.txt # Python 依存関係 ├── pytest.ini # pytest 設定 ├── start.bat # Windows 用起動スクリプト ├── .gitignore └── .gitattributes

### 2.3 ルートフォルダ配下の構成(業務データ)
ユーザーが指定する「ルートフォルダ」配下に、以下が存在(または `/api/setup` で自動生成)する。
<ルートフォルダ>/ ├── 甲号証リスト.docx # 結合順や対象を定義する Word ファイル ├── 個別マスタ/ # 個別の甲号証 Word ファイルを格納 │ ├── 甲第001号証.docx │ ├── 甲第002号証.docx │ └── ... └── 結合甲号証/ # 結合結果の出力先 └── (結合した Word ファイル)

> ※ フォルダ名・ファイル名の正確な値は `app/merge_service.py` の定数(`LIST_FILENAME`, `MASTER_DIRNAME`, `OUTPUT_DIRNAME`)で定義されている。詳細は後続セクションで追記する。

---

## 3. 技術スタック

### 3.1 バックエンド
| ライブラリ | バージョン | 用途 |
|---|---|---|
| Python | 3.10+ | 実行環境 |
| FastAPI | >=0.110.0 | Web フレームワーク |
| Uvicorn | >=0.27.0 (standard) | ASGI サーバー |
| Pydantic | >=2.0.0 | リクエスト/レスポンスのスキーマ検証 |
| python-docx | >=1.0.0 | Word ファイルの読み書き |
| docxcompose | >=1.4.0 | Word ファイルの結合(スタイル参照競合・画像 ID 衝突を回避) |

### 3.2 フロントエンド
- 単一の HTML ファイル(`app/static/index.html`)
- `GET /` で配信される
- React を含むかどうかは `index.html` の中身で確認する必要がある(後続セクションで追記)

### 3.3 テスト
| ライブラリ | バージョン | 用途 |
|---|---|---|
| pytest | >=8.0.0 | テストフレームワーク |
| httpx | >=0.27.0 | FastAPI のテストクライアント |

### 3.4 docxcompose を採用した理由
python-docx 単体で Word ファイルを結合すると、スタイル参照の競合や画像 ID の衝突が発生する。`docxcompose` を使うことでこれを回避している。

---

## 4. 起動方法

### 4.1 Windows(主対象環境)
1. `start.bat` をダブルクリック
2. 初回起動時は以下を自動実行:
   - Python(`py -3` または `python`)を PATH から検出
   - 仮想環境 `.venv` を作成
   - `requirements.txt` の依存関係をインストール
3. Uvicorn が起動し、`http://127.0.0.1:8000/` でアクセス可能
4. 停止は Ctrl+C

### 4.2 macOS / Linux
専用の起動スクリプトは未提供。手動で以下を実行:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 4.3 Python 検出ロジック(start.bat)
1. `where py` が成功 → `py -3` を使用
2. それも失敗 → `where python` が成功 → `python` を使用
3. どちらも失敗 → エラーメッセージを表示して終了

---

## 5. API エンドポイント一覧

すべて `app/main.py` に定義されている。エラー時は HTTP 400(クライアント起因)または 500(サーバー起因)を返す。

### 5.1 GET `/`
- **機能:** UI(シングルページ HTML)を返却
- **レスポンス:** `text/html`
  - `app/static/index.html` が存在する場合 → その内容を返却
  - 存在しない場合 → `<h1>甲号証管理システム</h1>` のみ返却

### 5.2 GET `/api/settings`
- **機能:** 保存済みのルートフォルダパスを取得
- **レスポンス:** `SettingsModel`
```json
  {"root_folder": "C:\\Users\\..." }   // 未設定なら null
```

### 5.3 POST `/api/settings`
- **機能:** ルートフォルダパスを保存(フォルダの存在確認は行わない)
- **リクエスト:** `SettingsModel`
```json
  {"root_folder": "C:\\Users\\..." }
```
- **レスポンス:** リクエストと同じ内容を返却

### 5.4 POST `/api/setup`
- **機能:** ルートフォルダを保存し、必要なフォルダ・ファイルを自動生成
- **リクエスト:** `RootFolderRequest`
```json
  {"root_folder": "C:\\Users\\..." }
```
- **動作:**
  1. ルート配下に「甲号証リスト.docx」「個別マスタ/」「結合甲号証/」が無ければ作成
  2. ルートフォルダパスを設定として保存
- **レスポンス:** `SetupResult`
```json
  {
    "root_folder": "...",
    "messages": [
      "ルートフォルダを設定しました: ...",
      "「甲号証リスト.docx」を新規作成しました。",
      "「個別マスタ」フォルダを確認しました。",
      "「結合甲号証」フォルダを新規作成しました。"
    ]
  }
```
- **エラー:** フォルダ作成失敗時 → HTTP 400

### 5.5 POST `/api/open-list`
- **機能:** ルート配下の「甲号証リスト.docx」を OS の既定アプリで開く
- **リクエスト:** `RootFolderRequest`
- **動作:**
  - Windows: `os.startfile()`
  - macOS: `open` コマンド
  - Linux: `xdg-open` コマンド
- **レスポンス:** `OpenListResult`
```json
  {"opened_path": "C:\\...\\甲号証リスト.docx"}
```
- **エラー:** ルートが存在しない → HTTP 400 / ファイルを開けない → HTTP 500

### 5.6 POST `/api/merge`
- **機能:** 個別マスタ配下の Word ファイルを 1 つに結合(docxcompose 使用)
- **リクエスト:** `RootFolderRequest`
- **レスポンス:** `MergeResult`
```json
  {
    "output_path": "...",
    "merged_files": ["甲第001号証.docx", "甲第002号証.docx"],
    "list_used": true,
    "missing_in_master": [],
    "warnings": []
  }
```
  - `list_used`: 「甲号証リスト.docx」を順序定義として使ったか
  - `missing_in_master`: リストには載っているが個別マスタに無いファイル
  - `warnings`: その他の警告メッセージ
- **エラー:** ルートが存在しない → HTTP 400

### 5.7 POST `/api/split`
- **機能:** 結合済みの Word ファイルを甲号証番号単位で分解
- **リクエスト:** `SplitRequest`
```json
  {
    "root_folder": "...",
    "input_path": "...",   // 任意。未指定時は既定の入力を使用
    "overwrite": true       // 既存の個別マスタファイルを上書きするか
  }
```
- **レスポンス:** `SplitResult`
```json
  {
    "output_dir": "...",
    "created_files": ["甲第001号証.docx"],
    "overwritten_files": [],
    "warnings": []
  }
```
- **エラー:** 入力ファイル不在 → HTTP 400 / 値の異常 → HTTP 400

### 5.8 GET `/api/master`
- **機能:** 個別マスタフォルダ配下の Word ファイル一覧を取得
- **クエリパラメータ:** `root_folder`(URL クエリで指定)
GET /api/master?root_folder=C:\Users...
- **レスポンス:** `MasterListingModel`
```json
  {
    "master_dir": "C:\\...\\個別マスタ",
    "entries": [
      {
        "filename": "甲第001号証.docx",
        "normalized_marker": "甲001",
        "main": 1,
        "branch": null,
        "size_bytes": 12345
      }
    ],
    "warnings": []
  }
```
  - `normalized_marker`: 正規化された甲号証番号
  - `main`: 主番号(例:甲第1号証 → 1)
  - `branch`: 枝番号(例:甲第1号証の2 → 2)
- **エラー:** ルートが存在しない → HTTP 400

---

## 6. 主要機能の処理ロジック

> 詳細は後続の更新で追記する。

- ### 6.1 結合(`merge_service.merge_kogo`)
- ### 6.2 分解(`split_service.split_kogo`)
- ### 6.3 個別マスタ一覧(`master_service.list_master`)
- ### 6.4 設定の永続化(`settings.py`)

---

## 7. データ構造と正規化ルール

> 詳細は後続の更新で追記する。

- ### 7.1 甲号証番号の正規化(`kogo_normalizer.py`)
- ### 7.2 甲号証リスト.docx の構造
- ### 7.3 個別マスタファイルの命名規則

---

## 8. 既知の制約・前提条件

- Windows を主対象とする(`start.bat` のみ提供)
- ローカル端末の単一ユーザーを想定(認証機能なし、`127.0.0.1` のみ待ち受け)
- 訴訟データはリポジトリに含めない(別フォルダで管理)
- データベースは使用せず、ファイルシステムで完結

---

## 9. 要確認事項

以下は実装から確実に読み取れず、後続のコード確認またはユーザー判断が必要な項目。

- [ ] `LIST_FILENAME`、`MASTER_DIRNAME`、`OUTPUT_DIRNAME` の正確な値(`app/merge_service.py` の定数)
- [ ] `app/static/index.html` の構成(React か素の HTML/JS か、UI で利用している API の範囲)
- [ ] アプリ設定(ルートフォルダパス)の保存先ファイルパスと保存形式(`app/settings.py` の実装)
- [ ] 甲号証番号の正規化ルールの詳細(`app/kogo_normalizer.py` の実装)
   - 半角/全角数字の扱い
   - 「第」の有無
   - スペースの扱い
   - 出力フォーマット(三桁全角?)
- [ ] 結合処理での順序決定ロジック(`merge_service.py`)
   - 「甲号証リスト.docx」をどう読み取るか
   - リストにない個別マスタファイルの扱い
- [ ] 分解処理でのページ境界判定アルゴリズム(`split_evidence_docx.py`)
   - 「明示的なページ区切り + 評価ラベル一致」の二条件判定の実装詳細
- [ ] `backend/` フォルダの現状(中身がほぼ空の旧構成の名残かどうか)
- [ ] 「証拠説明書」関連の機能が本実装に含まれているか(API 一覧には見当たらない)
- [ ] テスト件数(現在 5 ファイル。メモリ上の「11 ケース」と一致するかは要確認)
