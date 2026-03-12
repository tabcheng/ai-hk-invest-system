from src.db import save_signal


class _FakeQuery:
    def __init__(self, client):
        self.client = client
        self.payload = None

    def upsert(self, payload, **_kwargs):
        self.payload = payload
        return self

    def execute(self):
        self.client.payloads.append(self.payload)

        class Result:
            data = [self.payload]

        return Result()


class _FakeClient:
    def __init__(self):
        self.payloads = []

    def table(self, _table_name):
        return _FakeQuery(self)


def test_save_signal_attaches_run_id_when_provided():
    fake_client = _FakeClient()

    save_signal(
        fake_client,
        {"stock": "0700.HK", "signal": "BUY", "price": 300.0, "reason": "ok"},
        run_id=901,
    )

    assert fake_client.payloads[0]["run_id"] == 901
