"""Create visual review artifacts and check game-asset structure. Never approves art."""
import argparse,json,subprocess
from pathlib import Path
import cv2
import numpy as np
cv2.setNumThreads(2)
ROOT=Path(__file__).resolve().parent

def video_sheet(level_id):
    source=ROOT/'runs'/level_id/'video.mp4'
    cap=cv2.VideoCapture(str(source));count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS)
    if count<2 or fps<=0:raise ValueError(f'Invalid video: {source}')
    canvas=np.full((3*350,4*320,3),240,dtype=np.uint8)
    indexes=np.linspace(0,count-1,12).astype(int);previous=None;diffs=[]
    for i,idx in enumerate(indexes):
        cap.set(cv2.CAP_PROP_POS_FRAMES,int(idx));ok,frame=cap.read()
        if not ok:raise ValueError(f'Missing frame {idx}')
        frame=cv2.resize(frame,(320,320));y=(i//4)*350;x=(i%4)*320
        canvas[y+25:y+345,x:x+320]=frame
        cv2.putText(canvas,f'{level_id} - {idx/fps:.2f}s',(x+8,y+18),cv2.FONT_HERSHEY_SIMPLEX,.45,(30,30,30),1)
        if previous is not None:diffs.append(float(np.abs(frame.astype(float)-previous).mean()))
        previous=frame
    cap.release();out=ROOT/'reviews'/f'{level_id}-video-frames.jpg';cv2.imwrite(str(out),canvas)
    report={'frames':count,'fps':fps,'duration_seconds':count/fps,'sampled_frame_mean_absolute_differences':diffs,'sheet':str(out)}
    (ROOT/'reviews'/f'{level_id}-video-metrics.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

def check_processed(level_id):
    folder=ROOT.parent/'app_assets'/level_id;data=json.loads((folder/'data.json').read_text())
    m=cv2.imread(str(folder/'map.png'),cv2.IMREAD_UNCHANGED);outline=cv2.imread(str(folder/'lines.png'),cv2.IMREAD_UNCHANGED);original=cv2.imread(str(folder/'original.png'))
    h,w=m.shape;assert data['dimensions']=={'w':w,'h':h}
    assert outline.shape==(h,w,4) and original.shape==(h,w,3)
    palette=data['palette'];assert 1<len(palette)<254
    ids=set(map(int,np.unique(m)));assert ids<=set(range(len(palette)))|{254,255}
    errors=[];clearances=[]
    for number in data['numbers']:
        x,y=number['x'],number['y'];idx=number['color_index']
        if not(0<=x<w and 0<=y<h) or m[y,x]!=idx:errors.append(number)
        else:
            dist=cv2.distanceTransform(np.uint8(m==idx),cv2.DIST_L2,5);clearances.append(float(dist[y,x]))
    assert not errors,f'Labels outside corresponding paint areas: {errors}'
    report={'id':level_id,'palette_size':len(palette),'labels':len(data['numbers']),'paintable_pixels':int(np.count_nonzero(m<254)),'label_clearance_min_px':min(clearances) if clearances else 0,'labels_under_8px_clearance':sum(c<8 for c in clearances),'has_reward':(folder/'reward.mp4').exists()}
    # Faithful unpainted preview, including actual fixed outlines and metadata labels.
    preview=np.full((h,w,3),245,dtype=np.uint8);preview[outline[:,:,3]>0]=outline[outline[:,:,3]>0,:3]
    for number in data['numbers']:
        label=str(number['number']);size=cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,.5,1)[0]
        cv2.putText(preview,label,(number['x']-size[0]//2,number['y']+size[1]//2),cv2.FONT_HERSHEY_SIMPLEX,.5,(80,80,80),1,cv2.LINE_AA)
    cv2.imwrite(str(ROOT/'reviews'/f'{level_id}-paintable.png'),preview)
    (ROOT/'reviews'/f'{level_id}-processed-metrics.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['video','processed']);p.add_argument('ids',nargs='+');args=p.parse_args()
    for id in args.ids:
        (video_sheet if args.stage=='video' else check_processed)(id)
