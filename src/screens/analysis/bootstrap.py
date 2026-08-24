"""Colab VM bootstrap and environment staging utilities."""

from __future__ import annotations

import logging

logger = logging.getLogger("ColabBootstrap")


async def setup_colab_environment(colab, session_name: str, is_dark: bool = False):
    """Silent bootstrap script to initialize Python runtime environment in Colab VM.

    Configures:
    - Clean POSIX directories (/content/data, /content/exports)
    - Matplotlib & Seaborn styling matching app dark/light mode
    - Pandas display options for optimal output formatting
    - python-calamine, the fast Excel engine our load code prefers
    """
    if not session_name or not colab:
        return

    theme_style = "dark_background" if is_dark else "default"
    sns_style = "darkgrid" if is_dark else "whitegrid"

    bootstrap_code = (
        "import os\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        # Fast Excel engine: stock VMs lack python-calamine, so
        # pd.read_excel(engine='calamine') silently fell back to openpyxl,
        # which chokes on large workbooks (hundreds of MB of worksheet XML).
        # Install once per VM - prefer uv (parallel downloads) with plain pip
        # as fallback - and never fail the bootstrap over it.
        "import importlib.util as _ilu, shutil as _sh, subprocess as _sp\n"
        "import sys as _sys, os as _os\n"
        "if _ilu.find_spec('python_calamine') is None:\n"
        "    _attempts = []\n"
        "    if _sh.which('uv'):\n"
        "        _flags = [] if _os.environ.get('VIRTUAL_ENV') else ['--system']\n"
        "        _attempts.append(['uv', 'pip', 'install', '-q'] + _flags + ['python-calamine'])\n"
        "    _attempts.append([_sys.executable, '-m', 'pip', 'install', '-q', 'python-calamine'])\n"
        "    for _cmd in _attempts:\n"
        "        try:\n"
        "            _res = _sp.run(_cmd, timeout=180)\n"
        "            _ilu.invalidate_caches()\n"
        "            if _res.returncode == 0 and _ilu.find_spec('python_calamine'):\n"
        "                print('\\u2713 Installed python-calamine via ' + _cmd[0])\n"
        "                break\n"
        "        except Exception:\n"
        "            continue\n"
        "try:\n"
        "    import seaborn as sns\n"
        f"    sns.set_theme(style='{sns_style}')\n"
        "except Exception:\n"
        "    pass\n"
        f"plt.style.use('{theme_style}')\n"
        "pd.set_option('display.max_columns', 50)\n"
        "pd.set_option('display.width', 1000)\n"
        "os.makedirs('/content/data', exist_ok=True)\n"
        "os.makedirs('/content/exports', exist_ok=True)\n"
        "print('\\u2713 Colab environment ready')"
    )

    try:
        # The one-time calamine install can take ~10-30 s on a fresh VM.
        await colab.exec_code(bootstrap_code, session_name=session_name, timeout=120.0)
        logger.info("Colab environment bootstrap completed for %s", session_name)
    except Exception as e:
        logger.warning("Colab bootstrap non-fatal error: %s", e)
