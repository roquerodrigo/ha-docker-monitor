"""Binary sensor platform for docker_monitor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .health_binary_sensor import DockerMonitorHealthBinarySensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import DockerMonitorConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DockerMonitorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator = entry.runtime_data.coordinator
    known_containers: set[str] = set()

    def _add_new_entities() -> None:
        containers = coordinator.data["containers"]
        # Only containers that already report a health check become "known" —
        # a container whose health check appears later (e.g. recreated with
        # one) still gets its sensor on that refresh.
        new_names = {
            name
            for name in set(containers) - known_containers
            if containers[name]["health_status"] is not None
        }
        if not new_names:
            return

        entities = [
            DockerMonitorHealthBinarySensor(coordinator, name)
            for name in sorted(new_names)
        ]

        known_containers.update(new_names)
        async_add_entities(entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))
