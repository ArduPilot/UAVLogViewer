<template>
  <div class="progress">
    <div class="progress-bar" role="progressbar" v-bind:style="widthstr" v-bind:aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100">{{percent}}%</div>
  </div>
</template>

<script>
export default {
  name: 'Progress',
  props: ['percent'],
  computed: {
    widthstr () {
      return 'width: ' + this.percent + '%;'
    }
  }
}
</script>

<style scoped>

</style>
