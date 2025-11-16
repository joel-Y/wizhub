"""WizSmith Home Integration Sensors with MQTT publishing and debugging."""

import logging
import json
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import mqtt as hass_mqtt

_LOGGER = logging.getLogger(__name__)

DOMAIN = "wizsmith_home_integration"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    mqtt = hass.components.mqtt

    devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    entities = []

    for dev in devices:
        entities.append(WizSmithStateSensor(hass, mqtt, dev))

    async_add_entities(entities)


class WizSmithStateSensor(SensorEntity):
    def __init__(self, hass, mqtt, device):
        self.hass = hass
        self._mqtt = mqtt
        self._device = device
        self._state = None
        self._attr_name = f"WizSmith {device['id']} State"
        self._attr_unique_id = f"wizsmith_{device['id']}_state"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device['id'])},
            name=f"WizSmith Device {device['id']}",
            manufacturer="WizSmith",
        )

    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        # Example: fetch local state
        self._state = self._device.get("status", "unknown")
        await self._publish_state()

    async def _publish_state(self):
        topic = f"wizsmith/{self._device['id']}/state"
        payload = json.dumps({"state": self._state})

        _LOGGER.debug("Publishing MQTT state to %s: %s", topic, payload)
        self._mqtt.async_publish(topic, payload, qos=0, retain=False)
