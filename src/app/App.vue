<!-- mounted into index.html's #app -->
<template>
    <router-view />
</template>

<script>
export default {
    name: "App",
};
</script>

<style>
@import url("https://fonts.googleapis.com/css?family=Nunito+Sans&display=swap");

#app {
    height: 100%;
    font-family: "Nunito Sans", sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* the floating tool windows' scrolling content (components/widgets): a thin bar in their colour */
#paneContent {
    scrollbar-width: thin;
    scrollbar-color: rgb(38 53 71 / 60%) transparent;
}

html,
body {
    overscroll-behavior-y: contain;
}
</style>
