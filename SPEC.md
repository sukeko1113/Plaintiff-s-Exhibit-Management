# 甲号証管理アプリ — Claude Code 開発仕様書 v02

> 本ファイルはユーザー提供の v02 仕様書のコピーです。実装は本仕様書に従います。

## 0. このドキュメントの使い方
訴訟用「甲号証」管理アプリの完全仕様書です。実装中に不明点があれば必ずユーザーに確認します。特に以下の 3 点は誤実装すると致命的です。

- 表記ゆれの正規化ルール（§5）
- 甲号証の単位の判定ロジック（§6）
- 甲号証リスト.docx の記載形式（§4.4）

### v01 → v02 の主な変更点
1. **【最重要】** 分解ロジックを「ページ先頭」判定から「**【...】**（全角隅付き括弧）マーカー」判定に変更。フォールバックとして括弧なしの単独行マッチも許容。
2. 甲号証リスト.docx のフォーマット明確化（1 行 1 ラベル + 説明コメント）。
3. 結合甲号証ファイル名の自動生成規則を明記。
4. UI モックがない場合のフォールバック手順を追加。
5. dry-run（試行モード）を全破壊的操作に追加。
6. バックアップファイルの命名規則・世代管理ルールを追加（`_backup/YYYYMMDD-HHMMSS/`、10 世代保持）。

### 確定した仕様判断（実装時の確認済み）
- 証拠説明書テーブル: 個別マスタの本文から「標目／作成年月日／作成者」を完全自動抽出（不明欄は空欄）
- 甲号証リスト: 1 行 1 ラベルの単純テキスト形式（先頭にコメント行）
- 結合甲号証フォルダに複数ファイルがあるとき: UI のドロップダウンで対象を選択
- 上書きポリシー: `_backup/YYYYMMDD-HHMMSS/` へ自動退避してから上書き（確認モーダルなし）
- マーカー形式の優先度: 【】が見つかれば括弧なしマーカーは無視（§6.3）
- バックアップ世代数: 最新 10 世代を保持
- OS: Windows 10/11 のみを対象

## 1. プロジェクト概要
- 目的: 甲号証 Word ファイルの結合・分解・一覧表作成を半自動化
- 形態: ローカル Web アプリ（バックエンド = Python FastAPI、フロントエンド = React）
- データ場所: ローカル PC 上の Google Drive 同期フォルダ

## 2. 技術スタック
| レイヤ | 技術 |
| --- | --- |
| バックエンド | Python 3.10+ / FastAPI / Uvicorn |
| Word 操作 | python-docx |
| Word 結合 | docxcompose |
| フロントエンド | React 18 + Vite + Tailwind CSS |

## 3. プロジェクト構造
```
Plaintiff-s-Exhibit-Management/
├── README.md
├── SPEC.md
├── start.bat
├── backend/
│   ├── requirements.txt
│   ├── main.py
│   ├── api/{routes,schemas}.py
│   ├── core/{normalizer,splitter,combiner,list_builder,table_builder,
│   │       case_parser,folder_setup,backup}.py
│   └── tests/{test_normalizer,test_splitter,generate_fixtures}.py
└── frontend/{index.html,package.json,vite.config.js,
            tailwind.config.js,postcss.config.js,src/{App.jsx,api.js,main.jsx,index.css}}
```

## 4. データ構造とフォルダ規約
### 4.1 ルート直下に必要なもの
- `甲号証リスト.docx`
- `個別マスタ/`
- `結合甲号証/`
- `_backup/`（v02 追加）

### 4.2 個別マスタのファイル名規約
全角 3 桁: `甲第００１号証.docx` / `甲第０１２号証その１.docx`

### 4.4 甲号証リスト.docx のフォーマット
1 行 1 ラベル。先頭にコメント行（自動生成時）。空行・コメント行は無視。

### 4.5 結合甲号証のファイル名規約
- 自動生成（リスト→結合）: `<ルート名>_甲号証_結合_YYYYMMDD-HHMMSS.docx`
- 自動生成（案件→結合）: `<ルート名>_甲号証_完成_YYYYMMDD-HHMMSS.docx`
- ユーザー指定があればそれを優先。`.docx` が無ければ自動補完。

