from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping, Protocol

from src.market_data.review_provider import build_review_shell_market_data_provider
from src.market_data.smoke import (
    build_market_acceptance_by_ticker,
    build_market_data_acceptance_summary,
    classify_market_data_freshness,
)

_HKT = timezone(timedelta(hours=8))
_RUNTIME_SOURCE = "railway_runtime_env"
_NOT_CONFIGURED_SOURCE = "not_configured"
_LOCAL_ARTIFACT_SOURCE = "local_artifact"
_LOCAL_ARTIFACT_MAX_BYTES = 16 * 1024
_LATEST_SYSTEM_RUN_ALLOWED_STATUSES = {"success", "failed", "partial", "unknown"}
_MAX_RUN_ID_LEN = 80
_MAX_TIME_LEN = 40
_MAX_SUMMARY_LEN = 500
_MAX_LIMITATIONS = 5
_MAX_LIMITATION_ITEM_LEN = 160
_MAX_SHA_SHORT_LEN = 12


class MiniAppReadDataProvider(Protocol):
    def get_runtime_status_summary(self) -> dict[str, Any]:
        """Return bounded backend runtime status metadata for Mini App runner_status section."""

    def get_latest_system_run_summary(self) -> dict[str, Any]:
        """Return bounded latest-system-run contract for Mini App latest_system_run section."""

    def get_daily_review_summary(self) -> dict[str, Any]:
        """Return bounded daily-review-summary contract for Mini App daily_review_summary section."""

    def get_signals_summary(self) -> dict[str, Any]:
        """Return bounded signals-summary contract for Mini App signals_summary section."""

    def get_paper_pnl_summary(self) -> dict[str, Any]:
        """Return bounded paper-PnL summary contract for Mini App paper_pnl_summary section."""

    def get_risk_summary(self) -> dict[str, Any]:
        """Return bounded risk-summary contract for Mini App risk_summary section."""

    def get_decision_context_summary(self) -> dict[str, Any]:
        """Return bounded per-ticker decision context summary for review-shell."""

    def get_ticker_level_paper_portfolio_review(self) -> dict[str, Any]:
        """Return bounded ticker-level paper portfolio review section."""

    def get_ai_team_packet_summary(self) -> dict[str, Any]:
        """Return bounded AI team packet summary for read-only operator surfaces."""


