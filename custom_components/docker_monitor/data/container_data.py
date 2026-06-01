"""Container snapshot type."""

from __future__ import annotations

from typing import TypedDict


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
