from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _ensure_repo_root_on_path() -> None:
    repo_root = str(_REPO_ROOT)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_ensure_repo_root_on_path()

from src.backend_data_cadence import (
    build_backend_data_cadence_policy,
    get_effective_run_type,
    plan_backend_auto_refreshes,
)


def run_smoke(requested_run_type: str) -> dict[str, Any]:
    effective_run_type = get_effective_run_type({"AIHK_RUN_TYPE": requested_run_type})
    policy = build_backend_data_cadence_policy()
    plan = plan_backend_auto_refreshes(
        latest_system_run={"market_data_status": "unknown"},
        risk_summary={"risk_level": "unknown", "warnings": ["context insufficient"]},
        stock_dossier_items=[],
        max_items=10,
    )

    manual_policy_items = [row for row in policy if row.get("run_type") == "manual_operator_refresh_fallback"]
    manual_fallback_only = bool(manual_policy_items and manual_policy_items[0].get("manual_fallback_only") is True)

    guardrails = {
        "paper_only": True,
        "creates_orders": False,
        "broker_connection": False,
    }

    user_facing_fields = " ".join(
        str(part).lower()
        for item in list(plan.get("items") or [])
        for part in (
            item.get("reason") or "",
            item.get("operator_hint") or "",
            item.get("target_surface_label") or "",
            item.get("freshness_requirement") or "",
        )
    )
    contains_execution_wording = any(x in user_facing_fields for x in ("buy", "sell", "order", "execute"))

    pass_status = (
        len(policy) > 0
        and plan.get("status") == "ok"
        and plan.get("manual_refresh_fallback_only") is True
        and manual_fallback_only is True
        and all(row.get("paper_only") is True for row in policy)
        and all(row.get("creates_orders") is False for row in policy)
        and all(row.get("broker_connection") is False for row in policy)
        and contains_execution_wording is False
    )

    return {
        "requested_run_type": requested_run_type,
        "effective_run_type": effective_run_type,
        "policy_count": len(policy),
        "manual_refresh_fallback_only": bool(plan.get("manual_refresh_fallback_only") is True and manual_fallback_only is True),
        "auto_refresh_plan": {
            "status": str(plan.get("status") or "unknown"),
            "item_count": len(list(plan.get("items") or [])),
        },
        "contains_execution_wording": contains_execution_wording,
        "guardrails": guardrails,
        "status": "pass" if pass_status else "fail",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backend cadence summary-only smoke.")
    parser.add_argument("--run-type", default="post_close_daily_review")
    parser.add_argument("--output-json")
    args = parser.parse_args()

    report = run_smoke(args.run_type)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
