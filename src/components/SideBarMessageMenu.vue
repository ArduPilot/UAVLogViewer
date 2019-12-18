<template>
    <div v-if="hasMessages">

        <!--<li v-if="state.plot_on" @click="state.plot_on=!state.plot_on">-->
        <!--<a class="section">-->
        <!--<i class="fas fa-eye-slash fa-lg"></i> Toggle Plot</a>-->
        <!--</li>-->
        <tree-menu
            v-if="Object.keys(availableMessagePresets).length > 0"
            :nodes="availableMessagePresets"
            :label="'Presets'"
            :level="0">

        </tree-menu>
        <li v-b-toggle="'messages'">
            <a class="section">
                Plot Individual Field
                <i class="fas fa-caret-down"></i></a>
        </li>

        <b-collapse id="messages">
            <li class="input-li">
                <input id="filterbox" placeholder=" Type here to filter..." v-model="filter">
            </li>
            <template v-for="(message, key) in messageTypesFiltered">
                <li class="type" v-bind:key="key">
                    <div v-b-toggle="'type' + key">
                        <a class="section">{{key}}
                            <i class="expand fas fa-caret-down"></i></a>
                    </div>
                </li>
                <b-collapse :id="'type' + key" v-bind:key="key+'1'">
                    <template v-for="item in message.complexFields">
                        <li @click="toggle(key, item.name)"
                            class="field"
                            v-bind:key="key+'.'+item.name"
                            v-if="isPlottable(key,item.name)
                                && item.name.toLowerCase().indexOf(filter.toLowerCase()) !== -1">
                            <a> {{item.name}}
                                <span v-if="item.units!=='?' && item.units!==''"> ({{item.units}})</span>
                            </a>

                            <a @click="$eventHub.$emit('togglePlot', field.name)" v-if="isPlotted(key,item.name)">
                                <i class="remove-icon fas fa-trash" title="Remove data"></i>
                            </a>
                        </li>
                    </template>
                </b-collapse>
            </template>
        </b-collapse>
    </div>
</template>
<script>
import {store} from './Globals.js'
import TreeMenu from './widgets/TreeMenu'

