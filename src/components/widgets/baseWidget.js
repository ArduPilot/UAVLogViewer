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
            let pageX
            let pageY
            if (e.touches !== undefined) {
                pageX = e.touches[0].pageX
                pageY = e.touches[0].pageY
            } else {
                pageX = e.pageX
                pageY = e.pageY
            }
            const y = t + h - pageY
            const x = l + w - pageX
            const minWidth = 70
            const minHeight = 70

            const hasMoved = () =>
                !(t === this.offsetTop && l === this.offsetLeft)

            const hasResized = () =>
                !(w === this.offsetWidth && h === this.offsetHeight)

            const follow = (e) => {
                e.preventDefault()
                let pageX
                let pageY
                if (e.touches !== undefined) {
                    pageX = e.touches[0].pageX
                    pageY = e.touches[0].pageY
                } else {
                    pageX = e.pageX
                    pageY = e.pageY
                }
                // Set top/left of element according to mouse position
                _this.top = Math.max(0, Math.min(pageY + y - h, window.innerHeight - h))
                _this.left = Math.max(0, Math.min(pageX + x - w, window.innerWidth - w))
            }

            const resize = (e) => {
                e.preventDefault()
                if (e.touches !== undefined) {
                    pageX = e.touches[0].pageX
                    pageY = e.touches[0].pageY
                } else {
                    pageX = e.pageX
                    pageY = e.pageY
                }
                // Set width/height of element according to mouse position
                _this.width = Math.max(pageX - l + x, minWidth)
                _this.height = Math.max(pageY - t + y, minHeight)
            }

            const unresize = (e) => {
                // Remove listeners that were bound to document
                document.removeEventListener('mousemove', resize)
                document.removeEventListener('touchmove', resize)
                document.removeEventListener('mouseup', unresize)
                document.removeEventListener('touchend', unresize)
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
                document.removeEventListener('touchmove', follow)
                document.removeEventListener('touchend', unfollow)
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
                document.addEventListener('touchmove', follow, { passive: false })
                document.addEventListener('touchend', unfollow)
                // e.preventDefault()
            } else {
                document.addEventListener('mousemove', resize)
                document.addEventListener('mouseup', unresize)
                document.addEventListener('touchmove', resize, { passive: false })
                document.addEventListener('touchend', unresize)
                e.preventDefault()
            }
        }

        // Bind mutable to element mousedown
        $elem.addEventListener('mousedown', mutable)
        $elem.addEventListener('touchstart', mutable)
        // Listen for events from mutable element
        // $elem.addEventListener('clicked', (e) => $elem.innerHTML = 'clicked')
        // $elem.addEventListener('moved', (e) => $elem.innerHTML = 'moved')
        // $elem.addEventListener('resized', (e) => $elem.innerHTML = 'resized')
        this.setup()
        this.$eventHub.$on('paramsUpdated', function () {
            this.forceRecompute += 1
        }.bind(this))
    }
}
