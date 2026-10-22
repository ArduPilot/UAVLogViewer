// https://github.com/postcss/postcss-load-config (Vite reads it; it resolves @import and url() itself)

export default {
    plugins: {
        // vendor prefixes for the browsers in package.json's "browserslist"
        autoprefixer: {},
    },
};
