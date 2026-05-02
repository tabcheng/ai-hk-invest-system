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

    def get_latest_system_run_summary(self) -> dict[str, Any]:
        if not self._artifact_path:
            return self._unavailable_summary("Local artifact path is not configured.")

        try:
            payload = json.loads(Path(self._artifact_path).read_text(encoding="utf-8"))
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

        if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
            return self._unavailable_summary("Local artifact schema is incomplete for latest_system_run.")
        if not isinstance(run_status, str) or not run_status.strip():
            return self._unavailable_summary("Local artifact schema is incomplete for latest_system_run.")

        return {
            "status": "ok",
            "source": _LOCAL_ARTIFACT_SOURCE,
            "run_id": run_id,
            "run_status": run_status.strip(),
            "started_at_hkt": started_at_hkt if isinstance(started_at_hkt, str) else None,
            "completed_at_hkt": completed_at_hkt if isinstance(completed_at_hkt, str) else None,
            "data_timestamp_hkt": data_timestamp_hkt if isinstance(data_timestamp_hkt, str) else None,
            "summary": summary if isinstance(summary, str) else None,
            "limitations": [item for item in limitations if isinstance(item, str)]
            if isinstance(limitations, list)
            else [],
        }
