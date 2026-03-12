from src.db import save_signal


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.payload = None
        self.filters = {}
        self._mode = None

    def upsert(self, payload, **_kwargs):
        self.payload = payload
        self._mode = "upsert"
        return self

    def update(self, payload):
        self.payload = payload
        self._mode = "update"
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def execute(self):
        if self._mode == "upsert":
            self.client.upsert_payloads.append(self.payload)
            if self.client.simulate_duplicate_upsert:
                return _Result([])
            return _Result([self.payload])

        if self._mode == "update":
            self.client.update_calls.append((self.table_name, self.payload, dict(self.filters)))
            return _Result([self.payload])

        return _Result([])


class _FakeClient:
    def __init__(self, simulate_duplicate_upsert=False):
        self.simulate_duplicate_upsert = simulate_duplicate_upsert
        self.upsert_payloads = []
        self.update_calls = []

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_save_signal_attaches_run_id_when_provided():
    fake_client = _FakeClient()

    save_signal(
        fake_client,
        {"stock": "0700.HK", "signal": "BUY", "price": 300.0, "reason": "ok"},
        run_id=901,
    )

    assert fake_client.upsert_payloads[0]["run_id"] == 901


def test_save_signal_relinks_existing_same_day_row_to_current_run():
    fake_client = _FakeClient(simulate_duplicate_upsert=True)

    save_signal(
        fake_client,
        {"stock": "0700.HK", "signal": "BUY", "price": 300.0, "reason": "ok"},
        run_id=902,
    )

    assert len(fake_client.update_calls) == 1
    table_name, payload, filters = fake_client.update_calls[0]
    assert table_name == "signals"
    assert payload == {"run_id": 902}
    assert filters["date"]
    assert filters["stock"] == "0700.HK"
