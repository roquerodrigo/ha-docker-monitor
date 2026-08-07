from __future__ import annotations

import copy
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

pytest_plugins = "pytest_homeassistant_custom_component"

SAMPLE_CONTAINER: dict = {
    "name": "prometheus",
    "container_id": "346ee219ec9f",
    "image": "prom/prometheus:v2.53.0",
    "status": "running",
    "cpu_percent": 0.2,
    "memory_usage_mb": 63.7,
    "memory_limit_mb": 7800.0,
    "health_status": "healthy",
}

SAMPLE_CONTAINER_NO_HEALTH: dict = {
    "name": "nginx",
    "container_id": "bed43db69acb",
    "image": "nginx:1.27",
    "status": "running",
    "cpu_percent": 0.1,
    "memory_usage_mb": 40.0,
    "memory_limit_mb": 7800.0,
    "health_status": None,
}

SAMPLE_PAYLOAD: dict = {
    "containers": {
        "prometheus": copy.deepcopy(SAMPLE_CONTAINER),
        "nginx": copy.deepcopy(SAMPLE_CONTAINER_NO_HEALTH),
    },
}


@pytest.fixture
def sample_payload() -> dict:
    return copy.deepcopy(SAMPLE_PAYLOAD)


@pytest.fixture
def enable_custom_integrations(hass) -> None:
    from homeassistant.loader import DATA_CUSTOM_COMPONENTS

    hass.data.pop(DATA_CUSTOM_COMPONENTS, None)


@pytest.fixture
def mock_api_client(sample_payload) -> Generator:
    with (
        patch(
            "custom_components.docker_monitor.DockerMonitorApiClient",
        ) as mock_class,
        patch(
            "custom_components.docker_monitor.config_flow.DockerMonitorApiClient",
        ) as mock_flow_class,
    ):
        instance = mock_class.return_value
        instance.async_connect = AsyncMock()
        instance.async_close = AsyncMock()
        instance.async_list_container_names = AsyncMock(
            return_value=list(sample_payload["containers"].keys()),
        )
        instance.async_get_container_data = AsyncMock(
            side_effect=lambda name: copy.deepcopy(
                sample_payload["containers"][name],
            ),
        )

        flow_instance = mock_flow_class.return_value
        flow_instance.async_connect = AsyncMock()
        flow_instance.async_close = AsyncMock()
        flow_instance.async_list_container_names = AsyncMock(
            return_value=["prometheus"],
        )

        yield instance


@pytest.fixture
async def setup_integration(hass, mock_api_client, enable_custom_integrations):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.docker_monitor.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"socket_path": "/var/run/docker.sock"},
        unique_id="var-run-docker-sock",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
