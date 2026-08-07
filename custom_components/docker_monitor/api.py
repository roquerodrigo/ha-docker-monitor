"""Docker Monitor API Client — wraps aiodocker."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import aiodocker

from .const import LOGGER
from .exceptions import (
    DockerMonitorApiClientCommunicationError,
    DockerMonitorApiClientError,
)

if TYPE_CHECKING:
    from .data import DockerMonitorContainerData

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
type JsonObject = dict[str, JsonValue]

_MIN_HASH_LENGTH = 12
_HEX_DIGITS = frozenset("0123456789abcdef")


class DockerMonitorApiClient:
    """Async client that talks to the Docker Engine via a Unix socket."""

    def __init__(self, socket_path: str) -> None:
        """Initialize."""
        self._socket_path = socket_path
        self._docker: aiodocker.Docker | None = None

    async def async_connect(self) -> None:
        """
        Open a connection to the Docker daemon and verify it responds.

        ``aiodocker.Docker(...)`` is lazy — constructing it never touches
        the socket — so a bad path only surfaces on the first request.
        Issue a lightweight ``version()`` here so an unreachable or
        non-existent socket fails fast at connect time (which is what the
        config flow relies on to validate the path).
        """
        docker = aiodocker.Docker(url=f"unix://{self._socket_path}")
        try:
            await docker.version()
        except (aiodocker.DockerError, OSError, ValueError) as exception:
            await docker.close()
            msg = f"Failed to connect to Docker at {self._socket_path}: {exception}"
            raise DockerMonitorApiClientCommunicationError(msg) from exception
        self._docker = docker

    async def async_close(self) -> None:
        """Close the connection."""
        if self._docker is not None:
            await self._docker.close()
            self._docker = None

    async def async_list_container_names(self) -> list[str]:
        """Return the names of all running named containers."""
        try:
            containers = await self._client.containers.list()
        except (aiodocker.DockerError, OSError) as exception:
            msg = f"Failed to list containers: {exception}"
            raise DockerMonitorApiClientCommunicationError(msg) from exception

        names: list[str] = []
        for container in containers:
            # ``DockerContainer`` exposes the raw daemon payload via
            # ``__getitem__``; ``Names`` is the list of "/name" aliases.
            try:
                raw_names: list[str] = container["Names"]
            except KeyError:
                continue
            if not raw_names:
                continue
            name = raw_names[0].lstrip("/")
            if _is_anonymous(name):
                continue
            names.append(name)
        return names

    async def async_get_container_data(
        self,
        name: str,
    ) -> DockerMonitorContainerData:
        """Fetch stats and health for a container by name."""
        try:
            container = await self._client.containers.get(name)
            stats_list, inspect = await asyncio.gather(
                container.stats(stream=False),
                container.show(),
            )
        except (aiodocker.DockerError, OSError) as exception:
            msg = f"Failed to get data for container {name}: {exception}"
            raise DockerMonitorApiClientCommunicationError(msg) from exception

        stats = stats_list[0] if stats_list else {}

        cpu_percent = _calculate_cpu_percent(stats)
        memory_usage_mb, memory_limit_mb = _calculate_memory(stats)

        health_obj = inspect.get("State", {}).get("Health")
        health_status: str | None = (
            health_obj.get("Status") if isinstance(health_obj, dict) else None
        )

        image: str = inspect.get("Config", {}).get("Image", "")
        status: str = inspect.get("State", {}).get("Status", "unknown")
        container_id: str = inspect.get("Id", "")[:12]

        return {
            "name": name,
            "container_id": container_id,
            "image": image,
            "status": status,
            "cpu_percent": cpu_percent,
            "memory_usage_mb": memory_usage_mb,
            "memory_limit_mb": memory_limit_mb,
            "health_status": health_status,
        }

    @property
    def _client(self) -> aiodocker.Docker:
        """Return the active Docker client or raise."""
        if self._docker is None:
            msg = "Docker client is not connected"
            raise DockerMonitorApiClientError(msg)
        return self._docker


def _is_anonymous(name: str) -> bool:
    """
    Return True for auto-generated container names.

    Matches the two auto-generated shapes Docker actually produces — Compose
    one-off containers (``<project>-<service>-run-<hash>``) and fully hex,
    id-like names — without hiding a user-named container that merely ends in
    a hex-looking segment.
    """
    if _is_hex_hash(name):
        return True
    _, separator, suffix = name.rpartition("-run-")
    return bool(separator) and _is_hex_hash(suffix)


def _is_hex_hash(text: str) -> bool:
    """Return True when the text is a hex string long enough to be a hash."""
    return len(text) >= _MIN_HASH_LENGTH and set(text) <= _HEX_DIGITS


def _calculate_cpu_percent(stats: JsonObject) -> float | None:
    """Calculate CPU usage percentage from Docker stats."""
    cpu_stats = stats.get("cpu_stats")
    precpu_stats = stats.get("precpu_stats")
    if not isinstance(cpu_stats, dict) or not isinstance(precpu_stats, dict):
        return None

    cpu_usage = cpu_stats.get("cpu_usage")
    precpu_usage = precpu_stats.get("cpu_usage")
    if not isinstance(cpu_usage, dict) or not isinstance(precpu_usage, dict):
        return None

    cpu_total = cpu_usage.get("total_usage")
    precpu_total = precpu_usage.get("total_usage")
    sys_usage = cpu_stats.get("system_cpu_usage")
    presys_usage = precpu_stats.get("system_cpu_usage")
    online_cpus = cpu_stats.get("online_cpus")

    if (
        not isinstance(cpu_total, int | float)
        or not isinstance(precpu_total, int | float)
        or not isinstance(sys_usage, int | float)
        or not isinstance(presys_usage, int | float)
        or not isinstance(online_cpus, int | float)
    ):
        return None

    cpu_delta = float(cpu_total) - float(precpu_total)
    sys_delta = float(sys_usage) - float(presys_usage)

    if sys_delta <= 0 or float(online_cpus) <= 0:
        return None

    # Official `docker stats` formula: the container's share of total CPU
    # time over the sampling window, scaled by the number of online CPUs so
    # 100% means one fully-saturated core (matches the Docker CLI / API docs).
    percent = round((cpu_delta / sys_delta) * float(online_cpus) * 100.0, 2)
    LOGGER.debug("CPU: %.2f%% (online_cpus=%s)", percent, online_cpus)
    return percent


def _calculate_memory(
    stats: JsonObject,
) -> tuple[float | None, float | None]:
    """Calculate memory usage in MB from Docker stats."""
    mem_stats = stats.get("memory_stats")
    if not isinstance(mem_stats, dict):
        return None, None

    usage = mem_stats.get("usage")
    limit = mem_stats.get("limit")
    if not isinstance(usage, int | float) or not isinstance(limit, int | float):
        return None, None

    cache: int | float = 0
    inner_stats = mem_stats.get("stats")
    if isinstance(inner_stats, dict):
        raw_cache = inner_stats.get("cache", 0)
        if isinstance(raw_cache, int | float):
            cache = raw_cache

    used_mb = round((usage - cache) / 1024 / 1024, 1)
    limit_mb = round(limit / 1024 / 1024, 1)

    LOGGER.debug("Memory: used=%s MB, limit=%s MB", used_mb, limit_mb)

    return used_mb, limit_mb
