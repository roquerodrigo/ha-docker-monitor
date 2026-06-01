"""Health check binary sensor for a Docker container."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory

from ..entity import DockerMonitorEntity


class DockerMonitorHealthBinarySensor(DockerMonitorEntity, BinarySensorEntity):
    """Binary sensor reflecting the Docker health check status."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "health"
    _attr_icon = "mdi:heart-pulse"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self.coordinator.config_entry.entry_id}_{self._container_name}_health"

    @property
    def is_on(self) -> bool | None:
        """Return True when the container is unhealthy (problem device class)."""
        container = self._container
        if container is None:
            return None
        health = container["health_status"]
        if health is None:
            return None
        return health != "healthy"
