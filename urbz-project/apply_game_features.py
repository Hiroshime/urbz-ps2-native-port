#!/usr/bin/env python3
"""Add optional Urbz PAL camera and Apt interface aspect hooks to translated code.

No executable, ISO, or game-generated code is distributed by this script.
The two original instruction literals are identified by their exact ELF digest
and address. A changed translator layout is rejected rather than patched by guess.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parent.parent
MARKER='// URBZ_PAL_CAMERA_ASPECT_V1'
LABEL='L_0039B3F0:\n'
OLD=('    c.r[1].sd[0] = static_cast<std::int32_t>(0x3FAA0000u);\n'
     '    c.r[1].d[0] = c.r[1].d[0] | 43691ull;\n')
NEW=(f'    {MARKER}\n'
     '    c.r[1].sd[0] = static_cast<std::int32_t>(ps2::g_options.widescreen ? 0x3FE30000u : 0x3FAA0000u);\n'
     '    c.r[1].d[0] = c.r[1].d[0] | (ps2::g_options.widescreen ? 36394ull : 43691ull);\n')
APT_LABEL='L_00104998:\n'
APT_END='L_001049D8:\n'
APT_MARKER='// URBZ_PAL_APT_ASPECT_V1'
APT_TRANSLATED_SHA256='a31267036ebd354d63d33c2c2c3dbbf973424d25324f267c242528d54bd1a8cf'
APT_WORDS=[0xC4810000,0x3C03004C,0x246213C0,0xE46113C0,0xC4800004,
           0xE4400004,0xC4810008,0xE4410010,0xC480000C,0xE4400014,
           0xC4810010,0xE4410030,0xC4800014,0x03E00008,0xE4400034,0]
APT_OLD='    c.budget -= 15;\n'
APT_NEW=('    '+APT_MARKER+'\n'
         '    if (ps2::g_options.widescreen) {\n'
         '        std::uint32_t flags = c.fcr31; // Presentation transform preserves guest FPU flags.\n'
         '        st32(0x004C13C0u, fp::ee::mul(flags, ld32(0x004C13C0u), 0x3F400000u));\n'
         '        st32(0x004C13D0u, fp::ee::mul(flags, ld32(0x004C13D0u), 0x3F400000u));\n'
         '        st32(0x004C13F0u, fp::ee::add(flags, fp::ee::mul(flags, ld32(0x004C13F0u), 0x3F400000u), 0x42A00000u));\n'
         '    }\n'
         '    c.budget -= 15;\n')


def elf_word(data,address):
    phoff=struct.unpack_from('<I',data,28)[0]
    size,count=struct.unpack_from('<HH',data,42)
    for n in range(count):
        kind,offset,base,_,length=struct.unpack_from('<5I',data,phoff+n*size)
        if kind==1 and base<=address and address+4<=base+length:
            return struct.unpack_from('<I',data,offset+address-base)[0]
    raise ValueError('camera instruction is not file-backed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='verify that both aspect hooks are already present')
    args=parser.parse_args()
    config=json.loads((ROOT/'urbz-project/game.json').read_text())
    elf=ROOT/'games/urbz-pal/disc'/config['boot']
    data=elf.read_bytes()
    if hashlib.sha256(data).hexdigest()!=config['boot_sha256']:
        raise SystemExit('Camera hook: the game executable does not match the validated Urbz PAL revision.')
    if [elf_word(data,a) for a in [0x0039B3F0,0x0039B3F4]]!=[0x3C013FAA,0x3421AAAB]:
        raise SystemExit('Camera hook: original aspect instructions do not match.')
    if [elf_word(data,0x00104998+4*i) for i in range(len(APT_WORDS))]!=APT_WORDS:
        raise SystemExit('Apt hook: original affine-matrix callback does not match.')
    changes={}
    for label,old,new,end in [(LABEL,OLD,NEW,None),(APT_LABEL,APT_OLD,APT_NEW,APT_END)]:
        candidates=[]
        for path in (ROOT/'generated/urbz-pal').glob('unit_*.cpp'):
            text=path.read_text()
            if label in text:candidates.append((path,text))
        if len(candidates)!=1:raise SystemExit('Aspect hook: expected one translated entry; regenerate and inspect the translator output.')
        path,text=candidates[0]
        block=text[text.index(label):text.index(end)] if end else label+text.split(label,1)[1][:len(new)]
        if end and hashlib.sha256(block.replace(new,old,1).encode()).hexdigest()!=APT_TRANSLATED_SHA256:
            raise SystemExit('Apt hook: translated affine callback changed; no file modified.')
        if new in block and '#include "ps2/system.hpp"' in text:continue
        if args.check:raise SystemExit('Aspect hook is absent. Run apply_game_features.py after translating the game.')
        if block.count(old)!=1:raise SystemExit('Aspect hook: translated instructions changed; no file modified.')
        replacement=text.replace(block,block.replace(old,new,1),1)
        if '#include "ps2/system.hpp"' not in replacement:
            if '#include "units.hpp"' not in replacement:raise SystemExit('Aspect hook: translated include layout changed; no file modified.')
            replacement=replacement.replace('#include "units.hpp"','#include "units.hpp"\n#include "ps2/system.hpp"',1)
        changes[path]=replacement
    if args.check:
        print('Aspect hooks verified: optional camera and Apt 4:3/16:9 integration present.');return 0
    for path,replacement in changes.items():path.write_text(replacement)
    print('Optional Urbz PAL camera and Apt aspect hooks ready (4:3 default, 16:9 with --widescreen).')
    return 0


if __name__=='__main__':raise SystemExit(main())
