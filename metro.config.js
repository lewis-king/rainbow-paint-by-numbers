const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const projectRoot = __dirname;
const config = getDefaultConfig(projectRoot);

const defaultResolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  // Metro's classic web bundle cannot execute Zustand's ESM import.meta checks.
  // Use the package's equivalent CommonJS middleware entry on web.
  if (platform === 'web' && moduleName === 'zustand/middleware') {
    return { type: 'sourceFile', filePath: require.resolve('zustand/middleware') };
  }
  return defaultResolveRequest
    ? defaultResolveRequest(context, moduleName, platform)
    : context.resolveRequest(context, moduleName, platform);
};

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const rawAssetsPath = path.resolve(projectRoot, 'image-processing/raw_assets');
const rawAssetsPattern = new RegExp(`${escapeRegExp(rawAssetsPath)}[/\\\\].*`);
const currentBlockList = config.resolver.blockList ?? [];

config.resolver.blockList = Array.isArray(currentBlockList)
  ? [...currentBlockList, rawAssetsPattern]
  : [currentBlockList, rawAssetsPattern];

module.exports = config;
