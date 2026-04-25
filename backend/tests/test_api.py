"""API エンドポイントのスモークテスト（仕様 §12）。

TestClient で各ルートを通し、ハッピーパスとエラーパスを確認する。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.tests import generate_fixtures


client = TestClient(app)


@pytest.fixture(scope='module', autouse=True)
def _ensure_fixtures():
    generate_fixtures.generate_all()


@pytest.fixture
def root_dir(tmp_path):
    """初期化済みのルートフォルダを用意する。"""
    r = client.post('/api/setup', json={'root_path': str(tmp_path)})
    assert r.status_code == 200
    return tmp_path


def test_setup_creates_structure(tmp_path):
    r = client.post('/api/setup', json={'root_path': str(tmp_path)})
    assert r.status_code == 200
    body = r.json()
    assert (tmp_path / '個別マスタ').is_dir()
    assert (tmp_path / '結合甲号証').is_dir()
    assert (tmp_path / '甲号証リスト.docx').is_file()
    assert '個別マスタ' in body['created']


def test_setup_missing_root_404():
    r = client.post('/api/setup', json={'root_path': '/nonexistent/abs/path/xyz'})
    assert r.status_code == 404


def test_master_list_empty(root_dir):
    r = client.get('/api/master/list', params={'root_path': str(root_dir)})
    assert r.status_code == 200
    assert r.json()['files'] == []


def test_split_dry_run_empty_target(root_dir):
    src = generate_fixtures.FIXTURES_DIR / 'combined_simple.docx'
    target = root_dir / '結合甲号証' / src.name
    shutil.copy2(src, target)

    r = client.post('/api/split', json={
        'root_path': str(root_dir),
        'combined_file': str(target),
        'dry_run': True,
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body['preview_files']) == 5
    assert body['existing_files_in_target'] == []
    assert body['warning'] is None


def test_split_then_combine_then_list(root_dir):
    src = generate_fixtures.FIXTURES_DIR / 'combined_with_branch.docx'
    target = root_dir / '結合甲号証' / src.name
    shutil.copy2(src, target)

    # 1. split
    r = client.post('/api/split', json={
        'root_path': str(root_dir),
        'combined_file': str(target),
    })
    assert r.status_code == 200
    assert len(r.json()['produced_files']) == 6

    # 2. master list
    r = client.get('/api/master/list', params={'root_path': str(root_dir)})
    assert r.status_code == 200
    assert len(r.json()['files']) == 6

    # 3. combine
    r = client.post('/api/combine', json={
        'root_path': str(root_dir),
        'output_filename': 'rebuilt.docx',
    })
    assert r.status_code == 200
    body = r.json()
    assert body['source_count'] == 6
    assert Path(body['output_file']).is_file()

    # 4. list/from-master
    r = client.post('/api/list/from-master', json={'root_path': str(root_dir)})
    assert r.status_code == 200
    assert r.json()['labels'] == [
        '甲第００１号証',
        '甲第００２号証',
        '甲第００３号証',
        '甲第００３号証その１',
        '甲第００３号証その２',
        '甲第００４号証',
    ]


def test_list_from_combined(root_dir):
    src = generate_fixtures.FIXTURES_DIR / 'combined_simple.docx'
    target = root_dir / '結合甲号証' / src.name
    shutil.copy2(src, target)

    r = client.post('/api/list/from-combined', json={
        'root_path': str(root_dir),
        'combined_files': [str(target)],
    })
    assert r.status_code == 200
    fw = '０１２３４５６７８９'
    assert r.json()['labels'] == [f'甲第００{fw[i]}号証' for i in range(1, 6)]


def test_case_parse(root_dir):
    case = generate_fixtures.FIXTURES_DIR / 'case_sample.docx'
    r = client.post('/api/case/parse', json={'case_file': str(case)})
    assert r.status_code == 200
    labels = r.json()['labels']
    assert '甲第００１号証' in labels
    assert '甲第０１０号証その１' in labels


def test_evidence_pack_dry_run_reports_missing(root_dir):
    case = generate_fixtures.FIXTURES_DIR / 'case_sample.docx'
    # マスタは空 → 全部 missing
    r = client.post('/api/evidence-pack', json={
        'root_path': str(root_dir),
        'case_file': str(case),
        'dry_run': True,
    })
    assert r.status_code == 200
    body = r.json()
    assert set(body['used_labels']) == set(body['missing_labels'])
    assert body['output_file'] is None


def test_evidence_pack_full(root_dir):
    # 個別マスタを準備
    src = generate_fixtures.FIXTURES_DIR / 'combined_simple.docx'
    target = root_dir / '結合甲号証' / src.name
    shutil.copy2(src, target)
    r = client.post('/api/split', json={
        'root_path': str(root_dir),
        'combined_file': str(target),
    })
    assert r.status_code == 200

    case = generate_fixtures.FIXTURES_DIR / 'case_sample.docx'
    r = client.post('/api/evidence-pack', json={
        'root_path': str(root_dir),
        'case_file': str(case),
    })
    assert r.status_code == 200
    body = r.json()
    # case_sample.docx のうち、個別マスタにあるのは 1, 2, 3, 5 号証
    # （1の2、10その1 はマスタに無い）
    assert '甲第００１号証' in body['used_labels']
    assert Path(body['output_file']).is_file()


def test_master_table_preview(root_dir):
    src = generate_fixtures.FIXTURES_DIR / 'combined_simple.docx'
    target = root_dir / '結合甲号証' / src.name
    shutil.copy2(src, target)
    client.post('/api/split', json={
        'root_path': str(root_dir),
        'combined_file': str(target),
    })

    r = client.get('/api/master/table', params={'root_path': str(root_dir)})
    assert r.status_code == 200
    rows = r.json()['rows']
    assert len(rows) == 5
    assert rows[0]['display_label'] == '甲第1号証'
