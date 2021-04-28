#!/usr/bin/env bash
if [ ! -d "/tmp/testlogs" ]; then
    echo "log files not found, downloading..."
    mkdir /tmp/testlogs
    wget http://autotest.ardupilot.org/HeliCopter-test.tlog --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/Soaring-test.tlog --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/APMrover2-test.tlog --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/ArduSub-test.tlog --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/QuadPlane-test.tlog --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/BalanceBot-test.tlog --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/AntennaTracker-test.tlog --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/ArduCopter-test.tlog --directory-prefix=/tmp/testlogs/
    truncate --size=10M /tmp/testlogs/*.tlog
    wget http://autotest.ardupilot.org/ArduSub-log.bin --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/ArduCopter-log.bin --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/APMrover2-log.bin --directory-prefix=/tmp/testlogs/
    wget http://autotest.ardupilot.org/ArduPlane-log.bin --directory-prefix=/tmp/testlogs/
    truncate --size=10M /tmp/testlogs/*.bin
fi
