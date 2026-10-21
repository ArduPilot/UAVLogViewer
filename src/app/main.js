import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { eventHub } from "@/shared/lib/eventHub.js";
import { initLeapSeconds } from "@/shared/lib/datetools.js";
import "@/features/widgets/core/widget.css";

// Bootstrap 5 styles; the few components the app needs are in shared/ui
import "bootstrap/dist/css/bootstrap.min.css";
import { collapseToggle } from "@/shared/ui/collapseToggle.js";
// Icons bundled with the app (no CDN, works offline)
import "@fortawesome/fontawesome-free/css/all.css";

// Fetch leap-seconds.list before mounting so log parsing uses the
// runtime table. Falls back to the built-in one on failure, so the
// app always mounts.
await initLeapSeconds();

const app = createApp(App);
app.use(router);
app.directive("collapse-toggle", collapseToggle);
app.config.globalProperties.$eventHub = eventHub;
app.mount("#app");
