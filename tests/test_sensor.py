from __future__ import annotations

import copy
from datetime import UTC, datetime
from unittest.mock import MagicMock

from custom_components.docker_monitor.sensor.cpu_sensor import (
    DockerMonitorCpuSensor,
)
from custom_components.docker_monitor.sensor.image_sensor import (
    DockerMonitorImageSensor,
)
from custom_components.docker_monitor.sensor.image_tag_sensor import (
    DockerMonitorImageTagSensor,
)
from custom_components.docker_monitor.sensor.memory_sensor import (
    DockerMonitorMemorySensor,
)
from custom_components.docker_monitor.sensor.uptime_sensor import (
    DockerMonitorUptimeSensor,
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


def test_cpu_extra_attributes_expose_online_cpus():
    sensor = DockerMonitorCpuSensor(_coord(), "prometheus")
    assert sensor.extra_state_attributes == {"online_cpus": 4}


def test_cpu_extra_attributes_none_when_missing():
    payload = {"containers": {}}
    sensor = DockerMonitorCpuSensor(_coord(payload), "prometheus")
    assert sensor.extra_state_attributes is None


def test_cpu_extra_attributes_none_without_online_cpus():
    payload = copy.deepcopy(SAMPLE_PAYLOAD)
    payload["containers"]["prometheus"]["online_cpus"] = None
    sensor = DockerMonitorCpuSensor(_coord(payload), "prometheus")
    assert sensor.extra_state_attributes is None


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
    assert len(sensors) == 10


def test_uptime_native_value():
    sensor = DockerMonitorUptimeSensor(_coord(), "prometheus")
    assert sensor.native_value == datetime(2026, 11, 10, 17, 30, 18, 347365, tzinfo=UTC)


def test_uptime_native_value_none_when_missing():
    sensor = DockerMonitorUptimeSensor(_coord({"containers": {}}), "prometheus")
    assert sensor.native_value is None


def test_uptime_unique_id():
    sensor = DockerMonitorUptimeSensor(_coord(), "prometheus")
    assert sensor.unique_id == "eid_prometheus_uptime"


def test_image_native_value_is_repository():
    sensor = DockerMonitorImageSensor(_coord(), "prometheus")
    assert sensor.native_value == "prom/prometheus"


def test_image_native_value_none_when_missing():
    sensor = DockerMonitorImageSensor(_coord({"containers": {}}), "prometheus")
    assert sensor.native_value is None


def test_image_native_value_none_when_image_empty():
    payload = copy.deepcopy(SAMPLE_PAYLOAD)
    payload["containers"]["prometheus"]["image"] = ""
    sensor = DockerMonitorImageSensor(_coord(payload), "prometheus")
    assert sensor.native_value is None


def test_image_unique_id():
    sensor = DockerMonitorImageSensor(_coord(), "prometheus")
    assert sensor.unique_id == "eid_prometheus_image"


def test_image_tag_native_value():
    sensor = DockerMonitorImageTagSensor(_coord(), "prometheus")
    assert sensor.native_value == "v2.53.0"


def test_image_tag_native_value_none_when_missing():
    sensor = DockerMonitorImageTagSensor(_coord({"containers": {}}), "prometheus")
    assert sensor.native_value is None


def test_image_tag_native_value_none_when_image_empty():
    payload = copy.deepcopy(SAMPLE_PAYLOAD)
    payload["containers"]["prometheus"]["image"] = ""
    sensor = DockerMonitorImageTagSensor(_coord(payload), "prometheus")
    assert sensor.native_value is None


def test_image_tag_unique_id():
    sensor = DockerMonitorImageTagSensor(_coord(), "prometheus")
    assert sensor.unique_id == "eid_prometheus_image_tag"
