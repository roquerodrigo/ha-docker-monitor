"""Docker Monitor integration for Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, cast

from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.loader import async_get_loaded_integration

from .api import DockerMonitorApiClient
from .const import CONF_SOCKET_PATH, DEFAULT_SCAN_INTERVAL_SECONDS
from .coordinator import DockerMonitorDataUpdateCoordinator
from .data import DockerMonitorData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import DockerMonitorConfigData, DockerMonitorConfigEntry

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

    client = DockerMonitorApiClient(socket_path=config[CONF_SOCKET_PATH])
    await client.async_connect()

    coordinator = DockerMonitorDataUpdateCoordinator(
        hass=hass,
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
    hass: HomeAssistant,  # noqa: ARG001
    entry: DockerMonitorConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    await entry.runtime_data.client.async_close()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: DockerMonitorConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
