# -*- coding: utf-8 -*-
"""
甲号証 結合サービス。

`個別マスタ` 配下の docx を**正規化ファイル名で辞書順ソート**して結合する。
事前バリデーションを行い、規約外ファイルが 1 件でもある場合は結合を中止する
(InvalidMasterFilesError を送出)。

結合本体は app.merge_kogo_shoko の関数を再利用する。
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

from app.kogo_normalizer import (
    KogoNumber,
    detect_number,
)
from app.merge_kogo_shoko import ProgressCallback, prepare_and_merge


logger = logging.getLogger(__name__)


MASTER_DIRNAME = "個別マスタ"
OUTPUT_DIRNAME = "結合甲号証"
OUTPUT_FILENAME = "結合甲号証.docx"
BACKUP_SUFFIX = ".bak"

DEPRECATED_LIST_FILENAME = "甲号証リスト.docx"


@dataclass
class MergeOutcome:
    """結合処理の結果。FastAPI の MergeResult に詰め替える。"""

    output_path: Path
    merged_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationIssue:
    """個別マスタの規約外ファイル 1 件。"""

    filename: str
    reason: str
    suggested_rename: Optional[str] = None


class InvalidMasterFilesError(Exception):
    """個別マスタに規約外ファイルが含まれる場合に送出。

    `issues` には違反の詳細リストを保持する。ファイルシステムには
    一切変更を加えない (リネームも削除もしない)。
    """

    def __init__(self, issues: List[ValidationIssue]) -> None:
        self.issues = issues
        super().__init__(
            f"個別マスタに規約外のファイルがあるため、結合を中止しました ({len(issues)} 件)"
        )


# ---------------------------------------------------------------------------
# フォルダ初期化
# ---------------------------------------------------------------------------

def ensure_folders(root: Path) -> Path:
    """
    ルート直下に必要なフォルダを作成して、ルートパスを返す。

    - 個別マスタ/      （無ければ作成）
    - 結合甲号証/      （無ければ作成）
    """
    root = Path(root)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)

    (root / MASTER_DIRNAME).mkdir(parents=True, exist_ok=True)
    (root / OUTPUT_DIRNAME).mkdir(parents=True, exist_ok=True)

    return root


# ---------------------------------------------------------------------------
# 個別マスタ事前バリデーション
# ---------------------------------------------------------------------------

def validate_master_files(
    master_dir: Path,
) -> Tuple[List[Tuple[KogoNumber, Path]], List[ValidationIssue]]:
    """
    個別マスタ配下の docx を走査し、規約適合チェックを行う。

    返り値:
      - 適合ファイルの (KogoNumber, Path) リスト (issues が空のときのみ意味を持つ)
      - 規約外ファイルの ValidationIssue リスト

    規約 (SPEC.md §7.1.4):
      1. `~$` で始まる Word 一時ファイルは除外 (検査対象外)
      2. detect_number で番号が抽出できる
      3. ファイル名 (stem) が正規化形式 (`甲第NNN号証` または `甲第NNN号証そのN`) と一致する
      4. 同一番号 (main, branch) のファイルが重複していない

    canonical なファイルを先に処理することで、"non-canonical だが番号は重複"
    というケースを「重複」として正確に報告できるようにする。
    """
    pairs: List[Tuple[KogoNumber, Path]] = []
    issues: List[ValidationIssue] = []

    if not master_dir.exists():
        return pairs, issues

    files = [
        p for p in sorted(master_dir.glob("*.docx")) if not p.name.startswith("~$")
    ]

    # 第 1 パス: 番号抽出可否と名前形式で分類
    canonical: List[Tuple[Path, KogoNumber]] = []
    bad_format: List[Tuple[Path, KogoNumber]] = []
    no_number: List[Path] = []
    for path in files:
        try:
            kogo = detect_number(path)
        except ValueError:
            no_number.append(path)
            continue
        if path.stem == kogo.normalized_filename_stem:
            canonical.append((path, kogo))
        else:
            bad_format.append((path, kogo))

    # 第 2 パス: canonical をまず登録 (= "正" となる番号の集合を確定)
    seen_keys: dict[Tuple[int, Optional[int]], str] = {}
    for path, kogo in canonical:
        key = (kogo.main, kogo.branch)
        # 同一番号の canonical が複数 (= 同名ファイル) は FS 上ありえない
        seen_keys[key] = path.name
        pairs.append((kogo, path))

    # 第 3 パス: bad_format を処理 — 重複を優先判定し、なければ名前形式違反
    for path, kogo in bad_format:
        key = (kogo.main, kogo.branch)
        if key in seen_keys:
            issues.append(
                ValidationIssue(
                    filename=path.name,
                    reason=f"{seen_keys[key]} と番号が重複しています",
                    suggested_rename=None,
                )
            )
            continue
        expected_filename = f"{kogo.normalized_filename_stem}.docx"
        issues.append(
            ValidationIssue(
                filename=path.name,
                reason=f"ファイル名が正規化形式ではありません (期待: {expected_filename})",
                suggested_rename=expected_filename,
            )
        )
        # 後続の同番号 bad_format を「重複」として扱えるようにする
        seen_keys[key] = path.name

    # 第 4 パス: 番号抽出不可
    for path in no_number:
        issues.append(
            ValidationIssue(
                filename=path.name,
                reason="甲号証番号を抽出できません",
                suggested_rename=None,
            )
        )

    return pairs, issues


# ---------------------------------------------------------------------------
# 結合のメイン
# ---------------------------------------------------------------------------

def merge_kogo(
    root_folder: Path,
    *,
    on_progress: Optional[ProgressCallback] = None,
) -> MergeOutcome:
    """
    指定ルートフォルダ配下の甲号証を結合する。

    個別マスタ配下の docx を事前バリデーションし、規約外ファイルがあれば
    InvalidMasterFilesError を送出する (FS は変更しない)。

    on_progress が指定されていれば、各フェーズで進捗メッセージを通知する。
    """
    root = ensure_folders(Path(root_folder))
    master_dir = root / MASTER_DIRNAME
    output_dir = root / OUTPUT_DIRNAME
    output_path = output_dir / OUTPUT_FILENAME

    if on_progress:
        on_progress("バリデーション中: 個別マスタを検査しています")
    pairs, issues = validate_master_files(master_dir)

    if issues:
        raise InvalidMasterFilesError(issues)

    warnings: List[str] = []
    if not master_dir.exists():
        warnings.append(f"個別マスタフォルダが存在しません: {master_dir}")

    if not pairs:
        return MergeOutcome(
            output_path=output_path,
            merged_files=[],
            warnings=warnings + ["結合対象のファイルがありません"],
        )

    if on_progress:
        on_progress(f"バリデーション完了: {len(pairs)} 件のファイルを検出")

    # 既存出力をバックアップ
    if output_path.exists():
        backup = output_path.with_suffix(output_path.suffix + BACKUP_SUFFIX)
        shutil.copy2(output_path, backup)
        logger.info("既存の結合ファイルをバックアップ: %s", backup)
        if on_progress:
            on_progress(f"既存の結合ファイルをバックアップ: {backup.name}")

    # 正規化ファイル名で辞書順ソート (= 主番号昇順 → 枝番なし → 枝番昇順)
    pairs.sort(key=lambda x: x[1].name)
    prepare_and_merge(pairs, output_path, insert_pagebreak=True, on_progress=on_progress)

    return MergeOutcome(
        output_path=output_path,
        merged_files=[p.name for _, p in pairs],
        warnings=warnings,
    )
