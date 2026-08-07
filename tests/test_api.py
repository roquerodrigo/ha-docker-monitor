from __future__ import annotations

from custom_components.docker_monitor.api import (
    _calculate_cpu_percent,
    _calculate_memory,
    _is_anonymous,
)
from custom_components.docker_monitor.exceptions import (
    DockerMonitorApiClientCommunicationError,
    DockerMonitorApiClientError,
)


def test_communication_error_is_api_error():
    assert issubclass(
        DockerMonitorApiClientCommunicationError,
        DockerMonitorApiClientError,
    )


def test_api_error_is_exception():
    assert issubclass(DockerMonitorApiClientError, Exception)


def test_is_anonymous_compose_one_off():
    assert _is_anonymous("myproject-backup-run-a1b2c3d4e5f6") is True


def test_is_anonymous_id_like_name():
    assert _is_anonymous("346ee219ec9f346ee219ec9f") is True


def test_is_anonymous_short_name():
    assert _is_anonymous("prometheus") is False


def test_is_anonymous_compose_name():
    assert _is_anonymous("smart-home-prometheus-1") is False


def test_is_anonymous_keeps_named_container_with_hex_suffix():
    assert _is_anonymous("some-service-a1b2c3d4e5f6") is False


def test_is_anonymous_short_run_suffix():
    assert _is_anonymous("myproject-backup-run-a1b2") is False


def test_calculate_cpu_percent_basic():
    stats = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 200},
            "system_cpu_usage": 2000,
            "online_cpus": 4,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 100},
            "system_cpu_usage": 1000,
        },
    }
    result = _calculate_cpu_percent(stats)
    assert result is not None
    assert result == 40.0  # (100/1000) * 4 * 100


def test_calculate_cpu_percent_returns_none_on_missing():
    assert _calculate_cpu_percent({}) is None


def test_calculate_cpu_percent_returns_none_on_zero_delta():
    stats = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 100},
            "system_cpu_usage": 1000,
            "online_cpus": 4,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 100},
            "system_cpu_usage": 1000,
        },
    }
    assert _calculate_cpu_percent(stats) is None


def test_calculate_memory_basic():
    stats = {
        "memory_stats": {
            "usage": 104857600,  # 100 MB
            "limit": 1073741824,  # 1 GB
            "stats": {"cache": 0},
        },
    }
    used, limit = _calculate_memory(stats)
    assert used == 100.0
    assert limit == 1024.0


def test_calculate_memory_subtracts_cache():
    stats = {
        "memory_stats": {
            "usage": 104857600,
            "limit": 1073741824,
            "stats": {"cache": 10485760},  # 10 MB
        },
    }
    used, _ = _calculate_memory(stats)
    assert used == 90.0


def test_calculate_memory_returns_none_on_missing():
    used, limit = _calculate_memory({})
    assert used is None
    assert limit is None
