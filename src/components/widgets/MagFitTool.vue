<template>
    <div :id="getDivName()"
         v-bind:style='{ top: top + "px", left: left + "px" }'>
        <div id='paneContent'>
            <div class="header">
              <h5>Mag Fit Tool</h5>
              <span class="close-btn" @click="close()" title="Close">&times;</span>
            </div>
            <div class="section">
              <h6>Location</h6>
            <table>
              <tr v-if="GpsPosition" >
                <td>Lat</td><td>
                  <input type="text" disabled readonly v-model="GpsPosition.lat" size="10"/></td>
              </tr>
              <tr v-if="GpsPosition" >
                <td>Lon</td><td>
                  <input type="text" disabled readonly v-model="GpsPosition.lon" size="10"/></td>
              </tr>
              <tr v-if="!GpsPosition">
                <td>Lat</td><td>
                  <input type="text" v-model="userLat" size="10"/></td>
              </tr>
              <tr v-if="!GpsPosition">
                <td>Lon</td><td>
                  <input type="text" v-model="userLon" size="10"/></td>
              </tr>
              <tr v-if="!GpsPosition">
                <td></td><td>
                  <button @click="getLocationFromIp()" :disabled="fetchingLocation">
                    {{ fetchingLocation ? 'Locating...' : 'Get from IP' }}
                  </button></td>
              </tr>
              <tr v-if="!GpsPosition && locationError">
                <td></td><td style="color: #b00;">{{ locationError }}</td>
              </tr>
              <tr v-if="!positionValid">
                <td></td><td class="hint">Enter lat/lon to enable fitting</td>
              </tr>
              <tr>
                <td>Earth Field</td><td>{{ printEarthField }}</td>
              </tr>
            </table>
            </div>
            <div class="section">
              <h6>Fit settings</h6>
              <table>
                <tr>
                  <td>Fit</td>
                  <td>
                    <select v-model="fitType">
                      <option v-for="(label, key) in fitTypes" :key="key" :value="key">{{ label }}</option>
                    </select>
                  </td>
                </tr>
                <tr>
                  <td>Motor comp</td>
                  <td>
                    <label :title="currentSource ? '' : 'The log has no battery current'">
                      <input type="checkbox" v-model="fitMotor" :disabled="!currentSource">
                      {{ currentSource ? 'fit from ' + currentSource.name : 'no battery current in log' }}
                    </label>
                  </td>
                </tr>
                <tr>
                  <td>Expected yaw</td>
                  <td>
                    <select v-model="yawSource"
                            title="Compass: heading of the calibrated field (independent of the EKF).
