#!/usr/bin/env python3
"""Validate real final-image FSR1 output and unchanged gameplay on a local fixture.

Requires the user's two-player district snapshot, a built runner, an accessible
2560x1440 desktop and Pillow/NumPy. Captures are private game-derived artifacts.
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
OUT = ROOT / 'games/urbz-pal/validation/fsr'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(mode, capture, windows, wide):
    directory = OUT / (('windows' if windows else 'linux') + ('-wide' if wide else '')) / mode / ('capture' if capture else 'performance')
    directory.mkdir(parents=True, exist_ok=True)
    shots = directory / 'shots'
    shots.mkdir(exist_ok=True)
    end = 18100 if capture else 18500
    exe = ROOT / ('build/wine-urbz-pal/ps2run.exe' if windows else 'build/native-urbz-pal/ps2run')
    command = (['wine'] if windows else []) + [str(exe), '--disc', 'games/urbz-pal/disc.iso', '--game-dir', 'games/urbz-pal',
               '--pal', '--language', 'en', '--fullscreen', '--window-size', '2560x1440', '--pad2',
               '--load-state', 'games/urbz-pal/validation/movement/frame17990.state', '--frames', str(end),
               '--rtc', '1700000000', '--no-record', '--record', str(directory / 'run.inputs'),
               '--press', '18100:lup:60', '--press2', '18100:ldown:60']
    if wide:
        command += ['--widescreen']
    env = {k:v for k,v in os.environ.items() if not k.startswith('PS2_')}
    env.update(PS2_SCALE='2', PS2_LOOK='sharp_edges', PS2_SHARP_2D='1', PS2_GPU_BACKEND='vulkan',
               PS2_UPSCALER=mode, PS2_EE_LIVE='0', PS2_VU_LIVE='0', PS2_NO_VU_THREAD='1', PS2_GS_SYNC_READBACK='1',
               PS2_ONE_THREAD='1', PS2_NO_LIMIT='1', PS2_PRESENT_MODE='immediate', SDL_AUDIODRIVER='dummy',
               PS2_KEYS=str(directory / 'keys.ini'), WINEDEBUG='-all', WINEDLLOVERRIDES='mscoree,mshtml=')
    if capture:
        env['PS2_PRESENT_CAPTURE'] = '18080:' + str(directory / 'presented.ppm')
        command += ['--frames-dir', str(shots), '--frame-every', '0', '--frame-at', '18080']
    else:
        env['PS2_FRAME_LOG'] = str(directory / 'frames.txt')
    with (directory / 'run.log').open('w') as log:
        done = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    text = (directory / 'run.log').read_text(errors='replace')
    if done.returncode or f'stopped after {end} frames' not in text:
        raise RuntimeError(f'Runner failed: {directory.relative_to(ROOT)}/run.log')
    assert '[window] presenting through WebGPU' in text
    assert ('FSR1 EASU + RCAS enabled' in text) == (mode == 'fsr1')
    if mode == 'fsr1':
        assert ('FSR1 presentation target ' + ('2560x1440' if wide else '1920x1440')) in text
    records = [line for line in (directory / 'run.inputs').read_text().splitlines() if line.startswith(('p1 ', 'p2 ', 'h ', 'e '))]
    result = {'mode': mode, 'directory': str(directory.relative_to(ROOT)), 'passed': True}
    if capture:
        from PIL import Image
        final = Image.open(directory / 'presented.ppm')
        assert final.size == (2560, 1440), 'Desktop did not provide actual QHD output'
        final.save(directory / 'presented.png')
        result.update(output_size=list(final.size), raw_capture_sha256=sha(shots / 'frame_18080.ppm'), presented_sha256=sha(directory / 'presented.ppm'))
    else:
        rows = [line.split() for line in (directory / 'frames.txt').read_text().splitlines()[1:]]
        rows = [row for row in rows if 18101 <= int(row[0]) <= 18500]
        assert len(rows) == 400
        times = [float(row[1]) for row in rows]
        pace = re.search(r'\[pace\] (\d+) new pictures in (\d+) refreshes', text)
        pictures, refreshes = map(int, pace.groups())
        result.update(mean_ms=round(statistics.mean(times), 3), p95_ms=round(sorted(times)[379], 3),
                      refreshes_per_second=round(1000 / statistics.mean(times), 2),
                      new_pictures_total=pictures, refreshes_total=refreshes,
                      interpreted_vu_calls=sum(int(row[6]) for row in rows))
    print('PASS ' + mode + (' capture' if capture else ' performance'), flush=True)
    return result, records


def main():
    import numpy as np
    from PIL import Image
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows', action='store_true', help='Exercise the Windows executable via Wine; not native Windows certification')
    parser.add_argument('--widescreen', action='store_true', help='Validate corrected 16:9 presentation instead of default 4:3')
    parser.add_argument('--captures-only', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    executable = ROOT / ('build/wine-urbz-pal/ps2run.exe' if args.windows else 'build/native-urbz-pal/ps2run')
    report = {'executable_sha256': sha(executable),
              'snapshot_sha256': sha(ROOT / 'games/urbz-pal/validation/movement/frame17990.state'),
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'windows_via_wine': args.windows, 'widescreen': args.widescreen,
              'scope': 'One two-player district, actual fullscreen 2560x1440 Vulkan presentation. Sequential uncapped performance; 400 refreshes after warm-up, no diagnostic capture in timing runs. Not campaign certification.', 'tests': []}
    try:
        captured = [run(mode, True, args.windows, args.widescreen) for mode in ('off', 'fsr1')]
        assert captured[0][1] == captured[1][1], 'FSR changed recorded gameplay checkpoints'
        assert captured[0][0]['raw_capture_sha256'] == captured[1][0]['raw_capture_sha256'], 'FSR changed the source GS image'
        report['tests'] += [item[0] for item in captured]
        arrays = [np.asarray(Image.open(ROOT / item[0]['directory'] / 'presented.ppm')) for item in captured]
        for array in arrays:
            if not args.widescreen:
                assert not array[:, :320].any() and not array[:, 2240:].any(), '4:3 letterbox changed'
            assert np.std(array[:, 320:2240].astype(float)) > 20, 'Unexpected blank output'
        left, right = (0,2560) if args.widescreen else (320,2240)
        diff = np.abs(arrays[0][:,left:right].astype(float) - arrays[1][:,left:right].astype(float))
        changed = float(np.mean(np.max(diff, axis=2) > 0))
        assert changed > 0.05, 'Filter did not measurably change the presented image'
        report.update(raw_images_equal=True, gameplay_checkpoints_equal=True, letterbox_preserved=True,
                      changed_content_fraction=round(changed, 6), mean_absolute_channel_difference=round(float(np.mean(diff)), 4))
        if not args.captures_only:
            measured = [run(mode, False, args.windows, args.widescreen) for mode in ('off', 'fsr1')]
            assert measured[0][1] == measured[1][1], 'Performance run changed gameplay checkpoints'
            report['tests'] += [item[0] for item in measured]
        report['passed'] = True
    except Exception as error:
        report.update(passed=False, error=str(error))
        print('FAIL ' + str(error), flush=True)
    out = OUT / (('report-windows' if args.windows else 'report-linux') + ('-wide' if args.widescreen else '') + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
