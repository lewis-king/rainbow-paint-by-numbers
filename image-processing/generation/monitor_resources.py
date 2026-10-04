"""Record resource samples while a specific ComfyUI prompt is live.

Run with a prompt ID and output JSONL path. This observes, never submits jobs.
An observation failure is recorded and retried, not treated as job failure.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time
import urllib.request


def sample():
    gpu = subprocess.check_output([
        'nvidia-smi', '--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu',
        '--format=csv,noheader,nounits',
    ], text=True, timeout=5).strip()
    memory = {key: int(value.split()[0]) for key, value in
              (line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
              if key in ('MemAvailable', 'SwapFree')}
    return {'time': time.time(), 'gpu_mib_total_util_temp': gpu,
            'memory_kib': memory,
            'memory_pressure': Path('/proc/pressure/memory').read_text().strip()}


def observe(prompt_id, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    while True:
        terminal = False
        try:
            row = sample()
            with urllib.request.urlopen('http://127.0.0.1:8188/history/' + prompt_id, timeout=10) as response:
                history = json.load(response)
            if prompt_id in history:
                row['job_status'] = history[prompt_id].get('status')
                terminal = True
            else:
                with urllib.request.urlopen('http://127.0.0.1:8188/queue', timeout=10) as response:
                    queue = json.load(response)
                live = any(item[1] == prompt_id for item in queue['queue_running'] + queue['queue_pending'])
                row['job_status'] = 'live' if live else 'missing_from_queue_and_history'
                terminal = not live
        except Exception as error:
            row = {'time': time.time(), 'observation_error': str(error)}
        with output.open('a') as stream:
            stream.write(json.dumps(row) + '\n')
            stream.flush()
        if terminal:
            return
        time.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prompt_id')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    observe(args.prompt_id, args.output)
