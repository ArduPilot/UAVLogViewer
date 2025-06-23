#!/usr/bin/env bash
# update this file to trigger cache updates
if [ ! -d "test/testlogfiles/logs" ]; then
    echo "log files not found, downloading..."
    mkdir -p test/testlogfiles/logs
    # wget http://autotest.ardupilot.org/HeliCopter-test.tlog --directory-prefix=test/testlogfiles/logs/

    wget https://autotest.ardupilot.org/ArduPlane-PIDTuning-autotest-1627978628940194.tlog --directory-prefix=test/testlogfiles/logs/
    wget http://autotest.ardupilot.org/ArduSub-test.tlog --directory-prefix=test/testlogfiles/logs/

    truncate --size=10M test/testlogfiles/logs/*.tlog
    wget http://autotest.ardupilot.org/ArduSub-log.bin --directory-prefix=test/testlogfiles/logs/
    wget https://autotest.ardupilot.org/Rover-log.bin --directory-prefix=test/testlogfiles/logs/
    wget https://autotest.ardupilot.org/ArduPlane-Deadreckoning-00000049.BIN --directory-prefix=test/testlogfiles/logs/
    truncate --size=10M test/testlogfiles/logs/*.bin
fi
