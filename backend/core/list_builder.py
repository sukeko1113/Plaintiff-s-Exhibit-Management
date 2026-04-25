"""甲号証リスト.docx の自動作成・解析（仕様書 §7.4, §7.5）。"""
from __future__ import annotations

from pathlib import Path
from typing import List

from docx import Document

from .folder_setup import (
    backup_file,
    get_combined_dir,
    get_list_path,
    get_master_dir,
)
from .normalizer import (
    filename_to_label,
    koshou_sort_key,
    normalize_koshou_strict,
)
from .splitter import find_split_points


def labels_from_master(root_path: str) -> List[str]:
    """個別マスタ内の .docx を全件走査し、正規化ラベルを昇順で返す。"""
    master = get_master_dir(root_path)
    if not master.exists():
        return []
    labels: List[str] = []
    for path in master.iterdir():
        if not path.is_file() or path.suffix.lower() != '.docx':
            continue
        if path.name.endswith('.bak.docx'):
            continue
        label = filename_to_label(path.name)
        if label:
            labels.append(label)
    seen: set[str] = set()
    deduped: List[str] = []
    for label in sorted(labels, key=koshou_sort_key):
        if label in seen:
            continue
        seen.add(label)
        deduped.append(label)
    return deduped


def labels_from_combined_file(combined_path: Path) -> List[str]:
    """結合甲号証ファイルから含まれる甲号証ラベルを抽出して返す。"""
    doc = Document(str(combined_path))
    points = find_split_points(doc)
    return [p.label for p in points]


def write_list_file(root_path: str, labels: List[str]) -> Path:
    """甲号証リスト.docx を上書き保存する。既存があればバックアップ。"""
    list_path = get_list_path(root_path)
    backup_file(list_path)
    doc = Document()
    for label in labels:
        doc.add_paragraph(label)
    doc.save(str(list_path))
    return list_path


def parse_list_file(root_path: str) -> List[str]:
    """甲号証リスト.docx を読み、各行のラベルを正規化して返す。

    1 行が 1 ラベル形式（仕様書 §7.4 / 確定仕様）。
    正規化に失敗した行はスキップする。
    """
    list_path = get_list_path(root_path)
    if not list_path.exists():
        return []
    doc = Document(str(list_path))
    labels: List[str] = []
    seen: set[str] = set()
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        normalized = normalize_koshou_strict(text)
        if normalized is None:
            from .normalizer import normalize_koshou
            normalized = normalize_koshou(text)
        if normalized is None:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        labels.append(normalized)
    return labels


def auto_create_from_master(root_path: str) -> List[str]:
    labels = labels_from_master(root_path)
    write_list_file(root_path, labels)
    return labels


def auto_create_from_combined(root_path: str, combined_filename: str) -> List[str]:
    combined_path = get_combined_dir(root_path) / combined_filename
    if not combined_path.exists():
        raise FileNotFoundError(f'結合甲号証ファイルが見つかりません: {combined_path}')
    labels = labels_from_combined_file(combined_path)
    write_list_file(root_path, labels)
    return labels
