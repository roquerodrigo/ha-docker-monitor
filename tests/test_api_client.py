from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.docker_monitor.api import DockerMonitorApiClient
from custom_components.docker_monitor.exceptions import (
    DockerMonitorApiClientCommunicationError,
    DockerMonitorApiClientError,
)


@pytest.fixture
def mock_docker():
    with patch("custom_components.docker_monitor.api.aiodocker") as mock_mod:
        docker_instance = MagicMock()
        mock_mod.Docker.return_value = docker_instance
        mock_mod.DockerError = Exception
        yield docker_instance


@pytest.fixture
async def client(mock_docker):
    c = DockerMonitorApiClient("/var/run/docker.sock")
    await c.async_connect()
    return c


async def test_connect_creates_docker_client(mock_docker):
    client = DockerMonitorApiClient("/var/run/docker.sock")
    await client.async_connect()
    assert client._docker is not None


async def test_close_sets_none(client, mock_docker):
    mock_docker.close = AsyncMock()
    await client.async_close()
    assert client._docker is None


async def test_list_container_names_returns_names(client, mock_docker):
    container = MagicMock()
    container._container = {"Names": ["/prometheus"]}
    mock_docker.containers.list = AsyncMock(return_value=[container])

    names = await client.async_list_container_names()
    assert names == ["prometheus"]


async def test_list_container_names_skips_anonymous(client, mock_docker):
    named = MagicMock()
    named._container = {"Names": ["/prometheus"]}
    anon = MagicMock()
    anon._container = {"Names": ["/some-service-a1b2c3d4e5f6"]}
    mock_docker.containers.list = AsyncMock(return_value=[named, anon])

    names = await client.async_list_container_names()
    assert names == ["prometheus"]


async def test_list_container_names_skips_no_name(client, mock_docker):
    container = MagicMock()
    container._container = {"Names": []}
    mock_docker.containers.list = AsyncMock(return_value=[container])

    names = await client.async_list_container_names()
    assert names == []


async def test_list_containers_docker_error_raises(client, mock_docker):
    mock_docker.containers.list = AsyncMock(side_effect=OSError("socket gone"))

    with pytest.raises(DockerMonitorApiClientCommunicationError):
        await client.async_list_container_names()


async def test_get_container_data_returns_data(client, mock_docker):
    container = MagicMock()
    container.stats = AsyncMock(
        return_value=[
            {
                "cpu_stats": {
                    "cpu_usage": {"total_usage": 200},
                    "system_cpu_usage": 2000,
                    "online_cpus": 4,
                },
                "precpu_stats": {
                    "cpu_usage": {"total_usage": 100},
                    "system_cpu_usage": 1000,
                },
                "memory_stats": {
                    "usage": 104857600,
                    "limit": 1073741824,
                    "stats": {"cache": 0},
                },
            }
        ],
    )
    container.show = AsyncMock(
        return_value={
            "Id": "346ee219ec9fabcdef123456",
            "Config": {"Image": "prom/prometheus:v2.53.0"},
            "State": {
                "Status": "running",
                "Health": {"Status": "healthy"},
            },
        },
    )
    mock_docker.containers.get = AsyncMock(return_value=container)

    data = await client.async_get_container_data("prometheus")
    assert data["name"] == "prometheus"
    assert data["cpu_percent"] == 40.0
    assert data["memory_usage_mb"] == 100.0
    assert data["health_status"] == "healthy"
    assert data["container_id"] == "346ee219ec9f"


async def test_get_container_data_no_health(client, mock_docker):
    container = MagicMock()
    container.stats = AsyncMock(return_value=[{}])
    container.show = AsyncMock(
        return_value={
            "Id": "bed43db69acb",
            "Config": {"Image": "test:latest"},
            "State": {"Status": "running"},
        },
    )
    mock_docker.containers.get = AsyncMock(return_value=container)

    data = await client.async_get_container_data("test")
    assert data["health_status"] is None


async def test_get_container_data_oserror_raises(client, mock_docker):
    mock_docker.containers.get = AsyncMock(side_effect=OSError("gone"))

    with pytest.raises(DockerMonitorApiClientCommunicationError):
        await client.async_get_container_data("test")


async def test_client_property_raises_when_not_connected():
    client = DockerMonitorApiClient("/var/run/docker.sock")
    with pytest.raises(DockerMonitorApiClientError):
        _ = client._client


async def test_connect_oserror_raises():
    with patch(
        "custom_components.docker_monitor.api.aiodocker.Docker",
        side_effect=OSError("socket missing"),
    ):
        client = DockerMonitorApiClient("/nonexistent")
        with pytest.raises(DockerMonitorApiClientCommunicationError):
            await client.async_connect()
