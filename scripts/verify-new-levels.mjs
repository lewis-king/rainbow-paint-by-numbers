// Every picture in assets/images/levels must be wired into the app by hand-free means:
// a static entry in utils/level-loader.ts (Metro cannot bundle a computed require) and a
// title and category in utils/picture-catalog.json. This fails the release if one is missing.
// Whether the level files themselves are the approved ones is `npm run verify:levels`.
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const levels = path.join(root, 'assets/images/levels');
const loader = readFileSync(path.join(root, 'utils/level-loader.ts'), 'utf8');
const catalog = JSON.parse(readFileSync(path.join(root, 'utils/picture-catalog.json'), 'utf8'));
const files = { data: 'data.json', original: 'original.png', lines: 'lines.png', map: 'map.png', reward: 'reward.mp4' };
const PNG = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

const folders = readdirSync(levels, { withFileTypes: true })
  .filter(entry => entry.isDirectory()).map(entry => entry.name).sort((a, b) => Number(a) - Number(b));
const registered = [...loader.matchAll(/^  '(\d+)': \{([\s\S]*?)^  \},/gm)].map(match => [match[1], match[2]]);
const entries = new Map(registered);

assert(folders.length > 0, 'No level folders found');
for (const id of folders) {
  const folder = path.join(levels, id);
  const entry = entries.get(id);
  assert(entry, `Level ${id}: folder exists but utils/level-loader.ts has no entry, so the app will not show it`);
  assert(catalog[id]?.title && catalog[id]?.category, `Level ${id}: no title or category in utils/picture-catalog.json`);
  for (const [key, name] of Object.entries(files)) {
    const present = existsSync(path.join(folder, name));
    const reference = `${key}: require('@/assets/images/levels/${id}/${name}')`;
    if (key === 'reward' && !present) {
      assert(!entry.includes('reward:'), `Level ${id}: loader lists a reward that is not on disk`);
      continue;
    }
    assert(present, `Level ${id}: missing ${name}`);
    assert(entry.includes(reference), `Level ${id}: loader entry lacks ${reference}`);
    const bytes = readFileSync(path.join(folder, name));
    assert(bytes.length > 0, `Level ${id}: empty ${name}`);
    if (name.endsWith('.png')) assert(bytes.subarray(0, 8).equals(PNG), `Level ${id}: ${name} is not a PNG`);
  }
  const data = JSON.parse(readFileSync(path.join(folder, 'data.json'), 'utf8'));
  assert.equal(String(data.id), id, `Level ${id}: data.json is for level ${data.id}`);
  assert(data.palette.length > 1 && data.palette.length < 254, `Level ${id}: palette size`);
  assert(data.palette.every(color => /^#[0-9a-f]{6}$/i.test(color)), `Level ${id}: invalid palette colour`);
  assert(data.numbers.length > 0, `Level ${id}: no numbers`);
  for (const label of data.numbers) {
    assert(Number.isInteger(label.color_index) && label.color_index >= 0 && label.color_index < data.palette.length,
      `Level ${id}: number points at a colour outside the palette`);
    assert.equal(label.number, label.color_index + 1, `Level ${id}: number does not match its colour`);
    assert(label.x >= 0 && label.x < data.dimensions.w && label.y >= 0 && label.y < data.dimensions.h,
      `Level ${id}: number outside the picture`);
    if (label.size !== undefined) {
      assert(Number.isInteger(label.size) && label.size >= 4 && label.size <= 9, `Level ${id}: number size ${label.size}`);
    }
  }
}
for (const [id] of registered) assert(folders.includes(id), `Level ${id}: registered in the loader with no folder`);
for (const id of Object.keys(catalog)) assert(folders.includes(id), `Level ${id}: in the catalog with no folder`);

console.log(`${folders.length} levels: each has a loader entry, a catalog title, its files and sane numbers.`);
