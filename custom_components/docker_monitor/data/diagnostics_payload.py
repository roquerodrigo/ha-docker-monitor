"""Diagnostics payload type."""

from __future__ import annotations

from typing import TypedDict

from .diagnostics_entry import DockerMonitorDiagnosticsEntry
from .payload import DockerMonitorPayload


class DockerMonitorDiagnosticsPayload(TypedDict):
    """Top-level shape returned by async_get_config_entry_diagnostics."""

    entry: DockerMonitorDiagnosticsEntry
    coordinator_data: DockerMonitorPayload | None