Attitude: logged EKF yaw, which was itself estimated using the compass.">
                      <option v-for="(label, key) in yawSources" :key="key" :value="key">{{ label }}</option>
                    </select>
                  </td>
                </tr>
              </table>
            </div>
            <div class="section">
              <h6>Compasses (existing calibration)</h6>
              <table v-if="compassInputs.length" class="results">
                  <tr>
                      <th>Compass</th>
                      <th>Message</th>
                      <th>ofsx</th>
                      <th>ofsy</th>
                      <th>ofsz</th>
                      <th>scale</th>
                      <th title="RMS difference between the logged field and the expected earth field">
                        error (mGauss)</th>
                      <th colspan="3"></th>
                  </tr>
                  <tr :key="'param' + index" v-for="(params, index) in compassParams">
                    <td>{{ index + 1 }}</td>
                    <td>{{ compassMessageNames[index] }}</td>
                    <td>{{ params.offsets[0].toFixed(1) }}</td>
                    <td>{{ params.offsets[1].toFixed(1) }}</td>
                    <td>{{ params.offsets[2].toFixed(1) }}</td>
                    <td>{{ formatScale(params.scale) }}</td>
                    <td>{{ formatError(preErrors[index]) }}</td>
                    <td class="actions">
                      <button :disabled="processing || !positionValid"
                              :title="positionValid ? '' : 'Enter a latitude and longitude first'"
                              v-on:click="fitCompass(index)">
                        <i v-if="processing && processingInstance === index" class="fas fa-spinner fa-spin"></i>
                        <span v-else>Fit</span>
                      </button>
                    </td>
                    <td class="actions">
                      <button @click="plotOldRaw(index)">Plot Raw</button>
                    </td>
                    <td class="actions">
                      <button @click="plotOldHeading(index)">Plot Heading</button>
                    </td>
                  </tr>
              </table>
              <i v-else class="fas fa-spinner fa-spin">
              </i>
              <ul class="notes" v-if="calibrationNotes.length">
                <li v-for="note in calibrationNotes" :key="note">{{ note }}</li>
              </ul>
              <div class="section-footer" v-if="compassInputs.length > 1">
                <button :disabled="processing || !positionValid" @click="fitAll()">Fit all</button>
              </div>
            </div>
            <div class="section" v-if="compassMessageNames.length >= 2">
              <h6>Consistency</h6>
              <div style="margin-bottom: 6px;">
                Compare
                <select v-model.number="diffCompassA">
                  <option v-for="(name, index) in compassMessageNames" :key="'a' + index" :value="index">
                    {{ index + 1 }}
                  </option>
                </select>
                vs
                <select v-model.number="diffCompassB">
                  <option v-for="(name, index) in compassMessageNames" :key="'b' + index" :value="index">
                    {{ index + 1 }}
                  </option>
                </select>
              </div>
              <button :disabled="diffCompassA === diffCompassB"
                      @click="plotOldHeadingDiff(diffCompassA, diffCompassB)">Plot heading diff (raw)</button>
              <button v-if="isFitted(diffCompassA) && isFitted(diffCompassB)"
                      :disabled="diffCompassA === diffCompassB"
                      @click="plotNewHeadingDiff(diffCompassA, diffCompassB)">Plot heading diff (fitted)</button>
            </div>
            <div class="section" v-if="residualPlot">
              <h6>Field error, compass {{ residualInstance + 1 }}</h6>
              <svg class="residual-chart" :width="chartWidth" :height="chartHeight">
                <polyline :points="residualPlot.before" fill="none" stroke="#9aa3ad" stroke-width="1"/>
                <polyline :points="residualPlot.after" fill="none" stroke="#1a7f37" stroke-width="1.2"/>
              </svg>
              <div class="chart-caption">
                <span class="legend-before">existing</span> vs <span class="legend-after">fitted</span>
                &middot; 0 to {{ residualPlot.max.toFixed(0) }} mGauss over {{ residualPlot.duration.toFixed(0) }} s
              </div>
            </div>
            <div class="section" v-if="fittedIndices.length > 0 || fitFailures.length > 0 || processing">
              <h6>New calibration</h6>
              <table class="results" v-if="fittedIndices.length">
                  <tr>
                      <th>Param</th>
                      <th v-for="index in fittedIndices" :key="'head' + index">Compass {{ index + 1 }}</th>
                  </tr>
                  <tr>
                    <td>Fit</td>
                    <td v-for="index in fittedIndices" :key="'type' + index">{{ fitDescription(fits[index]) }}</td>
                  </tr>
                  <tr v-for="row in paramRows" :key="row.key">
                    <td>{{ row.key }}</td>
                    <td v-for="index in fittedIndices" :key="row.key + index"
                        :class="{ 'out-of-range': outOfRange(index, row.key) }"
                        :title="outOfRange(index, row.key) ? 'Outside typical range' : ''">
                      {{ row.value(fits[index].cal).toFixed(row.digits) }}
                    </td>
                  </tr>
                  <tr>
                    <td title="RMS difference between the corrected and expected field, existing vs new">
                      error (mGauss)</td>
                    <td v-for="index in fittedIndices" :key="'error' + index" :class="fitnessClass(index)">
                      {{ formatComparison(index) }}
                    </td>
                  </tr>
                  <tr>
                    <td>samples / passes</td>
                    <td v-for="index in fittedIndices" :key="'samples' + index"
                        :title="fits[index].converged ? '' : 'Stopped before converging'">
                      {{ fits[index].numSamples }} / {{ fits[index].iterations }}{{ fits[index].converged ? '' : '*' }}
                    </td>
                  </tr>
                  <tr>
                    <td></td>
                    <td v-for="index in fittedIndices" :key="'actions' + index" class="actions">
                      <button @click="plotRaw(index)">Plot Raw</button>
                      <button @click="plotNewHeading(index)">Plot Heading</button>
                      <button @click="residualInstance = index">Error</button>
                    </td>
                  </tr>
              </table>
              <ul class="notes warnings" v-if="fitFailures.length || fitWarnings.length">
                <li v-for="message in fitFailures" :key="message">{{ message }}</li>
                <li v-for="warning in fitWarnings" :key="warning">{{ warning }}</li>
              </ul>
              <div class="section-footer">
                <span v-if="processing"><i class="fas fa-spinner fa-spin"></i> Fitting...</span>
                <button v-else-if="fittedIndices.length" @click="downloadParams()">Download Params file</button>
              </div>
          </div>
        </div>
    </div>
</template>

<script>
import { store } from '../Globals.js'
import { baseWidget } from './baseWidget'
import { Vector3 } from '../../mavextra/vector3'
import { Matrix3 } from '../../mavextra/matrix3'
import { saveAs } from 'file-saver'
import {
    FIT_TYPES,
    MOT_COMP_CURRENT,
    YAW_SOURCES,
    applyCalibration,
    calibrationError,
    fitCalibration,
    interpolate,
    rangeWarnings,
    removeCalibration,
    scaleValid
} from '../../tools/magfit'

// Candidate compass message keys, in priority order. Covers tlogs (RAW_IMU,
// SCALED_IMU*), modern dataflash instanced messages (MAG[0..2]) and older
// dataflash logs (MAG, MAG2, MAG3). compassData and compassMessageNames are
// both derived from this list so their indices stay aligned.
const COMPASS_MESSAGE_CANDIDATES = [
    'RAW_IMU', 'SCALED_IMU2', 'SCALED_IMU3',
    'MAG[0]', 'MAG[1]', 'MAG[2]',
    'MAG', 'MAG2', 'MAG3'
]

const AXES = ['X', 'Y', 'Z']

// Rows of the new calibration table, in param file order
const PARAM_ROWS = [
    ...AXES.map((axis, i) => ({ key: `OFS_${axis}`, value: cal => cal.offsets[i], digits: 2 })),
    ...AXES.map((axis, i) => ({ key: `DIA_${axis}`, value: cal => cal.diagonals[i], digits: 4 })),
    ...AXES.map((axis, i) => ({ key: `ODI_${axis}`, value: cal => cal.offDiagonals[i], digits: 4 })),
    { key: 'SCALE', value: cal => cal.scale, digits: 4 },
    ...AXES.map((axis, i) => ({ key: `MOT_${axis}`, value: cal => cal.motor[i], digits: 3 }))
]

