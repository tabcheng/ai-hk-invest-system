from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

_MAX_ARTIFACT_BYTES = 16 * 1024
_ALLOWED_RUN_STATUSES = {"success", "failed", "partial", "unknown"}
_MAX_RUN_ID_LEN = 80
_MAX_TIME_LEN = 40
_MAX_SUMMARY_LEN = 500
_MAX_LIMITATIONS = 5
_MAX_LIMITATION_ITEM_LEN = 160
_ARTIFACT_KEYS = {
    "run_id",
    "run_status",
    "started_at_hkt",
    "completed_at_hkt",
    "data_timestamp_hkt",
    "summary",
    "limitations",
}


def _truncate_str(value: Any, max_len: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:max_len]


def _bounded_run_id(value: str | int | None) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:_MAX_RUN_ID_LEN]


def _bounded_limitations(value: list[str] | None) -> list[str]:
    if not isinstance(value, list):
        return []
    bounded: list[str] = []
    for item in value:
        limited = _truncate_str(item, _MAX_LIMITATION_ITEM_LEN)
        if limited is None:
            continue
        bounded.append(limited)
        if len(bounded) >= _MAX_LIMITATIONS:
            break
    return bounded


def build_latest_system_run_artifact(
    *,
    run_id: str | int | None,
    run_status: str,
    started_at_hkt: str | None = None,
    completed_at_hkt: str | None = None,
    data_timestamp_hkt: str | None = None,
    summary: str | None = None,
    limitations: list[str] | None = None,
) -> dict[str, object]:
    bounded_run_id = _bounded_run_id(run_id)
    if bounded_run_id is None:
        raise ValueError("run_id must be non-empty string/int")

    bounded_run_status = _truncate_str(run_status, 32)
    if bounded_run_status not in _ALLOWED_RUN_STATUSES:
        raise ValueError("run_status must be one of: success, failed, partial, unknown")

    return {
        "run_id": bounded_run_id,
        "run_status": bounded_run_status,
        "started_at_hkt": _truncate_str(started_at_hkt, _MAX_TIME_LEN),
        "completed_at_hkt": _truncate_str(completed_at_hkt, _MAX_TIME_LEN),
        "data_timestamp_hkt": _truncate_str(data_timestamp_hkt, _MAX_TIME_LEN),
        "summary": _truncate_str(summary, _MAX_SUMMARY_LEN),
        "limitations": _bounded_limitations(limitations),
    }


def _normalize_artifact_payload(artifact: Mapping[str, object]) -> dict[str, object]:
    unexpected = sorted(set(artifact.keys()) - _ARTIFACT_KEYS)
    if unexpected:
        raise ValueError(f"artifact contains unsupported keys: {', '.join(unexpected)}")

    return build_latest_system_run_artifact(
        run_id=artifact.get("run_id"),
        run_status=str(artifact.get("run_status", "") or ""),
        started_at_hkt=artifact.get("started_at_hkt") if isinstance(artifact.get("started_at_hkt"), str) else None,
        completed_at_hkt=artifact.get("completed_at_hkt") if isinstance(artifact.get("completed_at_hkt"), str) else None,
        data_timestamp_hkt=(
            artifact.get("data_timestamp_hkt")
            if isinstance(artifact.get("data_timestamp_hkt"), str)
            else None
        ),
        summary=artifact.get("summary") if isinstance(artifact.get("summary"), str) else None,
        limitations=artifact.get("limitations") if isinstance(artifact.get("limitations"), list) else None,
    )


def write_latest_system_run_artifact(path: str | Path, artifact: Mapping[str, object]) -> Path:
    target = Path(path)
    normalized = _normalize_artifact_payload(artifact)
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    encoded = payload.encode("utf-8")
    if len(encoded) > _MAX_ARTIFACT_BYTES:
        raise ValueError("artifact exceeds 16KB size cap")

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp_file:
            tmp_file.write(encoded)
            tmp_path = Path(tmp_file.name)
        tmp_path.replace(target)
        return target
    finally:
        if tmp_path and tmp_path.exists() and tmp_path != target:
            try:
                tmp_path.unlink()
            except OSError:
                pass
