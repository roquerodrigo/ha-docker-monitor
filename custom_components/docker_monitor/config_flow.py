"""Config flow for docker_monitor."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import DockerMonitorApiClient
from .const import (
    CONF_DOCKER_HOST,
    CONFIG_ENTRY_VERSION,
    DEFAULT_DOCKER_HOST,
    DOMAIN,
    LOGGER,
)
from .docker_host import DockerHost
from .exceptions import (
    DockerMonitorApiClientCommunicationError,
    DockerMonitorApiClientError,
)
from .options_flow import DockerMonitorOptionsFlow

if TYPE_CHECKING:
    from .data import DockerMonitorConfigData, DockerMonitorConfigEntry


def _docker_host_schema(default_url: str | None = None) -> vol.Schema:
    """Build the Docker host schema, optionally pre-filled."""
    return vol.Schema(
        {
            vol.Required(
                CONF_DOCKER_HOST,
                default=default_url or DEFAULT_DOCKER_HOST,
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
            ),
        },
    )


class DockerMonitorFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Docker Monitor."""

    VERSION = CONFIG_ENTRY_VERSION

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
            docker_host = DockerHost(user_input["docker_host"])
            errors = await self._validate(docker_host)
            if not errors:
                await self.async_set_unique_id(docker_host.unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=docker_host.url,
                    data={"docker_host": docker_host.url},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_docker_host_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: DockerMonitorConfigData | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Allow editing the Docker host of an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        existing = cast("DockerMonitorConfigData", entry.data)

        if user_input is not None:
            docker_host = DockerHost(user_input["docker_host"])
            errors = await self._validate(docker_host)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={"docker_host": docker_host.url},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_docker_host_schema(
                default_url=existing.get("docker_host"),
            ),
            errors=errors,
        )

    async def _validate(self, docker_host: DockerHost) -> dict[str, str]:
        """Test the connection to the Docker daemon."""
        if not docker_host.is_supported:
            return {"base": "invalid_host"}
        client = DockerMonitorApiClient(docker_host_url=docker_host.url)
        try:
            await client.async_connect()
            await client.async_list_container_names()
        except DockerMonitorApiClientCommunicationError as exception:
            LOGGER.error("Failed to connect to Docker: %s", exception)
            return {"base": "connection"}
        except DockerMonitorApiClientError:
            LOGGER.exception("Failed to validate Docker host")
            return {"base": "unknown"}
        finally:
            await client.async_close()
        return {}
