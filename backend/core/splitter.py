"""結合甲号証 → 個別マスタへの分解（仕様 §6）。

同梱の vendor.split_evidence_docx を呼び出し、以下を追加で行う:

* 枝番（その / の / 枝）対応の正規表現を渡す
* 仮ファイル名で出力させ、全角3桁＋枝番に **リネーム**
* dry-run モード（実書き出しなし、生成予定ファイル名だけ返す）

vendor スクリプトは改変禁止。追加処理はすべて本モジュール側で行う。
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from .normalizer import koshou_sort_key
from .vendor.split_evidence_docx import split_docx

# 主番号 + 任意で枝番 を「ひとつのグループ」として捕捉する拡張パターン
# 枝番は『号証』の **後** に出現する（例: 【甲第３号証その１】）。
# vendor.split_docx は group(1) しか参照しないため、両形式を 1 グループにまとめる:
#   【甲第3号証】       → group(1) = "3"
#   【甲第3号証その1】 → group(1) = "3号証その1"
# 後段の _build_final_filename がこの2形式を解釈する。
EXTENDED_MARKER_PATTERN = (
    r'【\s*甲\s*(?:第)?\s*'
    r'([0-9０-９]{1,3}(?:\s*号\s*証\s*(?:その|の|枝)\s*[0-9０-９]+)?)'
    r'\s*(?:号\s*証)?\s*】'
)

TMP_TEMPLATE = '__tmp_甲第{id}号証.docx'

FW_TO_HW = str.maketrans('０１２３４５６７８９', '0123456789')
HW_TO_FW = str.maketrans('0123456789', '０１２３４５６７８９')


def detect_sections(input_path: Path) -> list[str]:
    """入力ファイル中のマーカーを検出し、正規化済みラベルのリストを返す（dry-run 用）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_files = split_docx(
            str(input_path), tmpdir,
            marker_pattern=EXTENDED_MARKER_PATTERN,
            filename_template=TMP_TEMPLATE,
            verbose=False,
        )
        labels = [_build_final_filename(f.name, with_extension=False) for f in tmp_files]
        return sorted(labels, key=koshou_sort_key)


def split_combined_to_master(
    input_path: Path,
    output_dir: Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> list[Path]:
    """結合甲号証ファイルを分解し、個別マスタフォルダへ保存する。

    Parameters
    ----------
    input_path : 結合甲号証.docx
    output_dir : 個別マスタフォルダ
    overwrite  : True なら既存ファイルを上書き、False なら衝突で例外
    dry_run    : True なら実書き出しなし、生成予定ファイルパスだけ返す
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        labels = detect_sections(input_path)
        return [output_dir / f'{lbl}.docx' for lbl in labels]

    tmp_files = split_docx(
        str(input_path),
        str(output_dir),
        marker_pattern=EXTENDED_MARKER_PATTERN,
        filename_template=TMP_TEMPLATE,
        verbose=False,
    )

    final_files: list[Path] = []
    try:
        for tmp in tmp_files:
            final_name = _build_final_filename(tmp.name)
            final_path = tmp.parent / final_name

            if final_path.exists() and final_path.resolve() != tmp.resolve():
                if overwrite:
                    final_path.unlink()
                else:
                    # 仮ファイルは掃除してから例外
                    for leftover in tmp_files:
                        if leftover.exists():
                            leftover.unlink()
                    raise FileExistsError(
                        f'既存ファイルがあります: {final_path}'
                    )

            tmp.rename(final_path)
            final_files.append(final_path)
    except Exception:
        # 途中失敗時の片付け
        for leftover in tmp_files:
            if leftover.exists() and leftover not in final_files:
                try:
                    leftover.unlink()
                except OSError:
                    pass
        raise

    final_files.sort(key=lambda p: koshou_sort_key(p.stem))
    return final_files


def _build_final_filename(tmp_name: str, *, with_extension: bool = True) -> str:
    """仮ファイル名 '__tmp_甲第{id}号証.docx' から、
    全角3桁＋枝番形式 '甲第００１号証[その１].docx' を組み立てる。
    """
    # 枝番付きの場合、id 部分に "号証" が混入する（例: __tmp_甲第3号証その1号証.docx）。
    # 末尾の '号証.docx' を貪欲マッチさせて、group(1) に "3" or "3号証その1" を取り出す。
    m = re.match(r'__tmp_甲第(.+)号証\.docx$', tmp_name)
    if not m:
        raise ValueError(f'予期せぬ仮ファイル名: {tmp_name}')

    raw = m.group(1).translate(FW_TO_HW)
    mm = re.match(
        r'^\s*([0-9]+)\s*(?:号\s*証\s*(?:その|の|枝)\s*([0-9]+))?\s*$', raw
    )
    if not mm:
        raise ValueError(f'仮IDのパースに失敗: {raw}')

    main_num = int(mm.group(1))
    if not (1 <= main_num <= 999):
        raise ValueError(f'主番号が範囲外: {main_num}')
    main_fw = str(main_num).zfill(3).translate(HW_TO_FW)

    if mm.group(2):
        branch_fw = str(int(mm.group(2))).translate(HW_TO_FW)
        base = f'甲第{main_fw}号証その{branch_fw}'
    else:
        base = f'甲第{main_fw}号証'

    return base + '.docx' if with_extension else base
