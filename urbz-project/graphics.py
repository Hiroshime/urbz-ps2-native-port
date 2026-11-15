#!/usr/bin/env python3
"""Select optional launcher presets without editing the ISO or game saves."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PRESETS = Path(__file__).with_name('graphics-presets.json')
CONFIG = ROOT / 'games/urbz-pal/user/graphics.json'


def resolve(profile=None, config=CONFIG):
    data = json.loads(PRESETS.read_text(encoding='utf-8-sig'))
    if not profile:
        if config.exists():
            saved = json.loads(config.read_text(encoding='utf-8-sig'))
            if saved.get('version') != 1:raise ValueError('versão de configuração gráfica não reconhecida')
            profile = saved['profile']
        else:profile = data['default']
    if not isinstance(profile,str):raise ValueError('nome do perfil inválido')
    profile=profile.strip().lower()
    if profile not in data['presets']:
        raise ValueError('perfil desconhecido; escolha padrao, original, hd, alto, ultra ou qhd')
    return profile, data['presets'][profile]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['resolve','select','list'])
    parser.add_argument('profile',nargs='?',default=None)
    parser.add_argument('--config',type=Path,default=CONFIG)
    args = parser.parse_args()
    try:
        presets=json.loads(PRESETS.read_text(encoding='utf-8'))['presets']
        if args.action == 'list' or (args.action == 'select' and not args.profile):
            for n,(name,value) in enumerate(presets.items(),1):
                print(f'{n}. {value["label"]} ({name}) — {value["description"]}')
            if args.action=='list':return 0
            choice=input('Escolha o número ou o nome do perfil: ').strip().lower()
            args.profile=list(presets)[int(choice)-1] if choice.isdigit() and 1 <= int(choice) <= len(presets) else choice
        name,value=resolve(args.profile,args.config)
        if args.action=='resolve':
            print(name)
            print(value['scale'] or 0)
            print(value['look'] or '-')
            print(value['sharp_2d'] if value['sharp_2d'] is not None else -1)
            print(value['label'])
            print(value.get('upscaler','-'))
            print(value.get('window_size','-'))
            return 0
        args.config.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(prefix='graphics-',suffix='.tmp',dir=args.config.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as out:
                json.dump({'version':1,'profile':name},out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
            os.replace(temp,args.config)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        print(f'Perfil {value["label"]} selecionado para a próxima abertura. Configuração: {args.config}')
        return 0
    except (ValueError,KeyError,OSError,EOFError) as error:
        print('Gráficos: '+str(error),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