function formatParamValue (value) {
    return parseFloat(value.toFixed(6)).toString()
}

export default {
    name: 'MagFitTool',
    mixins: [baseWidget],
    data () {
        return {
            name: 'MagFitTool',
            state: store,
            width: 580,
            height: 680,
            left: 432,
            top: 12,
            maxFitSamples: 4000,
            compassData: [],
            compassMessageNames: [],
            attitude: null,
            currentSource: null,
            fitTypes: FIT_TYPES,
            yawSources: YAW_SOURCES,
            paramRows: PARAM_ROWS,
            fitType: 'offsets',
            fitMotor: false,
            yawSource: 'mag',
            fits: [],
            residualInstance: null,
            processing: false,
            processingInstance: null,
            chartWidth: 360,
            chartHeight: 90,
            userLat: 0,
            userLon: 0,
            fetchingLocation: false,
            locationError: null,
            diffCompassA: 0,
            diffCompassB: 1
        }
    },
    methods: {
        fullParamName (key, compassNumber) {
            // key is a param suffix such as OFS_X or SCALE
            if (key === 'SCALE') {
                return this.paramName('SCALE', compassNumber)
            }
            const [base, axis] = key.split('_')
            return `${this.paramName(base, compassNumber)}_${axis}`
        },
        downloadParams () {
            const lines = []
            const warnings = [...this.fitWarnings]
            let motorFitted = false
            for (const index of this.fittedIndices) {
                const fit = this.fits[index]
                const compassNumber = index + 1
                lines.push(`# Compass ${compassNumber} (${this.compassMessageNames[index]}): ` +
                    `${this.fitDescription(fit)}, error ${this.formatComparison(index)} mGauss`)
                for (const row of PARAM_ROWS) {
                    lines.push(`${this.fullParamName(row.key, compassNumber)},${formatParamValue(row.value(fit.cal))}`)
                }
                motorFitted = motorFitted || fit.fitMotor
            }

            // Motor compensation type is shared by all compasses
            const motorCompType = motorFitted ? MOT_COMP_CURRENT : 0
            lines.push(`COMPASS_MOTCT,${motorCompType}`)
            const oldMotorCompType = this.parameters.COMPASS_MOTCT || 0
            if (oldMotorCompType !== motorCompType) {
                this.compassParams.forEach((params, index) => {
                    if (!this.isFitted(index) && params.motor.some(v => v !== 0)) {
                        warnings.push(`COMPASS_MOTCT changes from ${oldMotorCompType} to ${motorCompType}, ` +
                            `but compass ${index + 1} was not fitted and has non-zero MOT params`)
                    }
                })
            }
            if (this.parameters.COMPASS_PMOT_EN && this.isFitted(0)) {
                // per-motor compensation replaces COMPASS_MOT on the first compass
                lines.push('COMPASS_PMOT_EN,0')
            }

            if (warnings.length > 0 &&
                !window.confirm(`Warning:\n${warnings.join('\n')}\n\nSave parameters anyway?`)) {
                return
            }

            let content = ''
            content += `# Compass-fit params from file: ${this.state.file}\n`
            content += `# Date: ${new Date()}\n`
            content += `# Expected field yaw source: ${YAW_SOURCES[this.yawSource]}\n`
            content += lines.join('\n') + '\n'

            const fileName = `${this.state.file}.params`
            const file = new File([content], `${fileName}-compassfit.txt`, { type: 'text/plain' })
            saveAs(file)
        },
        plotRaw (instance) {
            this.state.plotOn = true
            this.$nextTick(() => {
                this.$eventHub.$emit('togglePlot', 'MAGFIT' + instance + '.MagX', 0)
                this.$eventHub.$emit('togglePlot', 'MAGFIT' + instance + '.MagY', 0)
                this.$eventHub.$emit('togglePlot', 'MAGFIT' + instance + '.MagZ', 0)
            })
        },
        plotNewHeading (instance) {
            this.state.plotOn = true
            this.$nextTick(() => {
                const headingFunction = this.isTlog ? 'mag_heading' : 'mag_heading_df'
                const attitudeMessage = this.isTlog ? 'ATTITUDE' : 'ATT'
                const compassMessage = 'MAGFIT' + instance
                this.$eventHub.$emit('togglePlot', `${headingFunction}(${compassMessage}, ${attitudeMessage})`, 1)
            })
        },
        plotOldRaw (i) {
            this.state.plotOn = true
            this.$nextTick(() => {
                if (this.isTlog) {
                    this.$eventHub.$emit('togglePlot', this.compassMessageNames[i] + '.xmag', 0)
                    this.$eventHub.$emit('togglePlot', this.compassMessageNames[i] + '.ymag', 0)
                    this.$eventHub.$emit('togglePlot', this.compassMessageNames[i] + '.zmag', 0)
                } else {
                    this.$eventHub.$emit('togglePlot', this.compassMessageNames[i] + '.MagX', 0)
                    this.$eventHub.$emit('togglePlot', this.compassMessageNames[i] + '.MagY', 0)
                    this.$eventHub.$emit('togglePlot', this.compassMessageNames[i] + '.MagZ', 0)
                }
            })
        },
        plotOldHeading (i) {
            this.state.plotOn = true
            this.$nextTick(() => {
                this.$nextTick(() => {
                    const headingFunction = this.isTlog ? 'mag_heading' : 'mag_heading_df'
                    const attitudeMessage = this.isTlog ? 'ATTITUDE' : 'ATT'
                    const compassMessage = this.compassMessageNames[i]
                    this.$eventHub.$emit('togglePlot', `${headingFunction}(${compassMessage}, ${attitudeMessage})`, 1)
                })
            })
        },
        setup () {
            this.loadRequiredData()
        },
        async getLocationFromIp () {
            // fetch approximate coordinates from a geo-IP service when the log
            // has no position. Used to estimate the earth's magnetic field.
            this.fetchingLocation = true
            this.locationError = null
            const sources = [
                'https://ipapi.co/json/',
                'https://ipwho.is/'
            ]
            for (const url of sources) {
                try {
                    const response = await fetch(url)
                    if (!response.ok) {
                        continue
                    }
                    const data = await response.json()
                    // both services expose latitude/longitude as numbers
                    const lat = Number(data.latitude)
                    const lon = Number(data.longitude)
                    if (Number.isFinite(lat) && Number.isFinite(lon)) {
                        this.userLat = lat
                        this.userLon = lon
                        this.fetchingLocation = false
                        return
                    }
                } catch (error) {
                    console.log('geo-ip lookup failed for', url, error)
                }
            }
            this.locationError = 'Could not determine location from IP'
            this.fetchingLocation = false
        },
        messageLoaded (name) {
            if (this.state.messages[name]) {
                return true
            }
            const instances = this.state.messageTypes?.[name]?.instances
            if (instances) {
                return Object.values(instances).every(instanceName => this.state.messages[instanceName])
            }
            return false
        },
        waitForMessages (messages) {
            for (const message of messages) {
                this.$eventHub.$emit('loadType', message)
            }
            return new Promise((resolve) => {
                let counter = 0
                const interval = setInterval(() => {
                    counter += 1
                    // 30 * 300ms = 9 s timeout, carry on with whatever has loaded
                    if (messages.every(message => this.messageLoaded(message)) || counter > 30) {
                        clearInterval(interval)
                        resolve()
                    }
                }, 300)
            })
        },
        loadRequiredData () {
            // sends loadType messages for the compass, attitude and battery messages
            // of either log type, skipping the ones the log doesn't have
            const wanted = this.isTlog
                ? ['RAW_IMU', 'SCALED_IMU2', 'SCALED_IMU3', 'ATTITUDE', 'SYS_STATUS']
                : ['ATT', 'MAG', 'MAG2', 'MAG3', 'BAT']
            const available = Object.keys(this.state.messageTypes || {})
            const requiredTypes = available.length ? wanted.filter(type => available.includes(type)) : wanted
            this.waitForMessages(requiredTypes).then(() => {
                this.computeData()
            })
        },
        computeData () {
            // Shallow frozen copies so Vue doesn't make the (large) message arrays reactive
            this.compassData = COMPASS_MESSAGE_CANDIDATES
                .filter(message => this.state.messages[message])
                .map(message => Object.freeze({ ...this.state.messages[message] }))
            // state.messages keys are added non-reactively as types stream in, so
            // derive the names here (after the data is loaded) instead of in a
            // computed that would never recompute.
            this.compassMessageNames = COMPASS_MESSAGE_CANDIDATES.filter(
                message => this.state.messages[message]
            )
            this.attitude = this.extractAttitude()
            this.currentSource = this.extractCurrent()
            if (!this.currentSource) {
                this.fitMotor = false
            }
        },
        extractAttitude () {
            // attitude in radians
            if ('ATT' in this.state.messages) {
                const att = this.state.messages.ATT
                const toRad = values => Array.from(values, v => v * Math.PI / 180)
                return Object.freeze({
                    time: Array.from(att.time_boot_ms),
                    roll: toRad(att.Roll),
                    pitch: toRad(att.Pitch),
                    yaw: toRad(att.Yaw)
                })
            }
            const att = this.state.messages.ATTITUDE
            if (!att) {
                return null
            }
            return Object.freeze({
                time: Array.from(att.time_boot_ms),
                roll: Array.from(att.roll),
                pitch: Array.from(att.pitch),
                yaw: Array.from(att.yaw)
            })
        },
        extractCurrent () {
            // battery current in amps, used for current based motor compensation
            const messages = this.state.messages
            let source = null
            const bat = messages['BAT[0]'] || messages.BAT
            if (bat && bat.Curr) {
                source = {
                    name: 'BAT.Curr',
                    time: Array.from(bat.time_boot_ms),
                    current: Array.from(bat.Curr)
                }
            } else if (messages.SYS_STATUS && messages.SYS_STATUS.current_battery) {
                const status = messages.SYS_STATUS
                source = {
                    name: 'SYS_STATUS.current_battery',
                    time: Array.from(status.time_boot_ms),
                    // centi-amps, -1 if not measured
                    current: Array.from(status.current_battery, c => c < 0 ? NaN : c / 100)
                }
            }
            if (source === null || !source.current.some(c => Number.isFinite(c) && c !== 0)) {
                return null
            }
            return Object.freeze(source)
        },
        prepareCompass (message, index) {
            // Remove the existing calibration from the logged field to get the raw sensor field
            const fieldNames = this.isTlog ? ['xmag', 'ymag', 'zmag'] : ['MagX', 'MagY', 'MagZ']
            const time = Array.from(message.time_boot_ms)
            const logged = {
                x: Array.from(message[fieldNames[0]]),
                y: Array.from(message[fieldNames[1]]),
                z: Array.from(message[fieldNames[2]])
            }
            const params = this.compassParams[index]
            const current = this.currentSource
                ? interpolate(this.currentSource.time, this.currentSource.current, time)
                : null

            // Dataflash MAG messages log the offsets and motor compensation that were applied
            const loggedOffsets = !this.isTlog && message.OfsX !== undefined
            const offsets = loggedOffsets ? { x: message.OfsX, y: message.OfsY, z: message.OfsZ } : params.offsets
            let motorOffsets = null
            let motorRemoved = true
            const motorFields = ['MOX', 'MOY', 'MOZ'].every(field => message[field] !== undefined)
                ? ['MOX', 'MOY', 'MOZ']
                : ['MOfsX', 'MOfsY', 'MOfsZ']
            const loggedMotor = !this.isTlog && motorFields.every(field => message[field] !== undefined)
            if (loggedMotor) {
                motorOffsets = { x: message[motorFields[0]], y: message[motorFields[1]], z: message[motorFields[2]] }
            } else if (this.motorCompType !== 0 && params.motor.some(v => v !== 0)) {
                if (this.motorCompType === MOT_COMP_CURRENT && current) {
                    motorOffsets = {
                        x: current.map(amps => amps * params.motor[0]),
                        y: current.map(amps => amps * params.motor[1]),
                        z: current.map(amps => amps * params.motor[2])
                    }
                } else {
                    motorRemoved = false
                }
            }

            const raw = removeCalibration(logged, {
                offsets,
                motorOffsets,
                diagonals: params.diagonals,
                offDiagonals: params.offDiagonals,
                scale: params.scale
            })

            const att = this.attitude
            const nan = time.map(() => NaN)
            return Object.freeze({
                time,
                logged,
                raw,
                current,
                roll: att ? interpolate(att.time, att.roll, time, 2 * Math.PI) : nan,
                pitch: att ? interpolate(att.time, att.pitch, time) : nan,
                yaw: att ? interpolate(att.time, att.yaw, time, 2 * Math.PI) : nan,
                loggedOffsets,
                loggedMotor,
                motorRemoved,
                error: raw === null ? 'Existing iron calibration (DIA/ODI) is singular, cannot remove it' : null
            })
        },
        paramName (name, index) {
            if (this.newParamFormat) {
                return `COMPASS${index}_${name}`
            }

            if (index === 1) {
                return `COMPASS_${name}`
            }
            return `COMPASS_${name}${index}`
        },
        compassParamNames (compassIndex) {
            const names = AXES.map(axis => this.paramName('OFS', compassIndex) + '_' + axis)
            for (const name of ['DIA', 'ODI', 'MOT']) {
                names.push(...AXES.map(axis => this.paramName(name, compassIndex) + '_' + axis))
            }
            names.push(this.paramName('SCALE', compassIndex))
            return names
        },
        getCompassParams (compassIndex) {
            // Calibration params at the end of the log. Values that are missing from
            // the log take the firmware defaults.
            const get = (name, fallback) => {
                const value = this.parameters[name]
                return Number.isFinite(value) ? value : fallback
            }
            const vector = (name, fallback) => AXES.map(
                axis => get(this.paramName(name, compassIndex) + '_' + axis, fallback)
            )
            return {
                offsets: vector('OFS', 0),
                diagonals: vector('DIA', 1),
                offDiagonals: vector('ODI', 0),
                scale: get(this.paramName('SCALE', compassIndex), 0),
                motor: vector('MOT', 0)
            }
        },
        runFit (instance) {
            const input = this.compassInputs[instance]
            let result
            if (!input || input.error) {
                result = { ok: false, message: input ? input.error : 'No compass data' }
            } else {
                result = fitCalibration({
                    raw: input.raw,
                    roll: input.roll,
                    pitch: input.pitch,
                    yaw: input.yaw,
                    current: this.fitMotor ? input.current : null,
                    earthField: this.earthField,
                    fitType: this.fitType,
                    fitMotor: this.fitMotor,
                    yawSource: this.yawSource,
                    maxSamples: this.maxFitSamples
                })
            }
            // use $set so Vue detects the array index change (reactivity)
            this.$set(this.fits, instance, Object.freeze({
                ...result,
                fitType: this.fitType,
                fitMotor: this.fitMotor,
                yawSource: this.yawSource
            }))
            if (result.ok) {
                this.addFittedMessage(instance, result.cal)
                this.residualInstance = instance
            }
        },
        async runFits (instances) {
            // refuse to start a fit while one is running
            if (this.processing || !this.positionValid || !this.earthField) {
                return
            }
            this.processing = true
            try {
                for (const instance of instances) {
                    this.processingInstance = instance
                    // let the spinner render before the (synchronous) fit blocks the UI
                    await new Promise(resolve => setTimeout(resolve, 20))
                    this.runFit(instance)
                }
            } finally {
                this.processing = false
                this.processingInstance = null
            }
        },
        fitCompass (instance) {
            return this.runFits([instance])
        },
        fitAll () {
            return this.runFits([...this.compassInputs.keys()])
        },
        addFittedMessage (instance, cal) {
            // expose the re-calibrated field as a MAGFIT<n> message for plotting
            const input = this.compassInputs[instance]
            const corrected = applyCalibration(input.raw, cal, input.current)
            const messageName = 'MAGFIT' + instance
            this.state.messages[messageName] = {
                // eslint-disable-next-line camelcase
                time_boot_ms: input.time,
                MagX: corrected.x,
                MagY: corrected.y,
                MagZ: corrected.z
            }
            // drop plots of a previous fit
            for (const key of Object.keys(this.state.plotCache)) {
                if (key.includes(messageName)) {
                    this.$delete(this.state.plotCache, key)
                }
            }
            const newtype = {
                expressions: [
                    'MagX',
                    'MagY',
                    'MagZ'
                ],
                units: null,
                multipliers: null,
                complexFields: {
                    MagX: {
                        name: 'MagX',
                        units: 'mGauss',
                        multiplier: 1
                    },
                    MagY: {
                        name: 'MagY',
                        units: 'mGauss',
                        multiplier: 1
                    },
                    MagZ: {
                        name: 'MagZ',
                        units: 'mGauss',
                        multiplier: 1
                    }
                }
            }
            const availableMessages = this.state.messageTypes
            availableMessages[messageName] = newtype
            this.$eventHub.$emit('messageTypes', availableMessages)
        },
        isFitted (index) {
            return Boolean(this.fits[index]?.ok)
        },
        fitDescription (fit) {
            let description = FIT_TYPES[fit.fitType]
            if (fit.fitMotor) {
                description += ' + motor'
            }
            return description
        },
        formatScale (scale) {
            return scaleValid(scale) ? scale.toFixed(3) : 'unset'
        },
        formatError (error) {
            return error && Number.isFinite(error.rms) ? error.rms.toFixed(1) : '--'
        },
        formatComparison (index) {
            const comparison = this.errorComparison[index]
            if (!comparison) {
                return '--'
            }
            const format = v => Number.isFinite(v) ? v.toFixed(1) : '--'
            return `${format(comparison.before)} → ${format(comparison.after)}`
        },
        outOfRange (index, key) {
            return (this.rangeWarningsByCompass[index] || []).some(warning => warning.name === key)
        },
        headingDiffExpression (compass0, compass1) {
            // build an angle_diff() expression comparing the headings of two compasses
            const headingFunction = this.isTlog ? 'mag_heading' : 'mag_heading_df'
            const attitudeMessage = this.isTlog ? 'ATTITUDE' : 'ATT'
            const h0 = `${headingFunction}(${compass0}, ${attitudeMessage})`
            const h1 = `${headingFunction}(${compass1}, ${attitudeMessage})`
            return `abs(angle_diff(${h0}, ${h1}))`
        },
        plotOldHeadingDiff (i, j) {
            this.state.plotOn = true
            this.$nextTick(() => {
                const expression = this.headingDiffExpression(this.compassMessageNames[i], this.compassMessageNames[j])
                this.$eventHub.$emit('togglePlot', expression, 1)
            })
        },
        plotNewHeadingDiff (i, j) {
            this.state.plotOn = true
            this.$nextTick(() => {
                const expression = this.headingDiffExpression('MAGFIT' + i, 'MAGFIT' + j)
                this.$eventHub.$emit('togglePlot', expression, 1)
            })
        },
        fitnessClass (index) {
            // colour the post-fit error green/red depending on whether the fit
            // improved (lowered) the error compared to the original calibration
            const comparison = this.errorComparison[index]
            if (!comparison || !Number.isFinite(comparison.before) || !Number.isFinite(comparison.after)) {
                return ''
            }
            return comparison.after <= comparison.before ? 'fitness-better' : 'fitness-worse'
        }
    },
    computed: {
        GpsPosition () {
            const pos = Object.values(this.state.trajectories)[0]?.trajectory[0] ?? null
            if (pos === null) return null
            return {
                lon: pos[0],
                lat: pos[1]
            }
        },
        position () {
            return this.GpsPosition || this.userPosition
        },
        userPosition () {
            return {
                lat: parseFloat(this.userLat),
                lon: parseFloat(this.userLon)
            }
        },
        positionValid () {
            // a fit needs a location to compute the expected earth field. Either
            // the log has GPS, or the user must have entered valid lat/lon.
            if (this.GpsPosition) {
                return true
            }
            const lat = parseFloat(this.userLat)
            const lon = parseFloat(this.userLon)
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
                return false
            }
            if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
                return false
            }
            // treat the untouched (0, 0) default as "not entered yet"
            return !(lat === 0 && lon === 0)
        },
        earthField () {
            // NED earth field in mGauss, from the tables in mavextra.js
            if (!this.positionValid) {
                return null
            }
            const fieldVar = window.get_mag_field_ef(Number(this.position.lat), Number(this.position.lon))
            if (!fieldVar) {
                return null
            }
            let magEf = new Vector3(fieldVar[2] * 1000.0, 0.0, 0.0)
            const R = new Matrix3()
            R.fromEuler(0.0, -window.radians(fieldVar[1]), window.radians(fieldVar[0]))
            magEf = R.times(magEf)
            return [magEf.x, magEf.y, magEf.z]
        },
        printEarthField () {
            if (!this.earthField) {
                return '--'
            }
            return `( ${this.earthField[0].toFixed(0)}, ${this.earthField[1].toFixed(0)}, ` +
            ` ${this.earthField[2].toFixed(0)})`
        },
        isTlog () {
            return this.state.logType === 'tlog'
        },
        parameters () {
            // values at the end of the log rather than at the playback cursor
            return this.state.params?.lastValues ?? {}
        },
        newParamFormat () {
            return !('COMPASS_OFS_X' in this.parameters) && ('COMPASS1_OFS_X' in this.parameters)
        },
        motorCompType () {
            return this.parameters.COMPASS_MOTCT || 0
        },
        compassParams () {
            return this.compassData.map((message, index) => this.getCompassParams(index + 1))
        },
        compassInputs () {
            return this.compassData.map((message, index) => this.prepareCompass(message, index))
        },
        calibrationNotes () {
            // explain how the existing calibration was removed and what may be wrong with it
            const notes = []
            const inputs = this.compassInputs
            if (inputs.length === 0) {
                return notes
            }
            if (!this.state.params) {
                notes.push('No parameters in log: assuming the existing calibration has no offsets, ' +
                    'iron, scale or motor compensation unless logged per sample.')
            }
            if (inputs.every(input => input.loggedOffsets && input.loggedMotor)) {
                notes.push('Existing calibration removed per sample using the logged offsets (MAG.OfsX/Y/Z) ' +
                    'and motor compensation (MAG.MOX/Y/Z). Iron (DIA/ODI) and scale use the last values in the log.')
            } else if (!this.isTlog) {
                notes.push('Some MAG messages do not log the applied offsets or motor compensation, those are ' +
                    'removed using the last parameter values in the log. Iron (DIA/ODI) and scale also use the ' +
                    'last values in the log.')
            } else {
                notes.push('Telemetry log: compass messages do not include the applied calibration, so it is ' +
                    'removed using the last parameter values in the log (OFS, DIA, ODI, SCALE and, for current ' +
                    'based compensation, MOT). The fit is only valid if these were in use for the whole log.')
            }
            if (!this.attitude) {
                notes.push('No attitude messages in log, fitting is not possible.')
            }
            inputs.forEach((input, index) => {
                if (input.error) {
                    notes.push(`Compass ${index + 1}: ${input.error}.`)
                }
                if (!input.motorRemoved) {
                    notes.push(`Compass ${index + 1}: motor compensation (COMPASS_MOTCT ${this.motorCompType}) ` +
                        'could not be removed from this log, results may be biased.')
                }
            })
            if (this.state.params) {
                const changeable = this.isTlog ? null : ['DIA', 'ODI', 'SCALE']
                const changed = inputs.flatMap((input, index) => this.compassParamNames(index + 1))
                    .concat(this.isTlog ? ['COMPASS_MOTCT'] : [])
                    .filter(name => !changeable || changeable.some(base => name.includes(base)))
                    .filter(name => this.state.params.changedDuringLog(name))
                if (changed.length > 0) {
                    notes.push(`Changed during the log (last value used): ${changed.join(', ')}.`)
                }
            }
            return notes
        },
        preErrors () {
            // error of the logged (existing calibration) field
            if (!this.earthField) {
                return []
            }
            return this.compassInputs.map(input => calibrationError({
                corrected: input.logged,
                roll: input.roll,
                pitch: input.pitch,
                yaw: input.yaw,
                earthField: this.earthField,
                yawSource: this.yawSource
            }))
        },
        postErrors () {
            if (!this.earthField) {
                return []
            }
            return this.compassInputs.map((input, index) => {
                const fit = this.fits[index]
                if (!fit || !fit.ok) {
                    return null
                }
                return calibrationError({
                    corrected: applyCalibration(input.raw, fit.cal, input.current),
                    roll: input.roll,
                    pitch: input.pitch,
                    yaw: input.yaw,
                    earthField: this.earthField,
                    yawSource: this.yawSource
                })
            })
        },
        errorComparison () {
            // RMS error before and after over the samples where both are valid
            return this.postErrors.map((post, index) => {
                const pre = this.preErrors[index]
                if (!post || !pre) {
                    return null
                }
                let before = 0
                let after = 0
                let count = 0
                for (let i = 0; i < post.errors.length; i++) {
                    if (Number.isFinite(post.errors[i]) && Number.isFinite(pre.errors[i])) {
                        before += pre.errors[i] ** 2
                        after += post.errors[i] ** 2
                        count++
                    }
                }
                if (count === 0) {
                    return null
                }
                return { before: Math.sqrt(before / count), after: Math.sqrt(after / count) }
            })
        },
        fittedIndices () {
            return [...this.fits.keys()].filter(index => this.isFitted(index))
        },
        fitFailures () {
            const failures = []
            this.fits.forEach((fit, index) => {
                if (fit && !fit.ok) {
                    failures.push(`Compass ${index + 1}: ${fit.message}`)
                }
            })
            return failures
        },
        rangeWarningsByCompass () {
            return this.fits.map(fit => fit && fit.ok ? rangeWarnings(fit.cal) : [])
        },
        allRangeWarnings () {
            const warnings = []
            this.rangeWarningsByCompass.forEach((list, index) => {
                for (const warning of list) {
                    warnings.push(`${this.fullParamName(warning.name, index + 1)} ${warning.value.toFixed(3)} ` +
                        `outside typical range ${warning.range[0]} to ${warning.range[1]}`)
                }
            })
            return warnings
        },
        fitWarnings () {
            const warnings = []
            for (const index of this.fittedIndices) {
                const fit = this.fits[index]
                if (!fit.converged) {
                    warnings.push(`Compass ${index + 1}: fit stopped after ${fit.iterations} passes without ` +
                        'converging, the log may not have enough attitude variation to determine this calibration')
                }
            }
            return warnings.concat(this.allRangeWarnings)
        },
        residualPlot () {
            // per-sample field error of the existing and new calibration, bucket averaged
            const index = this.residualInstance
            const post = this.postErrors[index]
            const pre = this.preErrors[index]
            const input = this.compassInputs[index]
            if (index === null || !post || !pre || !input || input.time.length < 2) {
                return null
            }
            const buckets = 300
            const n = input.time.length
            const average = (errors, start, end) => {
                let sum = 0
                let count = 0
                for (let i = start; i < end; i++) {
                    if (Number.isFinite(errors[i])) {
                        sum += errors[i]
                        count++
                    }
                }
                return count > 0 ? sum / count : NaN
            }
            const before = []
            const after = []
            const times = []
            for (let b = 0; b < Math.min(buckets, n); b++) {
                const start = Math.floor(b * n / Math.min(buckets, n))
                const end = Math.max(start + 1, Math.floor((b + 1) * n / Math.min(buckets, n)))
                times.push(input.time[start])
                before.push(average(pre.errors, start, end))
                after.push(average(post.errors, start, end))
            }
            const finite = [...before, ...after].filter(Number.isFinite)
            if (finite.length === 0) {
                return null
            }
            const max = Math.max(...finite) || 1
            const t0 = input.time[0]
            const duration = (input.time[n - 1] - t0) || 1
            const pad = 3
            const w = this.chartWidth
            const h = this.chartHeight
            const toPoints = values => values.map((value, i) => {
                if (!Number.isFinite(value)) {
                    return null
                }
                const x = pad + ((times[i] - t0) / duration) * (w - 2 * pad)
                const y = pad + (1 - value / max) * (h - 2 * pad)
                return `${x.toFixed(1)},${y.toFixed(1)}`
            }).filter(point => point !== null).join(' ')
            return {
                before: toPoints(before),
                after: toPoints(after),
                max,
                duration: duration / 1000
            }
        }
    }
}
</script>

