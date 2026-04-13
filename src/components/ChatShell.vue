<template>
    <div>
        <b-sidebar :visible="store.showChat" right shadow @hidden="onHide" id="chat-shell" width="420px">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h5 class="mb-0">Chat</h5>
                <b-button size="sm" variant="outline-light" @click="toggle">Close</b-button>
            </div>
            <ChatPanel />
        </b-sidebar>
        <b-button class="chat-fab" variant="primary" @click="toggle">Chat</b-button>
    </div>
</template>

<script>
import { store } from './Globals.js'
import ChatPanel from './ChatPanel.vue'

export default {
    name: 'ChatShell',
    components: { ChatPanel },
    data () {
        return { store }
    },
    methods: {
        toggle () { this.store.showChat = !this.store.showChat },
        onHide () { this.store.showChat = false }
    }
}
</script>

<style scoped>
.chat-fab {
    position: fixed;
    right: 16px;
    bottom: 16px;
    z-index: 1050;
}
</style>
