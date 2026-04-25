"""splitter / combiner / case_parser の統合テスト。"""
from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document

from backend.core.case_parser import extract_labels_from_case_file
from backend.core.combiner import combine_files
from backend.core.list_builder import labels_from_combined_file
from backend.core.splitter import split_combined_file
from backend.tests.generate_fixtures import (
    make_case_fixture,
    make_combined_fixture,
    make_master_files,
)


def test_split_combined_extracts_three_files(tmp_path: Path) -> None:
    combined = tmp_path / 'combined.docx'
    make_combined_fixture(combined)
    out_dir = tmp_path / 'master'

    extracted = split_combined_file(combined, out_dir)
    labels = [e.label for e in extracted]

    assert labels == ['甲第００１号証', '甲第００２号証', '甲第００２号証その１']
    for e in extracted:
        assert (out_dir / e.filename).exists()


def test_labels_from_combined_file(tmp_path: Path) -> None:
    combined = tmp_path / 'combined.docx'
    make_combined_fixture(combined)
    assert labels_from_combined_file(combined) == [
        '甲第００１号証',
        '甲第００２号証',
        '甲第００２号証その１',
    ]


def test_combine_then_split_round_trip(tmp_path: Path) -> None:
    master = tmp_path / 'master'
    make_master_files(master)
    combined = tmp_path / 'out' / 'combined.docx'

    labels = ['甲第００１号証', '甲第００２号証', '甲第００２号証その１']
    result = combine_files(master, labels, combined)

    assert result.missing == []
    assert result.used == labels
    assert combined.exists()

    extracted_dir = tmp_path / 'extracted'
    extracted = split_combined_file(combined, extracted_dir)
    assert [e.label for e in extracted] == labels

    body_text = '\n'.join(p.text for p in Document(str(combined)).paragraphs)
    assert '甲第１号証の中身' in body_text
    assert '甲第２号証の枝番' in body_text


def test_combine_reports_missing_labels(tmp_path: Path) -> None:
    master = tmp_path / 'master'
    make_master_files(master)
    combined = tmp_path / 'out' / 'combined.docx'

    labels = ['甲第００１号証', '甲第９９９号証']
    result = combine_files(master, labels, combined)

    assert result.missing == ['甲第９９９号証']
    assert result.used == ['甲第００１号証']


def test_case_parser_extracts_from_body_and_table(tmp_path: Path) -> None:
    case = tmp_path / 'case.docx'
    make_case_fixture(case)
    labels = extract_labels_from_case_file(str(case))
    assert labels == [
        '甲第００１号証',
        '甲第００２号証その１',
        '甲第００３号証',
        '甲第０１２号証',
    ]


def test_split_raises_when_no_split_points(tmp_path: Path) -> None:
    empty = tmp_path / 'empty.docx'
    Document().save(str(empty))
    with pytest.raises(ValueError):
        split_combined_file(empty, tmp_path / 'master')
