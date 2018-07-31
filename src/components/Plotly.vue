<template>
  <div>
    <div class="tile is-ancestor">
      <div class="tile is-parent is-4">
        <article class="tile is-child box">
          <h4 class="title">Line</h4>
          <div ref="line"></div>
        </article>
      </div>

    </div>
  </div>
</template>

<script>
import Plotly from 'plotly.js'
export default {
  created () {
    this.fetchData()
  },
  mounted () {
    Plotly.plot(
      this.$refs.line,
      [{
        x: [1, 2, 3, 4, 5],
        y: [1, 2, 4, 8, 16]
      }],
      {
        margin: { t: 0, l: 0, b: 0, r: 0 }
      }
    )
  },
  data () {
    return {
      rows: []
    }
  },
  methods: {
  }
}
</script>

<style scoped>
  .js-plotly-plot {
    max-width: 100%;
  }
</style>
