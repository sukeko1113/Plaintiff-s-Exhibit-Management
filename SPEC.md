# 甲号証管理システム 仕様書 (SPEC.md)

> 本ドキュメントは、リポジトリ `Plaintiff-s-Exhibit-Management` に格納されている実装(`app/` 配下)を読み取り、現状の動作を文書化したものです。
> 「あるべき姿」ではなく「現時点で実装されている内容」を記述しています。

---

## 1. プロジェクト概要

### 1.1 目的
日本の民事訴訟における原告側の証拠書類「甲号証」(Ko-number Evidence)を管理するためのローカル Web アプリケーション。Word(.docx)形式の証拠書類について、以下の作業を支援する。

- 個別の甲号証ファイル(個別マスタ)を一括して 1 つの Word ファイルに**結合**する
- 結合済みの甲号証ファイルを甲号証番号(甲第○号証/甲○)単位で**分解**して個別ファイルに分ける
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
│   └── static/
│       └── index.html                # フロントエンド UI(1 ファイル)
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
├── 個別マスタ/                        # 個別の甲号証 Word ファイルを格納
│   ├── 甲第００１号証.docx
│   ├── 甲第００２号証.docx
│   └── ...
└── 結合甲号証/                        # 結合結果の出力先
    └── (結合した Word ファイル)
```

> ※ フォルダ名の正確な値は `app/merge_service.py` の定数(`MASTER_DIRNAME`, `OUTPUT_DIRNAME`)で定義されている。
> ※ 旧版で生成していた「甲号証リスト.docx」は廃止された。既存ルートに残っているファイルはアプリ側からは触らず、ユーザーが手動で削除する想定 (`/api/setup` 実行時に廃止案内を返す)。
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
- **機能:** ルートフォルダを保存し、必要なフォルダを自動生成
- **リクエスト:** `RootFolderRequest`
```json
  {"root_folder": "C:\\Users\\..." }
```
- **動作:**
  1. ルート配下に「個別マスタ/」「結合甲号証/」が無ければ作成
  2. 既存ルートに「甲号証リスト.docx」が残っていれば廃止案内を `messages` に追加(ファイルには触らない)
  3. ルートフォルダパスを設定として保存
- **レスポンス:** `SetupResult`
```json
  {
    "root_folder": "...",
    "messages": [
      "ルートフォルダを設定しました: ...",
      "「個別マスタ」フォルダを確認しました。",
      "「結合甲号証」フォルダを新規作成しました。"
    ]
  }
```
- **エラー:** フォルダ作成失敗時 → HTTP 400

### 5.5 (欠番)
旧 `POST /api/open-list` (甲号証リスト.docx を Word で開く) は廃止された。

### 5.6 POST `/api/merge`
- **機能:** 個別マスタ配下の Word ファイルを正規化ファイル名の辞書順で 1 つに結合(docxcompose 使用)
- **リクエスト:** `RootFolderRequest`
- **レスポンス形式:** **Server-Sent Events (`text/event-stream`)** で進捗を逐次送出。HTTP ステータスは正常時・規約外ファイル時とも `200`(処理結果はイベント種別で判別)
- **イベント種別:**

| イベント | データ形式 | 意味 |
|---|---|---|
| `progress` | `{"message": "..."}` | 進捗メッセージ。各フェーズ(バリデーション / 準備 / 結合 / 保存)で送出 |
| `done` | `{"output_path", "merged_files", "warnings"}` | 正常終了。最後に 1 件だけ送出される |
| `invalid` | `{"error", "message", "issues"[]}` | 規約外ファイル検出。最後に 1 件だけ送出される(`done` は出ない) |
| `error` | `{"message"}` | 想定外のエラー |

- **`done` イベントのデータ例:**
```json
  {
    "output_path": "...",
    "merged_files": ["甲第００１号証.docx", "甲第００２号証.docx"],
    "warnings": []
  }
```
- **`invalid` イベントのデータ例:**
```json
  {
    "error": "InvalidMasterFiles",
    "message": "個別マスタに規約外のファイルがあるため、結合を中止しました",
    "issues": [
      {
        "filename": "甲1号証.docx",
        "reason": "ファイル名が正規化形式ではありません (期待: 甲第００１号証.docx)",
        "suggested_rename": "甲第００１号証.docx"
      },
      {
        "filename": "メモ.docx",
        "reason": "甲号証番号を抽出できません",
        "suggested_rename": null
      }
    ]
  }
