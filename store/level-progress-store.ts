import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { encodeRuns, migrateStoredLevels } from '@/utils/painted-pixels';

// Wrap AsyncStorage to handle errors gracefully
const safeAsyncStorage = {
  getItem: async (key: string) => {
    try {
      return await AsyncStorage.getItem(key);
    } catch (error) {
      console.error('AsyncStorage.getItem error:', key, error);
      return null;
    }
  },
  setItem: async (key: string, value: string) => {
    try {
      await AsyncStorage.setItem(key, value);
    } catch (error) {
      console.error('AsyncStorage.setItem error:', key, error);
    }
  },
  removeItem: async (key: string) => {
    try {
      await AsyncStorage.removeItem(key);
    } catch (error) {
      console.error('AsyncStorage.removeItem error:', key, error);
    }
  },
};

interface LevelProgress {
  progress: number;
  isComplete: boolean;
  // Painted pixels as [start, length, ...] runs for restoration (only saved on exit).
  // See utils/painted-pixels.ts for why this is not a list of every pixel.
  paintedRuns?: number[];
  // Timestamp for cache-busting preview images
  lastUpdated: number;
}

interface LevelProgressState {
  levels: Record<string, LevelProgress>;
  _hasHydrated: boolean;

  // Get progress for a level
  getLevelProgress: (levelId: string) => LevelProgress | null;

  // Save progress (without pixel data - for quick updates)
  saveProgress: (levelId: string, progress: number, isComplete: boolean) => void;

  // Save full state with pixels (only called on exit)
  saveFullState: (levelId: string, progress: number, isComplete: boolean, paintedPixels: Set<number>) => void;

  // Reset a specific level
  resetLevel: (levelId: string) => void;

  // Check if level is complete
  isLevelComplete: (levelId: string) => boolean;

  // Hydration status
  setHasHydrated: (state: boolean) => void;
  forceHydrated: () => void;
}

export const useLevelProgressStore = create<LevelProgressState>()(
  persist(
    (set, get) => ({
      levels: {},
      _hasHydrated: false,

      // Force hydration complete (used as fallback)
      forceHydrated: () => set({ _hasHydrated: true }),

      getLevelProgress: (levelId: string) => {
        return get().levels[levelId] || null;
      },

      // Quick save - just progress percentage (called frequently)
      saveProgress: (levelId: string, progress: number, isComplete: boolean) => {
        set((state) => {
          const existing = state.levels[levelId];
          return {
            levels: {
              ...state.levels,
              [levelId]: {
                ...existing,
                progress,
                isComplete,
                lastUpdated: Date.now(),
              },
            },
          };
        });
      },

      // Full save with pixels - only called when exiting (back button, app background)
      saveFullState: (levelId: string, progress: number, isComplete: boolean, paintedPixels: Set<number>) => {
        set((state) => ({
          levels: {
            ...state.levels,
            [levelId]: {
              progress,
              isComplete,
              // Don't store pixels for completed levels - they show victory screen anyway
              paintedRuns: isComplete ? undefined : encodeRuns(paintedPixels),
              lastUpdated: Date.now(),
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
      storage: createJSONStorage(() => safeAsyncStorage),
      // Version 1 stores painted pixels as runs. Earlier saves are converted, not dropped.
      version: 1,
      migrate: (persisted, version) => {
        const state = (persisted ?? {}) as { levels?: Record<string, LevelProgress> };
        return version < 1 ? { ...state, levels: migrateStoredLevels(state.levels) } : state;
      },
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      partialize: (state) => ({ levels: state.levels }),
    }
  )
);
