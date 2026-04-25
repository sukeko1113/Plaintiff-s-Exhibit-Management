"""ルートフォルダの検証・初期化（仕様 §11）。"""

from __future__ import annotations

from pathlib import Path

from docx import Document


REQUIRED_FOLDERS = ['個別マスタ', '結合甲号証']
REQUIRED_FILES = ['甲号証リスト.docx']


def setup_root(root: Path) -> dict:
    """ルートフォルダを検証し、必須フォルダ／ファイルを補完する。

    既存のものは触らない。作成したものと既存のものを返す。
    """
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f'ルートフォルダが存在しません: {root}')
    if not root.is_dir():
        raise NotADirectoryError(f'ディレクトリではありません: {root}')

    created: list[str] = []
    existed: list[str] = []

    for folder in REQUIRED_FOLDERS:
        p = root / folder
        if p.exists():
            existed.append(folder)
        else:
            p.mkdir()
            created.append(folder)

    for fname in REQUIRED_FILES:
        p = root / fname
        if p.exists():
            existed.append(fname)
        else:
            Document().save(str(p))
            created.append(fname)

    return {'root': str(root), 'created': created, 'existed': existed}


def normalize_root_path(raw: str) -> Path:
    """UI から受け取った Windows パス文字列を pathlib.Path に変換。

    Windows ネイティブ表記（バックスラッシュ・ドライブレター）をそのまま受け付け、
    Linux 開発環境でもエラーにならないよう raw のまま Path 化する。
    """
    return Path(raw)
