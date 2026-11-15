#!/usr/bin/env python3
"""Compare 1x/2x/3x/4x on the same local two-player gameplay checkpoint.

Sequential runs, fixed input, uncapped window presentation, fixed viewport,
warm-up excluded. Captures are raw internal-resolution frames, before the final
presentation filters. Measurements count emulated PAL refreshes, not generated
frames or a claim of new game pictures per refresh.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'games/urbz-pal/validation/graphics'


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repeats', type=int, default=2)
    p.add_argument('--scales', nargs='+', type=int, choices=[1,2,3,4], default=[1,2,3,4])
    args = p.parse_args()
    if not 1 <= args.repeats <= 5:p.error('repeats must be 1..5')
    os.chdir(ROOT); OUT.mkdir(parents=True, exist_ok=True)
    snapshot = ROOT / 'games/urbz-pal/validation/movement/frame17990.state'
    exe = ROOT / 'build/native-urbz-pal/ps2run'
    results = []
    metadata = {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'executable_sha256':sha(exe),
                'snapshot_sha256':sha(snapshot), 'capture_frame':18080, 'measured_frames':[18101,18300],
                'scope':'Linux/Vulkan, one window at a time, 960x720 viewport, one simulation thread, uncapped, two-player first district. Not full-game or physical-PC certification.',
                'captures':'Raw internal-resolution output before final presentation filters; no image enhancement applied.'}
    try:
        metadata['gpu'] = subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],text=True).strip()
        for scale in args.scales:
            trials = []
            for trial in range(1,args.repeats+1):
                directory = OUT/f'{scale}x'/f'trial-{trial}'; directory.mkdir(parents=True,exist_ok=True)
                shots = directory/'shots';shots.mkdir(exist_ok=True)
                command = [str(exe),'--disc','games/urbz-pal/disc.iso','--game-dir','games/urbz-pal','--pal','--language','en',
                           '--window','--pad2','--load-state',str(snapshot),'--frames','18300','--rtc','1700000000',
                           '--press','18100:lup:60','--press2','18100:ldown:60','--record',str(directory/'run.inputs'),
                           '--frames-dir',str(shots),'--frame-every','0','--frame-at','18080','--no-record']
                env = os.environ.copy()
                # Do not inherit test hooks, profiling or forced user preferences.
                for key in list(env):
                    if key.startswith('PS2_'):env.pop(key)
                env.update(PS2_SCALE=str(scale),PS2_LOOK='sharp_edges',PS2_SHARP_2D='1',PS2_GPU_BACKEND='vulkan',
                           PS2_ONE_THREAD='1',PS2_THREADS='0',PS2_NO_LIMIT='1',PS2_EE_LIVE='0',PS2_VU_LIVE='0',
                           PS2_PRESENT_MODE='immediate',SDL_AUDIODRIVER='dummy',PS2_FRAME_LOG=str(directory/'frames.txt'),
                           PS2_KEYS=str(directory/'keys.ini'))
                (directory/'command.json').write_text(json.dumps(command,indent=2)+'\n')
                began = time.monotonic()
                with (directory/'run.log').open('w') as log:
                    done = subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
                text = (directory/'run.log').read_text(errors='replace')
                if done.returncode or 'stopped after 18300 frames' not in text:raise RuntimeError(f'{scale}x trial {trial}: see {directory}/run.log')
                cpu = re.search(r'^\[cpu\] (.+)$',text,re.MULTILINE)
                if cpu:metadata['cpu']=cpu[1].strip()
                rows = [line.split() for line in (directory/'frames.txt').read_text().splitlines()[1:]]
                times = [float(row[1]) for row in rows if 18101 <= int(row[0]) <= 18300]
                measured = [row for row in rows if 18101 <= int(row[0]) <= 18300]
                if len(times) != 200 or min(times) <= 0:raise RuntimeError(f'incomplete timing interval: {scale}x / {len(times)}')
                ppm = shots/'frame_18080.ppm'
                with ppm.open('rb') as f:
                    assert f.readline().strip()==b'P6'
                    width,height=map(int,f.readline().split())
                if width % scale or height % scale:raise RuntimeError(f'capture not aligned with scale: {width}x{height}')
                base=[width//scale,height//scale]
                if metadata.get('base_internal_size',base)!=base:raise RuntimeError('native viewport changed between trials')
                metadata['base_internal_size']=base
                pictures = re.search(r'\[pace\] (\d+) new pictures in (\d+) refreshes',text)
                interval = statistics.mean(times)
                trials.append({'trial':trial,'mean_ms':round(interval,3),'p95_ms':round(sorted(times)[189],3),
                               'refreshes_per_second':round(1000/interval,2),'elapsed_seconds':round(time.monotonic()-began,2),
                               'mean_cpu_ms':round(statistics.mean(float(row[2]) for row in measured),3),
                               'interpreted_vu_calls':sum(int(row[6]) for row in measured),
                               'samples':len(times),'internal_size':[width,height],'capture':str(ppm.relative_to(ROOT)),
                               'new_pictures_total':int(pictures[1]) if pictures else None,
                               'refreshes_total':int(pictures[2]) if pictures else None})
                print(f'PASS {scale}x trial {trial}: {width}x{height}, {interval:.2f} ms / refresh, {1000/interval:.2f} refreshes/s',flush=True)
            mean_ms=statistics.mean(t['mean_ms'] for t in trials)
            results.append({'scale':scale,'trials':trials,'mean_ms':round(mean_ms,3),
                            'refreshes_per_second':round(1000/mean_ms,2)})
        metadata['passed']=True
    except Exception as error:
        metadata.update(passed=False,error=str(error)); print('FAIL '+str(error),flush=True)
    metadata['results']=results
    (OUT/'report.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return 0 if metadata['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
