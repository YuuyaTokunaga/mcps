import io
import re
from pathlib import Path

import openpyxl
import pandas as pd
from PIL import Image


def _slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", name.strip()) or "sheet"
    return slug[:64]


def _extract_images(wb: openpyxl.Workbook, images_dir: Path) -> list[Path]:
    images: list[Path] = []
    for ws in wb.worksheets:
        sheet_dir = images_dir / _slugify(ws.title)
        sheet_dir.mkdir(parents=True, exist_ok=True)
        for idx, img in enumerate(getattr(ws, "_images", []), start=1):
            data = getattr(img, "_data", None)
            if callable(data):
                data = data()
            if data is None:
                continue
            try:
                pil_img = Image.open(io.BytesIO(data))
                out_path = sheet_dir / f"img-{idx:03d}.png"
                pil_img.save(out_path, format="PNG")
                images.append(out_path)
            except Exception:
                continue
    return images


def convert_excel(
    input_path: Path,
    out_dir: Path,
    include_images: bool = False,
    max_rows: int = 1000,
    max_cols: int = 100,
    max_sheets: int = 20,
) -> tuple[str, list[Path], dict[str, object], list[str]]:
    warnings: list[str] = []
    markdown_parts: list[str] = []
    images: list[Path] = []
    xl = pd.ExcelFile(input_path)
    sheet_names = xl.sheet_names[:max_sheets]
    if len(xl.sheet_names) > max_sheets:
        warnings.append("sheets truncated due to max_sheets")

    merge_warnings: list[str] = []
    try:
        wb = openpyxl.load_workbook(input_path, data_only=True)
        for ws in wb.worksheets:
            if ws.merged_cells.ranges:
                merge_warnings.append(f"sheet '{ws.title}' contains merged cells")
        if include_images:
            images_dir = out_dir / "images" / "excel"
            images = _extract_images(wb, images_dir)
    except Exception:
        warnings.append("failed to inspect workbook merges or images")

    for sheet in sheet_names:
        df = xl.parse(sheet, header=None, nrows=max_rows + 1)
        if len(df) > max_rows:
            df = df.iloc[:max_rows]
            warnings.append(f"sheet '{sheet}' rows truncated due to max_rows")
        if df.shape[1] > max_cols:
            df = df.iloc[:, :max_cols]
            warnings.append(f"sheet '{sheet}' columns truncated due to max_cols")
        header = f"## Sheet: {sheet}\n"
        markdown_parts.append(header)
        markdown_parts.append(df.to_markdown(index=False, headers=[]))
        markdown_parts.append("")

    markdown = "\n".join(markdown_parts).strip()
    meta: dict[str, object] = {
        "sheets": len(sheet_names),
        "max_rows": max_rows,
        "max_cols": max_cols,
        "max_sheets": max_sheets,
        "images": [str(p) for p in images],
    }
    warnings.extend(merge_warnings)
    return markdown, images, meta, warnings
