"""Dedicated scheduled daily-runner entrypoint.

This module keeps Railway cron execution focused on one explicit entrypoint
(`python -m src.daily_runner`) while preserving existing runtime behavior by
reusing `src.app.main` as the daily run orchestrator.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone


def _utc_now_iso() -> str:
    """Return a UTC ISO-8601 timestamp for runner observability logging."""
    return datetime.now(timezone.utc).isoformat()


def _run_daily_pipeline() -> None:
    """Load and execute the existing daily pipeline lazily.

    Guardrail: keep module import-time lightweight so simple smoke checks and CLI
    bootstrap diagnostics do not hard-fail before the runner actually executes.
    """
    from src.app import main as app_main

    app_main()


def run() -> int:
    """Execute one daily runner cycle and return a process exit code.

    Exit-code contract for scheduled execution:
    - `0`: Daily run finished without unhandled exception.
    - `1`: Daily run raised an unhandled exception.
    """
    print(f"[daily_runner] started_at={_utc_now_iso()}")
    try:
        _run_daily_pipeline()
    except Exception:
        print(f"[daily_runner] failed_at={_utc_now_iso()}")
        traceback.print_exc()
        return 1

    print(f"[daily_runner] completed_at={_utc_now_iso()}")
    return 0


def main() -> None:
    """CLI entrypoint for `python -m src.daily_runner`."""
    raise SystemExit(run())


if __name__ == "__main__":
    main()
