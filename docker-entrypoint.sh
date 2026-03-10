#!/bin/sh
set -eu

node /usr/src/app/scripts/generate-runtime-config.js

exec "$@"
