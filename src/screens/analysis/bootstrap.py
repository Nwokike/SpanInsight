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
    """
    if not session_name or not colab:
        return

    theme_style = "dark_background" if is_dark else "default"
    sns_style = "darkgrid" if is_dark else "whitegrid"

    bootstrap_code = (
        "import os\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
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
        "print('✓ Colab environment ready')"
    )

    try:
        await colab.exec_code(bootstrap_code, session_name=session_name, timeout=15.0)
        logger.info("Colab environment bootstrap completed for %s", session_name)
    except Exception as e:
        logger.warning("Colab bootstrap non-fatal error: %s", e)
