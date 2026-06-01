"""Options flow data type."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class DockerMonitorOptionsData(TypedDict, total=False):
    """Shape of the options writable by the options flow."""

    scan_interval: NotRequired[int]
