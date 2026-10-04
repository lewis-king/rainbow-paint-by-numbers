import assert from 'node:assert/strict';
import { test } from 'node:test';
import { isReviewDue, nextReviewMilestone } from '../utils/review-policy.ts';
const history = (n) => ({
  completedLevelIds: Array.from({ length: n }, (_, i) => String(i + 1)),
  nextReviewAt: 10, requestCount: 0, optedOut: false,
});
test('first request needs ten distinct pictures; replaying does not advance it', () => {
  assert.equal(isReviewDue(history(9)), false);
  assert.equal(isReviewDue(history(10)), true);
  assert.equal(isReviewDue({ ...history(9), completedLevelIds: [...history(9).completedLevelIds, '1'] }), false);
  assert.equal(isReviewDue({ ...history(5), nextReviewAt: 5 }), false);
});
test('requests are spaced at 10, 20, 30 completed pictures', () => {
  assert.equal(nextReviewMilestone(10), 20);
  assert.equal(nextReviewMilestone(20), 30);
  assert.equal(isReviewDue({ ...history(9), nextReviewAt: 10 }), false);
  assert.equal(isReviewDue({ ...history(10), nextReviewAt: 10 }), true);
  assert.equal(isReviewDue({ ...history(19), nextReviewAt: 20 }), false);
});
test('late first request still leaves ten more pictures; opt-out is respected', () => {
  assert.equal(nextReviewMilestone(14), 24);
  assert.equal(isReviewDue({ ...history(30), optedOut: true }), false);
});
