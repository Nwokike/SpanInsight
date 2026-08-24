"""Forms API client - CRUD operations against the D1-backed gateway.

Handles form creation, listing, response fetching, CSV download,
renewal, and deletion under project scopes.
"""

from __future__ import annotations

import logging

from core.constants import API_BASE_URL
from services.api_client import get_client, request_with_retry

logger = logging.getLogger(__name__)


def _resolve_project_id(project_id: str) -> str:
    """Resolve project_id falling back to state.active_project_id or state.user_uuid."""
    if project_id and project_id.strip():
        return project_id.strip()
    from core.state import state

    return (state.active_project_id or state.user_uuid or "").strip()


_VALID_FIELD_TYPES = frozenset(
    {
        "text",
        "textarea",
        "number",
        "email",
        "select",
        "radio",
        "checkbox",
        "date",
        "phone",
        "url",
        "rating",
    }
)


def _validate_schema(schema_json: list[dict]) -> str | None:
    """Return an error string for the first invalid field, else None.

    Checks structure/type AND that every question has a non-empty UNIQUE
    ``name`` - it is the storage key for collected responses.
    """
    if not isinstance(schema_json, list):
        return f"Form schema must be a list, got {type(schema_json).__name__}"
    seen_names: set[str] = set()
    for i, field in enumerate(schema_json):
        if not isinstance(field, dict):
            return f"Field {i} is not a dict"
        for key in ("name", "label", "type"):
            if key not in field:
                return f"Field {i} missing required key '{key}'"
        if field["type"] not in _VALID_FIELD_TYPES:
            return f"Field {i} has invalid type: {field['type']}"
        name = str(field.get("name") or "").strip()
        if not name:
            return f"Field {i} ('{field['label']}') has an empty name"
        if name in seen_names:
            return f"Field {i} ('{field['label']}') duplicates the name '{name}'"
        seen_names.add(name)
    return None


async def create_form(
    project_id: str,
    title: str,
    description: str,
    schema_json: list[dict],
) -> dict | None:
    """Create a form under a project via the gateway. Returns {id, url, expires_at} or None."""

    resolved_project_id = _resolve_project_id(project_id)
    if not resolved_project_id:
        logger.error("Create form failed: No active project or user identity found.")
        return None

    error = _validate_schema(schema_json)
    if error:
        logger.error("Create form rejected: %s", error)
        return None

    payload = {
        "project_id": resolved_project_id,
        "title": title,
        "description": description,
        "schema_json": schema_json,
    }
    try:
        resp = await request_with_retry(
            "POST",
            f"{API_BASE_URL}/forms",
            json=payload,
            timeout=10.0,
        )
        if resp.status_code == 201:
            data = resp.json()
            logger.info(
                "Form created under project %s: %s → %s",
                resolved_project_id,
                data["id"],
                data["url"],
            )
            return data
        logger.error(
            "Create form failed HTTP %d: %s", resp.status_code, resp.text[:200]
        )
        return None
    except Exception as e:
        logger.error("Create form error: %s", e)
        return None


async def update_form(
    form_id: str,
    project_id: str,
    title: str,
    description: str,
    schema_json: list[dict],
) -> bool:
    """Update a LIVE published form in place (smart merge).

    The gateway keeps every surviving question's collected answers and
    permanently purges answers of removed questions. Share URL and id are
    unchanged. Returns True on success.
    """
    resolved_project_id = _resolve_project_id(project_id)
    if not resolved_project_id:
        logger.error("Update form failed: No active project or user identity found.")
        return False

    error = _validate_schema(schema_json)
    if error:
        logger.error("Update form rejected: %s", error)
        return False

    payload = {
        "project_id": resolved_project_id,
        "title": title,
        "description": description,
        "schema_json": schema_json,
    }
    try:
        resp = await request_with_retry(
            "PATCH",
            f"{API_BASE_URL}/forms/{form_id}",
            json=payload,
            timeout=15.0,
        )
        if resp.status_code == 200:
            logger.info("Live form %s updated in place", form_id)
            return True
        logger.error(
            "Update form failed HTTP %d: %s", resp.status_code, resp.text[:200]
        )
        return False
    except Exception as e:
        logger.error("Update form error: %s", e)
        return False


