from __future__ import annotations
import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
import json


from src.railway_cadence_activation import build_railway_cadence_activation_plan


def build_checklist() -> dict:
    plan = build_railway_cadence_activation_plan()
    return {
        "title": "Railway Scheduled Cadence Activation Checklist (Scaffold Only)",
        "mutation_free": True,
        "railway_api_calls": False,
        "deploy_actions": False,
        "cron_active_claimed": False,
        "manual_refresh_fallback_only": True,
        "guardrails": {
            "paper_only": True,
            "creates_orders": False,
            "broker_connection": False,
            "no_live_execution": True,
        },
        "services": plan,
        "activation_sequence": [
            "Generate checklist from repo scaffold.",
            "Human operator reviews service/env/UTC-cron mapping.",
            "Human operator manually configures Railway services/env/cron.",
            "Human operator deploys and executes post-deploy smoke.",
            "Record status evidence and PASS/FAIL/BLOCKED conclusion in docs/status.md.",
        ],
    }


def to_markdown(payload: dict) -> str:
    lines = [
        "# Railway Scheduled Cadence Activation Checklist (Scaffold Only)",
        "",
        "- This output is repo-side scaffold only; it does not activate Railway cron.",
        "- Railway cron setup/deploy/smoke requires manual human operator actions.",
        "- All schedules are UTC; HKT windows are intent guidance only.",
        "",
    ]
    for row in payload["services"]:
        lines += [
            f"## {row['service_key']}",
            f"- run_type: `{row['run_type']}`",
            f"- intended_hkt_window: {row['intended_hkt_window']}",
            f"- railway_cron_utc: `{row['railway_cron_utc']}`",
            f"- activation_state: `{row['activation_state']}`",
            f"- required_env: {', '.join(row['required_env'])}",
            f"- acceptance_evidence_required: {row['acceptance_evidence_required']}",
            f"- manual_operator_step_required: {row['manual_operator_step_required']}",
            f"- guardrails: paper_only={row['paper_only']}, creates_orders={row['creates_orders']}, broker_connection={row['broker_connection']}",
            f"- notes: {row['notes']}",
            "",
        ]
    lines += [
        "## Post-deploy evidence template",
        "- service_name:",
        "- run_type:",
        "- railway_cron_utc:",
        "- intended_hkt_window:",
        "- deploy_id_or_timestamp:",
        "- run_log_evidence_pointer:",
        "- execution_summary.run_type:",
        "- smoke_command_or_run_id:",
        "- paper_only: true",
        "- creates_orders: false",
        "- broker_connection: false",
        "- no_secrets_observed: true/false",
        "- no_broker_live_order_execution_observed: true/false",
        "- operator_conclusion: PASS / FAIL / BLOCKED",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-md")
    parser.add_argument("--output-json")
    args = parser.parse_args()
    payload = build_checklist()
    md = to_markdown(payload)
    print(md)
    if args.output_md:
        Path(args.output_md).write_text(md, encoding="utf-8")
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
