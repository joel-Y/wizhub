"""Sensor publisher."""

import json
import logging
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt
from .const import *

_LOGGER = logging.getLogger(__name__)

async def publish_sensors(hass: HomeAssistant, or_client):
    """Publish all sensor and binary_sensor states to MQTT and OpenRemote."""
    states = hass.states.async_all()
    batch = {}
    
    for s in states:
        if s.entity_id.startswith(("sensor.", "binary_sensor.")):
            topic = f"wizsmith/{or_client.pi_id}/{s.domain}/{s.object_id}/state"
            payload = {
                "entity_id": s.entity_id,
                "state": s.state,
                "attributes": dict(s.attributes),
                "last_changed": str(s.last_changed),
            }
            
            try:
                # Use Home Assistant's built-in MQTT publish
                await mqtt.async_publish(
                    hass, 
                    topic, 
                    json.dumps(payload), 
                    qos=1, 
                    retain=False
                )
            except Exception as e:
                _LOGGER.debug("MQTT publish failed for %s: %s", topic, e)
            
            batch[topic] = payload

    # Send batch to OpenRemote if authenticated
    if (getattr(or_client, 'token', None) and 
        getattr(or_client, 'child_id', None) and 
        getattr(or_client, 'child_attr', None)):
        try:
            or_url = or_client.cfg.get(CONF_OR_URL, "").rstrip("/")
            attr_url = f"{or_url}/api/master/asset/{or_client.child_id}/attribute/{or_client.child_attr}"
            headers = {
                "Authorization": f"Bearer {or_client.token}", 
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    attr_url, 
                    json=batch, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.debug("OpenRemote batch post returned status %s", resp.status)
        except Exception as e:
            _LOGGER.debug("OpenRemote batch post failed: %s", e)