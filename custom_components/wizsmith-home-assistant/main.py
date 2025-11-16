# main.py - WizSmith Home Integration Add-on agent
import os
import time
import json
import logging
import signal
import requests
import threading
import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger("wizsmith_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Read config from environment (set in run.sh from add-on options)
MQTT_HOST = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")

OPENREMOTE_URL = os.getenv("OPENREMOTE_URL", "")  # e.g. http://74.208.69.198:8080
OPENREMOTE_USER = os.getenv("OPENREMOTE_USER", "")
OPENREMOTE_PASS = os.getenv("OPENREMOTE_PASS", "")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "30"))

CLIENT_ID = f"wizsmith-addon-{int(time.time())}"

# Simple in-memory fake device list (replace with discovery from HA core if desired)
DEVICES = [
    {"id": "rpi_power_status", "name": "RPi Power status", "domain": "binary_sensor", "device_class": "problem"},
    # Add other static devices here or dynamically build from HA state if you prefer
]

# OpenRemote token helper (basic username/password -> token for manager API)
def get_openremote_token():
    if not OPENREMOTE_URL or not OPENREMOTE_USER or not OPENREMOTE_PASS:
        _LOGGER.debug("OpenRemote credentials missing; skipping token fetch")
        return None
    try:
        login_url = f"{OPENREMOTE_URL}/auth/realms/master/protocol/openid-connect/token"
        data = {"grant_type": "password", "username": OPENREMOTE_USER, "password": OPENREMOTE_PASS, "client_id": "admin-cli"}
        resp = requests.post(login_url, data=data, timeout=10)
        resp.raise_for_status()
        token = resp.json().get("access_token")
        _LOGGER.info("Obtained OpenRemote token")
        return token
    except Exception as e:
        _LOGGER.exception("Failed to obtain OpenRemote token: %s", e)
        return None

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        _LOGGER.info("Connected to MQTT broker %s:%s (client_id=%s)", MQTT_HOST, MQTT_PORT, CLIENT_ID)
        # subscribe to commands from OpenRemote or other control channels
        client.subscribe("wizsmith/commands/#", qos=0)
    else:
        _LOGGER.error("MQTT connection failed with rc=%s", rc)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
    except Exception:
        payload = str(msg.payload)
    _LOGGER.info("MQTT message received: %s -> %s", msg.topic, payload)
    # Forward commands to OpenRemote REST API (simple mapping)
    if msg.topic.startswith("wizsmith/commands/"):
        # Example: wizsmith/commands/<device_id>/<action>
        parts = msg.topic.split("/")
        if len(parts) >= 3:
            device_id = parts[2]
            action_path = "/".join(parts[3:]) if len(parts) > 3 else ""
            forward_command_to_openremote(device_id, action_path, payload)

def safe_publish(mqtt_client, topic, payload, qos=0, retain=False):
    try:
        mqtt_client.publish(topic, payload, qos=qos, retain=retain)
        _LOGGER.debug("Published %s -> %s", topic, payload if len(str(payload)) < 200 else "<long>")
    except Exception as e:
        _LOGGER.exception("Publish failed for %s: %s", topic, e)

# Forward a command to OpenRemote manager (example implementation)
def forward_command_to_openremote(device_id, action_path, payload):
    token = get_openremote_token()
    if not token:
        _LOGGER.warning("No token to forward command for %s", device_id)
        return
    url = f"{OPENREMOTE_URL}/api/master/asset/attribute/update"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "device_id": device_id,
        "action": action_path,
        "payload": payload
    }
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        if resp.status_code >= 300:
            _LOGGER.error("OpenRemote command failed %s: %s", resp.status_code, resp.text)
        else:
            _LOGGER.info("OpenRemote command forwarded for %s", device_id)
    except Exception as e:
        _LOGGER.exception("Forward to OpenRemote failed: %s", e)

# Publish HA-style discovery messages for simple sensors
def publish_discovery_messages(mqtt_client):
    for d in DEVICES:
        topic = f"homeassistant/{d['domain']}/{d['id']}/config"
        payload = {
            "name": d["name"],
            "uniq_id": d["id"],
            "state_topic": f"wizsmith/{d['id']}/state",
            "qos": 0
        }
        if "device_class" in d:
            payload["device_class"] = d["device_class"]
        safe_publish(mqtt_client, topic, json.dumps(payload), qos=0, retain=True)
        _LOGGER.info("Published discovery for %s", d["id"])

# Publish periodic states (replace fetches with real sensor reads)
def publish_states_loop(mqtt_client, stop_event):
    while not stop_event.is_set():
        try:
            # Normally query Home Assistant via REST or listen to entity updates; for now publish sample states
            for d in DEVICES:
                st_topic = f"wizsmith/{d['id']}/state"
                # sample placeholder states
                if d["domain"] == "binary_sensor":
                    state_val = "OFF"
                else:
                    state_val = "unknown"
                payload = state_val
                safe_publish(mqtt_client, st_topic, payload, qos=0, retain=False)
            time.sleep(SYNC_INTERVAL)
        except Exception as e:
            _LOGGER.exception("State publish loop error: %s", e)
            time.sleep(5)

def main():
    client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    _LOGGER.info("Connecting to MQTT broker %s:%s", MQTT_HOST, MQTT_PORT)
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
    except Exception as e:
        _LOGGER.exception("Failed to connect to MQTT broker: %s", e)
        return

    stop_event = threading.Event()
    state_thread = threading.Thread(target=publish_states_loop, args=(client, stop_event), daemon=True)

    try:
        client.loop_start()
        publish_discovery_messages(client)
        state_thread.start()
        # Run until killed
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _LOGGER.info("Stopping (KeyboardInterrupt)")
    finally:
        stop_event.set()
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
