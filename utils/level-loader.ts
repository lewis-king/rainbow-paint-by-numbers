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
const LEVEL_IDS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'] as const;

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
  '7': {
    data: require('@/assets/images/levels/7/data.json'),
    original: require('@/assets/images/levels/7/original.png'),
    lines: require('@/assets/images/levels/7/lines.png'),
    map: require('@/assets/images/levels/7/map.png'),
    reward: require('@/assets/images/levels/7/reward.mp4'),
  },
  '8': {
    data: require('@/assets/images/levels/8/data.json'),
    original: require('@/assets/images/levels/8/original.png'),
    lines: require('@/assets/images/levels/8/lines.png'),
    map: require('@/assets/images/levels/8/map.png'),
    reward: require('@/assets/images/levels/8/reward.mp4'),
  },
  '9': {
    data: require('@/assets/images/levels/9/data.json'),
    original: require('@/assets/images/levels/9/original.png'),
    lines: require('@/assets/images/levels/9/lines.png'),
    map: require('@/assets/images/levels/9/map.png'),
    reward: require('@/assets/images/levels/9/reward.mp4'),
  },
  '10': {
    data: require('@/assets/images/levels/10/data.json'),
    original: require('@/assets/images/levels/10/original.png'),
    lines: require('@/assets/images/levels/10/lines.png'),
    map: require('@/assets/images/levels/10/map.png'),
    reward: require('@/assets/images/levels/10/reward.mp4'),
  },
  '11': {
    data: require('@/assets/images/levels/11/data.json'),
    original: require('@/assets/images/levels/11/original.png'),
    lines: require('@/assets/images/levels/11/lines.png'),
    map: require('@/assets/images/levels/11/map.png'),
    reward: require('@/assets/images/levels/11/reward.mp4'),
  },
  '12': {
    data: require('@/assets/images/levels/12/data.json'),
    original: require('@/assets/images/levels/12/original.png'),
    lines: require('@/assets/images/levels/12/lines.png'),
    map: require('@/assets/images/levels/12/map.png'),
    reward: require('@/assets/images/levels/12/reward.mp4'),
  },
  '13': {
    data: require('@/assets/images/levels/13/data.json'),
    original: require('@/assets/images/levels/13/original.png'),
    lines: require('@/assets/images/levels/13/lines.png'),
    map: require('@/assets/images/levels/13/map.png'),
    reward: require('@/assets/images/levels/13/reward.mp4'),
  },
  '14': {
    data: require('@/assets/images/levels/14/data.json'),
    original: require('@/assets/images/levels/14/original.png'),
    lines: require('@/assets/images/levels/14/lines.png'),
    map: require('@/assets/images/levels/14/map.png'),
    reward: require('@/assets/images/levels/14/reward.mp4'),
  },
  '15': {
    data: require('@/assets/images/levels/15/data.json'),
    original: require('@/assets/images/levels/15/original.png'),
    lines: require('@/assets/images/levels/15/lines.png'),
    map: require('@/assets/images/levels/15/map.png'),
    reward: require('@/assets/images/levels/15/reward.mp4'),
  },
  '16': {
    data: require('@/assets/images/levels/16/data.json'),
    original: require('@/assets/images/levels/16/original.png'),
    lines: require('@/assets/images/levels/16/lines.png'),
    map: require('@/assets/images/levels/16/map.png'),
    reward: require('@/assets/images/levels/16/reward.mp4'),
  },
  '17': {
    data: require('@/assets/images/levels/17/data.json'),
    original: require('@/assets/images/levels/17/original.png'),
    lines: require('@/assets/images/levels/17/lines.png'),
    map: require('@/assets/images/levels/17/map.png'),
    reward: require('@/assets/images/levels/17/reward.mp4'),
  },
  '18': {
    data: require('@/assets/images/levels/18/data.json'),
    original: require('@/assets/images/levels/18/original.png'),
    lines: require('@/assets/images/levels/18/lines.png'),
    map: require('@/assets/images/levels/18/map.png'),
    reward: require('@/assets/images/levels/18/reward.mp4'),
  },
  '19': {
    data: require('@/assets/images/levels/19/data.json'),
    original: require('@/assets/images/levels/19/original.png'),
    lines: require('@/assets/images/levels/19/lines.png'),
    map: require('@/assets/images/levels/19/map.png'),
    reward: require('@/assets/images/levels/19/reward.mp4'),
  },
  '20': {
    data: require('@/assets/images/levels/20/data.json'),
    original: require('@/assets/images/levels/20/original.png'),
    lines: require('@/assets/images/levels/20/lines.png'),
    map: require('@/assets/images/levels/20/map.png'),
    reward: require('@/assets/images/levels/20/reward.mp4'),
  },
  '21': {
    data: require('@/assets/images/levels/21/data.json'),
    original: require('@/assets/images/levels/21/original.png'),
    lines: require('@/assets/images/levels/21/lines.png'),
    map: require('@/assets/images/levels/21/map.png'),
    reward: require('@/assets/images/levels/21/reward.mp4'),
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
