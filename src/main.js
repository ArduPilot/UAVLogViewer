import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { eventHub } from "./eventHub.js";
import "./styles/widget.css";

// Bootstrap 5 styles; the few components the app needs are in components/ui
import "bootstrap/dist/css/bootstrap.min.css";
import { collapseToggle } from "./components/ui/collapseToggle.js";
// Icons bundled with the app (no CDN, works offline)
import "@fortawesome/fontawesome-free/css/all.css";

const app = createApp(App);
app.use(router);
app.directive("collapse-toggle", collapseToggle);
app.config.globalProperties.$eventHub = eventHub;
app.mount("#app");
