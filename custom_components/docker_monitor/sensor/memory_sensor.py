"""Memory usage sensor for a Docker container."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfInformation

from ..entity import DockerMonitorEntity


class DockerMonitorMemorySensor(DockerMonitorEntity, SensorEntity):
    """Memory usage in megabytes for a container."""

    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = UnitOfInformation.MEGABYTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_translation_key = "memory"
    _attr_icon = "mdi:memory"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self.coordinator.config_entry.entry_id}_{self._container_name}_memory"

    @property
    def native_value(self) -> float | None:
        """Return memory usage in MB."""
        container = self._container
        if container is None:
            return None
        return container["memory_usage_mb"]

    @property
    def extra_state_attributes(self) -> dict[str, float] | None:
        """Expose the container's memory limit (MB) alongside usage."""
        container = self._container
        if container is None:
            return None
        limit = container["memory_limit_mb"]
        if limit is None:
            return None
        return {"memory_limit_mb": limit}
