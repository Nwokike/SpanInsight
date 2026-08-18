"""File picker service.

Wraps ``ft.FilePicker`` to provide a clean async API for picking files.

Critical Flet 0.85.0 note: FilePicker is a Service, NOT a Control.
Do NOT add it to page.overlay — it causes "Unknown control: FilePicker".
Just instantiate and call pick_files() directly.

Based on Akili flet-rewrite's production pattern.
"""

from __future__ import annotations

import logging
import mimetypes
from collections.abc import Callable

import flet as ft

logger = logging.getLogger(__name__)


class FilePickerService:
    """File picker helper.

    Simplifies the flow of picking a file and reading its content as bytes.
    """

    def __init__(self, page: ft.Page, on_result: Callable | None = None):
        self._page = page
        self._on_result = on_result

        # Flet 0.85: FilePicker is a Service, NOT a Control. Do not add to overlay.
        self._picker = ft.FilePicker()

    def pick_data_file(self):
        """Trigger the data file picker dialog (CSV/Excel)."""
        self._page.run_task(self._run_data_picker)

    def pick_image(self):
        """Trigger the image file picker dialog."""
        self._page.run_task(self._run_image_picker)

    async def pick_files_async(
        self,
        allowed_extensions: list[str] | None = None,
        file_type: ft.FilePickerFileType = ft.FilePickerFileType.ANY,
    ) -> list | None:
        """Direct async call — returns file list or None."""
        try:
            result = await self._picker.pick_files(
                allow_multiple=False,
                allowed_extensions=allowed_extensions,
                file_type=file_type,
                with_data=True,
            )
            return result
        except Exception as e:
            logger.error("File picking failed: %s", e)
            return None

    async def save_file_async(
        self,
        file_name: str,
        allowed_extensions: list[str] | None = None,
        src_bytes: bytes | None = None,
    ) -> str | None:
        """Trigger the save file picker dialog natively."""
        try:
            result = await self._picker.save_file(
                file_name=file_name,
                allowed_extensions=allowed_extensions,
                src_bytes=src_bytes,
            )
            return result
        except Exception as e:
            logger.error("File saving failed: %s", e)
            return None

    async def _run_data_picker(self):
        """Async picker logic for CSV/Excel/JSON/XML/Stata/SAS/delimited files."""
        try:
            from core.constants import ALLOWED_EXTENSIONS

            allowed = [ext.lstrip(".") for ext in ALLOWED_EXTENSIONS]

            result = await self._picker.pick_files(
                allow_multiple=False,
                allowed_extensions=allowed,
                with_data=False,  # We read from path for large data files
            )

            if result and len(result) > 0:
                file = result[0]
                if self._on_result:
                    self._on_result(file)
            else:
                logger.info("File picking cancelled by user")

        except Exception as e:
            logger.error("Data file picking failed: %s", e)
            from core.utils import show_snack

            show_snack(self._page, f"File picker error: {e}", error=True)

    async def _run_image_picker(self):
        """Async picker logic for images (vision AI)."""
        try:
            result = await self._picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["png", "jpg", "jpeg", "webp"],
                file_type=ft.FilePickerFileType.IMAGE,
                with_data=True,  # Get bytes directly for multimodal AI
            )

            if result and len(result) > 0:
                file = result[0]
                if file.bytes and self._on_result:
                    mime, _ = mimetypes.guess_type(file.name)
                    if not mime:
                        ext = (
                            file.name.split(".")[-1].lower() if "." in file.name else ""
                        )
                        mime_map = {"png": "image/png", "webp": "image/webp"}
                        mime = mime_map.get(ext, "image/jpeg")
                    self._on_result(file.bytes, mime, file.name)
            else:
                logger.info("Image picking cancelled by user")

        except Exception as e:
            logger.error("Image picking failed: %s", e)
