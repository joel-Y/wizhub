#!/usr/bin/with-contenv bash
set -euo pipefail

# Populate env vars from add-on options (bashio available in HA add-on build)
if [ -f /usr/bin/bashio ]; then
  MQTT_HOST=$(bashio::config 'mqtt_host')
  MQTT_PORT=$(bashio::config 'mqtt_port')
  MQTT_USER=$(bashio::config 'mqtt_user')
  MQTT_PASS=$(bashio::config 'mqtt_pass')
  OPENREMOTE_URL=$(bashio::config 'openremote_url')
  OPENREMOTE_USER=$(bashio::config 'openremote_user')
  OPENREMOTE_PASS=$(bashio::config 'openremote_pass')
  SYNC_INTERVAL=$(bashio::config 'sync_interval')
  export MQTT_HOST MQTT_PORT MQTT_USER MQTT_PASS OPENREMOTE_URL OPENREMOTE_USER OPENREMOTE_PASS SYNC_INTERVAL
fi

exec python3 /app/main.py
