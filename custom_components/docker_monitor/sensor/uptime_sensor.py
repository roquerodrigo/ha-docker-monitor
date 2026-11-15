"""Uptime sensor for a Docker container."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from ..entity import DockerMonitorEntity

if TYPE_CHECKING:
    from datetime import datetime


class DockerMonitorUptimeSensor(DockerMonitorEntity, SensorEntity):
    """Moment the container last started."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "uptime"
    _attr_icon = "mdi:timer-outline"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self.coordinator.config_entry.entry_id}_{self._container_name}_uptime"

    @property
    def native_value(self) -> datetime | None:
        """Return when the container last started."""
        container = self._container
        if container is None:
            return None
        return container["started_at"]
