"""DataUpdateCoordinator for docker_monitor."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, RUNNING_STATE
from .exceptions import DockerMonitorApiClientError
from .stale_device_remover import DockerMonitorStaleDeviceRemover

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
    """
    Coordinator that polls Docker for container stats.

    The first refresh skips the resource stats so the entry sets up without
    waiting on Docker's one-second CPU sampling; every later refresh, starting
    with the one setup schedules in the background, includes them.

    A container whose data cannot be fetched is left out of that refresh, so
    only its own entities become unavailable; the refresh fails as a whole
    only when the container list or every container fails.
    """

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
        self._stale_device_remover = DockerMonitorStaleDeviceRemover(hass, entry)
        self._includes_stats = False
        self._unavailable_containers: set[str] = set()

    async def _async_update_data(self) -> DockerMonitorPayload:
        """Fetch stats for all running named containers."""
        client = self.config_entry.runtime_data.client
        include_stats = self._includes_stats
        self._includes_stats = True
        try:
            container_states = await client.async_list_container_states()
        except DockerMonitorApiClientError as exception:
            raise UpdateFailed(exception) from exception

        names = [
            name for name, state in container_states.items() if state == RUNNING_STATE
        ]
        outcomes = await asyncio.gather(
            *(
                self._async_fetch_container(name, include_stats=include_stats)
                for name in names
            ),
        )
        failures = [
            outcome
            for outcome in outcomes
            if isinstance(outcome, DockerMonitorApiClientError)
        ]
        if names and len(failures) == len(names):
            raise UpdateFailed(failures[0]) from failures[0]

        self._log_availability_changes(names, outcomes)
        self._stale_device_remover.async_remove_missing(container_states)

        containers: dict[str, DockerMonitorContainerData] = {
            outcome["name"]: outcome
            for outcome in outcomes
            if not isinstance(outcome, DockerMonitorApiClientError)
        }
        return {"containers": containers}

    async def _async_fetch_container(
        self,
        name: str,
        *,
        include_stats: bool,
    ) -> DockerMonitorContainerData | DockerMonitorApiClientError:
        """Fetch one container, returning the error instead of raising it."""
        client = self.config_entry.runtime_data.client
        try:
            return await client.async_get_container_data(
                name, include_stats=include_stats
            )
        except DockerMonitorApiClientError as exception:
            return exception

    def _log_availability_changes(
        self,
        names: list[str],
        outcomes: list[DockerMonitorContainerData | DockerMonitorApiClientError],
    ) -> None:
        """Log once when a container stops answering and once when it is back."""
        failed_now: set[str] = set()
        for name, outcome in zip(names, outcomes, strict=True):
            if isinstance(outcome, DockerMonitorApiClientError):
                failed_now.add(name)
                if name not in self._unavailable_containers:
                    LOGGER.info("Container %s is unavailable: %s", name, outcome)
            elif name in self._unavailable_containers:
                LOGGER.info("Container %s is available again", name)
        self._unavailable_containers = failed_now
