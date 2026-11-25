"""The level factory: recipe in, playable level out, with every gate enforced.

    venv/bin/python generation/factory.py status
    venv/bin/python generation/factory.py run 59-68        # do everything not blocked on review

One level moves through these stages. Each command is safe to repeat.

    add            write a new picture recipe into manifest.json
    submit image   queue the picture on ComfyUI (or `prepare` + comfy MCP + `record`)
    collect image  download the finished picture
    check image    source checks, build the numbered level, playability checks, review sheet
    review image   a person or vision model looks at the sheet and records PASS/FAIL
    submit video   queue the reward animation (needs the image gates)
    collect video
    check video    technical and motion checks, frame sheet
    review video
    cancel         take this factory's unfinished jobs off ComfyUI and free the GPU
    integrate      rebuild from the approved files, re-check everything, add to the app
                   (--replace swaps a factory level already in the app for a new attempt)
    refinish       run the current finishing pass over levels made before the factory
    verify         prove every integrated level still matches its records and passes

Nothing reaches assets/images/levels without passing the measured checks in
checks.py *and* a visual review bound to the exact file hashes. Changing a
picture, a video, a prompt or a seed invalidates the gates that depended on it.
`retry` archives an attempt and moves to a new seed.
"""
import argparse
import contextlib
import fcntl
import functools
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROCESSING = ROOT.parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PROCESSING))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import checks  # noqa: E402
import finish  # noqa: E402
from build_workflows import (IMAGE_MODEL, LEGACY_IMAGE_NEGATIVE, VIDEO_TEMPLATE, image_prompts,  # noqa: E402
                             qwen21_graph, qwen_original_graph, video_graph)
from durable_io import copy_file, save_json  # noqa: E402
from processing_resources import heavy_work_slot  # noqa: E402

FACTORY_REVISION = 1
COMFY_URL = os.environ.get('COMFYUI_URL', 'http://127.0.0.1:8188').rstrip('/')
MANIFEST = ROOT / 'manifest.json'
RUNS = ROOT / 'runs'
SOURCES = ROOT / 'sources'
LEVELS = REPO / 'assets' / 'images' / 'levels'
RAW = PROCESSING / 'raw_assets'
APP_ASSETS = PROCESSING / 'app_assets'
INDEX = ROOT / 'source-index.json'
REFINISHED = ROOT / 'refinished.json'
LEGACY = ROOT / 'legacy'
LOADER = REPO / 'utils' / 'level-loader.ts'
CATALOG = REPO / 'utils' / 'picture-catalog.json'
BUNDLE = ['data.json', 'original.png', 'lines.png', 'map.png', 'reward.mp4']
PLAYABLE = ['original.png', 'lines.png', 'map.png']
MODELS = {'image': 'qwen-image', 'video': 'wan2.2-i2v'}
EXTENSION = {'image': '.png', 'video': '.mp4'}
# VRAM ComfyUI must be able to claim before a job is queued. Queuing onto a GPU
# another program is using is how this workstation has frozen before.
VRAM_NEEDED_GIB = {'image': 20, 'video': 27}
KINDS = ('animal', 'object')
CATEGORIES = ('animals', 'fantasy', 'characters', 'vehicles', 'adventures', 'treats',
              'everyday', 'toys', 'nature')
REVIEW_CHECKLIST = {
    'image': [
        'Subject is instantly recognisable, cute and friendly for a 4-year-old; nothing scary',
        'Anatomy or structure is correct: right number of limbs, wheels, eyes; nothing malformed or fused',
        'Objects, vehicles, food and plants have no faces or limbs; animal faces look right',
        'No text, numerals, watermark or stray marks',
        'Numbered picture: every region is a sensible shape with a readable number, no clutter',
        'Painted picture matches the source: no lost features, ragged edges or wrong colours',
    ],
    'video': [
        'The subject moves in a charming, readable way and stays the same character throughout',
        'No extra or missing limbs, melting, morphing or flicker in any sampled frame',
        'No new objects, text or faces appear; objects still have no faces',
        'Subject stays inside the frame on a white background with a locked camera',
        'Nothing a parent would find odd or unsettling',
    ],
}


class Blocked(Exception):
    """A gate is not satisfied. The message says what to do next."""


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

