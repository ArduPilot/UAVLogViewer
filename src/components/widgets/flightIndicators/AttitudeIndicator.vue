<template>
    <div class="flight-indicator" :style="sizeStyle">
        <div class="roll indicator-box" :style="rollStyle">
            <img src="./img/horizon_back.svg" class="indicator-box" alt="" />
            <div class="pitch indicator-box" :style="pitchStyle">
                <img
                    src="./img/horizon_ball.svg"
                    class="indicator-box"
                    alt=""
                />
            </div>
            <img src="./img/horizon_circle.svg" class="indicator-box" alt="" />
        </div>
        <div class="mechanics indicator-box">
            <img
                src="./img/horizon_mechanics.svg"
                class="indicator-box"
                alt=""
            />
            <img src="./img/fi_circle.svg" class="indicator-box" alt="" />
        </div>
    </div>
</template>

<script>
// Attitude indicator (artificial horizon), adapted from the Attitude and Wrapper components of
// vue-flight-indicators 0.1.1 by Uğur Cibaroğlu, https://github.com/uCibar/vue-flight-indicators,
// licensed under the GNU GPL v3 like this app. That package only works with Vue 2.

const PITCH_BOUND = 30;

export default {
    name: "AttitudeIndicator",
    props: {
        size: { type: Number, default: 250 },
        // degrees
        roll: { type: Number, default: 0 },
        pitch: { type: Number, default: 0 },
    },
    computed: {
        sizeStyle() {
            return { width: this.size + "px", height: this.size + "px" };
        },
        rollStyle() {
            return { transform: "rotate(" + this.roll + "deg)" };
        },
        pitchStyle() {
            const pitch = Math.min(
                Math.max(this.pitch, -PITCH_BOUND),
                PITCH_BOUND,
            );
            return { top: pitch * 0.68 + "%" };
        },
    },
};
</script>

<style scoped>
.flight-indicator {
    position: relative;
    display: inline-block;
    overflow: hidden;
}

.indicator-box {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}
</style>
