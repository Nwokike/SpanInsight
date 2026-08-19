import asyncio
import os


def _resolve_log_dir() -> str:
    """Return the history log directory path."""
    storage_env = os.getenv("FLET_APP_STORAGE_DATA")
    if storage_env:
        base_dir = storage_env
    else:
        # Dev fallback - mirrors .flet/storage/data/ that Flet creates locally
        base_dir = os.path.join(".flet", "storage", "data")
    log_dir = os.path.join(base_dir, "history")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


async def get_log_impl(
    service,
    session_name: str,
    lines: int | None = None,
    event_type: str | None = None,
) -> list:
    """Get session history logs."""

    def _log():
        from colab_cli.history import HistoryLogger

        h = HistoryLogger(log_dir=_resolve_log_dir())
        events = h.get_history(session_name)
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        if lines:
            events = events[-lines:]
        return events

    return await asyncio.to_thread(_log)


async def list_log_sessions_impl(service) -> list:
    """List session names that have history logs."""

    def _list():
        from colab_cli.history import HistoryLogger

        h = HistoryLogger(log_dir=_resolve_log_dir())
        return h.list_sessions()

    return await asyncio.to_thread(_list)


async def export_log_impl(service, session_name: str, output_path: str) -> bool:
    """Export session history to a file."""

    def _export():
        from colab_cli.converter import export_history
        from colab_cli.history import HistoryLogger

        h = HistoryLogger(log_dir=_resolve_log_dir())
        events = h.get_history(session_name)
        if not events:
            return False
        export_history(events, session_name, output_path)
        return True

    return await asyncio.to_thread(_export)
