"""Runtime data stored on entry.runtime_data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from ..api import DockerMonitorApiClient
    from ..coordinator import DockerMonitorDataUpdateCoordinator


type DockerMonitorConfigEntry = ConfigEntry[DockerMonitorData]


@dataclass
class DockerMonitorData:
    """Data stored on entry.runtime_data."""

    client: DockerMonitorApiClient
    coordinator: DockerMonitorDataUpdateCoordinator
    integration: Integration