### 4.6 バックアップ規則
破壊的操作（個別マスタクリア・リスト上書き・結合甲号証同名上書き）の前に `_backup/YYYYMMDD-HHMMSS/` 配下へコピー。最新 10 世代のみ保持し、古いものから自動削除。

## 5. 表記ゆれ正規化（最重要）
- `甲(第)? <数字 1-3 桁> 号証` を寛容に認識
- 全角・半角混在、空白あり、`第` 省略を許容
- **隅付き括弧 `【...】` も許容**（剥がして同じラベルへ）
- 出力は `甲第<全角3桁>号証` 形式
- 枝番は `その|の|枝 + 数字` を認識し `その<全角>` へ統一
- 本体番号 1〜999 のみ受理
- 文中抽出版 (`normalize_koshou`) と段落全体マッチ版 (`normalize_koshou_strict`) の 2 種類

## 6. 「甲号証の単位」の判定ロジック（v02 で大幅修正）
### 6.1 仕様
> 一つの甲号証は、`【甲第xxx号証】` と表示されているところから、次の `【甲第yyy号証】` の前まで。

### 6.3 マーカー判定ルール
1. **【優先】**`MARKER_BRACKETED_PATTERN`（`【甲第xxx号証】` 形式）にマッチする段落全体
2. **【フォールバック】**`MARKER_BARE_STRICT_PATTERN`（括弧なし単独行）かつ直前段落が空 or 改ページ持ち（または自身が改ページを持つ）

【】 が 1 件でも見つかった場合はフォールバックを使わない（§6.3 混在禁止）。

## 7. 機能仕様（API）
- `POST /api/setup` — ルートフォルダ初期化、サマリ返却
- `POST /api/master/list` — 個別マスタ一覧（重複検出含む）
- `POST /api/master/clear` — 個別マスタを空にする（dry_run 対応）
- `POST /api/combined/list` — 結合甲号証ファイルの詳細一覧
- `POST /api/split` — 結合 → 個別 分解（dry_run 対応）
- `POST /api/list/open` — Word でリストを開く
- `POST /api/list/auto-create` — リストの自動作成（master / combined）（dry_run 対応）
- `POST /api/list/parse` — リスト解析（無視行も返却）
- `POST /api/combine` — 個別 → 結合（dry_run 対応、自動ファイル名）
- `POST /api/case/parse` — 案件ファイルから号証抽出（ヘッダ・フッタも走査）
- `POST /api/case/build-combined` — 案件ベース結合 + 証拠説明書テーブル
- `POST /api/backup/open` — `_backup` フォルダを Explorer で開く

すべての破壊的 API は `dry_run`（boolean、既定 false）をサポート。

## 8. UI 仕様
- React + Tailwind の SPA、6 セクション構成
- ヘッダーに「_backup を開く」ボタン
- 各破壊的操作の隣に「dry-run」チェックボックス
- リスト解析結果に「無視された行」を黄色注意で表示
- ログには時刻 + アイコン（⏳/✅/❌/🟡）

## 9. 起動スクリプト
`start.bat` でバックエンド venv 構築 → `python -m uvicorn backend.main:app` 起動 → フロント `npm install && npm run dev` → 5 秒後にブラウザ起動。

## 10. エラーハンドリング・エッジケース
- 日本語パス・全角括弧
- Google Drive 同期中のロック (`PermissionError`)
- テーブル内・ヘッダ・フッタの号証ラベル
- 画像のみの甲号証
- 同じ正規化結果になる別名ファイル（警告）
- マーカー 0 件のときは明示的にエラー
- バックアップ容量不足時は処理を中断

## 11. テスト要件
- pytest による normalizer / splitter / combiner / list_builder / case_parser のテスト
- `backend/tests/generate_fixtures.py` で bracketed / bare / case / list / master の 5 種を生成

## 13. 完成判定基準
- start.bat で起動・ブラウザ自動オープン
- フォルダ・ファイルが自動作成される（`_backup` 含む）
- 結合 → 分解 → 再結合 のラウンドトリップで内容が壊れない
- 正規化テスト全 pass
- 【】マーカー・括弧なし単独行どちらでも分解可能
- 案件ファイルからの結合甲号証作成
- 証拠説明書テーブルが先頭に挿入
- dry-run が破壊的操作で機能
- バックアップが `_backup/YYYYMMDD-HHMMSS/` に作成
