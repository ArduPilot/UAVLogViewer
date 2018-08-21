<template>
      <div id="line" ref="line" style="width:100%;height: 100%"></div>
</template>

<script>
import Plotly from 'plotly.js'

let plotOptions = {
  legend: {
    x: 0,
    y: 1,
    traceorder: 'normal',
    font: {
      color: '#FFF'
    },
    bgcolor: '#5b5b5b',
    bordercolor: '#FFFFFF',
    borderwidth: 2
  },
  plot_bgcolor: '#f8f8f8',
  paper_bgcolor: 'black',
  autosize: true,
  margin: { t: 0, l: 0, b: 20, r: 0 },
  xaxis: {
    rangeslider: {},
    autorange: true,
    titlefont: {
      color: '#fff'
    },
    tickfont: {
      color: '#fff'
    }
  },
  yaxis: {
    titlefont: {
      color: '#fff'
    },
    tickfont: {
      color: '#fff'
    }
  },
  shapes: [ { // plot cursor line
    type: 'line',
    y0: 0,
    x0: null,
    yref: 'paper',
    y1: 1,
    x1: null,
    line: {
      color: 'rgb(0, 0, 0)',
      width: 2,
      dash: 'dot'
    }
  }]
}
export default {
  created () {
    this.$eventHub.$on('animation-changed', this.setCursorState)
    this.$eventHub.$on('cesium-time-changed', this.setCursorTime)
    this.$eventHub.$on('addPlot', this.addPlot)
    this.$eventHub.$on('hidePlot', this.removePlot)
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
      this.resize()
    })
    this.instruction = ''
  },
  beforeDestroy () {
    window.removeEventListener('resize', this.resize)
    this.$eventHub.$off('animation-changed')
    this.$eventHub.$off('cesium-time-changed')
    this.$eventHub.$off('messages')
  },
  data () {
    return {
      gd: null,
      plotInstance: null,
      fields: []
    }
  },
  methods: {
    resize () {
      Plotly.Plots.resize(this.gd)
    },
    addPlot (fieldname) {
      if (!this.fields.includes(fieldname)) {
        this.fields.push(fieldname)
        this.plot()
      }
    },
    removePlot (fieldname) {
      var index = this.fields.indexOf(fieldname) // <-- Not supported in <IE9
      if (index !== -1) {
        this.fields.splice(index, 1)
      }
      this.plot()
      if (this.fields.length === 0) {
        this.$eventHub.$emit('plotEmpty')
      }
    },
    plot () {
      let _this = this
      let datasets = []

      for (let msgtype of Object.keys(this.alldata)) {
        for (let msgfield of this.alldata[msgtype][0].fieldnames) {
          if (this.fields.includes(msgtype + '.' + msgfield)) {
            let x = []
            let y = []
            for (let message of this.alldata[msgtype]) {
              x.push(message['time_boot_ms'])
              y.push(message[msgfield])
            }

            datasets.push({
              name: '' + msgfield,
              mode: 'lines',
              x: x,
              y: y
            })
          }
        }
      }

      let plotData = datasets
      if (plotOptions.shapes[0].x0 === null) {
        plotOptions.shapes[0].x0 = datasets[0].x[1]
        plotOptions.shapes[0].x1 = datasets[0].x[1]
      }

      if (this.plotInstance !== null) {
        plotOptions.xaxis = {range: this.gd._fullLayout.xaxis.range}
        // plotOptions.yaxis = {range: this.gd._fullLayout.yaxis.range}
        Plotly.newPlot(this.gd, plotData, plotOptions)
      } else {
        this.plotInstance = Plotly.newPlot(this.gd, plotData, plotOptions)
      }
      this.gd.on('plotly_hover', function (data) {
        let infotext = data.points.map(function (d) {
          return d.x
        })
        _this.$eventHub.$emit('hoveredTime', infotext[0])
        _this.setCursorTime(infotext[0])
      })
    },
    setCursorTime (time) {
      try {
        Plotly.relayout(this.gd, {
          'shapes[0].x0': time,
          'shapes[0].x1': time
        })
        let xrange = this.gd.layout.xaxis.range
        if (time < xrange[0] || time > xrange[1]) {
          let interval = xrange[1] - xrange[0]
          this.gd.layout.xaxis.range[0] = time - interval / 2
          this.gd.layout.xaxis.range[1] = time + interval / 2
        }
      } catch (err) {
        console.log(err)
      }
    },
    setCursorState (animationState) {
      let state = !animationState
      let stateStr
      if (state) {
        stateStr = 'x'
      } else {
        stateStr = false
      }
      Plotly.relayout(this.gd, {
        hovermode: stateStr
      })
    }
  },
  props: ['alldata']
}

</script>
<style>
  .js-plotly-plot {
    margin-left: 0!important;
  }
</style>
