"""仕様 §6.6 splitter テスト。"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from docx import Document

from backend.core.splitter import (
    detect_sections,
    split_combined_to_master,
)
from backend.tests import generate_fixtures


@pytest.fixture(scope='module', autouse=True)
def _ensure_fixtures():
    """テスト実行前に必ず fixture を生成する。"""
    generate_fixtures.generate_all()


def test_split_simple(tmp_path):
    src = generate_fixtures.FIXTURES_DIR / 'combined_simple.docx'
    out = tmp_path / 'out'
    files = split_combined_to_master(src, out)

    assert len(files) == 5
    expected = [
        '甲第００１号証.docx',
        '甲第００２号証.docx',
        '甲第００３号証.docx',
        '甲第００４号証.docx',
        '甲第００５号証.docx',
    ]
    assert [f.name for f in files] == expected
    # 全ファイルが docx として読み込めること
    for f in files:
        Document(str(f))


def test_split_with_branch(tmp_path):
    src = generate_fixtures.FIXTURES_DIR / 'combined_with_branch.docx'
    out = tmp_path / 'out'
    files = split_combined_to_master(src, out)

    names = [f.name for f in files]
    assert names == [
        '甲第００１号証.docx',
        '甲第００２号証.docx',
        '甲第００３号証.docx',
        '甲第００３号証その１.docx',
        '甲第００３号証その２.docx',
        '甲第００４号証.docx',
    ]
    for f in files:
        Document(str(f))


def test_split_preserves_table(tmp_path):
    src = generate_fixtures.FIXTURES_DIR / 'combined_with_table.docx'
    out = tmp_path / 'out'
    files = split_combined_to_master(src, out)

    assert len(files) == 3
    for f in files:
        with zipfile.ZipFile(f) as zf:
            xml = zf.read('word/document.xml').decode('utf-8')
        assert '<w:tbl' in xml, f'表が消失: {f.name}'


def test_split_preserves_image(tmp_path):
    src = generate_fixtures.FIXTURES_DIR / 'combined_with_image.docx'
    out = tmp_path / 'out'
    files = split_combined_to_master(src, out)

    assert len(files) == 3
    # 画像参照が残っていること
    for f in files:
        with zipfile.ZipFile(f) as zf:
            xml = zf.read('word/document.xml').decode('utf-8')
            names = zf.namelist()
        assert '<w:drawing' in xml, f'drawing が消失: {f.name}'
        # メディアファイル自体も保持される（vendor は全リソースをコピー）
        assert any(n.startswith('word/media/') for n in names), \
            f'word/media/ が消失: {f.name}'


def test_dry_run_returns_paths_without_writing(tmp_path):
    src = generate_fixtures.FIXTURES_DIR / 'combined_with_branch.docx'
    out = tmp_path / 'out'

    paths = split_combined_to_master(src, out, dry_run=True)

    assert [p.name for p in paths] == [
        '甲第００１号証.docx',
        '甲第００２号証.docx',
        '甲第００３号証.docx',
        '甲第００３号証その１.docx',
        '甲第００３号証その２.docx',
        '甲第００４号証.docx',
    ]
    # dry_run なので実ファイルは無い
    if out.exists():
        assert not list(out.glob('*.docx'))


def test_detect_sections(tmp_path):
    src = generate_fixtures.FIXTURES_DIR / 'combined_with_branch.docx'
    labels = detect_sections(src)
    assert labels == [
        '甲第００１号証',
        '甲第００２号証',
        '甲第００３号証',
        '甲第００３号証その１',
        '甲第００３号証その２',
        '甲第００４号証',
    ]


def test_overwrite_false_raises_on_collision(tmp_path):
    src = generate_fixtures.FIXTURES_DIR / 'combined_simple.docx'
    out = tmp_path / 'out'
    out.mkdir()
    # 既存ファイルを置く
    existing = out / '甲第００１号証.docx'
    existing.write_bytes(b'dummy')

    with pytest.raises(FileExistsError):
        split_combined_to_master(src, out, overwrite=False)

    # 既存ファイルは温存
    assert existing.read_bytes() == b'dummy'
    # 仮ファイルが残っていない
    assert not list(out.glob('__tmp_*'))


def test_overwrite_true_replaces_existing(tmp_path):
    src = generate_fixtures.FIXTURES_DIR / 'combined_simple.docx'
    out = tmp_path / 'out'
    out.mkdir()
    existing = out / '甲第００１号証.docx'
    existing.write_bytes(b'dummy')

    files = split_combined_to_master(src, out, overwrite=True)
    assert len(files) == 5
    # 上書きされたので docx として読み込める
    Document(str(out / '甲第００１号証.docx'))
