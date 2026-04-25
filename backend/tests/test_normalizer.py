"""normalizer.py のユニットテスト（仕様書 §5.4）。"""
from __future__ import annotations

import pytest

from backend.core.normalizer import (
    filename_to_label,
    koshou_sort_key,
    label_to_filename,
    normalize_koshou,
    normalize_koshou_strict,
)


@pytest.mark.parametrize(
    'text,expected',
    [
        ('甲第 1号証', '甲第００１号証'),
        ('甲第０1号証', '甲第００１号証'),
        ('甲第 12号証', '甲第０１２号証'),
        ('甲第１２号証', '甲第０１２号証'),
        ('甲01号証', '甲第００１号証'),
        ('甲第1号証', '甲第００１号証'),
        ('甲第０１２号証その１', '甲第０１２号証その１'),
        ('甲第12号証その3', '甲第０１２号証その３'),
        ('甲第１号証の2', '甲第００１号証その２'),
        ('甲第1号証枝1', '甲第００１号証その１'),
        ('参考: 甲第5号証 を引用', '甲第００５号証'),
        ('甲第123号証', '甲第１２３号証'),
        ('甲999号証', '甲第９９９号証'),
    ],
)
def test_normalize_koshou_positive(text: str, expected: str) -> None:
    assert normalize_koshou(text) == expected


@pytest.mark.parametrize(
    'text',
    [
        '普通の文章です',
        '',
        None,
        '甲第0号証',
        '甲第1000号証',
    ],
)
def test_normalize_koshou_negative(text) -> None:
    assert normalize_koshou(text) is None


@pytest.mark.parametrize(
    'text,expected',
    [
        ('甲第００１号証', '甲第００１号証'),
        ('  甲第１号証  ', '甲第００１号証'),
        ('甲第１号証その２', '甲第００１号証その２'),
        ('甲第１号証。', '甲第００１号証'),
        ('甲第１号証．', '甲第００１号証'),
        ('【甲第１号証】', '甲第００１号証'),
        ('【甲第 １号証】', '甲第００１号証'),
        ('【甲第２号証その１】', '甲第００２号証その１'),
        ('  【甲第３号証】  ', '甲第００３号証'),
        ('[甲第４号証]', '甲第００４号証'),
    ],
)
def test_normalize_koshou_strict_positive(text: str, expected: str) -> None:
    assert normalize_koshou_strict(text) == expected


@pytest.mark.parametrize(
    'text',
    [
        '甲第１号証を参照',
        '本文中に甲第２号証',
        '前置き 甲第３号証 後置き',
        '前置き【甲第３号証】後置き',
        '',
        None,
    ],
)
def test_normalize_koshou_strict_negative(text) -> None:
    assert normalize_koshou_strict(text) is None


def test_sort_key_orders_by_main_then_branch() -> None:
    labels = [
        '甲第００３号証その２',
        '甲第００１号証',
        '甲第００３号証',
        '甲第００２号証',
        '甲第００３号証その１',
        '甲第００４号証',
    ]
    expected = [
        '甲第００１号証',
        '甲第００２号証',
        '甲第００３号証',
        '甲第００３号証その１',
        '甲第００３号証その２',
        '甲第００４号証',
    ]
    assert sorted(labels, key=koshou_sort_key) == expected


def test_label_to_filename() -> None:
    assert label_to_filename('甲第００１号証') == '甲第００１号証.docx'
    assert label_to_filename('甲第０１２号証その３') == '甲第０１２号証その３.docx'


def test_filename_to_label() -> None:
    assert filename_to_label('甲第００１号証.docx') == '甲第００１号証'
    assert filename_to_label('甲第１号証.docx') == '甲第００１号証'
    assert filename_to_label('甲01号証.docx') == '甲第００１号証'
    assert filename_to_label('readme.txt') is None
