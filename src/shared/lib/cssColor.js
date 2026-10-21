import { formatHsl, hsl } from "culori";

// A darker version of a CSS color, for the flight-mode labels drawn over a band of that color:
// same hue and saturation, lightness lowered by `ratio` (0.2: 50% becomes 40%), as the `color`
// package's Color(css).darken(ratio) did. culori is also the library Plotly 4 reads colors with.
// A missing color counts as black.
export function darken(css, ratio) {
    const color = hsl(css ?? "black");
    return formatHsl({ ...color, l: color.l * (1 - ratio) });
}