```
  - 規約外ファイル保護フローの詳細は §6.1.4 参照。
- **`progress` イベントのメッセージ例:**
  - `バリデーション中: 個別マスタを検査しています`
  - `バリデーション完了: 10 件のファイルを検出`
  - `[準備 1/10] 甲第００１号証.docx のマーカーを書き換え`
  - `[結合 5/10] 甲第００５号証.docx を追加`
  - `出力ファイルを保存中`
- **配信フォーマット (text/event-stream):**
```
event: progress
data: {"message": "バリデーション中: 個別マスタを検査しています"}

event: progress
data: {"message": "[準備 1/2] 甲第００１号証.docx のマーカーを書き換え"}

event: done
data: {"output_path": "...", "merged_files": ["甲第００１号証.docx", "甲第００２号証.docx"], "warnings": []}
```
- **実装メモ:** バックエンドは別スレッドで `merge_kogo()` を実行し、`queue.Queue` 経由でメインスレッド側の `StreamingResponse` に進捗を流す
- **エラー:** ルートが存在しない → HTTP 400 (こちらは JSON で返却)

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

### 6.1 結合(`merge_service.merge_kogo`)

#### 6.1.1 入出力
- **入力:** ルートフォルダのパス
- **入力ファイル:** `<root>/個別マスタ/*.docx`
- **出力ファイル:** `<root>/結合甲号証/結合甲号証.docx`
- **既存出力のバックアップ:** 出力先に同名ファイルがある場合、`結合甲号証.docx.bak` として複製

#### 6.1.2 処理の流れ
1. `ensure_folders()` でルート配下の必要なフォルダを保証
2. `validate_master_files()` で個別マスタ配下の docx を**事前バリデーション**(§6.1.4)
3. 規約外ファイルが 1 件でも見つかった場合は `InvalidMasterFilesError` を送出して**結合を中止**(API 層は SSE の `invalid` イベントを送出、§5.6)。ファイルシステムには一切変更を加えない
4. 規約準拠ファイルの (KogoNumber, Path) リストを **正規化ファイル名(`path.name`)の辞書順**でソート
5. 既存出力があれば `.bak` にバックアップ
6. `prepare_and_merge()`(`docxcompose` を内部で利用)を呼び出してページ区切りを挿入しつつ結合
7. `MergeOutcome` を返却

`merge_kogo()` は任意のキーワード引数 `on_progress: Callable[[str], None]` を受け取り、各フェーズ(バリデーション開始 / 完了 / 既存出力バックアップ / 各ファイルのマーカー書き換え / 各ファイルの結合 / 出力保存)で進捗メッセージを通知する。SSE ストリーミングでこのコールバックを使い、フロントエンドのログ欄にリアルタイム表示する(§5.6)。

#### 6.1.3 ソート規則
- ソートキーは正規化ファイル名(`path.name`)そのまま(辞書順)
- 主番号は全角3桁ゼロパディングされている前提のため、辞書順 = 主番号昇順となる(§7.1.4)
- 枝番なし(`甲第００１号証.docx`)は枝番あり(`甲第００１号証その２.docx` 等)より先に並ぶ
  (`.` (U+002E) < `そ` (U+305D) のため)
- `~$` で始まる Word の一時ロックファイルは事前バリデーション前に除外

#### 6.1.4 規約外ファイル保護フロー(`validate_master_files`)

merge 実行時、個別マスタ配下の docx に対して**事前バリデーション**を行う。違反が 1 件でもあれば `InvalidMasterFilesError` を送出して結合を中止し、API 層は HTTP 409 を返す(§5.6)。**ファイルシステムには一切変更を加えない**(自動リネームはしない)。

##### バリデーション内容
個別マスタ配下の各 docx ファイル(`~$` で始まる一時ファイルを除く)が以下をすべて満たすことを確認:

1. `kogo_normalizer.detect_number` で番号が抽出できる(§7.3)
2. ファイル名(`path.stem`)が正規化形式と一致する(§7.1.4: `甲第ＮＮＮ号証` または `甲第ＮＮＮ号証そのＮ`)
3. 同一番号 (主番号 + 枝番) のファイルが重複していない

##### 判定ロジック(`validate_master_files`)
canonical(正規化形式に一致するファイル)を先に登録してから残りを判定することで、「正規化形式に違反しているが番号は重複」というケースを「重複」として正確に報告する:

1. **第 1 パス:** 全ファイルを「canonical」「bad_format(番号は抽出できるが名前が違う)」「no_number(番号抽出不可)」に分類
2. **第 2 パス:** canonical を `seen_keys` に登録し、結合対象に追加
3. **第 3 パス:** bad_format について、`seen_keys` に同番号があれば「重複」、無ければ「正規化形式違反」として `issues` に追加。後続の同番号 bad_format を「重複」扱いするため、bad_format の番号も `seen_keys` に登録
4. **第 4 パス:** no_number を「番号抽出不可」として `issues` に追加

##### `issues` 配列の各エントリ
| フィールド | 内容 |
|---|---|
| `filename` | 規約外ファイルの名前 (拡張子込み) |
| `reason` | 違反内容の日本語メッセージ |
| `suggested_rename` | `detect_number` で番号が抽出できた場合のみ正規化ファイル名を提案。番号が抽出できないファイルや重複ケースは `null` |

##### 確認テスト
- `tests/test_merge_sort.py` — ソート規則(主番号順、枝番なし先、`~$` 除外)
- `tests/test_merge_validation.py` — 規約外ファイル時の SSE `invalid` イベント、FS 不変、`suggested_rename` 付与条件、規約準拠時の正常結合
- `tests/test_merge.py::test_merge_invokes_progress_callback` — `on_progress` が各フェーズで呼ばれる
- `tests/test_api.py::test_merge_endpoint_happy_path` — `/api/merge` が `text/event-stream` を返し、`progress` と `done` イベントが正しく流れる

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

#### 6.2.3 ページ境界判定アルゴリズム(section anchor の決定)

`split_docx()` は `<w:body>` 直下のトップレベル要素(`<w:p>` / `<w:tbl>` / `<w:sectPr>`)を順に走査し、各段落について「section anchor(分割の起点となる段落)」かどうかを次の **3 条件** すべてを満たすかで判定する。

- **(A) 段落がページ先頭にある** — 次のいずれかに該当する場合のみ
  1. 文書中の最初のトップレベル要素である
  2. **直前の段落** の末尾に `<w:br w:type="page"/>` を持つ(ハード改ページ)
  3. **直前の段落** の `<w:pPr>` 内に `<w:sectPr>` が埋め込まれている(セクション区切り)
  4. **当該段落自身** が `<w:pPr>` 内に `<w:pageBreakBefore/>` を持つ
- **(B) 段落冒頭がマーカーパターンにマッチ** — 既定パターンは `^\s*【...】` で先頭に固定。段落の途中に出現するマーカー(本文中の引用)は section anchor として拾わない
- **(C) 【】 必須** — `【` `】` で括られていることが必要。本文の引用形式と区別するための制約

##### 補足
- **表 (`<w:tbl>`) はページ先頭性を伝播しない** — 表の直前段落がハード改ページや埋め込み sectPr を持っていたとしても、表をまたいで「次の段落をページ先頭」とは見做さない。
- セクション anchor が 0 件の場合、「ページ先頭の【甲第…号証】のみ対象」である旨を含む `ValueError` を送出する。
- N 番目の anchor 段落から N+1 番目の anchor 段落の直前までを 1 つの甲号証として切り出す。

#### 6.2.4 例外
- 分解元ファイル不在 → `FileNotFoundError`
- 分解処理の値異常(マーカー無し等) → `ValueError`(API 層で HTTP 400 に変換)

---

### 6.3 個別マスタ一覧(`master_service.list_master`)

> 詳細は `app/master_service.py` を確認(本フェーズ未取得)。  
> 推測ベースでは、個別マスタフォルダの docx を走査して `KogoNumber` で正規化した結果を `MasterListingModel` として返す。

---

### 6.4 設定の永続化(`settings.py`)

#### 6.4.1 保存先
- **Windows:** `%LOCALAPPDATA%/KogoKanri/settings.json`(`LOCALAPPDATA` 未設定なら `~/KogoKanri/settings.json`)
- **macOS / Linux:** `~/.kogo_kanri/settings.json`
- **テスト時:** 環境変数 `KOGO_KANRI_SETTINGS_PATH` で完全上書き可能

#### 6.4.2 形式
JSON。現在の項目は `root_folder`(任意)のみ。

```json
{"root_folder": "C:\\Users\\...\\..."}
```

#### 6.4.3 動作
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

4 種類のパターンを使い分けている。いずれも全角・半角の数字、「第」の有無、空白・改行の混入を許容する。

| パターン名 | 用途 | 先頭固定 | 「【】」の扱い |
|---|---|---|---|
| `MARKER_PATTERN` | 結合時の本文マーカー書き換え・検出 | なし | `【】` を許容(任意) |
| `FILENAME_PATTERN` | ファイル名からの番号検出 | なし | `【】` 含まず |
| `LIST_PATTERN` | 旧 甲号証リスト走査用(現在は未使用、将来再利用に備えて残置) | なし | `【】` 含まず |
| `DEFAULT_MARKER_PATTERN`(分解専用) | `split_evidence_docx.py` の section anchor 検出 | `^\s*` で**段落冒頭に固定** | `【】` **必須** |

#### 7.2.1 分解専用パターン(`DEFAULT_MARKER_PATTERN`)の補足

`app/split_evidence_docx.py` で定義され、結合済み docx をマーカー単位に分解する際にのみ使われる。`MARKER_PATTERN` と異なり、次の 2 点で **厳格化** されている:

- 先頭が `^\s*` で固定されている — 段落の冒頭にあるマーカーのみを対象とし、段落の途中に出現するマーカー(=本文中の引用)は対象外。
- `【` `】` を必須とする — 本文の引用形式や、ファイル名・リスト由来の番号と区別する。

このパターンは「ページ境界判定 (§6.2.3)」と組み合わせて section anchor を決定する。

### 7.3 番号の検出優先順位(`detect_number`)

個別マスタファイルから番号を検出するときの順序:

1. **本文の冒頭 10 段落**を `MARKER_PATTERN` で走査
2. 取れなければ**ファイル名**を `FILENAME_PATTERN` で走査
3. 両方取れたが値が異なる場合 → **本文を優先**して警告を出力
4. どちらも取れない場合 → `ValueError` を送出

### 7.4 (欠番)
旧 §7.4「甲号証リストの構造(`read_kogo_list`)」は廃止された。結合順序は個別マスタのファイル名辞書順で決まる(§6.1.3)。

---

## 8. 既知の制約・前提条件

- Windows を主対象とする(`start.bat` のみ提供)
- ローカル端末の単一ユーザーを想定(認証機能なし、`127.0.0.1` のみ待ち受け)
- 訴訟データはリポジトリに含めない(別フォルダで管理)
- データベースは使用せず、ファイルシステムで完結

---

## 9. 要確認事項

### 9.1 解消済み項目

| 項目 | 解消した内容 |
|---|---|
| `app/static/index.html` の構成 | 単一 HTML(タブ付き UI)。`v01-UI.md` を仕様の正本とする。 |
| `app/master_service.py` の詳細 | `MasterEntry` は filename / normalized_marker / main / branch / size_bytes を持つ。詳細は §6.3 で別途追記予定。 |
| `app/split_evidence_docx.py` のページ境界判定 | §6.2.3 にアルゴリズムを正式記載。 |
| `app/merge_kogo_shoko.py` の `prepare_and_merge` | §6.1 と本ファイルの該当節で記述済み。docxcompose を使用。 |
| 「証拠説明書」関連 | 現実装には存在しない。将来追加の場合は別 PR。 |

### 9.2 テスト件数

`pytest` 実行時のテスト件数(リスト機能廃止後):

| ファイル | 件数 |
|---|---|
| `tests/test_api.py` | 10 |
| `tests/test_master.py` | 4 |
| `tests/test_merge.py` | 28(parametrize 含む) |
| `tests/test_merge_sort.py` | 4 |
| `tests/test_merge_validation.py` | 8 |
| `tests/test_settings.py` | 4 |
| `tests/test_split.py` | 8 |
| `tests/test_split_page_top.py` | 6 |
| **合計** | **72** |

### 9.3 残課題

- [ ] 証拠説明書メタデータ(タイトル・日付・著者・立証趣旨)の取得元 — 個別マスタの本文から自動抽出するのか、ユーザー入力なのかが未確定。仕様確定後に SPEC.md に追記する。

