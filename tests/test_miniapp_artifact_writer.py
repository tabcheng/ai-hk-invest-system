from pathlib import Path
from threading import Thread

import pytest

from src.miniapp_artifact_writer import (
    build_latest_system_run_artifact,
    write_latest_system_run_artifact,
)
from src.miniapp_data_provider import LocalArtifactMiniAppReadDataProvider


def test_build_latest_system_run_artifact_returns_bounded_contract():
    artifact = build_latest_system_run_artifact(
        run_id="r" * 120,
        run_status="success",
        started_at_hkt="s" * 80,
        completed_at_hkt="c" * 80,
        data_timestamp_hkt="d" * 80,
        summary="m" * 900,
        limitations=["x" * 300, " ", "ok", "a" * 200, "b" * 200, "overflow"],
    )

    assert len(artifact["run_id"]) == 80
    assert artifact["run_status"] == "success"
    assert len(artifact["started_at_hkt"]) == 40
    assert len(artifact["completed_at_hkt"]) == 40
    assert len(artifact["data_timestamp_hkt"]) == 40
    assert len(artifact["summary"]) == 500
    assert len(artifact["limitations"]) == 5
    assert all(len(item) <= 160 for item in artifact["limitations"])


def test_build_latest_system_run_artifact_rejects_invalid_required_fields():
    with pytest.raises(ValueError):
        build_latest_system_run_artifact(run_id=None, run_status="success")

    with pytest.raises(ValueError):
        build_latest_system_run_artifact(run_id=89, run_status="completed")


def test_write_latest_system_run_artifact_writes_json_file(tmp_path: Path):
    artifact_path = tmp_path / "artifacts" / "latest_system_run.json"
    artifact = build_latest_system_run_artifact(
        run_id=89,
        run_status="partial",
        summary="Daily runner completed with partial data coverage.",
        limitations=["Paper-trading only", "No broker/live execution"],
    )

    written = write_latest_system_run_artifact(artifact_path, artifact)

    assert written == artifact_path
    assert artifact_path.exists()
    text = artifact_path.read_text(encoding="utf-8")
    assert '"run_id":"89"' in text
    assert '"run_status":"partial"' in text


def test_write_latest_system_run_artifact_applies_bounding_before_write(tmp_path: Path):
    artifact_path = tmp_path / "latest_system_run.json"
    artifact = build_latest_system_run_artifact(
        run_id=89,
        run_status="success",
        summary="s" * 500,
        limitations=["l" * 160] * 5,
    )
    artifact["summary"] = "x" * (16 * 1024)
    write_latest_system_run_artifact(artifact_path, artifact)
    text = artifact_path.read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) <= 16 * 1024


def test_write_latest_system_run_artifact_rejects_unsupported_keys(tmp_path: Path):
    artifact_path = tmp_path / "latest_system_run.json"
    artifact = {
        "run_id": 89,
        "run_status": "success",
        "padding": "should-not-pass",
    }

    with pytest.raises(ValueError):
        write_latest_system_run_artifact(artifact_path, artifact)


def test_writer_generated_artifact_is_readable_by_local_artifact_provider(tmp_path: Path):
    artifact_path = tmp_path / "latest_system_run.json"
    artifact = build_latest_system_run_artifact(
        run_id="89-run",
        run_status="success",
        summary="Step 89 writer/provider compatibility sample.",
    )
    write_latest_system_run_artifact(artifact_path, artifact)

    provider = LocalArtifactMiniAppReadDataProvider(artifact_path=str(artifact_path))
    summary = provider.get_latest_system_run_summary()

    assert summary["status"] == "ok"
    assert summary["source"] == "local_artifact"
    assert summary["run_id"] == "89-run"
    assert summary["run_status"] == "success"
    assert summary["summary"] == "Step 89 writer/provider compatibility sample."


def test_write_latest_system_run_artifact_repeated_writes_leave_no_tmp_files(tmp_path: Path):
    artifact_path = tmp_path / "latest_system_run.json"
    for run_id in range(5):
        artifact = build_latest_system_run_artifact(
            run_id=run_id,
            run_status="success",
            summary=f"run-{run_id}",
        )
        write_latest_system_run_artifact(artifact_path, artifact)

    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == []


def test_write_latest_system_run_artifact_cleanup_tmp_on_replace_failure(tmp_path: Path, monkeypatch):
    artifact_path = tmp_path / "latest_system_run.json"
    artifact = build_latest_system_run_artifact(run_id=1, run_status="success")

    original_replace = Path.replace

    def _fail_replace(self: Path, target: Path):
        if target == artifact_path:
            raise OSError("replace failed")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", _fail_replace)
    with pytest.raises(OSError):
        write_latest_system_run_artifact(artifact_path, artifact)
    assert list(tmp_path.glob("*.tmp")) == []


def test_write_latest_system_run_artifact_concurrent_calls(tmp_path: Path):
    artifact_path = tmp_path / "latest_system_run.json"
    errors: list[Exception] = []

    def _writer(run_id: int):
        try:
            artifact = build_latest_system_run_artifact(
                run_id=run_id,
                run_status="success",
                summary=f"run-{run_id}",
            )
            write_latest_system_run_artifact(artifact_path, artifact)
        except Exception as exc:  # pragma: no cover - should not happen
            errors.append(exc)

    threads = [Thread(target=_writer, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert artifact_path.exists()
