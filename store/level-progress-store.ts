import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface LevelProgress {
  progress: number;
  isComplete: boolean;
  // Store painted pixel indices (much smaller than full canvas data)
  paintedPixels: number[];
}

interface LevelProgressState {
  levels: Record<string, LevelProgress>;
  _hasHydrated: boolean;

  // Get progress for a level
  getLevelProgress: (levelId: string) => LevelProgress | null;

  // Save progress for a level
  saveLevelProgress: (levelId: string, progress: number, isComplete: boolean, paintedPixels: Set<number>) => void;

  // Reset a specific level
  resetLevel: (levelId: string) => void;

  // Check if level is complete
  isLevelComplete: (levelId: string) => boolean;

  // Hydration status
  setHasHydrated: (state: boolean) => void;
}

export const useLevelProgressStore = create<LevelProgressState>()(
  persist(
    (set, get) => ({
      levels: {},
      _hasHydrated: false,

      getLevelProgress: (levelId: string) => {
        return get().levels[levelId] || null;
      },

      saveLevelProgress: (levelId: string, progress: number, isComplete: boolean, paintedPixels: Set<number>) => {
        set((state) => ({
          levels: {
            ...state.levels,
            [levelId]: {
              progress,
              isComplete,
              paintedPixels: Array.from(paintedPixels),
            },
          },
        }));
      },

      resetLevel: (levelId: string) => {
        set((state) => {
          const { [levelId]: _, ...rest } = state.levels;
          return { levels: rest };
        });
      },

      isLevelComplete: (levelId: string) => {
        const level = get().levels[levelId];
        return level?.isComplete ?? false;
      },

      setHasHydrated: (state: boolean) => {
        set({ _hasHydrated: state });
      },
    }),
    {
      name: 'level-progress-storage',
      storage: createJSONStorage(() => AsyncStorage),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      partialize: (state) => ({ levels: state.levels }),
    }
  )
);
