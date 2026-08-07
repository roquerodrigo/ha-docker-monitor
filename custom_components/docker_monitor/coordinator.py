"""DataUpdateCoordinator for docker_monitor."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER
from .exceptions import DockerMonitorApiClientError

if TYPE_CHECKING:
    from datetime import timedelta

    from homeassistant.core import HomeAssistant

    from .data import (
        DockerMonitorConfigEntry,
        DockerMonitorContainerData,
        DockerMonitorPayload,
    )


class DockerMonitorDataUpdateCoordinator(
    DataUpdateCoordinator["DockerMonitorPayload"],
):
    """Coordinator that polls Docker for container stats."""

    config_entry: DockerMonitorConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: DockerMonitorConfigEntry,
        scan_interval: timedelta,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=scan_interval,
            always_update=False,
        )

    async def _async_update_data(self) -> DockerMonitorPayload:
        """Fetch stats for all running named containers."""
        client = self.config_entry.runtime_data.client
        try:
            names = await client.async_list_container_names()
            results: list[DockerMonitorContainerData] = list(
                await asyncio.gather(
                    *(client.async_get_container_data(n) for n in names),
                ),
            )
        except DockerMonitorApiClientError as exception:
            raise UpdateFailed(exception) from exception

        containers: dict[str, DockerMonitorContainerData] = {
            r["name"]: r for r in results
        }
        return {"containers": containers}
