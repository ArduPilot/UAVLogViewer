<template>
    <div id="app" style="height: 100%;">
        <router-view/>
    </div>
</template>

<script>
export default {
    name: 'App'
}
</script>

<style>

@import url('https://fonts.googleapis.com/css?family=Nunito+Sans&display=swap');

 #app {
    font-family: 'Nunito Sans', sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
 }

 html,
body {
    overscroll-behavior-y: contain;
}

</style>
