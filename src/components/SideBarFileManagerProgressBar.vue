<template>
  <div class="progress1">
    <b-progress  height="30px" :max="100">
      <b-progress-bar :value="percent">
        <strong>{{ percent < 100 ? percent.toFixed(1): complete }}</strong>
      </b-progress-bar>
    </b-progress>
  </div>
</template>

<script>
export default {
  name: 'Progress',
  props: ['percent', 'complete']
}
</script>

<style scoped>
.progress1 {
  margin: 20px;
}
  strong {
    font-size: 150%;
  }

.progress .progress-bar {
  -webkit-transition: none;
  -o-transition: none;
  transition: none;
}

</style>
