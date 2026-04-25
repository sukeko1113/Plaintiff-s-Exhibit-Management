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
- [ ] Step 5: `combiner.py` + tests
- [ ] Step 6: `list_builder.py` + 関連 API
- [ ] Step 7: `case_parser.py` + `/api/case/parse`
- [ ] Step 8: `table_builder.py` + `/api/evidence-pack`
- [ ] Step 9: `backup.py` + 全 API への組み込み
- [ ] Step 10: フロントエンド（`v01-UI.md` ベース、無ければ §13.5 フォールバック）
- [ ] Step 11: `start.bat` + README 完成

## ブロッカー

- **Step 10 着手前**（必須ではない）: `v01-UI.md` の提供。無ければ §13.5 のフォールバック UI を実装。

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
