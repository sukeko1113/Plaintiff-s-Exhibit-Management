# 実装進捗

仕様書 §17 の推奨順序に従って実装する。各ステップ完了時に動作する状態でコミット。

## ユーザ確認済み事項

- §0.1 同梱ファイル (`split_evidence_docx.py`, `v01-UI.md`): **ユーザが追加で提供する**
- §9.2 メタデータ取得方法: **本文先頭メタブロック方式**
- コミット粒度: **§17 のステップ毎に随時**

## ステップ進捗

- [x] Step 1: プロジェクト雛形（ディレクトリ・requirements.txt・package.json）
- [x] Step 2: `normalizer.py` + `tests/test_normalizer.py`（§5.4 全 14 ケース + 追加テスト）
- [x] Step 3: `folder_setup.py` + `main.py` + `/api/setup`
- [x] Step 4: `vendor/split_evidence_docx.py` 配置 + `splitter.py` + `tests/test_splitter.py`（8 件パス）
- [x] Step 5: `combiner.py` + `tests/test_combiner.py`（5 件パス）
- [x] Step 6: `list_builder.py` + `tests/test_list_builder.py`（7 件パス）+ 関連 API
- [x] Step 7: `case_parser.py` + `tests/test_case_parser.py`（5 件パス）+ `/api/case/parse`
- [x] Step 8: `table_builder.py` + `tests/test_table_builder.py`（7 件パス）+ `/api/evidence-pack`
- [x] Step 9: `backup.py` + `tests/test_backup.py`（8 件パス）。split / list 系で組み込み済み
- [x] Step 9.5: 全 API ルート実装 + `tests/test_api.py`（10 件パス、TestClient による E2E スモーク）
- [x] Step 10: フロントエンド（`v01-UI.md` ベース、`api.js` で実 API 接続、Vite ビルド確認済み）
- [x] Step 11: `start.bat` + README 完成

**現在のテスト総数: 76 件全パス。Vite production build 成功。**

## ブロッカー

なし（全ステップ完了）。

## Step 4 補足: マーカー正規表現

vendor `split_evidence_docx.py` は改変禁止のため、splitter 側で枝番に対応した拡張パターン
`EXTENDED_MARKER_PATTERN` を渡している。`【甲第3号証その1】` 形式（号証の **後** に枝番）
を group(1) に丸ごと取り込むため、group(1) は次の 2 形式となる:

| マーカー         | group(1) | 仮ファイル名                          |
| ---------------- | -------- | ------------------------------------- |
| 【甲第3号証】    | `3`      | `__tmp_甲第3号証.docx`                |
| 【甲第3号証その1】| `3号証その1` | `__tmp_甲第3号証その1号証.docx`   |

`_build_final_filename` がこの 2 形式を解釈して全角3桁に正規化する。

## テスト実行コマンド

```bash
cd backend
pip install -r requirements.txt
cd ..
python -m pytest backend/tests/ -v
```
