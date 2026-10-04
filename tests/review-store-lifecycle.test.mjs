import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
import ts from 'typescript';
import * as policy from '../utils/review-policy.ts';

const require = createRequire(import.meta.url);
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const settle = () => new Promise((resolve) => setImmediate(resolve));
function loadStore() {
  const storageRead = deferred();
  const availability = deferred();
  const writes = [];
  let nativeCalls = 0;
  const storage = {
    getItem: () => storageRead.promise,
    setItem: async (_, value) => { writes.push(JSON.parse(value)); },
    removeItem: async () => {},
  };
  const mocks = {
    '@react-native-async-storage/async-storage': { default: storage },
    'expo-store-review': {
      isAvailableAsync: () => availability.promise,
      requestReview: async () => { nativeCalls += 1; },
    },
    '@/utils/review-policy': policy,
  };
  const source = readFileSync(new URL('../store/review-store.ts', import.meta.url), 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(compiled, {
    exports: module.exports,
    require: (name) => name in mocks ? mocks[name] : require(name),
    console, Date, Set,
  });
  return { store: module.exports.useReviewStore, storageRead, availability, writes, nativeCalls: () => nativeCalls };
}

test('completion before hydration preserves saved opt-out and cadence without early writes', async () => {
  const app = loadStore();
  app.store.getState().recordCompletedLevel('6');
  app.store.getState().reconcileCompletions(['5', '6']);
  assert.equal(app.writes.length, 0);
  app.storageRead.resolve(JSON.stringify({ version: 1, state: {
    completedLevelIds: ['1', '2', '3', '4', '5'], optedOut: true,
    nextReviewAt: 20, requestCount: 2, lastReviewRequest: 123,
  } }));
  await settle();
  const state = app.store.getState();
  assert.equal(state._hasHydrated, true);
  assert.equal(state.optedOut, true);
  assert.equal(state.nextReviewAt, 20);
  assert.equal(state.completedLevelIds.length, 6);
  assert.equal(state.shouldShowReview(), false);
  assert.equal(app.writes.at(-1).state.optedOut, true);
});

test('failed hydration cannot overwrite saved data or request a review', async () => {
  const app = loadStore();
  app.store.getState().recordCompletedLevel('1');
  app.storageRead.reject(new Error('storage temporarily unavailable'));
  await settle();
  app.store.getState().reconcileCompletions(Array.from({ length: 10 }, (_, i) => String(i + 1)));
  await app.store.getState().requestReview(() => true);
  assert.equal(app.store.getState()._hasHydrated, false);
  assert.equal(app.writes.length, 0);
  assert.equal(app.nativeCalls(), 0);
});

test('leaving gallery during availability check neither prompts nor advances milestone', async () => {
  const app = loadStore();
  app.storageRead.resolve(null);
  await settle();
  app.store.getState().reconcileCompletions(Array.from({ length: 10 }, (_, i) => String(i + 1)));
  assert.equal(app.store.getState().shouldShowReview(), true);
  let onGallery = true;
  const request = app.store.getState().requestReview(() => onGallery);
  onGallery = false;
  app.availability.resolve(true);
  await request;
  assert.equal(app.nativeCalls(), 0);
  assert.equal(app.store.getState().requestCount, 0);
  assert.equal(app.store.getState().nextReviewAt, 10);
  assert.equal(app.store.getState().requestInFlight, false);
});