const degrees = function (a) {
    return a * 180 / Math.PI
}
export default {
    name: 'message-menu',
    components: {TreeMenu},
    data () {
        return {
            filter: '',
            checkboxes: {},
            state: store,
            messages: {},
            messageTypes: [],
            hiddenTypes: [
                'MISSION_CURRENT',
                'SYSTEM_TIME', 'HEARTBEAT', 'STATUSTEXT',
                'COMMAND_ACK', 'PARAM_VALUE', 'AUTOPILOT_VERSION',
                'TIMESYNC', 'MISSION_COUNT', 'MISSION_ITEM_INT',
                'MISSION_ITEM', 'MISSION_ITEM_REACHED', 'MISSION_ACK',
                'HOME_POSITION',
                'STRT',
                'ARM',
                'STAT',
                'FMT',
                'PARM',
                'MSG',
                'CMD',
                'MODE',
                'ORGN',
                'FMTU',
                'UNIT',
                'MULT'
            ],
            // TODO: lists are nor clear, use objects instead
            messagePresets: {
                'Speed/Ground vs Air Speed':
                    [
                        ['VFR_HUD.groundspeed', 0],
                        ['VFR_HUD.airspeed', 0]
                    ],
                'Speed/Ground vs Air Speed ':
                    [
                        ['GPS.Spd', 0],
                        ['ARSP.Airspeed', 0]
                    ],
                'Speed/Ground Speed':
                    [
                        ['VFR_HUD.groundspeed', 0]
                    ],
                'Speed/Ground Speed ':
                    [
                        ['GPS.Spd', 0]
                    ],
                'Attitude/Roll and Pitch':
                    [
                        ['ATTITUDE.roll', 0, undefined, function (a) { return degrees(a) }],
                        ['ATTITUDE.pitch', 0, undefined, function (a) { return degrees(a) }]
                    ],
                'Attitude/Roll and Pitch ':
                    [
                        ['ATT.Roll', 0],
                        ['ATT.Pitch', 0]
                    ],
                'Attitude/RP Comparison':
                    [
                        ['ATTITUDE.roll', 0, undefined, function (a) { return degrees(a) }],
                        ['ATTITUDE.pitch', 0, undefined, function (a) { return degrees(a) }],
                        ['AHRS2.roll', 0, undefined, function (a) { return degrees(a) }],
                        ['AHRS2.pitch', 0, undefined, function (a) { return degrees(a) }]
                    ],
                'Attitude/RP Comparison ':
                    [
                        ['ATT.Roll', 0],
                        ['ATT.Pitch', 0],
                        ['AHR2.Roll', 0],
                        ['AHR2.Pitch', 0]
                    ],
                'Attitude/Attitude Control':
                    [
                        ['NAV_CONTROLLER_OUTPUT.nav_roll', 0],
                        ['NAV_CONTROLLER_OUTPUT.nav_pitch', 0],
                        ['ATTITUDE.roll', 0, undefined, function (a) { return degrees(a) }],
                        ['ATTITUDE.pitch', 0, undefined, function (a) { return degrees(a) }]
                    ],
                'Attitude/Attitude Control ':
                    [
                        ['ATT.DesRoll', 0],
                        ['ATT.Roll', 0],
                        ['ATT.DesPitch', 0],
                        ['ATT.Pitch', 0]
                    ],
                'Attitude/Attitude Control  ':
                    [
                        ['CTUN.NavRoll', 0],
                        ['CTUN.Roll', 0],
                        ['CTUN.NavPitch', 0],
                        ['CTUN.Pitch', 0]
                    ],
                'Sensors/Accelerometer/Accelerometers':
                    [
                        ['RAW_IMU.xacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['RAW_IMU.yacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['RAW_IMU.zacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }]

                    ],
                'Sensors/Accelerometer/Accelerometers ':
                    [
                        ['IMU.AccX', 0],
                        ['IMU.AccY', 0],
                        ['IMU.AccZ', 0]

                    ],
                'Sensors/Accelerometer/Accelerometer(2)':
                    [
                        ['SCALED_IMU2.xacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU2.yacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU2.zacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }]
                    ],
                'Sensors/Accelerometer/Accelerometer(2) ':
                    [
                        ['IMU2.AccX', 0],
                        ['IMU2.AccY', 0],
                        ['IMU2.AccZ', 0]

                    ],
                'Sensors/Accelerometer/Accelerometer(3)':
                    [
                        ['SCALED_IMU3.xacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU3.yacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU3.zacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }]
                    ],
                'Sensors/Accelerometer/Accelerometer(3) ':
                    [
                        ['IMU3.AccX', 0],
                        ['IMU3.AccY', 0],
                        ['IMU3.AccZ', 0]

                    ],
                'Sensors/Accelerometer/Accelerometer Comparison':
                    [
                        ['RAW_IMU.xacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['RAW_IMU.yacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['RAW_IMU.zacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU2.xacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU2.yacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU2.zacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU3.xacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU3.yacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU3.zacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }]
                    ],
                'Sensors/Accelerometer/Accelerometer Comparison ':
                    [
                        ['RAW_IMU.xacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['RAW_IMU.yacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['RAW_IMU.zacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU2.xacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU2.yacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }],
                        ['SCALED_IMU2.zacc', 0, undefined, function (a) { return a * 9.81 * 0.001 }]
                    ],
                'Sensors/Accelerometer/Accelerometer Comparison  ':
                    [
                        ['IMU.AccX', 0],
                        ['IMU.AccY', 0],
                        ['IMU.AccZ', 0],
                        ['IMU2.AccX', 0],
                        ['IMU2.AccY', 0],
                        ['IMU2.AccZ', 0],
                        ['IMU3.AccX', 0],
                        ['IMU3.AccY', 0],
                        ['IMU3.AccZ', 0]
                    ],
                'Sensors/Accelerometer/Accelerometer Comparison   ':
                    [
                        ['IMU.AccX', 0],
                        ['IMU.AccY', 0],
                        ['IMU.AccZ', 0],
                        ['IMU2.AccX', 0],
                        ['IMU2.AccY', 0],
                        ['IMU2.AccZ', 0]
                    ],
                'Sensors/Gyroscope/Gyros':
                    [
                        ['RAW_IMU.xgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['RAW_IMU.ygyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['RAW_IMU.zgyro', 0, undefined, function (a) { return degrees(a * 0.001) }]
                    ],
                'Sensors/Gyroscope/Gyros ':
                    [
                        ['IMU.GyrX', 0],
                        ['IMU.GyrY', 0],
                        ['IMU.GyrZ', 0]
                    ],
                'Sensors/Gyroscope/Gyros(2)':
                    [
                        ['SCALED_IMU2.xgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU2.ygyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU2.zgyro', 0, undefined, function (a) { return degrees(a * 0.001) }]
                    ],
                'Sensors/Gyroscope/Gyros(2) ':
                    [
                        ['IMU2.GyrX', 0],
                        ['IMU2.GyrY', 0],
                        ['IMU2.GyrZ', 0]
                    ],
                'Sensors/Gyroscope/Gyros(3)':
                    [
                        ['SCALED_IMU3.xgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU3.ygyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU3.zgyro', 0, undefined, function (a) { return degrees(a * 0.001) }]
                    ],
                'Sensors/Gyroscope/Gyros(3) ':
                    [
                        ['IMU3.GyrX', 0],
                        ['IMU3.GyrY', 0],
                        ['IMU3.GyrZ', 0]
                    ],
                'Sensors/Gyroscope/Gyro Comparison':
                    [
                        ['RAW_IMU.xgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['RAW_IMU.ygyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['RAW_IMU.zgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU2.xgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU2.ygyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU2.zgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU3.xgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU3.ygyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU3.zgyro', 0, undefined, function (a) { return degrees(a * 0.001) }]
                    ],
                'Sensors/Gyroscope/Gyro Comparison ':
                    [
                        ['RAW_IMU.xgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['RAW_IMU.ygyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['RAW_IMU.zgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU2.xgyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU2.ygyro', 0, undefined, function (a) { return degrees(a * 0.001) }],
                        ['SCALED_IMU2.zgyro', 0, undefined, function (a) { return degrees(a * 0.001) }]
                    ],
                'Sensors/Gyroscope/Gyro Comparison  ':
                    [
                        ['IMU.GyrX', 0],
                        ['IMU.GyrY', 0],
                        ['IMU.GyrZ', 0],
                        ['IMU2.GyrX', 0],
                        ['IMU2.GyrY', 0],
                        ['IMU2.GyrZ', 0],
                        ['IMU3.GyrX', 0],
                        ['IMU3.GyrY', 0],
                        ['IMU3.GyrZ', 0]
                    ],
                'Sensors/Gyroscope/Gyro Comparison   ':
                    [
                        ['IMU.GyrX', 0],
                        ['IMU.GyrY', 0],
                        ['IMU.GyrZ', 0],
                        ['IMU2.GyrX', 0],
                        ['IMU2.GyrY', 0],
                        ['IMU2.GyrZ', 0]
                    ],
                'Sensors/Barometer/Barometer':
                    [

                        ['SCALED_PRESSURE.temperature', 0, undefined, function (a) { return a * 0.01 }]
                    ],
                'Sensors/Barometer/Barometer ':
                    [
                        ['BARO.Alt', 0],
                        ['BARO.Temp', 0]
                    ],
                'Sensors/Barometer/Barometer(2)':
                    [

                        ['SCALED_PRESSURE2.temperature', 0, undefined, function (a) { return a * 0.01 }]
                    ],
                'Sensors/Barometer/Barometer(2) ':
                    [
                        ['BAR2.Alt', 0],
                        ['BAR2.Temp', 0]
                    ],
                'Sensors/Barometer/Barometer(3)':
                    [

                        ['SCALED_PRESSURE3.temperature', 0, undefined, function (a) { return a * 0.01 }]
                    ],
                'Sensors/Barometer/Barometer(3) ':
                    [
                        ['BAR3.Alt', 0],
                        ['BAR3.Temp', 0]
                    ],
                'Sensors/Barometer/Barometer Comparison':
                    [

                        ['SCALED_PRESSURE.temperature', 0, undefined, function (a) { return a * 0.01 }],

                        ['SCALED_PRESSURE2.temperature', 0, undefined, function (a) { return a * 0.01 }],

                        ['SCALED_PRESSURE3.temperature', 0, undefined, function (a) { return a * 0.01 }]
                    ],
                'Sensors/Barometer/Barometer Comparison ':
                    [

                        ['SCALED_PRESSURE.temperature', 0, undefined, function (a) { return a * 0.01 }],

                        ['SCALED_PRESSURE2.temperature', 0, undefined, function (a) { return a * 0.01 }]
                    ],
                'Sensors/Barometer/Barometer Comparison  ':
                    [
                        ['BARO.Alt', 0],
                        ['BARO.Temp', 0],
                        ['BAR2.Alt', 0],
                        ['BAR2.Temp', 0],
                        ['BAR3.Alt', 0],
                        ['BAR3.Temp', 0]
                    ],
                'Sensors/Barometer/Barometer Comparison   ':
                    [
                        ['BARO.Alt', 0],
                        ['BARO.Temp', 0],
                        ['BAR2.Alt', 0],
                        ['BAR2.Temp', 0]
                    ],
                'Sensors/Barometer/Barometric Pressure':
                    [
                        ['SCALED_PRESSURE.press_abs', 0]
                    ],
                'Sensors/Barometer/Barometric Pressure ':
                    [
                        ['BARO.Press', 0]
                    ],
                'Sensors/Compass/Compass':
                    [
                        ['RAW_IMU.xmag', 0],
                        ['RAW_IMU.ymag', 0],
                        ['RAW_IMU.zmag', 0]

                    ],
                'Sensors/Compass/Compass ':
                    [
                        ['MAG.MagX', 0],
                        ['MAG.MagY', 0],
                        ['MAG.MagZ', 0]

                    ],
                'Sensors/Compass/Compass(2)':
                    [
                        ['SCALED_IMU2.xmag', 0],
                        ['SCALED_IMU2.ymag', 0],
                        ['SCALED_IMU2.zmag', 0]

                    ],
                'Sensors/Compass/Compass(2) ':
                    [
                        ['MAG2.MagX', 0],
                        ['MAG2.MagY', 0],
                        ['MAG2.MagZ', 0]

                    ],
                'Sensors/Compass/Compass(3)':
                    [
                        ['SCALED_IMU3.xmag', 0],
                        ['SCALED_IMU3.ymag', 0],
                        ['SCALED_IMU3.zmag', 0]

                    ],
                'Sensors/Compass/Compass(3) ':
                    [
                        ['MAG3.MagX', 0],
                        ['MAG3.MagY', 0],
                        ['MAG3.MagZ', 0]

                    ],
                'Sensors/Compass/Compass vs Yaw':
                    [

                        ['ATTITUDE.yaw', 0, undefined, function (a) { return degrees(a) }]
                    ],
                'Sensors/Compass/Compass vs Yaw ':
                    [

                        ['ATT.Yaw', 0]
                    ],
                'Servos/Servos 1-4':
                    [
                        ['SERVO_OUTPUT_RAW.servo1_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo2_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo3_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo4_raw', 0]
                    ],
                'Servos/Servos 1-4 ':
                    [
                        ['RCOU.Ch1', 0],
                        ['RCOU.Ch2', 0],
                        ['RCOU.Ch3', 0],
                        ['RCOU.Ch4', 0]
                    ],
                'Servos/Servos 1-4  ':
                    [
                        ['RCOU.C1', 0],
                        ['RCOU.C2', 0],
                        ['RCOU.C3', 0],
                        ['RCOU.C4', 0]
                    ],
                'Servos/Servos 1-8':
                    [
                        ['SERVO_OUTPUT_RAW.servo1_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo2_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo3_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo4_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo5_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo6_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo7_raw', 0],
                        ['SERVO_OUTPUT_RAW.servo8_raw', 0]
                    ],
                'Servos/Servos 1-8 ':
                    [
                        ['RCOU.Ch1', 0],
                        ['RCOU.Ch2', 0],
                        ['RCOU.Ch3', 0],
                        ['RCOU.Ch4', 0],
                        ['RCOU.Ch5', 0],
                        ['RCOU.Ch6', 0],
                        ['RCOU.Ch7', 0],
                        ['RCOU.Ch8', 0]
                    ],
                'Servos/Servos 1-8  ':
                    [
                        ['RCOU.C1', 0],
                        ['RCOU.C2', 0],
                        ['RCOU.C3', 0],
                        ['RCOU.C4', 0],
                        ['RCOU.C5', 0],
                        ['RCOU.C6', 0],
                        ['RCOU.C7', 0],
                        ['RCOU.C8', 0]
                    ],
                'RC/RC Input 1-4':
                    [
                        ['RC_CHANNELS.chan1_raw', 0],
                        ['RC_CHANNELS.chan2_raw', 0],
                        ['RC_CHANNELS.chan3_raw', 0],
                        ['RC_CHANNELS.chan4_raw', 0]
                    ],
                'RC/RC Input 1-4 ':
                    [
                        ['RC_CHANNELS_RAW.chan1_raw', 0],
                        ['RC_CHANNELS_RAW.chan2_raw', 0],
                        ['RC_CHANNELS_RAW.chan3_raw', 0],
                        ['RC_CHANNELS_RAW.chan4_raw', 0]
                    ],
                'RC/RC Input 1-4  ':
                    [
                        ['RCIN.C1', 0],
                        ['RCIN.C2', 0],
                        ['RCIN.C3', 0],
                        ['RCIN.C4', 0]
                    ],
                'RC/RC Input 1-8':
                    [
                        ['RC_CHANNELS.chan1_raw', 0],
                        ['RC_CHANNELS.chan2_raw', 0],
                        ['RC_CHANNELS.chan3_raw', 0],
                        ['RC_CHANNELS.chan4_raw', 0],
                        ['RC_CHANNELS.chan5_raw', 0],
                        ['RC_CHANNELS.chan6_raw', 0],
                        ['RC_CHANNELS.chan7_raw', 0],
                        ['RC_CHANNELS.chan8_raw', 0]
                    ],
                'RC/RC Input 1-8 ':
                    [
                        ['RC_CHANNELS_RAW.chan1_raw', 0],
                        ['RC_CHANNELS_RAW.chan2_raw', 0],
                        ['RC_CHANNELS_RAW.chan3_raw', 0],
                        ['RC_CHANNELS_RAW.chan4_raw', 0],
                        ['RC_CHANNELS_RAW.chan5_raw', 0],
                        ['RC_CHANNELS_RAW.chan6_raw', 0],
                        ['RC_CHANNELS_RAW.chan7_raw', 0],
                        ['RC_CHANNELS_RAW.chan8_raw', 0]
                    ],
                'RC/RC Input 1-8  ':
                    [
                        ['RCIN.C1', 0],
                        ['RCIN.C2', 0],
                        ['RCIN.C3', 0],
                        ['RCIN.C4', 0],
                        ['RCIN.C5', 0],
                        ['RCIN.C6', 0],
                        ['RCIN.C7', 0],
                        ['RCIN.C8', 0]
                    ],
                'Sensors/Lidar/Rangefinder vs Baro':
                    [
                        ['BARO.Alt', 0],
                        ['RFND.Dist1', 0],
                        ['RFND.Dist2', 0]
                    ],
                'Plane/PID Tuning/Pitch Controller':
                    [
                        ['PIDP.Des', 0],
                        ['PIDP.P', 0],
                        ['PIDP.I', 0],
                        ['PIDP.D', 0]

                    ],
                'Plane/PID Tuning/Roll Controller':
                    [
                        ['PIDR.Des', 0],
                        ['PIDR.P', 0],
                        ['PIDR.I', 0],
                        ['PIDR.D', 0]

                    ],
                'Sensors/Compass/Compare Predicted':
                    [
                        ['MAG.MagX', 0],

                        ['MAG.MagY', 0],

                        ['MAG.MagZ', 0]

                    ],
                'Sensors/Compass/Compare Predicted ':
                    [
                        ['RAW_IMU.xmag', 0],

                        ['RAW_IMU.ymag', 0],

                        ['RAW_IMU.zmag', 0]

                    ],
                'Sensors/Compass/Compare Predicted2':
                    [
                        ['MAG2.MagX', 0],

                        ['MAG2.MagY', 0],

                        ['MAG2.MagZ', 0]

                    ],
                'Sensors/Compass/Compare Predicted2 ':
                    [
                        ['SCALED_IMU2.xmag', 0],

                        ['SCALED_IMU2.ymag', 0],

                        ['SCALED_IMU2.zmag', 0]

                    ],
                'Sensors/Compass/Compare Predicted3':
                    [
                        ['MAG3.MagX', 0],

                        ['MAG3.MagY', 0],

                        ['MAG3.MagZ', 0]

                    ],
                'Sensors/Compass/Compare Predicted3 ':
                    [
                        ['SCALED_IMU3.xmag', 0],

                        ['SCALED_IMU3.ymag', 0],

                        ['SCALED_IMU3.zmag', 0]

                    ],

                'Copter/PID/PIDP':
                    [
                        ['PIDP.P', 0],
                        ['PIDP.I', 0],
                        ['PIDP.D', 0]
                    ],
                'Copter/PID/PIDR':
                    [
                        ['PIDR.P', 0],
                        ['PIDR.I', 0],
                        ['PIDR.D', 0]
                    ],
                'Copter/PID/PIDY':
                    [
                        ['PIDY.P', 0],
                        ['PIDY.I', 0],
                        ['PIDY.D', 0]
                    ],
                'Copter/PID/PIDA':
                    [
                        ['PIDA.P', 0],
                        ['PIDA.I', 0],
                        ['PIDA.D', 0]
                    ],
                'SITL/SIM RollRate vs GyrX':
                    [
                        ['IMU.GyrX', 0]

                    ],
                'SITL/SIM PitchRate vs GyrY':
                    [
                        ['IMU.GyrY', 0]

                    ],
                'SITL/SIM YawRate vs GyrZ':
                    [
                        ['IMU.GyrZ', 0]

                    ]
            },
            userPresets: {}
        }
    },
    created () {
        this.$eventHub.$on('messageTypes', this.handleMessageTypes)
        this.$eventHub.$on('presetsChanged', this.loadLocalPresets)
        this.loadLocalPresets()
    },
    beforeDestroy () {
        this.$eventHub.$off('messageTypes')
    },
    methods: {
        loadLocalPresets () {
            let saved = window.localStorage.getItem('savedFields')
            if (saved !== null) {
                this.userPresets = JSON.parse(saved)
            }
        },
        handleMessageTypes (messageTypes) {
            if (this.$route.query.hasOwnProperty('plots')) {
                this.state.plot_on = true
            }
            let newMessages = {}
            // populate list of message types
            for (let messageType of Object.keys(messageTypes)) {
                this.$set(this.checkboxes, messageType, messageTypes[messageType].fields.fields)
                newMessages[messageType] = messageTypes[messageType]
            }
            // populate checkbox status
            for (let messageType of Object.keys(messageTypes)) {
                this.checkboxes[messageType] = {fields: {}}
                // for (let field of this.getMessageNumericField(this.state.messages[messageType][0])) {
                for (let field of messageTypes[messageType].fields) {
                    if (this.state.plot_on) {
                        this.checkboxes[messageType].fields[field] =
                            this.$route.query.plots.indexOf(messageType + '.' + field) !== -1
                    } else {
                        this.checkboxes[messageType].fields[field] = false
                    }
                }
            }
            this.messageTypes = newMessages
            this.state.messageTypes = newMessages
        },
        isPlotted (message, field) {
            let fullname = message + '.' + field
            for (let field of this.state.fields) {
                if (field.name === fullname) {
                    return true
                }
            }
            return false
        },
        getMessageNumericField (message) {
            let numberFields = []
            if (message && message.hasOwnProperty('fieldnames')) {
                for (let field of message.fieldnames) {
                    if (!isNaN(message[field])) {
                        numberFields.push(field)
                    }
                }
            }
            return numberFields
        },
        toggle (message, item) {
            this.state.plot_on = true
            this.$nextTick(function () {
                this.$eventHub.$emit('togglePlot', message + '.' + item)
            })
        },
        isPlottable (msgtype, item) {
            return item !== 'TimeUS'
        }
    },
    computed: {
        hasMessages () {
            return Object.keys(this.messageTypes).length > 0
        },
        messageTypesFiltered () {
            let filtered = {}
            for (let key of Object.keys(this.messageTypes)) {
                if (this.hiddenTypes.indexOf(key) === -1) {
                    if (this.messageTypes[key].fields
                        .filter(field => field.toLowerCase().indexOf(this.filter.toLowerCase()) !== -1).length > 0) {
                        filtered[key] = this.messageTypes[key]
                        // console.log('type' + key, document.getElementById('type' + key))
                        if (document.getElementById('type' + key) &&
                                document.getElementById('type' + key).style &&
                                document.getElementById('type' + key).style.display === 'none'
                        ) {
                            console.log(document.getElementById('type' + key).style.display)
                            this.$root.$emit('bv::toggle::collapse', 'type' + key)
                        }
                    }
                }
            }
            return filtered
        },
        availableMessagePresets () {
            let dict = {}
            // do it for default messages
            for (const [key, value] of Object.entries(this.messagePresets)) {
                for (let field of value) {
                    // If any of the fields match, add this and move on
                    if (field[0].split('.')[0] in this.state.messageTypes) {
                        if (!(key in dict)) {
                            dict[key] = {messages: [field]}
                        } else {
                            dict[key].messages.push(field)
                        }
                    }
                }
            }
            // And again for user presets
            for (const [key, value] of Object.entries(this.userPresets)) {
                for (let field of value) {
                    // If any of the fields match, add this and move on
                    if (field[0].split('.')[0] in this.state.messageTypes) {
                        if (!(key in dict)) {
                            dict[key] = {messages: [field], user: true}
                        } else {
                            dict[key].messages.push(field)
                        }
                    }
                }
            }
            let newDict = {}
            for (const [key, value] of Object.entries(dict)) {
                let current = newDict
                let fields = key.split('/')
                let lastField = fields.pop()
                for (let field of fields) {
                    if (!(field in current)) {
                        console.log('overwriting ' + field)
                        current[field] = {}
                    }
                    current = current[field]
                }
                current[lastField] = value
            }
            return newDict
        }
    }
}
</script>
<style scoped>
    i {
        margin: 5px;
    }
    i.expand {
        float: right;
    }
    li > div {
        display: inline-block;
        width: 100%;
    }
    li.field {
        line-height: 25px;
        padding-left: 40px;
        font-size: 90%;
        display: inline-block;
        width: 100%;
    }
    li.type {
        line-height: 30px;
        padding-left: 10px;
        font-size: 85%;
    }
    input {
        margin: 12px 12px 15px 10px;
        border: 2px solid #ccc;
        -webkit-border-radius: 4px;
        -moz-border-radius: 4px;
        border-radius: 4px;
        background-color: rgba(255, 255, 255, 0.897);
        color: rgb(51, 51, 51);
        width: 92%;
    }
    input:focus {
        outline: none;
        border: 2px solid #135388;
    }
    .input-li:hover {
        background-color: rgba(30, 37, 54, 0.205);
        border-left: 3px solid rgba(24, 30, 44, 0.212);
    }
    ::placeholder { /* Chrome, Firefox, Opera, Safari 10.1+ */
        color: rgb(148, 147, 147);
        opacity: 1; /* Firefox */
    }
    :-ms-input-placeholder { /* Internet Explorer 10-11 */
        color: #2e2e2e;
    }
    ::-ms-input-placeholder { /* Microsoft Edge */
        color: #2e2e2e;
    }
    i.remove-icon {
        float: right;
    }

</style>
