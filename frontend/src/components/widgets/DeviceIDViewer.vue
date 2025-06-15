<template>
    <div :id="getDivName()"
         v-bind:style='{width:  width + "px", height: height + "px", top: top + "px", left: left + "px" }'>
        <div id='paneContent'>
            <span style="float: right; margin: 3px; cursor: pointer;" @click="close()"> X </span>
            <ul>
                <li v-bind:key="device.param" v-for="device in this.devices">
                    {{device.param}}:
                    <span style="float: right;">
                        {{device.deviceName}}({{device.address | toHex}}) @ {{device.busType}}({{device.bus}})
                    </span>
                </li>
            </ul>
        </div>
    </div>
</template>

<script>
import { store } from '../Globals.js'
import { baseWidget } from './baseWidget'

const busTypes = {
    1: 'I2C',
    2: 'SPI',
    3: 'UAVCAN',
    4: 'SITL',
    5: 'MSP',
    6: 'EAHRS'
}

const compassTypes = {
    0x01: 'HMC5883_OLD',
    0x07: 'HMC5883',
    0x02: 'LSM303D',
    0x04: 'AK8963 ',
    0x05: 'BMM150 ',
    0x06: 'LSM9DS1',
    0x08: 'LIS3MDL',
    0x09: 'AK09916',
    0x0A: 'IST8310',
    0x0B: 'ICM20948',
    0x0C: 'MMC3416',
    0x0D: 'QMC5883L',
    0x0E: 'MAG3110',
    0x0F: 'SITL',
    0x10: 'IST8308',
    0x11: 'RM3100',
    0x12: 'RM3100_2',
    0x13: 'MMC5883',
    0x14: 'AK09918',
    0x15: 'AK09915'
}

const imuTypes = {
    0x09: 'BMI160',
    0x10: 'L3G4200D',
    0x11: 'ACC_LSM303D',
    0x12: 'ACC_BMA180',
    0x13: 'ACC_MPU6000',
    0x16: 'ACC_MPU9250',
    0x17: 'ACC_IIS328DQ',
    0x18: 'ACC_LSM9DS1',
    0x21: 'GYR_MPU6000',
    0x22: 'GYR_L3GD20',
    0x24: 'GYR_MPU9250',
    0x25: 'GYR_I3G4250D',
    0x26: 'GYR_LSM9DS1',
    0x27: 'INS_ICM20789',
    0x28: 'INS_ICM20689',
    0x29: 'INS_BMI055',
    0x2A: 'SITL',
    0x2B: 'INS_BMI088',
    0x2C: 'INS_ICM20948',
    0x2D: 'INS_ICM20648',
    0x2E: 'INS_ICM20649',
    0x2F: 'INS_ICM20602',
    0x30: 'INS_ICM20601',
    0x31: 'INS_ADIS1647x',
    0x32: 'INS_SERIAL',
    0x33: 'INS_ICM40609',
    0x34: 'INS_ICM42688',
    0x35: 'INS_ICM42605'
}

const baroTypes = {
    0x01: 'BARO_SITL',
    0x02: 'BARO_BMP085',
    0x03: 'BARO_BMP280',
    0x04: 'BARO_BMP388',
    0x05: 'BARO_DPS280',
    0x06: 'BARO_DPS310',
    0x07: 'BARO_FBM320',
    0x08: 'BARO_ICM20789',
    0x09: 'BARO_KELLERLD',
    0x0A: 'BARO_LPS2XH',
    0x0B: 'BARO_MS5611',
    0x0C: 'BARO_SPL06',
    0x0D: 'BARO_UAVCAN'
}

const airspeedTypes = {
    0x01: 'AIRSPEED_SITL',
    0x02: 'AIRSPEED_MS4525',
    0x03: 'AIRSPEED_MS5525',
    0x04: 'AIRSPEED_DLVR',
    0x05: 'AIRSPEED_MSP',
    0x06: 'AIRSPEED_SDP3X',
    0x07: 'AIRSPEED_UAVCAN',
    0x08: 'AIRSPEED_ANALOG',
    0x09: 'AIRSPEED_NMEA',
    0x0A: 'AIRSPEED_ASP5033'
}

