"""Dedicated scheduled daily-runner entrypoint.

This module keeps Railway cron execution focused on one explicit entrypoint
(`python -m src.daily_runner`) while preserving existing runtime behavior by
reusing `src.app.main` as the daily run orchestrator.
"""

from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone

ENTRYPOINT = "python -m src.daily_runner"
SCHEDULE_BASIS = "HKT 20:00 (Railway cron UTC: 0 12 * * *)"
SUCCESS_STATUS = "success"
FAILED_STATUS = "failed"
_MAX_ERROR_SUMMARY_LENGTH = 240


def _utc_now() -> datetime:
    """Return the current UTC timestamp.

    Keeping this in one helper allows focused tests to monkeypatch time for
    deterministic duration and lifecycle-summary assertions.
    """

    return datetime.now(timezone.utc)


def _summarize_error(exc: Exception) -> str:
    """Return a short, safe error summary for operator review logs.

    Guardrail: include only exception type + message (trimmed) so logs are
    useful for triage while avoiding oversized/raw trace payloads in summary
    lines. Full traceback is still emitted separately to stderr.
    """

    normalized_message = " ".join(str(exc).split())
    raw_summary = f"{exc.__class__.__name__}: {normalized_message}"
    if len(raw_summary) <= _MAX_ERROR_SUMMARY_LENGTH:
        return raw_summary
    return raw_summary[: _MAX_ERROR_SUMMARY_LENGTH - 3] + "..."


def _print_execution_summary(
    *,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    error_summary: str | None = None,
) -> None:
    """Emit a consistent single-line JSON execution summary."""

    duration_seconds = max((finished_at - started_at).total_seconds(), 0.0)
    summary = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round(duration_seconds, 6),
        "status": status,
        "entrypoint": ENTRYPOINT,
        "schedule_basis": SCHEDULE_BASIS,
    }
    if error_summary is not None:
        summary["error_summary"] = error_summary

    # Single JSON line keeps scheduled-run logs concise, grep-able, and easy
    # for human operators to review after each run.
    print(f"[daily_runner] execution_summary={json.dumps(summary, sort_keys=True)}")


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

    started_at = _utc_now()
    print(f"[daily_runner] started entrypoint={ENTRYPOINT} started_at={started_at.isoformat()}")

    try:
        _run_daily_pipeline()
    except Exception as exc:
        finished_at = _utc_now()
        error_summary = _summarize_error(exc)
        print(
            "[daily_runner] failed "
            f"entrypoint={ENTRYPOINT} finished_at={finished_at.isoformat()} error_summary={error_summary}"
        )
        _print_execution_summary(
            started_at=started_at,
            finished_at=finished_at,
            status=FAILED_STATUS,
            error_summary=error_summary,
        )
        traceback.print_exc()
        return 1

    finished_at = _utc_now()
    print(f"[daily_runner] completed entrypoint={ENTRYPOINT} finished_at={finished_at.isoformat()}")
    _print_execution_summary(
        started_at=started_at,
        finished_at=finished_at,
        status=SUCCESS_STATUS,
    )
    return 0


def main() -> None:
    """CLI entrypoint for `python -m src.daily_runner`."""

    raise SystemExit(run())


if __name__ == "__main__":
    main()
