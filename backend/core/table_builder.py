"""証拠説明書テーブル生成（仕様 §9）。

メタデータ取得は **本文先頭メタブロック方式** を採用（ユーザ確認済み）。
個別マスタ .docx の冒頭に下記の形式でメタを書いておくと、自動で抽出される:

    【甲第００１号証】
    標目: 〇〇報告書
    作成年月日: 令和〇年〇月〇日
    作成者: 〇〇株式会社
    立証趣旨: 〇〇の事実を証明する。

    （本文以下…）

メタブロックが無いファイルは標目をファイル名から逆算（例: 甲第００１号証）し、
他は空欄でフォールバックする。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.document import Document as DocxDocument

from .normalizer import display_label, normalize_koshou


# サポートするメタキー（仕様 §9.1 の列構成）
_META_KEYS = ['標目', '作成年月日', '作成者', '立証趣旨']

_META_LINE_RE = re.compile(
    r'^\s*(' + '|'.join(_META_KEYS) + r')\s*[:：]\s*(.*?)\s*$'
)

_TABLE_HEADERS = ['号証', '標目', '作成年月日', '作成者', '立証趣旨']


def parse_metadata(individual_docx: Path) -> dict[str, str]:
    """個別マスタ .docx の冒頭メタブロックを解析。

    冒頭から空段落 / マーカー段落を除いて連続する数段落を走査し、
    `キー: 値` の形式に合致する行を辞書化する。
    最初のキーでない段落で打ち切る。
    """
    doc = Document(str(individual_docx))
    meta: dict[str, str] = {}
    started = False
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            if started:
                break
            continue
        # 先頭の【甲第〇号証】マーカー段落はスキップ
        if not started and normalize_koshou(text) and text.startswith('【'):
            continue

        m = _META_LINE_RE.match(text)
        if m:
            started = True
            key = m.group(1)
            val = m.group(2).strip()
            meta.setdefault(key, val)
            continue

        if started:
            # メタブロックが終わった
            break
        # メタブロックが始まる前の本文段落 → メタなしと判定
        break
    return meta


def _resolve_metadata(
    file_path: Path,
    metadata_map: dict[str, dict] | None,
) -> dict[str, str]:
    """1 ファイル分のメタデータを解決する。

    優先順位:
    1. metadata_map で明示指定されたもの（API/UI から渡される）
    2. ファイル本文のメタブロック
    3. 空欄（標目だけはファイル名から表示形にフォールバック）
    """
    label = normalize_koshou(file_path.stem) or file_path.stem
    base: dict[str, str] = {k: '' for k in _META_KEYS}

    parsed = parse_metadata(file_path)
    base.update(parsed)

    if metadata_map and label in metadata_map:
        for k, v in metadata_map[label].items():
            if v:
                base[k] = v

    if not base['標目']:
        base['標目'] = display_label(label)
    return base


def build_summary_doc(
    individual_files: Iterable[Path],
    metadata_map: dict[str, dict] | None = None,
) -> DocxDocument:
    """証拠説明書テーブルを先頭に持つ Document を返す。

    返した Document は docxcompose.Composer の master_doc として使う。
    """
    doc = Document()
    doc.add_heading('証拠説明書', level=1)

    files = list(individual_files)
    table = doc.add_table(rows=1 + len(files), cols=len(_TABLE_HEADERS))
    table.style = 'Table Grid'

    header_cells = table.rows[0].cells
    for i, h in enumerate(_TABLE_HEADERS):
        header_cells[i].text = h

    for row_idx, f in enumerate(files, start=1):
        f = Path(f)
        label = normalize_koshou(f.stem) or f.stem
        meta = _resolve_metadata(f, metadata_map)
        cells = table.rows[row_idx].cells
        cells[0].text = display_label(label)
        cells[1].text = meta['標目']
        cells[2].text = meta['作成年月日']
        cells[3].text = meta['作成者']
        cells[4].text = meta['立証趣旨']

    doc.add_page_break()
    return doc


def preview_metadata(individual_files: Iterable[Path]) -> list[dict]:
    """API /api/master/table 用: 各ファイルの解決済みメタを返す。"""
    rows: list[dict] = []
    for f in individual_files:
        f = Path(f)
        label = normalize_koshou(f.stem) or f.stem
        meta = _resolve_metadata(f, None)
        rows.append({
            'file': f.name,
            'label': label,
            'display_label': display_label(label),
            **meta,
        })
    return rows
