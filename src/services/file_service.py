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
    ".sav",  # SPSS
    ".sas7bdat",  # SAS
    ".pkl",
    ".pickle",
    ".zip",
    ".gz",
    ".tar",
    ".npy",  # NumPy array
    ".npz",  # NumPy archive
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
    """Suggest Python code to load a file on Colab based on its extension.

    Every tabular branch MUST leave a ``df`` DataFrame in the kernel — the
    schema extractor looks for it. Non-tabular branches leave ``data`` or
    print honest info instead of pretending to be a DataFrame.
    """
    ext = Path(file_name).suffix.lower()
    path = f"/content/{file_name}"

    loaded_tail = (
        'print(f"Loaded {len(df):,} rows × {len(df.columns)} cols")\ndf.head()'
    )

    if ext in (".csv", ".tsv"):
        sep = "\\t" if ext == ".tsv" else ","
        return (
            "import pandas as pd\n"
            "df = None\n"
            "for _enc in ('utf-8', 'latin-1'):\n"
            "    try:\n"
            f'        df = pd.read_csv("{path}", sep="{sep}", encoding=_enc)\n'
            "        break\n"
            "    except UnicodeDecodeError:\n"
            "        continue\n"
            "if df is None:\n"
            f'    raise ValueError("Could not decode {file_name} as utf-8 or latin-1")\n'
            + loaded_tail
        )

    if ext == ".txt":
        # Delimiter-sniffed text (v1 parity): sep=None + python engine detects the separator
        return (
            "import pandas as pd\n"
            "df = None\n"
            "for _enc in ('utf-8', 'latin-1'):\n"
            "    try:\n"
            f'        df = pd.read_csv("{path}", sep=None, engine="python", encoding=_enc)\n'
            "        break\n"
            "    except UnicodeDecodeError:\n"
            "        continue\n"
            "if df is None:\n"
            f'    raise ValueError("Could not decode {file_name} as utf-8 or latin-1")\n'
            + loaded_tail
        )

    if ext in (".xlsx", ".xls"):
        return f'import pandas as pd\ndf = pd.read_excel("{path}")\n' + loaded_tail

    if ext in (".json", ".jsonl"):
        return f'import pandas as pd\ndf = pd.read_json("{path}")\n' + loaded_tail

    if ext in (".parquet", ".pq"):
        return f'import pandas as pd\ndf = pd.read_parquet("{path}")\n' + loaded_tail

    if ext == ".feather":
        return f'import pandas as pd\ndf = pd.read_feather("{path}")\n' + loaded_tail

    if ext in (".sqlite", ".db"):
        return (
            "import sqlite3\n"
            "import pandas as pd\n"
            f'conn = sqlite3.connect("{path}")\n'
            "tables = pd.read_sql(\"SELECT name FROM sqlite_master WHERE type='table'\", conn)\n"
            'print("Tables:", tables["name"].tolist())\n'
            "if not tables.empty:\n"
            '    _t = tables["name"].iloc[0]\n'
            "    df = pd.read_sql_query(f'SELECT * FROM \"{_t}\"', conn)\n"
            "    print(f'Loaded table {_t}: {len(df):,} rows × {len(df.columns)} cols')\n"
            "    df.head()"
        )

    if ext in (".pkl", ".pickle"):
        return (
            "import pandas as pd\n"
            f'df = pd.read_pickle("{path}")\n'
            'print(f"Loaded {type(df).__name__}")\n'
            'df.head() if hasattr(df, "head") else df'
        )

    if ext in (".h5", ".hdf5"):
        return f'import pandas as pd\ndf = pd.read_hdf("{path}")\n' + loaded_tail

    if ext == ".dta":
        return f'import pandas as pd\ndf = pd.read_stata("{path}")\n' + loaded_tail

    if ext == ".sav":
        return f'import pandas as pd\ndf = pd.read_spss("{path}")\n' + loaded_tail

    if ext == ".sas7bdat":
        return f'import pandas as pd\ndf = pd.read_sas("{path}")\n' + loaded_tail

    if ext in (".npy", ".npz"):
        return (
            "import numpy as np\n"
            f'data = np.load("{path}")\n'
            'print(f"Loaded NumPy data: '
            "{data.shape if hasattr(data, 'shape') else list(data.files)}\")"
        )

    if ext == ".zip":
        # Extract then load the first tabular member into df (v1 parity)
        return (
            "import zipfile\n"
            "import pandas as pd\n"
            f'with zipfile.ZipFile("{path}", "r") as z:\n'
            '    z.extractall("/content/extracted")\n'
            "    _names = z.namelist()\n"
            'print("Extracted", len(_names), "files")\n'
            "_tabular = [n for n in _names if n.lower().endswith(('.csv', '.tsv', '.xlsx', '.json', '.parquet'))]\n"
            "if _tabular:\n"
            '    _target = "/content/extracted/" + _tabular[0]\n'
            '    _ext = _tabular[0].lower().rsplit(".", 1)[-1]\n'
            '    if _ext == "xlsx":\n'
            "        df = pd.read_excel(_target)\n"
            '    elif _ext == "json":\n'
            "        df = pd.read_json(_target)\n"
            '    elif _ext == "parquet":\n'
            "        df = pd.read_parquet(_target)\n"
            "    else:\n"
            "        df = None\n"
            "        for _enc in ('utf-8', 'latin-1'):\n"
            "            try:\n"
            "                df = pd.read_csv(_target, encoding=_enc)\n"
            "                break\n"
            "            except UnicodeDecodeError:\n"
            "                continue\n"
            '    print(f"Loaded {_tabular[0]}")\n'
            "    df.head()\n"
            "else:\n"
            '    print("No tabular file inside archive:", _names[:10])'
        )

    if ext in (".png", ".jpg", ".jpeg"):
        return (
            "from PIL import Image\n"
            "import matplotlib.pyplot as plt\n"
            f'img = Image.open("{path}")\n'
            "plt.imshow(img)\n"
            'plt.axis("off")\n'
            f'plt.title("{file_name}")\n'
            "plt.show()"
        )

    if ext == ".ipynb":
        return (
            "# Notebook uploaded\n"
            "import json\n"
            f'with open("{path}") as f:\n'
            "    nb = json.load(f)\n"
            "print(f\"Cells: {len(nb.get('cells', []))}\")"
        )

    # Generic fallback — honest info dump, never pretends to be a dataset
    return (
        "import os\n"
        f'print(f"File: {path}")\n'
        f'print(f"Size: {{os.path.getsize("{path}"):,}} bytes")'
    )


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
