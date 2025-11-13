"""Constants for the WizSmith Home Integration."""

DOMAIN = "wizsmith-home-assistant"

# Default values
DEFAULT_SYNC_INTERVAL = 30
DEFAULT_MQTT_PORT = 1883
DEFAULT_OR_REALM = "master"
DEFAULT_GITHUB_REPO = "joel-Y/wizhub"

# MQTT configuration keys
CONF_MQTT_HOST = "mqtt_host"
CONF_MQTT_PORT = "mqtt_port"
CONF_MQTT_USER = "mqtt_user"
CONF_MQTT_PASS = "mqtt_pass"

# OpenRemote configuration keys
CONF_OR_URL = "openremote_url"
CONF_OR_USER = "openremote_user"
CONF_OR_PASS = "openremote_pass"
CONF_OR_CLIENT_ID = "openremote_client_id"
CONF_OR_CLIENT_SECRET = "openremote_client_secret"
CONF_OR_REALM = "openremote_realm"

# GitHub repo for self-update
CONF_GITHUB_REPO = "github_repo"

# Sync interval
CONF_SYNC_INTERVAL = "sync_interval"

# MQTT topics
TOPIC_DISCOVERY = "wizsmith/discovery"
TOPIC_STATUS = "wizsmith/status"
TOPIC_EVENTS = "wizsmith/events"
