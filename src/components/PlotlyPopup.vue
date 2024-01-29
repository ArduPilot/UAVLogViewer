<template>
   <div id='vuewrapper' style="height: 100%;">
    <div id="line" ref="line" style="width:100%;height: 100%"></div>
  </div>
</template>

<script>
import Plotly from 'plotly.js'
import { store } from './Globals.js'
import * as d3 from 'd3'

const Color = require('color')

const timeformat = ':02,2f'
let annotationsEvents = []
const annotationsModes = []
let annotationsParams = []

const updatemenus = [
    {
        active: 0,
        buttons: [
            {
                args: ['annotations', annotationsModes],
                label: 'Nothing',
                method: 'relayout'
            },
            {
                args: ['annotations', [...annotationsEvents, ...annotationsModes]],
                label: 'Events',
                method: 'relayout'
            },
            {
                args: ['annotations', [...annotationsEvents, ...annotationsModes, ...annotationsParams]],
                label: 'Events + Params',
                method: 'relayout'
            }
        ],
        direction: 'left',
        pad: { r: 10, t: 10 },
        showactive: true,
        type: 'buttons',
        x: 0.1,
        xanchor: 'left',
        y: 1.2,
        yanchor: 'top'
    }
]

export default {
    name: 'PlotlyPopup',
    created () {
        this.zoomInterval = null
        this.cache = {}
    },
    mounted () {
        console.log('mounted')
        console.log(this.$route.path)
        window.plot = () => { this.plot() }
        window.setPlotData = (data) => { this.plotData = data }
        window.setPlotOptions = (options) => { this.plotOptions = options }
        window.setFlightModeChanges = (modes) => { this.flightModeChanges = modes }
        window.setCssColors = (colors) => { this.cssColors = colors }
        window.setTimeRange = (timeRange) => { this.setTimeRange(timeRange) }
        window.setEventHub = (eventHub) => {
            this.$eventHub = eventHub
            this.$eventHub.$on('cesium-time-changed', this.setCursorTime)
            this.$eventHub.$on('hoveredTime', this.setCursorTime)
            this.$eventHub.$on('child-zoomed', this.setTimeRange)
            this.$eventHub.$on('force-resize-plotly', this.resize)
        }
        const WIDTH_IN_PERCENT_OF_PARENT = 90
        d3.select('#line')
            .append('div')
            .style({
                width: '100%',
                'margin-left': (100 - WIDTH_IN_PERCENT_OF_PARENT) / 2 + '%',
                height: '100%'
            })

        this.gd = d3.select('#line').node()
    },
    beforeDestroy () {
        this.$eventHub.$off('animation-changed')
        this.$eventHub.$off('cesium-time-changed')
        clearInterval(this.interval)
    },
    data () {
        return {
            gd: null,
            plotInstance: null,
            state: store,
            plotData: [],
            plotOptions: {},
            flightModeChanges: [],
            externalTimeRange: null,
            $eventHub: null,
            cursor: null
        }
    },
    methods: {
        setTimeRange (timeRange) {
            this.externalTimeRange = timeRange
        },
        csvButton () {
            return {
                name: 'downloadCsv',
                title: 'Download data as csv',
                icon: Plotly.Icons.disk,
                click: () => {
                    console.log(this.gd.data)
                    const data = this.gd.data
                    const header = ['timestamp(ms)']
                    for (const series of data) {
                        header.push(series.name.split(' |')[0])
                    }

                    const indexes = []

                    const interval = 100
                    let lasttime = Infinity
                    let finaltime = 0

                    for (const series in data) {
                        indexes.push(0)
                        const x = data[series].x
                        lasttime = Math.min(lasttime, x[0])
                        finaltime = Math.max(finaltime, x[x.length - 1])
                    }
                    finaltime = Math.min(finaltime, this.state.timeRange[1])
                    lasttime = Math.max(lasttime, this.state.timeRange[0])

                    const csv = [header]
                    while (lasttime < finaltime - interval) {
                        const line = [lasttime]
                        for (const series in data) {
                            let index = indexes[series]
                            let x = data[series].x[index]
                            while (x < lasttime) {
                                indexes[series] += 1
                                index = indexes[series]
                                x = data[series].x[index]
                            }
                            line.push(data[series].y[index])
                        }
                        csv.push(line)
                        lasttime = lasttime + interval
                    }
                    const csvContent = csv.map(e => e.join(',')).join('\n')
                    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
                    const link = document.createElement('a')
                    const url = URL.createObjectURL(blob)
                    link.setAttribute('href', url)
                    link.setAttribute('download', 'data.csv')
                    link.style.visibility = 'hidden'
                    document.body.appendChild(link)
                    link.click()
                    document.body.removeChild(link)
                }
            }
        },
        resize () {
            Plotly.Plots.resize(this.gd)
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
                        if (!_this.loadedMessages.includes(message)) {
                            counter += 1
                            if (counter > 30) { // 30 * 300ms = 9 s timeout
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
        onRangeChanged (event) {
            this.addMaxMinMeanToTitles()
            if (event !== undefined) {
                // this.$router.push({query: query})
                if (event['xaxis.range']) {
                    this.setTimeRange(event['xaxis.range'])
                    this.$eventHub.$emit('child-zoomed', this.timeRange)
                }
                if (event['xaxis.range[0]']) {
                    this.setTimeRange([event['xaxis.range[0]'], event['xaxis.range[1]']])
                    this.$eventHub.$emit('child-zoomed', this.timeRange)
                }
                if (event['xaxis.autorange']) {
                    this.setTimeRange([this.gd.layout.xaxis.range[0], this.gd.layout.xaxis.range[1]])
                    this.$eventHub.$emit('child-zoomed', this.timeRange)
                }
            }
        },
        addMaxMinMeanToTitles   () {
            const average = arr => arr.reduce((p, c) => p + c, 0) / arr.length
            const gd = this.gd
            const xRange = gd.layout.xaxis.range

            let needsRelayout = false

            gd.data.forEach(trace => {
                const len = Math.min(trace.x.length, trace.y.length)
                const xInside = []
                const yInside = []

                for (let i = 0; i < len; i++) {
                    const x = trace.x[i]
                    const y = trace.y[i]

                    if (x > xRange[0] && x < xRange[1]) {
                        xInside.push(x)
                        yInside.push(y)
                    }
                }
                const extraData = ` | Min: ${Math.min(...yInside).toFixed(2)} \
    Max: ${Math.max(...yInside).toFixed(2)} \
    Mean: ${average(yInside).toFixed(2)}`

                if (trace.name.indexOf(extraData) === -1) {
                    trace.name = trace.name.split(' | ')[0] + extraData
                    needsRelayout = true
                }
            })
            if (needsRelayout) {
                Plotly.relayout(this.gd, this.gd.layout)
            }
        },

        plot () {
            console.log('plot()')
            const start = new Date()
            delete this.plotOptions.xaxis.rangeslider
            if (this.plotInstance !== null) {
                this.plotOptions.xaxis.range = this.gd._fullLayout.xaxis.range
                Plotly.newPlot(this.gd, this.plotData, this.plotOptions, { scrollZoom: true, responsive: true })
            } else {
                this.plotInstance = Plotly.newPlot(
                    this.gd,
                    this.plotData,
                    this.plotOptions,
                    {
                        modeBarButtonsToAdd: [this.csvButton()],
                        scrollZoom: true,
                        editable: true,
                        responsive: true
                    }
                )
            }
            console.log('plotting done in ' + (new Date() - start) + 'ms')
            this.gd.on('plotly_relayout', this.onRangeChanged)
            this.gd.on('plotly_hover', (data) => {
                const infotext = data.points.map(function (d) {
                    return d.x
                })
                this.$eventHub.$emit('hoveredTime', infotext[0])
                this.setCursorTime(infotext[0])
            })

            this.addModeShapes()
            this.addEvents()
            // this.addParamChanges()

            this.state.plotLoading = false

            const bglayer = document.getElementsByClassName('bglayer')[0]
            const rect = bglayer.childNodes[0]
            this.cursor = document.createElementNS('http://www.w3.org/2000/svg', 'line')
            const x = rect.getAttribute('x')
            const y = rect.getAttribute('y')
            const y2 = parseInt(y) + parseInt(rect.getAttribute('height'))
            this.cursor.setAttribute('id', 'batata')
            this.cursor.setAttribute('x1', x)
            this.cursor.setAttribute('y1', y)
            this.cursor.setAttribute('x2', x)
            this.cursor.setAttribute('y2', y2)
            this.cursor.setAttribute('stroke-width', 1)
            this.cursor.setAttribute('stroke', 'black')
            bglayer.append(this.cursor)
            console.log('layout done in ' + (new Date() - start) + 'ms')
        },
        setCursorTime (time) {
            try {
                const bglayer = document.getElementsByClassName('bglayer')[0]
                const rect = bglayer.childNodes[0]
                const x = parseInt(rect.getAttribute('x'))
                const width = parseInt(rect.getAttribute('width'))
                const percTime = (time - this.gd.layout.xaxis.range[0]) /
                    (this.gd.layout.xaxis.range[1] - this.gd.layout.xaxis.range[0])
                const newx = x + width * percTime
                this.cursor.setAttribute('x1', newx)
                this.cursor.setAttribute('x2', newx)
            } catch (err) {
                console.log(err)
            }
        },
        getMode (time) {
            for (const mode in this.flightModeChanges) {
                if (this.flightModeChanges[mode][0] > time) {
                    if (mode - 1 < 0) {
                        return this.flightModeChanges[0][1]
                    }
                    return this.flightModeChanges[mode - 1][1]
                }
            }
            return this.flightModeChanges[this.flightModeChanges.length - 1][1]
        },
        getModeColor (time) {
            return this.cssColors[this.setOfModes.indexOf(this.getMode(time))]
        },
        darker (color) {
            return Color(color).darken(0.2).string()
        },
        addModeShapes () {
            const shapes = []
            const modeChanges = [...this.flightModeChanges]
            modeChanges.push([this.gd.layout.xaxis.range[1], null])

            for (let i = 0; i < modeChanges.length - 1; i++) {
                shapes.push(
                    {
                        type: 'rect',
                        // x-reference is assigned to the x-values
                        xref: 'x',
                        // y-reference is assigned to the plot paper [0,1]
                        yref: 'paper',
                        x0: modeChanges[i][0],
                        y0: 0,
                        x1: modeChanges[i + 1][0],
                        y1: 1,
                        fillcolor: this.getModeColor(modeChanges[i][0] + 1),
                        opacity: 0.15,
                        line: {
                            width: 0
                        }
                    }
                )
            }
            Plotly.relayout(this.gd, {
                shapes: shapes
            })
        },
        calculateXAxisDomain () {
            let start = 0.02
            let end = 0.98
            for (const field of this.state.expressions) {
                if (field.axis === 0) {
                    start = Math.max(start, 0.03)
                } else if (field.axis === 1) {
                    start = Math.max(start, 0.07)
                } else if (field.axis === 2) {
                    start = Math.max(start, 0.11)
                } else if (field.axis === 5) {
                    end = Math.min(end, 0.96)
                } else if (field.axis === 4) {
                    end = Math.min(end, 0.92)
                } else if (field.axis === 3) {
                    end = Math.min(end, 0.88)
                }
            }
            return [start, end]
        },
        addEvents () {
            annotationsEvents = []
            let i = -300
            for (const event of this.state.events) {
                annotationsEvents.push(
                    {
                        xref: 'x',
                        yref: 'paper',
                        x: event[0],
                        y: 0,
                        yanchor: 'bottom',
                        text: event[1].toLowerCase(),
                        showarrow: true,
                        arrowwidth: 1,
                        arrowcolor: '#999999',
                        ay: i,
                        ax: 0
                    }
                )
                i += 23
                if (i > 0) {
                    i = -300
                }
            }
            const modeChanges = [...this.flightModeChanges]
            modeChanges.push([this.gd.layout.xaxis.range[1], null])
            for (let i = 0; i < modeChanges.length - 1; i++) {
                annotationsModes.push(
                    {
                        xref: 'x',
                        // y-reference is assigned to the plot paper [0,1]
                        yref: 'paper',
                        x: modeChanges[i][0],
                        xanchor: 'left',
                        y: 0,
                        textangle: 90,
                        text: '<b>' + modeChanges[i][1] + '</b>',
                        showarrow: false,
                        font: {
                            color: this.darker(this.getModeColor(modeChanges[i][0] + 1))
                        },
                        opacity: 1
                    }
                )
            }
            Plotly.relayout(this.gd, {
                annotations: annotationsModes,
                updatemenus: updatemenus
            })
            updatemenus[0].buttons[0].args = ['annotations', annotationsModes]
            updatemenus[0].buttons[1].args = ['annotations', [...annotationsEvents, ...annotationsModes]]
            updatemenus[0].buttons[2].args = ['annotations', [...annotationsEvents, ...annotationsModes,
                ...annotationsParams]]
        },
        addParamChanges () {
            let i = -300
            annotationsParams = []
            const firstFetch = new Set()
            let startAt = null
            for (const change of this.changeArray) {
                if (!firstFetch.has(change[1])) {
                    firstFetch.add(change[1])
                } else {
                    startAt = change[0]
                    break
                }
            }
            let last = [0, 0]
            for (const change of this.changeArray) {
                if (change[0] < startAt) {
                    continue
                }
                // This takes care of repeated param changed logs we get for some reason
                if (change[2] === last[2] && change[1] === last[1]) {
                    continue
                }
                // Filter some "noisy" parameters
                if (['STAT_FLTTIME', 'STAT_RUNTIME'].includes(change[1])) {
                    continue
                }
                last = change
                annotationsParams.push(
                    {
                        xref: 'x',
                        yref: 'paper',
                        x: change[0],
                        y: 0,
                        yanchor: 'bottom',
                        text: change[1] + '->' + change[2].toFixed(4),
                        showarrow: true,
                        arrowwidth: 1,
                        arrowcolor: '#999999',
                        ay: i,
                        ax: 0
                    }
                )
                i += 23
                if (i > 0) {
                    i = -300
                }
            }
            updatemenus[0].active = 0
            Plotly.relayout(this.gd, {
                annotations:
                [
                    ...annotationsModes
                ],
                updatemenus: updatemenus
            })
            updatemenus[0].buttons[2].args =
            [
                'annotations',
                [
                    ...annotationsEvents,
                    ...annotationsModes,
                    ...annotationsParams
                ]
            ]
        }
    },
    computed: {
        setOfModes () {
            const set = []
            for (const mode of this.flightModeChanges) {
                if (!set.includes(mode[1])) {
                    set.push(mode[1])
                }
            }
            return set
        },
        timeRange () {
            if (this.externalTimeRange != null) {
                return this.externalTimeRange
            }
            return undefined
        },
        expressions () {
            return this.state.expressions
        },
        loadedMessages () {
            return Object.keys(this.state.messages)
        },
        messagesInLog () {
            return Object.keys(this.state.messageTypes)
        }
    },
    watch: {
        timeRange (range) {
            console.log('timeRange', range)

            if (this.zoomInterval !== null) {
                clearTimeout(this.zoomInterval)
            }
            this.zoomInterval = setTimeout(() => {
                Plotly.relayout(this.gd, {
                    xaxis: {
                        title: 'Time since boot',
                        range: range,
                        domain: this.calculateXAxisDomain(),
                        tickformat: timeformat
                    }
                })
            }, 500)
            return range // make linter happy, it says this is a computed property(?)
        },
        expressions: {
            deep: true,
            handler () {
                this.plot()
            }
        }
    }
}

</script>
<style>
    .js-plotly-plot {
        margin-left: 0 !important;
    }

    .shapelayer path {
        pointer-events: none !important;
    }
</style>
