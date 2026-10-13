// Darkens a CSS rgb()/rgba() color the way the `color` package's Color(css).darken(ratio).string()
// did: the HSL lightness drops by `ratio`, and the result is an hsl()/hsla() string with every
// channel rounded to one decimal. A missing color counts as black, as it did there.
export function darken(css, ratio) {
    const [r = 0, g = 0, b = 0, alpha = 1] = (css?.match(/[\d.]+/g) ?? []).map(
        Number,
    );
    const [hue, s, l] = rgbToHsl(r, g, b);
    // the hue wraps into [0, 360) before rounding, as `color` did (360 becomes 0)
    const h = ((hue % 360) + 360) % 360;
    const round = (x) => Number(x.toFixed(1));
    const hsl = `${round(h)}, ${round(s)}%, ${round(l - l * ratio)}%`;
    return alpha === 1 ? `hsl(${hsl})` : `hsla(${hsl}, ${alpha})`;
}

// rgb 0-255 to [hue 0-360, saturation 0-100, lightness 0-100] (color-convert's rgb.hsl)
function rgbToHsl(red, green, blue) {
    const r = red / 255;
    const g = green / 255;
    const b = blue / 255;
    const min = Math.min(r, g, b);
    const max = Math.max(r, g, b);
    const delta = max - min;
    // a grey has no hue
    let h = 0;
    if (max !== min) {
        if (r === max) {
            h = (g - b) / delta;
        } else if (g === max) {
            h = 2 + (b - r) / delta;
        } else {
            h = 4 + (r - g) / delta;
        }
    }
    h = Math.min(h * 60, 360);
    if (h < 0) {
        h += 360;
    }
    const l = (min + max) / 2;
    let s = 0;
    if (max !== min) {
        s = l <= 0.5 ? delta / (max + min) : delta / (2 - max - min);
    }
    return [h, s * 100, l * 100];
}
