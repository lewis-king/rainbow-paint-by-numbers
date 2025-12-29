import { Asset } from 'expo-asset';
import type { LevelData } from '@/types/level';

export interface LevelAssets {
  data: LevelData;
  originalUri: string;
  linesUri: string;
  mapUri: string;
  rewardUri?: string;
}

// Import level assets statically (required for Expo bundling)
const levelAssets = {
  '1': {
    data: require('@/assets/images/levels/1/data.json') as LevelData,
    original: require('@/assets/images/levels/1/original.png'),
    lines: require('@/assets/images/levels/1/lines.png'),
    map: require('@/assets/images/levels/1/map.png'),
    reward: require('@/assets/images/levels/1/reward.mp4'),
  },
  '2': {
    data: require('@/assets/images/levels/2/data.json') as LevelData,
    original: require('@/assets/images/levels/2/original.png'),
    lines: require('@/assets/images/levels/2/lines.png'),
    map: require('@/assets/images/levels/2/map.png'),
    reward: require('@/assets/images/levels/2/reward.mp4'),
  },
} as const;

export const LEVEL_IDS = Object.keys(levelAssets) as Array<keyof typeof levelAssets>;

export interface LevelPreview {
  id: string;
  thumbnailSource: number; // require() returns a number
  title: string;
}

export function getLevelPreviews(): LevelPreview[] {
  return LEVEL_IDS.map((id) => ({
    id,
    thumbnailSource: levelAssets[id].lines,
    title: `Level ${id}`,
  }));
}

export async function loadLevelAssets(levelId: string): Promise<LevelAssets | null> {
  const assets = levelAssets[levelId as keyof typeof levelAssets];
  if (!assets) return null;

  // Load assets and get their local URIs
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
  const assets = levelAssets[levelId as keyof typeof levelAssets];
  return assets?.data ?? null;
}