export default {
    name: 'DeviceIDViewer',
    mixins: [baseWidget],
    data () {
        return {
            name: 'DeviceIDViewer',
            state: store,
            width: 300,
            height: 215,
            left: 768,
            top: 0,
            forceRecompute: 0,
            cursorTime: 0,
            devices: []
        }
    },
    methods: {
        update () {
            this.devices = []
            const devids = Object.keys(this.state.params.values).filter(
                param => (param.indexOf('DEVID') !== -1) ||
                param.indexOf('DEV_ID') !== -1 ||
                param.indexOf('_ID') !== -1
            )
            console.log(devids)
            devids.forEach(device => this.decode(device))
        },
        decode (device) {
            const devid = this.state.params.values[device]
            if (devid === 0) {
                return
            }
            const busType = busTypes[devid & 0x07]
            const bus = (devid >> 3) & 0x1F
            const address = (devid >> 8) & 0xFF
            const devtype = (devid >> 16)

            let decodedDevname

            if (device.startsWith('COMPASS')) {
                if (busType === 3 && devtype === 1) {
                    decodedDevname = 'UAVCAN'
                } else if (busType === 6 && devtype === 1) {
                    decodedDevname = 'EAHRS'
                } else {
                    decodedDevname = compassTypes[devtype] || 'UNKNOWN'
                }
            }
            if (device.startsWith('INS')) {
                decodedDevname = imuTypes[devtype] || 'UNKNOWN'
            }
            if (device.startsWith('GND_BARO')) {
                decodedDevname = baroTypes[devtype] || 'UNKNOWN'
            }
            if (device.startsWith('BARO')) {
                decodedDevname = baroTypes[devtype] || 'UNKNOWN'
            }
            if (device.startsWith('ARSP')) {
                decodedDevname = airspeedTypes[devtype] || 'UNKNOWN'
            }
            this.devices.push({
                param: device,
                deviceName: decodedDevname,
                busType: busType,
                bus: bus,
                address: address,
                devtype: devtype
            })
            console.log(`${device}: ${decodedDevname}, ${busType}(${bus}), ${address}, ${devtype}`)
        },
        setup () {
            this.update()
        }
    },

    computed: {
        filteredData () {
            // this seems necessary to force a recomputation
            // eslint-disable-next-line
            let potato = this.forceRecompute
            return this.state.textMessages.filter(key => (key[0] < this.cursorTime))
        }
    },
    filters: {
        toHex: function (value) {
            let hex = Number(value).toString(16)
            if (hex.length < 2) {
                hex = '0' + hex
            }
            return '0x' + hex
        }
    }
}
</script>

<style scoped>
    div #paneDeviceIDViewer {
        min-width: 220px;
        min-height: 150px;
        position: absolute;
        background: rgba(253, 254, 255, 0.856);
        color: #141924;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        z-index: 10000;
        box-shadow: 9px 9px 3px -6px rgba(26, 26, 26, 0.699);
        border-radius: 5px;
        user-select: none;
    }

    div #paneDeviceIDViewer::before {
        content: '\25e2';
        color: #ffffff;
        background-color: rgb(38, 53, 71);
        position: absolute;
        bottom: -1px;
        right: 0;
        width: 17px;
        height: 21px;
        padding: 2px 3px;
        border-radius: 10px 0px 1px 0px;
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        cursor: se-resize;
    }

     div #paneDeviceIDViewer::after {
        content: '\2725';
        color: #2E3F54;
        position: absolute;
        top: 0;
        left: 0;
        width: 18px;
        height: 17px;
        margin-top: -3px;
        padding: 0px 2px;
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        font-size: 17px;
         cursor: grab;
    }

    div#paneContent {
        height: 100%;
        overflow: auto;
        -webkit-user-select: none; /* Chrome all / Safari all */
        -moz-user-select: none; /* Firefox all */
        -ms-user-select: none; /* IE 10+ */
        user-select: none;
    }

    div#paneContent ul {
        list-style: none;
        line-height: 22px;
        padding: 16px;
        margin: 0;
    }

</style>
