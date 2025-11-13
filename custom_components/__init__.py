"""WizSmith Home Integration - zero-touch OpenRemote registration + MQTT publishing."""

from __future__ import annotations
import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

import aiohttp
import paho.mqtt.client as mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import *

_LOGGER = logging.getLogger(__name__)

def _load_config(entry: ConfigEntry) -> Dict[str, Any]:
    cfg = {}
    if entry and entry.data:
        cfg.update(entry.data)

    options_path = "/data/options.json"
    try:
        if os.path.exists(options_path):
            with open(options_path, "r") as f:
                opts = json.load(f)
                for k, v in opts.items():
                    if k not in cfg:
                        cfg[k] = v
    except Exception:
        _LOGGER.debug("No add-on options.json found or failed to read it")

    cfg.setdefault(CONF_MQTT_HOST, "core-mosquitto")
    cfg.setdefault(CONF_MQTT_PORT, DEFAULT_MQTT_PORT)
    cfg.setdefault(CONF_SYNC_INTERVAL, DEFAULT_SYNC_INTERVAL)
    cfg.setdefault(CONF_OR_REALM, DEFAULT_OR_REALM)

    return cfg

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    cfg = _load_config(entry)

    mqtt_host = cfg.get(CONF_MQTT_HOST)
    mqtt_port = int(cfg.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT))
    mqtt_user = cfg.get(CONF_MQTT_USER)
    mqtt_pass = cfg.get(CONF_MQTT_PASS)
    sync_interval = int(cfg.get(CONF_SYNC_INTERVAL, DEFAULT_SYNC_INTERVAL))
    openremote_url = cfg.get(CONF_OR_URL)
    realm = cfg.get(CONF_OR_REALM)
    github_repo = cfg.get(CONF_GITHUB_REPO, DEFAULT_GITHUB_REPO)

    # persistent pi_id
    pi_id_path = "/config/wizsmith_home_integration_pi_id"
    if "pi_id" in hass.data:
        pi_id = hass.data["pi_id"]
    else:
        try:
            if os.path.exists(pi_id_path):
                with open(pi_id_path, "r") as f:
                    pi_id = f.read().strip()
            else:
                pi_id = str(uuid.uuid4())
                with open(pi_id_path, "w") as f:
                    f.write(pi_id)
        except Exception:
            _LOGGER.exception("Could not read/write pi_id file; generating ephemeral id")
            pi_id = str(uuid.uuid4())
        hass.data["pi_id"] = pi_id

    _LOGGER.info("WizSmith integration starting for pi_id=%s", pi_id)

    # Setup MQTT client
    client = mqtt.Client(client_id=f"WizSmithHA-{pi_id}")
    if mqtt_user and mqtt_pass:
        client.username_pw_set(mqtt_user, mqtt_pass)
    try:
        client.connect(mqtt_host, mqtt_port, keepalive=60)
        client.loop_start()
        _LOGGER.info("Connected to MQTT broker %s:%s", mqtt_host, mqtt_port)
    except Exception as e:
        _LOGGER.error("Failed to connect to MQTT broker %s:%s - %s", mqtt_host, mqtt_port, e)
        return False

    # OpenRemote auth + ensure assets
    from .openremote_client import OpenRemoteClient
    or_client = OpenRemoteClient(hass, cfg, pi_id)
    await or_client.setup()

    # Publish loop
    async def _publish_loop() -> None:
        while True:
            try:
                from .sensor import publish_sensors
                await publish_sensors(hass, client, or_client)
            except Exception as e:
                _LOGGER.exception("Error in publish loop: %s", e)
            await asyncio.sleep(sync_interval)

    hass.async_create_task(_publish_loop())

    # GitHub release checker
    async def _check_github_release():
        try:
            gh_api = f"https://api.github.com/repos/{github_repo}/releases/latest"
            async with aiohttp.ClientSession() as s:
                async with s.get(gh_api, timeout=10) as resp:
                    if resp.status == 200:
                        r = await resp.json()
                        latest_tag = r.get("tag_name")
                        curr_version = None
                        try:
                            import pathlib
                            manifest_path = pathlib.Path(__file__).parent / "manifest.json"
                            with open(manifest_path, "r") as mf:
                                m = json.load(mf)
                                curr_version = m.get("version")
                        except Exception:
                            pass
                        if latest_tag and curr_version and latest_tag != curr_version:
                            _LOGGER.info("New integration release available on GitHub: %s (current=%s)", latest_tag, curr_version)
        except Exception:
            _LOGGER.debug("GitHub release check failed")

    hass.async_create_task(_check_github_release())
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Unloading WizSmith Home Integration")
    return True
