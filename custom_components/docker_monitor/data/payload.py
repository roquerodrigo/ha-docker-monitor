"""Coordinator payload type."""

from __future__ import annotations

from typing import TypedDict

from .container_data import DockerMonitorContainerData


class DockerMonitorPayload(TypedDict):
    """Coordinator payload — all running named containers."""

    containers: dict[str, DockerMonitorContainerData]
