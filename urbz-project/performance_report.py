#!/usr/bin/env python3
"""Plot the measured sequential renderer comparison without changing its data."""
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'games/urbz-pal/validation/performance'
os.environ.setdefault('MPLCONFIGDIR',str(OUT/'matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    report=json.loads((OUT/'report.json').read_text())
    if not report['passed']:raise SystemExit('Benchmark failed; no chart exported.')
    fig,ax=plt.subplots(figsize=(10,6),layout='constrained')
    fig.get_layout_engine().set(rect=(0,.055,1,.945))
    rows=report['results'];indices=list(range(len(rows)));width=.25
    for offset,key,label,color in [(-width,'baseline','Executável anterior','#64748b'),(0,'aot','VU compilado','#0891b2'),(width,'optimized','VU + apresentação direta','#0d9488')]:
        bars=ax.bar([i+offset for i in indices],[r[key]['refreshes_per_second'] for r in rows],width,label=label,color=color)
        ax.bar_label(bars,fmt='%.1f',padding=3,fontsize=9)
    ax.axhline(50,color='#b91c1c',linestyle='--',label='Velocidade PAL: 50 atualizações/s')
    ax.set_xticks(indices,[str(r['scale'])+'×' for r in rows]);ax.set_xlabel('Resolução interna')
    ax.set_ylabel('Atualizações simuladas por segundo (sem limite)')
    ax.set_title('The Urbz — mesmo trecho em dois jogadores\nRenderização sequencial, Linux/Vulkan, RTX 4070 SUPER')
    ax.set_ylim(0,110);ax.grid(axis='y',alpha=.18);ax.legend(loc='upper right',fontsize=9)
    fig.text(.5,.013,'Cada imagem nova usa duas atualizações no modo PAL original. Os números não são FPS de imagens distintas.',ha='center',va='bottom',fontsize=9)
    fig.savefig(OUT/'desempenho-comparado.png',dpi=145);plt.close(fig)
    print(OUT/'desempenho-comparado.png')


if __name__=='__main__':main()
