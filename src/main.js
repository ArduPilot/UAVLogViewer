// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import App from './App.vue'
import router from './router'

// Import Cesium and set ion access token
import { Ion } from 'cesium'

// Importing Bootstrap Vue
import BootstrapVue from 'bootstrap-vue'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import { library } from '@fortawesome/fontawesome-svg-core'
import { faPaperPlane } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

// Using imported components
import VueRouter from 'vue-router'

Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJjNDBlOGYxMi1hZGYyLTRmYzEtYmExZi03NWY4NmU' +
'zMTYyZmYiLCJpZCI6MzEyNzUxLCJpYXQiOjE3NTAxMDA3Mzh9.RfTzyX171HiRh85SzfwUj_psOfyxCJO8x2YY--PuFwk'

library.add(faPaperPlane)
Vue.component('font-awesome-icon', FontAwesomeIcon)
Vue.use(VueRouter)
Vue.use(BootstrapVue)

Vue.config.productionTip = false

Vue.prototype.$eventHub = new Vue() // Global event bus

/* eslint-disable no-new */
new Vue({
    el: '#app',
    router,
    components: { App },
    template: '<App/>'
})
