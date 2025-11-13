"""Config flow for WizSmith Home Integration."""

from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, DEFAULT_OR_REALM, DEFAULT_GITHUB_REPO, DEFAULT_SYNC_INTERVAL

class WizSmithConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the configuration flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            if not user_input.get("mqtt_host"):
                errors["mqtt_host"] = "required"
            else:
                return self.async_create_entry(
                    title="WizSmith Home Integration", data=user_input
                )

        data_schema = vol.Schema({
            vol.Required("mqtt_host", default="core-mosquitto"): str,
            vol.Optional("mqtt_port", default=1883): int,
            vol.Optional("mqtt_user", default=""): str,
            vol.Optional("mqtt_pass", default=""): str,
            vol.Required("openremote_url", default="http://74.208.69.198:8080"): str,
            vol.Optional("openremote_user", default=""): str,
            vol.Optional("openremote_pass", default=""): str,
            vol.Optional("openremote_client_id", default=""): str,
            vol.Optional("openremote_client_secret", default=""): str,
            vol.Optional("openremote_realm", default=DEFAULT_OR_REALM): str,
            vol.Optional("sync_interval", default=DEFAULT_SYNC_INTERVAL): int,
            vol.Optional("github_repo", default=DEFAULT_GITHUB_REPO): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WizSmithOptionsFlowHandler(config_entry)


class WizSmithOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.data
        data_schema = vol.Schema({
            vol.Optional("sync_interval", default=data.get("sync_interval", 30)): int,
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
