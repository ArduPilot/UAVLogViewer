require('@babel/register')
const config = require('../../config')

// http://nightwatchjs.org/gettingstarted#settings-file
module.exports = {
    src_folders: ['test/e2e/specs'],
    output_folder: 'test/e2e/reports',
    custom_assertions_path: ['test/e2e/custom-assertions'],
    selenium: {
        start_process: false,
        server_path: require('selenium-server').path,
        port: 4444,
        cli_args: {
            'webdriver.chrome.driver': require('chromedriver').path
        }
    },

    test_settings: {
        default: {
            selenium_port: 4444,
            selenium_host: 'localhost',
            silent: true,
            globals: {
                devServerURL: 'http://localhost:8080'
            }
        },
        chromeHeadless: {
            desiredCapabilities: {
                browserName: 'chromeHeadless',
                javascriptEnabled: true,
                acceptSslCerts: true,
                chromeOptions: {
                    args: [
                        'headless',
                        'disable-gpu',
                        'no-sandbox'
                    ]
                }
            }
        }
    }
}
