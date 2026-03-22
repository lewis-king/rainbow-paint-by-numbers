import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as StoreReview from 'expo-store-review';

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
  setItem: async (_key: string, value: string) => {
    try {
      await AsyncStorage.setItem(_key, value);
    } catch (error) {
      console.error('AsyncStorage.setItem error:', error);
    }
  },
  removeItem: async (key: string) => {
    try {
      await AsyncStorage.removeItem(key);
    } catch (error) {
      console.error('AsyncStorage.removeItem error:', error);
    }
  },
};

interface ReviewState {
  // Count of total completed levels
  totalLevelsCompleted: number;
  // Whether user has already clicked to review
  hasClickedReview: boolean;
  // Last review request timestamp
  lastReviewRequest: number | null;
  _hasHydrated: boolean;

  // Check if we should show review prompt
  shouldShowReview: () => boolean;

  // Mark that a level was completed
  incrementCompletedLevels: () => void;

  // Mark that user clicked review button
  markClickedReview: () => void;

  // Request the actual review
  requestReview: () => Promise<void>;

  // Hydration status
  setHasHydrated: (state: boolean) => void;
}

export const useReviewStore = create<ReviewState>()(
  persist(
    (set, get) => ({
      totalLevelsCompleted: 0,
      hasClickedReview: false,
      lastReviewRequest: null,
      _hasHydrated: false,

      setHasHydrated: (state: boolean) => {
        set({ _hasHydrated: state });
      },

      shouldShowReview: () => {
        const state = get();
        
        // Don't show if already clicked review button
        if (state.hasClickedReview) return false;
        
        // Only show after completing 10+ levels
        if (state.totalLevelsCompleted < 10) return false;
        
        // Cooldown: wait at least 7 days between review requests
        if (state.lastReviewRequest) {
          const daysSinceLastRequest = (Date.now() - state.lastReviewRequest) / (1000 * 60 * 60 * 24);
          if (daysSinceLastRequest < 7) return false;
        }
        
        return true;
      },

      incrementCompletedLevels: () => {
        set((state) => ({
          totalLevelsCompleted: state.totalLevelsCompleted + 1,
        }));
      },

      markClickedReview: () => {
        set({ hasClickedReview: true });
      },

      requestReview: async () => {
        try {
          const isAvailable = await StoreReview.isAvailableAsync();
          
          if (isAvailable) {
            await StoreReview.requestReview();
            // Mark that they clicked review (we can't know if they actually submitted)
            get().markClickedReview();
            set({ lastReviewRequest: Date.now() });
          }
        } catch (error) {
          console.error('Error requesting review:', error);
        }
      },
    }),
    {
      name: 'review-storage',
      storage: createJSONStorage(() => safeAsyncStorage),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      partialize: (state) => ({
        totalLevelsCompleted: state.totalLevelsCompleted,
        hasClickedReview: state.hasClickedReview,
        lastReviewRequest: state.lastReviewRequest,
      }),
    }
  )
);
