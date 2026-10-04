import { Asset } from 'expo-asset';
import pictureCatalog from './picture-catalog.json';
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
 * 3. Add static require entries to levelRegistry below
 */
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
  '22': {
    data: require('@/assets/images/levels/22/data.json'),
    original: require('@/assets/images/levels/22/original.png'),
    lines: require('@/assets/images/levels/22/lines.png'),
    map: require('@/assets/images/levels/22/map.png'),
    reward: require('@/assets/images/levels/22/reward.mp4'),
  },
  '23': {
    data: require('@/assets/images/levels/23/data.json'),
    original: require('@/assets/images/levels/23/original.png'),
    lines: require('@/assets/images/levels/23/lines.png'),
    map: require('@/assets/images/levels/23/map.png'),
    reward: require('@/assets/images/levels/23/reward.mp4'),
  },
  '24': {
    data: require('@/assets/images/levels/24/data.json'),
    original: require('@/assets/images/levels/24/original.png'),
    lines: require('@/assets/images/levels/24/lines.png'),
    map: require('@/assets/images/levels/24/map.png'),
    reward: require('@/assets/images/levels/24/reward.mp4'),
  },
  '25': {
    data: require('@/assets/images/levels/25/data.json'),
    original: require('@/assets/images/levels/25/original.png'),
    lines: require('@/assets/images/levels/25/lines.png'),
    map: require('@/assets/images/levels/25/map.png'),
    reward: require('@/assets/images/levels/25/reward.mp4'),
  },
  '26': {
    data: require('@/assets/images/levels/26/data.json'),
    original: require('@/assets/images/levels/26/original.png'),
    lines: require('@/assets/images/levels/26/lines.png'),
    map: require('@/assets/images/levels/26/map.png'),
    reward: require('@/assets/images/levels/26/reward.mp4'),
  },
  '27': {
    data: require('@/assets/images/levels/27/data.json'),
    original: require('@/assets/images/levels/27/original.png'),
    lines: require('@/assets/images/levels/27/lines.png'),
    map: require('@/assets/images/levels/27/map.png'),
    reward: require('@/assets/images/levels/27/reward.mp4'),
  },
  '28': {
    data: require('@/assets/images/levels/28/data.json'),
    original: require('@/assets/images/levels/28/original.png'),
    lines: require('@/assets/images/levels/28/lines.png'),
    map: require('@/assets/images/levels/28/map.png'),
    reward: require('@/assets/images/levels/28/reward.mp4'),
  },
  '29': {
    data: require('@/assets/images/levels/29/data.json'),
    original: require('@/assets/images/levels/29/original.png'),
    lines: require('@/assets/images/levels/29/lines.png'),
    map: require('@/assets/images/levels/29/map.png'),
    reward: require('@/assets/images/levels/29/reward.mp4'),
  },
  '30': {
    data: require('@/assets/images/levels/30/data.json'),
    original: require('@/assets/images/levels/30/original.png'),
    lines: require('@/assets/images/levels/30/lines.png'),
    map: require('@/assets/images/levels/30/map.png'),
    reward: require('@/assets/images/levels/30/reward.mp4'),
  },
  '31': {
    data: require('@/assets/images/levels/31/data.json'),
    original: require('@/assets/images/levels/31/original.png'),
    lines: require('@/assets/images/levels/31/lines.png'),
    map: require('@/assets/images/levels/31/map.png'),
    reward: require('@/assets/images/levels/31/reward.mp4'),
  },
  '33': {
    data: require('@/assets/images/levels/33/data.json'),
    original: require('@/assets/images/levels/33/original.png'),
    lines: require('@/assets/images/levels/33/lines.png'),
    map: require('@/assets/images/levels/33/map.png'),
    reward: require('@/assets/images/levels/33/reward.mp4'),
  },
  '41': {
    data: require('@/assets/images/levels/41/data.json'),
    original: require('@/assets/images/levels/41/original.png'),
    lines: require('@/assets/images/levels/41/lines.png'),
    map: require('@/assets/images/levels/41/map.png'),
    reward: require('@/assets/images/levels/41/reward.mp4'),
  },
  '42': {
    data: require('@/assets/images/levels/42/data.json'),
    original: require('@/assets/images/levels/42/original.png'),
    lines: require('@/assets/images/levels/42/lines.png'),
    map: require('@/assets/images/levels/42/map.png'),
    reward: require('@/assets/images/levels/42/reward.mp4'),
  },
  '43': {
    data: require('@/assets/images/levels/43/data.json'),
    original: require('@/assets/images/levels/43/original.png'),
    lines: require('@/assets/images/levels/43/lines.png'),
    map: require('@/assets/images/levels/43/map.png'),
    reward: require('@/assets/images/levels/43/reward.mp4'),
  },
  '36': {
    data: require('@/assets/images/levels/36/data.json'),
    original: require('@/assets/images/levels/36/original.png'),
    lines: require('@/assets/images/levels/36/lines.png'),
    map: require('@/assets/images/levels/36/map.png'),
    reward: require('@/assets/images/levels/36/reward.mp4'),
  },
  '38': {
    data: require('@/assets/images/levels/38/data.json'),
    original: require('@/assets/images/levels/38/original.png'),
    lines: require('@/assets/images/levels/38/lines.png'),
    map: require('@/assets/images/levels/38/map.png'),
    reward: require('@/assets/images/levels/38/reward.mp4'),
  },
  '32': {
    data: require('@/assets/images/levels/32/data.json'),
    original: require('@/assets/images/levels/32/original.png'),
    lines: require('@/assets/images/levels/32/lines.png'),
    map: require('@/assets/images/levels/32/map.png'),
    reward: require('@/assets/images/levels/32/reward.mp4'),
  },
  '34': {
    data: require('@/assets/images/levels/34/data.json'),
    original: require('@/assets/images/levels/34/original.png'),
    lines: require('@/assets/images/levels/34/lines.png'),
    map: require('@/assets/images/levels/34/map.png'),
    reward: require('@/assets/images/levels/34/reward.mp4'),
  },
  '35': {
    data: require('@/assets/images/levels/35/data.json'),
    original: require('@/assets/images/levels/35/original.png'),
    lines: require('@/assets/images/levels/35/lines.png'),
    map: require('@/assets/images/levels/35/map.png'),
    reward: require('@/assets/images/levels/35/reward.mp4'),
  },
  '37': {
    data: require('@/assets/images/levels/37/data.json'),
    original: require('@/assets/images/levels/37/original.png'),
    lines: require('@/assets/images/levels/37/lines.png'),
    map: require('@/assets/images/levels/37/map.png'),
    reward: require('@/assets/images/levels/37/reward.mp4'),
  },
  '39': {
    data: require('@/assets/images/levels/39/data.json'),
    original: require('@/assets/images/levels/39/original.png'),
    lines: require('@/assets/images/levels/39/lines.png'),
    map: require('@/assets/images/levels/39/map.png'),
    reward: require('@/assets/images/levels/39/reward.mp4'),
  },
  '40': {
    data: require('@/assets/images/levels/40/data.json'),
    original: require('@/assets/images/levels/40/original.png'),
    lines: require('@/assets/images/levels/40/lines.png'),
    map: require('@/assets/images/levels/40/map.png'),
    reward: require('@/assets/images/levels/40/reward.mp4'),
  },
  '44': {
    data: require('@/assets/images/levels/44/data.json'),
    original: require('@/assets/images/levels/44/original.png'),
    lines: require('@/assets/images/levels/44/lines.png'),
    map: require('@/assets/images/levels/44/map.png'),
    reward: require('@/assets/images/levels/44/reward.mp4'),
  },
  '45': {
    data: require('@/assets/images/levels/45/data.json'),
    original: require('@/assets/images/levels/45/original.png'),
    lines: require('@/assets/images/levels/45/lines.png'),
    map: require('@/assets/images/levels/45/map.png'),
    reward: require('@/assets/images/levels/45/reward.mp4'),
  },
  '46': {
    data: require('@/assets/images/levels/46/data.json'),
    original: require('@/assets/images/levels/46/original.png'),
    lines: require('@/assets/images/levels/46/lines.png'),
    map: require('@/assets/images/levels/46/map.png'),
    reward: require('@/assets/images/levels/46/reward.mp4'),
  },
  '47': {
    data: require('@/assets/images/levels/47/data.json'),
    original: require('@/assets/images/levels/47/original.png'),
    lines: require('@/assets/images/levels/47/lines.png'),
    map: require('@/assets/images/levels/47/map.png'),
    reward: require('@/assets/images/levels/47/reward.mp4'),
  },
  '48': {
    data: require('@/assets/images/levels/48/data.json'),
    original: require('@/assets/images/levels/48/original.png'),
    lines: require('@/assets/images/levels/48/lines.png'),
    map: require('@/assets/images/levels/48/map.png'),
    reward: require('@/assets/images/levels/48/reward.mp4'),
  },
  '49': {
    data: require('@/assets/images/levels/49/data.json'),
    original: require('@/assets/images/levels/49/original.png'),
    lines: require('@/assets/images/levels/49/lines.png'),
    map: require('@/assets/images/levels/49/map.png'),
    reward: require('@/assets/images/levels/49/reward.mp4'),
  },
  '50': {
    data: require('@/assets/images/levels/50/data.json'),
    original: require('@/assets/images/levels/50/original.png'),
    lines: require('@/assets/images/levels/50/lines.png'),
    map: require('@/assets/images/levels/50/map.png'),
    reward: require('@/assets/images/levels/50/reward.mp4'),
  },
  '51': {
    data: require('@/assets/images/levels/51/data.json'),
    original: require('@/assets/images/levels/51/original.png'),
    lines: require('@/assets/images/levels/51/lines.png'),
    map: require('@/assets/images/levels/51/map.png'),
    reward: require('@/assets/images/levels/51/reward.mp4'),
  },
  '52': {
    data: require('@/assets/images/levels/52/data.json'),
    original: require('@/assets/images/levels/52/original.png'),
    lines: require('@/assets/images/levels/52/lines.png'),
    map: require('@/assets/images/levels/52/map.png'),
    reward: require('@/assets/images/levels/52/reward.mp4'),
  },
  '53': {
    data: require('@/assets/images/levels/53/data.json'),
    original: require('@/assets/images/levels/53/original.png'),
    lines: require('@/assets/images/levels/53/lines.png'),
    map: require('@/assets/images/levels/53/map.png'),
    reward: require('@/assets/images/levels/53/reward.mp4'),
  },
  '54': {
    data: require('@/assets/images/levels/54/data.json'),
    original: require('@/assets/images/levels/54/original.png'),
    lines: require('@/assets/images/levels/54/lines.png'),
    map: require('@/assets/images/levels/54/map.png'),
    reward: require('@/assets/images/levels/54/reward.mp4'),
  },
  '55': {
    data: require('@/assets/images/levels/55/data.json'),
    original: require('@/assets/images/levels/55/original.png'),
    lines: require('@/assets/images/levels/55/lines.png'),
    map: require('@/assets/images/levels/55/map.png'),
    reward: require('@/assets/images/levels/55/reward.mp4'),
  },
  '56': {
    data: require('@/assets/images/levels/56/data.json'),
    original: require('@/assets/images/levels/56/original.png'),
    lines: require('@/assets/images/levels/56/lines.png'),
    map: require('@/assets/images/levels/56/map.png'),
    reward: require('@/assets/images/levels/56/reward.mp4'),
  },
  '57': {
    data: require('@/assets/images/levels/57/data.json'),
    original: require('@/assets/images/levels/57/original.png'),
    lines: require('@/assets/images/levels/57/lines.png'),
    map: require('@/assets/images/levels/57/map.png'),
    reward: require('@/assets/images/levels/57/reward.mp4'),
  },
  '58': {
    data: require('@/assets/images/levels/58/data.json'),
    original: require('@/assets/images/levels/58/original.png'),
    lines: require('@/assets/images/levels/58/lines.png'),
    map: require('@/assets/images/levels/58/map.png'),
    reward: require('@/assets/images/levels/58/reward.mp4'),
  },
};

export const LEVEL_IDS = Object.keys(levelRegistry).sort((a, b) => Number(a) - Number(b));

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
      title: pictureCatalog[id as keyof typeof pictureCatalog]?.title ?? `Picture ${id}`,
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
