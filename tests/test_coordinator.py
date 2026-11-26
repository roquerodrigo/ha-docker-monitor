from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

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
        data={"docker_host": "unix:///var/run/docker.sock"},
        version=2,
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
    assert "nginx" in data["containers"]


async def test_update_data_raises_update_failed_on_comm_error(
    hass,
    setup_integration,
):
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.config_entry.runtime_data.client.async_list_container_states = (
        AsyncMock(
            side_effect=DockerMonitorApiClientCommunicationError("timeout"),
        )
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_update_data_only_fetches_running_containers(hass, setup_integration):
    coordinator = setup_integration.runtime_data.coordinator
    client = setup_integration.runtime_data.client
    client.async_list_container_states = AsyncMock(
        return_value={"prometheus": "running", "nginx": "exited"},
    )

    payload = await coordinator._async_update_data()

    assert list(payload["containers"]) == ["prometheus"]


async def test_first_refresh_skips_stats_and_later_refreshes_include_them(hass):
    entry = _entry(hass)
    client = MagicMock()
    client.async_list_container_states = AsyncMock(
        return_value={"prometheus": "running"},
    )
    client.async_get_container_data = AsyncMock(
        side_effect=lambda name, **_: {"name": name},
    )
    entry.runtime_data = MagicMock(client=client)
    coordinator = DockerMonitorDataUpdateCoordinator(
        hass=hass,
        entry=entry,
        scan_interval=timedelta(seconds=30),
    )

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    assert [call.kwargs for call in client.async_get_container_data.call_args_list] == [
        {"include_stats": False},
        {"include_stats": True},
    ]


def _coordinator_with_client(hass, client) -> DockerMonitorDataUpdateCoordinator:
    entry = _entry(hass)
    entry.runtime_data = MagicMock(client=client)
    return DockerMonitorDataUpdateCoordinator(
        hass=hass,
        entry=entry,
        scan_interval=timedelta(seconds=30),
    )


def _client_failing_for(states: dict[str, str], failing: set[str]) -> MagicMock:
    client = MagicMock()
    client.async_list_container_states = AsyncMock(return_value=states)

    async def get_container_data(name, **_):
        if name in failing:
            msg = f"Failed to get data for container {name}: [408] Request Time-out"
            raise DockerMonitorApiClientCommunicationError(msg)
        return {"name": name}

    client.async_get_container_data = AsyncMock(side_effect=get_container_data)
    return client


async def test_failing_container_is_left_out_of_the_payload(hass):
    client = _client_failing_for(
        {"prometheus": "running", "nginx": "running"},
        failing={"nginx"},
    )
    coordinator = _coordinator_with_client(hass, client)

    payload = await coordinator._async_update_data()

    assert list(payload["containers"]) == ["prometheus"]


async def test_update_fails_when_every_container_fails(hass):
    client = _client_failing_for(
        {"prometheus": "running", "nginx": "running"},
        failing={"prometheus", "nginx"},
    )
    coordinator = _coordinator_with_client(hass, client)

    with pytest.raises(UpdateFailed, match="Request Time-out"):
        await coordinator._async_update_data()


async def test_no_running_container_is_not_a_failure(hass):
    client = _client_failing_for({"nginx": "exited"}, failing=set())
    coordinator = _coordinator_with_client(hass, client)

    payload = await coordinator._async_update_data()

    assert payload == {"containers": {}}


async def test_container_availability_is_logged_once_per_change(hass, caplog):
    states = {"prometheus": "running", "nginx": "running"}
    coordinator = _coordinator_with_client(
        hass, _client_failing_for(states, failing={"nginx"})
    )

    with caplog.at_level("INFO"):
        await coordinator._async_update_data()
        await coordinator._async_update_data()
        coordinator.config_entry.runtime_data.client = _client_failing_for(
            states, failing=set()
        )
        await coordinator._async_update_data()

    messages = [record.getMessage() for record in caplog.records]
    unavailable = [
        m for m in messages if m.startswith("Container nginx is unavailable")
    ]
    assert len(unavailable) == 1
    assert messages.count("Container nginx is available again") == 1
