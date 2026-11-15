#!/usr/bin/env python3
"""Compare the preserved runner, updated VU AOT, and direct GPU presentation."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'games/urbz-pal/validation/performance'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scales',nargs='+',type=int,choices=range(1,5),default=[1,2,4])
    parser.add_argument('--repeats',type=int,choices=range(1,6),default=2)
    args=parser.parse_args();os.chdir(ROOT);OUT.mkdir(parents=True,exist_ok=True)
    before=ROOT/'build/performance-baseline/ps2run';after=ROOT/'build/native-urbz-pal/ps2run'
    result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_sha256':sha(before),'optimized_sha256':sha(after),
            'snapshot_sha256':sha(ROOT/'games/urbz-pal/validation/movement/frame17990.state'),
            'scope':'Linux/Vulkan, sequential runs, two-player first district, one simulation thread, 960x720 viewport, uncapped immediate presentation, fixed input and RTC, live compilation off. 400 refreshes measured after 110 warm-up refreshes. Refreshes are not distinct images.',
            'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'],text=True).strip(),'results':[]}
    references={}
    try:
        for scale in args.scales:
            entries={name:[] for name in ['baseline','aot','optimized']}
            for trial in range(1,args.repeats+1):
                # Alternate order to reduce persistent warm-cache/order bias.
                order=['baseline','aot','optimized'] if trial%2 else ['optimized','aot','baseline']
                for name in order:
                    directory=OUT/f'{scale}x'/name/f'trial-{trial}';directory.mkdir(parents=True,exist_ok=True)
                    env={k:v for k,v in os.environ.items() if not k.startswith('PS2_')}
                    env.update(PS2_SCALE=str(scale),PS2_LOOK='sharp_edges',PS2_SHARP_2D='1',PS2_ONE_THREAD='1',PS2_THREADS='0',
                               PS2_NO_LIMIT='1',PS2_EE_LIVE='0',PS2_VU_LIVE='0',PS2_PRESENT_MODE='immediate',PS2_GPU_BACKEND='vulkan',
                               PS2_KEYS=str(directory/'keys.ini'),PS2_FRAME_LOG=str(directory/'frames.txt'),SDL_AUDIODRIVER='dummy')
                    if name=='aot':env['PS2_SDL_RENDERER']='1'
                    exe=before if name=='baseline' else after
                    command=[str(exe),'--disc','games/urbz-pal/disc.iso','--game-dir','games/urbz-pal','--pal','--language','en','--window','--pad2',
                             '--load-state','games/urbz-pal/validation/movement/frame17990.state','--frames','18500','--rtc','1700000000',
                             '--press','18100:lup:60','--press2','18100:ldown:60','--no-record','--record',str(directory/'run.inputs')]
                    (directory/'command.json').write_text(json.dumps(command,indent=2)+'\n')
                    with (directory/'run.log').open('w') as log:done=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
                    text=(directory/'run.log').read_text(errors='replace')
                    if done.returncode or 'stopped after 18500 frames' not in text:raise RuntimeError(f'{scale}x {name} trial {trial}: runner failed')
                    presentation='WebGPU' if '[window] presenting through WebGPU' in text else 'SDL'
                    if presentation!=('WebGPU' if name=='optimized' else 'SDL'):raise RuntimeError(f'{name}: unexpected {presentation} presentation')
                    rows=[l.split() for l in (directory/'frames.txt').read_text().splitlines()[1:]]
                    rows=[r for r in rows if 18101<=int(r[0])<=18500]
                    if len(rows)!=400:raise RuntimeError('incomplete measurement interval')
                    times=[float(r[1]) for r in rows];mean=statistics.mean(times)
                    records=[l for l in (directory/'run.inputs').read_text().splitlines() if l.startswith(('p1 ','p2 ','h ','e '))]
                    reference=references.setdefault(scale,records)
                    if records!=reference:raise RuntimeError(f'{scale}x {name}: gameplay checkpoints differ')
                    pace=re.search(r'\[pace\] (\d+) new pictures in (\d+) refreshes',text)
                    pictures,refreshes=map(int,pace.groups())
                    item={'trial':trial,'mean_ms':round(mean,3),'p95_ms':round(sorted(times)[379],3),'refreshes_per_second':round(1000/mean,2),
                          'mean_cpu_ms':round(statistics.mean(float(r[2]) for r in rows),3),'interpreted_vu_calls':sum(int(r[6]) for r in rows),
                          'new_pictures_total':pictures,'refreshes_total':refreshes,'new_pictures_per_second_estimated':round(1000/mean*pictures/refreshes,2),
                          'gameplay_checkpoints_equal_to_baseline':True,'presentation':presentation,'directory':str(directory.relative_to(ROOT))}
                    entries[name].append(item)
                    print(f'PASS {scale}x {name} trial {trial}: {1000/mean:.2f} refreshes/s, {item["interpreted_vu_calls"]} interpreted VU calls',flush=True)
            aggregate={name:{'trials':items,'refreshes_per_second':round(1000/statistics.mean(t['mean_ms'] for t in items),2)} for name,items in entries.items()}
            aggregate['speedup']=round(aggregate['optimized']['refreshes_per_second']/aggregate['baseline']['refreshes_per_second'],2)
            result['results'].append({'scale':scale,**aggregate})
        result['passed']=True
    except Exception as e:
        result.update(passed=False,error=str(e));print('FAIL '+str(e),flush=True)
    (OUT/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
