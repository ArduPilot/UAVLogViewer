<template>
    <div id="line" ref="line" style="width:100%;height: 100%"></div>
</template>

<script>
import Plotly from 'plotly.js'
import {store} from './Globals.js'

let timeformat = ':02,2f'
let plotOptions = {
    legend: {
        x: 0,
        y: -0.4,
        traceorder: 'normal',
        borderwidth: 1
    },
    plot_bgcolor: '#f8f8f8',
    paper_bgcolor: 'white',
    // autosize: true,
    margin: {t: 20, l: 0, b: 30, r: 10},
    xaxis: {
        title: 'Time since boot',
        domain: [0.15, 0.85],
        rangeslider: {},
        tickformat: timeformat
    },
    yaxis: {
        // title: 'axis1',
        titlefont: {
            color: '#1f77b4'
        },
        tickfont: {
            color: '#1f77b4'
        },
        anchor: 'free',
        position: 0.05
    },
    yaxis2: {
        // title: 'yaxis2 title',
        titlefont: {color: '#ff7f0e'},
        tickfont: {color: '#ff7f0e'},
        anchor: 'free',
        overlaying: 'y',
        side: 'left',
        position: 0.1
    },
    yaxis3: {
        // title: 'yaxis4 title',
        titlefont: {color: '#2ca02c'},
        tickfont: {color: '#2ca02c'},
        anchor: 'free',
        overlaying: 'y',
        side: 'left',
        position: 0.15
    },
    yaxis4: {
        // title: 'yaxis5 title',
        titlefont: {color: '#d62728'},
        tickfont: {color: '#d62728'},
        anchor: 'free',
        overlaying: 'y',
        side: 'left',
        position: 0.9
    },
    yaxis5: {
        // title: 'yaxis5 title',
        titlefont: {color: '#9467BD'},
        tickfont: {color: '#9467BD'},
        anchor: 'free',
        overlaying: 'y',
        side: 'left',
        position: 0.95
    },
    yaxis6: {
        // title: 'yaxis5 title',
        titlefont: {color: '#8C564B'},
        tickfont: {color: '#8C564B'},
        anchor: 'free',
        overlaying: 'y',
        side: 'left',
        position: 1.0
    }

}
/* eslint max-len: ["error", { "ignoreStrings": false }] */
Plotly.editable = true
Plotly.edits = {legendPosition: true}
export default {
    created () {
        this.$eventHub.$on('cesium-time-changed', this.setCursorTime)
        this.zoomInterval = null
    },
    mounted () {
        let d3 = Plotly.d3
        const WIDTH_IN_PERCENT_OF_PARENT = 90
        const gd3 = d3.select('#line')
            .append('div')
            .style({
                width: '100%',
                'margin-left': (100 - WIDTH_IN_PERCENT_OF_PARENT) / 2 + '%',
                height: '100%'
            })

        this.gd = gd3.node()
        let _this = this
        this.$nextTick(function () {
            window.addEventListener('resize', _this.resize)
            _this.resize()
            if (this.$route.query.hasOwnProperty('ranges')) {
                let ranges = []
                for (let field of this.$route.query.ranges.split(',')) {
                    ranges.push(parseFloat(field))
                }
                if (ranges.length > 0) {
                    plotOptions.xaxis.range = [ranges[0], ranges[1]]
                }
                if (ranges.length >= 4) {
                    plotOptions.yaxis.range = [ranges[2], ranges[3]]
                }
                if (ranges.length >= 6) {
                    plotOptions.yaxis2.range = [ranges[4], ranges[5]]
                }
                if (ranges.length >= 8) {
                    plotOptions.yaxis3.range = [ranges[6], ranges[7]]
                }
                if (ranges.length >= 10) {
                    plotOptions.yaxis4.range = [ranges[8], ranges[9]]
                }
            }
            if (this.$route.query.hasOwnProperty('plots')) {
                for (let field of this.$route.query.plots.split(',')) {
                    _this.addPlot(field)
                }
            }
        })
        this.instruction = ''
        this.$eventHub.$on('togglePlot', this.togglePlot)
        this.$eventHub.$on('clearPlot', this.clearPlot)
    },
    beforeDestroy () {
        window.removeEventListener('resize', this.resize)
        this.$eventHub.$off('animation-changed')
        this.$eventHub.$off('cesium-time-changed')
        this.$eventHub.$off('addPlot')
        this.$eventHub.$off('hidePlot')
        this.$eventHub.$off('togglePlot')
        clearInterval(this.interval)
    },
    data () {
        return {
            gd: null,
            plotInstance: null,
            state: store
        }
    },
    methods: {
        resize () {
            Plotly.Plots.resize(this.gd)
        },
        waitForMessage (fieldname) {
            this.$eventHub.$emit('loadType', fieldname.split('.')[0])
            let interval
            let _this = this
            let counter = 0
            return new Promise((resolve, reject) => {
                interval = setInterval(function () {
                    if (_this.state.messages.hasOwnProperty(fieldname.split('.')[0])) {
                        clearInterval(interval)
                        counter += 1
                        resolve()
                    } else {
                        if (counter > 6) {
                            console.log('not resolving')
                            clearInterval(interval)
                            reject(new Error('Could not load messageType'))
                        }
                    }
                }, 2000)
            })
        },
        onRangeChanged (event) {
            let query = Object.create(this.$route.query) // clone it
            query['plots'] = this.state.fields.join(',')
            let list = [
                this.gd._fullLayout.xaxis.range[0].toFixed(0),
                this.gd._fullLayout.xaxis.range[1].toFixed(0)
            ]
            this.state.xrange = list
            if (this.gd._fullLayout.yaxis !== undefined) {
                list.push(this.gd._fullLayout.yaxis.range[0].toFixed(0))
                list.push(this.gd._fullLayout.yaxis.range[1].toFixed(0))
            }
            if (this.gd._fullLayout.yaxis2 !== undefined) {
                list.push(this.gd._fullLayout.yaxis2.range[0].toFixed(0))
                list.push(this.gd._fullLayout.yaxis2.range[1].toFixed(0))
            }
            if (this.gd._fullLayout.yaxis3 !== undefined) {
                list.push(this.gd._fullLayout.yaxis3.range[0].toFixed(0))
                list.push(this.gd._fullLayout.yaxis3.range[1].toFixed(0))
            }
            if (this.gd._fullLayout.yaxis4 !== undefined) {
                list.push(this.gd._fullLayout.yaxis4.range[0].toFixed(0))
                list.push(this.gd._fullLayout.yaxis4.range[1].toFixed(0))
            }
            query['ranges'] = list.join(',')

            // this.$router.push({query: query})
            // if (event.hasOwnProperty('xaxis.range')) {
            //     this.$eventHub.$emit('rangeChanged', event['xaxis.range'])
            // }
            // if (event.hasOwnProperty('xaxis.range[0]')) {
            //     this.$eventHub.$emit('rangeChanged', [event['xaxis.range[0]'], event['xaxis.range[1]']])
            // }
            if (event !== undefined) {
                // this.$router.push({query: query})
                if (event.hasOwnProperty('xaxis.range')) {
                    this.state.timeRange = event['xaxis.range']
                }
                if (event.hasOwnProperty('xaxis.range[0]')) {
                    this.state.timeRange = [event['xaxis.range[0]'], event['xaxis.range[1]']]
                }
            }
        },
        isPlotted (fieldname) {
            for (let field of this.state.fields) {
                if (field.name === fieldname) {
                    return true
                }
            }
            return false
        },
        getFirstFreeAxis () {
            // get free axis number
            for (let i of this.state.allAxis) {
                let taken = false
                for (let field of this.state.fields) {
                    if (field.axis == i) {
                        taken = true
                    }
                }
                if (!taken) {
                    return i
                }
            }
            return this.state.allAxis.length - 1
        },
        getFirstFreeColor () {
            // get free color
            for (let i of this.state.allColors) {
                let taken = false
                for (let field of this.state.fields) {
                    console.log(field.color + '==' + i + ' =' + (field.color == i))
                    if (field.color == i) {
                        taken = true
                    }
                }
                if (!taken) {
                    return i
                }
            }
            return this.state.allColors[this.state.allColors.length - 1]
        },
        createNewField (fieldname) {
            return {
                name: fieldname,
                color: this.getFirstFreeColor(),
                axis: this.getFirstFreeAxis()
            }
        },

        addPlot (fieldname) {
            // ensure we have the data
            this.state.plot_loading = true
            if (!this.state.messages.hasOwnProperty(fieldname.split('.')[0])) {
                console.log('missing message type: ' + fieldname.split('.')[0])
                this.waitForMessage(fieldname).then(function () {
                    this.addPlot(fieldname)
                    console.log('got message ' + fieldname)
                }.bind(this))
            } else {
                if (!this.isPlotted(fieldname)) {
                    this.state.fields.push(this.createNewField(fieldname))
                }
                this.plot()
                this.state.plot_loading = false
                if (this.state.fields.length === 1) {
                    Plotly.relayout(this.gd, {
                        xaxis: {
                            range: this.timeRange,
                            domain: [0.15, 0.85],
                            rangeslider: {},
                            title: 'time_boot (ms)'
                        }
                    })
                    this.addModeShapes()
                }
            }
        },
        removePlot (fieldname) {
            var index = this.state.fields.indexOf(fieldname) // <-- Not supported in <IE9
            if (index !== -1) {
                this.state.fields = this.state.fields.splice(index, 1)
            }
            this.plot()
            if (this.state.fields.length === 0) {
                this.state.plot_on = false
            }
            this.onRangeChanged()
        },
        clearPlot () {
            while (this.state.fields.length) {
                this.state.fields.pop()
            }
            this.state.fields.lenght = 0
        },
        togglePlot (fieldname) {
            if (this.isPlotted((fieldname))) {
                let index
                for (let i in this.state.fields) {
                    if (this.state.fields[i].name === fieldname) {
                        index = i
                    }
                }
                this.state.fields.splice(index, 1)
                if (this.state.fields.length === 0) {
                    this.state.plot_on = false
                }
                this.onRangeChanged()
            } else {
                this.addPlot(fieldname)
            }
            console.log(this.state.fields)
            this.plot()
        },
        calculateXAxisDomain () {
            let start = 0.02
            let end = 0.98
            for (let field of this.state.fields) {
                if (field.axis === 0) {
                    start = Math.max(start, 0.06)
                } else if (field.axis === 1) {
                    start = Math.max(start, 0.11)
                } else if (field.axis === 2) {
                    start = Math.max(start, 0.16)
                } else if (field.axis === 5) {
                    end = Math.min(end, 0.94)
                } else if (field.axis === 4) {
                    end = Math.min(end, 0.89)
                } else if (field.axis === 3) {
                    end = Math.min(end, 0.84)
                }
            }
            return [start, end]
        },
        getAxisTitle (fieldAxis) {
            let names = []
            for (let field of this.state.fields) {
                if (field.axis === fieldAxis) {
                    names.push(field.name.split('.')[1])
                }
            }
            return names.join(', ')
        },
        plot () {
            let _this = this
            let datasets = []

            for (let field of this.state.fields) {
                let msgtype = field.name.split('.')[0]
                let msgfield = field.name.split('.')[1]
                if (!(msgtype in this.state.messages) || this.state.messages[msgtype].length === 0) {
                    console.log('ERROR: attempted to plot unavailable message: ' + msgtype)
                    return
                }
                if (('' + this.state.messageTypes[msgtype].fields).indexOf(msgfield) === -1) {
                    console.log('ERROR: Attempt to plot invalid field ' + msgfield + ' of ' + msgtype)
                    console.log('available options ' + this.state.messageTypes[msgtype].fields)
                    return
                }

                let x = []
                let y = []
                for (let message of this.state.messages[msgtype]) {
                    x.push(message['time_boot_ms'])
                    y.push(message[msgfield])
                }
                datasets.push({
                    name: msgtype + '.' + msgfield,
                    mode: 'scattergl',
                    x: x,
                    y: y,
                    yaxis: 'y' + (field.axis + 1),
                    line: {
                        color: field.color
                    }
                })
                let axisname = field.axis > 0 ? ('yaxis' + (field.axis + 1)) : 'yaxis'
                console.log(axisname)

                if (field.axis <= 6) {
                    plotOptions[axisname].title = {
                        text: this.getAxisTitle(field.axis),
                        font: {
                            color: field.color
                        }
                    }
                    plotOptions[axisname].tickfont.color = field.color
                    console.log(this.state.messageTypes[msgtype].complexFields[msgfield])
                    if (this.state.messageTypes[msgtype].complexFields[msgfield].units !== '?') {
                        plotOptions[axisname].title.text += ' (' + this.state.messageTypes[msgtype].complexFields[msgfield].units + ')'
                    }
                }
            }

            let plotData = datasets

            if (this.plotInstance !== null) {
                plotOptions.xaxis = {
                    rangeslider: {},
                    range: this.gd._fullLayout.xaxis.range,
                    domain: this.calculateXAxisDomain(),
                    title: 'time_boot (ms)',
                    tickformat: ':04,2f'
                }
                Plotly.newPlot(this.gd, plotData, plotOptions, {scrollZoom: true})
            } else {
                this.plotInstance = Plotly.newPlot(this.gd, plotData, plotOptions, {scrollZoom: true})
            }
            this.gd.on('plotly_relayout', this.onRangeChanged)
            this.gd.on('plotly_hover', function (data) {
                let infotext = data.points.map(function (d) {
                    return d.x
                })
                _this.$eventHub.$emit('hoveredTime', infotext[0])
            })
            let bglayer = document.getElementsByClassName('bglayer')[0]
            let rect = bglayer.childNodes[0]
            console.log(rect)
            this.cursor = document.createElementNS('http://www.w3.org/2000/svg', 'line')
            let x = rect.getAttribute('x')
            let y = rect.getAttribute('y')
            let y2 = parseInt(y) + parseInt(rect.getAttribute('height'))
            this.cursor.setAttribute('id', 'batata')
            this.cursor.setAttribute('x1', x)
            this.cursor.setAttribute('y1', y)
            this.cursor.setAttribute('x2', x)
            this.cursor.setAttribute('y2', y2)
            this.cursor.setAttribute('stroke-width', 1)
            this.cursor.setAttribute('stroke', 'black')
            bglayer.append(this.cursor)
        },
        setCursorTime (time) {
            try {
                let bglayer = document.getElementsByClassName('bglayer')[0]
                let rect = bglayer.childNodes[0]
                let x = parseInt(rect.getAttribute('x'))
                let width = parseInt(rect.getAttribute('width'))
                let percTime = (time - this.gd.layout.xaxis.range[0]) / (this.gd.layout.xaxis.range[1] - this.gd.layout.xaxis.range[0])
                let newx = x + width * percTime
                this.cursor.setAttribute('x1', newx)
                this.cursor.setAttribute('x2', newx)
            } catch (err) {
                console.log(err)
            }
        },
        getMode (time) {
            for (let mode in this.state.flight_mode_changes) {
                if (this.state.flight_mode_changes[mode][0] > time) {
                    if (mode - 1 < 0) {
                        return this.state.flight_mode_changes[0][1]
                    }
                    return this.state.flight_mode_changes[mode - 1][1]
                }
            }
            return this.state.flight_mode_changes[this.state.flight_mode_changes.length - 1][1]
        },
        getModeColor (time) {
            return this.state.cssColors[this.setOfModes.indexOf(this.getMode(time))]
        },
        addModeShapes () {
            let shapes = []
            let modeChanges = this.state.flight_mode_changes
            modeChanges.push([this.gd.layout.xaxis.range[1], null])

            for (let i = 0; i < modeChanges.length - 1; i++) {
                console.log(i)
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
                        opacity: 0.2,
                        line: {
                            width: 0
                        }
                    }
                )
            }
            Plotly.relayout(this.gd, {
                shapes: shapes
            })
        }
    },
    computed: {
        setOfModes () {
            let set = []
            for (let mode of this.state.flight_mode_changes) {
                if (!set.includes(mode[1])) {
                    set.push(mode[1])
                }
            }
            return set
        },
        timeRange () {
            if (this.state.timeRange != null) {
                return this.state.timeRange
            }
        },
        fields () {
            return this.state.fields
        }
    },
    watch: {
        timeRange (range) {
            if (Math.abs(this.gd.layout.xaxis.range[0] - range[0]) > 5 ||
                    Math.abs(this.gd.layout.xaxis.range[1] - range[1]) > 5) {
                if (this.zoomInterval !== null) {
                    clearTimeout(this.zoomInterval)
                }
                this.zoomInterval = setTimeout(function () {
                    Plotly.relayout(this.gd, {
                        xaxis: {
                            title: 'Time since boot',
                            range: range,
                            domain: [0.15, 0.85],
                            rangeslider: {},
                            tickformat: timeformat
                        }
                    })
                }.bind(this), 500)
            }
        },
        fields: {
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
</style>
