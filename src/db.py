from datetime import date, datetime, timezone

from supabase import Client


def build_signal_payload(signal_data: dict, signal_date: date | None = None) -> dict:
    effective_date = signal_date or datetime.now(timezone.utc).date()
    return {
        "date": effective_date.isoformat(),
        "stock": signal_data["stock"],
        "signal": signal_data["signal"],
        "price": signal_data["price"],
        "reason": signal_data["reason"],
    }


def save_signal(client: Client, signal_data: dict, run_id: int | None = None) -> None:
    payload = build_signal_payload(signal_data)
    # Attach run linkage when available so every persisted daily signal row can be
    # traced back to the parent run record for auditing/debugging.
    if run_id is not None:
        payload["run_id"] = run_id

    result = (
        client.table("signals")
        .upsert(
            payload,
            on_conflict="date,stock",
            ignore_duplicates=True,
            returning="representation",
        )
        .execute()
    )

    if result.data:
        print(f"Inserted into Supabase: {payload}")
    else:
        # Same-day reruns may hit the unique (date, stock) constraint. We keep the
        # original dedup behavior but still relink that existing row to the current
        # run so downstream artifacts never reference a newer run while signals point
        # at an older one.
        if run_id is not None:
            # Only re-link run lineage; do not mutate signal values on reruns so
            # strategy outputs remain consistent with existing same-day dedup rules.
            client.table("signals").update({"run_id": run_id}).eq("date", payload["date"]).eq(
                "stock", payload["stock"]
            ).execute()
        print(
            "Duplicate protection triggered: "
            f"signal already exists for {signal_data['stock']} on {payload['date']}."
        )

    print(f"Supabase response: {result}")
