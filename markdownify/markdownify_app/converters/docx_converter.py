from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
    "v": "urn:schemas-microsoft-com:vml",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
}


def _iter_block_items(document: DocxDocument) -> Iterator[Paragraph | Table]:
    body = document.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _heading_prefix(paragraph: Paragraph) -> str | None:
    style = getattr(paragraph, "style", None)
    name = getattr(style, "name", "") or ""
    if not name:
        return None
    lowered = name.lower()
    if not lowered.startswith("heading"):
        return None
    digits = "".join(ch for ch in lowered if ch.isdigit())
    if digits:
        level = max(1, min(6, int(digits)))
        return "#" * level
    return "##"


def _is_list_item(paragraph: Paragraph) -> bool:
    try:
        ppr = paragraph._p.pPr  # noqa: SLF001
        return ppr is not None and ppr.numPr is not None
    except Exception:  # noqa: BLE001
        return False


def _table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""

    col_count = max((len(r) for r in rows), default=0)
    normalized = [(r + [""] * (col_count - len(r)))[:col_count] for r in rows]

    header = normalized[0]
    body = normalized[1:] if len(normalized) > 1 else []

    parts: list[str] = []
    parts.append("| " + " | ".join(cell or "" for cell in header) + " |")
    parts.append("|" + " --- |" * col_count)
    for row in body:
        parts.append("| " + " | ".join(cell or "" for cell in row) + " |")
    return "\n".join(parts)


def convert_docx(
    input_path: Path,
    *,
    max_paragraphs: int = 10_000,
    max_tables: int = 200,
    max_table_rows: int = 5_000,
    max_table_cols: int = 100,
) -> tuple[str, list[Path], dict[str, object], list[str]]:
    warnings: list[str] = []
    markdown_parts: list[str] = []
    images: list[Path] = []

    doc = Document(input_path)

    # ベストエフォートで「画像/図の存在」を判定する。
    # python-docx は描画要素をすべて高レベルAPIで扱えないため、XML走査も併用。
    inline_image_count = 0
    try:
        inline_image_count = len(doc.inline_shapes)
    except Exception:  # noqa: BLE001
        inline_image_count = 0

    xml = doc.element

    def _count_xpath(expr: str) -> int:
        try:
            return len(xml.xpath(expr, namespaces=_NS))
        except Exception:  # noqa: BLE001
            return 0

    drawing_count = _count_xpath(".//w:drawing")
    vml_shape_count = _count_xpath(".//v:shape")
    wps_shape_count = _count_xpath(".//wps:wsp")
    chart_count = _count_xpath(".//c:chart")
    smartart_count = _count_xpath(".//dgm:relIds")
    textbox_count = _count_xpath(".//w:txbxContent")

    has_images_or_figures = any(
        count > 0
        for count in [
            inline_image_count,
            drawing_count,
            vml_shape_count,
            wps_shape_count,
            chart_count,
            smartart_count,
            textbox_count,
        ]
    )

    paragraphs_seen = 0
    tables_seen = 0

    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = (block.text or "").strip()
            if not text:
                continue

            paragraphs_seen += 1
            if paragraphs_seen > max_paragraphs:
                warnings.append("paragraphs truncated due to max_paragraphs")
                break

            heading_prefix = _heading_prefix(block)
            if heading_prefix is not None:
                markdown_parts.append(f"{heading_prefix} {text}")
                markdown_parts.append("")
                continue

            if _is_list_item(block):
                markdown_parts.append(f"- {text}")
                continue

            markdown_parts.append(text)
            markdown_parts.append("")

        elif isinstance(block, Table):
            tables_seen += 1
            if tables_seen > max_tables:
                warnings.append("tables truncated due to max_tables")
                break

            rows: list[list[str]] = []
            for r_idx, row in enumerate(block.rows):
                if r_idx >= max_table_rows:
                    warnings.append("table rows truncated due to max_table_rows")
                    break
                cells: list[str] = []
                for c_idx, cell in enumerate(row.cells):
                    if c_idx >= max_table_cols:
                        warnings.append("table cols truncated due to max_table_cols")
                        break
                    cells.append((cell.text or "").strip().replace("\n", " "))
                rows.append(cells)

            if rows:
                markdown_parts.append(_table_to_markdown(rows))
                markdown_parts.append("")

    markdown = "\n".join(markdown_parts).strip()
    meta: dict[str, object] = {
        "paragraphs_processed": min(paragraphs_seen, max_paragraphs),
        "tables_processed": min(tables_seen, max_tables),
        "max_paragraphs": max_paragraphs,
        "max_tables": max_tables,
        "max_table_rows": max_table_rows,
        "max_table_cols": max_table_cols,
        "figures": {
            "has_any": has_images_or_figures,
            "inline_images": inline_image_count,
            "word_drawings": drawing_count,
            "vml_shapes": vml_shape_count,
            "wps_shapes": wps_shape_count,
            "charts": chart_count,
            "smartart": smartart_count,
            "textboxes": textbox_count,
        },
    }

    return markdown, images, meta, warnings
