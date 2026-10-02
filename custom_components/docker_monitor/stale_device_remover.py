"""Removal of devices whose container no longer exists in Docker."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER, STALE_DEVICE_GRACE_PERIOD

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime

    from homeassistant.core import HomeAssistant

    from .data import DockerMonitorConfigEntry


class DockerMonitorStaleDeviceRemover:
    """
    Remove the device of a container once Docker no longer has it.

    A stopped container still exists, so its device is kept. A missing one is
    only removed after ``STALE_DEVICE_GRACE_PERIOD``: ``docker compose up``
    recreates a container by deleting it first, and a poll landing in that
    window must not drop the device and its entity customisations.
    """

    def __init__(self, hass: HomeAssistant, entry: DockerMonitorConfigEntry) -> None:
        """Initialize."""
        self._hass = hass
        self._entry = entry
        self._missing_since: dict[str, datetime] = {}

    def async_remove_missing(self, existing_container_names: Collection[str]) -> None:
        """Remove the devices whose container has been missing for too long."""
        device_registry = dr.async_get(self._hass)
        now = dt_util.utcnow()
        tracked_device_ids: set[str] = set()

        for device in dr.async_entries_for_config_entry(
            device_registry,
            self._entry.entry_id,
        ):
            container_name = _container_name(device)
            if container_name is None or container_name in existing_container_names:
                continue
            tracked_device_ids.add(device.id)
            missing_since = self._missing_since.setdefault(device.id, now)
            if now - missing_since < STALE_DEVICE_GRACE_PERIOD:
                continue
            LOGGER.info("Removing device of deleted container %s", container_name)
            device_registry.async_remove_device(device.id)
            tracked_device_ids.discard(device.id)

        self._missing_since = {
            device_id: missing_since
            for device_id, missing_since in self._missing_since.items()
            if device_id in tracked_device_ids
        }


def _container_name(device: dr.DeviceEntry) -> str | None:
    """Return the container name a device is keyed by."""
    for domain, identifier in device.identifiers:
        if domain == DOMAIN:
            return identifier
    return None
