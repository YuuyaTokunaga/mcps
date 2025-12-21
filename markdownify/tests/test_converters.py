from __future__ import annotations

from pathlib import Path

import fitz
from openpyxl import Workbook

from markdownify_app.converters import csv_converter, excel_converter, pdf_converter


def test_convert_csv_truncates_rows_and_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    rows = ["c1,c2,c3"] + ["1,2,3" for _ in range(5)]
    csv_path.write_text("\n".join(rows), encoding="utf-8")

    markdown, images, meta, warnings = csv_converter.convert_csv(csv_path, max_rows=2, max_cols=2)

    assert "rows truncated due to max_rows" in warnings
    assert "columns truncated due to max_cols" in warnings
    assert "c1" in markdown
    assert images == []
    assert meta["rows"] == 2
    assert meta["cols"] == 2


def test_convert_excel_limits_sheets_and_reports_merges(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "book.xlsx"
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Data"
    ws1.append(["A", "B"])
    ws1.append(["1", "2"])
    ws1.merge_cells("A1:B1")
    ws2 = wb.create_sheet("Extra")
    ws2.append(["X", "Y"])
    wb.save(xlsx_path)

    markdown, images, meta, warnings = excel_converter.convert_excel(
        xlsx_path,
        tmp_path / "out",
        include_images=False,
        max_rows=10,
        max_cols=5,
        max_sheets=1,
    )

    assert "sheets truncated due to max_sheets" in warnings
    assert any("merged cells" in w for w in warnings)
    assert markdown.startswith("## Sheet: Data")
    assert images == []
    assert meta["sheets"] == 1


def test_convert_pdf_truncates_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "doc.pdf"
    doc = fitz.open()
    for idx in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Hello {idx + 1}")
    doc.save(pdf_path)
    doc.close()

    markdown, images, meta, warnings = pdf_converter.convert_pdf(
        pdf_path,
        tmp_path / "out",
        include_images=False,
        max_pages=2,
        render_dpi=50,
    )

    assert "pages truncated due to max_pages" in warnings
    assert markdown.startswith("## Page 1")
    assert images == []
    assert meta["pages_processed"] == 2
