from supabase import Client


def create_run(client: Client) -> int:
    result = (
        client.table("runs")
        .insert({"status": "RUNNING"}, returning="representation")
        .execute()
    )
    run_id = result.data[0]["id"]
    print(f"Created run record: id={run_id}")
    return run_id


def update_run(client: Client, run_id: int, payload: dict) -> None:
    client.table("runs").update(payload).eq("id", run_id).execute()
