"""個別マスタ → 結合甲号証への結合（仕様 §7）。

- python-docx 単体は結合で書式が壊れるため、必ず docxcompose を使う
- 入力ファイルは番号順に並べ替えてから結合
- add_summary_table=True の場合、先頭に証拠説明書テーブルを挿入する
  （table_builder は循環インポート回避のため遅延インポート）
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docxcompose.composer import Composer

from .normalizer import koshou_sort_key


def combine_to_evidence_pack(
    individual_files: list[Path],
    output_path: Path,
    *,
    add_summary_table: bool = False,
    metadata_map: dict[str, dict] | None = None,
) -> Path:
    """個別マスタ群を、番号順に結合した 1 つの .docx を出力する。

    Parameters
    ----------
    individual_files  : 結合する個別マスタ .docx のリスト
    output_path       : 出力先 .docx
    add_summary_table : True の場合、先頭に証拠説明書テーブルを挿入
    metadata_map      : ラベル→メタデータ辞書（add_summary_table=True のとき使用）
    """
    sorted_files = sorted(individual_files, key=lambda p: koshou_sort_key(Path(p).stem))
    if not sorted_files:
        raise ValueError('結合対象ファイルが空です')

    if add_summary_table:
        from . import table_builder  # 遅延インポート（循環防止）

        master_doc = table_builder.build_summary_doc(sorted_files, metadata_map)
        files_to_append = sorted_files
    else:
        master_doc = Document(str(sorted_files[0]))
        files_to_append = sorted_files[1:]

    composer = Composer(master_doc)
    for f in files_to_append:
        composer.append(Document(str(f)))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    composer.save(str(output_path))
    return output_path
