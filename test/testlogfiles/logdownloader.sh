#!/usr/bin/env bash
# Download ArduPilot autotest logs for the parser unit tests into $TEST_LOG_DIR
# (default /tmp/testlogs, which the specs also read). Autotest .BIN names change
# between runs, so they are picked from the server's index. Only the first 10 MB
# of each log is downloaded.
# update this file to trigger cache updates
set -euo pipefail

dest="${TEST_LOG_DIR:-/tmp/testlogs}"
base="https://autotest.ardupilot.org"

if compgen -G "$dest/*.tlog" >/dev/null && compgen -G "$dest/*.[bB][iI][nN]" >/dev/null; then
    echo "test logs already in $dest"
    exit 0
fi
mkdir -p "$dest"

fetch() {
    echo "downloading $1"
    curl -fsSL --range 0-10485759 -o "$dest/$1" "$base/$1"
}

index="$(curl -fsSL "$base/")"
# first log matching the pattern that is at least 2 MB (short runs don't have enough data)
pick() {
    local name size
    while read -r name; do
        size="$(curl -fsSI "$base/$name" | tr -d '\r' | awk 'tolower($1) == "content-length:" { print $2 }')"
        if [ "${size:-0}" -ge 2000000 ]; then
            echo "$name"
            return
        fi
    done < <(grep -oE "href=\"$1\"" <<<"$index" | sed -e 's/^href="//' -e 's/"$//')
}

fetch ArduCopter-test.tlog
bin="$(pick 'ArduCopter-DefaultIntervalsFromFiles-[0-9]+\.BIN')"
if [ -z "$bin" ]; then
    echo "no ArduCopter DefaultIntervalsFromFiles .BIN log of 2 MB or more on $base" >&2
    exit 1
fi
fetch "$bin"
