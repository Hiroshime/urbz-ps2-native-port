#!/usr/bin/env python3
"""Check independent graphics presets against full EE/IOP LAN state checks."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from test_lan_protocol import free_port

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'games/urbz-pal/validation/graphics/netplay'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--windows',action='store_true')
    ap.add_argument('--boot',action='store_true',help='validate parallel rendering from power-on instead of the district snapshot')
    ap.add_argument('--append-report',action='store_true')
    ap.add_argument('--pairs',nargs='+',default=['1:1','2:2','3:3','4:4','1:2','2:2:filter','2:2:look'])
    args=ap.parse_args()
    os.chdir(ROOT);OUT.mkdir(parents=True,exist_ok=True)
    report=OUT/(('report-boot-' if args.boot else 'report-')+('windows.json' if args.windows else 'linux.json'))
    results=json.loads(report.read_text())['tests'] if args.append_report and report.exists() else []
    try:
        for pair in args.pairs:
            parts=pair.split(':')
            a,b=map(int,parts[:2])
            variant=parts[2] if len(parts)==3 else ''
            if len(parts) not in (2,3) or variant not in ('','filter','look','fsr','wide','aspect'):raise ValueError('invalid test case')
            if a not in range(1,5) or b not in range(1,5):raise ValueError('scales must be 1..4')
            incompatible=a!=b or variant in ('filter','aspect')
            name=('boot-' if args.boot else '')+f'{a}x-{b}x'+('-'+variant if variant else '')+('-wine' if args.windows else '')
            directory=OUT/name;directory.mkdir(exist_ok=True)
            port=str(free_port())
            first,end=(0,1200) if args.boot else (17990,18200)
            checks=end//30-first//30
            common=['--disc','games/urbz-pal/disc.iso','--game-dir','games/urbz-pal','--pal','--language','en','--window',
                    '--frames',str(end),'--rtc','1700000000',
                    '--net-delay','3','--net-timeout-ms','30000','--net-secure']
            if not args.boot:common+=['--load-state','games/urbz-pal/validation/movement/frame17990.state']
            host=[str(ROOT/'build/native-urbz-pal/ps2run'),*common,'--net-host',port,'--net-bind','127.0.0.1','--press','300:start:3' if args.boot else '18100:lup:60']
            exe=str(ROOT/('build/wine-urbz-pal/ps2run.exe' if args.windows else 'build/native-urbz-pal/ps2run'))
            client=(['wine',exe] if args.windows else [exe])+common+['--net-join','127.0.0.1:'+port,'--press','600:cross:3' if args.boot else '18100:ldown:60']
            processes=[];files=[];began=time.monotonic()
            try:
                for index,(scale,command) in enumerate([(a,host),(b,client)]):
                    side='host' if index==0 else 'client'
                    env=os.environ.copy()
                    for key in list(env):
                        if key.startswith('PS2_'):env.pop(key)
                    env.update(PS2_SCALE=str(scale),PS2_LOOK='crisp' if scale==1 else 'sharp_edges',PS2_SHARP_2D='0' if scale==1 else '1',
                               PS2_GPU_BACKEND='vulkan',SDL_AUDIODRIVER='dummy',PS2_KEYS=str(directory/(side+'-keys.ini')),
                               URBZ_NET_KEY='0123456789abcdef0123456789abcdef',WINEDEBUG='-all',WINEDLLOVERRIDES='mscoree,mshtml=')
                    if index==1 and variant=='filter':env['PS2_SHARP_2D']='2'
                    if index==1 and variant=='look':env['PS2_LOOK']='soft_edges'
                    if variant=='fsr':
                        env['PS2_UPSCALER']='fsr1' if index==0 else 'off'
                        command += ['--window-size','2560x1440' if index==0 else '1280x960']
                    if variant=='wide' or (variant=='aspect' and index==1):command += ['--widescreen']
                    if args.windows:env['WINEPREFIX']=os.environ.get('WINEPREFIX',str(ROOT/'tools/wine-prefix-net'))
                    command += ['--record',str(directory/(side+'.inputs'))]
                    stream=(directory/(side+'.log')).open('w');files.append(stream)
                    processes.append(subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT))
                codes=[p.wait(timeout=max(1,180-(time.monotonic()-began))) for p in processes]
            finally:
                for p in processes:
                    if p.poll() is None:p.kill()
                    p.wait(timeout=10)
                for f in files:f.close()
            logs=[(directory/(s+'.log')).read_text(errors='replace') for s in ('host','client')]
            records=[]
            for side in ('host','client'):
                path=directory/(side+'.inputs')
                records.append([l for l in path.read_text().splitlines() if l.startswith(('p1 ','p2 ','h ','e '))] if path.exists() else [])
            if incompatible:
                passed=all(c!=0 for c in codes) and any('including internal resolution and 2D filtering' in t for t in logs)
                passed &= all('connected as player' not in t for t in logs)
            else:
                passed=codes==[0,0] and all(f'complete: {end-first} frames, {checks} state checks matched' in t for t in logs) and records[0]==records[1]
            if variant=='fsr' and not incompatible:
                passed &= 'FSR1 EASU + RCAS enabled' in logs[0] and 'FSR1 presentation target' in logs[0]
                passed &= 'FSR1 EASU + RCAS enabled' not in logs[1]
            results.append({'pair':pair,'windows_via_wine':args.windows,'passed':passed,'exit_codes':codes,'matching_state_checks':checks if passed and not incompatible else 0,'recordings_equal':records[0]==records[1], 'incompatible_settings_rejected':bool(passed and incompatible),'power_on':args.boot})
            print(('PASS ' if passed else 'FAIL ')+name,flush=True)
            if not passed:raise RuntimeError('graphics synchronization failed: '+name)
        passed=all(test['passed'] for test in results)
    except Exception as e:
        results.append({'name':'runner','passed':False,'error':str(e)});print('FAIL '+str(e),flush=True);passed=False
    report.write_text(json.dumps({'passed':passed,'tests':results,'scope':('Power-on' if args.boot else 'First-district snapshot')+' loopback sessions; not full-game graphics determinism certification.'},indent=2)+'\n')
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