class RailwayRuntimeEnvMiniAppReadDataProvider:
    """Bounded internal provider backed by Railway runtime environment metadata only."""

    def __init__(self, env: Mapping[str, str] | None = None, now: datetime | None = None):
        self._env = env or {}
        self._now = now

    @staticmethod
    def _safe_env_get(env: Mapping[str, str], key: str) -> str | None:
        value = str(env.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _short_commit_sha(value: str | None) -> str | None:
        if not value:
            return None
        normalized = "".join(re.findall(r"[0-9a-fA-F]", value.strip()))
        if not normalized:
            return None
        return normalized.lower()[:_MAX_SHA_SHORT_LEN]

    def _generated_at_hkt(self) -> str:
        generated_at = self._now.astimezone(_HKT) if self._now else datetime.now(_HKT)
        return generated_at.isoformat()

    def get_runtime_status_summary(self) -> dict[str, Any]:
        service_name = self._safe_env_get(self._env, "RAILWAY_SERVICE_NAME")
        environment = self._safe_env_get(self._env, "RAILWAY_ENVIRONMENT_NAME")
        git_branch = self._safe_env_get(self._env, "RAILWAY_GIT_BRANCH")
        git_commit_sha_short = self._short_commit_sha(
            self._safe_env_get(self._env, "RAILWAY_GIT_COMMIT_SHA")
        )
        deployment_id = self._safe_env_get(self._env, "RAILWAY_DEPLOYMENT_ID")

        status = "ok" if all([service_name, environment, git_branch, git_commit_sha_short]) else "unknown"

        return {
            "status": status,
            "source": _RUNTIME_SOURCE,
            "service_name": service_name,
            "environment": environment,
            "git_branch": git_branch,
            "git_commit_sha_short": git_commit_sha_short,
            "deployment_id_present": bool(deployment_id),
            "generated_at_hkt": self._generated_at_hkt(),
        }

    def get_latest_system_run_summary(self) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "source": _NOT_CONFIGURED_SOURCE,
            "run_id": None,
            "run_status": None,
            "started_at_hkt": None,
            "completed_at_hkt": None,
            "data_timestamp_hkt": None,
            "summary": None,
            "limitations": ["No production data source configured in Step 86."],
        }

    def get_daily_review_summary(self) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "source": "daily_review_read_model",
            "reason": "daily review summary is not available yet",
            "boundary": "read-only review surface; no decision capture, no order creation, no broker/live execution",
        }

    def get_signals_summary(self) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "source": "signals_read_model",
            "reason": "signals summary is not available yet",
            "operator_note": "信號摘要暫時未有資料；可先檢視系統運行狀態及每日檢視摘要。",
            "boundary": "read-only signals summary; no decision capture, no order creation, no broker/live execution",
        }

    def get_paper_pnl_summary(self) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "source": "paper_pnl_read_model",
            "paper_trade_only": True,
            "business_date": None,
            "data_timestamp_hkt": None,
            "updated_at_hkt": None,
            "total_positions": 0,
            "open_positions": 0,
            "closed_positions": 0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_pnl": 0.0,
            "currency": "HKD",
            "reason": "paper PnL source not available yet",
            "limitations": ["No production paper PnL read model configured yet."],
        }

    def get_risk_summary(self) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "source": "risk_read_model",
            "paper_trade_only": True,
            "business_date": None,
            "data_timestamp_hkt": None,
            "updated_at_hkt": None,
            "risk_level": "unknown",
            "total_exposure": None,
            "cash_usage": None,
            "exposure_pct": None,
            "concentration_notes": [],
            "max_position_pct": None,
            "warnings": [],
            "reason": "risk source not available yet",
            "limitations": ["No production risk summary read model configured yet."],
        }

    def get_decision_context_summary(self) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "paper_trade_only": True,
            "business_date": None,
            "data_timestamp_hkt": None,
            "source": "review_shell_decision_context",
            "context_readiness": "insufficient",
            "tickers": [],
            "global_limitations": ["No production decision context source configured yet."],
        }

    def get_ticker_level_paper_portfolio_review(self) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "source": "paper_pnl_read_model",
            "paper_trade_only": True,
            "rows": [],
            "limitations": ["No production ticker-level paper portfolio read model configured yet."],
        }

    def get_ai_team_packet_summary(self) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "source": "latest_system_runs",
            "paper_trade_only": True,
            "decision_support_only": True,
            "reason": "AI Team packet summary is not available yet",
            "boundary": "read-only AI simulated context only; no broker/live execution",
        }


def _format_hkt_display(value: Any) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(_HKT).strftime("%Y-%m-%d %H:%M:%S HKT")


