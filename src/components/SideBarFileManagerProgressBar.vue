<template>
    <div class="progress1" v-bind:id="[percent > 99 ? 'hideMe' : '']">
        <b-progress :max="100" height="30px">
            <b-progress-bar :value="percent">
                <strong>{{ percent < 100 ? percent.toFixed(1): complete }}</strong>
            </b-progress-bar>
        </b-progress>
    </div>
</template>

<script>
export default {
    name: 'Progress',
    props: ['percent', 'complete']
}
</script>

<style scoped>
    .progress1 {
        margin: 20px;
    }

    strong {
        font-size: 150%;
    }

    .progress .progress-bar {
        background: rgba(0, 50, 168, 0.63);
        background: linear-gradient(0deg, rgba(30,37,53,1) 51%, rgba(51,62,88,1) 100%);
        -webkit-transition: none;
        -o-transition: none;
        transition: none;
    }

    #hideMe {
        -moz-animation: cssAnimation 5s ease-in 5s forwards;
        /* Firefox */
        -webkit-animation: cssAnimation 5s ease-in 5s forwards;
        /* Safari and Chrome */
        -o-animation: cssAnimation 5s ease-in 5s forwards;
        /* Opera */
        animation: cssAnimation 5s ease-in 5s forwards;
        -webkit-animation-fill-mode: forwards;
        animation-fill-mode: forwards;
    }

    @keyframes cssAnimation {
        to {
            opacity: 0;
            overflow: hidden;
        }
    }

    @-webkit-keyframes cssAnimation {
        to {
            opacity: 0;
            height: 0;
        }
    }
</style>
