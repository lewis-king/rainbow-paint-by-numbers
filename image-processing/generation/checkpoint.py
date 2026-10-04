"""Preserve hash-approved source images and exact runs in the versioned repo."""
import hashlib
import json
import shutil
from pathlib import Path
from durable_io import save_json, copy_file

ROOT = Path(__file__).resolve().parent

def checkpoint():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    saved = []
    for level in manifest['levels']:
        level_id = level['id']
        review_path = ROOT / 'reviews' / f'{level_id}-image.json'
        if not review_path.exists():
            continue
        review = json.loads(review_path.read_text())
        if review.get('verdict') != 'PASS' or review.get('engagement_revision') != 2:
            continue
        if int(level_id) >= 41 and review.get('object_realism_revision') != 1:
            continue
        run = ROOT / 'runs' / level_id
        image = run / 'image.png'
        if not image.exists():
            # A source may be archived while its replacement is being reviewed.
            continue
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if review.get('sha256') != digest:
            raise ValueError(f'Stale image approval: {level_id}')
        dest = ROOT / 'sources' / level_id
        dest.mkdir(parents=True, exist_ok=True)
        for name in ('image.png', 'image.api.json', 'image-job.json'):
            copy_file(run / name, dest / name)
        copy_file(review_path, dest / 'image-review.json')
        save_json(dest / 'recipe.json', level)
        if level.get('image_reference'):
            reference = ROOT / level['image_reference']
            if reference.resolve() != (dest / 'reference.png').resolve():
                copy_file(reference, dest / 'reference.png')
        entry = {'id': level_id, 'title': level['title'], 'sha256': digest}
        video_review_path = ROOT / 'reviews' / f'{level_id}-video.json'
        video = run / 'video.mp4'
        if video.exists() and video_review_path.exists():
            video_review = json.loads(video_review_path.read_text())
            video_digest = hashlib.sha256(video.read_bytes()).hexdigest()
            if (video_review.get('verdict') == 'PASS'
                    and video_review.get('source_sha256') == digest
                    and video_review.get('sha256') == video_digest):
                for name in ('video.mp4', 'video.api.json', 'video-job.json'):
                    copy_file(run / name, dest / name)
                copy_file(video_review_path, dest / 'video-review.json')
                entry['video_sha256'] = video_digest
        saved.append(entry)
    save_json(ROOT / 'source-index.json', saved)
    print(f'Preserved {len(saved)} approved source images with exact workflows and recipes.')

if __name__ == '__main__':
    checkpoint()
