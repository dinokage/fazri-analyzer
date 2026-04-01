#!/bin/sh
# Substitute environment variables in the config template before starting go2rtc.
# GO2RTC_HOST must be set to the server's public IP so WebRTC ICE candidates
# point to a reachable address (the Docker internal IP is not browser-accessible).
if [ -z "$GO2RTC_HOST" ]; then
  echo "ERROR: GO2RTC_HOST is not set or empty. Cannot generate valid ICE candidates." >&2
  exit 1
fi
envsubst '${GO2RTC_HOST}' < /config/go2rtc.yaml.template > /config/go2rtc.yaml
exec go2rtc "$@"
