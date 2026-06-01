"""Sensor platform for docker_monitor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .cpu_sensor import DockerMonitorCpuSensor
from .memory_sensor import DockerMonitorMemorySensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import DockerMonitorConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DockerMonitorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator = entry.runtime_data.coordinator
    known_containers: set[str] = set()

    def _add_new_entities() -> None:
        containers = coordinator.data["containers"]
        new_names = set(containers) - known_containers
        if not new_names:
            return

        entities: list[DockerMonitorCpuSensor | DockerMonitorMemorySensor] = []
        for name in sorted(new_names):
            entities.append(DockerMonitorCpuSensor(coordinator, name))
            entities.append(DockerMonitorMemorySensor(coordinator, name))

        known_containers.update(new_names)
        async_add_entities(entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))
