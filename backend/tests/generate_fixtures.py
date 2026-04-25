"""テスト用 .docx ファイル生成スクリプト（仕様書 v02 §11.2）。

実行例::

    python -m backend.tests.generate_fixtures
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_BREAK


FIXTURE_DIR = Path(__file__).parent / 'fixtures'


def _add_page_break(doc: Document) -> None:
    para = doc.add_paragraph()
    run = para.add_run()
    run.add_break(WD_BREAK.PAGE)


def make_combined_fixture_bracketed(path: Path) -> None:
    """【甲第xxx号証】マーカー形式の結合ファイル（v02 §11.2）。"""
    doc = Document()

    doc.add_paragraph('【甲第１号証】')
    doc.add_paragraph('これは甲第１号証の本文です。中で甲第3号証への言及をしても誤検出されません。')
    _add_page_break(doc)
    doc.add_paragraph('【甲第２号証】')
    doc.add_paragraph('令和8年4月1日 作成')
    doc.add_paragraph('被告（〇〇学園）作成の保護者説明会配布資料。')
    _add_page_break(doc)
    doc.add_paragraph('【甲第２号証その１】')
    doc.add_paragraph('続報資料（枝番付き）。')

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def make_combined_fixture_bare(path: Path) -> None:
    """括弧なし単独行マーカー形式の結合ファイル（フォールバック検証用）。"""
    doc = Document()

    doc.add_paragraph('甲第１号証')
    doc.add_paragraph('本文 1')
    _add_page_break(doc)
    doc.add_paragraph('甲第２号証')
    doc.add_paragraph('本文 2')
    _add_page_break(doc)
    doc.add_paragraph('甲第２号証その１')
    doc.add_paragraph('枝番資料')

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def make_case_fixture(path: Path) -> None:
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


def make_list_fixture(path: Path) -> None:
    doc = Document()
    doc.add_paragraph('（このファイルは甲号証管理アプリが管理します。1 行 1 号証ラベルで記入してください。例: 甲第００１号証）')
    for label in ['甲第００１号証', '甲第００２号証', '甲第００２号証その１']:
        doc.add_paragraph(label)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def make_master_files(master_dir: Path) -> None:
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
    make_combined_fixture_bracketed(FIXTURE_DIR / 'sample_combined_bracketed.docx')
    make_combined_fixture_bare(FIXTURE_DIR / 'sample_combined_bare.docx')
    make_case_fixture(FIXTURE_DIR / 'sample_case.docx')
    make_list_fixture(FIXTURE_DIR / 'sample_list.docx')
    make_master_files(FIXTURE_DIR / 'sample_master')
    print(f'Fixtures written to {FIXTURE_DIR}')


# 後方互換のエイリアス（既存テストが make_combined_fixture を参照する場合）
make_combined_fixture = make_combined_fixture_bracketed


if __name__ == '__main__':
    main()
