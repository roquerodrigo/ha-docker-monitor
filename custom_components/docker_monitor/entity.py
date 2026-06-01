"""DockerMonitorEntity base class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import DockerMonitorDataUpdateCoordinator

if TYPE_CHECKING:
    from .data import DockerMonitorContainerData, DockerMonitorPayload


class DockerMonitorEntity(
    CoordinatorEntity[DockerMonitorDataUpdateCoordinator],
):
    """Base entity for Docker Monitor — one device per container."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DockerMonitorDataUpdateCoordinator,
        container_name: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._container_name = container_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info keyed by container name (stable across recreations)."""
        container = self._container
        image = container["image"] if container else ""
        image_name = image.split(":")[0] if image else ""
        return DeviceInfo(
            identifiers={(DOMAIN, self._container_name)},
            name=self._container_name,
            manufacturer=image_name,
            sw_version=image,
        )

    @property
    def available(self) -> bool:
        """Return True when the container is present in the latest payload."""
        # ``data`` is typed non-optional by the coordinator generic, but is
        # ``None`` until the first successful refresh — narrow defensively.
        data: DockerMonitorPayload | None = self.coordinator.data
        return (
            self.coordinator.last_update_success
            and data is not None
            and self._container_name in data["containers"]
        )

    @property
    def _container(self) -> DockerMonitorContainerData | None:
        """Return the container snapshot or None if not found."""
        data: DockerMonitorPayload | None = self.coordinator.data
        if data is None:
            return None
        return data["containers"].get(self._container_name)
