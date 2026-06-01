"""Diagnostics support for docker_monitor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import (
        DockerMonitorConfigEntry,
        DockerMonitorDiagnosticsEntry,
        DockerMonitorDiagnosticsPayload,
    )

TO_REDACT: frozenset[str] = frozenset()


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DockerMonitorConfigEntry,
) -> DockerMonitorDiagnosticsPayload:
    """Return diagnostics for a config entry."""
    diag_entry: DockerMonitorDiagnosticsEntry = {
        "title": entry.title,
        "version": entry.version,
        "domain": entry.domain,
        "data": {"socket_path": entry.data.get("socket_path", "")},
        "options": dict(entry.options),
    }
    return {
        "entry": diag_entry,
        "coordinator_data": entry.runtime_data.coordinator.data,
    }
