from __future__ import annotations

from custom_components.docker_monitor.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_includes_socket_path(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["data"]["socket_path"] == "/var/run/docker.sock"


async def test_diagnostics_includes_entry_metadata(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["domain"] == "docker_monitor"
    assert "title" in diag["entry"]


async def test_diagnostics_includes_coordinator_data(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert "containers" in diag["coordinator_data"]
    assert "prometheus" in diag["coordinator_data"]["containers"]
