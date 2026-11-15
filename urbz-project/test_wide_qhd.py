#!/usr/bin/env python3
"""Capture one local PAL scene in 4:3 and corrected 16:9 at QHD output."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'games/urbz-pal/validation/wide-qhd'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scene',choices=['gameplay','title'],default='gameplay')
    args=ap.parse_args()
    fixtures={'gameplay':('movement/frame17990.state',18100,18080),
              'title':('title/frame4100.state',4140,4130)}
    snapshot,end,capture=fixtures[args.scene]
    out=OUT if args.scene=='gameplay' else OUT/args.scene
    os.chdir(ROOT);out.mkdir(parents=True,exist_ok=True)
    results=[]
    for name,wide in [('original-4x3',False),('wide-16x9',True)]:
        directory=out/name;shots=directory/'shots';shots.mkdir(parents=True,exist_ok=True)
        env={k:v for k,v in os.environ.items() if not k.startswith('PS2_')}
        env.update(PS2_SCALE='1',PS2_LOOK='crisp',PS2_SHARP_2D='0',PS2_ONE_THREAD='1',PS2_NO_LIMIT='1',
                   PS2_EE_LIVE='0',PS2_VU_LIVE='0',PS2_GPU_BACKEND='vulkan',SDL_AUDIODRIVER='dummy',PS2_KEYS=str(directory/'keys.ini'))
        command=[str(ROOT/'build/native-urbz-pal/ps2run'),'--disc','games/urbz-pal/disc.iso','--game-dir','games/urbz-pal',
                 '--pal','--language','en','--window','--window-size','2560x1440','--pad2','--no-record','--rtc','1700000000',
                 '--load-state','games/urbz-pal/validation/'+snapshot,'--frames',str(end),
                 '--frames-dir',str(shots),'--frame-every','0','--frame-at',str(capture),'--record',str(directory/'run.inputs')]
        if wide:command+=['--widescreen']
        with (directory/'run.log').open('w') as log:done=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        text=(directory/'run.log').read_text(errors='replace')
        if done.returncode or f'stopped after {end} frames' not in text:raise RuntimeError(name+': runner failed')
        match=re.search(r'\[window\] requested (\d+)x(\d+), drawable (\d+)x(\d+), aspect (\S+)',text)
        if not match:raise RuntimeError(name+': missing output-size evidence')
        width,height,dw,dh=map(int,match.groups()[:4]);aspect=match[5]
        assert [width,height]==[2560,1440]
        assert aspect==('16:9' if wide else '4:3')
        ppm=shots/f'frame_{capture:05d}.ppm'
        with ppm.open('rb') as f:
            assert f.readline().strip()==b'P6'
            internal=list(map(int,f.readline().split()))
        assert internal==[640,511]
        results.append({'case':name,'passed':True,'requested_output':[width,height],'drawable_output':[dw,dh],
                        'display_aspect':aspect,'internal_capture':internal,'capture':str(ppm.relative_to(ROOT)),
                        'scope':'Raw internal capture; the compositor may constrain window size. Visual geometry/FOV comparison still requires inspection.'})
        print('PASS '+name,flush=True)
    (out/'report.json').write_text(json.dumps({'passed':True,'scene':args.scene,'frame':capture,'cases':results,'native_windows_tested':False},indent=2)+'\n')


if __name__=='__main__':main()
