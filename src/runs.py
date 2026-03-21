from datetime import datetime, timedelta, timezone
from typing import Any

def create_run(client: Any) -> int:
    result = (
        client.table("runs")
        .insert({"status": "RUNNING"}, returning="representation")
        .execute()
    )
    run_id = result.data[0]["id"]
    print(f"Created run record: id={run_id}")
    return run_id


def update_run(client: Any, run_id: int, payload: dict) -> None:
    client.table("runs").update(payload).eq("id", run_id).execute()


def list_recent_runs(client: Any, *, days: int = 5, limit: int = 50) -> list[dict[str, Any]]:
    """
    Read recent run history from the persistent `runs` table.

    Guardrail/traceability note:
    - This function intentionally uses durable DB records instead of log parsing.
    - It is read-only and returns operator-facing metadata only (id/status/time).
    """
    if days <= 0:
        raise ValueError("days must be a positive integer")

    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = (
        client.table("runs")
        .select("id,status,created_at,updated_at")
        .gte("created_at", cutoff.isoformat())
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(result.data or [])
