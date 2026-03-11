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


def save_signal(client: Client, signal_data: dict) -> None:
    payload = build_signal_payload(signal_data)
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
        print(
            "Duplicate protection triggered: "
            f"signal already exists for {signal_data['stock']} on {payload['date']}."
        )

    print(f"Supabase response: {result}")
