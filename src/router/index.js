import Vue from 'vue'
import Router from 'vue-router'
// import HelloWorld from '@/components/HelloWorld'
import Home from '../../src/components/Home.vue'

Vue.use(Router)

export default new Router({
    routes: [
        {
            path: '/v/:id/',
            name: 'Home',
            component: Home
        },
        {
            path: '/',
            name: 'Home',
            component: Home
        }

    ]
})
