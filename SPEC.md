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
- 個別マスタまたは結合甲号証から甲号証リストを生成する

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
```
Plaintiff-s-Exhibit-Management/
├── app/                              # バックエンド本体
│   ├── __init__.py
│   ├── main.py                       # FastAPI エントリポイント
│   ├── settings.py                   # アプリ設定の保存・読み込み
│   ├── kogo_normalizer.py            # 甲号証番号の正規化
│   ├── master_service.py             # 個別マスタ一覧取得
│   ├── merge_service.py              # 結合処理
│   ├── merge_kogo_shoko.py           # 結合の補助処理
│   ├── split_service.py              # 分解処理
│   ├── split_evidence_docx.py        # 分解の本体処理
│   ├── list_service.py               # 甲号証リスト生成処理
│   └── static/
│       └── index.html                # フロントエンド UI(1 ファイル)
├── backend/                          # 旧構成の名残(現在は実質未使用)
│   ├── api/
│   └── core/vendor/
├── tests/                            # pytest テスト
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_master.py
│   ├── test_merge.py
│   ├── test_settings.py
│   └── test_split.py
├── CLAUDE.md                         # Claude Code 向けルール
├── README.md                         # プロジェクト説明
├── requirements.txt                  # Python 依存関係
├── pytest.ini                        # pytest 設定
├── start.bat                         # Windows 用起動スクリプト
├── .gitignore
└── .gitattributes
```

### 2.3 ルートフォルダ配下の構成(業務データ)
ユーザーが指定する「ルートフォルダ」配下に、以下が存在(または `/api/setup` で自動生成)する。

```
<ルートフォルダ>/
├── 甲号証リスト.docx                  # 結合順や対象を定義する Word ファイル
├── 個別マスタ/                        # 個別の甲号証 Word ファイルを格納
│   ├── 甲第001号証.docx
│   ├── 甲第002号証.docx
│   └── ...
└── 結合甲号証/                        # 結合結果の出力先
    └── (結合した Word ファイル)
```

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

### 5.9 POST `/api/auto-list`
- **機能:** 個別マスタまたは結合甲号証から甲号証番号を抽出し、ルート直下の「甲号証リスト.docx」を生成する(番号を縦に並べただけのシンプルなリスト)
- **リクエスト:** `AutoListRequest`
```json
  {
    "root_folder": "C:\\Users\\...",
    "source": "master"
  }
```
  - `source`: `"master"`(個別マスタ配下の docx を走査)/ `"combined"`(結合甲号証/結合甲号証.docx の本文マーカーを走査)
- **動作:**
  1. ルートフォルダ配下の必要フォルダを保証(`ensure_folders`)
  2. `source` に応じて番号を抽出(詳細は §6.4)
  3. 既存の「甲号証リスト.docx」があれば `甲号証リスト.docx.bak` にバックアップしてから上書き
  4. `(main, branch or 0)` 昇順で並べ、1 行 1 段落で書き出す
     - 表記は正規化ファイル名形式(例:`甲第００１号証`、枝番付きは `甲第００１号証その２`)
     - 【】(マーカー形式)は使わない
- **レスポンス:** `AutoListResult`
```json
  {
    "output_path": "C:\\...\\甲号証リスト.docx",
    "source": "master",
    "numbers_written": ["甲第００１号証", "甲第００２号証"],
    "backup_created": true,
    "warnings": []
  }
```
- **エラー:**
  - ルートが存在しない → HTTP 400
  - `source` が `"master"`/`"combined"` 以外 → HTTP 400
  - `source="combined"` で結合甲号証.docx が不在 → HTTP 400

---
## 6. 主要機能の処理ロジック

### 6.1 結合(`merge_service.merge_kogo`)

#### 6.1.1 入出力
- **入力:** ルートフォルダのパス
- **入力ファイル:** `<root>/個別マスタ/*.docx`
- **参照ファイル:** `<root>/甲号証リスト.docx`(順序・対象の指定用)
- **出力ファイル:** `<root>/結合甲号証/結合甲号証.docx`
- **既存出力のバックアップ:** 出力先に同名ファイルがある場合、`結合甲号証.docx.bak` として複製

#### 6.1.2 処理の流れ
1. `ensure_folders()` でルート配下の必要なフォルダ・ファイルを保証
2. `read_kogo_list()` で甲号証リストから(主番号, 枝番号)のセットを抽出
3. `collect_master_files()` で個別マスタ配下の docx を走査
4. **モード分岐:**
   - **リスト使用モード(`list_used = True`):**
     - 甲号証リストに有効な番号が 1 件以上記載されている場合
     - リストに含まれる番号のみを個別マスタから抽出して結合
     - リストにあるが個別マスタに無い番号は `missing_in_master` に記録
   - **全結合モード(`list_used = False`):**
     - リスト不在 / 空 / 番号抽出ゼロ件の場合
     - 個別マスタ配下の全 docx を結合
