from __future__ import annotations

import copy
from unittest.mock import MagicMock

from custom_components.docker_monitor.const import ATTRIBUTION, DOMAIN
from custom_components.docker_monitor.entity import DockerMonitorEntity
from tests.conftest import SAMPLE_PAYLOAD


def _make_entity(name="prometheus", payload=None, options=None):
    coordinator = MagicMock()
    coordinator.data = payload or copy.deepcopy(SAMPLE_PAYLOAD)
    coordinator.config_entry.entry_id = "eid"
    coordinator.config_entry.options = options or {}
    coordinator.last_update_success = True
    return DockerMonitorEntity(coordinator=coordinator, container_name=name)


def test_attribution():
    assert _make_entity()._attr_attribution == ATTRIBUTION


def test_has_entity_name():
    assert _make_entity()._attr_has_entity_name is True


def test_device_info_name():
    assert _make_entity().device_info["name"] == "prometheus"


def test_device_info_name_with_suffix():
    entity = _make_entity(options={"device_name_suffix": " Oracle "})
    assert entity.device_info["name"] == "prometheus @ Oracle"


def test_device_info_name_ignores_blank_suffix():
    entity = _make_entity(options={"device_name_suffix": "  "})
    assert entity.device_info["name"] == "prometheus"


def test_device_info_identifiers_ignore_suffix():
    entity = _make_entity(options={"device_name_suffix": "Oracle"})
    assert entity.device_info["identifiers"] == {(DOMAIN, "prometheus")}


def test_device_info_identifiers_contain_name():
    identifiers = _make_entity().device_info["identifiers"]
    assert (DOMAIN, "prometheus") in identifiers


def test_device_info_manufacturer_is_image_name():
    assert _make_entity().device_info["manufacturer"] == "prom/prometheus"


def test_device_info_manufacturer_keeps_registry_port():
    payload = copy.deepcopy(SAMPLE_PAYLOAD)
    payload["containers"]["prometheus"]["image"] = "localhost:5000/prometheus:v3"
    entity = _make_entity(payload=payload)
    assert entity.device_info["manufacturer"] == "localhost:5000/prometheus"


def test_device_info_sw_version():
    assert _make_entity().device_info["sw_version"] == "prom/prometheus:v2.53.0"


def test_available_true_when_present():
    assert _make_entity().available is True


def test_available_false_when_missing():
    assert _make_entity("nonexistent").available is False


def test_container_returns_data():
    entity = _make_entity()
    assert entity._container is not None
    assert entity._container["name"] == "prometheus"


def test_container_returns_none_when_missing():
    entity = _make_entity("nonexistent")
    assert entity._container is None