@contextlib.contextmanager
def file_lock(path):
    """Exclusive across processes; released by the kernel if the holder dies."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def one_at_a_time(function):
    """Two factory processes never change the same level at once."""
    @functools.wraps(function)
    def guarded(level, *args, **kwargs):
        with file_lock(level.run / '.lock'):
            return function(level, *args, **kwargs)
    return guarded


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def sha_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read_json(path, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    return json.loads(path.read_text())


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def code_hashes():
    return {'process.py': sha(PROCESSING / 'process.py'), 'finish.py': sha(ROOT / 'finish.py'),
            'checks.py': sha(ROOT / 'checks.py')}


def bundle_sha(folder, names=BUNDLE):
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode())
        digest.update((Path(folder) / name).read_bytes())
    return digest.hexdigest()


def playable_sha(folder):
    """Identity of what the child plays: pixels, palette and numbers (not the video)."""
    data = read_json(Path(folder) / 'data.json')
    digest = hashlib.sha256(bundle_sha(folder, PLAYABLE).encode())
    digest.update(sha_json({k: data[k] for k in ('palette', 'numbers', 'dimensions')}).encode())
    return digest.hexdigest()


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

def load_manifest():
    manifest = read_json(MANIFEST)
    seen_ids, seen_slugs, seen_titles = set(), set(), {}
    catalog = read_json(CATALOG, {})
    for number, entry in catalog.items():
        seen_titles[entry['title'].lower()] = number
    for level in manifest['levels']:
        level_id = level.get('id')
        if not isinstance(level_id, str) or not level_id.isdecimal() or str(int(level_id)) != level_id:
            raise ValueError(f'Manifest level id must be a plain number string: {level_id!r}')
        if level_id in seen_ids or level.get('slug') in seen_slugs:
            raise ValueError(f'Duplicate manifest id or slug: {level_id} {level.get("slug")}')
        seen_ids.add(level_id)
        seen_slugs.add(level.get('slug'))
        if 'factory' not in level:
            continue  # levels 29-58 predate the factory; their records are historical
        for key in ('slug', 'title', 'category', 'kind', 'seed', 'image_prompt', 'video_prompt'):
            if not level.get(key) and level.get(key) != 0:
                raise ValueError(f'Level {level_id}: manifest field {key!r} is missing')
        if level['kind'] not in KINDS or level['category'] not in CATEGORIES:
            raise ValueError(f'Level {level_id}: kind must be one of {KINDS}, category one of {CATEGORIES}')
        if not all(c.isalnum() or c == '-' for c in level['slug']):
            raise ValueError(f'Level {level_id}: slug must be letters, digits and hyphens')
        owner = seen_titles.get(level['title'].lower())
        if owner is not None and owner != level_id:
            raise ValueError(f'Level {level_id}: the game already has a picture called {level["title"]!r} (level {owner})')
        seen_titles[level['title'].lower()] = level_id
    return manifest


def add_level(manifest, title, category, kind, subject, motion):
    """Append a recipe with the next free id. Prompts are built once and stored."""
    taken = {int(level['id']) for level in manifest['levels']} | {int(key) for key in read_json(CATALOG, {})}
    level_id = str(max(taken) + 1)
    slug = '-'.join(''.join(c if c.isalnum() else ' ' for c in title.lower()).split())
    image_prompt, image_negative = image_prompts(subject, kind)
    recipe = {
        'id': level_id, 'slug': slug, 'title': title, 'category': category, 'kind': kind, 'factory': FACTORY_REVISION,
        'added': time.strftime('%Y-%m-%d'), 'seed': int(time.strftime('%Y%m%d')) * 100 + int(level_id) % 100,
        'subject': subject.rstrip('. '), 'motion': motion.rstrip('. '),
        'image_prompt': image_prompt, 'image_negative': image_negative, 'image_model': IMAGE_MODEL,
        'video_prompt': VIDEO_TEMPLATE.format(motion=motion.rstrip('. ')),
    }
    with file_lock(RUNS / '.manifest.lock'):
        manifest['levels'].append(recipe)
        save_json(MANIFEST, manifest)
    load_manifest()  # rejects a duplicate title before anything is generated
    return recipe


def factory_levels(manifest, ids=None):
    levels = [level for level in manifest['levels'] if 'factory' in level]
    if ids:
        known = {level['id'] for level in levels}
        missing = [i for i in ids if i not in known]
        if missing:
            raise ValueError(f'Not factory levels in manifest.json: {missing}')
        levels = [level for level in levels if level['id'] in ids]
    return levels


def expand_ids(values):
    """`59 61 64` is a list; `59-68` is a range. Never guessed from two numbers."""
    if not values:
        return None
    ids = []
    for value in values:
        first, dash, last = value.partition('-')
        if dash and first.isdecimal() and last.isdecimal() and int(first) <= int(last):
            ids += [str(i) for i in range(int(first), int(last) + 1)]
        elif value.isdecimal():
            ids.append(value)
        else:
            raise ValueError(f'Not a level id or range: {value!r} (use 59 or 59-68)')
    return ids


# --------------------------------------------------------------------------
# ComfyUI over HTTP (the same server the comfy MCP drives)
# --------------------------------------------------------------------------

def comfy(path, data=None, timeout=60):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(COMFY_URL + path, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def comfy_upload(path, name, subfolder):
    boundary = uuid.uuid4().hex
    parts = []
    for field, value in (('subfolder', subfolder), ('overwrite', 'true'), ('type', 'input')):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
                 f'Content-Type: image/png\r\n\r\n'.encode() + Path(path).read_bytes() + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    request = urllib.request.Request(COMFY_URL + '/upload/image', data=b''.join(parts),
                                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.load(response)
    return f"{result['subfolder']}/{result['name']}" if result.get('subfolder') else result['name']


def comfy_download(output, target):
    query = urllib.parse.urlencode({'filename': output['filename'], 'subfolder': output.get('subfolder', ''),
                                    'type': output.get('type', 'output')})
    temporary = Path(target).with_suffix(Path(target).suffix + '.part')
    with urllib.request.urlopen(f'{COMFY_URL}/view?{query}', timeout=300) as response, open(temporary, 'wb') as stream:
        shutil.copyfileobj(response, stream)
    copy_file(temporary, target)
    temporary.unlink()


def gpu_headroom_gib():
    """VRAM ComfyUI can use right now.

    While ComfyUI is working through its queue the GPU is already its own, and a
    new job simply waits its turn. When it is idle it may still be holding the last
    models it used, so it is asked to release them before free memory is read;
    what remains in use then belongs to some other program.
    """
    queue = comfy('/queue')
    if queue['queue_running'] or queue['queue_pending']:
        return float('inf')
    free = comfy('/system_stats')['devices'][0]['vram_free'] / 2 ** 30
    if free < max(VRAM_NEEDED_GIB.values()):
        request = urllib.request.Request(COMFY_URL + '/free', data=json.dumps(
            {'unload_models': True, 'free_memory': True}).encode(), headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(request, timeout=60).close()
        time.sleep(4)
        free = comfy('/system_stats')['devices'][0]['vram_free'] / 2 ** 30
    return free


def wait_for_gpu(stage, wait_minutes):
    needed = VRAM_NEEDED_GIB[stage]
    deadline = time.time() + wait_minutes * 60
    announced = False
    while True:
        headroom = gpu_headroom_gib()
        if headroom >= needed:
            return
        if time.time() >= deadline:
            raise Blocked(f'GPU is busy: {headroom:.1f} GiB free, {stage} generation needs {needed}. '
                          'Another program is using it. Retry later or pass --wait-gpu MINUTES.')
        if not announced:
            print(f'GPU busy ({headroom:.1f} GiB free, {needed} needed); waiting up to {wait_minutes:g} min', flush=True)
            announced = True
        time.sleep(30)


# --------------------------------------------------------------------------
# Per-level state
# --------------------------------------------------------------------------

class Level:
    def __init__(self, recipe):
        self.recipe = recipe
        self.id = recipe['id']
        self.run = RUNS / self.id
        self.image = self.run / 'image.png'
        self.video = self.run / 'video.mp4'
        self.candidate = self.run / 'level' / self.id

    def artifact(self, stage):
        return self.image if stage == 'image' else self.video

    def seed(self, stage):
        return self.recipe['seed'] if stage == 'image' else self.recipe.get('video_seed', self.recipe['seed'])

    def input_name(self):
        return f'{self.id}-{sha(self.image)[:12]}.png'

    def graph(self, stage):
        prefix = f"rainbow-paint-by-numbers/{stage}/{self.id}-{self.recipe['slug']}"
        if stage == 'image':
            if self.recipe.get('image_model') == IMAGE_MODEL:
                return qwen21_graph(self.recipe['image_prompt'], self.recipe['seed'], prefix, self.recipe['image_negative'])
            return qwen_original_graph(self.recipe['image_prompt'], self.recipe['seed'], prefix,
                                       self.recipe.get('image_negative', LEGACY_IMAGE_NEGATIVE))
        if not self.image.is_file():
            raise Blocked(f'{self.id}: no image yet')
        return video_graph(f'rainbow-paint-by-numbers/{self.input_name()}', self.recipe['video_prompt'],
                           self.seed('video'), prefix)

    def job(self, stage):
        return read_json(self.run / f'{stage}-job.json')

    def model(self, stage):
        return self.recipe.get('image_model', MODELS['image']) if stage == 'image' else MODELS['video']

    def generated(self, stage):
        """The stage output exists and was produced by the current recipe."""
        job = self.job(stage)
        artifact = self.artifact(stage)
        if not job or job.get('status') != 'completed' or not artifact.is_file():
            return False
        if job.get('sha256') != sha(artifact):
            raise Blocked(f'{self.id}: {artifact.name} changed after generation; run `retry {self.id} {stage}`')
        return job.get('graph_sha256') == sha_json(self.graph(stage))

    def report(self, name):
        return read_json(self.run / f'{name}-check.json')

    def check_current(self, name):
        saved = self.report(name)
        if not saved or saved.get('code') != code_hashes():
            return None
        if saved.get('image_sha256') != sha(self.image):
            return None
        if name == 'video' and saved.get('video_sha256') != sha(self.video):
            return None
        if name == 'level' and (not self.candidate.is_dir() or saved.get('playable_sha256') != playable_sha(self.candidate)):
            return None
        return saved

    def review(self, stage):
        saved = read_json(self.run / f'{stage}-review.json')
        if not saved or saved.get('image_sha256') != sha(self.image):
            return None
        if stage == 'image':
            if not self.candidate.is_dir() or saved.get('playable_sha256') != playable_sha(self.candidate):
                return None
        elif saved.get('video_sha256') != sha(self.video):
            return None
        return saved

    def image_gate(self):
        """Raises Blocked unless the picture passed every check and its review."""
        if not self.generated('image'):
            raise Blocked(f'{self.id}: picture not generated with the current recipe')
        for name in ('image', 'level'):
            saved = self.check_current(name)
            if saved is None:
                raise Blocked(f'{self.id}: run `check image {self.id}`')
            if saved['verdict'] != 'PASS':
                raise Blocked(f"{self.id}: {name} check failed: {'; '.join(saved['failures'])}")
        review = self.review('image')
        if review is None:
            raise Blocked(f'{self.id}: picture needs a visual review of {self.run / "review-image.jpg"}')
        if review['verdict'] != 'PASS':
            raise Blocked(f'{self.id}: picture was rejected in review; run `retry {self.id} image`')

    def video_gate(self):
        self.image_gate()
        if not self.generated('video'):
            raise Blocked(f'{self.id}: reward video not generated from the approved picture')
        saved = self.check_current('video')
        if saved is None:
            raise Blocked(f'{self.id}: run `check video {self.id}`')
        if saved['verdict'] != 'PASS':
            raise Blocked(f"{self.id}: video check failed: {'; '.join(saved['failures'])}")
        review = self.review('video')
        if review is None:
            raise Blocked(f'{self.id}: video needs a visual review of {self.run / "review-video.jpg"}')
        if review['verdict'] != 'PASS':
            raise Blocked(f'{self.id}: video was rejected in review; run `retry {self.id} video`')

    def integrated(self):
        receipt = read_json(SOURCES / self.id / 'receipt.json')
        if not (receipt and receipt.get('factory_revision') and (LEVELS / self.id / 'data.json').is_file()):
            return False
        # After a retry the app still holds the earlier version; the level is in progress again.
        shipped = read_json(SOURCES / self.id / 'recipe.json') or {}
        return all(shipped.get(key) == self.recipe.get(key) for key in ('seed', 'video_seed', 'image_prompt', 'video_prompt'))

    def status(self):
        if self.integrated():
            return 'integrated'
        for gate, stage in ((self.image_gate, 'image'), (self.video_gate, 'video')):
            try:
                gate()
            except Blocked as blocked:
                job = self.job(stage)
                if job and job.get('status') == 'queued' and not self.artifact(stage).is_file():
                    return f'{stage} queued on ComfyUI ({job["prompt_id"]})'
                return str(blocked).split(': ', 1)[1]
        return 'ready to integrate'


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def prepare(level, stage):
    """Write the exact graph (uploading the source picture for a video). Returns its path."""
    if stage == 'video':
        level.image_gate()
        comfy_upload(level.image, level.input_name(), 'rainbow-paint-by-numbers')
    if level.generated(stage):
        raise Blocked(f'{level.id}: {stage} already generated; `retry {level.id} {stage}` to replace it')
    job = level.job(stage)
    if job and job.get('status') == 'queued' and job.get('graph_sha256') == sha_json(level.graph(stage)):
        raise Blocked(f'{level.id}: {stage} is already queued ({job["prompt_id"]}); `collect {stage} {level.id}`')
    if job or level.artifact(stage).exists():
        raise Blocked(f'{level.id}: a previous {stage} attempt exists (or its recipe changed); '
                      f'run `retry {level.id} {stage}` to archive it first')
    path = level.run / f'{stage}.api.json'
    save_json(path, level.graph(stage))
    return path


def record(level, stage, prompt_id):
    if level.job(stage) or level.artifact(stage).exists():
        raise Blocked(f'{level.id}: a {stage} job is already recorded; `retry {level.id} {stage}` starts a new attempt')
    graph = read_json(level.run / f'{stage}.api.json')
    if graph is None or sha_json(graph) != sha_json(level.graph(stage)):
        raise Blocked(f'{level.id}: run `prepare {stage} {level.id}` before recording a job')
    save_json(level.run / f'{stage}-job.json', {
        'id': level.id, 'stage': stage, 'model': level.model(stage), 'prompt_id': prompt_id, 'status': 'queued',
        'graph_sha256': sha_json(graph), 'seed': level.seed(stage), 'submitted_at': now()})


@one_at_a_time
def submit(level, stage, wait_gpu):
    job = level.job(stage)
    if job and job.get('status') == 'queued' and job.get('graph_sha256') == sha_json(level.graph(stage)):
        print(f'{level.id}: {stage} already queued ({job["prompt_id"]})')
        return
    path = prepare(level, stage)
    wait_for_gpu(stage, wait_gpu)
    if level.job(stage) or level.artifact(stage).exists():
        raise Blocked(f'{level.id}: {stage} was started by another process while waiting for the GPU')
    result = comfy('/prompt', {'prompt': read_json(path), 'client_id': 'rainbow-factory'})
    if result.get('node_errors'):
        raise RuntimeError(f'ComfyUI rejected the {stage} graph for {level.id}: {result["node_errors"]}')
    record(level, stage, result['prompt_id'])
    print(f'{level.id}: {stage} queued ({result["prompt_id"]})', flush=True)


def collect(level, stage, wait_minutes=0):
    """Returns True when the output is on disk."""
    job = level.job(stage)
    if not job:
        raise Blocked(f'{level.id}: no {stage} job recorded')
    if job['status'] == 'completed':
        return True
    if job['status'] == 'error':
        raise Blocked(f"{level.id}: {stage} generation failed ({job.get('error')}); run `retry {level.id} {stage}`")
    prompt_id = job['prompt_id']
    deadline = time.time() + wait_minutes * 60
    while True:
        try:
            history = comfy('/history/' + prompt_id)
            if prompt_id in history:
                break
            queue = comfy('/queue')
            live = any(item[1] == prompt_id for item in queue['queue_running'] + queue['queue_pending'])
            if not live and prompt_id not in comfy('/history/' + prompt_id):
                job.update(status='error', error='job vanished from the ComfyUI queue and history (server restarted?)')
                save_json(level.run / f'{stage}-job.json', job)
                raise Blocked(f'{level.id}: {job["error"]}; run `retry {level.id} {stage}`')
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            print(f'ComfyUI not answering ({error}); still waiting', flush=True)
        if time.time() >= deadline:
            return False
        time.sleep(10)
    return _store_output(level, stage, history[prompt_id])


@one_at_a_time
def _store_output(level, stage, result):
    job = level.job(stage)
    if job['status'] == 'completed':
        return True  # another process collected it while this one was waiting
    if result.get('status', {}).get('status_str') == 'error':
        job.update(status='error', error=str(result['status'].get('messages', ''))[-600:])
        save_json(level.run / f'{stage}-job.json', job)
        raise Blocked(f'{level.id}: {stage} generation failed on ComfyUI; run `retry {level.id} {stage}`')
    outputs = [item for node in result.get('outputs', {}).values() for key in ('images', 'gifs', 'videos')
               for item in node.get(key, []) if item.get('filename', '').endswith(EXTENSION[stage])]
    if len(outputs) != 1:
        raise RuntimeError(f'{level.id}: expected one {EXTENSION[stage]} output, got {len(outputs)}')
    target = level.artifact(stage)
    comfy_download(outputs[0], target)
    job.update(comfy_output=outputs[0], comfy_sha256=sha(target))
    if stage == 'image':
        # Keep exactly what the model drew, and give the subject a margin if it has none.
        framed = finish.frame_picture(cv2.imread(str(target), cv2.IMREAD_COLOR))
        if framed is not None:
            copy_file(target, level.run / 'image-as-generated.png')
            cv2.imwrite(str(target), framed)
            job['reframed'] = True
    job.update(status='completed', finished_at=now(), sha256=sha(target))
    save_json(level.run / f'{stage}-job.json', job)
    print(f'{level.id}: {stage} collected', flush=True)
    return True


def comfy_post(path, data):
    request = urllib.request.Request(COMFY_URL + path, data=json.dumps(data).encode(),
                                     headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(request, timeout=60).close()


def cancel(levels):
    """Give the GPU back: remove this factory's unfinished jobs from ComfyUI.

    Only jobs recorded in these levels' receipts are touched; anything else in
    the ComfyUI queue belongs to someone else and is left alone. The receipts
    are removed so the same recipes can simply be submitted again later.
    """
    mine = {}
    for level in levels:
        for stage in ('image', 'video'):
            job = level.job(stage)
            if job and job.get('status') == 'queued':
                mine[job['prompt_id']] = (level, stage)
    if not mine:
        print('No factory jobs are queued.')
        return
    queue = comfy('/queue')
    pending = [item[1] for item in queue['queue_pending'] if item[1] in mine]
    if pending:
        comfy_post('/queue', {'delete': pending})
    running = [item[1] for item in queue['queue_running'] if item[1] in mine]
    if running:
        comfy_post('/interrupt', {'prompt_id': running[0]})
    time.sleep(3)
    for prompt_id, (level, stage) in mine.items():
        done = comfy('/history/' + prompt_id).get(prompt_id, {})
        if done.get('status', {}).get('status_str') == 'success':
            print(f'{level.id}: {stage} had already finished; `collect {stage} {level.id}`')
            continue
        with file_lock(level.run / '.lock'):
            for name in (f'{stage}-job.json', f'{stage}.api.json'):
                (level.run / name).unlink(missing_ok=True)
        print(f'{level.id}: {stage} job cancelled')
    still = comfy('/queue')
    if not still['queue_running'] and not still['queue_pending']:
        comfy_post('/free', {'unload_models': True, 'free_memory': True})
        print('ComfyUI is idle; its models were unloaded from the GPU.')


# --------------------------------------------------------------------------
# Building and checking
# --------------------------------------------------------------------------

def build_level(level_id, input_dir, output_dir):
    """process.py (unchanged) then the finishing pass. Returns finish statistics."""
    target = Path(output_dir) / level_id
    if target.exists():
        shutil.rmtree(target)
    script = ('import process, sys; process.INPUT_DIR, process.OUTPUT_DIR = sys.argv[1:3]; '
              'process.process_level(sys.argv[3] + ".png")')
    environment = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4')
    with heavy_work_slot():
        done = subprocess.run([sys.executable, '-c', script, str(input_dir), str(output_dir), level_id],
                              cwd=PROCESSING, env=environment, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f'process.py failed for {level_id}:\n{done.stdout[-800:]}\n{done.stderr[-1500:]}')
    return finish.finish_level(target, source=Path(input_dir) / f'{level_id}.png')


def _number_view(folder, width):
    """The unpainted picture as GameCanvas.tsx draws it, at `width` screen pixels."""
    data = read_json(folder / 'data.json')
    lines = cv2.imread(str(folder / 'lines.png'), cv2.IMREAD_UNCHANGED)
    view = np.full((checks.SIZE, checks.SIZE, 3), checks.UNPAINTED_RGB[::-1], np.uint8)
    alpha = lines[..., 3] > 0
    view[alpha] = lines[alpha][:, :3]
    view = cv2.resize(view, (width, width), interpolation=cv2.INTER_AREA)
    scale = width / checks.SIZE
    zoom = width / checks.PHONE_CANVAS
    for label in data['numbers']:
        small = checks._label_scale(label)
        origin = (int(round(label['x'] * scale + checks.GLYPH_LEFT * small * zoom)),
                  int(round(label['y'] * scale + checks.GLYPH_BASELINE * small * zoom)))
        cv2.putText(view, str(label['number']), origin, cv2.FONT_HERSHEY_SIMPLEX,
                    0.29 * zoom * small, (102, 102, 102), max(1, round(0.65 * zoom * small)), cv2.LINE_AA)
    return view


def image_sheet(level):
    """Source | numbered (3x phone) | painted, with the palette and a true-size phone view."""
    folder = level.candidate
    data = read_json(folder / 'data.json')
    size = 3 * checks.PHONE_CANVAS
    source = cv2.resize(cv2.imread(str(level.image)), (size, size), interpolation=cv2.INTER_AREA)
    painted = cv2.resize(cv2.imread(str(folder / 'original.png')), (size, size), interpolation=cv2.INTER_AREA)
    strip = np.full((checks.PHONE_CANVAS + 16, 3 * size, 3), 46, np.uint8)
    strip[8:8 + checks.PHONE_CANVAS, 8:8 + checks.PHONE_CANVAS] = _number_view(folder, checks.PHONE_CANVAS)
    cv2.putText(strip, 'true phone size', (8, checks.PHONE_CANVAS + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    for index, color in enumerate(data['palette']):
        r, g, b = checks._hex_rgb(color)
        centre = (checks.PHONE_CANVAS + 70 + index * 120, 90)
        cv2.circle(strip, centre, 48, (b, g, r), -1)
        text = (0, 0, 0) if 0.299 * r + 0.587 * g + 0.114 * b > 128 else (255, 255, 255)
        cv2.putText(strip, str(index + 1), (centre[0] - 14 * len(str(index + 1)), centre[1] + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, text, 3, cv2.LINE_AA)
    cv2.putText(strip, f"{level.id} {level.recipe['title']} ({level.recipe['kind']})  -  {len(data['palette'])} colours, "
                f"{len(data['numbers'])} numbers", (checks.PHONE_CANVAS + 30, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                (235, 235, 235), 2, cv2.LINE_AA)
    sheet = np.vstack([np.hstack([source, _number_view(folder, size), painted]), strip])
    path = level.run / 'review-image.jpg'
    cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return path


def video_sheet(level):
    """The source picture followed by 15 evenly spaced frames, first and last included."""
    frames = checks.read_frames(level.video, 384)
    picks = np.linspace(0, len(frames) - 1, 15).round().astype(int)
    tiles = [cv2.resize(cv2.imread(str(level.image)), (384, 384), interpolation=cv2.INTER_AREA)]
    cv2.putText(tiles[0], 'source', (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    for pick in picks:
        tile = frames[pick].copy()
        cv2.putText(tile, f'frame {pick}', (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        tiles.append(tile)
    sheet = np.vstack([np.hstack(tiles[row:row + 4]) for row in range(0, 16, 4)])
    path = level.run / 'review-video.jpg'
    cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return path


@one_at_a_time
def check_image(level):
    if not level.generated('image'):
        raise Blocked(f'{level.id}: picture not generated with the current recipe')
    image_sha = sha(level.image)
    result = checks.check_image(level.image)
    save_json(level.run / 'image-check.json', dict(result, id=level.id, image_sha256=image_sha,
                                                   code=code_hashes(), checked_at=now()))
    if result['verdict'] != 'PASS':
        return False, result['failures']
    staging = level.run / 'level-input'
    staging.mkdir(parents=True, exist_ok=True)
    copy_file(level.image, staging / f'{level.id}.png')
    try:
        stats = build_level(level.id, staging, level.run / 'level')
    except (RuntimeError, ValueError) as error:
        save_json(level.run / 'level-check.json', dict(checks.report({}, [f'Level could not be built: {error}']),
                                                       id=level.id, image_sha256=image_sha, code=code_hashes()))
        return False, [str(error)]
    result = checks.check_level(level.candidate, source=level.image, level_id=level.id)
    save_json(level.run / 'level-check.json', dict(
        result, id=level.id, image_sha256=image_sha, playable_sha256=playable_sha(level.candidate),
        finish=stats, code=code_hashes(), checked_at=now()))
    image_sheet(level)
    return result['verdict'] == 'PASS', result['failures']


@one_at_a_time
def check_video(level):
    level.image_gate()
    if not level.generated('video'):
        raise Blocked(f'{level.id}: reward video not generated from the approved picture')
    result = checks.check_video(level.video, level.image)
    save_json(level.run / 'video-check.json', dict(
        result, id=level.id, image_sha256=sha(level.image), video_sha256=sha(level.video),
        code=code_hashes(), checked_at=now()))
    if result['metrics'].get('frames', 0) >= 30:
        video_sheet(level)
    return result['verdict'] == 'PASS', result['failures']


@one_at_a_time
def review(level, stage, verdict, reviewer, notes):
    if stage == 'image':
        gates = [level.check_current('image'), level.check_current('level')]
    else:
        level.image_gate()
        gates = [level.check_current('video')]
    if any(g is None for g in gates):
        raise Blocked(f'{level.id}: run `check {stage} {level.id}` first; the files changed or were never checked')
    if verdict == 'PASS' and any(g['verdict'] != 'PASS' for g in gates):
        raise Blocked(f'{level.id}: measured checks failed; a review cannot override them')
    sheet = level.run / f'review-{stage}.jpg'
    if not sheet.is_file():
        raise Blocked(f'{level.id}: no review sheet; run `check {stage} {level.id}`')
    if not notes:
        raise Blocked('A review needs at least one --note saying what was seen')
    saved = {'id': level.id, 'stage': stage, 'verdict': verdict, 'reviewer': reviewer, 'notes': notes,
             'checklist': REVIEW_CHECKLIST[stage], 'image_sha256': sha(level.image),
             'sheet_sha256': sha(sheet), 'reviewed_at': now()}
    if stage == 'image':
        saved['playable_sha256'] = playable_sha(level.candidate)
    else:
        saved['video_sha256'] = sha(level.video)
    save_json(level.run / f'{stage}-review.json', saved)


def retry(manifest, level, stage, seed, reason, keep_seed=False, subject=None, motion=None):
    """Archive this attempt (and what depended on it) and move to a new seed."""
    with file_lock(RUNS / '.manifest.lock'), file_lock(level.run / '.lock'):
        # Another process may have changed other levels since this one read the manifest.
        manifest = load_manifest()
        level.recipe = next(recipe for recipe in manifest['levels'] if recipe['id'] == level.id)
        _retry(manifest, level, stage, seed, reason, keep_seed, subject, motion)


def _retry(manifest, level, stage, seed, reason, keep_seed, subject, motion):
    names = ['video.mp4', 'video.api.json', 'video-job.json', 'video-check.json', 'video-review.json', 'review-video.jpg']
    if stage == 'image':
        names += ['image.png', 'image-as-generated.png', 'image.api.json', 'image-job.json', 'image-check.json', 'level-check.json',
                  'image-review.json', 'review-image.jpg', 'level', 'level-input']
    present = [name for name in names if (level.run / name).exists()]
    if present:
        attempts = level.run / 'attempts'
        number = len(list(attempts.glob('*'))) + 1 if attempts.is_dir() else 1
        archive = attempts / f'{number:02d}-{stage}'
        archive.mkdir(parents=True)
        for name in present:
            shutil.move(str(level.run / name), str(archive / name))
        save_json(archive / 'recipe.json', dict(level.recipe, retry_reason=reason))
    if subject:
        level.recipe['subject'] = subject.rstrip('. ')
    if stage == 'image' and level.recipe.get('subject'):
        # a new picture always uses the current prompt template
        level.recipe['image_prompt'], level.recipe['image_negative'] = image_prompts(
            level.recipe['subject'], level.recipe['kind'])
        level.recipe['image_model'] = IMAGE_MODEL
    if motion:
        level.recipe['motion'] = motion.rstrip('. ')
        level.recipe['video_prompt'] = VIDEO_TEMPLATE.format(motion=level.recipe['motion'])
    key = 'seed' if stage == 'image' else 'video_seed'
    old = level.seed(stage)
    level.recipe[key] = old if keep_seed else seed if seed is not None else old + 1000
    level.recipe.setdefault('history', []).append(
        {'at': now(), 'stage': stage, 'seed_was': old, 'reason': reason})
    if stage == 'image':
        level.recipe.pop('video_seed', None)
    save_json(MANIFEST, manifest)
    print(f'{level.id}: {stage} attempt archived; next seed {level.recipe[key]}')


# --------------------------------------------------------------------------
# Integration
# --------------------------------------------------------------------------

def loader_entry(level_id):
    keys = zip(['data', 'original', 'lines', 'map', 'reward'], BUNDLE)
    body = ''.join(f"    {key}: require('@/assets/images/levels/{level_id}/{name}'),\n" for key, name in keys)
    return f"  '{level_id}': {{\n{body}  }},\n"


@one_at_a_time
def integrate(level, replace=False):
    """`replace` swaps a level this factory put in the app for a newer attempt.
    Only for levels that have not been released: the picture itself changes."""
    level.video_gate()
    made_here = (read_json(SOURCES / level.id / 'receipt.json') or {}).get('factory_revision')
    replace = bool(replace and made_here)
    code = code_hashes()
    # Re-measure everything from the files rather than trusting saved reports.
    fresh = {'image': checks.check_image(level.image), 'video': checks.check_video(level.video, level.image)}
    for name, result in fresh.items():
        if result['verdict'] != 'PASS':
            raise Blocked(f"{level.id}: {name} check no longer passes: {'; '.join(result['failures'])}")
    for stage in ('image', 'video'):
        target = RAW / f'{level.id}{EXTENSION[stage]}'
        if target.exists() and sha(target) != sha(level.artifact(stage)) and not replace:
            raise Blocked(f'{target} already exists with different content; `integrate --replace {level.id}` '
                          f'swaps a factory level that has not been released')
        copy_file(level.artifact(stage), target)
    final = APP_ASSETS / level.id
    stats = build_level(level.id, RAW, APP_ASSETS)
    if playable_sha(final) != playable_sha(level.candidate):
        raise Blocked(f'{level.id}: the rebuilt level differs from the one that was reviewed; '
                      f'run `check image {level.id}` and review it again')
    result = checks.check_level(final, source=level.image, level_id=level.id, require_reward=True)
    if result['verdict'] != 'PASS':
        raise Blocked(f"{level.id}: final level fails: {'; '.join(result['failures'])}")
    if sha(final / 'reward.mp4') != sha(level.video):
        raise Blocked(f'{level.id}: reward.mp4 is not the reviewed video')
    fresh['level'] = result

    destination = LEVELS / level.id
    if destination.exists() and not replace and any(
            not (destination / name).is_file() or sha(destination / name) != sha(final / name) for name in BUNDLE):
        raise Blocked(f'{destination} already holds different files; refusing to overwrite a shipped level')
    loader = LOADER.read_text()
    marker = '};\n\nexport const LEVEL_IDS'
    if f"  '{level.id}': {{" not in loader and marker not in loader:
        raise Blocked('utils/level-loader.ts no longer has the registry marker the factory inserts before')
    catalog = read_json(CATALOG)

    destination.mkdir(parents=True, exist_ok=True)
    for name in BUNDLE:
        copy_file(final / name, destination / name)
    if f"  '{level.id}': {{" not in loader:
        LOADER.write_text(loader.replace(marker, loader_entry(level.id) + marker, 1))
    catalog[level.id] = {'title': level.recipe['title'], 'category': level.recipe['category']}
    ordered = {key: catalog[key] for key in sorted(catalog, key=int)}
    save_json(CATALOG, ordered)

    record_dir = SOURCES / level.id
    for name in ('image.png', 'image.api.json', 'image-job.json', 'image-review.json', 'review-image.jpg',
                 'video.mp4', 'video.api.json', 'video-job.json', 'video-review.json', 'review-video.jpg'):
        copy_file(level.run / name, record_dir / name)
    save_json(record_dir / 'recipe.json', level.recipe)
    for name, result in fresh.items():
        save_json(record_dir / f'{name}-check.json', result)
    save_json(record_dir / 'receipt.json', {
        'id': level.id, 'title': level.recipe['title'], 'factory_revision': FACTORY_REVISION,
        'integrated_at': now(), 'models': {stage: level.model(stage) for stage in MODELS}, 'code': code, 'finish': stats,
        'image_sha256': sha(level.image), 'video_sha256': sha(level.video),
        'playable_sha256': playable_sha(final), 'bundle_sha256': bundle_sha(final),
        'files': {name: sha(final / name) for name in BUNDLE},
        'bytes': {name: (final / name).stat().st_size for name in BUNDLE},
        'reviews': {stage: {'reviewer': level.review(stage)['reviewer'], 'sha256': sha(level.run / f'{stage}-review.json')}
                    for stage in ('image', 'video')}})
    index = [entry for entry in read_json(INDEX, []) if entry['id'] != level.id]
    index.append({'id': level.id, 'title': level.recipe['title'], 'sha256': sha(level.image),
                  'video_sha256': sha(level.video)})
    save_json(INDEX, sorted(index, key=lambda entry: int(entry['id'])))
    print(f'{level.id}: integrated as "{level.recipe["title"]}"', flush=True)


def refinish(level_id):
    """Run the current finishing pass over a level made before the factory.

    The art, title and reward stay; the numbered picture is rebuilt from the
    level as process.py first made it (kept in legacy/ID) and the source picture,
    so running it again with a newer finish.py never builds on an earlier pass. Check failures are recorded, not
    enforced: these pictures were approved long ago and are simplified as far
    as the art allows. Saved progress survives, because the game stores which
    pixels were painted and reads their colour from the new map."""
    if (read_json(SOURCES / level_id / 'receipt.json') or {}).get('factory_revision'):
        raise Blocked(f'{level_id}: a factory level; `check image {level_id}` rebuilds it')
    folder, source = LEVELS / level_id, RAW / f'{level_id}.png'
    if not (folder / 'data.json').is_file() or not source.is_file():
        raise Blocked(f'{level_id}: needs {folder} and {source}')
    with file_lock(RUNS / '.refinish.lock'):
        records = read_json(REFINISHED, {})
        names = ['data.json'] + PLAYABLE
        saved = records.get(level_id)
        if (saved and saved['finish_revision'] == finish.REVISION
                and all(sha(folder / name) == saved['files'][name] for name in names)):
            print(f'{level_id}: already at finish revision {finish.REVISION}', flush=True)
            return saved
        first = LEGACY / level_id
        if not first.is_dir():
            if saved:
                raise Blocked(f'{level_id}: {first} is missing; restore the level as process.py made it')
            for name in names:
                copy_file(folder / name, first / name)
        work = RUNS / 'refinish' / level_id
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        for name in names:
            copy_file(first / name, work / name)
        if (folder / 'reward.mp4').is_file():
            copy_file(folder / 'reward.mp4', work / 'reward.mp4')
        before = read_json(first / 'data.json')
        try:
            stats = finish.finish_level(work, source=source)
        except ValueError as error:
            raise Blocked(f'{level_id}: could not be finished: {error}')
        result = checks.check_level(work, source=source, level_id=level_id, require_reward=True)
        after = read_json(work / 'data.json')
        for name in names + (['debug_preview.png'] if (folder / 'debug_preview.png').is_file() else []):
            copy_file(work / name, folder / name)
        records[level_id] = {
            'finish_revision': finish.REVISION, 'refinished_at': now(), 'source_sha256': sha(source),
            'files': {name: sha(folder / name) for name in names}, 'playable_sha256': playable_sha(folder),
            'numbers': [len(before['numbers']), len(after['numbers'])],
            'colours': [len(before['palette']), len(after['palette'])],
            'verdict': result['verdict'], 'failures': result['failures'], 'finish': stats}
        save_json(REFINISHED, {key: records[key] for key in sorted(records, key=int)})
        shutil.rmtree(work)
    print(f"{level_id}: {len(before['numbers'])} -> {len(after['numbers'])} numbers, {len(after['palette'])} colours, "
          f"checks {result['verdict']}" + ''.join(f'\n    {failure}' for failure in result['failures']), flush=True)
    return records[level_id]


def verify_level(level_id):
    """Everything a release depends on, recomputed from the committed files."""
    problems = []
    record_dir = SOURCES / level_id
    receipt = read_json(record_dir / 'receipt.json')
    folder = LEVELS / level_id
    for name in BUNDLE:
        if not (folder / name).is_file():
            problems.append(f'missing {name}')
        elif sha(folder / name) != receipt['files'][name]:
            problems.append(f'{name} differs from the integrated file')
    if problems:
        return problems
    if sha(record_dir / 'image.png') != receipt['image_sha256'] or sha(record_dir / 'video.mp4') != receipt['video_sha256']:
        problems.append('preserved source picture or video differs from the receipt')
    if sha(folder / 'reward.mp4') != receipt['video_sha256']:
        problems.append('reward.mp4 is not the approved video')
    for stage in ('image', 'video'):
        saved = read_json(record_dir / f'{stage}-review.json')
        if not saved or saved.get('verdict') != 'PASS' or saved.get('image_sha256') != receipt['image_sha256']:
            problems.append(f'{stage} review missing, failed or for a different picture')
        elif stage == 'image' and saved.get('playable_sha256') != playable_sha(folder):
            problems.append('numbered picture differs from the one reviewed')
        elif stage == 'video' and saved.get('video_sha256') != receipt['video_sha256']:
            problems.append('video review is for a different video')
    for name, result in (('image', checks.check_image(record_dir / 'image.png')),
                         ('level', checks.check_level(folder, source=record_dir / 'image.png', level_id=level_id, require_reward=True)),
                         ('video', checks.check_video(folder / 'reward.mp4', record_dir / 'image.png'))):
        problems += [f'{name} check: {failure}' for failure in result['failures']]
    if loader_entry(level_id) not in LOADER.read_text():
        problems.append('utils/level-loader.ts entry missing or altered')
    recipe = read_json(record_dir / 'recipe.json')
    if read_json(CATALOG).get(level_id) != {'title': recipe['title'], 'category': recipe['category']}:
        problems.append('utils/picture-catalog.json entry missing or altered')
    return problems


def verify(ids=None):
    loader = LOADER.read_text()
    catalog = read_json(CATALOG)
    folders = sorted((p.name for p in LEVELS.iterdir() if p.is_dir()), key=int)
    failed = False
    for level_id in folders:
        registered = f"  '{level_id}': {{" in loader
        if not registered or level_id not in catalog:
            print(f'{level_id}: FAIL in assets but {"not registered in level-loader.ts" if not registered else "has no title in picture-catalog.json"}')
            failed = True
    for level_id in catalog:
        if level_id not in folders:
            print(f'{level_id}: FAIL listed in picture-catalog.json with no level folder')
            failed = True
    made = sorted((p.name for p in SOURCES.iterdir() if (p / 'receipt.json').is_file()
                   and read_json(p / 'receipt.json').get('factory_revision')), key=int)
    for level_id in made:
        if ids and level_id not in ids:
            continue
        problems = verify_level(level_id)
        print(f'{level_id}: {"FAIL " + "; ".join(problems) if problems else "ok"}')
        failed = failed or bool(problems)
    refinished = read_json(REFINISHED, {})
    for level_id, saved in refinished.items():
        if ids and level_id not in ids:
            continue
        changed = [name for name, digest in saved['files'].items()
                   if not (LEVELS / level_id / name).is_file() or sha(LEVELS / level_id / name) != digest]
        if changed:
            print(f'{level_id}: FAIL {", ".join(changed)} changed since it was refinished')
            failed = True
    print(f'{len(folders)} levels in the app, {len(made)} made by the factory, {len(refinished)} refinished.')
    return not failed


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

def each(levels, action):
    """Run `action` per level; one blocked level never stops the others."""
    blocked = 0
    for level in levels:
        try:
            action(level)
        except Blocked as reason:
            blocked += 1
            print(f'BLOCKED {reason}', flush=True)
    return blocked


def run(levels, wait_gpu):
    """Advance every level as far as it can go without a visual review."""
    def advance(level):
        if level.integrated():
            return
        for stage in ('image', 'video'):
            if stage == 'video':
                level.image_gate()
            if not level.generated(stage):
                submit(level, stage, wait_gpu)
                if not collect(level, stage, wait_minutes=60):
                    raise Blocked(f'{level.id}: {stage} still generating; run again later')
            if level.check_current(stage) is None or (stage == 'image' and level.check_current('level') is None):
                ok, failures = (check_image if stage == 'image' else check_video)(level)
                print(f"{level.id}: {stage} check {'PASS' if ok else 'FAIL: ' + '; '.join(failures)}", flush=True)
        level.video_gate()
        integrate(level)
    return each(levels, advance)


GALLERY_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Level gallery</title>
<style>
:root{--bg:#f6f4ef;--card:#fff;--ink:#1d1d1f;--soft:#6b6b70;--line:#e3dfd6;--new:#0a7d4f}
@media (prefers-color-scheme: dark){:root{--bg:#17171a;--card:#222226;--ink:#f1f1f1;--soft:#a2a2a8;--line:#35353b;--new:#57d39b}}
*{box-sizing:border-box}body{margin:0;padding:16px;background:var(--bg);color:var(--ink);font:15px/1.4 system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--bg);padding:8px 0 12px;display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
h1{font-size:20px;margin:0 8px 0 0}button{font:inherit;padding:6px 14px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
button[aria-pressed=true]{background:var(--ink);color:var(--bg)}label{color:var(--soft)}
.level{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin:0 0 14px}
.level h2{font-size:16px;margin:0 0 8px;display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline}
.level h2 small{font-weight:400;color:var(--soft)}.tag{color:var(--new);font-weight:600;font-size:13px}
.row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.row>*{width:100%;aspect-ratio:1;background:#fff;border:1px solid var(--line);border-radius:8px;display:block;object-fit:contain}
.sw{display:inline-block;width:14px;height:14px;border-radius:50%;border:1px solid var(--line);vertical-align:-2px}
body.plain text{display:none}
@media (max-width:520px){.row{gap:4px}}
</style></head><body>
<header><h1>Level gallery</h1>
<button data-show="all" aria-pressed="true">All __TOTAL__</button><button data-show="new">Factory __NEW__</button><button data-show="old">Earlier __OLD__</button>
<label><input type="checkbox" id="numbers" checked> numbers</label>
<label>Picture, lines as the game draws them, reward. Built __WHEN__.</label></header>
__ROWS__
<script>
const levels=[...document.querySelectorAll('.level')];
document.querySelectorAll('button[data-show]').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('button[data-show]').forEach(o=>o.setAttribute('aria-pressed',o===b));
  levels.forEach(l=>l.hidden=b.dataset.show!=='all'&&l.dataset.kind!==b.dataset.show);});
document.getElementById('numbers').onchange=e=>document.body.classList.toggle('plain',!e.target.checked);
const watch=new IntersectionObserver(es=>es.forEach(e=>{e.isIntersecting?e.target.play().catch(()=>{}):e.target.pause();}),{rootMargin:'200px'});
document.querySelectorAll('video').forEach(v=>watch.observe(v));
</script></body></html>
"""


