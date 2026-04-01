#!/bin/sh
# Substitute environment variables in the config template before starting go2rtc.
# GO2RTC_HOST must be set to the server's public IP so WebRTC ICE candidates
# point to a reachable address (the Docker internal IP is not browser-accessible).
envsubst '${GO2RTC_HOST}' < /config/go2rtc.yaml.template > /config/go2rtc.yaml
exec go2rtc "$@"
