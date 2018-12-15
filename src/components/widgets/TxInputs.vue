<template>
    <div id="pane">
        <div id="title">Resize, Drag or Snap Me!</div>
    </div>
</template>

<script>
export default {
    name: 'TxInputs',
    props: {'snappable': {type: Boolean, default: false}},
    mounted () {
        const $elem = document.getElementById('pane')
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

            const hasMoved = () =>
                !(t === this.offsetTop && l === this.offsetLeft)

            const hasResized = () =>
                !(w === this.offsetWidth && h === this.offsetHeight)

            const follow = (e) => {
                // Set top/left of element according to mouse position
                this.style.top = `${e.pageY + y - h}px`
                this.style.left = `${e.pageX + x - w}px`
            }

            const resize = (e) => {
                // Set width/height of element according to mouse position
                this.style.width = `${(e.pageX - l + x)}px`
                this.style.height = `${(e.pageY - t + y)}px`
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
                e.preventDefault()
            } else {
                document.addEventListener('mousemove', resize)
                document.addEventListener('mouseup', unresize)
                e.preventDefault()
            }
        }

        // Bind mutable to element mousedown
        $elem.addEventListener('mousedown', mutable)
        // Listen for events from mutable element
        $elem.addEventListener('clicked', (e) => $elem.innerHTML = 'clicked')
        $elem.addEventListener('moved', (e) => $elem.innerHTML = 'moved')
        $elem.addEventListener('resized', (e) => $elem.innerHTML = 'resized')
    }
}
</script>

<style scoped>
    div #pane {
        position: absolute;
        width: 100px;
        height: 100px;
        left: 20px;
        top: 20px;
        overflow: auto;
        background: rgba(255, 255, 255, 0.5);
        font-size: 10px;
        text-transform: uppercase;
        z-index: 10000;
        border-radius: 10px;
    }

    div #pane::before {
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
</style>
