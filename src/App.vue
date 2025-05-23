<template>
    <div id="app" style="height: 100%;">
        <router-view />
        <ChatbotComponent />
    </div>
</template>

<script>
// Chat Bot Component starts here
import ChatbotComponent from './components/Chatbot.vue'

export default {
    name: 'App',
    components: {
        ChatbotComponent
    }
}
</script>

<style>
    /* Existing global styles */
    @import url('https://fonts.googleapis.com/css?family=Nunito+Sans&display=swap');

    #app {
        font-family: 'Nunito Sans', sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    html,
    body {
        overscroll-behavior-y: contain;
        margin: 0;
        padding: 0;
    }
</style>
