/** Painted pixels are saved as runs: [start, length, start, length, ...] in ascending
 * pixel index. A half-painted picture is a few thousand runs. As a plain list of pixel
 * indexes it was several megabytes of JSON, and a handful of started pictures overflowed
 * Android's storage limit, after which nothing was saved at all.
 */
export function encodeRuns(pixels: Iterable<number>): number[] {
  let highest = -1;
  for (const pixel of pixels) {
    if (Number.isInteger(pixel) && pixel > highest) highest = pixel;
  }
  if (highest < 0) return [];
  const painted = new Uint8Array(highest + 1);
  for (const pixel of pixels) {
    if (Number.isInteger(pixel) && pixel >= 0) painted[pixel] = 1;
  }
  const runs: number[] = [];
  let start = -1;
  for (let index = 0; index <= highest; index++) {
    if (painted[index]) {
      if (start < 0) start = index;
    } else if (start >= 0) {
      runs.push(start, index - start);
      start = -1;
    }
  }
  if (start >= 0) runs.push(start, highest + 1 - start);
  return runs;
}

export function decodeRuns(runs: readonly number[] | undefined): number[] {
  const pixels: number[] = [];
  if (!runs) return pixels;
  for (let index = 0; index + 1 < runs.length; index += 2) {
    const start = runs[index];
    const length = runs[index + 1];
    if (!Number.isInteger(start) || !Number.isInteger(length) || start < 0 || length <= 0) continue;
    for (let offset = 0; offset < length; offset++) pixels.push(start + offset);
  }
  return pixels;
}

type StoredLevel = { paintedPixels?: number[]; paintedRuns?: number[] };

/** Progress saved by versions up to 1.4 listed every painted pixel. Rewrite it as runs. */
export function migrateStoredLevels<T extends object>(levels: Record<string, T> | undefined): Record<string, T> {
  const migrated: Record<string, T> = {};
  for (const [id, level] of Object.entries(levels ?? {})) {
    const { paintedPixels, ...rest } = level as StoredLevel;
    migrated[id] = (Array.isArray(paintedPixels) && !rest.paintedRuns
      ? { ...rest, paintedRuns: encodeRuns(paintedPixels) }
      : rest) as T;
  }
  return migrated;
}
