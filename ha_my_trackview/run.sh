#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -e

export TRACKVIEW_LOG_LEVEL="$(bashio::config 'log_level' 'info')"
export TRACKVIEW_DATA="/data"
export TRACKVIEW_VERSION="$(bashio::app.version 2>/dev/null || echo 1.1.1)"

bashio::log.info "Starting My TrackView ${TRACKVIEW_VERSION} (log level ${TRACKVIEW_LOG_LEVEL})"
cd /app
exec python3 -u /app/main.py
