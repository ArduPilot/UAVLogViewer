import { Color } from 'cesium'

export default class ColorCoderRange {
  requiredMessages = ['RFND']
  lastindex = 0 // lets track this so we are more efficient
  maxDist = 3
  stats = null
  constructor (state) {
      this.state = state
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
              name: 'shallow',
              color: 'rgb(255, 0, 0)'
          },
          {
              name: 'deep',
              color: 'rgb(0, 0, 255)'
          }
      ]
      return legend
  }

  getMax () {
      return this.stats.avg + this.stats.std * 2
  }

  getColor (time) {
      if (!this.stats) {
          this.stats = this.computeStats(this.state.messages.RFND.Dist)
      }
      if (this.state.messages.RFND.time_boot_ms[this.lastindex] - time > 1000) {
          this.lastindex = 0
      }
      while (this.state.messages.RFND.time_boot_ms[this.lastindex] < time &&
        this.lastindex < this.state.messages.RFND.time_boot_ms.length - 1) {
          this.lastindex++
      }
      const maxDist = Math.min(this.stats.avg + this.stats.std * 3, this.stats.max)
      const color = Math.max(Math.min(this.state.messages.RFND.Dist[this.lastindex] / maxDist, 255), 0)
      return new Color(255 - color, 255 - color, color)
  }
}
