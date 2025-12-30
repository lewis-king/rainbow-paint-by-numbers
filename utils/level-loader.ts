import { Asset } from 'expo-asset';
import type { LevelData } from '@/types/level';

export interface LevelAssets {
  data: LevelData;
  originalUri: string;
  linesUri: string;
  mapUri: string;
  rewardUri?: string;
}

/**
 * Level Registry
 *
 * To add a new level:
 * 1. Add folder to assets/images/levels/{id}/
 * 2. Include: data.json, original.png, lines.png, map.png, reward.mp4
 * 3. Add the ID to this array:
 */
const LEVEL_IDS = ['1', '2', '3', '4', '5', '6'] as const;

// Metro requires static imports - this maps IDs to their assets
// Each level must have these files in assets/images/levels/{id}/
const levelRegistry: Record<string, {
  data: LevelData;
  original: number;
  lines: number;
  map: number;
  reward?: number;
}> = {
  '1': {
    data: require('@/assets/images/levels/1/data.json'),
    original: require('@/assets/images/levels/1/original.png'),
    lines: require('@/assets/images/levels/1/lines.png'),
    map: require('@/assets/images/levels/1/map.png'),
    reward: require('@/assets/images/levels/1/reward.mp4'),
  },
  '2': {
    data: require('@/assets/images/levels/2/data.json'),
    original: require('@/assets/images/levels/2/original.png'),
    lines: require('@/assets/images/levels/2/lines.png'),
    map: require('@/assets/images/levels/2/map.png'),
    reward: require('@/assets/images/levels/2/reward.mp4'),
  },
  '3': {
    data: require('@/assets/images/levels/3/data.json'),
    original: require('@/assets/images/levels/3/original.png'),
    lines: require('@/assets/images/levels/3/lines.png'),
    map: require('@/assets/images/levels/3/map.png'),
    reward: require('@/assets/images/levels/3/reward.mp4'),
  },
  '4': {
    data: require('@/assets/images/levels/4/data.json'),
    original: require('@/assets/images/levels/4/original.png'),
    lines: require('@/assets/images/levels/4/lines.png'),
    map: require('@/assets/images/levels/4/map.png'),
    reward: require('@/assets/images/levels/4/reward.mp4'),
  },
  '5': {
    data: require('@/assets/images/levels/5/data.json'),
    original: require('@/assets/images/levels/5/original.png'),
    lines: require('@/assets/images/levels/5/lines.png'),
    map: require('@/assets/images/levels/5/map.png'),
    reward: require('@/assets/images/levels/5/reward.mp4'),
  },
  '6': {
    data: require('@/assets/images/levels/6/data.json'),
    original: require('@/assets/images/levels/6/original.png'),
    lines: require('@/assets/images/levels/6/lines.png'),
    map: require('@/assets/images/levels/6/map.png'),
    reward: require('@/assets/images/levels/6/reward.mp4'),
  },
};

export { LEVEL_IDS };

export interface LevelPreview {
  id: string;
  thumbnailSource: number;
  originalSource: number;
  title: string;
}

export function getLevelPreviews(): LevelPreview[] {
  return LEVEL_IDS
    .filter(id => levelRegistry[id]) // Only include registered levels
    .map((id) => ({
      id,
      thumbnailSource: levelRegistry[id].lines,
      originalSource: levelRegistry[id].original,
      title: `Level ${id}`,
    }));
}

export async function loadLevelAssets(levelId: string): Promise<LevelAssets | null> {
  const assets = levelRegistry[levelId];
  if (!assets) return null;

  const [originalAsset, linesAsset, mapAsset, rewardAsset] = await Promise.all([
    Asset.fromModule(assets.original).downloadAsync(),
    Asset.fromModule(assets.lines).downloadAsync(),
    Asset.fromModule(assets.map).downloadAsync(),
    assets.reward ? Asset.fromModule(assets.reward).downloadAsync() : Promise.resolve(null),
  ]);

  return {
    data: assets.data,
    originalUri: originalAsset.localUri!,
    linesUri: linesAsset.localUri!,
    mapUri: mapAsset.localUri!,
    rewardUri: rewardAsset?.localUri ?? undefined,
  };
}

export function getLevelData(levelId: string): LevelData | null {
  return levelRegistry[levelId]?.data ?? null;
}
