from __future__ import annotations

import copy
from unittest.mock import MagicMock

from custom_components.docker_monitor.binary_sensor.health_binary_sensor import (
    DockerMonitorHealthBinarySensor,
)
from tests.conftest import SAMPLE_PAYLOAD


def _coord(payload=None):
    coord = MagicMock()
    coord.data = payload or copy.deepcopy(SAMPLE_PAYLOAD)
    coord.config_entry.entry_id = "eid"
    coord.last_update_success = True
    return coord


def test_health_is_on_when_unhealthy():
    payload = copy.deepcopy(SAMPLE_PAYLOAD)
    payload["containers"]["prometheus"]["health_status"] = "unhealthy"
    sensor = DockerMonitorHealthBinarySensor(_coord(payload), "prometheus")
    assert sensor.is_on is True


def test_health_is_off_when_healthy():
    sensor = DockerMonitorHealthBinarySensor(_coord(), "prometheus")
    assert sensor.is_on is False


def test_health_is_none_when_no_health():
    sensor = DockerMonitorHealthBinarySensor(_coord(), "nginx")
    assert sensor.is_on is None


def test_health_unique_id():
    sensor = DockerMonitorHealthBinarySensor(_coord(), "prometheus")
    assert sensor.unique_id == "eid_prometheus_health"


async def test_health_entity_only_for_containers_with_healthcheck(
    hass, setup_integration
):
    binary_sensors = hass.states.async_all("binary_sensor")
    assert len(binary_sensors) == 1
    assert "prometheus" in binary_sensors[0].entity_id


async def test_health_entity_added_when_healthcheck_appears_later(
    hass, setup_integration, sample_payload
):
    coordinator = setup_integration.runtime_data.coordinator
    late_payload = copy.deepcopy(sample_payload)
    late_payload["containers"]["nginx"]["health_status"] = "healthy"
    coordinator.async_set_updated_data(late_payload)
    await hass.async_block_till_done()

    binary_sensors = hass.states.async_all("binary_sensor")
    assert len(binary_sensors) == 2
    assert any("nginx" in state.entity_id for state in binary_sensors)
