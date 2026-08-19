import asyncio
import logging
from collections.abc import Callable

logger = logging.getLogger("colab_files_ops")


async def ls_impl(
    service,
    session_name: str,
    path: str = "/content",
    auth_method: str = "oauth2",
) -> list[dict]:
    """List files at a remote path. Returns list of file dicts."""
    await service._ensure_online()

    def _ls():
        import posixpath

        from colab_cli.auth import AuthProvider
        from colab_cli.common import State
        from colab_cli.contents import ContentsClient

        norm_path = posixpath.normpath(path) if path else ""
        if norm_path == "." or norm_path == "/":
            norm_path = ""

        provider = AuthProvider.ADC if auth_method == "adc" else AuthProvider.OAUTH2
        st = State()
        st.auth_provider = provider
        name = session_name or service._resolve_session(st)
        s = st.store.get(name)
        if not s:
            raise ValueError(f"Session '{name}' not found")

        client = ContentsClient(s)
        data = client.list_dir(norm_path)
        st.history.log_event(name, "file_operation", {"op": "ls", "path": norm_path})

        if data.get("type") == "directory":
            items = data.get("content", [])
            return sorted(
                [
                    {
                        "name": i.get("name"),
                        "type": i.get("type"),
                        "size": i.get("size", 0),
                    }
                    for i in items
                ],
                key=lambda x: (x["type"] != "directory", x["name"]),
            )
        return [
            {
                "name": data.get("name"),
                "type": data.get("type"),
                "size": data.get("size", 0),
            }
        ]

    return await asyncio.to_thread(_ls)


class ProgressReader:
    """File-like reader that tracks byte read progress via callback."""

    def __init__(
        self,
        data: bytes,
        callback: Callable[[int, int], None] | None = None,
    ):
        self._data = data
        self.total = len(data)
        self._offset = 0
        self.callback = callback

    def read(self, size: int = -1) -> bytes:
        if self._offset >= self.total:
            return b""
        if size < 0:
            chunk = self._data[self._offset :]
            self._offset = self.total
        else:
            chunk = self._data[self._offset : self._offset + size]
            self._offset += len(chunk)
        if self.callback:
            try:
                self.callback(self._offset, self.total)
            except Exception:
                pass
        return chunk

    def __len__(self) -> int:
        return self.total


async def upload_impl(
    service,
    session_name: str,
    local_path: str,
    remote_path: str,
    auth_method: str = "oauth2",
    progress_callback: Callable[[int, int], None] | None = None,
) -> bool:
    """Upload a local file to the remote session with high-capacity chunked streaming."""
    await service._ensure_online()

    def _upload():
        import base64
        import os
        import posixpath
        from urllib.parse import quote

        import requests
        from colab_cli.auth import AuthProvider
        from colab_cli.common import State

        norm_remote = posixpath.normpath(remote_path)

        provider = AuthProvider.ADC if auth_method == "adc" else AuthProvider.OAUTH2
        st = State()
        st.auth_provider = provider
        name = session_name or service._resolve_session(st)
        s = st.store.get(name)
        if not s:
            raise ValueError(f"Session '{name}' not found")

        total_file_bytes = os.path.getsize(local_path)
        if progress_callback:
            progress_callback(0, total_file_bytes)

        filename = norm_remote.split("/")[-1]
        quoted_path = quote(norm_remote.strip("/"), safe="/")
        base_url = s.url.rstrip("/")
        url = f"{base_url}/api/contents/{quoted_path}"
        req_params = {"authuser": "0", "colab-runtime-proxy-token": s.token}
        headers = {"Content-Type": "application/json"}

        # 2MB binary chunk size (converts to ~2.6MB base64 JSON payload, well below 32MB Colab limit)
        CHUNK_SIZE = 2 * 1024 * 1024

        with open(local_path, "rb") as f:
            if total_file_bytes <= CHUNK_SIZE:
                # Single chunk upload for small files (<2MB)
                raw_bytes = f.read()
                b64_content = base64.b64encode(raw_bytes).decode("ascii")
                payload = {
                    "name": filename,
                    "path": norm_remote,
                    "type": "file",
                    "format": "base64",
                    "content": b64_content,
                    "chunk": 1,
                }
                resp = requests.put(
                    url,
                    params=req_params,
                    json=payload,
                    headers=headers,
                    timeout=180.0,
                )
                resp.raise_for_status()
                if progress_callback:
                    progress_callback(total_file_bytes, total_file_bytes)
            else:
                # Multi-chunk streaming upload for large files (40MB to 1GB+)
                sent_bytes = 0
                chunk_index = 1
                while True:
                    raw_bytes = f.read(CHUNK_SIZE)
                    if not raw_bytes:
                        break

                    is_last = (sent_bytes + len(raw_bytes)) >= total_file_bytes
                    b64_content = base64.b64encode(raw_bytes).decode("ascii")

                    payload = {
                        "name": filename,
                        "path": norm_remote,
                        "type": "file",
                        "format": "base64",
                        "content": b64_content,
                        "chunk": -1 if is_last else chunk_index,
                    }

                    resp = requests.put(
                        url,
                        params=req_params,
                        json=payload,
                        headers=headers,
                        timeout=180.0,
                    )
                    resp.raise_for_status()

                    sent_bytes += len(raw_bytes)
                    chunk_index += 1
                    if progress_callback:
                        progress_callback(
                            min(sent_bytes, total_file_bytes), total_file_bytes
                        )

        st.history.log_event(
            name,
            "file_operation",
            {
                "op": "upload",
                "local": local_path,
                "remote": norm_remote,
                "bytes": total_file_bytes,
            },
        )
        return True

    return await asyncio.to_thread(_upload)


