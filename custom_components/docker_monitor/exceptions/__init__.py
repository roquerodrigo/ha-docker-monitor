"""Exception classes for the docker_monitor API client."""

from __future__ import annotations

from .api_client_communication_error import (
    DockerMonitorApiClientCommunicationError,
)
from .api_client_error import DockerMonitorApiClientError

__all__ = [
    "DockerMonitorApiClientCommunicationError",
    "DockerMonitorApiClientError",
]
