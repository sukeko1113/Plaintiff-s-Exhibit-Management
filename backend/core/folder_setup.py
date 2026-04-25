"""ルートフォルダの初期化（仕様書 §4.1, §7.1）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from docx import Document

LIST_FILENAME = '甲号証リスト.docx'
MASTER_DIR = '個別マスタ'
COMBINED_DIR = '結合甲号証'


@dataclass
class SetupResult:
    ok: bool
    messages: List[str]


def _ensure_dir(path: Path, label: str, messages: List[str]) -> None:
    if path.exists():
        if not path.is_dir():
            raise ValueError(f'「{label}」がフォルダではありません: {path}')
        messages.append(f'✅ 「{label}」フォルダを確認しました。')
    else:
        path.mkdir(parents=True, exist_ok=False)
        messages.append(f'✅ 「{label}」フォルダを作成しました。')


def _ensure_list_file(path: Path, messages: List[str]) -> None:
    if path.exists():
        if not path.is_file():
            raise ValueError(f'「{LIST_FILENAME}」がファイルではありません: {path}')
        messages.append(f'✅ 「{LIST_FILENAME}」を確認しました。')
        return
    Document().save(str(path))
    messages.append(f'✅ 「{LIST_FILENAME}」を作成しました。')


def setup_root_folder(root_path: str) -> SetupResult:
    """ルートフォルダ配下に必須のファイル／フォルダを作成する。"""
    root = Path(root_path).expanduser()
    if not root.exists():
        raise FileNotFoundError(f'指定のルートフォルダが存在しません: {root}')
    if not root.is_dir():
        raise NotADirectoryError(f'指定のパスがフォルダではありません: {root}')

    messages: List[str] = []
    _ensure_list_file(root / LIST_FILENAME, messages)
    _ensure_dir(root / MASTER_DIR, MASTER_DIR, messages)
    _ensure_dir(root / COMBINED_DIR, COMBINED_DIR, messages)

    return SetupResult(ok=True, messages=messages)


def get_master_dir(root_path: str) -> Path:
    return Path(root_path) / MASTER_DIR


def get_combined_dir(root_path: str) -> Path:
    return Path(root_path) / COMBINED_DIR


def get_list_path(root_path: str) -> Path:
    return Path(root_path) / LIST_FILENAME


def list_combined_files(root_path: str) -> List[str]:
    """結合甲号証フォルダ内の .docx ファイル名の一覧（更新日時の新しい順）。"""
    combined = get_combined_dir(root_path)
    if not combined.exists():
        return []
    files = [
        p
        for p in combined.iterdir()
        if p.is_file() and p.suffix.lower() == '.docx' and not p.name.endswith('.bak.docx')
    ]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.name for p in files]


def backup_file(path: Path) -> Path | None:
    """`<元ファイル名>.bak.docx` のバックアップを作成して返す。元が無ければ None。"""
    if not path.exists():
        return None
    backup = path.with_name(path.stem + '.bak' + path.suffix)
    backup.write_bytes(path.read_bytes())
    return backup
