"""Container snapshot type."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from datetime import datetime


class DockerMonitorContainerData(TypedDict):
    """Snapshot of a single container's state."""

    name: str
    container_id: str
    image: str
    status: str
    cpu_percent: float | None
    online_cpus: int | None
    memory_usage_mb: float | None
    memory_limit_mb: float | None
    health_status: str | None
    started_at: datetime | None
