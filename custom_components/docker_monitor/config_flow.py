"""Config flow for docker_monitor."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .api import DockerMonitorApiClient
from .const import CONF_SOCKET_PATH, DEFAULT_SOCKET_PATH, DOMAIN, LOGGER
from .exceptions import (
    DockerMonitorApiClientCommunicationError,
    DockerMonitorApiClientError,
)
from .options_flow import DockerMonitorOptionsFlow

if TYPE_CHECKING:
    from .data import DockerMonitorConfigData, DockerMonitorConfigEntry


def _socket_schema(default_path: str | None = None) -> vol.Schema:
    """Build the socket path schema, optionally pre-filled."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SOCKET_PATH,
                default=default_path or DEFAULT_SOCKET_PATH,
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
            ),
        },
    )


class DockerMonitorFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Docker Monitor."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: DockerMonitorConfigEntry,  # noqa: ARG004
    ) -> DockerMonitorOptionsFlow:
        """Return the options flow handler."""
        return DockerMonitorOptionsFlow()

    async def async_step_user(  # type: ignore[override]  # narrowed user_input type
        self,
        user_input: DockerMonitorConfigData | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._validate(user_input)
            if not errors:
                await self.async_set_unique_id(
                    slugify(user_input["socket_path"]),
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input["socket_path"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_socket_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: DockerMonitorConfigData | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Allow editing the socket path of an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        existing = cast("DockerMonitorConfigData", entry.data)

        if user_input is not None:
            errors = await self._validate(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=dict(user_input),
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_socket_schema(
                default_path=existing.get("socket_path"),
            ),
            errors=errors,
        )

    async def _validate(
        self,
        user_input: DockerMonitorConfigData,
    ) -> dict[str, str]:
        """Test connection to the Docker socket."""
        client = DockerMonitorApiClient(
            socket_path=user_input["socket_path"],
        )
        try:
            await client.async_connect()
            await client.async_list_container_names()
        except DockerMonitorApiClientCommunicationError as exception:
            LOGGER.error("Failed to connect to Docker socket: %s", exception)
            return {"base": "connection"}
        except DockerMonitorApiClientError:
            LOGGER.exception("Failed to validate Docker socket")
            return {"base": "unknown"}
        finally:
            await client.async_close()
        return {}
