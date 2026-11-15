#!/usr/bin/env python3
"""Check authenticated Internet transport, including rejection before card access."""
import json
import os
from pathlib import Path
import socket
import subprocess
from test_lan_protocol import Link, free_port, wait_for

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'games/urbz-pal/validation/direct-tls'
PROBE = ROOT / 'build/native-urbz-pal/ps2nettest'
# Public test vector, not a key used by the user's launchers.
KEY = '0123456789abcdef0123456789abcdef'


class Tamper:
    def __init__(self):
        self.buffers = {True: bytearray(), False: bytearray()}
        self.changed = False

    def __call__(self, client_to_host, data):
        buf = self.buffers[client_to_host]
        buf.extend(data)
        out = bytearray()
        while len(buf) >= 5:
            size = 5 + int.from_bytes(buf[3:5], 'big')
            if len(buf) < size:
                break
            record = buf[:size]
            del buf[:size]
            if client_to_host and record[0] == 23 and not self.changed:
                record[-1] ^= 1  # Damage the authenticated TLS record tag.
                self.changed = True
            out.extend(record)
        return bytes(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []

    def pair(name, host_args=(), client_args=(), bad_key=False, bad=False, proxy=False, tamper=None):
        port = free_port()
        processes, streams = [], []
        link = None
        logs = [OUT / (name + '-' + s + '.log') for s in ('host','client')]
        try:
            for player, (extra, path) in enumerate(zip((host_args,client_args),logs)):
                if player:
                    wait_for(logs[0], 'waiting on', processes[0])
                    if proxy or tamper:
                        link = Link(port, delay_ms=10, fragment=3, transform=tamper)
                args = [str(PROBE), '--port', str(link.port if player and link else port), '--secure', '--timeout', '1500', *extra]
                if not player:
                    args.append('--host')
                env = {**os.environ, 'URBZ_NET_KEY': 'f'*32 if player and bad_key else KEY}
                stream = path.open('w'); streams.append(stream)
                processes.append(subprocess.Popen(args, cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT))
            codes = [p.wait(timeout=20) for p in processes]
        finally:
            for p in processes:
                if p.poll() is None:p.kill()
                p.wait(timeout=5)
            for f in streams:f.close()
            if link:link.close()
        texts = [p.read_text(errors='replace') for p in logs]
        passed = all(c != 0 for c in codes) if bad else codes == [0,0]
        if not bad:
            passed &= all('120 frames, 4 state checks matched' in t for t in texts)
            passed &= all('authenticated encrypted connection' in t for t in texts)
        if bad_key or tamper:
            passed &= all('shared memory card synchronized' not in t for t in texts)
        if tamper:passed &= tamper.changed
        results.append({'name':name,'passed':bool(passed),'exit_codes':codes})
        print(('PASS ' if passed else 'FAIL ')+name,flush=True)
        if not passed:raise RuntimeError(name)

    try:
        pair('encrypted-controller-routing')
        pair('encrypted-card-transfer',host_args=['--sync-card'],client_args=['--sync-card'])
        pair('encrypted-fragmented-stream',proxy=True)
        pair('wrong-key-no-card-transfer',host_args=['--sync-card'],client_args=['--sync-card'],bad_key=True,bad=True)
        pair('tampered-record-no-card-transfer',host_args=['--sync-card'],client_args=['--sync-card'],tamper=Tamper(),bad=True)
        pair('encrypted-desync-detected',client_args=['--bad-check','60'],bad=True)
        pair('encrypted-disconnect-detected',client_args=['--drop','40'],bad=True)

        # A bad key must not consume the host's waiting room; a friend can retry.
        port=free_port(); host_log=OUT/'retry-host.log'; good_log=OUT/'retry-good.log'; bad_log=OUT/'retry-bad.log'
        env={**os.environ,'URBZ_NET_KEY':KEY}
        with host_log.open('w') as hs, good_log.open('w') as gs, bad_log.open('w') as bs:
            host=subprocess.Popen([str(PROBE),'--host','--port',str(port),'--secure','--timeout','8000'],stdout=hs,stderr=subprocess.STDOUT,env=env,cwd=ROOT)
            try:
                wait_for(host_log,'waiting on',host)
                bad=subprocess.run([str(PROBE),'--port',str(port),'--secure'],stdout=bs,stderr=subprocess.STDOUT,env={**env,'URBZ_NET_KEY':'f'*32},cwd=ROOT,timeout=10)
                assert bad.returncode != 0
                good=subprocess.run([str(PROBE),'--port',str(port),'--secure'],stdout=gs,stderr=subprocess.STDOUT,env=env,cwd=ROOT,timeout=10)
                assert good.returncode == 0 and host.wait(timeout=10)==0
            finally:
                if host.poll() is None:host.kill()
                host.wait(timeout=5)
        results.append({'name':'friend-can-join-after-rejected-peer','passed':True})
        print('PASS friend-can-join-after-rejected-peer',flush=True)
        done=True
    except Exception as error:
        results.append({'name':'runner','passed':False,'error':str(error)})
        print('FAIL '+str(error),flush=True);done=False
    (OUT/'report.json').write_text(json.dumps({'passed':done,'tests':results,'scope':'Real TLS over loopback; no Internet/router traversal certified.'},indent=2)+'\n')
    return 0 if done else 1


if __name__=='__main__':raise SystemExit(main())
