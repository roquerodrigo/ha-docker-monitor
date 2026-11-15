"""Constants for docker_monitor."""

from __future__ import annotations

from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "docker_monitor"
ATTRIBUTION = "Data provided by Docker Engine API"

CONFIG_ENTRY_VERSION = 2

CONF_DOCKER_HOST = "docker_host"
DEFAULT_DOCKER_HOST = "unix:///var/run/docker.sock"
SUPPORTED_DOCKER_HOST_SCHEMES = frozenset({"unix", "tcp", "http", "https"})
REQUEST_TIMEOUT = timedelta(seconds=30)

CONF_DEVICE_NAME_SUFFIX = "device_name_suffix"

DEFAULT_SCAN_INTERVAL_SECONDS = 15
MIN_SCAN_INTERVAL_SECONDS = 10

RUNNING_STATE = "running"
STALE_DEVICE_GRACE_PERIOD = timedelta(minutes=5)

STATIC_URL_PREFIX = "/docker_monitor"
