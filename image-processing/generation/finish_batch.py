"""Watch explicit review gates; process and integrate only current approved assets.

This never generates approvals or submits generation jobs. It can run alongside
batch.py and visual reviewers, and safely resumes from processing receipts.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from promote import ROOT, REPO, approved, process, integrate, processing_is_current

def finish_once():
    statuses={}
    for level in json.loads((ROOT/'manifest.json').read_text())['levels']:
        id=level['id'];folder=ROOT/'runs'/id
        try:
            approved(id,'image',folder/'image.png')
            approved(id,'video',folder/'video.mp4')
        except (ValueError,FileNotFoundError) as error:
            statuses[id]=str(error);continue
        receipt=folder/'processed-job.json'
        if not receipt.exists():
            process(id)
            subprocess.run([sys.executable,str(ROOT/'phone_previews.py'),'--final',id],check=True,stdout=subprocess.DEVNULL)
        elif not processing_is_current(id,json.loads(receipt.read_text())):
            statuses[id]='Processing changed; inspect before replacing reviewed output';continue
        try:
            integrate(id)
        except (ValueError,FileNotFoundError) as error:
            statuses[id]=str(error);continue
        statuses[id]='integrated'
    (ROOT/'batch-status.json').write_text(json.dumps(statuses,indent=2)+'\n')
    return statuses

if __name__=='__main__':
    os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
    os.environ.setdefault('OMP_NUM_THREADS','4')
    previous=None
    while True:
        statuses=finish_once()
        if statuses!=previous:
            print(json.dumps(statuses),flush=True);previous=statuses
        if all(s=='integrated' for s in statuses.values()):break
        if '--once' in sys.argv:break
        time.sleep(10)
