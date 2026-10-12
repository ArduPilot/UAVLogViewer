// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import { eventHub } from "./eventHub.js";

// Bootstrap 5 styles; the few components the app needs are in components/ui
import "bootstrap/dist/css/bootstrap.min.css";
import { collapseToggle } from "./components/ui/collapseToggle.js";
// Icons bundled with the app (no CDN, works offline)
import "@fortawesome/fontawesome-free/css/all.css";

// Using imported components
import VueRouter from "vue-router";

Vue.use(VueRouter);
Vue.directive("collapse-toggle", collapseToggle);

Vue.config.productionTip = false;

Vue.prototype.$eventHub = eventHub;

new Vue({
    router,
    components: { App },
    template: "<App/>",
}).$mount("#app");
