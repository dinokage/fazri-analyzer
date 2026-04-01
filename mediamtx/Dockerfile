FROM alexxit/go2rtc:latest
# gettext provides envsubst for substituting GO2RTC_HOST into the config
RUN apk add --no-cache gettext
COPY mediamtx.yml /config/go2rtc.yaml.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 1984 8554 8555
ENTRYPOINT ["/entrypoint.sh"]
