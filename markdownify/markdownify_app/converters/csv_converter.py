from pathlib import Path

import pandas as pd


def convert_csv(
    input_path: Path,
    max_rows: int = 2000,
    max_cols: int = 100,
) -> tuple[str, list[Path], dict[str, object], list[str]]:
    warnings: list[str] = []
    try:
        df = pd.read_csv(input_path, engine="python", encoding_errors="ignore", nrows=max_rows + 1)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"failed to read csv: {exc}") from exc

    if len(df) > max_rows:
        df = df.iloc[:max_rows]
        warnings.append("rows truncated due to max_rows")
    if df.shape[1] > max_cols:
        df = df.iloc[:, :max_cols]
        warnings.append("columns truncated due to max_cols")

    markdown = df.to_markdown(index=False)
    meta: dict[str, object] = {
        "rows": len(df),
        "cols": df.shape[1],
        "max_rows": max_rows,
        "max_cols": max_cols,
    }
    return markdown, [], meta, warnings
