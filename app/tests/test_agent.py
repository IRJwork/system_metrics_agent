
"""Tests unitaires de l'agent de collecte."""

from unittest.mock import patch

import pytest

from app.agent import run_once, run_forever
from app.collector import MetricsCollectionError
from app.config import Settings
from app.sender import MetricsDeliveryError


@pytest.fixture
def settings():
    """Fournit une configuration de test."""
    return Settings(
        metrics_endpoint="http://localhost:8000/metrics",
        collection_interval=5.0,
        request_timeout=3.0,
    )


# -------------------------------------------------------------------
# Tests de run_once()
# -------------------------------------------------------------------

@patch("app.agent.send_metrics")
@patch("app.agent.format_metrics")
@patch("app.agent.collect_system_metrics")
def test_run_once_success(
    mock_collect,
    mock_format,
    mock_send,
    settings,
):
    """Vérifie le cycle complet lorsque tout réussit."""
    mock_collect.return_value = {
        "cpu": {"percent": 25.0},
    }

    mock_format.return_value = {
        "agent": "agent-test",
        "data": {"cpu": {"percent": 25.0}},
    }

    mock_send.return_value = {
        "status_code": 201,
        "response": {"status": "received"},
    }

    result = run_once(settings)

    assert result["status_code"] == 201

    mock_collect.assert_called_once_with()

    mock_format.assert_called_once_with(
        mock_collect.return_value,
    )

    mock_send.assert_called_once_with(
        endpoint=settings.metrics_endpoint,
        payload=mock_format.return_value,
        timeout=settings.request_timeout,
    )


@patch(
    "app.agent.collect_system_metrics",
    side_effect=MetricsCollectionError("Erreur de collecte"),
)
def test_run_once_propagates_collection_error(
    mock_collect,
    settings,
):
    """Vérifie la propagation d'une erreur de collecte."""
    with pytest.raises(
        MetricsCollectionError,
        match="Erreur de collecte",
    ):
        run_once(settings)

    mock_collect.assert_called_once_with()


# -------------------------------------------------------------------
# Tests de run_forever()
# -------------------------------------------------------------------

@patch("app.agent.time.sleep")
@patch("app.agent.run_once")
@patch("app.agent.Settings.from_env")
def test_run_forever_logs_success_and_stops(
    mock_settings,
    mock_run_once,
    mock_sleep,
):
    """Vérifie un cycle réussi puis l'arrêt de l'agent."""
    mock_settings.return_value = Settings(
        metrics_endpoint="http://localhost:8000/metrics",
        collection_interval=5.0,
        request_timeout=3.0,
    )

    # Le premier cycle réussit.
    # Le second déclenche l'interruption dans le bloc try.
    mock_run_once.side_effect = [
        {"status_code": 201},
        KeyboardInterrupt,
    ]

    run_forever()

    assert mock_run_once.call_count == 2
    mock_sleep.assert_called_once_with(5.0)


@pytest.mark.parametrize(
    "error",
    [
        MetricsCollectionError("Erreur de collecte"),
        MetricsDeliveryError("Erreur d'envoi"),
        ValueError("Configuration invalide"),
    ],
)
@patch("app.agent.logger.error")
@patch("app.agent.time.sleep")
@patch("app.agent.run_once")
@patch("app.agent.Settings.from_env")
def test_run_forever_logs_cycle_errors(
    mock_settings,
    mock_run_once,
    mock_sleep,
    mock_log_error,
    error,
):
    """Vérifie la journalisation des erreurs métier."""
    mock_settings.return_value = Settings(
        metrics_endpoint="http://localhost:8000/metrics",
        collection_interval=5.0,
        request_timeout=3.0,
    )

    # L'erreur testée est suivie d'une interruption contrôlée.
    # Cela évite une boucle infinie pendant le test.
    mock_run_once.side_effect = [
        error,
        KeyboardInterrupt,
    ]

    run_forever()

    mock_log_error.assert_called_once()

    mock_sleep.assert_called_once_with(5.0)
