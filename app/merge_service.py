# -*- coding: utf-8 -*-
"""
甲号証 結合サービス。

ルートフォルダ直下の `甲号証リスト.docx` を読み取り、
- 有効な番号が1件以上記載されていればその番号集合だけを `個別マスタ` から選んで結合
- リスト不在 / 空 / 番号抽出ゼロなら `個別マスタ` 内の全 docx を結合

結合本体は app.merge_kogo_shoko の関数を再利用する。
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from docx import Document

from app.kogo_normalizer import (
    KogoNumber,
    LIST_PATTERN,
    detect_number,
    extract_numbers_from_text,
    iter_doc_text_blocks,
)
from app.merge_kogo_shoko import prepare_and_merge


logger = logging.getLogger(__name__)


LIST_FILENAME = "甲号証リスト.docx"
MASTER_DIRNAME = "個別マスタ"
OUTPUT_DIRNAME = "結合甲号証"
OUTPUT_FILENAME = "結合甲号証.docx"
BACKUP_SUFFIX = ".bak"


@dataclass
class MergeOutcome:
    """結合処理の結果。FastAPI の MergeResult に詰め替える。"""

    output_path: Path
    merged_files: List[str] = field(default_factory=list)
    list_used: bool = False
    missing_in_master: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# フォルダ初期化
# ---------------------------------------------------------------------------

def ensure_folders(root: Path) -> Path:
    """
    ルート直下に必要なフォルダ・ファイルを作成して、ルートパスを返す。

    - 個別マスタ/      （無ければ作成）
    - 結合甲号証/      （無ければ作成）
    - 甲号証リスト.docx （無ければ空の docx を作成）
    """
    root = Path(root)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)

    (root / MASTER_DIRNAME).mkdir(parents=True, exist_ok=True)
    (root / OUTPUT_DIRNAME).mkdir(parents=True, exist_ok=True)

    list_path = root / LIST_FILENAME
    if not list_path.exists():
        doc = Document()
        doc.save(str(list_path))
        logger.info("空の甲号証リストを作成: %s", list_path)

    return root


# ---------------------------------------------------------------------------
# 甲号証リスト読み取り
# ---------------------------------------------------------------------------

def read_kogo_list(list_path: Path) -> Tuple[Set[Tuple[int, Optional[int]]], List[str]]:
    """
    甲号証リスト.docx を読み、(main, branch) のセットと警告リストを返す。

    - 段落と表セルの両方を走査する
    - LIST_PATTERN で全マッチを拾い、重複は集合で排除
    - リストが存在しない / 空 / 番号ゼロ件 の場合は空セットを返す
    """
    warnings: List[str] = []
    found: Set[Tuple[int, Optional[int]]] = set()

    if not list_path.exists():
        return found, warnings

    try:
        doc = Document(str(list_path))
    except Exception as e:
        warnings.append(f"甲号証リストの読み込みに失敗しました: {e}")
        return found, warnings

    # 重複を検知してログに残すため、key 単位の出現回数を数える
    counts: Dict[Tuple[int, Optional[int]], int] = {}
    for text in iter_doc_text_blocks(doc):
        for kogo in extract_numbers_from_text(text, LIST_PATTERN):
            key = (kogo.main, kogo.branch)
            counts[key] = counts.get(key, 0) + 1
            found.add(key)

    duplicates = [k for k, v in counts.items() if v > 1]
    for main, branch in duplicates:
        marker = KogoNumber(main, branch).normalized_marker
        warnings.append(f"甲号証リストに重複した番号があります: {marker}")

    return found, warnings


# ---------------------------------------------------------------------------
# 個別マスタ収集
# ---------------------------------------------------------------------------

def collect_master_files(master_dir: Path) -> Tuple[List[Tuple[KogoNumber, Path]], List[str]]:
    """
    個別マスタフォルダ内の docx を走査し、(KogoNumber, Path) のリストを返す。

    - `~$` で始まる一時ファイルは除外
    - 番号が抽出できないファイルは警告として記録、リストには含めない
    """
    warnings: List[str] = []
    out: List[Tuple[KogoNumber, Path]] = []

    if not master_dir.exists():
        warnings.append(f"個別マスタフォルダが存在しません: {master_dir}")
        return out, warnings

    for path in sorted(master_dir.glob("*.docx")):
        if path.name.startswith("~$"):
            continue
        try:
            kogo = detect_number(path)
        except ValueError as e:
            warnings.append(str(e))
            continue
        out.append((kogo, path))

    return out, warnings


# ---------------------------------------------------------------------------
# 結合のメイン
# ---------------------------------------------------------------------------

def merge_kogo(root_folder: Path) -> MergeOutcome:
    """
    指定ルートフォルダ配下の甲号証を結合する。
    """
    root = ensure_folders(Path(root_folder))
    list_path = root / LIST_FILENAME
    master_dir = root / MASTER_DIRNAME
    output_dir = root / OUTPUT_DIRNAME
    output_path = output_dir / OUTPUT_FILENAME

    list_keys, list_warnings = read_kogo_list(list_path)
    master_pairs, master_warnings = collect_master_files(master_dir)

    warnings: List[str] = []
    warnings.extend(list_warnings)
    warnings.extend(master_warnings)

    list_used = bool(list_keys)
    missing_in_master: List[str] = []

    if list_used:
        master_keys = {(k.main, k.branch) for k, _ in master_pairs}
        # リストにあるがマスタに無い番号 → missing_in_master
        for key in sorted(list_keys, key=lambda x: (x[0], x[1] or 0)):
            if key not in master_keys:
                missing_in_master.append(KogoNumber(key[0], key[1]).normalized_marker)
        # マスタからリストに含まれるものだけを抽出
        selected = [(k, p) for (k, p) in master_pairs if (k.main, k.branch) in list_keys]
    else:
        selected = list(master_pairs)

    if not selected:
        outcome = MergeOutcome(
            output_path=output_path,
            merged_files=[],
            list_used=list_used,
            missing_in_master=missing_in_master,
            warnings=warnings + ["結合対象のファイルがありません"],
        )
        return outcome

    # マスタ内の重複番号を警告
    seen_keys: Set[Tuple[int, Optional[int]]] = set()
    deduped: List[Tuple[KogoNumber, Path]] = []
    for kogo, path in selected:
        key = (kogo.main, kogo.branch)
        if key in seen_keys:
            warnings.append(
                f"個別マスタに重複した番号があります: {kogo.normalized_marker} ({path.name})"
            )
            continue
        seen_keys.add(key)
        deduped.append((kogo, path))

    # 既存出力をバックアップ
    if output_path.exists():
        backup = output_path.with_suffix(output_path.suffix + BACKUP_SUFFIX)
        shutil.copy2(output_path, backup)
        logger.info("既存の結合ファイルをバックアップ: %s", backup)

    deduped.sort(key=lambda x: x[0].sort_key)
    prepare_and_merge(deduped, output_path, insert_pagebreak=True)

    return MergeOutcome(
        output_path=output_path,
        merged_files=[p.name for _, p in deduped],
        list_used=list_used,
        missing_in_master=missing_in_master,
        warnings=warnings,
    )
