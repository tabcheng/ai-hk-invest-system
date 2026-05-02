from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping, Protocol


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

        status = (
            "ok" if all([service_name, environment, git_branch, git_commit_sha_short]) else "unknown"
        )

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
