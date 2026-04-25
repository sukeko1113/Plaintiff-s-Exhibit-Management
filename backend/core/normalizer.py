"""甲号証ラベルの表記ゆれ正規化モジュール（最重要）。

仕様書 §5 に従い、`甲第<全角3桁>号証[その<全角>]` 形式へ変換する。
"""
from __future__ import annotations

import re
from typing import Optional

FULLWIDTH_TO_HALFWIDTH = str.maketrans('０１２３４５６７８９', '0123456789')
HALFWIDTH_TO_FULLWIDTH = str.maketrans('0123456789', '０１２３４５６７８９')

_BODY = (
    r'甲\s*(?:第)?\s*([0-9０-９]{1,3})\s*号証'
    r'(?:\s*(?:その|の|枝)\s*([0-9０-９]+))?'
)

KOSHOU_PATTERN = re.compile(_BODY)
KOSHOU_STRICT_PATTERN = re.compile(r'^\s*' + _BODY + r'\s*[。．\.]?\s*$')

# 段落の前後に付き得る装飾的な括弧（【】や []）を取り除くための補助パターン。
# 「【甲第１号証】」のような表記を strict マッチさせるために使う。
_STRIP_BRACKETS_PATTERN = re.compile(r'^\s*(?:【\s*(.*?)\s*】|\[\s*(.*?)\s*\])\s*$')


def _to_fullwidth_padded(num: int, width: int = 3) -> str:
    return str(num).zfill(width).translate(HALFWIDTH_TO_FULLWIDTH)


def _to_fullwidth(num: int) -> str:
    return str(num).translate(HALFWIDTH_TO_FULLWIDTH)


def _format(main_num: int, branch_num: Optional[int]) -> str:
    label = f'甲第{_to_fullwidth_padded(main_num)}号証'
    if branch_num is not None and branch_num > 0:
        label += f'その{_to_fullwidth(branch_num)}'
    return label


def parse_match(match: re.Match) -> Optional[str]:
    main_raw = match.group(1).translate(FULLWIDTH_TO_HALFWIDTH)
    try:
        main_num = int(main_raw)
    except ValueError:
        return None
    if not (1 <= main_num <= 999):
        return None

    branch_num: Optional[int] = None
    if match.group(2):
        branch_raw = match.group(2).translate(FULLWIDTH_TO_HALFWIDTH)
        try:
            branch_num = int(branch_raw)
        except ValueError:
            return None
        if branch_num <= 0:
            return None

    return _format(main_num, branch_num)


def normalize_koshou(text: str) -> Optional[str]:
    """文字列から最初に現れる甲号証ラベルを抽出して正規化する。

    マッチしなければ ``None``。本文中の言及からも抽出するため、文中検索版。
    """
    if not text:
        return None
    match = KOSHOU_PATTERN.search(text)
    if match is None:
        return None
    return parse_match(match)


def normalize_koshou_strict(text: str) -> Optional[str]:
    """段落全体が甲号証ラベルそのものの場合のみ正規化形を返す。

    末尾に句点（``。``、``．``、``.``）が付いている場合は許容する。
    全体が ``【…】`` ないし ``[…]`` で囲まれている場合は括弧を取り除いてからマッチを試みる。
    本文中の言及（``…甲第3号証を参照…``）はマッチしない。
    """
    if not text:
        return None
    bracket_match = _STRIP_BRACKETS_PATTERN.match(text)
    if bracket_match is not None:
        inner = bracket_match.group(1) or bracket_match.group(2) or ''
        text = inner
    match = KOSHOU_STRICT_PATTERN.match(text)
    if match is None:
        return None
    return parse_match(match)


_SORT_KEY_PATTERN = re.compile(r'^甲第([０-９]{3})号証(?:その([０-９]+))?$')


def koshou_sort_key(label: str) -> tuple[int, int]:
    """正規化済みラベルからソート用のキーを返す。

    本体番号で昇順、同一本体番号内では枝番昇順（枝なしは 0 として最初に来る）。
    """
    match = _SORT_KEY_PATTERN.match(label)
    if match is None:
        return (10**9, 10**9)
    main_num = int(match.group(1).translate(FULLWIDTH_TO_HALFWIDTH))
    branch_num = 0
    if match.group(2):
        branch_num = int(match.group(2).translate(FULLWIDTH_TO_HALFWIDTH))
    return (main_num, branch_num)


def label_to_filename(label: str) -> str:
    """正規化済みラベルからファイル名（拡張子付き）を作る。"""
    return f'{label}.docx'


def filename_to_label(filename: str) -> Optional[str]:
    """ファイル名から正規化ラベルを取り出す。失敗したら ``None``。"""
    stem = filename
    for ext in ('.docx', '.DOCX'):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    return normalize_koshou_strict(stem)
