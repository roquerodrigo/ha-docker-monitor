from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.docker_monitor.const import DOMAIN
from custom_components.docker_monitor.exceptions import (
    DockerMonitorApiClientCommunicationError,
    DockerMonitorApiClientError,
)

USER_INPUT = {"socket_path": "/var/run/docker.sock"}
NEW_INPUT = {"socket_path": "/run/docker.sock"}


def _patch_client(side_effect=None):
    return patch(
        "custom_components.docker_monitor.config_flow.DockerMonitorApiClient",
    )


async def _start_user_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )


async def test_step_user_shows_form(hass, enable_custom_integrations):
    result = await _start_user_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_step_user_success(hass, enable_custom_integrations):
    with _patch_client() as mock:
        instance = mock.return_value
        instance.async_connect = AsyncMock()
        instance.async_close = AsyncMock()
        instance.async_list_container_names = AsyncMock(return_value=["test"])
        result = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=USER_INPUT,
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == USER_INPUT["socket_path"]
    assert result["data"] == USER_INPUT


async def test_step_user_duplicate_aborts(hass, enable_custom_integrations):
    with _patch_client() as mock:
        instance = mock.return_value
        instance.async_connect = AsyncMock()
        instance.async_close = AsyncMock()
        instance.async_list_container_names = AsyncMock(return_value=["test"])
        flow1 = await _start_user_flow(hass)
        await hass.config_entries.flow.async_configure(
            flow1["flow_id"],
            user_input=USER_INPUT,
        )
        flow2 = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow2["flow_id"],
            user_input=USER_INPUT,
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_step_user_connection_error(hass, enable_custom_integrations):
    with _patch_client() as mock:
        instance = mock.return_value
        instance.async_connect = AsyncMock(
            side_effect=DockerMonitorApiClientCommunicationError("fail"),
        )
        instance.async_close = AsyncMock()
        flow = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"],
            user_input=USER_INPUT,
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "connection"
    instance.async_close.assert_awaited_once()


async def test_step_user_unknown_error(hass, enable_custom_integrations):
    with _patch_client() as mock:
        instance = mock.return_value
        instance.async_connect = AsyncMock()
        instance.async_close = AsyncMock()
        instance.async_list_container_names = AsyncMock(
            side_effect=DockerMonitorApiClientError("oops"),
        )
        flow = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"],
            user_input=USER_INPUT,
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"
    instance.async_close.assert_awaited_once()


def _existing_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=USER_INPUT,
        unique_id="var-run-docker-sock",
    )
    entry.add_to_hass(hass)
    return entry


async def test_reconfigure_shows_form(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"


async def test_reconfigure_success(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    with _patch_client() as mock:
        instance = mock.return_value
        instance.async_connect = AsyncMock()
        instance.async_close = AsyncMock()
        instance.async_list_container_names = AsyncMock(return_value=["test"])
        result = await entry.start_reconfigure_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=NEW_INPUT,
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["socket_path"] == "/run/docker.sock"
