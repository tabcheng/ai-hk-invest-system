import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_test_dependency_stubs() -> None:
    """
    Install lightweight local stubs for optional runtime dependencies in test env.

    Guardrail: these shims exist only to unblock import-time module loading in
    constrained CI/sandbox environments. Runtime behavior in production still
    depends on real third-party packages (`requests`, `supabase`).
    """
    if "requests" not in sys.modules:
        requests_stub = types.ModuleType("requests")

        def _post(*_args, **_kwargs):
            raise RuntimeError("requests stub: tests must monkeypatch transport calls.")

        requests_stub.post = _post
        sys.modules["requests"] = requests_stub

    if "supabase" not in sys.modules:
        supabase_stub = types.ModuleType("supabase")

        class _Client:  # pragma: no cover - structural import stub only
            pass

        def _create_client(*_args, **_kwargs):
            raise RuntimeError("supabase stub: tests must monkeypatch client access.")

        supabase_stub.Client = _Client
        supabase_stub.create_client = _create_client
        sys.modules["supabase"] = supabase_stub

    if "pandas" not in sys.modules:
        pandas_stub = types.ModuleType("pandas")

        class _DataFrame:  # pragma: no cover - structural import stub only
            pass

        class _MultiIndex:  # pragma: no cover - structural import stub only
            pass

        pandas_stub.DataFrame = _DataFrame
        pandas_stub.MultiIndex = _MultiIndex
        sys.modules["pandas"] = pandas_stub

    if "yfinance" not in sys.modules:
        yfinance_stub = types.ModuleType("yfinance")

        def _download(*_args, **_kwargs):
            raise RuntimeError("yfinance stub: tests must monkeypatch provider calls.")

        yfinance_stub.download = _download
        sys.modules["yfinance"] = yfinance_stub


_install_test_dependency_stubs()
