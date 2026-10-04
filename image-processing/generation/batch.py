"""Resumeable generation; writes candidates only. Human/Astra gates precede promotion.

python batch.py image 29 34       # generate image candidates
python batch.py video 29 34      # requires approved image gate
python batch.py sheets           # contact sheets for review
"""
import argparse, hashlib, json, shutil, sys, time, urllib.request, urllib.error
from pathlib import Path
from build_workflows import qwen_graph, h3_graph, ui_graph
from durable_io import save_json, copy_file
ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from processing_resources import serialized_work
COMFY=Path('/home/lewis/comfy/ComfyUI')
URL='http://127.0.0.1:8188'

def request(path, data=None):
    req=urllib.request.Request(URL+path, data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def save(path, value):
    save_json(path, value)

@serialized_work
def generate(stage, rows):
    for level in rows:
        level_id=level['id'];folder=ROOT/'runs'/level_id;folder.mkdir(parents=True,exist_ok=True)
        record=folder/f'{stage}-job.json'
        if record.exists():
            job=json.loads(record.read_text())
            if job['status']=='completed':
                print(stage,level_id,'already completed',flush=True);continue
            if job['status']=='error':raise RuntimeError(f'{record} failed; inspect before making a new attempt')
        else:
            prefix=f"rainbow-paint-by-numbers/{stage}/{level_id}-{level['slug']}"
            if stage=='image':
                reference=None
                if level.get('image_reference'):
                    source_reference=ROOT/level['image_reference']
                    if level.get('image_reference_sha256') and hashlib.sha256(source_reference.read_bytes()).hexdigest()!=level['image_reference_sha256']:
                        raise RuntimeError(f'Image edit reference changed: {level_id}')
                    inp=COMFY/'input'/'rainbow-paint-by-numbers'/'references';inp.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(source_reference,inp/f'{level_id}.png')
                    reference=f'rainbow-paint-by-numbers/references/{level_id}.png'
                graph=qwen_graph(level['image_prompt'],level['seed'],prefix,reference=reference)
            else:
                approval=ROOT/'reviews'/f'{level_id}-image.json'
                if not approval.exists() or json.loads(approval.read_text()).get('verdict')!='PASS' or json.loads(approval.read_text()).get('engagement_revision')!=2:raise RuntimeError(f'Image {level_id} not approved')
                if int(level_id)>=41 and json.loads(approval.read_text()).get('object_realism_revision')!=1:raise RuntimeError(f'Image {level_id} requires face-free object review')
                image=folder/'image.png'
                if hashlib.sha256(image.read_bytes()).hexdigest()!=json.loads(approval.read_text())['sha256']:raise RuntimeError('Image changed after approval')
                inp=COMFY/'input'/'rainbow-paint-by-numbers';inp.mkdir(exist_ok=True)
                shutil.copyfile(image,inp/f'{level_id}.png')
                graph=h3_graph(f'rainbow-paint-by-numbers/{level_id}.png',level['video_prompt'],level.get('video_seed',level['seed']),prefix)
            save(folder/f'{stage}.api.json',graph)
            result=request('/prompt',{'prompt':graph,'client_id':'rainbow-paint-by-numbers'})
            job={'id':level_id,'stage':stage,'prompt_id':result['prompt_id'],'status':'queued','started_at':time.time()}
            save(record,job)
        pid=job['prompt_id'];print(stage,level_id,pid,flush=True)
        while True:
            try:
                history=request('/history/'+pid)
                if pid in history:
                    result=history[pid]
                    if result.get('status',{}).get('status_str')=='error':
                        job.update(status='error',error=result.get('status'));save(record,job);raise RuntimeError(f'Generation failed for {level_id}: {job["error"]}')
                    outputs=[]
                    for v in result.get('outputs',{}).values():
                        for key in ('images','gifs','videos'):
                            outputs.extend(v.get(key,[]))
                    ext='.png' if stage=='image' else '.mp4'
                    outputs=[o for o in outputs if o.get('filename','').endswith(ext)]
                    if not outputs:raise RuntimeError(f'Completed without {ext}: {pid}')
                    output=outputs[-1];source=COMFY/output.get('type','output')/output.get('subfolder','')/output['filename']
                    target=folder/(stage+ext);copy_file(source,target)
                    job.update(status='completed',finished_at=time.time(),output=str(target),source=str(source),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
                    save(record,job);print(stage,level_id,'completed',round(job['finished_at']-job['started_at']), 'seconds',flush=True);break
                queue=request('/queue')
                if not any(item[1]==pid for item in queue['queue_running']+queue['queue_pending']):
                    raise RuntimeError(f'Job {pid} missing from queue and history; do not resubmit without inspection')
            except (urllib.error.URLError, TimeoutError) as err:
                print('Observation retry:',err,flush=True)
            time.sleep(5)

def sheets():
    from PIL import Image,ImageOps,ImageDraw
    rows=json.loads((ROOT/'manifest.json').read_text())['levels']
    for start in range(0,len(rows),6):
        group=rows[start:start+6];canvas=Image.new('RGB',(1536,1060),'#e9e9e9');draw=ImageDraw.Draw(canvas)
        for index,level in enumerate(group):
            path=ROOT/'runs'/level['id']/'image.png'
            if not path.exists():continue
            im=ImageOps.contain(Image.open(path).convert('RGB'),(500,500));x=index%3*512;y=index//3*530
            canvas.paste(im,(x+(512-im.width)//2,y+25));draw.text((x+12,y+8),level['id']+' '+level['title'],fill='black')
        target=ROOT/'reviews'/f'images-{group[0]["id"]}-{group[-1]["id"]}.jpg';canvas.save(target,quality=95);print(target)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['image','video','sheets']);p.add_argument('first',type=int,nargs='?',default=29);p.add_argument('last',type=int,nargs='?',default=58);args=p.parse_args()
    if args.stage=='sheets':sheets()
    else:
        rows=json.loads((ROOT/'manifest.json').read_text())['levels']
        generate(args.stage,[r for r in rows if args.first<=int(r['id'])<=args.last])
