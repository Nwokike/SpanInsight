"""Forms API client — CRUD operations against the D1-backed gateway.

Handles form creation, listing, response fetching, CSV download,
renewal, and deletion under project scopes.
"""

from __future__ import annotations

import logging

from core.constants import API_BASE_URL
from services.api_client import get_client, request_with_retry

logger = logging.getLogger(__name__)


async def create_form(
    project_id: str,
    title: str,
    description: str,
    schema_json: list[dict],
) -> dict | None:
    """Create a form under a project via the gateway. Returns {id, url, expires_at} or None."""

    # Validate schema structure before sending
    if not isinstance(schema_json, list):
        logger.error("Form schema must be a list, got %s", type(schema_json).__name__)
        return None

    valid_types = {
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
    for i, field in enumerate(schema_json):
        if not isinstance(field, dict):
            logger.error("Field %d is not a dict", i)
            return None
        if "name" not in field or "label" not in field or "type" not in field:
            logger.error("Field %d missing required keys (name, label, type)", i)
            return None
        if field["type"] not in valid_types:
            logger.error("Field %d has invalid type: %s", i, field["type"])
            return None

    payload = {
        "project_id": project_id,
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
                project_id,
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


async def list_forms(project_id: str) -> list[dict]:
    """Fetch all forms for a project. Returns list of form dicts."""
    if not project_id:
        return []
    try:
        client = get_client()
        resp = await client.get(
            f"{API_BASE_URL}/forms",
            params={"project_id": project_id},
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json().get("forms", [])
        return []
    except Exception as e:
        logger.error("List forms error: %s", e)
        return []


async def get_responses(form_id: str, project_id: str = "") -> dict:
    """Fetch all responses for a form inside a project. Returns {count, responses}."""
    try:
        client = get_client()
        params = {}
        if project_id:
            params["project_id"] = project_id
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


async def renew_form(form_id: str, project_id: str = "") -> str | None:
    """Extend form expiry by 7 days. Returns new expires_at or None."""
    try:
        resp = await request_with_retry(
            "POST",
            f"{API_BASE_URL}/forms/{form_id}/renew",
            json={"project_id": project_id} if project_id else None,
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
    try:
        client = get_client()
        resp = await client.request(
            "DELETE",
            f"{API_BASE_URL}/forms/{form_id}",
            json={"project_id": project_id} if project_id else None,
            timeout=10.0,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error("Delete form error: %s", e)
        return False


def responses_to_csv_bytes(responses: list[dict]) -> bytes:
    """Convert a list of response dicts to CSV bytes for download.

    Each response has a 'data' dict with field values.
    """
    if not responses:
        return b""

    import csv
    import io

    rows = [r["data"] for r in responses]
    if not rows:
        return b""

    # Collect all unique field names preserving order
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")
