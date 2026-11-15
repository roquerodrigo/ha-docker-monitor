"""Image tag sensor for a Docker container."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from ..entity import DockerMonitorEntity
from ..image_reference import DockerImageReference


class DockerMonitorImageTagSensor(DockerMonitorEntity, SensorEntity):
    """Tag of the image the container runs."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "image_tag"
    _attr_icon = "mdi:tag-outline"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return (
            f"{self.coordinator.config_entry.entry_id}_{self._container_name}_image_tag"
        )

    @property
    def native_value(self) -> str | None:
        """Return the image tag, or None for an untagged or digest-pinned image."""
        container = self._container
        if container is None or not container["image"]:
            return None
        return DockerImageReference.parse(container["image"]).tag
