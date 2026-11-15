"""Image sensor for a Docker container."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from ..entity import DockerMonitorEntity
from ..image_reference import DockerImageReference


class DockerMonitorImageSensor(DockerMonitorEntity, SensorEntity):
    """Repository of the image the container runs, without its tag."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "image"
    _attr_icon = "mdi:docker"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self.coordinator.config_entry.entry_id}_{self._container_name}_image"

    @property
    def native_value(self) -> str | None:
        """Return the image repository."""
        container = self._container
        if container is None or not container["image"]:
            return None
        return DockerImageReference.parse(container["image"]).repository
