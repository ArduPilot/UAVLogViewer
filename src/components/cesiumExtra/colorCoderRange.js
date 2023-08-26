import { Color } from 'cesium'

export default class ColorCoderRange {
  requiredMessages = ['RFND']
  lastindex = 0 // lets track this so we are more efficient
  maxDist = 3
  constructor (state) {
      this.state = state
  }

  getLegend () {
      const legend = [
          {
              name: 'shallow',
              color: 'rgb(0, 0, 255)'
          },
          {
              name: 'deep',
              color: 'rgb(255, 0, 0)'
          }
      ]
      return legend
  }

  getMax () {
      this.maxDist = 0
      for (const dist of this.state.messages.RFND.Dist) {
          if (dist > this.maxDist) {
              this.maxDist = dist
          }
      }
  }

  getColor (time) {
      if (this.maxDist === 0) {
          this.getMax()
      }
      if (this.state.messages.RFND.time_boot_ms[this.lastindex] - time > 1000) {
          this.lastindex = 0
      }
      while (this.state.messages.RFND.time_boot_ms[this.lastindex] < time &&
        this.lastindex < this.state.messages.RFND.time_boot_ms.length - 1) {
          this.lastindex++
      }
      const color = this.state.messages.RFND.Dist[this.lastindex] / this.maxDist
      return new Color(1 - color, 0, color)
  }
}
