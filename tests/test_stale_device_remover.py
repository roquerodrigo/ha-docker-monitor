from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.docker_monitor.const import DOMAIN, STALE_DEVICE_GRACE_PERIOD
from custom_components.docker_monitor.stale_device_remover import (
    DockerMonitorStaleDeviceRemover,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory


def _entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"socket_path": "/var/run/docker.sock"},
    )
    entry.add_to_hass(hass)
    return entry


def _device(hass, entry: MockConfigEntry, container_name: str) -> dr.DeviceEntry:
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, container_name)},
        name=container_name,
    )


def _device_exists(hass, device: dr.DeviceEntry) -> bool:
    return dr.async_get(hass).async_get(device.id) is not None


async def test_keeps_device_of_existing_container(hass):
    entry = _entry(hass)
    device = _device(hass, entry, "prometheus")
    remover = DockerMonitorStaleDeviceRemover(hass, entry)

    remover.async_remove_missing({"prometheus": "exited"})

    assert _device_exists(hass, device)


async def test_keeps_missing_container_within_grace_period(
    hass,
    freezer: FrozenDateTimeFactory,
):
    entry = _entry(hass)
    device = _device(hass, entry, "grafana")
    remover = DockerMonitorStaleDeviceRemover(hass, entry)

    remover.async_remove_missing({})
    freezer.tick(STALE_DEVICE_GRACE_PERIOD - timedelta(seconds=1))
    remover.async_remove_missing({})

    assert _device_exists(hass, device)


async def test_removes_container_missing_past_grace_period(
    hass,
    freezer: FrozenDateTimeFactory,
):
    entry = _entry(hass)
    device = _device(hass, entry, "grafana")
    remover = DockerMonitorStaleDeviceRemover(hass, entry)

    remover.async_remove_missing({})
    freezer.tick(STALE_DEVICE_GRACE_PERIOD)
    remover.async_remove_missing({})

    assert not _device_exists(hass, device)


async def test_removes_device_through_registry_removal(
    hass,
    freezer: FrozenDateTimeFactory,
):
    entry = _entry(hass)
    device = _device(hass, entry, "grafana")
    device_registry = dr.async_get(hass)
    remover = DockerMonitorStaleDeviceRemover(hass, entry)

    remover.async_remove_missing({})
    freezer.tick(STALE_DEVICE_GRACE_PERIOD)
    with (
        patch.object(
            device_registry,
            "async_remove_device",
            wraps=device_registry.async_remove_device,
        ) as remove_device,
        patch.object(
            device_registry,
            "async_update_device",
            wraps=device_registry.async_update_device,
        ) as update_device,
    ):
        remover.async_remove_missing({})

    remove_device.assert_called_once_with(device.id)
    update_device.assert_not_called()


async def test_recreated_container_restarts_grace_period(
    hass,
    freezer: FrozenDateTimeFactory,
):
    entry = _entry(hass)
    device = _device(hass, entry, "grafana")
    remover = DockerMonitorStaleDeviceRemover(hass, entry)

    remover.async_remove_missing({})
    freezer.tick(STALE_DEVICE_GRACE_PERIOD - timedelta(seconds=1))
    remover.async_remove_missing({"grafana": "running"})
    freezer.tick(timedelta(seconds=1))
    remover.async_remove_missing({})

    assert _device_exists(hass, device)


async def test_ignores_device_without_container_identifier(
    hass,
    freezer: FrozenDateTimeFactory,
):
    entry = _entry(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("other_domain", "grafana")},
    )
    remover = DockerMonitorStaleDeviceRemover(hass, entry)

    remover.async_remove_missing({})
    freezer.tick(STALE_DEVICE_GRACE_PERIOD)
    remover.async_remove_missing({})

    assert _device_exists(hass, device)
