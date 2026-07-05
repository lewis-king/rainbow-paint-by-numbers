#!/usr/bin/env node

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const projectRoot = path.resolve(__dirname, '..');
const rawAssetsDir = path.join(projectRoot, 'image-processing', 'raw_assets');
const allowedAssetDirs = [
  path.join(projectRoot, 'assets'),
];
const defaultTargets = [
  path.join(projectRoot, 'android', 'app', 'build', 'outputs'),
  path.join(projectRoot, 'ios', 'build'),
  path.join(projectRoot, 'dist'),
];
const archiveExtensions = new Set(['.apk', '.aab', '.ipa', '.zip']);
const rawPathPattern = /(^|[\\/])(image-processing|raw_assets)([\\/]|$)/i;

function walkFiles(root) {
  if (!fs.existsSync(root)) return [];
  const stat = fs.statSync(root);
  if (stat.isFile()) return [root];

  const files = [];
  const stack = [root];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
      } else if (entry.isFile()) {
        files.push(fullPath);
      }
    }
  }
  return files;
}

function hashFile(filePath) {
  const hash = crypto.createHash('sha256');
  hash.update(fs.readFileSync(filePath));
  return hash.digest('hex');
}

function createFileIndex(files) {
  const index = new Map();

  for (const filePath of files) {
    const { size } = fs.statSync(filePath);
    const hash = hashFile(filePath);
    const entries = index.get(size) ?? new Map();
    const paths = entries.get(hash) ?? [];
    paths.push(path.relative(projectRoot, filePath));
    entries.set(hash, paths);
    index.set(size, entries);
  }

  return index;
}

function getUniqueRawAssetIndex() {
  const rawFiles = walkFiles(rawAssetsDir);
  const allowedHashes = new Set(
    allowedAssetDirs
      .flatMap(walkFiles)
      .map(hashFile)
  );
  const uniqueRawFiles = rawFiles.filter((filePath) => !allowedHashes.has(hashFile(filePath)));

  return createFileIndex(uniqueRawFiles);
}

function checkFile(filePath, rawIndex, findings, context = filePath) {
  const relativePath = path.relative(projectRoot, filePath);
  const normalizedContext = context.split(path.sep).join('/');

  if (rawPathPattern.test(relativePath) || rawPathPattern.test(normalizedContext)) {
    findings.push(`raw asset path found: ${normalizedContext}`);
    return;
  }

  const { size } = fs.statSync(filePath);
  const hashesForSize = rawIndex.get(size);
  if (!hashesForSize) return;

  const hash = hashFile(filePath);
  const rawMatches = hashesForSize.get(hash);
  if (!rawMatches) return;

  findings.push(
    `raw-only asset content found: ${normalizedContext} matches ${rawMatches.join(', ')}`
  );
}

function checkDirectory(root, rawIndex, findings) {
  for (const filePath of walkFiles(root)) {
    checkFile(filePath, rawIndex, findings);
  }
}

function unzipArchive(archivePath) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'raw-asset-check-'));
  const result = spawnSync('unzip', ['-qq', archivePath, '-d', tempDir], {
    encoding: 'utf8',
  });

  if (result.error) {
    throw new Error(`Unable to run unzip for ${archivePath}: ${result.error.message}`);
  }

  if (result.status !== 0) {
    throw new Error(`Unable to inspect ${archivePath}: ${result.stderr.trim()}`);
  }

  return tempDir;
}

function checkArchive(archivePath, rawIndex, findings) {
  const tempDir = unzipArchive(archivePath);
  try {
    for (const extractedFile of walkFiles(tempDir)) {
      const archiveEntry = path.relative(tempDir, extractedFile);
      checkFile(
        extractedFile,
        rawIndex,
        findings,
        `${path.relative(projectRoot, archivePath)}!/${archiveEntry}`
      );
    }
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

function parseArgs() {
  const args = process.argv.slice(2);
  const targets = [];
  let allowEmpty = false;

  for (const arg of args) {
    if (arg === '--allow-empty') {
      allowEmpty = true;
    } else {
      targets.push(path.resolve(projectRoot, arg));
    }
  }

  return {
    allowEmpty,
    targets: targets.length > 0 ? targets : defaultTargets,
  };
}

function main() {
  const { allowEmpty, targets } = parseArgs();
  const existingTargets = targets.filter(fs.existsSync);

  if (existingTargets.length === 0) {
    const message = `No build artifacts found to scan: ${targets
      .map((target) => path.relative(projectRoot, target))
      .join(', ')}`;

    if (allowEmpty) {
      console.log(message);
      return;
    }

    console.error(message);
    process.exit(1);
  }

  const rawIndex = getUniqueRawAssetIndex();
  const findings = [];

  for (const target of existingTargets) {
    if (fs.statSync(target).isDirectory()) {
      checkDirectory(target, rawIndex, findings);
      continue;
    }

    if (archiveExtensions.has(path.extname(target).toLowerCase())) {
      checkArchive(target, rawIndex, findings);
    } else {
      checkFile(target, rawIndex, findings);
    }
  }

  if (findings.length > 0) {
    console.error('Raw image-processing assets were found in build artifacts:');
    for (const finding of findings) {
      console.error(`- ${finding}`);
    }
    process.exit(1);
  }

  console.log('No raw image-processing assets found in scanned build artifacts.');
}

main();
