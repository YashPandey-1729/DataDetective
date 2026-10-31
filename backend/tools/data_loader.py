import io
import csv
import zipfile
from pathlib import Path
import pandas as pd
import numpy as np

MAX_UPLOAD = 15 * 1024 * 1024
MAX_ROWS = 150_000
MAX_COLUMNS = 100


def validate_headers(headers):
    # Check the source header before Pandas can silently rename duplicate columns.
    names = ['' if value is None or pd.isna(value) else str(value).strip() for value in headers]
    if not names or len(names) > MAX_COLUMNS:
        raise ValueError('Dataset must have between 1 and 100 columns.')
    if len(set(name.casefold() for name in names)) != len(names) or any(not c or len(c) > 120 or '\x00' in c for c in names):
        raise ValueError('Column names must be unique (ignoring case), nonempty, and at most 120 characters.')
    return names


def load_dataset(content: bytes, filename: str) -> pd.DataFrame:
    if not content or len(content) > MAX_UPLOAD:
        raise ValueError('Upload an uncompressed CSV or Excel file smaller than 15 MB.')
    extension = Path(filename).suffix.lower()
    try:
        if extension == '.csv':
            if b'\x00' in content:
                raise ValueError('CSV must be UTF-8 text.')
            text = content.decode('utf-8-sig')
            parsed = csv.reader(io.StringIO(text), strict=True)
            source_header = next((row for row in parsed if row), None)
            if source_header is None:
                raise ValueError('CSV is empty.')
            headers = validate_headers(source_header)
            # Pandas tolerates over-wide first rows by inferring an index. Reject
            # ragged input explicitly rather than silently dropping that value.
            for index, row in enumerate(parsed, start=1):
                if not row:
                    continue
                if len(row) != len(headers):
                    raise ValueError(f'CSV record {index + 1} has {len(row)} fields; expected {len(headers)}.')
                if index > MAX_ROWS:
                    raise ValueError('Dataset exceeds 150,000 rows.')
            df = pd.read_csv(io.StringIO(text), nrows=MAX_ROWS + 1)
        elif extension in {'.xlsx', '.xls'}:
            if extension == '.xlsx':
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    if sum(i.file_size for i in archive.infolist()) > 60 * 1024 * 1024:
                        raise ValueError('Expanded workbook exceeds 60 MB.')
            raw_header = pd.read_excel(io.BytesIO(content), header=None, nrows=1)
            headers = validate_headers(raw_header.iloc[0].tolist() if len(raw_header) else [])
            df = pd.read_excel(io.BytesIO(content), nrows=MAX_ROWS + 1)
        else:
            raise ValueError('Supported file types: .csv, .xlsx, .xls.')
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Could not read dataset. Check its format, encoding, and workbook contents.') from exc
    if df.empty or len(df) > MAX_ROWS or len(df.columns) > MAX_COLUMNS:
        raise ValueError('Dataset must contain 1–150,000 rows and at most 100 columns.')
    df.columns = headers
    numeric = df.select_dtypes(include='number')
    if np.isinf(numeric.to_numpy(dtype=float, na_value=np.nan)).any():
        raise ValueError('Dataset contains infinite numeric values. Replace them with finite values or blank cells.')
    for col in df.select_dtypes(include=['object', 'string']).columns:
        nonnull = df[col].dropna()
        # Only infer dates from date-like strings; leave identifiers intact.
        if len(nonnull) and nonnull.astype(str).str.match(r'^\d{4}-\d{2}-\d{2}').all():
            parsed = pd.to_datetime(df[col], errors='coerce')
            if parsed.notna().sum() == len(nonnull):
                df[col] = parsed
    return df
