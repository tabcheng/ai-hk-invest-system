import sys
import types
from datetime import date, datetime, timedelta
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_pandas_stub() -> None:
    """
    Install a minimal pandas compatibility stub for constrained test environments.

    Scope guardrail:
    - This shim only covers API surface required by current market-data/signals tests.
    - It is intentionally narrow and should be expanded only when tests require it.
    """

    class _SeriesILoc:
        def __init__(self, values):
            self._values = values

        def __getitem__(self, idx):
            return self._values[idx]

    class _RollingSeries:
        def __init__(self, values, window: int):
            self._values = values
            self._window = window

        def mean(self):
            rolling_values = []
            for i in range(len(self._values)):
                if i + 1 < self._window:
                    rolling_values.append(None)
                    continue
                window_values = self._values[i + 1 - self._window : i + 1]
                if any(value is None for value in window_values):
                    rolling_values.append(None)
                    continue
                rolling_values.append(sum(window_values) / self._window)
            return _Series(rolling_values)

    class _Series:
        def __init__(self, values):
            self._values = list(values)

        @property
        def empty(self):
            return len(self._values) == 0

        @property
        def iloc(self):
            return _SeriesILoc(self._values)

        def rolling(self, window: int):
            return _RollingSeries(self._values, window)

        def to_list(self):
            return list(self._values)

    class _DataFrameILoc:
        def __init__(self, frame):
            self._frame = frame

        def __getitem__(self, idx):
            return dict(self._frame._rows[idx])

    class _MultiIndex:  # pragma: no cover - structural import stub only
        pass

    class _DataFrame:
        def __init__(self, data=None, columns=None):
            self._rows = []
            self._index = []

            if data is None:
                self.columns = list(columns or [])
                return

            if isinstance(data, dict):
                self.columns = list(columns or data.keys())
                row_count = 0
                normalized = {}
                for col in self.columns:
                    raw = data.get(col, [])
                    if isinstance(raw, list):
                        normalized[col] = raw
                    else:
                        normalized[col] = [raw]
                    row_count = max(row_count, len(normalized[col]))
                self._rows = []
                for i in range(row_count):
                    row = {}
                    for col in self.columns:
                        col_values = normalized[col]
                        row[col] = col_values[i] if i < len(col_values) else None
                    self._rows.append(row)
                return

            if isinstance(data, list):
                if not data:
                    self.columns = list(columns or [])
                    self._rows = []
                    return
                if data and isinstance(data[0], dict):
                    seen_columns = list(columns or [])
                    if not seen_columns:
                        for row in data:
                            for key in row.keys():
                                if key not in seen_columns:
                                    seen_columns.append(key)
                    self.columns = seen_columns
                    self._rows = [{col: row.get(col) for col in self.columns} for row in data]
                    return

            raise TypeError("pandas stub DataFrame supports only dict/list input in tests.")

        @property
        def empty(self):
            return len(self._rows) == 0

        @property
        def iloc(self):
            return _DataFrameILoc(self)

        def __len__(self):
            return len(self._rows)

        def __getitem__(self, key):
            if isinstance(key, str):
                return _Series([row.get(key) for row in self._rows])
            if isinstance(key, list):
                return _DataFrame([{col: row.get(col) for col in key} for row in self._rows], columns=key)
            raise TypeError("Unsupported key type for pandas stub DataFrame.")

        def __setitem__(self, key, value):
            if isinstance(value, _Series):
                values = value.to_list()
            elif isinstance(value, list):
                values = value
            else:
                values = [value] * len(self._rows)

            if not self._rows:
                self._rows = [{key: item} for item in values]
                self.columns = [key]
                return

            if len(values) != len(self._rows):
                raise ValueError("pandas stub assignment length mismatch.")

            if key not in self.columns:
                self.columns.append(key)
            for row, item in zip(self._rows, values):
                row[key] = item

        def dropna(self, subset=None):
            subset = subset or []
            return _DataFrame(
                [row for row in self._rows if all(row.get(col) is not None for col in subset)],
                columns=list(self.columns),
            )

        def tail(self, n: int):
            return _DataFrame(self._rows[-n:], columns=list(self.columns))

        def set_index(self, key: str):
            self._index = [row.get(key) for row in self._rows]
            if key in self.columns:
                self.columns.remove(key)
                for row in self._rows:
                    row.pop(key, None)
            return self

        def copy(self):
            return _DataFrame([dict(row) for row in self._rows], columns=list(self.columns))

    def _date_range(start, end, freq="D"):
        if freq != "D":
            raise ValueError("pandas stub currently supports only daily frequency ('D').")
        if isinstance(start, str):
            start = datetime.fromisoformat(start).date()
        if isinstance(end, str):
            end = datetime.fromisoformat(end).date()
        if not isinstance(start, date) or not isinstance(end, date):
            raise TypeError("pandas stub date_range expects date or ISO date string values.")
        if end < start:
            return []
        return [start + timedelta(days=i) for i in range((end - start).days + 1)]

    pandas_stub = types.ModuleType("pandas")
    pandas_stub.DataFrame = _DataFrame
    pandas_stub.MultiIndex = _MultiIndex
    pandas_stub.Series = _Series
    pandas_stub.date_range = _date_range
    sys.modules["pandas"] = pandas_stub


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

    if "pandas" not in sys.modules and find_spec("pandas") is None:
        _install_pandas_stub()

    if "yfinance" not in sys.modules:
        yfinance_stub = types.ModuleType("yfinance")

        def _download(*_args, **_kwargs):
            raise RuntimeError("yfinance stub: tests must monkeypatch provider calls.")

        yfinance_stub.download = _download
        sys.modules["yfinance"] = yfinance_stub


_install_test_dependency_stubs()
