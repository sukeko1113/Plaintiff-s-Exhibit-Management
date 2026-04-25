# 甲号証管理アプリ — Claude Code 開発仕様書

> 本ファイルはユーザーから提供された開発仕様書のコピーです。実装は本仕様書に従います。

## 0. このドキュメントの使い方
これは、訴訟用「甲号証（こうごうしょう）」管理アプリを Claude Code で実装してもらうための完全仕様書です。Claude Code はこのドキュメントを `SPEC.md` として保存し、本仕様に従ってプロジェクト一式（バックエンド・フロントエンド・起動スクリプト）を生成します。

実装中に仕様の不明点があれば、推測ではなく **必ずユーザーに質問** してください。特に「表記ゆれの正規化ルール」と「甲号証の単位の判定ロジック」は誤実装すると致命的なので、迷ったら確認してください。

## 確定した仕様判断（実装前の確認結果）
- 証拠説明書テーブル：本文から「標目／作成年月日／作成者」も完全自動抽出を試みる（不明欄は空欄）
- 甲号証リスト：1 行 1 号証ラベルの単純テキスト形式
- 結合甲号証フォルダに複数ファイルがあるとき：UI のドロップダウンで対象を選択
- 上書きポリシー：`<元ファイル名>.bak.docx` のバックアップを作成してから確認なしで上書き
- OS：Windows 10/11 のみを対象

## 1. プロジェクト概要
### 1.1 目的
弁護士・法律事務員が、訴訟で提出する **甲号証（原告側証拠書類）** を Word ファイル単位で管理し、結合・分解・一覧表作成を半自動化するためのローカル Web アプリ。

### 1.2 利用シーン
- 各甲号証は 1 ファイル = 1 Word（.docx）として「個別マスタ」に保管される
- 申立書（案件ファイル）に列挙された号証を、番号順に結合して 1 つの「結合甲号証.docx」を作る
- 結合甲号証の先頭に「証拠説明書（一覧テーブル）」を自動生成する
- 既存の結合甲号証を逆方向に分解して、個別マスタを再構築する

### 1.3 動作環境
- OS: Windows 10/11
- 形態: ローカル Web アプリ（バックエンド = Python FastAPI、フロントエンド = React、ブラウザで操作）
- データ場所: ローカル PC 上の Google Drive 同期フォルダ

## 2. 技術スタック
| レイヤ | 技術 | 用途 |
| --- | --- | --- |
| バックエンド | Python 3.10+ / FastAPI / Uvicorn | REST API サーバー |
| Word 操作 | python-docx | 読み取り・パラグラフ単位の操作 |
| Word 結合 | docxcompose | 書式を保ったままの .docx 結合 |
| ファイル操作 | pathlib / shutil / os.startfile | パス処理・Word 起動 |
| フロントエンド | React 18 + Vite + Tailwind CSS | UI |
| アイコン | lucide-react | UI |
| HTTP クライアント | fetch | フロント↔バック通信 |

## 3. プロジェクト構造
```
Plaintiff-s-Exhibit-Management/
├── README.md
├── SPEC.md
├── start.bat
├── backend/
│   ├── requirements.txt
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── normalizer.py
│   │   ├── splitter.py
│   │   ├── combiner.py
│   │   ├── list_builder.py
│   │   ├── table_builder.py
│   │   ├── case_parser.py
│   │   └── folder_setup.py
│   └── tests/
│       ├── test_normalizer.py
│       ├── test_splitter.py
│       └── fixtures/
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api.js
        └── index.css
```

## 4. データ構造とフォルダ規約
### 4.1 ルートフォルダ配下の構成（必須）
| 名前 | 種類 | 説明 |
| --- | --- | --- |
| `甲号証リスト.docx` | ファイル | 申立書で使用される甲号証番号を縦に列挙した Word ファイル |
| `個別マスタ` | フォルダ | 各甲号証を 1 ファイル 1 号証で保管 |
| `結合甲号証` | フォルダ | 結合済み甲号証ファイルの保存先 |

