<template>
      <div id="line" ref="line" style="width:100%;height: 100%">{{ instruction }}</div>
</template>

<script>
import Plotly from 'plotly.js'

export default {
  created () {
    this.$eventHub.$on('animation-changed', this.setCursorState)
    this.$eventHub.$on('cesium-time-changed', this.setCursorTime)

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
    this.plot(this.plotData)
  },
  beforeDestroy () {
    window.removeEventListener('resize', this.getWindowWidth)
    window.removeEventListener('resize', this.getWindowHeight)
    this.$eventHub.$off('animation-changed')
    this.$eventHub.$off('cesium-time-changed')
  },
  data () {
    return {
      rows: [],
      gd: null,
      plotInstance: null,
      instruction: 'Click on a message type on the left panel to plot'
    }
  },
  methods: {
    resize () {
      Plotly.Plots.resize(this.gd)
    },
    plot (data) {
      let _this = this
      let fields = data[0].fieldnames.slice(1)
      let datasets = []
      for (let i = 0; i < fields.length; i++) {
        datasets.push({
          name: '' + fields[i],
          mode: 'lines',
          x: [],
          y: []
        })
      }

      for (let msg in data) {
        for (let field in fields) {
          datasets[field].x.push(data[msg].time_boot_ms)
          datasets[field].y.push(data[msg][fields[field]])
        }
      }
      let plotData = datasets
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
        shapes: [ {
          type: 'line',
          y0: 0,
          x0: data[0].time_boot_ms,
          yref: 'paper',
          y1: 1,
          x1: data[0].time_boot_ms,
          line: {
            color: 'rgb(0, 0, 0)',
            width: 2,
            dash: 'dot'
          }
        }]
      }
      console.log(plotData, plotOptions)

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
    },
    setCursorState (animationState)
    {
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
  props: ['plotData', 'cursorState'],
  watch: {
    plotData: function (newVal, oldVal) { // watch it
      this.instruction = ''
      this.plot(newVal)
    },

  }
}

</script>
<style>
  .js-plotly-plot {
    margin-left: 0!important;
  }
</style>
