"""仕様 §4.7 backup テスト。"""

from __future__ import annotations

from pathlib import Path

from backend.core.backup import (
    BACKUP_DIR_NAME,
    MAX_GENERATIONS,
    backup_paths,
    list_generations,
    rotate,
)


def test_backup_file_and_dir(tmp_path):
    f = tmp_path / 'file.txt'
    f.write_text('content')
    d = tmp_path / 'subdir'
    d.mkdir()
    (d / 'inner.txt').write_text('inner')

    bdir = backup_paths(tmp_path, [f, d], timestamp='20260101-100000')

    assert bdir is not None
    assert bdir == tmp_path / BACKUP_DIR_NAME / '20260101-100000'
    assert (bdir / 'file.txt').read_text() == 'content'
    assert (bdir / 'subdir' / 'inner.txt').read_text() == 'inner'

    # 元ファイルは温存されている（バックアップは copy なので）
    assert f.exists()
    assert d.exists()


def test_backup_skips_missing(tmp_path):
    bdir = backup_paths(tmp_path, [tmp_path / 'absent.txt'])
    assert bdir is None


def test_backup_returns_none_for_empty_list(tmp_path):
    assert backup_paths(tmp_path, []) is None


def test_rotate_keeps_latest(tmp_path):
    base = tmp_path / BACKUP_DIR_NAME
    base.mkdir()
    timestamps = [
        '20260101-000000',
        '20260102-000000',
        '20260103-000000',
        '20260104-000000',
        '20260105-000000',
    ]
    for ts in timestamps:
        (base / ts).mkdir()

    deleted = rotate(tmp_path, max_generations=3)

    remaining = sorted(p.name for p in base.iterdir())
    assert remaining == ['20260103-000000', '20260104-000000', '20260105-000000']
    assert sorted(p.name for p in deleted) == ['20260101-000000', '20260102-000000']


def test_rotate_no_op_when_under_limit(tmp_path):
    base = tmp_path / BACKUP_DIR_NAME
    base.mkdir()
    (base / '20260101-000000').mkdir()
    deleted = rotate(tmp_path, max_generations=10)
    assert deleted == []
    assert (base / '20260101-000000').is_dir()


def test_rotate_ignores_non_timestamp_dirs(tmp_path):
    base = tmp_path / BACKUP_DIR_NAME
    base.mkdir()
    (base / 'random_folder').mkdir()  # 形式違いは無視
    (base / '20260101-000000').mkdir()
    deleted = rotate(tmp_path, max_generations=0)
    assert (base / 'random_folder').is_dir()
    assert sorted(p.name for p in deleted) == ['20260101-000000']


def test_backup_triggers_rotation(tmp_path):
    """backup_paths が自動でローテーションする。"""
    base = tmp_path / BACKUP_DIR_NAME
    base.mkdir()
    # 既に MAX_GENERATIONS 件ある状態
    for i in range(MAX_GENERATIONS):
        (base / f'2026010{i % 10}-00000{i:1d}').mkdir(exist_ok=True)
    # ↑ ファイル名衝突を避けるため、明示的に列挙
    for d in list(base.iterdir()):
        d.rmdir() if d.is_dir() and not list(d.iterdir()) else None
    for i in range(MAX_GENERATIONS):
        (base / f'202601{i:02d}-000000').mkdir()

    f = tmp_path / 'file.txt'
    f.write_text('x')
    backup_paths(tmp_path, [f], timestamp='20260201-000000')

    generations = list_generations(tmp_path)
    assert len(generations) == MAX_GENERATIONS
    # 最新は新しく追加したもの
    assert generations[0].name == '20260201-000000'


def test_list_generations_empty(tmp_path):
    assert list_generations(tmp_path) == []
