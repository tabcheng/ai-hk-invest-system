import pytest

import src.config as config


def _set_base_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)


def test_uses_supabase_secret_key_first(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "secret-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setenv("SUPABASE_KEY", "legacy-key")

    captured = {}

    def fake_create_client(url, key):
        captured["url"] = url
        captured["key"] = key
        return object()

    monkeypatch.setattr(config, "create_client", fake_create_client)

    config.get_supabase_client()

    assert captured["url"] == "https://project.supabase.co"
    assert captured["key"] == "secret-key"


def test_uses_service_role_key_when_secret_missing(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")

    captured = {}

    def fake_create_client(url, key):
        captured["key"] = key
        return object()

    monkeypatch.setattr(config, "create_client", fake_create_client)

    config.get_supabase_client()

    assert captured["key"] == "service-role-key"


def test_falls_back_to_legacy_supabase_key_with_warning(monkeypatch, caplog):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_KEY", "legacy-key")

    captured = {}

    def fake_create_client(url, key):
        captured["key"] = key
        return object()

    monkeypatch.setattr(config, "create_client", fake_create_client)

    config.get_supabase_client()

    assert captured["key"] == "legacy-key"
    assert "SUPABASE_KEY is deprecated" in caplog.text
    assert "legacy-key" not in caplog.text


def test_priority_is_correct_when_all_keys_exist(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "secret-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setenv("SUPABASE_KEY", "legacy-key")

    captured = {}

    def fake_create_client(url, key):
        captured["key"] = key
        return object()

    monkeypatch.setattr(config, "create_client", fake_create_client)

    config.get_supabase_client()

    assert captured["key"] == "secret-key"


def test_missing_key_raises_clear_non_secret_error(monkeypatch):
    _set_base_env(monkeypatch)

    with pytest.raises(ValueError) as exc_info:
        config.get_supabase_client()

    msg = str(exc_info.value)
    assert "SUPABASE_SECRET_KEY" in msg
    assert "SUPABASE_SERVICE_ROLE_KEY" in msg
    assert "transitional fallback" in msg
    assert "secret-key" not in msg
    assert "service-role-key" not in msg
    assert "legacy-key" not in msg


def test_whitespace_only_primary_key_falls_back_to_service_role(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "   ")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")

    captured = {}

    def fake_create_client(url, key):
        captured["key"] = key
        return object()

    monkeypatch.setattr(config, "create_client", fake_create_client)
    config.get_supabase_client()

    assert captured["key"] == "service-role-key"


def test_whitespace_only_primary_and_secondary_fall_back_to_legacy(monkeypatch, caplog):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "   ")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "   ")
    monkeypatch.setenv("SUPABASE_KEY", "legacy-key")

    captured = {}

    def fake_create_client(url, key):
        captured["key"] = key
        return object()

    monkeypatch.setattr(config, "create_client", fake_create_client)
    config.get_supabase_client()

    assert captured["key"] == "legacy-key"
    assert "SUPABASE_KEY is deprecated" in caplog.text
    assert "legacy-key" not in caplog.text


def test_whitespace_only_all_keys_raise_missing_key_error(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "   ")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "   ")
    monkeypatch.setenv("SUPABASE_KEY", "   ")

    with pytest.raises(ValueError) as exc_info:
        config.get_supabase_client()

    msg = str(exc_info.value)
    assert "SUPABASE_SECRET_KEY" in msg
    assert "SUPABASE_SERVICE_ROLE_KEY" in msg
    assert "SUPABASE_KEY (transitional fallback)" in msg


def test_whitespace_only_legacy_key_does_not_warn_or_leak(monkeypatch, caplog):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_KEY", "   ")

    with pytest.raises(ValueError):
        config.get_supabase_client()

    assert "SUPABASE_KEY is deprecated" not in caplog.text


def test_whitespace_only_supabase_url_raises_missing_config_error(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_URL", "   ")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "secret-key")

    with pytest.raises(ValueError) as exc_info:
        config.get_supabase_client()

    assert "SUPABASE_URL" in str(exc_info.value)
