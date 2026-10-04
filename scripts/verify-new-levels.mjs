import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const generation = path.join(root, 'image-processing/generation');
const loader = readFileSync(path.join(root, 'utils/level-loader.ts'), 'utf8');
const files = { data: 'data.json', original: 'original.png', lines: 'lines.png', map: 'map.png', reward: 'reward.mp4' };
const missing = [];
let verified = 0;
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

for (let number = 29; number <= 58; number++) {
  const id = String(number);
  const folder = path.join(root, 'assets/images/levels', id);
  const registered = loader.match(new RegExp(`^  '${id}': \\{([\\s\\S]*?)^  \\},`, 'm'));
  if (!existsSync(folder) && !registered) { missing.push(id); continue; }
  assert(registered, `Level ${id}: folder exists but explicit loader entry is missing`);
  const bundle = createHash('sha256');
  for (const [key, name] of Object.entries(files)) {
    const reference = `${key}: require('@/assets/images/levels/${id}/${name}')`;
    assert(registered[1].includes(reference), `Level ${id}: missing static import ${reference}`);
    const bytes = readFileSync(path.join(folder, name));
    assert(bytes.length > 0, `Level ${id}: empty ${name}`);
    if (name.endsWith('.png')) {
      assert(bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])), `Level ${id}: invalid PNG ${name}`);
      assert.equal(bytes.readUInt32BE(16), 1024, `Level ${id}: PNG width`);
      assert.equal(bytes.readUInt32BE(20), 1024, `Level ${id}: PNG height`);
    }
    bundle.update(name).update(bytes);
  }
  const data = JSON.parse(readFileSync(path.join(folder, 'data.json'), 'utf8'));
  assert.equal(String(data.id), id);
  assert.equal(data.has_reward, true);
  assert(data.palette.length > 1 && data.palette.length < 254, `Level ${id}: invalid palette size`);
  assert(data.palette.every(color => /^#[0-9a-f]{6}$/i.test(color)), `Level ${id}: invalid palette color`);
  assert(data.numbers.length > 0, `Level ${id}: no number labels`);
  for (const label of data.numbers) {
    assert(Number.isInteger(label.color_index) && label.color_index >= 0 && label.color_index < data.palette.length);
    assert.equal(label.number, label.color_index + 1);
    assert(label.x >= 0 && label.x < 1024 && label.y >= 0 && label.y < 1024);
  }
  // The user retained the original processor. Verify its exact output and inputs;
  // experimental beginner-mode visual reviews are historical, not release gates.
  const receipt = JSON.parse(readFileSync(path.join(generation, 'runs', id, 'processed-job.json'), 'utf8'));
  assert.equal(receipt.beginner_mode, false, `Level ${id}: experimental processing output`);
  assert.equal(receipt.processor_sha256, sha(readFileSync(path.join(root, 'image-processing/process.py'))));
  assert.equal(receipt.bundle_sha256, bundle.digest('hex'), `Level ${id}: game files differ from processed bundle`);
  for (const name of Object.values(files)) {
    assert.equal(sha(readFileSync(path.join(folder, name))),
      sha(readFileSync(path.join(root, 'image-processing/app_assets', id, name))),
      `Level ${id}: copied ${name} differs from processor output`);
  }
  const source = readFileSync(path.join(generation, 'sources', id, 'image.png'));
  const imageReview = JSON.parse(readFileSync(path.join(generation, 'reviews', `${id}-image.json`), 'utf8'));
  const videoReview = JSON.parse(readFileSync(path.join(generation, 'reviews', `${id}-video.json`), 'utf8'));
  assert.equal(imageReview.verdict, 'PASS');
  assert.equal(imageReview.engagement_revision, 2);
  if (number >= 41) assert.equal(imageReview.object_realism_revision, 1);
  assert.equal(imageReview.sha256, sha(source));
  assert.equal(receipt.image_sha256, sha(source));
  assert.equal(videoReview.verdict, 'PASS');
  assert.equal(videoReview.source_sha256, sha(source));
  assert.equal(videoReview.sha256, sha(readFileSync(path.join(folder, 'reward.mp4'))));
  assert.equal(receipt.video_sha256, videoReview.sha256);
  verified++;
}

console.log(`Verified ${verified}/30 new levels: explicit imports, original-processor receipts, files, metadata and source/video approvals.`);
if (missing.length) {
  console.log(`Not integrated yet: ${missing.join(', ')}`);
  if (!process.argv.includes('--allow-incomplete')) process.exitCode = 1;
}
