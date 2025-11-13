"""Helper for OpenRemote API interactions."""

import aiohttp
import logging
from .const import *

_LOGGER = logging.getLogger(__name__)

class OpenRemoteClient:
    """OpenRemote API wrapper."""

    def __init__(self, hass, cfg, pi_id):
        self.hass = hass
        self.cfg = cfg
        self.pi_id = pi_id
        self.token = None
        self.agent_id = None
        self.child_id = None
        self.child_attr = None

    async def setup(self):
        url = self.cfg.get(CONF_OR_URL)
        realm = self.cfg.get(CONF_OR_REALM, DEFAULT_OR_REALM)

        async with aiohttp.ClientSession() as session:
            # Authenticate
            self.token = await self._get_token(session, url, realm)
            if not self.token:
                _LOGGER.warning("OpenRemote authentication failed")
                return

            # Ensure MQTTAgent
            self.agent_id = await self._ensure_agent(session, url)
            if self.agent_id:
                child = await self._create_child(session, url)
                if child:
                    self.child_id = child["child_id"]
                    self.child_attr = child["attribute"]

    async def _get_token(self, session, base_url, realm):
        from urllib.parse import urljoin
        # client_credentials first
        client_id = self.cfg.get(CONF_OR_CLIENT_ID)
        client_secret = self.cfg.get(CONF_OR_CLIENT_SECRET)
        if client_id and client_secret:
            data = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            }
            token_url = urljoin(base_url, f"/auth/realms/{realm}/protocol/openid-connect/token")
            try:
                async with session.post(token_url, data=data, timeout=10) as resp:
                    if resp.status == 200:
                        r = await resp.json()
                        return r.get("access_token")
            except Exception as e:
                _LOGGER.warning("Client credentials token error: %s", e)
        # password grant
        username = self.cfg.get(CONF_OR_USER)
        password = self.cfg.get(CONF_OR_PASS)
        if username and password:
            data = {
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": username,
                "password": password
            }
            token_url = urljoin(base_url, f"/auth/realms/{realm}/protocol/openid-connect/token")
            try:
                async with session.post(token_url, data=data, timeout=10) as resp:
                    if resp.status == 200:
                        r = await resp.json()
                        return r.get("access_token")
            except Exception as e:
                _LOGGER.warning("Password grant token error: %s", e)
        return None

    async def _ensure_agent(self, session, base_url):
        name = f"wizsmith-pi-{self.pi_id}"
        # Query or create asset
        query_url = f"{base_url.rstrip('/')}/api/master/asset/query"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {"names": [name]}
        try:
            async with session.post(query_url, json=payload, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    if isinstance(res, dict) and res.get("items"):
                        return res["items"][0].get("id")
        except Exception:
            pass
        # fallback: create
        create_url = f"{base_url.rstrip('/')}/api/master/asset"
        payload = {
            "name": name,
            "description": "WizSmith auto-provisioned MQTTAgent for Pi",
            "configuration": {"host": self.cfg.get(CONF_MQTT_HOST), "port": self.cfg.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT)}
        }
        try:
            async with session.post(create_url, json=payload, headers=headers, timeout=10) as resp:
                if resp.status in (200, 201):
                    r = await resp.json()
                    return r.get("id")
        except Exception as e:
            _LOGGER.warning("Create agent failed: %s", e)
        return None

    async def _create_child(self, session, base_url):
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        child_payload = {"name": "HA Sensors", "parent": {"id": self.agent_id}}
        create_url = f"{base_url.rstrip('/')}/api/master/asset"
        try:
            async with session.post(create_url, json=child_payload, headers=headers, timeout=10) as resp:
                if resp.status in (200, 201):
                    res = await resp.json()
                    child_id = res.get("id")
                    attr_payload = {"name": "sensors_json", "type": "json", "writeable": True, "readable": True}
                    attr_url = f"{base_url.rstrip('/')}/api/master/asset/{child_id}/attribute"
                    async with session.post(attr_url, json=attr_payload, headers=headers, timeout=10):
                        return {"child_id": child_id, "attribute": "sensors_json"}
        except Exception as e:
            _LOGGER.warning("Create child/attribute failed: %s", e)
        return None
