#!/usr/bin/env python3
"""Compare actual PAL pacing and gameplay against a preserved local runner.

Requires the private two-player snapshot and user-owned ISO. Uses dummy audio to
exercise the audio queue while timing refreshes through SDL's performance clock.
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

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'games/urbz-pal/validation/pacing'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(name, executable, windows=False):
    directory = OUT / name
    directory.mkdir(parents=True, exist_ok=True)
    env = {k:v for k,v in os.environ.items() if not k.startswith('PS2_')}
    env.update(PS2_SCALE='2', PS2_LOOK='sharp_edges', PS2_SHARP_2D='1', PS2_UPSCALER='fsr1',
               PS2_GPU_BACKEND='vulkan', PS2_NO_VU_THREAD='1', PS2_GS_SYNC_READBACK='1',
               PS2_EE_LIVE='0', PS2_VU_LIVE='0', SDL_AUDIODRIVER='dummy',
               PS2_FRAME_LOG=str(directory/'frames.txt'), PS2_KEYS=str(directory/'keys.ini'),
               WINEDEBUG='-all', WINEDLLOVERRIDES='mscoree,mshtml=')
    command = (['wine'] if windows else []) + [str(executable), '--disc', 'games/urbz-pal/disc.iso',
               '--game-dir', 'games/urbz-pal', '--pal', '--language', 'en', '--window', '--fullscreen',
               '--window-size', '2560x1440', '--widescreen', '--pad2', '--rtc', '1700000000',
               '--load-state', 'games/urbz-pal/validation/movement/frame17990.state', '--frames', '18990',
               '--press', '18100:lup:60', '--press2', '18100:ldown:60', '--record', str(directory/'run.inputs')]
    with (directory/'run.log').open('w') as log:
        done = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    text = (directory/'run.log').read_text(errors='replace')
    assert done.returncode == 0 and 'stopped after 18990 frames' in text, name + ': runner failed'
    assert 'FSR1 presentation target 2560x1440' in text, name + ': FSR/QHD inactive'
    assert 'PS2_NO_LIMIT is set' not in text
    rows = [line.split() for line in (directory/'frames.txt').read_text().splitlines()[1:]]
    rows = [row for row in rows if 18191 <= int(row[0]) <= 18990]
    assert len(rows) == 800
    mean = statistics.mean(float(row[1]) for row in rows)
    pictures, refreshes = map(int, re.search(r'\[pace\] (\d+) new pictures in (\d+) refreshes', text).groups())
    records = [line for line in (directory/'run.inputs').read_text().splitlines() if line.startswith(('p1 ', 'p2 ', 'h ', 'e '))]
    item = {'name':name, 'windows_via_wine':windows, 'executable_sha256':sha(executable),
            'measured_refreshes':len(rows), 'mean_ms':round(mean, 5), 'refreshes_per_second':round(1000/mean, 5),
            'new_pictures':pictures, 'total_refreshes':refreshes, 'directory':str(directory.relative_to(ROOT))}
    if name != 'baseline':
        assert 'audio correction can slow execution only' in text
        assert 49.4 <= 1000/mean <= 50.03, name + ': pacing outside the expected nominal-rate bound'
    print(f'PASS {name}: {1000/mean:.5f} refreshes/s', flush=True)
    return item, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT/'build/pacing-baseline/ps2run')
    parser.add_argument('--windows', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    report = {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'passed':False, 'tests':[],
              'scope':'One private two-player PAL district, sequential real window runs, parallel renderer, FSR1/QHD/16:9, dummy audio, 1000 refreshes with 200 warm-up excluded. Not a physical-console movement comparison or full-game certification.'}
    try:
        cases = [('baseline', args.baseline.resolve(), False), ('linux', ROOT/'build/native-urbz-pal/ps2run', False)]
        if args.windows:
            cases.append(('windows', ROOT/'build/wine-urbz-pal/ps2run.exe', True))
        reference = None
        for name, executable, windows in cases:
            item, records = run(name, executable, windows)
            if reference is None:
                reference = records
            assert records == reference, name + ': gameplay checkpoints changed'
            item['gameplay_checkpoints_equal_to_baseline'] = True
            report['tests'].append(item)
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
        print('FAIL ' + str(error), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
