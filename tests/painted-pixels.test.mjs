import assert from 'node:assert/strict';
import { test } from 'node:test';
import { encodeRuns, decodeRuns, migrateStoredLevels } from '../utils/painted-pixels.ts';

test('runs round-trip any set of pixels, in any order', () => {
  const pixels = new Set([9, 3, 4, 5, 1048575, 0, 700, 701]);
  const runs = encodeRuns(pixels);
  assert.deepEqual(runs, [0, 1, 3, 3, 9, 1, 700, 2, 1048575, 1]);
  assert.deepEqual(decodeRuns(runs), [...pixels].sort((a, b) => a - b));
});

test('nothing painted is an empty list', () => {
  assert.deepEqual(encodeRuns(new Set()), []);
  assert.deepEqual(decodeRuns([]), []);
  assert.deepEqual(decodeRuns(undefined), []);
});

test('a filled area is far smaller as runs than as a list of pixels', () => {
  const pixels = [];
  for (let y = 100; y < 600; y++) for (let x = 200; x < 800; x++) pixels.push(y * 1024 + x);
  const runs = encodeRuns(pixels);
  assert.equal(runs.length, 1000);
  assert.ok(JSON.stringify(runs).length * 100 < JSON.stringify(pixels).length);
  assert.deepEqual(decodeRuns(runs), pixels);
});

test('damaged runs are skipped, never expanded into nonsense', () => {
  assert.deepEqual(decodeRuns([5, 2, -4, 3, 9, 0, 20, 1, 7]), [5, 6, 20]);
});

test('progress saved by 1.4 keeps every painted pixel after the update', () => {
  const stored = {
    '3': { progress: 40, isComplete: false, lastUpdated: 1, paintedPixels: [10, 11, 12, 50] },
    '7': { progress: 100, isComplete: true, lastUpdated: 2 },
  };
  const migrated = migrateStoredLevels(stored);
  assert.equal(migrated['3'].paintedPixels, undefined);
  assert.deepEqual(decodeRuns(migrated['3'].paintedRuns), [10, 11, 12, 50]);
  assert.equal(migrated['3'].progress, 40);
  assert.deepEqual(migrated['7'], stored['7']);
  assert.deepEqual(migrateStoredLevels(migrated), migrated);   // running it twice changes nothing
  assert.deepEqual(migrateStoredLevels(undefined), {});
});
