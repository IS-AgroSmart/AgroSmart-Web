
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
var HtmlWebpackExcludeAssetsPlugin = require('html-webpack-exclude-assets-plugin');


module.exports = {
  devServer: {
    port: 8001,
    watchOptions: {
      poll: true
    },
    disableHostCheck: true
  },
  runtimeCompiler: true,
  configureWebpack: {
    //mode: 'production',
    //inject: false,
    plugins: [
      // BundleAnalyzer generates a report showing which packages add more size to the bundle
      // new BundleAnalyzerPlugin({analyzerMode: "static"}),
      // HtmlWebpackExcludeAssets will NOT include chunk-vendors.js on index.html
      new HtmlWebpackExcludeAssetsPlugin(),
    ]
  },
  chainWebpack: config => {
    config.plugin('html').tap(options => {
      // Configure HtmlWebpackExcludeAssets to ignore chunk-vendors.js (it's added manually and served by GitHack)
      //options[0].excludeAssets = /chunk-vendors.js/;
      return options;
    });
  },
}