5. 個別マスタ内に同一番号の重複があれば警告に記録し、最初の 1 件のみ採用
6. ソートキー(`(main, branch or 0)`)で並び替え
7. `prepare_and_merge()`(`docxcompose` を内部で利用)を呼び出してページ区切りを挿入しつつ結合
8. `MergeOutcome` を返却

#### 6.1.3 個別マスタ走査の特例
- `~$` で始まる Word の一時ロックファイルは除外
- 番号を抽出できないファイルは警告に記録し、結合対象から除外

---

### 6.2 分解(`split_service.split_kogo`)

#### 6.2.1 入出力
- **入力:** ルートフォルダのパス、(任意で)分解元 docx パス、上書きフラグ
- **既定の入力ファイル:** `<root>/結合甲号証/結合甲号証.docx`
- **出力先:** `<root>/個別マスタ/`
- **出力ファイル:** マーカーごとに分解された個別 docx(正規化済みファイル名)

#### 6.2.2 処理の流れ
1. `ensure_folders()` でルート配下を保証
2. 入力ファイルの存在確認(無ければ `FileNotFoundError`)
3. 一時ディレクトリ(`tempfile.mkdtemp("kogo_split_")`)を作成
4. `split_docx()` で本体処理を実行(詳細は `split_evidence_docx.py` 参照)
5. 生成された各ファイルを個別マスタへ移動:
   - 既存ファイルが無い → `created_files` に記録
   - 既存ファイルあり、`overwrite=True` → 上書きして `overwritten_files` に記録
   - 既存ファイルあり、`overwrite=False` → スキップして警告に記録
6. 一時ディレクトリを削除(`finally` で必ず実行)
7. `SplitOutcome` を返却

#### 6.2.3 例外
- 分解元ファイル不在 → `FileNotFoundError`
- 分解処理の値異常 → `ValueError`(API 層で HTTP 400 に変換)

---

### 6.3 個別マスタ一覧(`master_service.list_master`)

> 詳細は `app/master_service.py` を確認(本フェーズ未取得)。  
> 推測ベースでは、個別マスタフォルダの docx を走査して `KogoNumber` で正規化した結果を `MasterListingModel` として返す。

---

### 6.4 リスト生成(`list_service.generate_list`)

#### 6.4.1 入出力
- **入力:** ルートフォルダのパス、`source`(`"master"` または `"combined"`)
- **入力ファイル:**
  - `source="master"`: `<root>/個別マスタ/*.docx`
  - `source="combined"`: `<root>/結合甲号証/結合甲号証.docx`
- **出力ファイル:** `<root>/甲号証リスト.docx`(ルート直下の 1 ファイル)
- **既存出力のバックアップ:** 出力先に同名ファイルがある場合、`甲号証リスト.docx.bak` として複製
  - 理由:このファイルは結合(merge)の入力でもあり、ユーザーが手動で並び順を編集している可能性があるため、不可逆的な上書きを避ける
  - 判定は「呼び出し時点で既存だったか」で行う(`ensure_folders` が空ファイルを新規作成するケースを除外するため)

#### 6.4.2 処理の流れ
1. `source` の妥当性チェック(`"master"`/`"combined"` のみ受理、それ以外は `ValueError`)
2. 出力ファイルの事前存在チェック(バックアップ要否の判定用)
3. `ensure_folders()` でルート配下を保証
4. **モード分岐:**
   - **`source="master"`:**
     - 個別マスタ配下の docx を `sorted(...glob("*.docx"))` で走査
     - `~$` で始まる Word の一時ロックファイルは除外
     - `kogo_normalizer.detect_number` で番号を抽出(本文 → ファイル名の優先順位)
     - 番号を抽出できないファイルは警告に記録して除外
     - 同一番号の重複は最初の 1 件のみ採用、警告に記録
   - **`source="combined"`:**
     - 結合甲号証.docx が不在なら `FileNotFoundError`
     - 全段落のテキストを `MARKER_PATTERN` で走査
     - 重複は除去(最初の出現のみ採用)
5. `(main, branch or 0)` 昇順で並べ替え
6. 既存出力があれば `甲号証リスト.docx.bak` にバックアップ
7. 番号を正規化ファイル名形式(`甲第〇〇〇号証` / `甲第〇〇〇号証その〇`、§7.1.4)で 1 段落 1 件として書き出す
   - python-docx のみで生成(docxcompose は不要)
   - 【】(マーカー形式)は使わない
8. `ListOutcome` を返却

#### 6.4.3 例外
- `source` が不正 → `ValueError`(API 層で HTTP 400 に変換)
- `source="combined"` で結合甲号証.docx 不在 → `FileNotFoundError`(API 層で HTTP 400 に変換)
- ルートフォルダ不在 → API 層で HTTP 400(`_require_existing_root` が判定)

---

### 6.5 設定の永続化(`settings.py`)

