#!/usr/bin/env python3
"""Load a locally captured two-Urb save and save again through real netplay.

Requires the local game-generated card from the manual Save-menu validation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from test_lan_protocol import free_port

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", action="store_true")
    parser.add_argument("--secure", action="store_true")
    parser.add_argument("--windowed", action="store_true", help="exercise the window's parallel renderer without forcing screenshot readbacks")
    parser.add_argument("--confirm-checkpoint", action="store_true", help="isolate overwriting a save using the local confirmation-dialog checkpoint")
    args = parser.parse_args()
    os.chdir(ROOT)
    case = ("tls-" if args.secure else "") + ("cross" if args.windows else "linux") + ("-confirm" if args.confirm_checkpoint else "")
    if args.windowed:case += "-windowed"
    out = ROOT / "games/urbz-pal/validation/saved-game-netplay" / case
    out.mkdir(parents=True, exist_ok=True)
    fixture = ROOT / "games/urbz-pal/validation/save-menu/card.ps2"
    if not fixture.is_file():
        parser.error("Missing local two-Urb game save fixture; it is not distributed with source.")
    host_card, client_card = out / "host.ps2", out / "client.ps2"
    shutil.copyfile(fixture, host_card)
    shutil.copyfile(fixture if args.confirm_checkpoint else ROOT / "games/urbz-pal/validation/network-saves/fixtures/client.ps2", client_card)
    initial = sha(host_card)
    port = str(free_port())
    first, end = (19300, 20600) if args.confirm_checkpoint else (0, 17000)
    frames, checks = end - first, end // 30 - first // 30
    common = ["--disc", "games/urbz-pal/disc.iso", "--game-dir", "games/urbz-pal", "--pal", "--language", "en", "--rtc", "1700000000",
              "--frames", str(end), "--net-delay", "6", "--net-timeout-ms", "30000"]
    if args.confirm_checkpoint:
        common += ["--load-state", "games/urbz-pal/validation/save-overwrite/confirm.state"]
    else:
        common += ["--net-sync-card"]
    if args.secure:
        common += ["--net-secure"]
    if args.windowed:common += ["--window"]
    host = [str(ROOT / "build/native-urbz-pal/ps2run"), *common, "--net-host", port, "--net-bind", "127.0.0.1", "--memcard", str(host_card)]
    binary = str(ROOT / ("build/wine-urbz-pal/ps2run.exe" if args.windows else "build/native-urbz-pal/ps2run"))
    client = (["wine", binary] if args.windows else [binary]) + common + ["--net-join", "127.0.0.1:" + port, "--memcard", str(client_card)]
    presses = [(19350,"up"),(19400,"cross")] if args.confirm_checkpoint else [(300,"start"),(600,"cross"),(900,"cross"),(1200,"cross"),(2100,"start"),(2700,"start"),(3300,"start"),
                          (4300,"down"),(4400,"cross"),(5000,"down"),(5100,"cross"),(6000,"cross"),(6800,"cross"),
                          (10050,"cross"),(10300,"cross"),(14500,"start"),(14700,"cross"),(15200,"cross"),(15750,"up"),(15800,"cross")]
    for frame, button in presses:
        host += ["--press", f"{frame}:{button}:3"]
    for frame in (() if args.confirm_checkpoint else (10600,10800)):
        client += ["--press", f"{frame}:cross:3"]
    processes, files = [], []
    began = time.monotonic()
    result = {"passed": False, "windows_via_wine": args.windows, "initial_card_sha256": initial,
              "confirmation_checkpoint": args.confirm_checkpoint,"windowed":args.windowed}
    result['authenticated_tls'] = args.secure
    try:
        for side, command in [("host",host),("client",client)]:
            shots = out / (side + "-shots")
            shots.mkdir(exist_ok=True)
            command += ["--record", str(out / (side + ".inputs"))]
            if not args.windowed:command += ["--frames-dir", str(shots), "--frame-every", "0", "--frame-at", str(end - 100)]
            if not args.confirm_checkpoint and not args.windowed:
                command += ["--frame-at", "14000"]
            (out / (side + ".command.json")).write_text(json.dumps(command, indent=2) + "\n")
            stream = (out / (side + ".log")).open("w")
            files.append(stream)
            env = {**os.environ,"SDL_AUDIODRIVER":"dummy","SDL_VIDEODRIVER":"dummy","PS2_GPU_BACKEND":"vulkan","WINEDEBUG":"-all","WINEDLLOVERRIDES":"mscoree,mshtml="}
            if args.windowed:
                env.pop('SDL_VIDEODRIVER',None)
                env.pop('PS2_ONE_THREAD',None)
                env['PS2_KEYS']=str(out/(side+'-keys.ini'))
            env.pop("PS2_TEST_CARD_DIRTY", None)
            if args.secure:
                env['URBZ_NET_KEY'] = '0123456789abcdef0123456789abcdef'
            processes.append(subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,env=env))
        codes = [p.wait(timeout=max(1, 600 - (time.monotonic()-began))) for p in processes]
        logs = [(out / (s + ".log")).read_text(errors="replace") for s in ("host","client")]
        writes = [max([int(n) for n in re.findall(r"(\d+) page writes", log)] or [0]) for log in logs]
        assert codes == [0,0], codes
        assert all(f"complete: {frames} frames, {checks} state checks matched" in log for log in logs)
        assert all(n > 0 for n in writes), f"game did not write a save: {writes}"
        assert sha(host_card) == sha(client_card)
        records = [[l for l in (out/(side+'.inputs')).read_text().splitlines() if l.startswith(('p1 ','p2 ','h ','e '))] for side in ('host','client')]
        assert records[0] == records[1]
        result.update(passed=True, exit_codes=codes, frames=frames, matching_state_checks=checks, game_page_writes=writes, final_card_sha256=sha(host_card), recordings_equal=True)
        print(f"PASS real game save over TCP: {frames} frames, {checks} state checks, identical written cards", flush=True)
    except Exception as error:
        result["error"] = str(error)
        print("FAIL " + str(error), flush=True)
    finally:
        for p in processes:
            if p.poll() is None:
                p.kill()
            p.wait(timeout=10)
        for f in files:
            f.close()
    result["elapsed_seconds"] = round(time.monotonic()-began,2)
    (out/"report.json").write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
