"""Custom types for docker_monitor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import DockerMonitorApiClient
    from .coordinator import DockerMonitorDataUpdateCoordinator


class DockerMonitorContainerData(TypedDict):
    """Snapshot of a single container's state."""

    name: str
    container_id: str
    image: str
    status: str
    cpu_percent: float | None
    memory_usage_mb: float | None
    memory_limit_mb: float | None
    health_status: str | None


class DockerMonitorPayload(TypedDict):
    """Coordinator payload — all running named containers."""

    containers: dict[str, DockerMonitorContainerData]


class DockerMonitorConfigData(TypedDict):
    """Shape of the data persisted on the config entry."""

    socket_path: str


class DockerMonitorOptionsData(TypedDict, total=False):
    """Shape of the options writable by the options flow."""

    scan_interval: NotRequired[int]


class DockerMonitorDiagnosticsEntry(TypedDict):
    """Entry section of the diagnostics dump."""

    title: str
    version: int
    domain: str
    data: DockerMonitorConfigData
    options: DockerMonitorOptionsData


class DockerMonitorDiagnosticsPayload(TypedDict):
    """Top-level shape returned by async_get_config_entry_diagnostics."""

    entry: DockerMonitorDiagnosticsEntry
    coordinator_data: DockerMonitorPayload | None


type DockerMonitorConfigEntry = ConfigEntry[DockerMonitorData]


@dataclass
class DockerMonitorData:
    """Data stored on entry.runtime_data."""

    client: DockerMonitorApiClient
    coordinator: DockerMonitorDataUpdateCoordinator
    integration: Integration