<style scoped>
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin: 0 0 8px 0;
      padding-left: 16px;
    }
    h5 {
      margin: 0;
      font-size: 14px;
      letter-spacing: 0.5px;
    }
    h6 {
      margin: 0 0 6px 0;
      padding-bottom: 3px;
      border-bottom: 1px solid #d2d6dc;
      font-size: 11px;
      letter-spacing: 0.5px;
      color: #2E3F54;
    }
    .close-btn {
      cursor: pointer;
      font-size: 18px;
      line-height: 1;
      padding: 0 4px;
      color: #6b7280;
    }
    .close-btn:hover {
      color: #b00;
    }
    div.section {
      border: 1px solid #d2d6dc;
      border-radius: 4px;
      width: fit-content;
      max-width: 100%;
      padding: 8px 10px;
      margin-bottom: 8px;
      box-sizing: border-box;
      background: rgba(255, 255, 255, 0.45);
    }
    table {
      border-collapse: collapse;
    }
    th, td {
      white-space: nowrap;
    }
    td {
      padding: 2px;
      padding-left: 6px;
    }
    table.results th,
    table.results td {
      padding: 3px 8px;
      text-align: right;
    }
    table.results th {
      border-bottom: 1px solid #d2d6dc;
      font-weight: 700;
      color: #4b5563;
    }
    table.results th:first-child,
    table.results td:first-child {
      text-align: center;
    }
    table.results td.actions {
      text-align: center;
      padding: 2px 3px;
    }
    .fitness-better {
      color: #1a7f37;
      font-weight: 700;
    }
    .fitness-worse {
      color: #b00;
      font-weight: 700;
    }
    .section-footer {
      margin-top: 6px;
    }
    .hint {
      color: #9a6700;
      font-style: italic;
    }
    .residual-chart {
      display: block;
      background: #f3f5f8;
      border: 1px solid #d2d6dc;
      border-radius: 3px;
    }
    .chart-caption {
      margin-top: 3px;
      color: #4b5563;
    }
    .legend-before {
      color: #7b8591;
    }
    .legend-after {
      color: #1a7f37;
    }
    .out-of-range {
      color: #b00;
      font-weight: 700;
    }
    ul.notes {
      margin: 6px 0 0 0;
      padding-left: 14px;
      max-width: 520px;
      white-space: normal;
      text-transform: none;
      font-weight: 400;
      color: #4b5563;
    }
    ul.notes.warnings {
      color: #b00;
    }
    button {
      white-space: nowrap;
      padding: 3px 8px;
      margin: 1px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      color: #fff;
      background: #2E3F54;
      border: none;
      border-radius: 3px;
      cursor: pointer;
      transition: background 0.15s ease;
    }
    button:hover:not(:disabled) {
      background: #3f5573;
    }
    button:disabled {
      background: #b8c0cc;
      cursor: not-allowed;
    }
    input[type="text"] {
      border: 1px solid #aab;
      border-radius: 3px;
      padding: 2px 5px;
      font-size: 11px;
    }
    input[type="text"]:disabled {
      background: #eef0f3;
      color: #555;
    }
    select {
      border: 1px solid #aab;
      border-radius: 3px;
      padding: 1px 3px;
      font-size: 11px;
      background: #fff;
      cursor: pointer;
    }
    .input {
      margin: 5px;
    }
    .data {
      display: block;
    }
    div #paneMagFitTool {
        padding: 10px;
        width: max-content;
        height: auto;
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

     div #paneMagFitTool::after {
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
        height: auto;
        overflow: visible;
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