def _safe_int_counter(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return 0
        try:
            return int(float(normalized))
        except ValueError:
            return 0
    return 0


def _safe_int_metric(value: Any, default: int = 0) -> int:
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return default
        try:
            return int(float(normalized))
        except ValueError:
            return default
    return default


def _safe_float_metric(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return default
        try:
            return float(normalized)
        except ValueError:
            return default
    return default


class SupabaseLatestSystemRunMiniAppReadDataProvider(RailwayRuntimeEnvMiniAppReadDataProvider):
    def __init__(self, *, client: Any | None, env: Mapping[str, str] | None = None, now: datetime | None = None):
        super().__init__(env=env, now=now)
        self._client = client
        self._cached_latest_row: dict[str, Any] | None = None
        self._latest_row_loaded = False
        self._cached_signals_summary: dict[str, Any] | None = None
        self._signals_summary_loaded = False
        self._cached_paper_pnl_summary: dict[str, Any] | None = None
        self._paper_pnl_summary_loaded = False
        self._cached_risk_summary: dict[str, Any] | None = None
        self._risk_summary_loaded = False

    @staticmethod
    def _unavailable(boundary: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "source": "latest_system_runs",
            "reason": "latest bounded row is not available yet",
            "boundary": boundary,
        }

    def get_latest_system_run_summary(self) -> dict[str, Any]:
        boundary = "read-only latest-state row; no broker/live execution"
        row = self._get_latest_row()

        if not isinstance(row, dict) or not row:
            return self._unavailable(boundary)

        summary = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
        if summary.get("paper_trade_only") is not True:
            return self._unavailable(boundary)

        return {
            "status": "ok",
            "source": "latest_system_runs",
            "business_date": str(row.get("business_date") or ""),
            "run_id": str(row.get("run_id") or ""),
            "runner_status": str(row.get("status") or "unknown"),
            "data_timestamp_hkt": _format_hkt_display(row.get("data_timestamp")),
            "updated_at_hkt": _format_hkt_display(row.get("updated_at")),
            "paper_trade_only": True,
            "processed_tickers": _safe_int_counter(summary.get("processed_tickers")),
            "successful_tickers": _safe_int_counter(summary.get("successful_tickers")),
            "failed_tickers": _safe_int_counter(summary.get("failed_tickers")),
            "boundary": boundary,
        }

    def get_daily_review_summary(self) -> dict[str, Any]:
        boundary = "read-only review surface; no decision capture, no order creation, no broker/live execution"
        unavailable = {
            "status": "unavailable",
            "source": "daily_review_read_model",
            "reason": "daily review summary is not available yet",
            "boundary": boundary,
        }
        if self._client is None:
            return unavailable

        row = self._get_latest_row()
        if not isinstance(row, dict) or not row:
            return unavailable
        summary = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
        if summary.get("paper_trade_only") is not True:
            return unavailable
        available_sections = ["latest_system_run"]
        unavailable_sections: list[str] = []
        signals_summary = self.get_signals_summary()
        paper_pnl_summary = self.get_paper_pnl_summary()
        risk_summary = self.get_risk_summary()
        if signals_summary.get("status") == "ok":
            available_sections.append("signals")
        else:
            unavailable_sections.append("signals")
        if paper_pnl_summary.get("status") == "ok":
            available_sections.append("paper_pnl")
        else:
            unavailable_sections.append("paper_pnl")
        if risk_summary.get("status") == "ok":
            available_sections.append("risk")
        else:
            unavailable_sections.append("risk")
        review_readiness = "ready" if len(unavailable_sections) == 0 else "partial"
        return {
            "status": "ok",
            "source": "daily_review_read_model",
            "business_date": str(row.get("business_date") or ""),
            "run_id": str(row.get("run_id") or ""),
            "runner_status": str(row.get("status") or "unknown"),
            "data_timestamp_hkt": _format_hkt_display(row.get("data_timestamp")),
            "updated_at_hkt": _format_hkt_display(row.get("updated_at")),
            "paper_trade_only": True,
            "review_readiness": review_readiness,
            "processed_tickers": _safe_int_counter(summary.get("processed_tickers")),
            "successful_tickers": _safe_int_counter(summary.get("successful_tickers")),
            "failed_tickers": _safe_int_counter(summary.get("failed_tickers")),
            "available_sections": available_sections,
            "unavailable_sections": unavailable_sections,
            "operator_note": "Read-only partial daily review summary from latest system run only; human final decision remains outside system.",
            "boundary": boundary,
        }

    def get_paper_pnl_summary(self) -> dict[str, Any]:
        if self._paper_pnl_summary_loaded and self._cached_paper_pnl_summary is not None:
            return self._cached_paper_pnl_summary
        boundary = "read-only paper summary; no order creation, no broker/live execution"
        unavailable = {
            "status": "unavailable",
            "source": "paper_pnl_read_model",
            "paper_trade_only": True,
            "business_date": None,
            "data_timestamp_hkt": None,
            "updated_at_hkt": None,
            "total_positions": 0,
            "open_positions": 0,
            "closed_positions": 0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_pnl": 0.0,
            "currency": "HKD",
            "reason": "paper PnL source not available yet",
            "limitations": ["資料未有"],
            "boundary": boundary,
        }
        row = self._get_latest_row()
        if not isinstance(row, dict) or not row or self._client is None:
            self._paper_pnl_summary_loaded = True
            self._cached_paper_pnl_summary = unavailable
            return unavailable
        summary = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
        if summary.get("paper_trade_only") is not True:
            self._paper_pnl_summary_loaded = True
            self._cached_paper_pnl_summary = unavailable
            return unavailable
        from src.paper_trading import get_paper_position_pnl_review_snapshot
        try:
            snap = get_paper_position_pnl_review_snapshot(self._client)
        except Exception:
            self._paper_pnl_summary_loaded = True
            self._cached_paper_pnl_summary = unavailable
            return unavailable
        if not isinstance(snap, dict):
            self._paper_pnl_summary_loaded = True
            self._cached_paper_pnl_summary = unavailable
            return unavailable
        per_symbol_raw = snap.get("per_symbol")
        per_symbol = per_symbol_raw if isinstance(per_symbol_raw, list) else []
        realized = _safe_float_metric(snap.get("total_realized_pnl"), default=0.0)
        unrealized = _safe_float_metric(snap.get("total_unrealized_pnl"), default=0.0)
        limitations: list[str] = []
        if not isinstance(per_symbol_raw, list):
            limitations.append("per_symbol malformed; bounded to empty list")
        if any(
            [
                isinstance(snap.get("open_positions_count"), bool),
                isinstance(snap.get("closed_positions_count"), bool),
                isinstance(snap.get("total_realized_pnl"), bool),
                isinstance(snap.get("total_unrealized_pnl"), bool),
            ]
        ):
            limitations.append("one or more numeric fields were malformed; bounded defaults applied")
        result = {
            "status": "ok",
            "source": "paper_pnl_read_model",
            "paper_trade_only": True,
            "business_date": str(row.get("business_date") or ""),
            "data_timestamp_hkt": _format_hkt_display(row.get("data_timestamp")),
            "updated_at_hkt": _format_hkt_display(row.get("updated_at")),
            "total_positions": len(per_symbol),
            "open_positions": _safe_int_metric(snap.get("open_positions_count"), default=0),
            "closed_positions": _safe_int_metric(snap.get("closed_positions_count"), default=0),
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            "total_pnl": realized + unrealized,
            "currency": "HKD",
            "limitations": limitations[:_MAX_LIMITATIONS],
            "boundary": boundary,
        }
        self._paper_pnl_summary_loaded = True
        self._cached_paper_pnl_summary = result
        return result

    def get_ticker_level_paper_portfolio_review(self) -> dict[str, Any]:
        if self._client is None:
            return {
                "status": "unavailable",
                "source": "paper_pnl_read_model",
                "paper_trade_only": True,
                "rows": [],
                "limitations": ["Supabase client unavailable."],
            }
        from src.paper_trading import (
            build_ticker_level_paper_portfolio_review,
            get_paper_position_pnl_review_snapshot,
        )
        try:
            snap = get_paper_position_pnl_review_snapshot(self._client)
        except Exception:
            return {
                "status": "unavailable",
                "source": "paper_pnl_read_model",
                "paper_trade_only": True,
                "rows": [],
                "limitations": ["Ticker-level paper portfolio snapshot unavailable."],
            }
        if not isinstance(snap, dict):
            return {
                "status": "unavailable",
                "source": "paper_pnl_read_model",
                "paper_trade_only": True,
                "rows": [],
                "limitations": ["Ticker-level paper portfolio snapshot unavailable."],
            }
        ticker_scope = [
            str(row.get("stock") or "").strip().upper()
            for row in (snap.get("per_symbol") or [])
            if isinstance(row, dict) and str(row.get("stock") or "").strip()
        ] or ["0700.HK", "0388.HK", "1299.HK"]
        market_acceptance_by_ticker = build_market_acceptance_by_ticker(ticker_scope, env=dict(self._env))
        rows = build_ticker_level_paper_portfolio_review(
            snap,
            market_acceptance_by_ticker=market_acceptance_by_ticker,
        )
        return {
            "status": "ok",
            "source": "paper_pnl_read_model",
            "paper_trade_only": True,
            "rows": rows,
            "limitations": ["Read-only paper-trading review only; no order creation."],
        }

    def get_risk_summary(self) -> dict[str, Any]:
        if self._risk_summary_loaded and self._cached_risk_summary is not None:
            return self._cached_risk_summary
        boundary = "read-only risk summary; review only, no order creation, no broker/live execution"
        unavailable = {
            "status": "unavailable",
            "source": "risk_read_model",
            "paper_trade_only": True,
            "business_date": None,
            "data_timestamp_hkt": None,
            "updated_at_hkt": None,
            "risk_level": "unknown",
            "total_exposure": None,
            "cash_usage": None,
            "exposure_pct": None,
            "concentration_notes": [],
            "max_position_pct": None,
            "warnings": [],
            "reason": "risk source not available yet",
            "limitations": ["資料未有"],
            "boundary": boundary,
        }
        row = self._get_latest_row()
        if not isinstance(row, dict) or not row or self._client is None:
            self._risk_summary_loaded = True
            self._cached_risk_summary = unavailable
            return unavailable
        summary = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
        if summary.get("paper_trade_only") is not True:
            self._risk_summary_loaded = True
            self._cached_risk_summary = unavailable
            return unavailable
        from src.paper_trading import get_paper_risk_review_for_run
        try:
            risk = get_paper_risk_review_for_run(self._client, run_id=int(row.get("run_id")))
        except Exception:
            self._risk_summary_loaded = True
            self._cached_risk_summary = unavailable
            return unavailable
        if not isinstance(risk, dict):
            self._risk_summary_loaded = True
            self._cached_risk_summary = unavailable
            return unavailable
        blocked = _safe_int_metric(risk.get("total_blocked_buys"), default=0)
        warned = _safe_int_metric(risk.get("total_warning_buys"), default=0)
        executed = _safe_int_metric(risk.get("total_executed_buys"), default=0)
        limitations: list[str] = []
        if any(
            [
                isinstance(risk.get("total_blocked_buys"), bool),
                isinstance(risk.get("total_warning_buys"), bool),
                isinstance(risk.get("total_executed_buys"), bool),
            ]
        ):
            limitations.append("one or more risk count fields were malformed; bounded defaults applied")
        risk_level = "high" if blocked > 0 else ("medium" if warned > 0 else ("low" if executed > 0 else "unknown"))
        warnings: list[str] = []
        if blocked > 0:
            warnings.append(f"{blocked} blocked paper buy risk event(s)")
        if warned > 0:
            warnings.append(f"{warned} warning paper buy risk event(s)")
        result = {
            "status": "ok",
            "source": "risk_read_model",
            "paper_trade_only": True,
            "business_date": str(row.get("business_date") or ""),
            "data_timestamp_hkt": _format_hkt_display(row.get("data_timestamp")),
            "updated_at_hkt": _format_hkt_display(row.get("updated_at")),
            "risk_level": risk_level,
            "warnings": warnings[:5],
            "limitations": limitations[:_MAX_LIMITATIONS],
            "boundary": boundary,
        }
        self._risk_summary_loaded = True
        self._cached_risk_summary = result
        return result

    def get_signals_summary(self) -> dict[str, Any]:
        if self._signals_summary_loaded and self._cached_signals_summary is not None:
            return self._cached_signals_summary
        boundary = "read-only signals summary; no decision capture, no order creation, no broker/live execution"
        unavailable = {
            "status": "unavailable",
            "source": "signals_read_model",
            "reason": "signals summary is not available yet",
            "operator_note": "信號摘要暫時未有資料；可先檢視系統運行狀態及每日檢視摘要。",
            "boundary": boundary,
        }
        row = self._get_latest_row()
        if not isinstance(row, dict) or not row:
            self._signals_summary_loaded = True
            self._cached_signals_summary = unavailable
            return unavailable
        summary = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
        if summary.get("paper_trade_only") is not True:
            self._signals_summary_loaded = True
            self._cached_signals_summary = unavailable
            return unavailable
        if self._client is None:
            self._signals_summary_loaded = True
            self._cached_signals_summary = unavailable
            return unavailable
        run_id = row.get("run_id")
        if run_id is None:
            self._signals_summary_loaded = True
            self._cached_signals_summary = unavailable
            return unavailable

        try:
            result = (
                self._client.table("signals")
                .select("stock,signal,reason,date,run_id")
                .eq("date", str(row.get("business_date") or ""))
                .eq("run_id", run_id)
                .order("id", desc=False)
                .limit(20)
                .execute()
            )
            signal_rows = result.data if isinstance(result.data, list) else []
        except Exception:
            self._signals_summary_loaded = True
            self._cached_signals_summary = unavailable
            return unavailable
        if not signal_rows:
            self._signals_summary_loaded = True
            self._cached_signals_summary = unavailable
            return unavailable

        def _norm_signal(value: Any) -> str:
            normalized = str(value or "").strip().upper()
            return {"BUY": "positive", "HOLD": "neutral", "SELL": "negative"}.get(normalized, "unknown")

        counts = {"positive": 0, "neutral": 0, "negative": 0, "unknown": 0}
        ticker_set: set[str] = set()
        top_items: list[dict[str, Any]] = []
        for item in signal_rows:
            ticker = str(item.get("stock") or "").strip()
            label = _norm_signal(item.get("signal"))
            counts[label] += 1
            if ticker:
                ticker_set.add(ticker)
            if len(top_items) < 5:
                top_items.append({
                    "ticker": ticker,
                    "display_name": ticker,
                    "signal_label": label,
                    "confidence_label": "unknown",
                    "reason_short": str(item.get("reason") or "").strip()[:120] or None,
                    "data_timestamp_hkt": _format_hkt_display(row.get("data_timestamp")),
                })

        result = {
            "status": "ok",
            "source": "signals_read_model",
            "business_date": str(row.get("business_date") or ""),
            "run_id": str(row.get("run_id") or ""),
            "data_timestamp_hkt": _format_hkt_display(row.get("data_timestamp")),
            "updated_at_hkt": _format_hkt_display(row.get("updated_at")),
            "paper_trade_only": True,
            "review_readiness": "ready",
            "shown_signals": len(signal_rows),
            "shown_positive_signals": counts["positive"],
            "shown_neutral_signals": counts["neutral"],
            "shown_negative_signals": counts["negative"],
            "shown_unknown_signals": counts["unknown"],
            "covered_tickers": len(ticker_set),
            "top_items_limit": 5,
            "top_items": top_items,
            "operator_note": "AI 模擬信號只供檢視，不是買賣指示；真實交易決定仍由人類在系統外作出。",
            "boundary": boundary,
        }
        self._signals_summary_loaded = True
        self._cached_signals_summary = result
        return result

    def get_decision_context_summary(self) -> dict[str, Any]:
        default_provider = RailwayRuntimeEnvMiniAppReadDataProvider()
        row = self._get_latest_row()
        if not isinstance(row, dict) or not row or self._client is None:
            return default_provider.get_decision_context_summary()
        summary = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
        if summary.get("paper_trade_only") is not True:
            return default_provider.get_decision_context_summary()

        signals = self.get_signals_summary()
        risk = self.get_risk_summary()
        if signals.get("status") != "ok":
            return {
                "status": "partial",
                "paper_trade_only": True,
                "business_date": str(row.get("business_date") or ""),
                "data_timestamp_hkt": _format_hkt_display(row.get("data_timestamp")),
                "source": "review_shell_decision_context",
                "context_readiness": "insufficient",
                "tickers": [],
                "global_limitations": ["Signals unavailable; ticker-level decision context not ready."],
            }

        tickers: list[dict[str, Any]] = []
        risk_level = risk.get("risk_level", "unknown") if risk.get("status") == "ok" else "unknown"
        risk_warnings = risk.get("warnings", []) if risk.get("status") == "ok" else []
        risk_limitations = (
            risk.get("limitations", [])
            if risk.get("status") == "ok"
            else ["Risk data not available yet."]
        )

        market_provider = build_review_shell_market_data_provider(env=dict(self._env))
        for item in signals.get("top_items", [])[:5]:
            ticker = str(item.get("ticker") or "").strip()
            market_snapshot = market_provider.get_ticker_market_snapshot(ticker, str(row.get("business_date") or ""))
            freshness_meta = classify_market_data_freshness(
                data_timestamp_hkt=market_snapshot.data_timestamp_hkt,
                provider_freshness_status=market_snapshot.freshness_status,
                delay_minutes=market_snapshot.delay_minutes,
            )
            missing_context = [
                {"key": "latest_price_missing", "label_zh": "最新價 / Reference price：未有資料", "label_en": "Reference price unavailable", "status": "missing"},
                {"key": "liquidity_missing", "label_zh": "流動性 / 成交額：未有資料", "label_en": "Liquidity/turnover unavailable", "status": "missing"},
                {"key": "fundamentals_missing", "label_zh": "基本面 / Fundamentals：未有資料", "label_en": "Fundamentals unavailable", "status": "missing"},
                {"key": "news_catalyst_missing", "label_zh": "新聞 / Catalyst：未有資料", "label_en": "News/catalyst unavailable", "status": "missing"},
                {"key": "valuation_missing", "label_zh": "估值 / Valuation：未有資料", "label_en": "Valuation unavailable", "status": "missing"},
                {"key": "per_position_exposure_missing", "label_zh": "持倉級別 exposure：未有資料", "label_en": "Per-position exposure unavailable", "status": "missing"},
                {"key": "data_source_missing", "label_zh": "資料來源 / Data source：未有資料", "label_en": "Data source unavailable", "status": "missing"},
            ]
            if not summary.get("strategy_version"):
                missing_context.append({"key": "strategy_version_missing", "label_zh": "策略版本 / Strategy version：未有資料", "label_en": "Strategy version unavailable", "status": "missing"})
            if market_snapshot.reference_price is not None:
                missing_context = [x for x in missing_context if x.get("key") != "latest_price_missing"]
            if market_snapshot.turnover is not None or market_snapshot.volume is not None:
                missing_context = [x for x in missing_context if x.get("key") != "liquidity_missing"]
            if market_snapshot.status in {"ok", "partial"} and market_snapshot.data_source:
                missing_context = [x for x in missing_context if x.get("key") != "data_source_missing"]
            tickers.append(
                {
                    "ticker": ticker,
                    "signal": {
                        "direction": item.get("signal_label"),
                        "confidence": item.get("confidence_label", "unknown"),
                        "reason": item.get("reason_short"),
                        "strategy_version": summary.get("strategy_version"),
                        "data_timestamp_hkt": item.get("data_timestamp_hkt")
                        or signals.get("data_timestamp_hkt"),
                    },
                    "market": {
                        "status": market_snapshot.status,
                        "reference_price": market_snapshot.reference_price,
                        "previous_close": market_snapshot.previous_close,
                        "change": market_snapshot.change,
                        "change_pct": market_snapshot.change_pct,
                        "volume": market_snapshot.volume,
                        "turnover": market_snapshot.turnover,
                        "currency": market_snapshot.currency,
                        "market": market_snapshot.market,
                        "data_source": market_snapshot.data_source,
                        "data_timestamp_hkt": market_snapshot.data_timestamp_hkt,
                        "freshness_status": market_snapshot.freshness_status,
                        "freshness_status_display": freshness_meta.get("freshness_status_display"),
                        "freshness_label_zh": freshness_meta.get("freshness_label_zh"),
                        "freshness_label_en": freshness_meta.get("freshness_label_en"),
                        "freshness_warning": freshness_meta.get("freshness_warning"),
                        "data_age_minutes": freshness_meta.get("data_age_minutes"),
                        "data_age_hours": freshness_meta.get("data_age_hours"),
                        "is_stale": freshness_meta.get("is_stale"),
                        **build_market_data_acceptance_summary(
                            freshness_status_display=freshness_meta.get("freshness_status_display")
                        ),
                        "delay_minutes": market_snapshot.delay_minutes,
                        "adjustment_policy": market_snapshot.adjustment_policy,
                        "confidence": market_snapshot.confidence,
                        "limitations": market_snapshot.limitations,
                    },
                    "paper_position": {
                        "status": "unavailable",
                        "position_qty": None,
                        "avg_cost": None,
                        "unrealized_pnl": None,
                        "exposure_pct": None,
                        "limitations": ["Selected ticker position/exposure not available yet."],
                    },
                    "risk": {
                        "risk_level": risk_level,
                        "warnings": risk_warnings,
                        "limitations": risk_limitations,
                    },
                    "missing_context": missing_context,
                    "limitations": [
                        "Provider boundary is bounded to review-shell market snapshot fields only."
                    ],
                }
            )
        return {
            "status": "partial",
            "paper_trade_only": True,
            "business_date": str(row.get("business_date") or ""),
            "data_timestamp_hkt": signals.get("data_timestamp_hkt"),
            "source": "review_shell_decision_context",
            "context_readiness": "insufficient",
            "tickers": tickers,
            "global_limitations": [
                "Market data fields unavailable from current bounded read sources."
            ],
        }

    def get_ai_team_packet_summary(self) -> dict[str, Any]:
        row = self._get_latest_row()
        if not isinstance(row, dict) or not row:
            return RailwayRuntimeEnvMiniAppReadDataProvider().get_ai_team_packet_summary()
        summary = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
        packet = summary.get("ai_team_packet") if isinstance(summary.get("ai_team_packet"), dict) else None
        if not isinstance(packet, dict):
            return RailwayRuntimeEnvMiniAppReadDataProvider().get_ai_team_packet_summary()
        return {
            "status": str(packet.get("status") or "unavailable")[:40],
            "source": "latest_system_runs",
            "schema_version": str(packet.get("schema_version") or "")[:64],
            "packet_schema_version": str(packet.get("packet_schema_version") or "")[:64],
            "paper_trade_only": bool(packet.get("paper_trade_only", True)),
            "decision_support_only": bool(packet.get("decision_support_only", True)),
            "covered_tickers": _safe_int_counter(packet.get("covered_tickers")),
            "slot_status_counts": packet.get("slot_status_counts")
            if isinstance(packet.get("slot_status_counts"), dict)
            else {"ok": 0, "partial": 0, "missing": 0, "unknown": 0},
            "simulated_direction_counts": packet.get("simulated_direction_counts")
            if isinstance(packet.get("simulated_direction_counts"), dict)
            else {"insufficient_data": 0, "watch_only": 0, "mixed_watch": 0},
            "top_gaps": [str(x)[:80] for x in list(packet.get("top_gaps") or [])[:5]],
            "limitations": [str(x)[:120] for x in list(packet.get("limitations") or [])[:5]],
            "boundary": "read-only AI simulated context only; no broker/live execution",
        }

    def _get_latest_row(self) -> dict[str, Any] | None:
        if self._latest_row_loaded:
            return self._cached_latest_row
        self._latest_row_loaded = True
        if self._client is None:
            self._cached_latest_row = None
            return None
        from src.latest_system_runs_repository import get_latest_system_run
        try:
            row = get_latest_system_run(self._client, source="paper_daily_runner")
        except Exception:
            self._cached_latest_row = None
            return None
        self._cached_latest_row = row if isinstance(row, dict) else None
        return self._cached_latest_row


class LocalArtifactMiniAppReadDataProvider(RailwayRuntimeEnvMiniAppReadDataProvider):
    """Bounded provider for latest-system-run based on local JSON artifact only."""

    def __init__(
        self,
        artifact_path: str | None,
        env: Mapping[str, str] | None = None,
        now: datetime | None = None,
    ):
        super().__init__(env=env, now=now)
        self._artifact_path = str(artifact_path or "").strip()

    @staticmethod
    def _unavailable_summary(limitation: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "source": _LOCAL_ARTIFACT_SOURCE,
            "run_id": None,
            "run_status": None,
            "started_at_hkt": None,
            "completed_at_hkt": None,
            "data_timestamp_hkt": None,
            "summary": None,
            "limitations": [limitation],
        }

    @staticmethod
    def _truncate_str(value: Any, max_len: int) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized[:max_len]

    @staticmethod
    def _bounded_run_id(value: Any) -> str | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            text = str(value)
        elif isinstance(value, str):
            text = value.strip()
        else:
            return None
        if not text:
            return None
        return text[:_MAX_RUN_ID_LEN]

    @staticmethod
    def _bounded_limitations(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        bounded: list[str] = []
        for item in value:
            limited = LocalArtifactMiniAppReadDataProvider._truncate_str(item, _MAX_LIMITATION_ITEM_LEN)
            if limited is None:
                continue
            bounded.append(limited)
            if len(bounded) >= _MAX_LIMITATIONS:
                break
        return bounded

    def get_latest_system_run_summary(self) -> dict[str, Any]:
        if not self._artifact_path:
            return self._unavailable_summary("Local artifact path is not configured.")

        try:
            artifact_path = Path(self._artifact_path)
            artifact_size = artifact_path.stat().st_size
            if artifact_size > _LOCAL_ARTIFACT_MAX_BYTES:
                return self._unavailable_summary("Local artifact exceeds maximum allowed size.")
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return self._unavailable_summary("Local artifact is missing or invalid JSON.")

        if not isinstance(payload, dict):
            return self._unavailable_summary("Local artifact root must be a JSON object.")

        run_id = payload.get("run_id")
        run_status = payload.get("run_status")
        started_at_hkt = payload.get("started_at_hkt")
        completed_at_hkt = payload.get("completed_at_hkt")
        data_timestamp_hkt = payload.get("data_timestamp_hkt")
        summary = payload.get("summary")
        limitations = payload.get("limitations")

        bounded_run_id = self._bounded_run_id(run_id)
        if bounded_run_id is None:
            return self._unavailable_summary("Local artifact schema is incomplete for latest_system_run.")
        bounded_run_status = self._truncate_str(run_status, max_len=32)
        if bounded_run_status is None or bounded_run_status not in _LATEST_SYSTEM_RUN_ALLOWED_STATUSES:
            return self._unavailable_summary("Local artifact schema is incomplete for latest_system_run.")

        return {
            "status": "ok",
            "source": _LOCAL_ARTIFACT_SOURCE,
            "run_id": bounded_run_id,
            "run_status": bounded_run_status,
            "started_at_hkt": self._truncate_str(started_at_hkt, _MAX_TIME_LEN),
            "completed_at_hkt": self._truncate_str(completed_at_hkt, _MAX_TIME_LEN),
            "data_timestamp_hkt": self._truncate_str(data_timestamp_hkt, _MAX_TIME_LEN),
            "summary": self._truncate_str(summary, _MAX_SUMMARY_LEN),
            "limitations": self._bounded_limitations(limitations),
        }
