#!/usr/bin/env bash
# update this file to trigger cache updates
if [ ! -d "/tmp/testlogs" ]; then
    echo "log files not found, downloading..."
    mkdir /tmp/testlogs
    # wget http://autotest.ardupilot.org/HeliCopter-test.tlog --directory-prefix=/tmp/testlogs/

    wget https://autotest.ardupilot.org/ArduPlane-PIDTuning-autotest-1627978628940194.tlog --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/ArduSub-test.tlog --directory-prefix=/tmp/testlogs/

    truncate --size=10M /tmp/testlogs/*.tlog
    wget http://autotest.ardupilot.org/ArduSub-log.bin --directory-prefix=/tmp/testlogs/
    wget https://autotest.ardupilot.org/Rover-log.bin --directory-prefix=/tmp/testlogs/
    wget https://autotest.ardupilot.org/ArduPlane-Deadreckoning-00000049.BIN --directory-prefix=/tmp/testlogs/
    truncate --size=10M /tmp/testlogs/*.bin
fi
