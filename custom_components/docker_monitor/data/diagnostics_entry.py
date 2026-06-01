"""Diagnostics entry type."""

from __future__ import annotations

from typing import TypedDict

from .config_data import DockerMonitorConfigData
from .options_data import DockerMonitorOptionsData


class DockerMonitorDiagnosticsEntry(TypedDict):
    """Entry section of the diagnostics dump."""

    title: str
    version: int
    domain: str
    data: DockerMonitorConfigData
    options: DockerMonitorOptionsData
