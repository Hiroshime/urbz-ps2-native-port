#!/usr/bin/env python3
"""Validate the local two-player foundation using the user's PAL disc."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "games/urbz-pal"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--windows", action="store_true", help="also replay with the Windows build under Wine")
    ap.add_argument("--gameplay", action="store_true", help="also replay the captured two-player city scenario")
    args = ap.parse_args()
    os.chdir(ROOT)
    expected = json.loads((ROOT / "urbz-project/game.json").read_text())
    boot = GAME / "disc" / expected["boot"]
    if not boot.is_file() or digest(boot) != expected["boot_sha256"]:
        sys.exit("Executável PAL incompatível. Execute Construir-Linux.sh com a ISO configurada.")
    out = GAME / "validation/multiplayer-baseline"
    out.mkdir(parents=True, exist_ok=True)
    exe = ROOT / "build/native-urbz-pal/ps2run"
    report = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "game": expected["serial"], "boot_sha256": digest(boot),
              "linux_executable_sha256": digest(exe), "tests": [],
              "scope": "Local controls and recorded EE checkpoints; no network session or full-game certification."}
    base = ["--disc", "games/urbz-pal/disc.iso", "--game-dir", "games/urbz-pal", "--pal", "--language", "en"]

    def run(name, command, expected_code=0, contains=None, extra_env=None):
        env = os.environ.copy()
        env.update(SDL_AUDIODRIVER="dummy", SDL_VIDEODRIVER="dummy")
        if extra_env:
            env.update(extra_env)
        log = out / (name + ".log")
        (out / (name + ".command.json")).write_text(json.dumps(command, indent=2) + "\n")
        with log.open("w") as stream:
            process = subprocess.run(["timeout", "-k", "5", "180", *command], env=env,
                                     stdout=stream, stderr=subprocess.STDOUT)
        text = log.read_text(errors="replace")
        passed = process.returncode == expected_code and (contains is None or contains in text)
        entry = {"name": name, "passed": passed, "exit_code": process.returncode,
                 "log": str(log.relative_to(ROOT))}
        checks = re.search(r"(\d+) checkpoints all equal", text)
        if checks:
            entry["matching_checkpoints"] = int(checks[1])
            passed = entry["passed"] = passed and int(checks[1]) > 0
        report["tests"].append(entry)
        print(("PASS " if passed else "FAIL ") + name, flush=True)
        if not passed:
            raise RuntimeError(f"{name}: veja {log.relative_to(ROOT)}")
        return text

    try:
        run("two-controller-runtime", [str(ROOT / "build/native-urbz-pal/ps2padtest")], contains="62 checks, 0 failed")
        run("save-files", [str(ROOT / "build/native-urbz-pal/ps2savetest")], contains="0 failed")
        recording = str(out / "run.inputs")
        snapshot = str(out / "frame4100.state")
        command = [str(exe), *base, "--pad2", "--frames", "5000", "--rtc", "1700000000",
                   "--record", recording, "--save-state", "4100:" + snapshot,
                   "--frames-dir", str(out), "--frame-every", "0", "--frame-at", "4400"]
        for frame, button in [(300, "start"), (600, "cross"), (900, "cross"), (1200, "cross"),
                              (2100, "start"), (2700, "start"), (3300, "start"),
                              (4300, "down"), (4400, "cross")]:
            command += ["--press", f"{frame}:{button}:3"]
        command += ["--press2", "4700:start:3"]
        run("record-two-players", command, contains="stopped after 5000 frames")
        inputs = Path(recording).read_text()
        if not re.search(r"^p2 4700 0008 .* 1$", inputs, re.M):
            raise RuntimeError("O comando do jogador 2 não apareceu na gravação.")
        run("linux-replay", [str(exe), *base, "--replay", recording], contains="333 checkpoints all equal")

        # Change a meaningful menu input: down selected 2 Player, up selects Credits.
        changed = re.sub(r"^p1 4300 0040 ", "p1 4300 0010 ", inputs, count=1, flags=re.M)
        if changed == inputs:
            raise RuntimeError("Não foi encontrado o comando de seleção do modo 2 Player.")
        bad = out / "desync.inputs"
        bad.write_text(changed)
        run("detect-changed-input", [str(exe), *base, "--replay", str(bad)], expected_code=3, contains="DIFFERENT")

        gameplay = ["--load-state", str(GAME / "validation/movement/frame17990.state"),
                    "--replay", str(GAME / "validation/gameplay-inputs/run.inputs")]
        if args.gameplay:
            run("linux-gameplay-replay", [str(exe), *base, *gameplay], contains="34 checkpoints all equal")

        if args.windows:
            win = ROOT / "build/wine-urbz-pal/ps2run.exe"
            report["windows_executable_sha256"] = digest(win)
            env = {"WINEPREFIX": os.environ.get("WINEPREFIX", str(ROOT / "tools/wine-prefix")), "WINEDEBUG": "-all",
                   "WINEDLLOVERRIDES": "mscoree,mshtml=", "PS2_GPU_BACKEND": "vulkan"}
            run("windows-replay-via-wine", ["wine", str(win), *base, "--replay", recording],
                contains="333 checkpoints all equal", extra_env=env)
            if args.gameplay:
                run("windows-gameplay-replay-via-wine", ["wine", str(win), *base, *gameplay],
                    contains="34 checkpoints all equal", extra_env=env)
        report["passed"] = True
    except (RuntimeError, OSError) as error:
        report["passed"] = False
        report["error"] = str(error)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Relatório: " + str((out / "report.json").relative_to(ROOT)))
    if not report["passed"]:
        print(report["error"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
