#!/usr/bin/env python3
"""Run two real game instances over loopback, optionally Linux with Windows/Wine."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from test_lan_protocol import Link, free_port

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "games/urbz-pal/validation/lan-game"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--windows", action="store_true")
    ap.add_argument("--windowed", action="store_true")
    ap.add_argument("--secure", action="store_true", help="test the authenticated direct-Internet transport on loopback")
    ap.add_argument("--case", choices=["all", "boot", "gameplay", "latency", "wan", "cross", "windowed"], default="all")
    args = ap.parse_args()
    os.chdir(ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot = "games/urbz-pal/validation/movement/frame17990.state"
    results = []
    cases = [("boot", False, False, False, False, 1200),
             ("gameplay", True, False, False, False, 18500),
             ("latency", True, True, False, False, 18120),
             ("wan", True, True, args.windows, False, 18200)]
    if args.windows:
        cases += [("cross", True, False, True, False, 18500)]
    if args.windowed:
        cases += [("windowed", True, False, args.windows, True, 18300)]
    try:
        for name, state, proxy, windows, windowed, end in cases:
            if args.case != "all" and args.case != name:
                continue
            directory = OUT / (("tls-" if args.secure else "") + name)
            directory.mkdir(exist_ok=True)
            port = free_port()
            first = 17990 if state else 0
            expected_frames = end - first
            expected_checks = end // 30 - first // 30
            delay = 6 if name == "wan" else 3
            proxy_delay = 50 if name == "wan" else 10
            common = ["--disc", "games/urbz-pal/disc.iso", "--game-dir", "games/urbz-pal", "--frames", str(end),
                      "--pal", "--language", "en", "--rtc", "1700000000", "--net-delay", str(delay), "--net-timeout-ms", "60000"]
            if state:
                common += ["--load-state", snapshot]
            if args.secure:
                common += ["--net-secure"]
            host = [str(ROOT / "build/native-urbz-pal/ps2run"), *common, "--net-host", str(port), "--net-bind", "127.0.0.1"]
            link = Link(port, delay_ms=proxy_delay, fragment=1024 if name == "wan" else 3) if proxy else None
            peer = (str(ROOT / "build/wine-urbz-pal/ps2run.exe") if windows else str(ROOT / "build/native-urbz-pal/ps2run"))
            client = (["wine", peer] if windows else [peer]) + common + ["--net-join", f"127.0.0.1:{link.port if link else port}"]
            environment = os.environ.copy()
            environment.update(SDL_AUDIODRIVER="dummy", PS2_GPU_BACKEND="vulkan", PS2_ONE_THREAD="1")
            if args.secure:
                environment['URBZ_NET_KEY'] = '0123456789abcdef0123456789abcdef'
            if windows:
                environment.update(WINEPREFIX=os.environ.get("WINEPREFIX", str(ROOT / "tools/wine-prefix-net")), WINEDEBUG="-all", WINEDLLOVERRIDES="mscoree,mshtml=")
            commands = [host, client]
            files, processes = [], []
            start = time.monotonic()
            try:
                for player, command in enumerate(commands):
                    prefix = "host" if player == 0 else "client"
                    env = environment.copy()
                    if windowed:
                        script = directory / f"{prefix}.pad"
                        axis = "lefty" if player == 0 else "leftx"
                        value = -32768 if player == 0 else 32767
                        script.write_text(f"17990 plug 0\n18100 axis 0 {axis} {value} 60\n")
                        env["PS2_PAD_SCRIPT"] = str(script.resolve())
                        shots = directory / (prefix + "-shots")
                        shots.mkdir(exist_ok=True)
                        command += ["--window", "--frames-dir", str(shots), "--frame-every", "0", "--frame-at", str(end)]
                    else:
                        command += ["--press", "18100:lup:60" if player == 0 else "18100:ldown:60"] if state else ["--press", "300:start:8"]
                    command += ["--record", str(directory / (prefix + ".inputs"))]
                    (directory / (prefix + ".command.json")).write_text(json.dumps(command, indent=2) + "\n")
                    stream = (directory / (prefix + ".log")).open("w")
                    files.append(stream)
                    # A proxy must not connect to the backend before it is listening.
                    if player == 1 and proxy:
                        deadline = time.monotonic() + 90
                        while "waiting on" not in (directory / "host.log").read_text(errors="replace"):
                            if processes[0].poll() is not None or time.monotonic() > deadline:
                                raise RuntimeError("host did not start listening")
                            time.sleep(.05)
                    processes.append(subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env=env))
                codes = [p.wait(timeout=max(1, 180-(time.monotonic()-start))) for p in processes]
            finally:
                for p in processes:
                    if p.poll() is None:
                        p.kill()
                    p.wait(timeout=10)
                for f in files:
                    f.close()
                if link:
                    link.close()
            texts = [(directory / (side + ".log")).read_text(errors="replace") for side in ["host", "client"]]
            message = f"complete: {expected_frames} frames, {expected_checks} state checks matched"
            passed = codes == [0, 0] and all(message in text for text in texts)
            recordings = []
            for side in ["host", "client"]:
                recordings.append([line for line in (directory / (side + ".inputs")).read_text().splitlines()
                                   if line.startswith(("p1 ", "p2 ", "h ", "e "))])
            passed &= recordings[0] == recordings[1]
            # Also require distinct inputs from each peer, rather than accepting
            # two identical recordings of controllers that never moved.
            if state:
                samples = [line.split() for line in recordings[0] if line.startswith(("p1 ", "p2 "))]
                host_moved = any(p[0] == "p1" and 18100 + delay <= int(p[1]) <= 18100 + delay + 7 and p[6] == "0" for p in samples)
                axis = 5 if windowed else 6
                client_moved = any(p[0] == "p2" and 18100 + delay <= int(p[1]) <= 18100 + delay + 7 and p[axis] == "255" for p in samples)
                distinct_inputs = host_moved and client_moved
            else:
                distinct_inputs = all(any(line.startswith(f"p{player} 303 0008 ") for line in recordings[0]) for player in (1, 2))
            passed &= distinct_inputs
            result = {"name": name, "passed": bool(passed), "exit_codes": codes, "frames": expected_frames,
                      "matching_state_checks": expected_checks, "input_and_checkpoint_records_equal": recordings[0] == recordings[1],
                      "both_peer_inputs_observed": distinct_inputs,
                      "windows_via_wine": windows, "windowed": windowed, "proxy_delay_ms_each_way": proxy_delay if proxy else 0,
                      "input_delay_frames": delay,
                      "authenticated_tls": args.secure,
                      "elapsed_seconds": round(time.monotonic()-start, 2)}
            results.append(result)
            print(("PASS " if passed else "FAIL ") + name + ": " + message, flush=True)
            if not passed:
                raise RuntimeError(f"{name}: check {directory}")
        if not results:
            raise RuntimeError("No test selected; use --windows or --windowed for those cases.")
        passed = True
    except Exception as error:
        results.append({"name": "runner", "passed": False, "error": str(error)})
        print("FAIL " + str(error), flush=True)
        passed = False
    report_name = "report.json" if args.case == "all" else f"report-{args.case}.json"
    (OUT / (("tls-" if args.secure else "") + report_name)).write_text(
        json.dumps({"passed": passed, "tests": results, "scope": "Loopback LAN tests; no second physical PC or Internet session tested."}, indent=2) + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
