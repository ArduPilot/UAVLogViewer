#!/usr/bin/env bash
# update this file to trigger cache updates
if [ ! -d "/tmp/testlogs" ]; then
    echo "log files not found, downloading..."
    mkdir /tmp/testlogs
    # wget http://autotest.ardupilot.org/HeliCopter-test.tlog --directory-prefix=/tmp/testlogs/

    wget https://autotest.ardupilot.org/Rover-test.tlog --directory-prefix=/tmp/testlogs/

    truncate --size=10M /tmp/testlogs/*.tlog
    wget https://autotest.ardupilot.org/ArduCopter-Replay-00000200.BIN --directory-prefix=/tmp/testlogs/
   truncate --size=10M /tmp/testlogs/*.bin
fi
