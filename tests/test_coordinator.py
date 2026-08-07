from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.docker_monitor.const import DOMAIN
from custom_components.docker_monitor.coordinator import (
    DockerMonitorDataUpdateCoordinator,
)
from custom_components.docker_monitor.exceptions import (
    DockerMonitorApiClientCommunicationError,
)


def _entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"socket_path": "/var/run/docker.sock"},
    )
    entry.add_to_hass(hass)
    return entry


def test_init_sets_domain_name(hass):
    coord = DockerMonitorDataUpdateCoordinator(
        hass=hass,
        entry=_entry(hass),
        scan_interval=timedelta(seconds=30),
    )
    assert coord.name == DOMAIN


def test_init_sets_update_interval(hass):
    coord = DockerMonitorDataUpdateCoordinator(
        hass=hass,
        entry=_entry(hass),
        scan_interval=timedelta(seconds=42),
    )
    assert coord.update_interval == timedelta(seconds=42)


def test_init_binds_config_entry_explicitly(hass):
    entry = _entry(hass)
    coord = DockerMonitorDataUpdateCoordinator(
        hass=hass,
        entry=entry,
        scan_interval=timedelta(seconds=30),
    )
    assert coord.config_entry is entry


async def test_update_data_returns_payload(hass, setup_integration):
    data = setup_integration.runtime_data.coordinator.data
    assert "containers" in data
    assert "prometheus" in data["containers"]
    assert "ha-mcp" in data["containers"]


async def test_update_data_raises_update_failed_on_comm_error(
    hass,
    setup_integration,
):
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.config_entry.runtime_data.client.async_list_container_names = AsyncMock(
        side_effect=DockerMonitorApiClientCommunicationError("timeout"),
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
