<template>
    <div :id="getDivName()"
         v-bind:style='{width:  width + "px", height: height + "px", top: top + "px", left: left + "px" }'>
        <div id='paneContent'>
            <span style="float: right; margin: 3px; cursor: pointer;" @click="close()"> X </span>
            <h5>Mag Fit Tool</h5>
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
              <tr>
                <td>Earth Field</td><td>{{ printEarthField }}</td>
              </tr>
            </table>
            </div>
            <div class="section">
              <h6>Compasses</h6>
              <table v-if="Object.keys(compassOffsets).length">
                  <tr>
                      <th>Compass</th>
                      <th>ofsx</th>
                      <th>ofsy</th>
                      <th>ofsz</th>
                      <th>scale</th>
                      <th>Fitness</th>
                  </tr>
                  <tr :key="'param' + index" v-for="(value, index) in compassOffsets">
                    <td> {{ index }} </td>
                      <td>{{ value.offsets.x.toFixed(2) }}</td>
                      <td>{{ value.offsets.y.toFixed(2) }}</td>
                      <td>{{ value.offsets.z.toFixed(2) }}</td>
                      <td>{{ value.scaling.toFixed(2) }}</td>
                      <td>{{ fitnessesPreCalibration[index].toFixed(0)}}</td>
                      <td><button v-on:click="fitWmm(index)"> Fit </button></td>
                      <td><button v-if="value?.offsets" @click="plotOldRaw(index)">Plot Raw</button></td>
                      <td><button v-if="value?.offsets" @click="plotOldHeading(index)">Plot Heading</button></td>

                  </tr>
              </table>
              <i v-else class="fas fa-spinner fa-spin">
              </i>
            </div>
            <div class="section" v-if="newCorrections.length > 0 || this.processing">
              <h6>New</h6>
              <table>
                  <tr>
                      <th>Compass</th>
                      <th>ofsx</th>
                      <th>ofsy</th>
                      <th>ofsz</th>
                      <th>scale</th>
                      <th>fitness</th>
                  </tr>
                  <tr :key="'param' + index" v-for="(value, index) in newCorrections">
                    <td> {{ index }} </td>
                      <td>{{ value?.offsets?.x?.toFixed(2) }}</td>
                      <td>{{ value?.offsets?.y?.toFixed(2) }}</td>
                      <td>{{ value?.offsets?.z?.toFixed(2) }}</td>
                      <td>{{ value?.scaling?.toFixed(2) }}</td>
                      <td>{{ fitnessesPostCalibration[index]?.toFixed(0) ?? '--'  }}</td>
                      <td><button v-if="value?.offsets" @click="plotRaw(index)">Plot Raw</button></td>
                      <td><button v-if="value?.offsets" @click="plotNewHeading(index)">Plot Heading</button></td>
                  </tr>
              </table>
              <i v-if="processing" class="fas fa-spinner fa-spin"></i>
              <button v-if="!processing" @click="downloadParams()"> Download Params file</button>
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

// eslint-disable-next-line
async function geneticOptimizer(f, xStart, bounds, { populationSize = 100, mutationRate = 0.01, maxGenerations = 100, mutationSize = 0.05 } = {}) {
    // eslint-disable-next-line
    let population = Array(populationSize - 1).fill().map(() => bounds.map(bound => Math.random() * (bound[1] - bound[0]) + bound[0]))
    population.push(xStart)

    for (let generation = 0; generation < maxGenerations; generation++) {
        const scores = population.map(f)
        const minScore = Math.min(...scores)
        const maxScore = Math.max(...scores)
        const fitness = scores.map(score => (maxScore - score) / (maxScore - minScore))
        const totalFitness = fitness.reduce((a, b) => a + b, 0)
        const probs = fitness.map(fit => fit / totalFitness)

        const newPopulation = []
        for (let i = 0; i < populationSize; i++) {
            const parents = await selectParentsAsync(population, probs)

            // Crossover
            const point = Math.floor(Math.random() * bounds.length)
            let child = [...parents[0].slice(0, point), ...parents[1].slice(point)]

            // Mutation
            child = child.map((val, index) => {
                if (Math.random() < mutationRate) {
                    const delta = (Math.random() - 0.5) * mutationSize * (bounds[index][1] - bounds[index][0])
                    return Math.min(Math.max(val + delta, bounds[index][0]), bounds[index][1])
                } else {
                    return val
                }
            })

            newPopulation.push(child)
        }

        population = newPopulation
        if (generation < maxGenerations - 1) {
            await sleep(10) // Introduce a delay between generations
        }
    }

    const bestIndex = population.map(f).reduce((iMax, x, i, arr) => x < arr[iMax] ? i : iMax, 0)
    return population[bestIndex]
}

