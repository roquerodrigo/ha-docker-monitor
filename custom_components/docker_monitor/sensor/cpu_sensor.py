"""CPU usage sensor for a Docker container."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE

from ..entity import DockerMonitorEntity


class DockerMonitorCpuSensor(DockerMonitorEntity, SensorEntity):
    """CPU usage percentage for a container."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_translation_key = "cpu"
    _attr_icon = "mdi:cpu-64-bit"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self.coordinator.config_entry.entry_id}_{self._container_name}_cpu"

    @property
    def native_value(self) -> float | None:
        """Return CPU usage percentage."""
        container = self._container
        if container is None:
            return None
        return container["cpu_percent"]