#### 6.5.1 保存先
- **Windows:** `%LOCALAPPDATA%/KogoKanri/settings.json`(`LOCALAPPDATA` 未設定なら `~/KogoKanri/settings.json`)
- **macOS / Linux:** `~/.kogo_kanri/settings.json`
- **テスト時:** 環境変数 `KOGO_KANRI_SETTINGS_PATH` で完全上書き可能

#### 6.5.2 形式
JSON。現在の項目は `root_folder`(任意)のみ。

```json
{"root_folder": "C:\\Users\\...\\..."}
```

#### 6.5.3 動作
- `load_settings()`: ファイルが無ければ既定値の `AppSettings()` を返す。読み込み失敗時はログに警告を出して既定値を返す(例外は外に出さない)。
- `save_settings()`: 親フォルダを作成しつつ JSON を書き出す。

---
## 7. データ構造と正規化ルール

### 7.1 甲号証番号の正規化(`kogo_normalizer.py`)

#### 7.1.1 KogoNumber データクラス
甲号証番号は「主番号(必須)」と「枝番号(任意)」の組として表現する。

```python
@dataclass(frozen=True)
class KogoNumber:
    main: int                    # 主番号(半角整数で保持)
    branch: Optional[int] = None # 枝番号(無ければ None)
```

#### 7.1.2 正規化ルール

| 項目 | 規則 |
|---|---|
| 主番号 | **全角 3 桁ゼロ埋め**(例:1 → `００１`、25 → `０２５`) |
| 主番号(4 桁以上) | **そのまま全角化**(例:1234 → `１２３４`) |
| 枝番号 | **全角化のみ、ゼロ埋めなし**(例:2 → `２`) |
| 数字種別 | 半角数字(0-9)・全角数字(０-９)のいずれも入力として受け付ける |

#### 7.1.3 正規化マーカー(本文用)
- 枝番無し: `【甲第〇〇〇号証】`(例:`【甲第００１号証】`)
- 枝番有り: `【甲第〇〇〇号証その〇】`(例:`【甲第００１号証その２】`)

#### 7.1.4 正規化ファイル名(拡張子前まで)
- 枝番無し: `甲第〇〇〇号証`(例:`甲第００１号証`)
- 枝番有り: `甲第〇〇〇号証その〇`(例:`甲第００１号証その２`)

### 7.2 番号抽出のパターン(正規表現)

3 種類のパターンを使い分けている。いずれも全角・半角の数字、「第」の有無、空白・改行の混入を許容する。

| パターン名 | 用途 | 「【】」の扱い |
|---|---|---|
| `MARKER_PATTERN` | 結合済み本文中のマーカー検出(分解時など) | `【】` を許容 |
| `FILENAME_PATTERN` | ファイル名からの番号検出 | `【】` 含まず |
| `LIST_PATTERN` | 甲号証リストの段落・セルから番号を拾う | `【】` 含まず |

### 7.3 番号の検出優先順位(`detect_number`)

個別マスタファイルから番号を検出するときの順序:

1. **本文の冒頭 10 段落**を `MARKER_PATTERN` で走査
2. 取れなければ**ファイル名**を `FILENAME_PATTERN` で走査
3. 両方取れたが値が異なる場合 → **本文を優先**して警告を出力
4. どちらも取れない場合 → `ValueError` を送出

### 7.4 甲号証リストの構造(`read_kogo_list`)

#### 7.4.1 走査対象
- 段落のテキスト
- すべての表のすべてのセルのすべての段落

#### 7.4.2 番号抽出
- `LIST_PATTERN` で各テキストブロックからすべてのマッチを拾う
- 重複は集合で排除
- 重複が検知された番号は警告に記録

#### 7.4.3 リスト不在 / 空の扱い
- ファイルが存在しない → 空セット(全結合モードへ)
- 読み込み失敗 → 警告に記録、空セット
- 番号がゼロ件 → 空セット

---

## 8. 既知の制約・前提条件

- Windows を主対象とする(`start.bat` のみ提供)
- ローカル端末の単一ユーザーを想定(認証機能なし、`127.0.0.1` のみ待ち受け)
- 訴訟データはリポジトリに含めない(別フォルダで管理)
- データベースは使用せず、ファイルシステムで完結

---

## 9. 要確認事項

> 第 2 フェーズで多くを解消した。残る項目を以下に絞って記載する。

- [ ] `app/static/index.html` の構成(React か素の HTML/JS か、API 呼び出しの実装)
- [ ] `app/master_service.py` の詳細(`MasterEntry` の各フィールドの算出方法)
- [ ] `app/split_evidence_docx.py` の詳細(ページ境界判定アルゴリズム)
- [ ] `app/merge_kogo_shoko.py` の詳細(`prepare_and_merge` の実装、ページ区切り挿入の仕組み)
- [ ] `backend/` フォルダの今後の扱い(削除するか、何かに使うか)
- [ ] 「証拠説明書」関連の機能が今後追加されるかどうか(現実装には存在しない)
- [ ] テストファイルの内容と件数(`tests/` 配下、特に `test_*.py` の各テスト件数)

