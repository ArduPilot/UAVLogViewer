import { Color } from 'cesium'

export default class ColorCoderPlot {
  requiredMessages = []
  lastindex = 0 // lets track this so we are more efficient
  maxDist = 3
  stats = null
  constructor (state, key) {
      this.state = state
      this.key = key
  }

  computeStats (arr) {
      const n = arr.length
      if (n === 0) return { min: null, max: null, avg: null, std: null }

      let min = Infinity
      let max = -Infinity
      let sum = 0
      let sumOfSquares = 0

      for (let i = 0; i < n; i++) {
          const value = arr[i]
          if (!value) continue
          if (value < min) min = value
          if (value > max) max = value
          sum += value
          sumOfSquares += value * value
      }

      const avg = sum / n
      // Calculate variance as: (sumOfSquares/n) - avg^2
      // Then, standard deviation is the square root of variance
      const std = Math.sqrt((sumOfSquares / n) - avg * avg)
      return { min, max, avg, std }
  }

  getLegend () {
      const legend = [
          {
              name: 'high',
              color: 'rgb(0, 0, 255)'
          },
          {
              name: 'low',
              color: 'rgb(255, 255, 0)'
          }
      ]
      return legend
  }

  getMax () {
      return this.stats.avg + this.stats.std * 2
  }

  getColor (time) {
      if (!this.stats) {
          this.stats = this.computeStats(this.state.plotCache[this.key].y)
          console.log('stats', this.stats)
      }
      const data = this.state.plotCache[this.key]
      if (!this.timeRange) {
          this.timeRange = [data.x[0], data.x[data.x.length - 1]]
      }
      if (time < this.timeRange[0] || time > this.timeRange[1]) {
          return new Color(0, 0, 0)
      }
      if (time < data.x[this.lastindex] - 1000) {
          console.log(`t${time} < ${data.x[this.lastindex]}, [${this.lastindex}]resetting index`)
          this.lastindex = 0
      }
      console.log(this.lastindex)
      while (data.x[this.lastindex] < time &&
        this.lastindex < data.x.length - 1) {
          this.lastindex++
      }
      console.log(this.lastindex, data.y[this.lastindex])
      const value = data.y[this.lastindex]
      if (value === null) {
          return new Color(0, 0, 0)
      }
      // constrain new value between min/max, then map it to 0-255
      const color = (value - this.stats.min) / (this.stats.max - this.stats.min)
      return new Color(255 - color, 255 - color, color)
  }
}
