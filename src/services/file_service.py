"""File service v2 — file validation and Colab upload helpers.

All heavy data loading (pandas, numpy) now happens on Colab.
This service handles local file picking, validation, and upload coordination.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported file types for upload to Colab
UPLOAD_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".txt",
    ".xlsx",
    ".xls",
    ".json",
    ".jsonl",
    ".parquet",
    ".pq",
    ".xml",
    ".dta",  # Stata
    ".sas7bdat",  # SAS
    ".pkl",
    ".pickle",
    ".zip",
    ".gz",
    ".tar",
    ".py",
    ".ipynb",
    ".h5",
    ".hdf5",
    ".feather",
    ".sqlite",
    ".db",
    ".png",
    ".jpg",
    ".jpeg",
}

# 100MB max upload
MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024
MAX_UPLOAD_SIZE_MB = 100


class FileValidationError(Exception):
    """Raised when a file fails validation checks."""


def validate_file(file_path: str) -> None:
    """Validate file extension and size. Raises FileValidationError on failure."""
    path = Path(file_path)

    ext = path.suffix.lower()
    if ext not in UPLOAD_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file type: '{ext}'. "
            f"Supported: {', '.join(sorted(UPLOAD_EXTENSIONS))}"
        )

    try:
        size = os.path.getsize(file_path)
    except OSError:
        raise FileValidationError(
            "Could not read file. It may have been moved or deleted."
        )

    if size > MAX_UPLOAD_SIZE_BYTES:
        raise FileValidationError(
            f"File is too large ({size / (1024 * 1024):.1f} MB). "
            f"Maximum upload size is {MAX_UPLOAD_SIZE_MB} MB."
        )

    if size == 0:
        raise FileValidationError("File is empty (0 bytes).")


def get_file_info(file_path: str) -> dict:
    """Get basic file info without loading it."""
    path = Path(file_path)
    return {
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": os.path.getsize(file_path),
        "size_mb": os.path.getsize(file_path) / (1024 * 1024),
    }


def suggest_load_code(file_name: str) -> str:
    """Suggest Python code to load a file on Colab based on its extension."""
    ext = Path(file_name).suffix.lower()
    path = f"/content/{file_name}"

    if ext in (".csv", ".tsv", ".txt"):
        sep = "\\t" if ext == ".tsv" else ","
        return f'import pandas as pd\ndf = pd.read_csv("{path}", sep="{sep}")\nprint(f"Loaded {{len(df):,}} rows × {{len(df.columns)}} cols")\ndf.head()'

    if ext in (".xlsx", ".xls"):
        return f'import pandas as pd\ndf = pd.read_excel("{path}")\nprint(f"Loaded {{len(df):,}} rows × {{len(df.columns)}} cols")\ndf.head()'

    if ext in (".json", ".jsonl"):
        return f'import pandas as pd\ndf = pd.read_json("{path}")\nprint(f"Loaded {{len(df):,}} rows × {{len(df.columns)}} cols")\ndf.head()'

    if ext in (".parquet", ".pq"):
        return f'import pandas as pd\ndf = pd.read_parquet("{path}")\nprint(f"Loaded {{len(df):,}} rows × {{len(df.columns)}} cols")\ndf.head()'

    if ext == ".feather":
        return f'import pandas as pd\ndf = pd.read_feather("{path}")\nprint(f"Loaded {{len(df):,}} rows × {{len(df.columns)}} cols")\ndf.head()'

    if ext in (".sqlite", ".db"):
        return f'import sqlite3\nimport pandas as pd\nconn = sqlite3.connect("{path}")\ntables = pd.read_sql("SELECT name FROM sqlite_master WHERE type=\'table\'", conn)\nprint("Tables:", tables["name"].tolist())'

    if ext in (".pkl", ".pickle"):
        return f'import pandas as pd\ndf = pd.read_pickle("{path}")\nprint(f"Loaded {{type(df).__name__}}")\ndf.head() if hasattr(df, "head") else df'

    if ext in (".h5", ".hdf5"):
        return f'import pandas as pd\ndf = pd.read_hdf("{path}")\nprint(f"Loaded {{len(df):,}} rows × {{len(df.columns)}} cols")\ndf.head()'

    if ext in (".png", ".jpg", ".jpeg"):
        return f'from PIL import Image\nimport matplotlib.pyplot as plt\nimg = Image.open("{path}")\nplt.imshow(img)\nplt.axis("off")\nplt.title("{file_name}")\nplt.show()'

    if ext == ".ipynb":
        return f'# Notebook uploaded: {path}\nimport json\nwith open("{path}") as f:\n    nb = json.load(f)\nprint(f"Cells: {{len(nb.get(\'cells\', []))}}")'

    # Generic fallback
    return f'import os\nprint(f"File: {path}")\nprint(f"Size: {{os.path.getsize(\\"{path}\\"):,}} bytes")'


def detect_spatial_columns(df) -> dict | None:
    """Detect latitude/longitude column pairs in a DataFrame.

    Returns:
        Dict with 'lat' and 'lon' keys mapping to column names, or None.
    """
    lat_names = {"lat", "latitude", "y", "lat_col", "geo_lat"}
    lon_names = {"lon", "lng", "longitude", "x", "lon_col", "geo_lon", "long"}

    if df is None:
        return None

    cols_lower = {c.lower(): c for c in df.columns}

    lat_col = None
    lon_col = None
    for name in lat_names:
        if name in cols_lower:
            lat_col = cols_lower[name]
            break
    for name in lon_names:
        if name in cols_lower:
            lon_col = cols_lower[name]
            break

    if lat_col and lon_col:
        return {"lat": lat_col, "lon": lon_col}
    return None
