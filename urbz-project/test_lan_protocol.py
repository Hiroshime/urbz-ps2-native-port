#!/usr/bin/env python3
"""Exercise the actual TCP transport without a game or graphics device."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "build/native-urbz-pal/ps2nettest"
OUT = ROOT / "games/urbz-pal/validation/lan-protocol"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Link:
    """An owned loopback proxy introducing delay and tiny writes in both directions."""
    def __init__(self, target, delay_ms=10, fragment=3, transform=None):
        self.target = target
        self.delay = delay_ms / 1000
        self.fragment = fragment
        self.transform = transform
        self.stop = threading.Event()
        self.sockets = []
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.port = self.server.getsockname()[1]
        self.server.listen(1)
        self.server.settimeout(.1)
        self.thread = threading.Thread(target=self.accept, daemon=True)
        self.thread.start()

    def accept(self):
        try:
            while not self.stop.is_set():
                try:
                    client, _ = self.server.accept()
                    break
                except socket.timeout:
                    continue
            else:
                return
            backend = socket.create_connection(("127.0.0.1", self.target), timeout=5)
            self.sockets = [client, backend]
            for sock in self.sockets:
                sock.settimeout(.1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            threads = [threading.Thread(target=self.forward, args=pair, daemon=True)
                       for pair in [(client, backend), (backend, client)]]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        except OSError:
            pass

    def forward(self, source, target):
        try:
            while not self.stop.is_set():
                try:
                    data = source.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    target.shutdown(socket.SHUT_WR)
                    return
                if self.transform:
                    data = self.transform(source is self.sockets[0], data)
                    if not data:
                        continue
                if self.stop.wait(self.delay):
                    return
                for i in range(0, len(data), self.fragment):
                    target.sendall(data[i:i + self.fragment])
        except OSError:
            pass

    def close(self):
        self.stop.set()
        self.server.close()
        for sock in self.sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        self.thread.join(timeout=2)


@contextmanager
def process(command, log):
    with log.open("w") as stream:
        p = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        try:
            yield p
        finally:
            if p.poll() is None:
                p.kill()
            p.wait(timeout=5)


def wait_for(log, text, p, seconds=5):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if text in log.read_text(errors="replace"):
            return
        if p.poll() is not None:
            break
        time.sleep(.01)
    raise RuntimeError(f"{log.name}: did not reach {text!r}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []

    def pair(name, delay=3, client_args=(), host_args=(), good=True, proxy=False, contains=None):
        port = free_port()
        host_log, client_log = OUT / f"{name}-host.log", OUT / f"{name}-client.log"
        link = None
        try:
            with process([str(PROBE), "--host", "--port", str(port), "--delay", str(delay), *host_args], host_log) as host:
                wait_for(host_log, "waiting on", host)
                if proxy:
                    link = Link(port)
                with process([str(PROBE), "--port", str(link.port if link else port), "--delay", str(delay), *client_args], client_log) as client:
                    codes = [host.wait(timeout=15), client.wait(timeout=15)]
            text = host_log.read_text() + client_log.read_text()
            okay = codes == [0, 0] if good else all(code != 0 for code in codes)
            if good:
                okay &= text.count("120 frames, 4 state checks matched") == 2
            if contains:
                okay &= contains in text
            results.append({"name": name, "passed": bool(okay), "exit_codes": codes})
            print(("PASS " if okay else "FAIL ") + name, flush=True)
            if not okay:
                raise RuntimeError(name)
        finally:
            if link:
                link.close()

    try:
        subprocess.run([str(PROBE), "--self-test"], check=True)
        data = OUT / "sha-stream.bin"
        data.write_bytes(bytes(range(256)) * 4097)
        actual = subprocess.check_output([str(PROBE), "--hash-file", str(data)], text=True).strip()
        assert actual == hashlib.sha256(data.read_bytes()).hexdigest()
        data.unlink()
        results.append({"name": "sha256-vectors-and-file-stream", "passed": True})
        for delay in [0, 3, 12]:
            pair(f"controller-routing-delay-{delay}", delay=delay)
        held = []
        try:
            # A large inherited descriptor table must fail cleanly before FD_SET
            # could write outside its fixed-size buffer on POSIX.
            held = [os.open(os.devnull, os.O_RDONLY) for _ in range(1030)]
            check = subprocess.run([str(PROBE), "--host", "--port", str(free_port())],
                                   pass_fds=held, capture_output=True, text=True, timeout=5)
            okay = check.returncode != 0 and "socket descriptor exceeds the select limit" in check.stderr
            results.append({"name": "large-socket-descriptor-rejected", "passed": okay})
            print(("PASS " if okay else "FAIL ") + "large-socket-descriptor-rejected", flush=True)
            if not okay:
                raise RuntimeError("large-socket-descriptor-rejected")
        finally:
            for fd in held:
                os.close(fd)
        pair("delayed-fragmented-tcp", proxy=True)
        pair("wrong-game-rejected", client_args=["--bad-game"], good=False, contains="game executable differs")
        pair("wrong-delay-rejected", client_args=["--delay", "4"], good=False, contains="input delay differs")
        pair("shared-card-transferred", host_args=["--sync-card"], client_args=["--sync-card"], contains="shared card content verified")
        pair("shared-card-mode-mismatch", host_args=["--sync-card"], good=False, contains="synchronization mode differs")
        pair("shared-card-install-failure", host_args=["--sync-card"], client_args=["--sync-card", "--reject-card"], good=False, contains="installation rejected")
        pair("shared-card-final-mismatch", host_args=["--sync-card"], client_args=["--sync-card", "--bad-save"], good=False, contains="memory cards differ at session end")
        pair("desync-detected", client_args=["--bad-check", "60"], good=False, contains="DESYNC at frame 60")
        pair("disconnect-detected", client_args=["--drop", "40"], good=False, contains="disconnected")
        for name, payload, needle in [("oversized-message-rejected", (513).to_bytes(4, "big"), "invalid network message length"),
                                      ("silent-peer-timeout", b"", "timeout waiting")]:
            port, log = free_port(), OUT / (name + ".log")
            with process([str(PROBE), "--host", "--port", str(port), "--timeout", "500"], log) as host:
                wait_for(log, "waiting on", host)
                with socket.create_connection(("127.0.0.1", port)) as peer:
                    if payload:
                        peer.sendall(payload)
                    code = host.wait(timeout=5)
            okay = code != 0 and needle in log.read_text()
            results.append({"name": name, "passed": okay, "exit_code": code})
            print(("PASS " if okay else "FAIL ") + name, flush=True)
            if not okay:
                raise RuntimeError(name)
        passed = True
    except Exception as error:
        results.append({"name": "test-runner", "passed": False, "error": str(error)})
        passed = False
    (OUT / "report.json").write_text(json.dumps({"passed": passed, "tests": results}, indent=2) + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
