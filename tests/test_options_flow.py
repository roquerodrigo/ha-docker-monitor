from __future__ import annotations

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.docker_monitor.const import (
    DEFAULT_SCAN_INTERVAL_SECONDS,
)


async def test_options_flow_shows_form_with_default(hass, setup_integration):
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    scan_interval_key = next(
        k for k in schema if getattr(k, "schema", k) == CONF_SCAN_INTERVAL
    )
    assert scan_interval_key.default() == DEFAULT_SCAN_INTERVAL_SECONDS


async def test_options_flow_persists_scan_interval(
    hass, setup_integration, mock_api_client
):
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_SCAN_INTERVAL: 60}
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert setup_integration.options[CONF_SCAN_INTERVAL] == 60


async def test_options_flow_uses_existing_value_as_default(hass, setup_integration):
    hass.config_entries.async_update_entry(
        setup_integration, options={CONF_SCAN_INTERVAL: 120}
    )
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    schema = result["data_schema"].schema
    scan_interval_key = next(
        k for k in schema if getattr(k, "schema", k) == CONF_SCAN_INTERVAL
    )
    assert scan_interval_key.default() == 120


async def test_options_flow_suffix_names_devices_and_entities(
    hass, setup_integration, mock_api_client
):
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    from custom_components.docker_monitor.const import DOMAIN

    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 15, "device_name_suffix": "NAS"},
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "prometheus"), setup_integration.entry_id
    )
    assert device is not None
    assert device.name == "prometheus @ NAS"
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{setup_integration.entry_id}_prometheus_cpu"
    )
    assert hass.states.get(entity_id).name == "prometheus @ NAS CPU"


async def test_options_flow_suggests_current_suffix(hass, setup_integration):
    hass.config_entries.async_update_entry(
        setup_integration, options={"device_name_suffix": "NAS"}
    )
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    schema = result["data_schema"].schema
    suffix_key = next(
        k for k in schema if getattr(k, "schema", k) == "device_name_suffix"
    )
    assert suffix_key.description == {"suggested_value": "NAS"}


async def test_options_flow_clearing_suffix_restores_names(
    hass, setup_integration, mock_api_client
):
    from homeassistant.helpers import device_registry as dr

    from custom_components.docker_monitor.const import DOMAIN

    hass.config_entries.async_update_entry(
        setup_integration, options={"device_name_suffix": "NAS"}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_SCAN_INTERVAL: 15}
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "prometheus"), setup_integration.entry_id
    )
    assert device is not None
    assert device.name == "prometheus"
    assert "device_name_suffix" not in setup_integration.options
