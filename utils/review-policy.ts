export const REVIEW_MILESTONE = 10;

export interface ReviewHistory {
  completedLevelIds: string[];
  nextReviewAt: number;
  requestCount: number;
  optedOut: boolean;
}

export function isReviewDue(history: ReviewHistory): boolean {
  return !history.optedOut
    && new Set(history.completedLevelIds).size >= Math.max(REVIEW_MILESTONE, history.nextReviewAt);
}

export function nextReviewMilestone(completed: number): number {
  // First request at 10, then 20, 30, … . If availability delayed a request,
  // leave ten further distinct completions before trying again.
  return completed + REVIEW_MILESTONE;
}
