"""甲号証ラベルの表記ゆれ正規化。

仕様 §5 を実装。すべて「全角3桁 + 任意の枝番（その + 全角数字）」の形式に統一する。
ファイル名・本文テキスト・甲号証リスト・案件ファイル抽出すべてで本モジュールを使う。
"""

from __future__ import annotations

import re

# 主番号 + 任意で枝番 を捕捉する正規表現
# group 1: 主番号（半角 or 全角の数字 1〜3 桁）
# group 2: 枝番（半角 or 全角の数字、省略可）
KOSHOU_PATTERN = re.compile(
    r'【?\s*甲\s*(?:第)?\s*'
    r'([0-9０-９]{1,3})'
    r'\s*号\s*証'
    r'(?:\s*(?:その|の|枝)\s*([0-9０-９]+))?'
    r'\s*】?'
)

FW_TO_HW = str.maketrans('０１２３４５６７８９', '0123456789')
HW_TO_FW = str.maketrans('0123456789', '０１２３４５６７８９')


def normalize_koshou(text: str) -> str | None:
    """文字列中から甲号証表記を 1 件抽出し、正規化形を返す。

    マッチしない / 主番号が範囲外（1〜999 以外）の場合は None。
    """
    if not text:
        return None
    m = KOSHOU_PATTERN.search(text)
    if not m:
        return None

    main_num = int(m.group(1).translate(FW_TO_HW))
    if not (1 <= main_num <= 999):
        return None

    main_fw = str(main_num).zfill(3).translate(HW_TO_FW)
    result = f'甲第{main_fw}号証'

    if m.group(2):
        branch_num = int(m.group(2).translate(FW_TO_HW))
        branch_fw = str(branch_num).translate(HW_TO_FW)
        result += f'その{branch_fw}'

    return result


_SORT_KEY_PATTERN = re.compile(r'甲第([０-９]{3})号証(?:その([０-９]+))?')


def koshou_sort_key(label: str) -> tuple[int, int]:
    """正規化済みラベルからソートキーを返す。枝なし → 枝1 → 枝2…の順。"""
    m = _SORT_KEY_PATTERN.match(label)
    if not m:
        return (10**6, 10**6)
    main = int(m.group(1).translate(FW_TO_HW))
    branch = int(m.group(2).translate(FW_TO_HW)) if m.group(2) else 0
    return (main, branch)


def display_label(normalized: str) -> str:
    """正規化済みラベル → 表示用（半角・最小桁・枝番は「の」）に変換。

    例: '甲第００１号証'        → '甲第1号証'
        '甲第０１２号証その１'  → '甲第12号証の1'
    """
    m = _SORT_KEY_PATTERN.match(normalized)
    if not m:
        return normalized
    main = int(m.group(1).translate(FW_TO_HW))
    if m.group(2):
        branch = int(m.group(2).translate(FW_TO_HW))
        return f'甲第{main}号証の{branch}'
    return f'甲第{main}号証'
