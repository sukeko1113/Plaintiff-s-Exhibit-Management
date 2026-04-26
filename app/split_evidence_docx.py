#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_evidence_docx.py — 結合甲号証(乙号証等)Wordファイルの分割ツール
==================================================================

1つのWord文書(.docx)に【甲第XX号証】等のマーカーで区切られた複数の文書
が結合されている場合、これを各マーカーごとに個別の.docxファイルへ分割する。

特徴
----
* Python標準ライブラリ(zipfile, re等)のみを使用。外部依存なし。
* 元の書式・画像・表・ヘッダー/フッター・スタイル等をすべてそのまま保持。
* マーカーパターンと出力ファイル名はカスタマイズ可能。
  - 甲号証 ⇒ 乙号証, 丙号証, あるいは「別紙第N号」等にも適用可能。

使い方
-----
コマンドライン:
    python -m app.split_evidence_docx 結合ファイル.docx 出力フォルダ/

    # 乙号証用にカスタマイズ:
    python -m app.split_evidence_docx 結合乙.docx out/ \\
        --pattern '【\\s*乙\\s*第\\s*([0-9０-９]+)\\s*号\\s*証\\s*】' \\
        --filename '乙第{id:0>2}号証.docx'

Pythonコードから:
    from app.split_evidence_docx import split_docx
    split_docx('結合ファイル.docx', './出力/')

ロジック概要
-----------
.docxファイルはZIPアーカイブで、本文は word/document.xml に格納される。
本文 <w:body> の直下に <w:p>(段落)・<w:tbl>(表)・<w:sectPr>(セクション設定)
が並んでおり、これらが「トップレベル要素」となる。

[アルゴリズム]
1. .docxを ZIP として開き、word/document.xml を読み込む。
2. <w:body> 内のトップレベル要素を順に走査する。
3. テキスト内容に【甲第XX号証】を含む段落の位置をすべて記録する。
4. body末尾の <w:sectPr> (body-level sectPr) を別途取り出す。
5. N番目のマーカー段落から、N+1番目のマーカー段落の直前までを「1つの甲号証」
   とみなして切り出す。
6. 各セクション末尾の段落に <w:sectPr> が埋め込まれている場合(セクション区切り)、
   それを段落の <w:pPr> から取り出して body 直下に「昇格」させる。
   - これによって、各分割ファイルに有効な末尾 sectPr が必ず1つ存在する状態にする。
   - 最後のマーカーのセクションは元の body-level sectPr をそのまま使用する。
7. 各セクションごとに、document.xml だけを差し替えた新しい.docx(ZIP)を作成。
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path
from typing import Iterable

# -------------------------------------------------------------------
# デフォルト設定
# -------------------------------------------------------------------

# 【甲第XX号証】 をマッチする正規表現。
# 第1グループに主番号、第2グループ(任意)に枝番を捕捉する。
DEFAULT_MARKER_PATTERN = (
    r'【\s*甲\s*第?\s*([0-9０-９]+)\s*号\s*証'
    r'(?:\s*その\s*([0-9０-９]+))?\s*】'
)

# 出力ファイル名のテンプレート。{id} に主番号(全角3桁ゼロ詰め) が入る。
# {branch} は枝番(全角、ゼロ詰めなし)、無い場合は空文字。
DEFAULT_FILENAME_TEMPLATE = '甲第{id}号証{branch_suffix}.docx'

FALLBACK_BODY_SECTPR = (
    '    <w:sectPr>'
    '<w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="567" w:right="567" w:bottom="567" w:left="567" '
    'w:header="0" w:footer="0" w:gutter="0"/>'
    '<w:cols w:space="720"/>'
    '</w:sectPr>'
)


# -------------------------------------------------------------------
# ユーティリティ
# -------------------------------------------------------------------

ZEN2HAN_DIGITS = str.maketrans('０１２３４５６７８９', '0123456789')
HAN2ZEN_DIGITS = str.maketrans('0123456789', '０１２３４５６７８９')


def _to_int(num_str: str) -> int:
    return int(num_str.translate(ZEN2HAN_DIGITS))


def _normalize_main_id(id_str: str, width: int = 3) -> str:
    """主番号を全角3桁ゼロ埋めの全角数字に正規化。"""
    n = _to_int(id_str)
    return str(n).zfill(width).translate(HAN2ZEN_DIGITS)


