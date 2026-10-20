<template>
    <div
        :id="getDivName()"
        class="uav-widget"
        :style="{
            width: width + 'px',
            height: height + 'px',
            top: top + 'px',
            left: left + 'px',
        }"
    >
        <span class="uav-widget__move"></span>
        <span class="uav-widget__resize"></span>
        <span class="uav-widget__close" @click="close()"></span>
        <div class="uav-widget__content">
            <ul>
                <li v-for="device in devices" :key="device.param">
                    {{ device.param }}:
                    <span class="uav-widget__value">
                        {{ device.deviceName }}({{ toHex(device.address) }}) @
                        {{ device.busType }}({{ device.bus }})
                    </span>
                </li>
            </ul>
        </div>
    </div>
</template>

<script>
import { store } from "../Globals.js";
import { useWidget, widgetProps } from "./useWidget.js";

const busTypes = {
    1: "I2C",
    2: "SPI",
    3: "UAVCAN",
    4: "SITL",
    5: "MSP",
    6: "EAHRS",
};

const compassTypes = {
    0x01: "HMC5883_OLD",
    0x07: "HMC5883",
    0x02: "LSM303D",
    0x04: "AK8963 ",
    0x05: "BMM150 ",
    0x06: "LSM9DS1",
    0x08: "LIS3MDL",
    0x09: "AK09916",
    0x0a: "IST8310",
    0x0b: "ICM20948",
    0x0c: "MMC3416",
    0x0d: "QMC5883L",
    0x0e: "MAG3110",
    0x0f: "SITL",
    0x10: "IST8308",
    0x11: "RM3100",
    0x12: "RM3100_2",
    0x13: "MMC5883",
    0x14: "AK09918",
    0x15: "AK09915",
};

const imuTypes = {
    0x09: "BMI160",
    0x10: "L3G4200D",
    0x11: "ACC_LSM303D",
    0x12: "ACC_BMA180",
    0x13: "ACC_MPU6000",
    0x16: "ACC_MPU9250",
    0x17: "ACC_IIS328DQ",
    0x18: "ACC_LSM9DS1",
    0x21: "GYR_MPU6000",
    0x22: "GYR_L3GD20",
    0x24: "GYR_MPU9250",
    0x25: "GYR_I3G4250D",
    0x26: "GYR_LSM9DS1",
    0x27: "INS_ICM20789",
    0x28: "INS_ICM20689",
    0x29: "INS_BMI055",
    0x2a: "SITL",
    0x2b: "INS_BMI088",
    0x2c: "INS_ICM20948",
    0x2d: "INS_ICM20648",
    0x2e: "INS_ICM20649",
    0x2f: "INS_ICM20602",
    0x30: "INS_ICM20601",
    0x31: "INS_ADIS1647x",
    0x32: "INS_SERIAL",
    0x33: "INS_ICM40609",
    0x34: "INS_ICM42688",
    0x35: "INS_ICM42605",
};

const baroTypes = {
    0x01: "BARO_SITL",
    0x02: "BARO_BMP085",
    0x03: "BARO_BMP280",
    0x04: "BARO_BMP388",
    0x05: "BARO_DPS280",
    0x06: "BARO_DPS310",
    0x07: "BARO_FBM320",
    0x08: "BARO_ICM20789",
    0x09: "BARO_KELLERLD",
    0x0a: "BARO_LPS2XH",
    0x0b: "BARO_MS5611",
    0x0c: "BARO_SPL06",
    0x0d: "BARO_UAVCAN",
};

const airspeedTypes = {
    0x01: "AIRSPEED_SITL",
    0x02: "AIRSPEED_MS4525",
    0x03: "AIRSPEED_MS5525",
    0x04: "AIRSPEED_DLVR",
    0x05: "AIRSPEED_MSP",
    0x06: "AIRSPEED_SDP3X",
    0x07: "AIRSPEED_UAVCAN",
    0x08: "AIRSPEED_ANALOG",
    0x09: "AIRSPEED_NMEA",
    0x0a: "AIRSPEED_ASP5033",
};

export default {
    name: "DeviceIDViewer",
    props: widgetProps,
    emits: ["close"],
    setup(props, { emit }) {
        return useWidget(props, emit, {
            name: "DeviceIDViewer",
            width: 300,
            height: 215,
            left: 768,
            top: 0,
        });
    },
    data() {
        return {
            state: store,
            cursorTime: 0,
            devices: [],
        };
    },

    computed: {
        filteredData() {
            // this seems necessary to force a recomputation
            this.dependOnParams();
            return this.state.textMessages.filter(
                (key) => key[0] < this.cursorTime,
            );
        },
    },
    mounted() {
        this.init();
    },
    methods: {
        toHex(value) {
            let hex = Number(value).toString(16);
            if (hex.length < 2) {
                hex = "0" + hex;
            }
            return "0x" + hex;
        },
        update() {
            this.devices = [];
            const devids = Object.keys(this.state.params?.values ?? {}).filter(
                (param) =>
                    param.includes("DEVID") ||
                    param.includes("DEV_ID") ||
                    param.includes("_ID"),
            );
            console.log(devids);
            devids.forEach((device) => this.decode(device));
        },
        decode(device) {
            const devid = this.state.params.values[device];
            if (devid === 0) {
                return;
            }
            const busType = busTypes[devid & 0x07];
            const bus = (devid >> 3) & 0x1f;
            const address = (devid >> 8) & 0xff;
            const devtype = devid >> 16;

            let decodedDevname;

            if (device.startsWith("COMPASS")) {
                if (busType === 3 && devtype === 1) {
                    decodedDevname = "UAVCAN";
                } else if (busType === 6 && devtype === 1) {
                    decodedDevname = "EAHRS";
                } else {
                    decodedDevname = compassTypes[devtype] || "UNKNOWN";
                }
            }
            if (device.startsWith("INS")) {
                decodedDevname = imuTypes[devtype] || "UNKNOWN";
            }
            if (device.startsWith("GND_BARO")) {
                decodedDevname = baroTypes[devtype] || "UNKNOWN";
            }
            if (device.startsWith("BARO")) {
                decodedDevname = baroTypes[devtype] || "UNKNOWN";
            }
            if (device.startsWith("ARSP")) {
                decodedDevname = airspeedTypes[devtype] || "UNKNOWN";
            }
            this.devices.push({
                param: device,
                deviceName: decodedDevname,
                busType,
                bus,
                address,
                devtype,
            });
            console.log(
                `${device}: ${decodedDevname}, ${busType}(${bus}), ${address}, ${devtype}`,
            );
        },
        init() {
            this.update();
        },
    },
};
</script>

<style scoped>
/* Nothing widget-specific yet — all shell rules live in src/styles/widget.css */
</style>