def gallery(output=None):
    """One page to vet every level in the app by eye: picture, lines and numbers, reward."""
    import html
    output = Path(output) if output else ROOT / 'gallery.html'
    output.parent.mkdir(parents=True, exist_ok=True)
    catalog = read_json(CATALOG, {})
    rows, new = [], 0
    folders = sorted((p.name for p in LEVELS.iterdir() if p.is_dir()), key=int)
    for level_id in folders:
        folder = LEVELS / level_id
        data = read_json(folder / 'data.json')
        entry = catalog.get(level_id, {})
        made_here = (SOURCES / level_id / 'receipt.json').is_file()
        new += made_here
        link = lambda name: html.escape(os.path.relpath(folder / name, output.parent))
        size = data['dimensions']
        generated = RAW / f'{level_id}.png'  # the picture as generated; the bundle's original.png sits on black
        art = html.escape(os.path.relpath(generated, output.parent)) if generated.is_file() else link('original.png')
        scale = size['w'] / 344  # the game draws 10px digits on a 344px canvas
        digits = ''.join(
            f'<text x="{n["x"]}" y="{n["y"] + 3.5 * scale * n.get("size", 10) / 10:.0f}" font-size="{n.get("size", 10) * scale:.0f}" text-anchor="middle">{n["number"]}</text>'
            for n in data['numbers'])
        swatches = ''.join(f'<span class="sw" style="background:{html.escape(c)}"></span>' for c in data['palette'])
        reward = (f'<video src="{link("reward.mp4")}" muted loop playsinline preload="none" controls></video>'
                  if (folder / 'reward.mp4').is_file() else '<div></div>')
        rows.append(
            f'<section class="level" data-kind="{"new" if made_here else "old"}"><h2>{level_id} {html.escape(entry.get("title", "not in catalog"))}'
            f'<small>{html.escape(entry.get("category", ""))}</small>'
            + ('<span class="tag">factory</span>' if made_here else '')
            + f'<small>{len(data["palette"])} colours, {len(data["numbers"])} numbers</small><span>{swatches}</span></h2>'
            f'<div class="row"><img loading="lazy" src="{art}" alt="">'
            f'<svg viewBox="0 0 {size["w"]} {size["h"]}" font-family="sans-serif" fill="#222">'
            f'<image href="{link("lines.png")}" width="{size["w"]}" height="{size["h"]}"/>{digits}</svg>{reward}</div></section>')
    page = (GALLERY_PAGE.replace('__ROWS__', '\n'.join(rows)).replace('__TOTAL__', str(len(rows)))
            .replace('__NEW__', str(new)).replace('__OLD__', str(len(rows) - new)).replace('__WHEN__', now()))
    output.write_text(page)
    print(f'{len(rows)} levels: {output}')
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)

    def add(name, stage=False, ids=True, **kwargs):
        sub = commands.add_parser(name, **kwargs)
        if stage:
            sub.add_argument('stage', choices=['image', 'video'])
        if ids:
            sub.add_argument('ids', nargs='*', help='level ids, e.g. 59 61 or a range 59-68')
        return sub

    add('status')
    add('prepare', stage=True)
    add('submit', stage=True).add_argument('--wait-gpu', type=float, default=0, metavar='MINUTES')
    add('collect', stage=True).add_argument('--wait', type=float, default=0, metavar='MINUTES')
    add('check', stage=True)
    add('integrate').add_argument('--replace', action='store_true',
                                  help='swap a factory level already in the app; only before it is released')
    add('refinish', help='run the current finishing pass over levels made before the factory')
    add('cancel', help="remove this factory's queued jobs from ComfyUI and free the GPU")
    add('verify')
    add('audit')
    add('gallery', ids=False, help='write one HTML page showing every level in the app').add_argument('--output')
    add('run').add_argument('--wait-gpu', type=float, default=0, metavar='MINUTES')
    sub = add('add', ids=False, help='add a new picture recipe to manifest.json')
    sub.add_argument('--title', required=True)
    sub.add_argument('--category', required=True, choices=CATEGORIES)
    sub.add_argument('--kind', required=True, choices=KINDS, help='objects must have no faces')
    sub.add_argument('--subject', required=True, help='what is in the picture, naming every colour')
    sub.add_argument('--motion', required=True, help='what gently moves in the reward animation')
    sub = add('record', ids=False)
    sub.add_argument('stage', choices=['image', 'video'])
    sub.add_argument('id')
    sub.add_argument('prompt_id')
    sub = add('review', ids=False)
    sub.add_argument('id')
    sub.add_argument('stage', choices=['image', 'video'])
    sub.add_argument('verdict', choices=['PASS', 'FAIL'])
    sub.add_argument('--reviewer', required=True)
    sub.add_argument('--note', action='append', default=[])
    sub = add('retry', ids=False)
    sub.add_argument('id')
    sub.add_argument('stage', choices=['image', 'video'])
    sub.add_argument('--seed', type=int, help='default: current seed + 1000')
    sub.add_argument('--subject', help='rewrite what the picture shows (rebuilds the image prompt)')
    sub.add_argument('--motion', help='rewrite what moves (rebuilds the video prompt)')
    sub.add_argument('--keep-seed', action='store_true', help='same recipe again, after a ComfyUI failure or a prompt edit')
    sub.add_argument('--reason', required=True)
    args = parser.parse_args(argv)

    if args.command == 'verify':
        return 0 if verify(expand_ids(args.ids)) else 1
    if args.command == 'gallery':
        gallery(args.output)
        return 0
    if args.command == 'audit':
        folders = expand_ids(args.ids) or sorted((p.name for p in LEVELS.iterdir() if p.is_dir()), key=int)
        for level_id in folders:
            result = checks.check_level(LEVELS / level_id, level_id=level_id, require_reward=True)
            print(f"{level_id}: {result['verdict']}" + ''.join(f'\n    {failure}' for failure in result['failures']))
        return 0

    if args.command == 'refinish':
        blocked = 0
        for level_id in expand_ids(args.ids) or []:
            try:
                refinish(level_id)
            except Blocked as reason:
                blocked += 1
                print(f'BLOCKED {reason}', flush=True)
        return 2 if blocked else 0

    manifest = load_manifest()
    if args.command == 'add':
        before = MANIFEST.read_text()
        try:
            recipe = add_level(manifest, args.title, args.category, args.kind, args.subject, args.motion)
        except ValueError as error:
            MANIFEST.write_text(before)
            print(f'Not added: {error}')
            return 2
        print(f"Added level {recipe['id']} \"{recipe['title']}\" (seed {recipe['seed']})")
        return 0
    wanted = [args.id] if hasattr(args, 'id') else expand_ids(args.ids)
    levels = [Level(recipe) for recipe in factory_levels(manifest, wanted)]

    try:
        if args.command == 'status':
            for level in levels:
                print(f"{level.id} {level.recipe['title']:<16} {level.status()}")
            return 0
        if args.command == 'prepare':
            blocked = each(levels, lambda level: print(json.dumps({'id': level.id, 'workflow': str(prepare(level, args.stage))})))
        elif args.command == 'record':
            record(levels[0], args.stage, args.prompt_id)
            blocked = 0
        elif args.command == 'submit':
            blocked = each(levels, lambda level: submit(level, args.stage, args.wait_gpu))
        elif args.command == 'collect':
            def gather(level):
                if not collect(level, args.stage, args.wait):
                    raise Blocked(f'{level.id}: {args.stage} still generating')
            blocked = each(levels, gather)
        elif args.command == 'check':
            def judge(level):
                ok, failures = (check_image if args.stage == 'image' else check_video)(level)
                print(f"{level.id}: {'PASS  review ' + str(level.run / ('review-' + args.stage + '.jpg')) if ok else 'FAIL'}"
                      + ''.join(f'\n    {failure}' for failure in failures), flush=True)
                if not ok:
                    raise Blocked(f'{level.id}: {args.stage} failed its checks; `retry {level.id} {args.stage}`')
            blocked = each(levels, judge)
        elif args.command == 'review':
            review(levels[0], args.stage, args.verdict, args.reviewer, args.note)
            print(f'{args.id}: {args.stage} review {args.verdict} recorded')
            blocked = 0
        elif args.command == 'retry':
            if args.subject and args.stage != 'image':
                raise Blocked('--subject changes the picture; use `retry ID image`')
            retry(manifest, levels[0], args.stage, args.seed, args.reason, args.keep_seed, args.subject, args.motion)
            blocked = 0
        elif args.command == 'cancel':
            cancel(levels)
            blocked = 0
        elif args.command == 'integrate':
            blocked = each(levels, lambda level: integrate(level, args.replace))
        else:
            blocked = run(levels, args.wait_gpu)
    except Blocked as reason:
        print(f'BLOCKED {reason}')
        return 2
    except urllib.error.URLError as error:
        print(f'ComfyUI is not answering at {COMFY_URL} ({error.reason}). Start it, then run this again.')
        return 3
    return 2 if blocked else 0


if __name__ == '__main__':
    sys.exit(main())
