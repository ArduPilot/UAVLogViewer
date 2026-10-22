<template>
    <div :id="[percent > 99 ? 'hideMe' : '']" class="progress1">
        <div class="progress" style="height: 30px">
            <div
                class="progress-bar"
                role="progressbar"
                :style="{ width: percent + '%' }"
                :aria-valuenow="percent"
                aria-valuemin="0"
                aria-valuemax="100"
            >
                <strong>{{
                    percent < 100 ? percent.toFixed(1) : complete
                }}</strong>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "Progress",
    props: {
        percent: { type: Number, required: true },
        complete: { type: String, default: "" },
    },
};
</script>

<style scoped>
.progress1 {
    margin: 20px;
}

strong {
    font-size: 150%;
}

.progress .progress-bar {
    background: rgb(0 50 168 / 63%);
    background: linear-gradient(
        0deg,
        rgb(30 37 53 / 100%) 51%,
        rgb(51 62 88 / 100%) 100%
    );
    transition: none;
}

#hideMe {
    animation: fade-out 5s ease-in 5s forwards;
    animation-fill-mode: forwards;
}

@keyframes fade-out {
    to {
        opacity: 0;
        overflow: hidden;
    }
}
</style>
