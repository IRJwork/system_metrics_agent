
"""Tests du module de collecte des métriques système."""

from unittest.mock import Mock, patch

import pytest

from app.collector import (
    MetricsCollectionError,
    collect_system_metrics,
    get_load_average,
)


@patch("app.collector.platform.system", return_value="Linux")
@patch("app.collector.subprocess.run")
def test_get_load_average_success(mock_run, mock_system):
    mock_run.return_value = Mock(
        stdout=" 10:00:00 up 2 days, load average: 0.10, 0.20, 0.30\n"
    )

    result = get_load_average()

    assert result == {
        "load_1m": 0.10,
        "load_5m": 0.20,
        "load_15m": 0.30,
    }
    mock_run.assert_called_once_with(
        ["uptime"],
        capture_output=True,
        text=True,
        check=True,
        timeout=3,
    )


@patch("app.collector.platform.system", return_value="Windows")
@patch("app.collector.subprocess.run")
def test_get_load_average_on_windows(mock_run, mock_system):
    result = get_load_average()

    assert result == {
        "load_1m": None,
        "load_5m": None,
        "load_15m": None,
    }
    mock_run.assert_not_called()


@pytest.mark.parametrize(
    "exception",
    [
        FileNotFoundError("uptime absent"),
        __import__("subprocess").CalledProcessError(1, ["uptime"]),
        __import__("subprocess").TimeoutExpired(["uptime"], 3),
    ],
)
@patch("app.collector.platform.system", return_value="Linux")
@patch("app.collector.subprocess.run")
def test_get_load_average_command_errors(
    mock_run, mock_system, exception
):
    mock_run.side_effect = exception

    with pytest.raises(MetricsCollectionError, match="uptime"):
        get_load_average()


@pytest.mark.parametrize(
    "output",
    [
        "",
        "uptime: load averages unavailable",
        "load average: invalid, 0.20, 0.30",
    ],
)
@patch("app.collector.platform.system", return_value="Linux")
@patch("app.collector.subprocess.run")
def test_get_load_average_invalid_output(
    mock_run, mock_system, output
):
    mock_run.return_value = Mock(stdout=output)

    with pytest.raises(
        MetricsCollectionError,
        match="analyser la sortie uptime",
    ):
        get_load_average()


@patch("app.collector.get_load_average")
@patch("app.collector.psutil.cpu_percent")
@patch("app.collector.psutil.cpu_count")
@patch("app.collector.psutil.virtual_memory")
def test_collect_system_metrics(
    mock_memory,
    mock_cpu_count,
    mock_cpu_percent,
    mock_load,
):
    mock_memory.return_value = Mock(
        total=1000,
        available=400,
        used=600,
        percent=60.0,
    )
    mock_cpu_percent.return_value = 25.5
    mock_cpu_count.return_value = 8
    mock_load.return_value = {
        "load_1m": 0.1,
        "load_5m": 0.2,
        "load_15m": 0.3,
    }

    metrics = collect_system_metrics()

    assert metrics["cpu"]["percent"] == 25.5
    assert metrics["cpu"]["logical_cores"] == 8
    assert metrics["memory"]["percent"] == 60.0
    assert metrics["system"]["load_1m"] == 0.1
    assert "timestamp" in metrics
    assert "hostname" in metrics


@patch(
    "app.collector.get_load_average",
    side_effect=MetricsCollectionError("Erreur uptime"),
)
@patch("app.collector.psutil.cpu_percent", return_value=20.0)
@patch("app.collector.psutil.virtual_memory")
def test_collect_system_metrics_propagates_collection_error(
    mock_memory, mock_cpu_percent, mock_load
):
    mock_memory.return_value = Mock(
        total=1000,
        available=400,
        used=600,
        percent=60.0,
    )

    with pytest.raises(
        MetricsCollectionError,
        match="Erreur uptime",
    ):
        collect_system_metrics()


@patch(
    "app.collector.psutil.virtual_memory",
    side_effect=RuntimeError("Erreur mémoire"),
)
def test_collect_system_metrics_wraps_unexpected_error(mock_memory):
    with pytest.raises(
        MetricsCollectionError,
        match="Erreur pendant la collecte",
    ):
        collect_system_metrics()
