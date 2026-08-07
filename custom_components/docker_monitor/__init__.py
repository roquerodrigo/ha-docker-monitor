"""Docker Monitor integration for Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, cast

from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.loader import async_get_loaded_integration

from .api import DockerMonitorApiClient
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN
from .coordinator import DockerMonitorDataUpdateCoordinator
from .data import DockerMonitorData
from .exceptions import DockerMonitorApiClientError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry

    from .data import (
        DockerMonitorConfigData,
        DockerMonitorConfigEntry,
        DockerMonitorPayload,
    )

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DockerMonitorConfigEntry,
) -> bool:
    """Set up Docker Monitor from a config entry."""
    config = cast("DockerMonitorConfigData", entry.data)
    scan_interval_seconds: int = int(
        entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
    )

    client = DockerMonitorApiClient(socket_path=config["socket_path"])
    try:
        await client.async_connect()
    except DockerMonitorApiClientError as exception:
        message = f"Failed to connect to Docker at {config['socket_path']}"
        raise ConfigEntryNotReady(message) from exception
    # Registered before the first refresh so the client's aiohttp session is
    # closed on any setup failure from here on, not only on a clean unload.
    entry.async_on_unload(client.async_close)

    coordinator = DockerMonitorDataUpdateCoordinator(
        hass=hass,
        entry=entry,
        scan_interval=timedelta(seconds=scan_interval_seconds),
    )
    entry.runtime_data = DockerMonitorData(
        client=client,
        coordinator=coordinator,
        integration=async_get_loaded_integration(hass, entry.domain),
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: DockerMonitorConfigEntry,
) -> bool:
    """
    Handle removal of an entry.

    The API client is not closed here: the ``entry.async_on_unload`` hook
    registered during setup closes it after the platforms have unloaded, and
    only when unloading succeeds — an in-flight poll never crosses a closed
    session, and a failed unload keeps a usable client.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: DockerMonitorConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant,  # noqa: ARG001 -- HA device-removal contract requires this parameter
    entry: DockerMonitorConfigEntry,
    device_entry: DeviceEntry,
) -> bool:
    """
    Allow removing a device whose container Docker no longer reports.

    A container still present in the latest payload is refused, since the next
    update would immediately re-create its device. Any other device — a
    container that was stopped, renamed or removed — can be deleted. A
    container that comes back is simply registered again.
    """
    # ``data`` is typed non-optional by the coordinator generic, but is ``None``
    # until the first successful refresh — narrow defensively.
    payload: DockerMonitorPayload | None = entry.runtime_data.coordinator.data
    container_names = {
        identifier[1]
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
    }
    if payload is None or not container_names:
        return True
    return container_names.isdisjoint(payload["containers"])