async def list_forms(project_id: str = "") -> list[dict]:
    """Fetch all forms for a project or user scope. Returns list of form dicts."""
    resolved_project_id = _resolve_project_id(project_id)
    if not resolved_project_id:
        return []
    try:
        client = get_client()
        resp = await client.get(
            f"{API_BASE_URL}/forms",
            params={"project_id": resolved_project_id},
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json().get("forms", [])
        return []
    except Exception as e:
        logger.error("List forms error: %s", e)
        return []


async def get_form(form_id: str) -> dict | None:
    """Fetch one form's FULL definition (including parsed schema_json).

    Uses the public GET /forms/{id} route - the project list route omits
    schema_json to keep listings light, so any edit/detail flow that needs
    the actual questions must hydrate through here.
    """
    if not form_id:
        return None
    try:
        client = get_client()
        resp = await client.get(f"{API_BASE_URL}/forms/{form_id}", timeout=10.0)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        logger.error("Get form error: %s", e)
        return None


async def get_responses(form_id: str, project_id: str = "") -> dict:
    """Fetch one page of responses for a form. Returns {count, responses}."""
    resolved_project_id = _resolve_project_id(project_id)
    try:
        client = get_client()
        params = {}
        if resolved_project_id:
            params["project_id"] = resolved_project_id
        resp = await client.get(
            f"{API_BASE_URL}/forms/{form_id}/responses",
            params=params,
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"count": 0, "responses": []}
    except Exception as e:
        logger.error("Get responses error: %s", e)
        return {"count": 0, "responses": []}


async def fetch_all_responses(form_id: str, project_id: str = "") -> list[dict]:
    """Fetch EVERY response for a form, walking gateway pagination.

    The gateway serves RESPONSES_PAGE_SIZE (200) rows per page; exports need
    the complete set, not just page 1.
    """
    resolved_project_id = _resolve_project_id(project_id)
    all_rows: list[dict] = []
    page = 1
    total = None
    try:
        client = get_client()
        while True:
            params = {"page": page}
            if resolved_project_id:
                params["project_id"] = resolved_project_id
            resp = await client.get(
                f"{API_BASE_URL}/forms/{form_id}/responses",
                params=params,
                timeout=20.0,
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            total = int(data.get("count", 0) or 0)
            rows = data.get("responses", []) or []
            all_rows.extend(rows)
            if not rows or len(all_rows) >= total:
                break
            page += 1
            if page > 500:  # hard safety bound (~100k rows)
                break
        return all_rows
    except Exception as e:
        logger.error("Fetch all responses error: %s", e)
        return all_rows


async def renew_form(form_id: str, project_id: str = "") -> str | None:
    """Extend form expiry by 7 days. Returns new expires_at or None."""
    resolved_project_id = _resolve_project_id(project_id)
    try:
        resp = await request_with_retry(
            "POST",
            f"{API_BASE_URL}/forms/{form_id}/renew",
            json={"project_id": resolved_project_id} if resolved_project_id else None,
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json().get("expires_at")
        return None
    except Exception as e:
        logger.error("Renew form error: %s", e)
        return None


async def delete_form(form_id: str, project_id: str = "") -> bool:
    """Delete a form and all its responses under a project."""
    resolved_project_id = _resolve_project_id(project_id)
    try:
        client = get_client()
        resp = await client.request(
            "DELETE",
            f"{API_BASE_URL}/forms/{form_id}",
            json={"project_id": resolved_project_id} if resolved_project_id else None,
            timeout=10.0,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error("Delete form error: %s", e)
        return False


def responses_to_csv_bytes(
    responses: list[dict], schema_fields: list[dict] | None = None
) -> bytes:
    """Convert a list of response dicts to CSV bytes for download.

    Each response has a 'data' dict keyed by question id. Column headers use
    the question's human-readable LABEL from ``schema_fields`` when available;
    unknown or orphaned keys fall back to the raw storage key.
    """
    if not responses:
        return b""

    import csv
    import io

    rows = [r["data"] for r in responses]
    if not rows:
        return b""

    labels_by_name = {
        str(f.get("name")): str(f.get("label") or f.get("name"))
        for f in (schema_fields or [])
        if f.get("name")
    }

    # Collect all unique storage keys preserving order
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    # Human headers; on label collisions keep the unique storage key instead.
    headers = []
    used = set()
    for key in fieldnames:
        label = labels_by_name.get(key, key)
        if label in used:
            label = key
        used.add(label)
        headers.append(label)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(key, "") for key in fieldnames])
    return output.getvalue().encode("utf-8")
