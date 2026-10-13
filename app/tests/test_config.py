"""Tests du chargement de la configuration."""

import pytest

from app.config import Settings


def test_from_env_uses_defaults(monkeypatch):
    """Vérifie les valeurs par défaut."""
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)

    monkeypatch.delenv("METRICS_ENDPOINT", raising=False)
    monkeypatch.delenv("COLLECTION_INTERVAL", raising=False)
    monkeypatch.delenv("REQUEST_TIMEOUT", raising=False)

    settings = Settings.from_env()

    assert settings.metrics_endpoint == "http://127.0.0.1:8000/metrics"
    assert settings.collection_interval == 5.0
    assert settings.request_timeout == 5.0


def test_from_env_uses_custom_values(monkeypatch):
    """Vérifie les valeurs personnalisées."""
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)

    monkeypatch.setenv("METRICS_ENDPOINT", "http://localhost:9000/metrics")
    monkeypatch.setenv("COLLECTION_INTERVAL", "10")
    monkeypatch.setenv("REQUEST_TIMEOUT", "3.5")

    settings = Settings.from_env()

    assert settings.metrics_endpoint == "http://localhost:9000/metrics"
    assert settings.collection_interval == 10.0
    assert settings.request_timeout == 3.5


@pytest.mark.parametrize(
    "variable",
    ["COLLECTION_INTERVAL", "REQUEST_TIMEOUT"],
)
def test_from_env_rejects_non_numeric_values(monkeypatch, variable):
    """Vérifie le rejet des valeurs non numériques."""
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    monkeypatch.setenv(variable, "abc")

    with pytest.raises(ValueError, match="doivent être numériques"):
        Settings.from_env()


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("COLLECTION_INTERVAL", "0"),
        ("COLLECTION_INTERVAL", "-1"),
        ("REQUEST_TIMEOUT", "0"),
        ("REQUEST_TIMEOUT", "-1"),
    ],
)
def test_from_env_rejects_non_positive_values(monkeypatch, variable, value):
    """Vérifie le rejet des valeurs nulles ou négatives."""
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    monkeypatch.setenv(variable, value)

    with pytest.raises(ValueError, match="doivent être > 0"):
        Settings.from_env()
