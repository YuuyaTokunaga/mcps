from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber


def _table_to_markdown(table: list[list[str]]) -> str:
    if not table:
        return ""
    header = table[0]
    rows = table[1:] if len(table) > 1 else []
    parts = ["| " + " | ".join(cell or "" for cell in header) + " |"]
    parts.append("|" + " --- |" * len(header))
    for row in rows:
        parts.append("| " + " | ".join(cell or "" for cell in row) + " |")
    return "\n".join(parts)


def convert_pdf(
    input_path: Path,
    out_dir: Path,
    include_images: bool = False,
    max_pages: int = 200,
    render_dpi: int = 200,
) -> tuple[str, list[Path], dict[str, object], list[str]]:
    warnings: list[str] = []
    markdown_parts: list[str] = []
    images: list[Path] = []

    with pdfplumber.open(input_path) as pdf:
        page_count = len(pdf.pages)
        pages = pdf.pages[:max_pages]
        if page_count > max_pages:
            warnings.append("pages truncated due to max_pages")
        for idx, page in enumerate(pages, start=1):
            markdown_parts.append(f"## Page {idx}")
            text = page.extract_text() or ""
            if text.strip():
                markdown_parts.append(text.strip())
            tables = page.extract_tables() or []
            for t_idx, table in enumerate(tables, start=1):
                markdown_parts.append(f"\nTable {t_idx}:\n")
                markdown_parts.append(_table_to_markdown(table))
            markdown_parts.append("")

    if include_images:
        images_dir = out_dir / "images" / "pdf"
        images_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(input_path)
        for idx in range(min(max_pages, doc.page_count)):
            page = doc.load_page(idx)
            pix = page.get_pixmap(dpi=render_dpi)
            out_path = images_dir / f"page-{idx + 1:03d}.png"
            pix.save(out_path)
            images.append(out_path)
        doc.close()

    markdown = "\n".join(markdown_parts).strip()
    meta: dict[str, object] = {
        "pages_processed": min(page_count, max_pages),
        "max_pages": max_pages,
        "images": [str(p) for p in images],
    }
    return markdown, images, meta, warnings