def _normalize_branch_id(id_str: str | None) -> str:
    """枝番を全角(ゼロ詰めなし)に変換。None なら空文字。"""
    if id_str is None or id_str == '':
        return ''
    return str(_to_int(id_str)).translate(HAN2ZEN_DIGITS)


def _find_top_level_spans(body_xml: str) -> list[dict]:
    """
    <w:body> 内のトップレベル要素 (<w:p>, <w:tbl>, <w:sectPr>) のスパンを返す。

    スタックベースのXMLスキャナで、ネストの深さが0に戻った時点を要素境界とする。
    """
    spans: list[dict] = []
    stack: list[tuple[str, int]] = []
    pos = 0
    tag_re = re.compile(r'<(/?)([A-Za-z][\w:.-]*)\b([^<>]*?)(/?)>', re.DOTALL)

    while pos < len(body_xml):
        m = tag_re.search(body_xml, pos)
        if not m:
            break
        is_close = (m.group(1) == '/')
        tag_name = m.group(2)
        is_self_closing = (m.group(4) == '/')

        if is_close:
            if stack and stack[-1][0] == tag_name:
                _, start = stack.pop()
                if not stack:
                    spans.append({
                        'tag': tag_name,
                        'start': start,
                        'end': m.end(),
                        'xml': body_xml[start:m.end()],
                    })
        elif is_self_closing:
            if not stack:
                spans.append({
                    'tag': tag_name,
                    'start': m.start(),
                    'end': m.end(),
                    'xml': body_xml[m.start():m.end()],
                })
        else:
            stack.append((tag_name, m.start()))

        pos = m.end()

    return spans


def _extract_paragraph_text(paragraph_xml: str) -> str:
    """段落XMLから、表示テキスト(全 <w:t> の連結)を取り出す。"""
    return ''.join(re.findall(r'<w:t\b[^>]*>([^<]*)</w:t>', paragraph_xml))


def _promote_embedded_sectpr(section_xml: str) -> tuple[str, str | None]:
    """
    section_xml の中の最後の <w:sectPr> (= 段落 pPr に埋め込まれたセクション区切り)
    を見つけ、それを除いた section_xml と、body直下に置けるよう成形した sectPr XML
    を返す。見つからなければ (section_xml, None)。
    """
    pat = re.compile(r'<w:sectPr\b[^>]*>.*?</w:sectPr>', re.DOTALL)
    matches = list(pat.finditer(section_xml))
    if not matches:
        pat2 = re.compile(r'<w:sectPr\b[^/>]*/>')
        matches2 = list(pat2.finditer(section_xml))
        if not matches2:
            return section_xml, None
        last = matches2[-1]
    else:
        last = matches[-1]

    sectpr_xml = last.group(0)
    cleaned = section_xml[:last.start()] + section_xml[last.end():]
    cleaned = re.sub(r'\n\s*(\n)', r'\1', cleaned)
    return cleaned, '    ' + sectpr_xml.strip()


# -------------------------------------------------------------------
# メイン関数
# -------------------------------------------------------------------

