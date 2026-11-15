"""Options flow for docker_monitor."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers import selector

from .const import (
    CONF_DEVICE_NAME_SUFFIX,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)

if TYPE_CHECKING:
    from .data import DockerMonitorOptionsData


class DockerMonitorOptionsFlow(OptionsFlow):
    """Options flow for Docker Monitor."""

    async def async_step_init(
        self,
        user_input: DockerMonitorOptionsData | None = None,
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=dict(user_input))

        current_value: int = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL_SECONDS,
        )
        current_suffix: str = self.config_entry.options.get(
            CONF_DEVICE_NAME_SUFFIX,
            "",
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_value,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_SECONDS,
                            step=5,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                    # A suggested value instead of a default, so clearing the
                    # field removes the suffix rather than restoring it.
                    vol.Optional(
                        CONF_DEVICE_NAME_SUFFIX,
                        description={"suggested_value": current_suffix},
                    ): selector.TextSelector(),
                },
            ),
        )
