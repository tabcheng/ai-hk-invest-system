from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Mapping, Protocol


_HKT = timezone(timedelta(hours=8))
_RUNTIME_SOURCE = "railway_runtime_env"
_MAX_SHA_SHORT_LEN = 12


class MiniAppReadDataProvider(Protocol):
    def get_latest_system_run_summary(self) -> dict[str, Any]:
        """Return a bounded latest-system-run summary for Mini App read model."""


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

    def get_latest_system_run_summary(self) -> dict[str, Any]:
        generated_at = self._now.astimezone(_HKT) if self._now else datetime.now(_HKT)

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
            "generated_at_hkt": generated_at.isoformat(),
        }
