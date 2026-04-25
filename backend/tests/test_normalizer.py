"""仕様 §5.4 必須テストケース。"""

from __future__ import annotations

import pytest

from backend.core.normalizer import (
    display_label,
    koshou_sort_key,
    normalize_koshou,
)


TEST_CASES = [
    ('甲第 1号証', '甲第００１号証'),
    ('甲第０1号証', '甲第００１号証'),
    ('甲第 12号証', '甲第０１２号証'),
    ('甲第１２号証', '甲第０１２号証'),
    ('甲01号証', '甲第００１号証'),
    ('甲第1号証', '甲第００１号証'),
    ('甲第０１２号証その１', '甲第０１２号証その１'),
    ('甲第12号証その3', '甲第０１２号証その３'),
    ('甲第１号証の2', '甲第００１号証その２'),
    ('参考: 甲第5号証 を引用', '甲第００５号証'),
    ('【甲第１号証】', '甲第００１号証'),
    ('【甲第０１２号証その１】', '甲第０１２号証その１'),
    ('普通の文章です', None),
    ('甲第000号証', None),  # 0 番は無効
]


@pytest.mark.parametrize('text, expected', TEST_CASES)
def test_normalize_koshou(text, expected):
    assert normalize_koshou(text) == expected


def test_sort_order():
    labels = [
        '甲第００３号証その２',
        '甲第００１号証',
        '甲第００３号証',
        '甲第００２号証',
        '甲第００３号証その１',
        '甲第００４号証',
    ]
    sorted_labels = sorted(labels, key=koshou_sort_key)
    assert sorted_labels == [
        '甲第００１号証',
        '甲第００２号証',
        '甲第００３号証',
        '甲第００３号証その１',
        '甲第００３号証その２',
        '甲第００４号証',
    ]


def test_sort_key_invalid_goes_last():
    labels = ['不正データ', '甲第００１号証']
    assert sorted(labels, key=koshou_sort_key) == ['甲第００１号証', '不正データ']


@pytest.mark.parametrize('normalized, expected', [
    ('甲第００１号証', '甲第1号証'),
    ('甲第０１２号証', '甲第12号証'),
    ('甲第０１２号証その１', '甲第12号証の1'),
    ('甲第０９９号証その１２', '甲第99号証の12'),
])
def test_display_label(normalized, expected):
    assert display_label(normalized) == expected


def test_normalize_empty():
    assert normalize_koshou('') is None
    assert normalize_koshou(None) is None  # type: ignore[arg-type]