function sleep (ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}

async function selectParentsAsync (population, probs) {
    const parents = []
    for (let j = 0; j < 2; j++) {
        const parent = await selectParentAsync(population, probs)
        parents.push(parent)
    }
    return parents
}

async function selectParentAsync (population, probs) {
    return new Promise((resolve) => {
        let r = Math.random()
        let index = 0
        while ((r -= probs[index]) > 0) index++
        resolve(population[index])
    })
}

export default {
    name: 'MagFitTool',
    mixins: [baseWidget],
    data () {
        return {
            name: 'MagFitTool',
            state: store,
            width: 471,
            height: 563,
            left: 432,
            top: 12,
            forceRecompute: 0,
            numberOfPoints: 1000, // TODO: expose this to the user
            newParamFormat: true,
            forceScale: false,
            maxOffset: 1000,
            maxScale: 1.01,
            minScale: 0.99,
            optimizingData: null,
            compassData: [],
            oldCorrections: [],
            newCorrections: [],
            processing: false,
            fitnesses: {},
            userLat: 0,
            userLon: 0
        }
    },
    methods: {
        downloadParams () {
            const params = []
            for (let [index, corr] of Object.entries(this.newCorrections)) {
                if (!corr) {
                    // filtering weird data coming though... we should switch to TS
                    continue
                }
                index = parseFloat(index)
                console.log(corr)
                params.push([this.paramName('OFS', index + 1) + '_X', corr.offsets.x])
                params.push([this.paramName('OFS', index + 1) + '_Y', corr.offsets.y])
                params.push([this.paramName('OFS', index + 1) + '_Z', corr.offsets.z])
                params.push([this.paramName('SCALE', index + 1), corr.scaling])
            }
            console.log(params)

            let content = ''
            content += `# Compass-fit params from file: ${this.state.file}\n`
            content += `# Date: ${new Date()}\n`

            const fileName = `${this.state.file}.params`

            for (const param of params) {
                // Calculate space between name and value to make it pretty
                content += `${param[0]}, ${param[1]}\n`
            }

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
        loadedMessages () {
            return Object.keys(this.state.messages)
        },
        waitForMessages (messages) {
            for (const message of messages) {
                this.$eventHub.$emit('loadType', message)
            }
            let interval
            const _this = this
            let counter = 0
            return new Promise((resolve, reject) => {
                interval = setInterval(function () {
                    for (const message of messages) {
                        if (!_this.loadedMessages().includes(message.split('[')[0])) {
                            counter += 1
                            if (counter > 10) { // 10 * 300ms = 3 s timeout
                                console.log('not resolving')
                                clearInterval(interval)
                                reject(new Error(`Could not load messageType ${message}`))
                            }
                            return
                        }
                    }
                    clearInterval(interval)
                    resolve()
                }, 300)
            })
        },
        loadRequiredData () {
            // sends loadType messages for all of the following tyoes:
            // this includes both dataflash and telemetry logs
            let requiredTypes = []
            if (this.state.logType === 'tlog') {
                requiredTypes = ['RAW_IMU', 'SCALED_IMU2', 'SCALED_IMU3', 'ATTITUDE']
            } else {
                requiredTypes = ['ATT', 'MAG', 'MAG2', 'MAG3']
            }
            this.waitForMessages(requiredTypes).finally(() => {
                this.computeData()
            }).catch((error) => {
                console.log(error)
            })
        },
        computeData () {
            this.compassData = this.getCompassData()
        },
        removeOffsets (data, offsets) {
            /* remove all corrections to get raw sensor data */
            let correctionMatrix = new Matrix3(
                new Vector3(offsets.diag.x, offsets.offdiag.x, offsets.offdiag.y),
                new Vector3(offsets.offdiag.x, offsets.diag.y, offsets.offdiag.z),
                new Vector3(offsets.offdiag.y, offsets.offdiag.z, offsets.diag.z)
            )
            try {
                correctionMatrix = correctionMatrix.invert()
            } catch (error) {
                console.log(error)
                return false
            }

            const newData = {
                magX: [],
                magY: [],
                magZ: [],
                time: []
            }
            const length = Object.values(data)[0].length
            for (let index = 0; index < length; index++) {
                let field = new Vector3(data.xmag[index], data.ymag[index], data.zmag[index])
                // console.log(field)
                field = correctionMatrix.times(field)
                // console.log(field)
                field.multiply(1.0 / offsets.scaling)
                field.subtract(offsets.offsets)
                newData.magX.push(field.x)
                newData.magY.push(field.y)
                newData.magZ.push(field.z)
                newData.time.push(data.time_boot_ms[index])
            }
            return newData
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
        getCompassParams (compassIndex) {
            console.log('getting compass params')
            const oldCorrections = {}
            if ('COMPASS_OFS_X' in this.parameters) {
                this.newParamFormat = false
            } else if ('COMPASS1_OFS_X' in this.parameters) {
                this.newParamFormat = true
            }
            oldCorrections.offsets = new Vector3(
                this.parameters[this.paramName('OFS', compassIndex) + '_X'] || 0.0,
                this.parameters[this.paramName('OFS', compassIndex) + '_Y'] || 0.0,
                this.parameters[this.paramName('OFS', compassIndex) + '_Z'] || 0.0
            )
            oldCorrections.diag = new Vector3(
                this.parameters[this.paramName('DIA', compassIndex) + '_X'] || 1.0,
                this.parameters[this.paramName('DIA', compassIndex) + '_Y'] || 1.0,
                this.parameters[this.paramName('DIA', compassIndex) + '_Z'] || 1.0
            )

            if (oldCorrections.diag.equals(new Vector3(0, 0, 0))) {
                oldCorrections.diag = new Vector3(1, 1, 1)
            }

            oldCorrections.offdiag = new Vector3(
                this.parameters[this.paramName('ODI', compassIndex) + '_X'] || 0.0,
                this.parameters[this.paramName('ODI', compassIndex) + '_Y'] || 0.0,
                this.parameters[this.paramName('ODI', compassIndex) + '_Z'] || 0.0
            )

            // oldCorrections.cmot_mode = this.parameters['COMPASS_MOTCT', CMOT_MODE_NONE)
            oldCorrections.cmot = new Vector3(
                this.parameters[this.paramName('MOT', compassIndex) + '_X'] || 0.0,
                this.parameters[this.paramName('MOT', compassIndex) + '_Y'] || 0.0,
                this.parameters[this.paramName('MOT', compassIndex) + '_Z'] || 0.0
            )

            oldCorrections.scaling = this.parameters[this.paramName('SCALE', compassIndex)] || null

            if (oldCorrections.scaling === null || oldCorrections.scaling < 0.1) {
                this.forceScale = false
                oldCorrections.scaling = 1.0
            } else {
                this.forceScale = true
            }
            return oldCorrections
        },

        getYaw (ATT, mag, corr) {
            /* calculate heading from raw magnetometer and new offsets */

            // Go via a DCM matrix to match the APM calculation
            mag = this.correct(mag, null, corr)
            // verified to match magfit_wmm.py
            const dcmMatrix = (new Matrix3()).fromEuler(
                window.radians(ATT.roll),
                window.radians(ATT.pitch),
                window.radians(ATT.yaw)
            )
            const cosPitchSq = 1.0 - (dcmMatrix.c.x * dcmMatrix.c.x)
            const headY = mag.y * dcmMatrix.c.z - mag.z * dcmMatrix.c.y
            const headX = mag.x * cosPitchSq - dcmMatrix.c.x * (mag.y * dcmMatrix.c.y + mag.z * dcmMatrix.c.z)

            let yaw = window.degrees(Math.atan2(-headY, headX)) + this.declination
            if (yaw < 0) {
                yaw += 360
            }
            return yaw
        },
        expectedField (ATT, yaw) {
            // return expected magnetic field for attitude

            const roll = ATT.roll
            const pitch = ATT.pitch

            const rot = new Matrix3()
            rot.fromEuler(window.radians(roll), window.radians(pitch), window.radians(yaw))

            const field = rot.transposed().times(this.earthField)

            return field
        },
        wmmErrorOnce (origdata, corrections) {
            const data = Object.assign({}, origdata)
            console.log(data, corrections)

            let ret = 0
            for (let i = 0; i < data.time.length; i++) {
                const MAG = {
                    x: data.magX[i],
                    y: data.magY[i],
                    z: data.magZ[i]
                }
                const ATT = {
                    roll: data.roll[i],
                    pitch: data.pitch[i],
                    yaw: data.yaw[i]
                }
                const BAT = null
                if (ATT.roll === undefined) {
                    console.log('skipping bad data', ATT)
                    continue
                }
                const yaw = this.getYaw(ATT, MAG, corrections) // matches
                // console.log('yaw: ', yaw)
                const expected = this.expectedField(ATT, yaw) // matches
                // console.log('expected: ', expected)
                const observed = this.correct(MAG, BAT, corrections) // matches
                // console.log('observed: ', observed)
                const error = expected.subtract(observed).length()
                ret += error
            }
            ret /= data.magX.length
            return ret
        },

        wmmError (corrections) {
            // console.log(corrections)
            const data = Object.assign({}, this.optimizingData)
            const corr = {}
            corr.offsets = new Vector3(corrections[0], corrections[1], corrections[2])
            corr.scaling = corrections[3]

            corr.diag = new Vector3(1.0, 1.0, 1.0)
            corr.offdiag = new Vector3(0.0, 0.0, 0.0)

            let ret = 0
            for (let i = 0; i < data.time.length; i++) {
                const MAG = {
                    x: data.magX[i],
                    y: data.magY[i],
                    z: data.magZ[i]
                }
                const ATT = {
                    roll: data.roll[i],
                    pitch: data.pitch[i],
                    yaw: data.yaw[i]
                }
                if (ATT.roll === undefined) {
                    console.log('skipping bad data', ATT)
                    continue
                }
                const BAT = null
                const yaw = this.getYaw(ATT, MAG, corr) // matches
                // console.log('yaw: ', yaw)
                const expected = this.expectedField(ATT, yaw) // matches
                // console.log('expected: ', expected)
                const observed = this.correct(MAG, BAT, corr) // matches
                // console.log('observed: ', observed)
                const error = expected.subtract(observed).length()
                ret += error
            }

            ret /= data.magX.length
            console.log(ret)
            return ret
        },

        correct (MAG, BAT, c) {
            // console.log('uncorrected mag: ', MAG)
            /* correct a mag sample, returning a Vector3 */
            let mag = new Vector3(MAG.x, MAG.y, MAG.z)
            // add the given offsets
            mag.add(c.offsets)
            // multiply by scale factor
            mag.multiply(c.scaling)
            // apply elliptical corrections
            const mat = new Matrix3(
                new Vector3(c.diag.x, c.offdiag.x, c.offdiag.y),
                new Vector3(c.offdiag.x, c.diag.y, c.offdiag.z),
                new Vector3(c.offdiag.y, c.offdiag.z, c.diag.z)
            )

            mag = mat.times(mag)
            // apply compassmot corrections
            // if (BAT !== null && BAT.Curr !== undefined && !isNaN(BAT.Curr)) {
            //     mag.add(c.cmot.multiply(BAT.Curr))
            // }
            // console.log('corrected mag: ', mag)
            return mag
        },
        async fitWmm (instance) {
            this.processing = true
            const data = this.compassDataAugmentedWithATT[instance]
            this.optimizingData = data
            this.oldCorrections = this.compassOffsets[instance]
            const corr = Object.assign({}, this.oldCorrections)
            const optimizationParams = [corr.offsets.x, corr.offsets.y, corr.offsets.z, corr.scaling]

            const ofs = this.maxOffset
            const bounds = [
                [-ofs, ofs],
                [-ofs, ofs],
                [-ofs, ofs],
                [this.minScale, this.maxScale]
            ]
            console.log(bounds)

            console.log('optimizing')
            const result = await geneticOptimizer(this.wmmError, optimizationParams, bounds)
            console.log('Optimization result: ', result)
            const c = Object.assign({}, this.oldCorrections)
            c.offsets = new Vector3(result[0], result[1], result[2])
            c.scaling = result[3]
            c.diag = new Vector3(1.0, 1.0, 1.0)
            c.offdiag = new Vector3(0.0, 0.0, 0.0)
            c.cmot = new Vector3(0.0, 0.0, 0.0)
            this.newCorrections[instance] = c
            // trigger reactivity
            this.$set(this.newCorrections, this.newCorrections, null)

            const newMessage = {
                // eslint-disable-next-line camelcase
                time_boot_ms: [],
                MagX: [],
                MagY: [],
                MagZ: []
            }
            for (const i in this.compassDataAugmentedWithATT[instance].time) {
                const msg = this.compassDataAugmentedWithATT[instance]
                newMessage.time_boot_ms.push(msg.time[i])
                const mag = this.correct(({
                    x: msg.magX[i],
                    y: msg.magY[i],
                    z: msg.magZ[i]
                }), null, c)
                newMessage.MagX.push(mag.x)
                newMessage.MagY.push(mag.y)
                newMessage.MagZ.push(mag.z)
            }
            this.state.messages['MAGFIT' + instance] = newMessage
            const newtype = {
                expressions: [
                    'MagX',
                    'MagY',
                    'MagZ'

                ],
                units: null,
                multipiers: null,
                complexFields: {
                    magX: {
                        name: 'MagX',
                        units: '?',
                        multiplier: 1
                    },
                    magY: {
                        name: 'MagY',
                        units: '?',
                        multiplier: 1
                    },
                    magZ: {
                        name: 'MagZ',
                        units: '?',
                        multiplier: 1
                    }
                }
            }
            const availableMessages = this.state.messageTypes
            availableMessages['MAGFIT' + instance] = newtype
            this.$eventHub.$emit('messageTypes', availableMessages)
            this.processing = false
            return c
        },
        getCompassData () {
            const data = []
            for (const message of [
                'RAW_IMU', 'SCALED_IMU2', 'SCALED_IMU3', 'MAG[0]', 'MAG[1]', 'MAG[2]', 'MAG', 'MAG2'
            ]) {
                if (this.state.messages[message]) {
                    data.push(this.state.messages[message])
                } else {
                    console.log('no message', message)
                }
            }
            return data
        }
    },
    computed: {
        fitnessesPreCalibration () {
            const ret = []
            for (const instance in this.compassDataAugmentedWithATT) {
                ret.push(this.wmmErrorOnce(this.compassDataAugmentedWithATT[instance], this.compassOffsets[instance]))
            }
            return ret
        },
        fitnessesPostCalibration () {
            return this.newCorrections.map((c, i) => {
                return this.wmmErrorOnce(this.compassDataAugmentedWithATT[i], c)
            })
        },
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
                lat: this.userLat,
                lon: this.userLon
            }
        },
        // next three come from mavextra.js
        intensity () {
            return window.interpolate_table(window.intensity_table, this.position.lat, this.position.lon)
        },
        declination () {
            return window.interpolate_table(window.declination_table, this.position.lat, this.position.lon)
        },
        inclination () {
            return window.interpolate_table(window.inclination_table, this.position.lat, this.position.lon)
        },
        earthField () {
            const fieldVar = window.get_mag_field_ef(this.position.lat, this.position.lon)
            let magEf = new Vector3(fieldVar[2] * 1000.0, 0.0, 0.0)
            const R = new Matrix3()
            R.fromEuler(0.0, -window.radians(fieldVar[1]), window.radians(fieldVar[0]))
            magEf = R.times(magEf)
            return magEf
            // This has been verified to match MAGFIT_WMM.py
        },
        printEarthField () {
            return `( ${this.earthField.x.toFixed(0)}, ${this.earthField.y.toFixed(0)}, ` +
            ` ${this.earthField.z.toFixed(0)})`
        },
        filteredCompassData () {
            // returns the compassData, but with the data filtered to only include the data that is used
            // that means we will only pass through the following fields:
            // TODO: add dataflash ones
            const wantedFields = ['time_boot_ms', 'xmag', 'ymag', 'zmag', 'MagX', 'MagY', 'MagZ']
            const filtered = []
            const nameMap = {
                xmag: 'xmag',
                ymag: 'ymag',
                zmag: 'zmag',
                MagX: 'xmag',
                MagY: 'ymag',
                MagZ: 'zmag',
                // eslint-disable-next-line camelcase
                time_boot_ms: 'time_boot_ms'
            }
            for (const message of this.compassData) {
                const filteredMessage = {}
                // for each key, value in message, filter it down:
                for (const [key, values] of Object.entries(message)) {
                    if (wantedFields.includes(key)) {
                        filteredMessage[nameMap[key]] = values
                    }
                }
                filtered.push(filteredMessage)
            }
            return filtered
        },
        sampledCompassData () {
            // returns this.compassData, but sampled down in a way that every array child of each message
            // has at most this.numberOfPoints
            const sampled = []
            for (const message of this.filteredCompassData) {
                const messageLength = Object.values(message)[0].length
                const sampleRate = Math.floor(messageLength / this.numberOfPoints) || 1
                const sampledMessage = {}
                // for each key, value in message, sample value down:
                for (const [key, values] of Object.entries(message)) {
                    const sampledValue = []
                    for (let i = 0; i < values.length; i += sampleRate) {
                        sampledValue.push(values[i])
                    }
                    sampledMessage[key] = sampledValue
                }
                sampled.push(sampledMessage)
            }
            return sampled
        },
        compassOffsets () {
            const offsets = []
            if (this.sampledCompassData.length === 0) {
                console.log('no compass data')
                return offsets
            }
            for (const compass in this.sampledCompassData) {
                offsets.push(this.getCompassParams(parseFloat(compass) + 1))
            }
            return offsets
        },
        compassDataRemovedOffsets () {
            // returns this.compassData, but with the offsets removed
            const data = []
            for (const [compass, message] of Object.entries(this.sampledCompassData)) {
                data.push(this.removeOffsets(message, this.compassOffsets[compass]))
            }
            return data
        },
        attitudeMessageName () {
            if ('ATT' in this.state.messages) {
                return 'ATT'
            }
            return 'ATTITUDE'
        },
        isTlog () {
            return this.state.logType === 'tlog'
        },
        compassMessageNames () {
            const names = []
            for (const message of ['RAW_IMU', 'SCALED_IMU2', 'SCALED_IMU3', 'MAG[0]', 'MAG[1]', 'MAG[2]']) {
                if (this.state.messages[message]) {
                    names.push(message)
                }
            }
            return names
        },
        attitudeMessages () {
            if ('ATT' in this.state.messages) {
                return this.state.messages.ATT
            }
            return this.state.messages.ATTITUDE
        },
        compassDataAugmentedWithATT () {
            // iterates on index of compassDataRemovedOffsets.time_boot_ms, finds the nearest ATT message
            // with the closes time_boot_ms, and adds that to the compassDataRemovedOffsets message
            return this.compassDataRemovedOffsets.map((message) => {
                const augmentedMessage = Object.assign({}, message)
                augmentedMessage.roll = []
                augmentedMessage.pitch = []
                augmentedMessage.yaw = []
                let attIndex = 0
                for (const time of message.time) {
                    while (this.attitudeMessages.time_boot_ms[attIndex] < time) {
                        attIndex++
                    }
                    if ('Roll' in this.attitudeMessages) {
                        augmentedMessage.roll.push(this.attitudeMessages.Roll[attIndex])
                        augmentedMessage.pitch.push(this.attitudeMessages.Pitch[attIndex])
                        augmentedMessage.yaw.push(this.attitudeMessages.Yaw[attIndex])
                    } else {
                        augmentedMessage.roll.push(this.attitudeMessages.roll[attIndex])
                        augmentedMessage.pitch.push(this.attitudeMessages.pitch[attIndex])
                        augmentedMessage.yaw.push(this.attitudeMessages.yaw[attIndex])
                    }
                }
                return augmentedMessage
            })
        },
        parameters () {
            return this.state.params.values
        }
    }
}
</script>

<style scoped>
    div.section {
      border: 1px solid #ccc;
      width: fit-content;
      padding: 5px;
    }
    td {
      padding: 2px;
      padding-left: 6px;
    }
    .input {
      margin: 5px;
    }
    .data {
      display: block;
    }
    div #paneMagFitTool {
        padding: 15px;
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

    div #paneMagFitTool::before {
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
