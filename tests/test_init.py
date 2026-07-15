from __future__ import annotations

import copy
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntryState

from custom_components.docker_monitor import async_remove_config_entry_device
from custom_components.docker_monitor.const import DOMAIN
from tests.conftest import SAMPLE_PAYLOAD


async def _can_remove(identifiers, payload):
    entry = MagicMock()
    entry.runtime_data.coordinator.data = payload
    device = MagicMock()
    device.identifiers = identifiers
    return await async_remove_config_entry_device(MagicMock(), entry, device)


async def test_remove_rejected_for_reported_container():
    payload = copy.deepcopy(SAMPLE_PAYLOAD)

    assert await _can_remove({(DOMAIN, "prometheus")}, payload) is False


async def test_remove_allowed_for_absent_container():
    payload = copy.deepcopy(SAMPLE_PAYLOAD)

    assert await _can_remove({(DOMAIN, "removed-container")}, payload) is True


async def test_remove_allowed_without_payload():
    assert await _can_remove({(DOMAIN, "prometheus")}, None) is True


async def test_remove_allowed_for_device_without_docker_monitor_identifier():
    payload = copy.deepcopy(SAMPLE_PAYLOAD)

    assert await _can_remove({("other", "prometheus")}, payload) is True


async def test_setup_entry_loads(hass, setup_integration):
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_setup_entry_creates_sensor_entities(hass, setup_integration):
    sensors = hass.states.async_all("sensor")
    assert len(sensors) == 4  # 2 containers x (cpu + memory)


async def test_setup_entry_creates_binary_sensor_for_healthcheck(
    hass, setup_integration
):
    binary_sensors = hass.states.async_all("binary_sensor")
    assert len(binary_sensors) == 1  # only prometheus has health


async def test_runtime_data_populated(hass, setup_integration):
    assert setup_integration.runtime_data.client is not None
    assert setup_integration.runtime_data.coordinator is not None
    assert setup_integration.runtime_data.integration is not None


async def test_unload_entry(hass, setup_integration):
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert setup_integration.state == ConfigEntryState.NOT_LOADED


async def test_reload_entry(hass, setup_integration, mock_api_client):
    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_scan_interval_defaults(hass, setup_integration):
    from datetime import timedelta

    from custom_components.docker_monitor.const import DEFAULT_SCAN_INTERVAL_SECONDS

    assert setup_integration.runtime_data.coordinator.update_interval == timedelta(
        seconds=DEFAULT_SCAN_INTERVAL_SECONDS,
    )


async def test_scan_interval_from_options(
    hass, mock_api_client, enable_custom_integrations
):
    from datetime import timedelta

    from homeassistant.const import CONF_SCAN_INTERVAL
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.docker_monitor.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"socket_path": "/var/run/docker.sock"},
        options={CONF_SCAN_INTERVAL: 60},
        unique_id="custom",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.coordinator.update_interval == timedelta(seconds=60)