async def download_impl(
    service,
    session_name: str,
    remote_path: str,
    local_path: str,
    auth_method: str = "oauth2",
) -> bool:
    """Download a remote file to a local path."""
    await service._ensure_online()

    def _download():
        import posixpath

        from colab_cli.auth import AuthProvider
        from colab_cli.common import State
        from colab_cli.contents import ContentsClient

        norm_remote = posixpath.normpath(remote_path)

        provider = AuthProvider.ADC if auth_method == "adc" else AuthProvider.OAUTH2
        st = State()
        st.auth_provider = provider
        name = session_name or service._resolve_session(st)
        s = st.store.get(name)
        if not s:
            raise ValueError(f"Session '{name}' not found")

        client = ContentsClient(s)
        client.download(norm_remote, local_path)
        st.history.log_event(
            name,
            "file_operation",
            {
                "op": "download",
                "remote": norm_remote,
                "local": local_path,
            },
        )
        return True

    return await asyncio.to_thread(_download)


async def download_folder_impl(
    service,
    session_name: str,
    remote_path: str,
    local_path: str,
    auth_method: str = "oauth2",
    on_progress: Callable | None = None,
) -> bool:
    """Download a remote directory as a zip file to a local path."""
    import posixpath

    norm_dir = posixpath.normpath(remote_path)
    if norm_dir.startswith("/content/") or norm_dir == "/content":
        vm_target_dir = norm_dir
    else:
        clean_rel = norm_dir.lstrip("/")
        vm_target_dir = (
            posixpath.join("/content", clean_rel) if clean_rel else "/content"
        )

    base_name = posixpath.basename(vm_target_dir)
    if not base_name:
        base_name = "folder"

    parent_dir = posixpath.dirname(vm_target_dir)
    vm_zip_base = posixpath.join(parent_dir, f"{base_name}_temp")
    vm_zip_path = f"{vm_zip_base}.zip"

    code = f"""
import subprocess, shutil, os
try:
    if shutil.which('zip'):
        subprocess.run(['zip', '-q', '-r', '{vm_zip_base}.zip', '.'], cwd='{vm_target_dir}', check=True, capture_output=True, text=True)
    else:
        shutil.make_archive('{vm_zip_base}', 'zip', '{vm_target_dir}')
except Exception as e:
    shutil.make_archive('{vm_zip_base}', 'zip', '{vm_target_dir}')
"""
    api_path = vm_zip_path

    logger.info(
        f"[colab_service] Zipping remote folder '{vm_target_dir}' on Colab VM into '{vm_zip_path}'..."
    )
    if on_progress:
        on_progress(f"Zipping {base_name} on VM...")

    try:
        outputs = await service.exec_code(
            code=code,
            session_name=session_name,
            auth_method=auth_method,
            timeout=120.0,
        )
        if outputs:
            for out in outputs:
                if out.get("output_type") == "error":
                    ename = out.get("ename", "Error")
                    evalue = out.get("evalue", "")
                    logger.error(
                        f"[colab_service] VM zipping failed: {ename}: {evalue}"
                    )
                    raise RuntimeError(
                        f"Failed to zip folder on VM ({ename}): {evalue}"
                    )

        logger.info(
            f"[colab_service] Zipping completed. Downloading '{api_path}' to '{local_path}' over HTTP..."
        )
        if on_progress:
            on_progress(f"Downloading {api_path} over HTTP...")

        await service.download(
            remote_path=api_path,
            local_path=local_path,
            session_name=session_name,
            auth_method=auth_method,
        )
        logger.info(
            f"[colab_service] Download completed successfully to '{local_path}'. Cleaning up temporary file '{api_path}' on VM..."
        )
        if on_progress:
            on_progress("Cleaning up temporary zip on VM...")
        return True
    finally:
        try:
            await service.rm(
                path=api_path,
                session_name=session_name,
                auth_method=auth_method,
            )
            logger.info(f"[colab_service] Temporary file '{api_path}' removed from VM.")
        except Exception as ex:
            logger.warning(
                f"[colab_service] Failed to remove temporary file '{api_path}': {ex}"
            )


async def rm_impl(
    service, session_name: str, path: str, auth_method: str = "oauth2"
) -> bool:
    """Delete a remote file."""

    def _rm():
        import posixpath

        from colab_cli.auth import AuthProvider
        from colab_cli.common import State
        from colab_cli.contents import ContentsClient

        norm_path = posixpath.normpath(path)

        provider = AuthProvider.ADC if auth_method == "adc" else AuthProvider.OAUTH2
        st = State()
        st.auth_provider = provider
        name = session_name or service._resolve_session(st)
        s = st.store.get(name)
        if not s:
            raise ValueError(f"Session '{name}' not found")

        client = ContentsClient(s)
        client.rm(norm_path)
        st.history.log_event(name, "file_operation", {"op": "rm", "path": norm_path})
        return True

    return await asyncio.to_thread(_rm)
