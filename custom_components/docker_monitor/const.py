"""Constants for docker_monitor."""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "docker_monitor"
ATTRIBUTION = "Data provided by Docker Engine API"

CONF_SOCKET_PATH = "socket_path"
DEFAULT_SOCKET_PATH = "/var/run/docker.sock"

DEFAULT_SCAN_INTERVAL_SECONDS = 30
MIN_SCAN_INTERVAL_SECONDS = 10
