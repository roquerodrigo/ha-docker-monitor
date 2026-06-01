from __future__ import annotations

import copy
from unittest.mock import MagicMock

from custom_components.docker_monitor.sensor.cpu_sensor import (
    DockerMonitorCpuSensor,
)
from custom_components.docker_monitor.sensor.memory_sensor import (
    DockerMonitorMemorySensor,
)
from tests.conftest import SAMPLE_PAYLOAD


def _coord(payload=None):
    coord = MagicMock()
    coord.data = payload or copy.deepcopy(SAMPLE_PAYLOAD)
    coord.config_entry.entry_id = "eid"
    coord.last_update_success = True
    return coord


def test_cpu_native_value():
    sensor = DockerMonitorCpuSensor(_coord(), "prometheus")
    assert sensor.native_value == 0.2


def test_cpu_native_value_none_when_missing():
    payload = {"containers": {}}
    sensor = DockerMonitorCpuSensor(_coord(payload), "prometheus")
    assert sensor.native_value is None


def test_cpu_unique_id():
    sensor = DockerMonitorCpuSensor(_coord(), "prometheus")
    assert sensor.unique_id == "eid_prometheus_cpu"


def test_memory_native_value():
    sensor = DockerMonitorMemorySensor(_coord(), "prometheus")
    assert sensor.native_value == 63.7


def test_memory_unique_id():
    sensor = DockerMonitorMemorySensor(_coord(), "prometheus")
    assert sensor.unique_id == "eid_prometheus_memory"


def test_memory_extra_attributes_expose_limit():
    sensor = DockerMonitorMemorySensor(_coord(), "prometheus")
    assert sensor.extra_state_attributes == {"memory_limit_mb": 7800.0}


def test_memory_extra_attributes_none_when_missing():
    payload = {"containers": {}}
    sensor = DockerMonitorMemorySensor(_coord(payload), "prometheus")
    assert sensor.extra_state_attributes is None


async def test_sensor_entities_created(hass, setup_integration):
    sensors = hass.states.async_all("sensor")
    assert len(sensors) == 4
