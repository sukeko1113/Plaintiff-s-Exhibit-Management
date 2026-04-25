"""テスト用 .docx ファイルを生成するスクリプト。

実行例:
    python -m backend.tests.generate_fixtures
"""
from __future__ import annotations

from pathlib import Path

from docx import Document


FIXTURE_DIR = Path(__file__).parent / 'fixtures'


def make_combined_fixture(path: Path) -> None:
    """3 つの甲号証を含む結合ファイルを生成する。

    改ページの有無は分解判定に影響しない。``【甲第〇〇号証】`` 等のラベル段落
    のみで 1 つの甲号証の単位を判定する。

    甲第１号証（本文 1 段落、ラベルは括弧無し）
    甲第２号証（本文 2 段落、ラベルは ``【】`` 付き）
    甲第２号証その１（本文 1 段落、枝番付き）
    """
    doc = Document()

    doc.add_paragraph('甲第１号証')
    doc.add_paragraph('これは甲第１号証の本文です。中で甲第3号証への言及をしても誤検出されないことを期待します。')

    doc.add_paragraph('【甲第２号証】')
    doc.add_paragraph('令和8年4月1日 作成')
    doc.add_paragraph('被告（〇〇学園）作成の保護者説明会配布資料。')

    doc.add_paragraph('【甲第２号証その１】')
    doc.add_paragraph('続報資料（枝番付き）。')

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def make_case_fixture(path: Path) -> None:
    """本文中とテーブル内に号証ラベルが混在する案件ファイル。"""
    doc = Document()
    doc.add_heading('訴状（サンプル）', level=1)
    doc.add_paragraph('原告は本件において、甲第1号証ないし甲第3号証を提出する。')
    doc.add_paragraph('特に甲第２号証その１は重要である。')

    table = doc.add_table(rows=2, cols=2)
    table.style = 'Table Grid'
    table.rows[0].cells[0].text = '号証'
    table.rows[0].cells[1].text = '備考'
    table.rows[1].cells[0].text = '甲第12号証'
    table.rows[1].cells[1].text = '事件記録'

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def make_master_files(master_dir: Path) -> None:
    """個別マスタフォルダにいくつかの甲号証ファイルを生成する。"""
    master_dir.mkdir(parents=True, exist_ok=True)
    for label, body in [
        ('甲第００１号証', '甲第１号証の中身'),
        ('甲第００２号証', '甲第２号証の中身'),
        ('甲第００２号証その１', '甲第２号証の枝番'),
    ]:
        doc = Document()
        doc.add_paragraph(label)
        doc.add_paragraph(body)
        doc.save(str(master_dir / f'{label}.docx'))


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    make_combined_fixture(FIXTURE_DIR / 'sample_combined.docx')
    make_case_fixture(FIXTURE_DIR / 'sample_case.docx')
    make_master_files(FIXTURE_DIR / 'sample_master')
    print(f'Fixtures written to {FIXTURE_DIR}')


if __name__ == '__main__':
    main()
