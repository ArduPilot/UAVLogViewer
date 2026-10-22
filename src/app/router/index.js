import { createRouter, createWebHashHistory } from "vue-router";
import Layout from "@/app/Layout.vue";
import PlotlyPopup from "@/features/plot/components/PlotlyPopup.vue";

// hash URLs (/#/, /#/plot) as with Vue Router 3's default mode
export default createRouter({
    history: createWebHashHistory(),
    routes: [
        {
            path: "/",
            name: "Home",
            component: Layout,
        },
        {
            path: "/plot",
            name: "Plot",
            component: PlotlyPopup,
        },
        {
            path: "/v/:id",
            name: "View",
            component: Layout,
        },
    ],
});
