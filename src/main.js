// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from "vue";
import App from "./App.vue";
import router from "./router";

// Importing Bootstrap Vue
import BootstrapVue from "bootstrap-vue";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-vue/dist/bootstrap-vue.css";
// Icons bundled with the app (no CDN, works offline)
import "@fortawesome/fontawesome-free/css/all.css";

// Using imported components
import VueRouter from "vue-router";

Vue.use(VueRouter);
Vue.use(BootstrapVue);

Vue.config.productionTip = false;

Vue.prototype.$eventHub = new Vue(); // Global event bus

new Vue({
    router,
    components: { App },
    template: "<App/>",
}).$mount("#app");