def split_docx(
    input_path: str | Path,
    output_dir: str | Path,
    marker_pattern: str = DEFAULT_MARKER_PATTERN,
    filename_template: str = DEFAULT_FILENAME_TEMPLATE,
    verbose: bool = True,
) -> list[Path]:
    """
    結合 docx を分割し、生成したファイルパスのリストを返す。

    Parameters
    ----------
    input_path : 入力 .docx
    output_dir : 出力フォルダ(無ければ作成)
    marker_pattern : 区切りマーカーの正規表現。
        グループ 1 に主番号、グループ 2 (任意) に枝番を捕捉すること。
    filename_template : 出力ファイル名のテンプレート。
        利用可能なプレースホルダ: {id} (主番号 全角3桁), {branch} (枝番 全角),
        {branch_suffix} (枝番がある場合 'そのＮ'、無ければ空文字)。
    verbose : 進捗を標準出力に表示する。
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(input_path, 'r') as zf:
        original_files: dict[str, bytes] = {n: zf.read(n) for n in zf.namelist()}
        original_infos = {info.filename: info for info in zf.infolist()}

    if 'word/document.xml' not in original_files:
        raise ValueError("有効な docx ではありません: word/document.xml が見つかりません。")

    doc_xml = original_files['word/document.xml'].decode('utf-8')

    m = re.search(r'(<w:body\b[^>]*>)(.*)(</w:body>)', doc_xml, re.DOTALL)
    if not m:
        raise ValueError("<w:body> が document.xml に見つかりません。")
    pre_body = doc_xml[:m.end(1)]
    body_inner = m.group(2)
    post_body = doc_xml[m.start(3):]

    spans = _find_top_level_spans(body_inner)

    body_level_sectpr_xml: str | None = None
    last_idx_for_content = len(spans)
    if spans and spans[-1]['tag'] == 'w:sectPr':
        body_level_sectpr_xml = spans[-1]['xml']
        last_idx_for_content = len(spans) - 1

    marker_re = re.compile(marker_pattern)
    section_anchors: list[tuple[int, str, str]] = []  # (span_idx, main_id, branch_id)
    for i, span in enumerate(spans[:last_idx_for_content]):
        if span['tag'] != 'w:p':
            continue
        text = _extract_paragraph_text(span['xml'])
        mm = marker_re.search(text)
        if mm:
            main_id = _normalize_main_id(mm.group(1))
            branch_id = ''
            if mm.lastindex and mm.lastindex >= 2:
                branch_id = _normalize_branch_id(mm.group(2))
            section_anchors.append((i, main_id, branch_id))

    if not section_anchors:
        first_text = _extract_paragraph_text(spans[0]['xml']) if spans else '(空)'
        raise ValueError(
            f"マーカーが見つかりません。pattern={marker_pattern!r}\n"
            f"document.xml の冒頭テキスト: {first_text}"
        )

    if verbose:
        print(f"検出: {len(section_anchors)} 件のセクション")
        for _, mid, bid in section_anchors:
            label = f"第{mid}号証" + (f"その{bid}" if bid else "")
            print(f"  - {label}")

    output_files: list[Path] = []

    for n, (start_idx, main_id, branch_id) in enumerate(section_anchors):
        is_last = (n == len(section_anchors) - 1)
        end_idx = section_anchors[n + 1][0] if not is_last else last_idx_for_content

        section_spans = spans[start_idx:end_idx]
        if not section_spans:
            continue

        section_xml = body_inner[section_spans[0]['start']:section_spans[-1]['end']]

        if is_last and body_level_sectpr_xml is not None:
            section_clean = section_xml
            tail_sectpr = body_level_sectpr_xml
        else:
            section_clean, tail_sectpr = _promote_embedded_sectpr(section_xml)
            if tail_sectpr is None:
                tail_sectpr = body_level_sectpr_xml or FALLBACK_BODY_SECTPR

        new_body = '\n' + section_clean.rstrip() + '\n' + tail_sectpr + '\n  '
        new_doc_xml = pre_body + new_body + post_body

        new_files = dict(original_files)
        new_files['word/document.xml'] = new_doc_xml.encode('utf-8')

        branch_suffix = f"その{branch_id}" if branch_id else ""
        out_filename = filename_template.format(
            id=main_id,
            branch=branch_id,
            branch_suffix=branch_suffix,
        )
        out_path = output_dir / out_filename
        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name, data in new_files.items():
                info = original_infos.get(name)
                if info is not None:
                    zi = zipfile.ZipInfo(filename=name, date_time=info.date_time)
                    zi.compress_type = info.compress_type
                    zf.writestr(zi, data)
                else:
                    zf.writestr(name, data)

        if verbose:
            size = out_path.stat().st_size
            print(f"  - 出力: {out_path.name} ({size:,} bytes)")
        output_files.append(out_path)

    return output_files


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description='結合された甲号証 docx ファイルを各マーカーごとに分割します。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('input', help='入力 .docx ファイル')
    p.add_argument('output_dir', help='出力フォルダ')
    p.add_argument('--pattern', default=DEFAULT_MARKER_PATTERN,
                   help='マーカー正規表現(g1=主番号, g2=枝番任意)')
    p.add_argument('--filename', default=DEFAULT_FILENAME_TEMPLATE,
                   help='出力ファイル名テンプレート({id}/{branch}/{branch_suffix})')
    p.add_argument('-q', '--quiet', action='store_true', help='ログを抑制')
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    try:
        split_docx(
            args.input, args.output_dir,
            marker_pattern=args.pattern,
            filename_template=args.filename,
            verbose=(not args.quiet),
        )
    except Exception as e:
        print(f'エラー: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
