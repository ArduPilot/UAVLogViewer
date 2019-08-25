import {store} from '../Globals.js'

export const baseWidget = {
    name: 'baseWidgetMixin',
    props: {
        'snappable': {type: Boolean, default: false},
        'fixedAspectRatio': {type: Boolean, default: false},
        'aspectRatio': {type: Number, default: 2}
    },
    data () {
        return {
            name: 'baseWidgetMixin',
            state: store,
            width: 264,
            height: 120,
            left: 780,
            top: 12
        }
    },
    methods: {
        getDivName () {
            console.log('pane' + this.name)
            return 'pane' + this.name
        }
    },
    mounted () {
        const _this = this
        const $elem = document.getElementById(this.getDivName())
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
                // e.preventDefault()
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
        this.$eventHub.$on('paramsUpdated', function () {
            this.forceRecompute += 1
        }.bind(this))
    }
}
