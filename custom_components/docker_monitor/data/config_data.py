"""Config entry data type."""

from __future__ import annotations

from typing import TypedDict


class DockerMonitorConfigData(TypedDict):
    """Shape of the data persisted on the config entry."""

    socket_path: str
