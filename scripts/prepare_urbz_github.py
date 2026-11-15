#!/usr/bin/env python3
"""Audit publishable sources; optionally export a source-only working-tree archive."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROOTS = {'games','generated','tools','build','dist','isos','logs','.git','.aws','.codex','.agents'}
PRIVATE_SUFFIXES = {'.iso','.chd','.cso','.bin','.elf','.exe','.dll','.a','.o','.obj','.wasm','.ps2','.mcd','.mc2','.sav','.state','.sstate','.dmp','.ppm','.png','.jpg','.jpeg','.mp4','.wav','.zip','.7z','.rar','.pnach','.pem','.key'}
SECRETS = [re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
           re.compile(rb'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{30,}'),
           re.compile(rb'\bAKIA[0-9A-Z]{16}\b')]


def git(*args):
    return subprocess.check_output(['git','-c',f'safe.directory={ROOT}',*args],cwd=ROOT)


def forbidden(name):
    p=Path(name)
    return (p.parts[0] in PRIVATE_ROOTS or p.suffix.lower() in PRIVATE_SUFFIXES or
            p.name=='.env' or (p.name.startswith('.env.') and p.name!='.env.example') or
            p.name.endswith(('.tar.gz','.tar.xz','.tar.zst','.pyc')) or '__pycache__' in p.parts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='audit without creating an archive')
    parser.add_argument('--archive',action='store_true',help='export only audited source files, without Git history')
    args=parser.parse_args()
    names=sorted(set(n.decode() for n in git('ls-files','--cached','--others','--exclude-standard','-z').split(b'\0') if n))
    issues=[]
    for name in names:
        path=ROOT/name
        if forbidden(name):issues.append((name,'excluded artifact in publication candidates'));continue
        if path.is_symlink():issues.append((name,'symlink requires manual review'));continue
        if not path.is_file():issues.append((name,'tracked file missing'));continue
        data=path.read_bytes()
        if len(data)>5*1024*1024:issues.append((name,'source exceeds 5 MiB'))
        if any(rule.search(data) for rule in SECRETS):issues.append((name,'possible credential; inspect locally'))
        if re.search(rb'/home/[A-Za-z0-9_.-]+/(?:Downloads|Documents)/',data):issues.append((name,'private absolute workspace path'))
    historical=0
    for line in git('rev-list','--objects','--all').decode().splitlines():
        fields=line.split(' ',1)
        if len(fields)==2 and fields[1] and forbidden(fields[1]):
            issues.append((fields[1],'excluded artifact in reachable Git history'));historical+=1
    if issues:
        for name,reason in issues:print(f'FAIL {name}: {reason}')
        return 1
    print(f'PASS {len(names)} source files; no blocked artifacts, recognized credentials or private workspace paths in candidates.')
    print('PASS reachable Git history paths; this is a bounded audit, not proof against every possible secret.')
    shallow=git('rev-parse','--is-shallow-repository').strip()==b'true'
    if shallow:print('INFO shallow checkout: history checks cover locally available objects only.')
    if args.archive:
        output=ROOT/'dist/source';output.mkdir(parents=True,exist_ok=True)
        archive=output/'urbz-ps2-source.tar.gz'
        with tarfile.open(archive,'w:gz',dereference=False) as tar:
            for name in names:
                path=ROOT/name;info=tar.gettarinfo(str(path),arcname='urbz-ps2-port/'+name)
                info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                info.mode=0o755 if path.stat().st_mode & 0o111 else 0o644
                with path.open('rb') as stream:tar.addfile(info,stream)
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        (output/'SHA256SUMS').write_text(f'{digest}  {archive.name}\n')
        (output/'audit.json').write_text(json.dumps({'files':len(names),'sha256':digest,'source_archive':archive.name,'git_history_included':False,'shallow_checkout':shallow,'scope':'Working-tree candidates scanned for excluded artifacts, common credential patterns, size, symlinks and private workspace path. Locally reachable Git history checked by path only.'},indent=2)+'\n')
        print(f'Exported {archive.relative_to(ROOT)} ({archive.stat().st_size} bytes)')
    return 0


if __name__=='__main__':raise SystemExit(main())
