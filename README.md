# 甲号証管理アプリ

訴訟用の甲号証（原告側証拠書類）を Word ファイル単位で管理し、結合・分解・
一覧表作成を半自動化するローカル Web アプリ。

詳細仕様は [`SPEC.md`](./SPEC.md)、実装進捗は [`PROGRESS.md`](./PROGRESS.md) を参照。

## 機能

- ルートフォルダ初期化（必須フォルダ／ファイルの自動補完）
- 結合甲号証 → 個別マスタへの分解（書式・表・画像を温存）
- 個別マスタ → 結合甲号証への結合（`docxcompose`）
- 表記ゆれの自動正規化（半角/全角／桁数／枝番すべて全角3桁＋枝番形式に統一）
- 甲号証リストの編集／個別マスタ・結合甲号証からの自動生成
- 案件ファイル（申立書等）解析 → 必要号証だけを結合した「証拠説明書付き結合甲号証」生成
- 破壊的操作前の自動バックアップ（10 世代ローテーション）

## 動作環境

- Windows 10 / 11
- Python 3.10 以上
- Node.js 18 以上

> Mac / Linux でもバックエンド単体は動作するが、`os.startfile`（リスト編集）
> は Windows 専用。フロントエンドは OS 依存なし。

## 初回セットアップ

```cmd
:: バックエンド
cd backend
pip install -r requirements.txt

:: フロントエンド
cd ..\frontend
npm install
```

## 起動

`start.bat` をダブルクリック。バックエンド／フロントエンドが別ウィンドウで起動し、
ブラウザが自動で `http://localhost:5173` を開きます。

| 用途           | ポート |
| -------------- | ------ |
| バックエンド   | 8765   |
| フロントエンド | 5173   |

ポートを変更する場合は `start.bat` の `--port`、`frontend/vite.config.js` の `server.port` を編集。

## 使い方

1. **ルートフォルダを設定**: 例 `I:\マイドライブ\...\令和8年（ワ）第131号` を入力 → 「設定・構成確認」
   - `甲号証リスト.docx` / `個別マスタ` / `結合甲号証` が無ければ自動作成されます。
2. **結合甲号証 → 分解**: 結合甲号証フォルダから対象を選択 → 「結合甲号証の分解」
   - 個別マスタが空でなければ、確認ダイアログのうえバックアップを取ってから上書きします。
3. **甲号証リスト編集／自動生成**: 「Word で開く」または「リスト自動作成」（個別マスタ／結合甲号証から）
4. **個別マスタ → 結合**: 「個別マスタの結合」。「証拠説明書テーブルを先頭に挿入」をオンにすると先頭に表が付きます。
5. **案件ファイル基準の結合**: 案件ファイルのパスを入力 → 「証拠説明書付き結合甲号証の作成」

## 証拠説明書テーブルのメタデータ

個別マスタ .docx の **冒頭** に下記の形式でメタを書くと自動で抽出されます（仕様 §9.2、ユーザ確認済み）:

```
【甲第００１号証】
標目: 〇〇報告書
作成年月日: 令和〇年〇月〇日
作成者: 〇〇株式会社
立証趣旨: 〇〇の事実を証明する。

（本文以下…）
```

メタブロックが無いファイルは標目だけファイル名から逆算（`甲第１号証` 等）し、他は空欄になります。

## テスト

```cmd
python -m pytest backend/tests/ -v
```

合計 76 件。バックエンド全モジュール + API E2E スモークが含まれます。

## ディレクトリ

```
koshou-kanri/
├── start.bat              ワンクリック起動（Windows）
├── README.md
├── SPEC.md                仕様書（索引）
├── PROGRESS.md            実装進捗
├── backend/
│   ├── requirements.txt
│   ├── main.py            FastAPI エントリポイント
│   ├── api/               ルート定義 + Pydantic スキーマ
│   ├── core/
│   │   ├── normalizer.py  表記ゆれ正規化
│   │   ├── splitter.py    結合 → 個別 分解（vendor の薄ラッパー）
│   │   ├── combiner.py    個別 → 結合（docxcompose）
│   │   ├── list_builder.py
│   │   ├── case_parser.py
│   │   ├── table_builder.py
│   │   ├── folder_setup.py
│   │   ├── backup.py
│   │   └── vendor/
│   │       ├── split_evidence_docx.py    改変禁止スクリプト
│   │       └── split_evidence_prompt.md
│   └── tests/             pytest 一式 + fixtures 自動生成
└── frontend/
    ├── package.json
    ├── index.html
    ├── v01-UI.md          UI モック雛形（リファレンス）
    └── src/
        ├── main.jsx
        ├── App.jsx        実 API 接続版
        ├── api.js         API ラッパ
        └── index.css
```

## トラブルシュート

- **ポート競合**: `start.bat` 中の `--port 8765` と `vite.config.js` の `server.port: 5173` を変更。
  あわせて `frontend/src/api.js` の `BASE` も同期させること。
- **「ルートフォルダが存在しません」**: 入力したパスが Google Drive 同期前の可能性あり。
  実際にエクスプローラで開けるパスかを確認してから再試行してください。
- **「個別マスタが空ではありません」**: 上書きを選ぶと `_backup/<timestamp>/個別マスタ` に
  退避してから削除されます。バックアップは最新 10 世代まで保持。
- **Word の修復ダイアログが出る**: 分解スクリプトの sectPr 昇格に失敗している可能性。
  `backend/core/vendor/split_evidence_prompt.md` の「よくある落とし穴」を参照。

## ライセンス・帰属

- `backend/core/vendor/split_evidence_docx.py` はユーザ提供の改変禁止スクリプト。
- それ以外のソースは本プロジェクト用に新規実装。
