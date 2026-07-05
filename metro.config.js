const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const projectRoot = __dirname;
const config = getDefaultConfig(projectRoot);

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
