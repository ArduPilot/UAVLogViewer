module.exports = function (api) {
    api.cache(true)

    return {
        'presets'
    :
        [
            [
                '@babel/preset-env',
                {
                    'modules': 'auto',
                    'targets': {
                        'browsers': ['> 1%', 'last 2 versions', 'not ie <= 8', 'ie >= 11'],
                        'node': 'current'
                    }
                }
            ]
        ],
            'plugins'
    :
        [
            '@babel/plugin-syntax-dynamic-import',
        ]
    }
}

