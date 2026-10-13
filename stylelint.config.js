// https://stylelint.io/user-guide/configure
// ids and classes are shared with templates and scripts (e.g. "pane" + name), so camelCase
// and snake_case names are fine too
const name = "^[a-z][a-zA-Z0-9]*(?:[-_][a-zA-Z0-9]+)*$";

export default {
    extends: ["stylelint-config-standard", "stylelint-config-recommended-vue"],
    rules: {
        "selector-id-pattern": name,
        "selector-class-pattern": name,
        // min-/max- media features: the range syntax needs Safari 16.4
        "media-feature-range-notation": "prefix",
        // It flags rules whose source order doesn't matter, because specificity already
        // decides between them; reordering these stylesheets could change cascades
        // between selectors of equal specificity.
        "no-descending-specificity": null,
    },
};
