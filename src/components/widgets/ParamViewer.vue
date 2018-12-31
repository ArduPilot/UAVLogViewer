<template>
    <div id="paneParam" v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div id="panecontent">
            <input id="filterbox" v-model="filter" placeholder="Filter">
            <ul>
                <li v-for="param in filteredData"> {{ param }} : {{state.params.values[param]}}</li>
            </ul>
        </div>
    </div>
</template>

<script>
import {store} from '../Globals.js'

export default {
    name: 'ParamViewer',
    props: {'snappable': {type: Boolean, default: false}},
    data () {
        return {
            filter: '',
            state: store,
            throttle: 50,
            yaw: 50,
            pitch: 50,
            roll: 50,
            width: 264,
            height: 120,
            left: 750,
            top: 12
        }
    },
    methods: {
        waitForMessage (fieldname) {
            this.$eventHub.$emit('loadType', fieldname.split('.')[0])
            let interval
            let _this = this
            let counter = 0
            return new Promise((resolve, reject) => {
                interval = setInterval(function () {
                    if (_this.state.messages.hasOwnProperty(fieldname.split('.')[0])) {
                        clearInterval(interval)
                        counter += 1
                        resolve()
                    } else {
                        if (counter > 6) {
                            console.log('not resolving')
                            clearInterval(interval)
                            reject(new Error('Could not load messageType'))
                        }
                    }
                }, 2000)
            })
        }
    },
    computed: {
        filteredData () {
            return Object.keys(this.state.params.values).filter(key => key.indexOf(this.filter.toUpperCase()) !== -1)
        }
    },
    mounted () {
        const _this = this
        const $elem = document.getElementById('paneParam')
        const mutable = function (e) {
            // Elements initial width and height
            const h = this.offsetHeight
            const w = this.offsetWidth
            // Elements original position
            const t = this.offsetTop
            const l = this.offsetLeft
            // Click position within element
            const y = t + h - e.pageY
            const x = l + w - e.pageX
            const minWidth = 70
            const minHeight = 70

            const hasMoved = () =>
                !(t === this.offsetTop && l === this.offsetLeft)

            const hasResized = () =>
                !(w === this.offsetWidth && h === this.offsetHeight)

            const follow = (e) => {
                // Set top/left of element according to mouse position
                _this.top = Math.max(0, Math.min(e.pageY + y - h, window.innerHeight - h))
                _this.left = Math.max(0, Math.min(e.pageX + x - w, window.innerWidth - w))
            }

            const resize = (e) => {
                // Set width/height of element according to mouse position
                _this.width = Math.max(e.pageX - l + x, minWidth)
                _this.height = Math.max(e.pageY - t + y, minHeight)
            }

            const unresize = (e) => {
                // Remove listeners that were bound to document
                document.removeEventListener('mousemove', resize)
                document.removeEventListener('mouseup', unresize)
                // Emit events according to interaction
                if (hasResized(e)) {
                    this.dispatchEvent(new Event('resized'))
                } else {
                    this.dispatchEvent(new Event('clicked'))
                }
                e.preventDefault()
            }

            const unfollow = (e) => {
                // Remove listeners that were bound to document
                document.removeEventListener('mousemove', follow)
                document.removeEventListener('mouseup', unfollow)
                // Emit events according to interaction
                if (hasMoved(e)) {
                    this.dispatchEvent(new Event('moved'))
                } else {
                    this.dispatchEvent(new Event('clicked'))
                }
                e.preventDefault()
            }

            // Add follow listener if not resizing
            if (x > 12 && y > 12) {
                document.addEventListener('mousemove', follow)
                document.addEventListener('mouseup', unfollow)
                //e.preventDefault()
            } else {
                document.addEventListener('mousemove', resize)
                document.addEventListener('mouseup', unresize)
                e.preventDefault()
            }
        }

        // Bind mutable to element mousedown
        $elem.addEventListener('mousedown', mutable)
        // Listen for events from mutable element
        // $elem.addEventListener('clicked', (e) => $elem.innerHTML = 'clicked')
        // $elem.addEventListener('moved', (e) => $elem.innerHTML = 'moved')
        // $elem.addEventListener('resized', (e) => $elem.innerHTML = 'resized')

    }
}
</script>

<style scoped>
    div #paneParam {
        position: absolute;
        width: 100px;
        height: 100px;
        left: 20px;
        top: 20px;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.5);
        font-size: 10px;
        text-transform: uppercase;
        z-index: 10000;
        border-radius: 10px;
    }

    div #paneParam::before {
        content: '\2198';
        color: #fff;
        position: absolute;
        bottom: 0;
        right: 0;
        width: 20px;
        height: 20px;
        padding: 2px;
        padding-left: 5px;
        padding-bottom: 3px;
        background: #000;
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        border-radius: 5px;
    }

    div#paneContent {
        width:90%;height: 90%; overflow: auto;
    }

    input#filterbox {
        margin-left: 30px;
        background-color: rgba(255,255,255,0.5);
        border: 1px solid black;
        border-radius: 5px;
    }

</style>
