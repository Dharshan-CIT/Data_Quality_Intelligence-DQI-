"""Robust ingestion for CSV / Parquet / Excel.

A failure on one file must never crash the session — every entry point here
returns an IngestResult with `ok=False` and a human-readable `error` instead
of raising, except for truly unsupported inputs where we raise a clear
ValueError the caller is expected to catch.
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from typing import Optional, Union

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".xlsx", ".xls"}


@dataclass
class IngestResult:
    ok: bool
    filename: str
    dataframe: Optional[pd.DataFrame] = None
    error: Optional[str] = None
    warnings: list = field(default_factory=list)
    size_bytes: int = 0


def _read_csv_robust(buffer_or_path, warnings: list) -> pd.DataFrame:
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    last_err = None
    for enc in encodings:
        try:
            if hasattr(buffer_or_path, "seek"):
                buffer_or_path.seek(0)
            df = pd.read_csv(buffer_or_path, encoding=enc, low_memory=False)
            if enc != "utf-8":
                warnings.append(f"File was not valid UTF-8; decoded using {enc}.")
            return df
        except UnicodeDecodeError as e:
            last_err = e
            continue
        except pd.errors.EmptyDataError as e:
            raise ValueError("The file is empty — no columns could be parsed.") from e
        except pd.errors.ParserError as e:
            # Retry with the python engine, which tolerates ragged rows better.
            try:
                if hasattr(buffer_or_path, "seek"):
                    buffer_or_path.seek(0)
                df = pd.read_csv(buffer_or_path, encoding=enc, engine="python",
                                  on_bad_lines="warn", low_memory=False)
                warnings.append("Some malformed rows were skipped during parsing.")
                return df
            except Exception as e2:
                last_err = e2
                continue
    raise ValueError(f"Could not decode or parse the CSV file ({last_err}).")


def load_file(source: Union[str, io.BytesIO], filename: Optional[str] = None) -> IngestResult:
    """Load a CSV/Parquet/Excel file from a path or an in-memory buffer.

    Never raises for ordinary data problems (empty file, bad encoding,
    malformed rows, mismatched schema) — those come back as IngestResult.error.
    """
    if filename is None:
        filename = source if isinstance(source, str) else "uploaded_file"
    name = os.path.basename(filename)
    ext = os.path.splitext(name)[1].lower()
    warnings: list = []

    try:
        if isinstance(source, str):
            size_bytes = os.path.getsize(source) if os.path.exists(source) else 0
        else:
            source.seek(0, io.SEEK_END)
            size_bytes = source.tell()
            source.seek(0)
    except Exception:
        size_bytes = 0

    if size_bytes == 0:
        return IngestResult(ok=False, filename=name, error="File is empty (0 bytes).", size_bytes=0)

    if ext not in SUPPORTED_EXTENSIONS:
        return IngestResult(
            ok=False, filename=name,
            error=f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
            size_bytes=size_bytes,
        )

    try:
        if ext == ".csv":
            df = _read_csv_robust(source, warnings)
        elif ext == ".parquet":
            df = pd.read_parquet(source)
        else:  # .xlsx / .xls
            df = pd.read_excel(source)
    except ValueError as e:
        return IngestResult(ok=False, filename=name, error=str(e), size_bytes=size_bytes)
    except Exception as e:
        return IngestResult(ok=False, filename=name, error=f"Failed to read file: {e}", size_bytes=size_bytes)

    if df.shape[1] == 0:
        return IngestResult(ok=False, filename=name, error="File has no columns.", size_bytes=size_bytes)
    if df.shape[0] == 0:
        warnings.append("File has headers but no data rows.")

    # Normalize column names: strip whitespace, de-duplicate blind duplicates.
    original_cols = list(df.columns)
    df.columns = [str(c).strip() for c in df.columns]
    if len(set(df.columns)) != len(df.columns):
        seen: dict = {}
        new_cols = []
        for c in df.columns:
            if c in seen:
                seen[c] += 1
                new_cols.append(f"{c}__dup{seen[c]}")
            else:
                seen[c] = 0
                new_cols.append(c)
        df.columns = new_cols
        warnings.append("Duplicate column names were found and suffixed to keep them distinct.")
    if list(df.columns) != [str(c) for c in original_cols]:
        pass  # whitespace-only rename, not worth a warning

    return IngestResult(ok=True, filename=name, dataframe=df, warnings=warnings, size_bytes=size_bytes)


def load_many(sources: list) -> dict:
    """Load several (source, filename) pairs. One bad file never blocks the rest."""
    results = {}
    for item in sources:
        if isinstance(item, tuple):
            source, filename = item
        else:
            source, filename = item, getattr(item, "name", str(item))
        result = load_file(source, filename)
        results[result.filename] = result
    return results
