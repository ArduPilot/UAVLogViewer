module.exports = function babel(api) {
    api.cache(true);

    return {
        presets: [
            [
                "@babel/preset-env",
                {
                    modules: "auto",
                    targets: {
                        browsers: [
                            "> 1%",
                            "last 2 versions",
                            "not dead",
                            "not ie 11",
                        ],
                        node: "current",
                    },
                },
            ],
        ],
        plugins: ["@babel/plugin-syntax-dynamic-import"],
    };
};