### 4.2 個別マスタのファイル名規約
全角数字 3 桁に強制統一：
- `甲第００１号証.docx`
- `甲第０１２号証.docx`
- `甲第０１２号証その１.docx`（枝番あり）

### 4.3 案件ファイル
ユーザーが指定する Word ファイル。「甲第〇〇号証」という記述（本文中・表中問わず）が含まれており、そこから使用する号証を抽出する。

## 5. 表記ゆれ正規化（最重要・厳守）
詳細はオリジナル仕様書に従う。要点：

- `甲(第)? <数字 1-3 桁> 号証` を寛容に認識
- 全角・半角混在、空白あり、`第` 省略を許容
- 出力は `甲第<全角3桁>号証` 形式
- 枝番は `その|の|枝 + 数字` を認識し `その<全角>` で出力
- 本体番号 1〜999 のみ受理
- 文中抽出版 (`normalize_koshou`) と段落全体マッチ版 (`normalize_koshou_strict`) の 2 種類

## 6. 「甲号証の単位」の判定ロジック
- ドキュメント先頭、`pageBreakBefore`、ラン内 `<w:br w:type="page"/>`、`sectPr` を「ページ先頭相当」とみなす
- その直後の最初の非空段落が `KOSHOU_STRICT_PATTERN` にマッチしたら甲号証の開始
- 詳細はオリジナル仕様書（疑似コード）参照

## 7. 機能仕様（API 単位）
バックエンドは `http://127.0.0.1:8765` でホスト。CORS は `http://localhost:5173` を許可。

主要エンドポイント:
- `POST /api/setup` — ルートフォルダ初期化
- `POST /api/split` — 結合 → 個別 分解
- `POST /api/combine` — 個別 → 結合
- `POST /api/list/open` / `auto-create` / `parse`
- `POST /api/case/parse` / `build-combined`
- `POST /api/master/list` / `clear`

## 8. UI 仕様
- React + Tailwind の SPA
- ルートフォルダ設定、ログ表示、各種操作ボタン、案件ファイル指定、証拠説明書テーブル編集
- ログには時刻 + アイコン（⏳/✅/❌）

## 9. 起動スクリプト (`start.bat`)
バックエンド venv 作成 → `pip install -r requirements.txt` → `uvicorn` 起動。
フロントエンド `npm install` → `npm run dev`。
5 秒後に `http://localhost:5173` を開く。

## 10. エラーハンドリング・エッジケース
- 日本語パス・全角括弧
- Google Drive 同期中のファイルロック (`PermissionError`)
- テーブル内の号証ラベル
- 画像のみの甲号証
- 同じ正規化結果になる別名ファイル（警告）
- 4 桁・0 番の号証（警告／エラー）

## 11. テスト要件
- pytest による normalizer/splitter/combiner のテスト
- fixture 生成スクリプト `tests/generate_fixtures.py`

## 12. 実装の進め方
1. プロジェクト雛形 + start.bat
2. normalizer.py（最重要）
3. folder_setup.py + /api/setup
4. splitter.py + /api/split
5. combiner.py + /api/combine
6. list_builder.py + /api/list/*
7. case_parser.py + /api/case/parse
8. table_builder.py + /api/case/build-combined
9. フロントエンド実装
10. README とユーザーマニュアル

## 13. 完成判定基準
- start.bat ダブルクリックで起動
- フォルダ自動作成
- 結合 → 分解 → 再結合 のラウンドトリップで内容が壊れない
- 正規化テスト全 pass
- 表記ゆれを含むファイルでも正しくグルーピングされる
- 案件ファイルから抽出した号証で結合甲号証が作れる
- 証拠説明書テーブルが先頭に挿入される
- UI ログ欄にエラー表示

## 14. 不明点（解決済み）
セクション冒頭の「確定した仕様判断」を参照。
