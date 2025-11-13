"""Sensor publisher."""

import json
import logging
from homeassistant.core import HomeAssistant
from .const import *

_LOGGER = logging.getLogger(__name__)

async def publish_sensors(hass: HomeAssistant, client, or_client):
    """Publish all sensor and binary_sensor states to MQTT and OpenRemote."""
    states = hass.states.async_all()
    batch = {}
    for s in states:
        if s.entity_id.startswith(("sensor.", "binary_sensor.")):
            topic = f"wizsmith/{or_client.pi_id}/{s.domain}/{s.object_id}/state"
            payload = {
                "entity_id": s.entity_id,
                "state": s.state,
                "attributes": s.attributes,
                "last_changed": str(s.last_changed),
            }
            try:
                client.publish(topic, json.dumps(payload), qos=1, retain=False)
            except Exception:
                _LOGGER.debug("MQTT publish failed for %s", topic)
            batch[topic] = payload

    if getattr(or_client, 'token', None) and getattr(or_client, 'child_id', None) and getattr(or_client, 'child_attr', None):
        try:
            import aiohttp
            attr_url = f"{or_client.cfg.get('openremote_url').rstrip('/')}/api/master/asset/{or_client.child_id}/attribute/{or_client.child_attr}"
            headers = {"Authorization": f"Bearer {or_client.token}", "Content-Type": "application/json"}
            async with aiohttp.ClientSession() as s:
                async with s.post(attr_url, json=batch, headers=headers, timeout=10):
                    pass
        except Exception:
            _LOGGER.debug("OpenRemote batch post failed")
