"""甲号証ラベルの表記ゆれ正規化モジュール（最重要）。

仕様書 v02 §5 に従い、`甲第<全角3桁>号証[その<全角>]` 形式へ変換する。
隅付き括弧 【...】 が付いた表記も剥がして同じラベルへ正規化する。
"""
from __future__ import annotations

import re
from typing import Optional

FULLWIDTH_TO_HALFWIDTH = str.maketrans('０１２３４５６７８９', '0123456789')
HALFWIDTH_TO_FULLWIDTH = str.maketrans('0123456789', '０１２３４５６７８９')

# 文中抽出用：【】の有無は問わず本体だけ捕捉する
_BODY = (
    r'甲\s*(?:第)?\s*([0-9０-９]{1,3})\s*号証'
    r'(?:\s*(?:その|の|枝)\s*([0-9０-９]+))?'
)

KOSHOU_PATTERN = re.compile(_BODY)

# 段落全体マッチ：前後の括弧・空白・句点を許容
KOSHOU_STRICT_PATTERN = re.compile(
    r'^\s*【?\s*' + _BODY + r'\s*】?\s*[。．\.]?\s*$'
)

# 区切りマーカー：v02 §6.5
MARKER_BRACKETED_PATTERN = re.compile(
    r'^\s*【\s*甲\s*(?:第)?\s*[0-9０-９]{1,3}\s*号証'
    r'(?:\s*(?:その|の|枝)\s*[0-9０-９]+)?\s*】\s*$'
)
MARKER_BARE_STRICT_PATTERN = re.compile(
    r'^\s*甲\s*(?:第)?\s*[0-9０-９]{1,3}\s*号証'
    r'(?:\s*(?:その|の|枝)\s*[0-9０-９]+)?\s*$'
)


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
    """文字列から最初に現れる甲号証ラベルを抽出して正規化する（隅付き括弧も剥がす）。"""
    if not text:
        return None
    match = KOSHOU_PATTERN.search(text)
    if match is None:
        return None
    return parse_match(match)


def normalize_koshou_strict(text: str) -> Optional[str]:
    """段落全体が甲号証ラベル（前後の【】・空白・句点を許容）の場合のみ正規化形を返す。"""
    if not text:
        return None
    match = KOSHOU_STRICT_PATTERN.match(text)
    if match is None:
        return None
    return parse_match(match)


def is_bracketed_marker(text: str) -> bool:
    """段落テキストが 【甲第xxx号証】 形式の区切りマーカーか。"""
    if not text:
        return False
    return MARKER_BRACKETED_PATTERN.match(text) is not None


def is_bare_marker(text: str) -> bool:
    """段落テキストが括弧なしの単独行マーカーか（フォールバック判定用）。"""
    if not text:
        return False
    return MARKER_BARE_STRICT_PATTERN.match(text) is not None


_SORT_KEY_PATTERN = re.compile(r'^甲第([０-９]{3})号証(?:その([０-９]+))?$')


def koshou_sort_key(label: str) -> tuple[int, int]:
    match = _SORT_KEY_PATTERN.match(label)
    if match is None:
        return (10**9, 10**9)
    main_num = int(match.group(1).translate(FULLWIDTH_TO_HALFWIDTH))
    branch_num = 0
    if match.group(2):
        branch_num = int(match.group(2).translate(FULLWIDTH_TO_HALFWIDTH))
    return (main_num, branch_num)


def label_to_filename(label: str) -> str:
    return f'{label}.docx'


def filename_to_label(filename: str) -> Optional[str]:
    stem = filename
    for ext in ('.docx', '.DOCX'):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    return normalize_koshou_strict(stem)
