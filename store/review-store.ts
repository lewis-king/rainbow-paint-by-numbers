import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as StoreReview from 'expo-store-review';
import { isReviewDue, nextReviewMilestone, REVIEW_MILESTONE, type ReviewHistory } from '@/utils/review-policy';

interface ReviewState extends ReviewHistory {
  lastReviewRequest: number | null;
  _hasHydrated: boolean;
  requestInFlight: boolean;
  recordCompletedLevel: (id: string) => void;
  reconcileCompletions: (ids: string[]) => void;
  shouldShowReview: () => boolean;
  requestReview: (canPresent: () => boolean) => Promise<void>;
  setHasHydrated: () => void;
}

// Do not write defaults over saved cadence/opt-out while storage is loading.
const pendingCompletions = new Set<string>();

export const useReviewStore = create<ReviewState>()(
  persist(
    (set, get) => ({
      completedLevelIds: [],
      lastReviewRequest: null,
      nextReviewAt: REVIEW_MILESTONE,
      requestCount: 0,
      optedOut: false,
      _hasHydrated: false,
      requestInFlight: false,
      setHasHydrated: () => {
        set({
          _hasHydrated: true,
          completedLevelIds: [...new Set([...get().completedLevelIds, ...pendingCompletions])],
        });
        pendingCompletions.clear();
      },
      recordCompletedLevel: (id) => {
        if (!get()._hasHydrated) {
          pendingCompletions.add(id);
          return;
        }
        if (!get().completedLevelIds.includes(id)) {
          set({ completedLevelIds: [...get().completedLevelIds, id] });
        }
      },
      reconcileCompletions: (ids) => {
        if (!get()._hasHydrated) {
          ids.forEach((id) => pendingCompletions.add(id));
          return;
        }
        const merged = [...new Set([...get().completedLevelIds, ...ids])];
        if (merged.length !== get().completedLevelIds.length) set({ completedLevelIds: merged });
      },
      shouldShowReview: () => get()._hasHydrated && !get().requestInFlight && isReviewDue(get()),
      requestReview: async (canPresent) => {
        if (!canPresent() || !get().shouldShowReview()) return;
        set({ requestInFlight: true });
        try {
          if (!await StoreReview.isAvailableAsync()) return;
          if (!canPresent() || !isReviewDue(get())) return;
          // An attempt is not proof the OS displayed a dialog or a review was submitted.
          // Persist first so rerenders/relaunches cannot spam requests.
          set({
            lastReviewRequest: Date.now(),
            nextReviewAt: nextReviewMilestone(get().completedLevelIds.length),
            requestCount: get().requestCount + 1,
          });
          await StoreReview.requestReview();
        } catch (error) {
          console.warn('Native review request unavailable:', error);
        } finally {
          set({ requestInFlight: false });
        }
      },
    }),
    {
      name: 'review-storage',
      version: 1,
      storage: createJSONStorage(() => AsyncStorage),
      migrate: (stored) => {
        const previous = stored as { hasClickedReview?: boolean; lastReviewRequest?: number | null } | null;
        return {
          completedLevelIds: [], // Recover distinct completions from level-progress-storage.
          // The old flag also meant “don't ask again”; preserve that choice.
          optedOut: previous?.hasClickedReview ?? false,
          lastReviewRequest: previous?.lastReviewRequest ?? null,
          nextReviewAt: REVIEW_MILESTONE,
          requestCount: 0,
        };
      },
      onRehydrateStorage: () => (state) => {
        // Fail closed on storage errors: do not prompt with unknown history.
        state?.setHasHydrated();
      },
      partialize: ({ completedLevelIds, lastReviewRequest, nextReviewAt, requestCount, optedOut }) => ({
        completedLevelIds, lastReviewRequest, nextReviewAt, requestCount, optedOut,
      }),
    }
  )
);
