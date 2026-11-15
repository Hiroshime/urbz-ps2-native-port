#!/usr/bin/env python3
"""Isolated timing experiments. Not a supported gameplay preset or a 60 FPS claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import struct
import subprocess

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'games/urbz-pal/validation/performance/high-fps'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--tuning',action='store_true')
    mode.add_argument('--threading',action='store_true')
    parser.add_argument('--tile',type=int,choices=[4,8,16])
    parser.add_argument('--tile-thread',type=int,choices=[0,1])
    parser.add_argument('--profile',action='store_true',help='collect CPU/GPU-call diagnostics; not a clean throughput measurement')
    args=parser.parse_args()
    os.chdir(ROOT);OUT.mkdir(parents=True,exist_ok=True)
    state=(ROOT/'games/urbz-pal/validation/movement/frame17990.state').read_bytes()
    ram=memoryview(state)[1476:]
    assert struct.unpack_from('<I',ram,0x3AE2F8)[0]==0x28820002
    initial_ticks=struct.unpack_from('<I',ram,0x4C00B0)[0]
    results=[]
    cases=[
        ('original-pal',50,[]),
        ('pal50-counter-candidate',50,[(0x4F074C,1)]),
        ('ntsc60-pal-clock-negative-control',60,[(0x4F074C,1)]),
        ('ntsc60-clock-candidate',60,[(0x4F074C,1),(0x4C0DD8,0x3C888889),(0x4B8DA0,0)]),
    ]
    tuning={}
    if args.tuning:
        clock=[(0x4F074C,1),(0x4C0DD8,0x3C888889),(0x4B8DA0,0)]
        tuning={'tile4':{'PS2_TILE':'4'},'tile8':{'PS2_TILE':'8'},'tile16':{'PS2_TILE':'16'},'tile16-submit0':{'PS2_TILE':'16','PS2_GPU_SUBMIT_THREAD':'0'}}
        cases=[(name,60,clock) for name in tuning]
    if args.threading:
        clock=[(0x4F074C,1),(0x4C0DD8,0x3C888889),(0x4B8DA0,0)]
        cases=[(name,60,clock) for name in ['strict-single','strict-render-1','strict-render-2']]
    reference=None
    for name,rate,patches in cases:
        suffix=(f'-tile{args.tile}' if args.tile else '')+(f'-helper{args.tile_thread}' if args.tile_thread is not None else '')
        directory=OUT/(name+suffix);directory.mkdir(exist_ok=True)
        patch=directory/'runtime.patches';patch.write_text(''.join(f'1 {address:x} 4 {value:x}\n' for address,value in patches))
        env={k:v for k,v in os.environ.items() if not k.startswith('PS2_')}
        env.update(PS2_SCALE='1',PS2_LOOK='sharp_edges',PS2_SHARP_2D='1',PS2_ONE_THREAD='1',PS2_THREADS='0',PS2_NO_LIMIT='1',
                   PS2_EE_LIVE='0',PS2_VU_LIVE='0',PS2_PRESENT_MODE='immediate',PS2_GPU_BACKEND='vulkan',SDL_AUDIODRIVER='dummy',
                   PS2_KEYS=str(directory/'keys.ini'),PS2_FRAME_LOG=str(directory/'frames.txt'),PS2_DUMP=str(directory/'ram.bin'))
        env.update(tuning.get(name,{}))
        if args.tile:env['PS2_TILE']=str(args.tile)
        if args.tile_thread is not None:env['PS2_TILE_THREAD']=str(args.tile_thread)
        if args.threading:
            env.update(PS2_GS_SYNC_READBACK='1',PS2_NO_VU_THREAD='1')
            if name!='strict-single':env.pop('PS2_ONE_THREAD',None)
        if args.profile and name=='strict-render-1':
            env.update(PS2_PROFILE=str(directory/'cpu.profile'),PS2_PROFILE_FROM='18100',PS2_GPU_WGPU_TIME='600')
        command=[str(ROOT/'build/native-urbz-pal/ps2run'),'--disc','games/urbz-pal/disc.iso','--game-dir','games/urbz-pal',
                 '--pal' if rate==50 else '--ntsc','--language','en','--window','--pad2','--load-state','games/urbz-pal/validation/movement/frame17990.state',
                 '--frames','18590','--rtc','1700000000','--patches',str(patch),'--no-record']
        if args.tuning or args.threading:command+=['--record',str(directory/'run.inputs')]
        if args.tuning:
            (directory/'shots').mkdir(exist_ok=True)
            command+=['--frames-dir',str(directory/'shots'),'--frame-every','0','--frame-at','18080']
        with (directory/'run.log').open('w') as log:done=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        text=(directory/'run.log').read_text(errors='replace')
        if done.returncode:raise RuntimeError(name+' runner failed')
        data=(directory/'ram.bin').read_bytes()
        ticks=struct.unpack_from('<I',data,0x4C00B0)[0]
        quantum=struct.unpack_from('<f',data,0x4C0DD8)[0]
        dt=struct.unpack_from('<f',data,0x4C00B8)[0]
        pace=re.search(r'\[pace\] (\d+) new pictures in (\d+) refreshes',text)
        pictures,refreshes=map(int,pace.groups())
        rows=[l.split() for l in (directory/'frames.txt').read_text().splitlines()[1:]]
        rows=[r for r in rows if 18101<=int(r[0])<=18590]
        ms=statistics.mean(float(r[1]) for r in rows)
        virtual_seconds=600/rate
        item={'name':name,'experimental':True,'refreshes':refreshes,'pictures':pictures,'refresh_capacity_per_second':round(1000/ms,2),
              'estimated_distinct_picture_capacity_per_second':round(1000/ms*pictures/refreshes,2),'quantum':quantum,'last_engine_delta':dt,
              'engine_tick_delta':ticks-initial_ticks,'engine_elapsed_seconds_from_ticks':round((ticks-initial_ticks)*quantum,4),
              'virtual_seconds':virtual_seconds,'engine_time_ratio':round((ticks-initial_ticks)*quantum/virtual_seconds,4),
              'scope':'Counter candidate differs from public opcode patch. Timing accumulator only; physics, animations, saves and network unvalidated. Not shipped as gameplay setting.'}
        item.update(tile=args.tile,tile_thread=args.tile_thread,profiling_enabled=bool(args.profile and name=='strict-render-1'))
        if args.tuning:
            record=[l for l in (directory/'run.inputs').read_text().splitlines() if l.startswith(('p1 ','p2 ','h ','e '))]
            image_hash=hashlib.sha256((directory/'shots/frame_18080.ppm').read_bytes()).hexdigest()
            if reference is None:reference=(record,image_hash)
            item.update(checkpoints_equal_to_reference=record==reference[0],capture_equal_to_reference=image_hash==reference[1],capture_sha256=image_hash,environment=tuning[name])
        if args.threading:
            record=[l for l in (directory/'run.inputs').read_text().splitlines() if l.startswith(('p1 ','p2 ','h ','e '))]
            if reference is None:reference=record
            item['checkpoints_equal_to_single_thread']=record==reference
            if record!=reference:raise RuntimeError(name+': render-thread determinism regression')
        results.append(item);print(json.dumps(item),flush=True)
    filename='threading-strict-report.json' if args.threading else 'tuning-report.json' if args.tuning else 'report.json'
    if args.tile or args.tile_thread is not None:filename=suffix+'-'+filename
    with (ROOT/'build/native-urbz-pal/ps2run').open('rb') as f:executable_sha=hashlib.file_digest(f,'sha256').hexdigest()
    (OUT/filename).write_text(json.dumps({'experiments':results,'supported_60fps_delivered':False,'executable_sha256':executable_sha},indent=2)+'\n')


if __name__=='__main__':main()
