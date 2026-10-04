"""Promote only hash-matched, explicitly approved candidates into raw/game assets."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
from durable_io import save_json, copy_file, sync_files
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
FILES=['data.json','original.png','lines.png','map.png','reward.mp4']

def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bundle_sha(folder):
    digest=hashlib.sha256()
    for name in FILES:digest.update(name.encode());digest.update((folder/name).read_bytes())
    return digest.hexdigest()

def processing_receipt(level):
    return {'image_sha256':file_sha(ROOT/'runs'/level/'image.png'),
            'video_sha256':file_sha(ROOT/'runs'/level/'video.mp4'),
            'processor_sha256':file_sha(ROOT.parent/'process.py'),
            'bundle_sha256':bundle_sha(ROOT.parent/'app_assets'/level),
            'beginner_mode':False}

def processing_is_current(level, receipt):
    current=processing_receipt(level)
    # The engine hash records provenance. A later engine change does not revoke
    # an unchanged, individually approved output produced by the earlier engine.
    return all(receipt.get(key)==current[key] for key in
               ('image_sha256','video_sha256','bundle_sha256','beginner_mode'))

def approved(level,stage,artifact):
    path=ROOT/'reviews'/f'{level}-{stage}.json'
    if not path.exists():raise ValueError(f'Missing {stage} gate for {level}')
    record=json.loads(path.read_text())
    if record.get('verdict')!='PASS' or (stage=='image' and record.get('engagement_revision')!=2):raise ValueError(f'{stage} gate did not pass: {level}')
    if stage=='image' and int(level)>=41 and record.get('object_realism_revision')!=1:raise ValueError(f'Face-free object review missing: {level}')
    if record.get('sha256')!=hashlib.sha256(artifact.read_bytes()).hexdigest():raise ValueError(f'{stage} changed after review: {level}')
    if stage=='video' and record.get('source_sha256')!=file_sha(ROOT/'runs'/level/'image.png'):raise ValueError(f'Video source changed after review: {level}')

def process(level):
    folder=ROOT/'runs'/level
    for stage,ext in [('image','.png'),('video','.mp4')]:
        artifact=folder/(stage+ext);approved(level,stage,artifact)
        dest=ROOT.parent/'raw_assets'/(level+ext)
        if dest.exists() and dest.read_bytes()!=artifact.read_bytes():raise ValueError(f'Existing raw asset differs: {dest}')
        copy_file(artifact,dest)
    subprocess.run([str(ROOT.parent/'venv'/'bin'/'python'),'process.py','--from',level,'--to',level],cwd=ROOT.parent,check=True)
    subprocess.run([str(ROOT.parent/'venv'/'bin'/'python'),str(ROOT/'inspect_assets.py'),'processed',level],check=True)
    sync_files(ROOT.parent/'app_assets'/level, FILES)
    save_json(folder/'processed-job.json', processing_receipt(level))

def integrate(level):
    source=ROOT.parent/'app_assets'/level
    # The processed gate binds the entire level, including video and metadata.
    approved(level,'image',ROOT/'runs'/level/'image.png')
    approved(level,'video',ROOT/'runs'/level/'video.mp4')
    receipt=json.loads((ROOT/'runs'/level/'processed-job.json').read_text())
    if not processing_is_current(level,receipt):raise ValueError(f'Processing inputs or output changed: {level}')
    files=FILES
    review=json.loads((ROOT/'reviews'/f'{level}-processed.json').read_text())
    if review.get('verdict')!='PASS' or review.get('sha256')!=bundle_sha(source):raise ValueError(f'Processed gate missing or stale: {level}')
    dest=REPO/'assets'/'images'/'levels'/level
    if dest.exists():
        if not all((dest/n).exists() and (dest/n).read_bytes()==(source/n).read_bytes() for n in files):raise ValueError(f'Existing game assets differ: {dest}')
    else:
        dest.mkdir()
        for name in files:copy_file(source/name,dest/name)
    loader=REPO/'utils'/'level-loader.ts';text=loader.read_text()
    if f"  '{level}': {{" not in text:
        entry=f"  '{level}': {{\n"+''.join(f"    {key}: require('@/assets/images/levels/{level}/{name}'),\n" for key,name in zip(['data','original','lines','map','reward'],files))+"  },\n"
        marker='};\n\nexport const LEVEL_IDS'
        if marker not in text:raise ValueError('Registry marker not found')
        loader.write_text(text.replace(marker,entry+marker,1))
    print('Integrated',level)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['process','integrate']);p.add_argument('ids',nargs='+');args=p.parse_args()
    for level in args.ids:
        if not level.isdecimal() or int(level)<29 or int(level)>58:raise ValueError('Expected a new level ID 29–58')
        (process if args.stage=='process' else integrate)(level)
