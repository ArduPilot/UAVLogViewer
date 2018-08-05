<template>
  <div>
    <b-progress :max="100" height="20px" :value="percent" show-progress animated class="mb-3"></b-progress>
  </div>
</template>

<script>
export default {
  name: 'Progress',
  props: ['percent']
}
</script>

<style scoped>

</style>
