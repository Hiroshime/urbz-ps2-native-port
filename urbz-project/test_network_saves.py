#!/usr/bin/env python3
"""Exercise shared memory cards through the real runner and TCP connection.

The write test uses the runtime's explicit IOP test hook. It proves persistence
and resynchronization, not that every mission in The Urbz can be saved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from test_lan_protocol import free_port

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "games/urbz-pal/validation/network-saves"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", action="store_true")
    parser.add_argument("--secure", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    fixtures = OUT / "fixtures"
    fixtures.mkdir(exist_ok=True)
    for name, date in [("host", "2026-01-01 00:00:00"), ("client", "2026-02-01 00:00:00")]:
        target = fixtures / f"{name}.ps2"
        if not target.exists():
            subprocess.run(["python3", "scripts/mcformat.py", str(target), "--date", date], check=True)
    results = []

    def pair(name, host_card, client_card, marker=False, fail=False, one_sided_marker=False):
        directory = OUT / (("tls-" if args.secure else "") + ("windows-" if args.windows else "linux-") + name)
        directory.mkdir(exist_ok=True)
        port = str(free_port())
        common = ["--disc", "games/urbz-pal/disc.iso", "--game-dir", "games/urbz-pal", "--pal", "--language", "en",
                  "--rtc", "1700000000", "--frames", "120", "--net-delay", "6", "--net-timeout-ms", "5000", "--net-sync-card"]
        if args.secure:
            common += ["--net-secure"]
        host = [str(ROOT / "build/native-urbz-pal/ps2run"), *common, "--net-host", port, "--net-bind", "127.0.0.1", "--memcard", str(host_card)]
        binary = str(ROOT / ("build/wine-urbz-pal/ps2run.exe" if args.windows else "build/native-urbz-pal/ps2run"))
        client = (["wine", binary] if args.windows else [binary]) + common + ["--net-join", "127.0.0.1:" + port, "--memcard", str(client_card)]
        processes, streams = [], []
        start = time.monotonic()
        try:
            for index, command in enumerate([host, client]):
                env = os.environ.copy()
                env.update(SDL_AUDIODRIVER="dummy", SDL_VIDEODRIVER="dummy", WINEDEBUG="-all", WINEDLLOVERRIDES="mscoree,mshtml=", PS2_GPU_BACKEND="vulkan")
                if args.secure:
                    env['URBZ_NET_KEY'] = '0123456789abcdef0123456789abcdef'
                if marker or (one_sided_marker and index == 1):
                    env["PS2_TEST_CARD_DIRTY"] = "80"
                else:
                    env.pop("PS2_TEST_CARD_DIRTY", None)
                stream = (directory / ("host.log" if index == 0 else "client.log")).open("w")
                streams.append(stream)
                processes.append(subprocess.Popen(command, env=env, stdout=stream, stderr=subprocess.STDOUT))
            codes = [p.wait(timeout=max(1, 100 - (time.monotonic() - start))) for p in processes]
        finally:
            for p in processes:
                if p.poll() is None:
                    p.kill()
                p.wait(timeout=10)
            for stream in streams:
                stream.close()
        logs = [(directory / name).read_text(errors="replace") for name in ("host.log", "client.log")]
        passed = all(c != 0 for c in codes) if fail else codes == [0, 0] and all("complete: 120 frames, 4 state checks matched" in log for log in logs)
        result = {"name": name, "passed": passed, "exit_codes": codes, "windows_via_wine": args.windows, "authenticated_tls": args.secure}
        results.append(result)
        if not passed:
            raise RuntimeError(f"{name}: inspect {directory}")
        return logs

    try:
        work = OUT / ("cross-cards" if args.windows else "linux-cards")
        work.mkdir(exist_ok=True)
        host_card, client_card = work / "host.ps2", work / "client.ps2"
        shutil.copyfile(fixtures / "host.ps2", host_card)
        shutil.copyfile(fixtures / "client.ps2", client_card)
        before = digest(client_card)
        pair("write-and-share", host_card, client_card, marker=True)
        assert digest(host_card) == digest(client_card)
        assert digest(Path(str(client_card) + ".before-net.ps2")) == before
        image = host_card.read_bytes()
        assert b"card flush test, frame 80" in image[4000 * 528:4000 * 528 + 100]
        saved = digest(host_card)
        print("PASS shared card transfer, previous-client backup and persistent IOP write", flush=True)

        # A stale client must receive the host's existing progress on the next run.
        shutil.copyfile(fixtures / "client.ps2", client_card)
        pair("restart-with-stale-client", host_card, client_card)
        assert digest(host_card) == digest(client_card) == saved
        print("PASS restart keeps saved bytes and replaces stale client cache", flush=True)

        shutil.copyfile(fixtures / "client.ps2", client_card)
        before = digest(client_card)
        backup = Path(str(client_card) + ".before-net.ps2")
        backup.unlink(missing_ok=True)
        backup.mkdir()
        try:
            logs = pair("backup-failure-preserves-client", host_card, client_card, fail=True)
            assert any("cannot install shared memory card" in log for log in logs)
            assert digest(client_card) == before and digest(host_card) == saved
        finally:
            backup.rmdir()
        print("PASS failed backup stops session and preserves both cards", flush=True)

        shutil.copyfile(fixtures / "host.ps2", host_card)
        logs = pair("different-final-card-detected", host_card, client_card, one_sided_marker=True, fail=True)
        assert any("memory cards differ at session end" in log for log in logs)
        print("PASS different final memory cards detected", flush=True)
        passed = True
    except Exception as error:
        results.append({"name": "runner", "passed": False, "error": str(error)})
        print("FAIL " + str(error), flush=True)
        passed = False
    report = {"passed": passed, "tests": results,
              "scope": "Loopback shared-card bootstrap, explicit IOP test-hook write, restart and failure safety. No full-game save certification."}
    report_name = "report-windows.json" if args.windows else "report-linux.json"
    (OUT / (("tls-" if args.secure else "") + report_name)).write_text(json.dumps(report, indent=2) + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
