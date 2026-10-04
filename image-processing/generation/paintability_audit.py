"""Run the existing processor on image candidates, then measure usable palette variety.
This produces diagnostic assets only; source/video/processed approvals still gate shipping.
"""
import argparse,json,sys,shutil,hashlib
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent));import process

def audit(id):
    base=ROOT/'paintability-candidates';inputs=base/'sources';inputs.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'runs'/id/'image.png',inputs/f'{id}.png')
    source_sha=hashlib.sha256((inputs/f'{id}.png').read_bytes()).hexdigest()
    process.INPUT_DIR=str(inputs);process.OUTPUT_DIR=str(base/'processed');process.process_level(f'{id}.png')
    folder=base/'processed'/id;d=json.loads((folder/'data.json').read_text());m=cv2.imread(str(folder/'map.png'),0)
    paintable=int(np.sum(m<254));threshold=max(1800,int(paintable*.008));entries=[]
    for i,hex in enumerate(d['palette']):
        mask=np.uint8(m==i);area=int(mask.sum());radius=float(cv2.distanceTransform(mask,cv2.DIST_L2,5).max())
        if area<threshold or radius<10:continue
        rgb=np.array([[[int(hex[k:k+2],16)/255 for k in (1,3,5)]]],dtype=np.float32)
        lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB)[0,0]
        entries.append({'index':i,'hex':hex,'area':area,'radius':round(radius,1),'lab':lab})
    groups=[]
    for c in sorted(entries,key=lambda c:c['area'],reverse=True):
        match=next((g for g in groups if np.linalg.norm(c['lab']-g[0]['lab'])<20),None)
        if match is None:groups.append([c])
        else:match.append(c)
    report={'id':id,'processor_revision':'original-restored','source_sha256':source_sha,'source_palette_entries':len(d['palette']),'meaningful_color_groups':len(groups),'paintable_pixels':paintable,'number_labels':len(d['numbers']),'area_cutoff':threshold,'groups':[[{k:v for k,v in c.items() if k!='lab'} for c in g] for g in groups]}
    lines=cv2.imread(str(folder/'lines.png'),cv2.IMREAD_UNCHANGED);preview=np.full((*m.shape,3),248,np.uint8);preview[lines[:,:,3]>0]=lines[lines[:,:,3]>0,:3]
    for label in d['numbers']:
        t=str(label['number']);w,h=cv2.getTextSize(t,cv2.FONT_HERSHEY_SIMPLEX,.5,1)[0];cv2.putText(preview,t,(label['x']-w//2,label['y']+h//2),cv2.FONT_HERSHEY_SIMPLEX,.5,(85,85,85),1,cv2.LINE_AA)
    cv2.imwrite(str(folder/'unpainted.png'),preview)
    (ROOT/'reviews'/f'{id}-paintability.json').write_text(json.dumps(report,indent=2)+'\n');print('AUDIT',id,len(groups),'meaningful colors',len(d['numbers']),'labels',flush=True)
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('ids',nargs='+');args=p.parse_args()
    for id in args.ids:audit(id)
