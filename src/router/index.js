import { createRouter, createWebHashHistory } from "vue-router";
import Home from "../components/Home.vue";
import PlotlyPopup from "../components/PlotlyPopup.vue";

// hash URLs (/#/, /#/plot) as with Vue Router 3's default mode
export default createRouter({
    history: createWebHashHistory(),
    routes: [
        {
            path: "/",
            name: "Home",
            component: Home,
        },
        {
            path: "/plot",
            name: "Plot",
            component: PlotlyPopup,
        },
        {
            path: "/v/:id",
            name: "View",
            component: Home,
        },
    ],
});
