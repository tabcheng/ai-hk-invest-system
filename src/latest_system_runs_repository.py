from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

TABLE_NAME = "latest_system_runs"
_ALLOWED_STATUS = {"success", "failed", "partial", "unknown"}


def _iso_or_none(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_latest_system_run_upsert_payload(
    *,
    run_id: int | str,
    business_date: date,
    status: str,
    source: str,
    data_timestamp: datetime,
    summary_json: dict[str, Any],
    risk_summary_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_status = status.strip().lower()
    if normalized_status not in _ALLOWED_STATUS:
        raise ValueError("status must be one of success/failed/partial/unknown")

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": str(run_id),
        "business_date": business_date.isoformat(),
        "status": normalized_status,
        "source": source,
        "data_timestamp": _iso_or_none(data_timestamp),
        "summary_json": summary_json,
        "risk_summary_json": risk_summary_json or {},
    }

    if payload["summary_json"].get("paper_trade_only") is not True:
        raise ValueError("summary_json.paper_trade_only must be true")

    return payload


def upsert_latest_system_run(client: Any, payload: dict[str, Any]) -> None:
    payload_for_write = dict(payload)
    payload_for_write["updated_at"] = datetime.now(timezone.utc).isoformat()
    (
        client.table(TABLE_NAME)
        .upsert(payload_for_write, on_conflict="source", returning="minimal")
        .execute()
    )


def get_latest_system_run(client: Any, *, source: str = "paper_daily_runner") -> dict[str, Any] | None:
    result = (
        client.table(TABLE_NAME)
        .select(
            "id,run_id,business_date,status,source,data_timestamp,summary_json,risk_summary_json,created_at,updated_at"
        )
        .eq("source", source)
        .order("updated_at", desc=True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = list(result.data or [])
    return rows[0] if rows else None
