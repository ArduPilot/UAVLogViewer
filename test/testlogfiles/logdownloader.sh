#!/usr/bin/env bash
wget http://autotest.ardupilot.org/HeliCopter-test.tlog
wget http://autotest.ardupilot.org/ArduPlane-test.tlog
wget http://autotest.ardupilot.org/APMrover2-test.tlog
wget http://autotest.ardupilot.org/ArduSub-test.tlog
wget http://autotest.ardupilot.org/QuadPlane-test.tlog
wget http://autotest.ardupilot.org/BalanceBot-test.tlog
wget http://autotest.ardupilot.org/AntennaTracker-test.tlog
wget http://autotest.ardupilot.org/ArduCopter-test.tlog
truncate --size=1M *.tlog
wget http://autotest.ardupilot.org/ArduSub-log.bin
wget http://autotest.ardupilot.org/ArduCopter-log.bin
wget http://autotest.ardupilot.org/APMrover2-log.bin
wget http://autotest.ardupilot.org/ArduPlane-log.bin
truncate --size=1M *.bin
