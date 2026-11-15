#!/usr/bin/env python3
"""Export the measured renderer output and an offline interactive comparison."""
import html
import hashlib
import json
import os
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'games/urbz-pal/validation/graphics'
os.environ.setdefault('MPLCONFIGDIR',str(OUT/'matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    data=json.loads((OUT/'report.json').read_text())
    if not data['passed']:raise SystemExit('The benchmark did not complete; inspect report.json.')
    rows=[]
    capture_urls={}
    for item in data['results']:
        scale=item['scale']
        ppm=ROOT/item['trials'][0]['capture']
        image=Image.open(ppm)
        png=ppm.with_suffix('.png');image.save(png)  # Lossless re-encoding; no enhancement.
        capture_urls[str(scale)]=str(png.relative_to(OUT))
        rates=[t['refreshes_per_second'] for t in item['trials']]
        width,height=item['trials'][0]['internal_size']
        ratio=item['trials'][0]['new_pictures_total']/item['trials'][0]['refreshes_total']
        rows.append({'scale':scale,'size':f'{width}×{height}','rate':item['refreshes_per_second'],'mean_ms':item['mean_ms'],
                     'new_picture_rate':round(item['refreshes_per_second']*ratio,2),
                     'min_rate':min(rates),'max_rate':max(rates)})
    fig,axes=plt.subplots(2,2,figsize=(14,11),layout='constrained')
    for ax,row in zip(axes.flat,rows):
        img=Image.open(OUT/capture_urls[str(row['scale'])])
        ax.imshow(img,interpolation='nearest',aspect='auto');ax.set_box_aspect(3/4);ax.axis('off')
        ax.set_title(f"{row['scale']}× — {row['size']}",fontsize=13)
    fig.suptitle('The Urbz — mesmo frame 18080, texturas originais\nCapturas da resolução interna, antes dos filtros finais',fontsize=15)
    fig.savefig(OUT/'comparacao.png',dpi=130);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    bars=ax.bar([f"{r['scale']}×" for r in rows],[r['rate'] for r in rows],color=['#64748b','#0891b2','#0d9488','#7c3aed'])
    ax.axhline(50,color='#b91c1c',linestyle='--',label='Velocidade PAL: 50 atualizações/s')
    ax.bar_label(bars,labels=[f"{r['rate']:.1f}" for r in rows],padding=4)
    ax.set_ylim(0,max(58,max(r['rate'] for r in rows)*1.25))
    ax.set_ylabel('Atualizações simuladas por segundo');ax.set_xlabel('Resolução interna')
    ax.set_title('Primeira área, dois jogadores — Linux/Vulkan, RTX 4070 SUPER')
    ax.legend(loc='upper right');ax.grid(axis='y',alpha=.2)
    fig.savefig(OUT/'desempenho.png',dpi=150);plt.close(fig)
    met=[str(r['scale'])+'×' for r in rows if r['rate']>=50]
    speed_note=('Escalas com média de pelo menos 50 atualizações/s: '+', '.join(met)+'.') if met else 'Nenhuma escala atingiu a velocidade PAL no intervalo medido.'
    with (ROOT/'build/native-urbz-pal/ps2run').open('rb') as binary:current_sha=hashlib.file_digest(binary,'sha256').hexdigest()
    version_note='<p><strong>Medição de um executável anterior.</strong> O runtime foi otimizado depois deste registro. Consulte DESEMPENHO.md na documentação para os resultados atuais.</p>' if current_sha!=data['executable_sha256'] else ''
    table=''.join(f"<tr><td>{r['scale']}×</td><td>{r['size']}</td><td>{r['mean_ms']:.2f}</td><td>{r['rate']:.2f}</td><td>{r['min_rate']:.2f}–{r['max_rate']:.2f}</td><td>{r['new_picture_rate']:.2f}</td></tr>" for r in rows)
    options=''.join(f'<option value="{s}">{s}×</option>' for s in capture_urls)
    page='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Urbz — comparação gráfica</title><style>
body{margin:0;background:#101622;color:#e9eff8;font:16px system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:28px}h1{font-size:28px}p{line-height:1.65;color:#c1cede}a{color:#67e8f9}label{display:inline-flex;align-items:center;gap:12px;margin:12px 20px 12px 0}select,button{font:inherit;padding:8px;background:#253248;color:white;border:1px solid #526681;border-radius:6px}input[type=range]{width:100%}.viewer{position:relative;aspect-ratio:4/3;overflow:hidden;background:black;border:1px solid #526681}.viewer img{position:absolute;inset:0;width:100%;height:100%;object-fit:fill}.tag{position:absolute;top:10px;z-index:3;background:#101622dd;padding:5px 10px;border-radius:4px}.right{right:10px}#divider{position:absolute;top:0;bottom:0;left:50%;width:2px;background:#67e8f9;z-index:2}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.grid img{width:100%}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid #334155}.scroll{overflow:auto}.chart{max-width:850px;width:100%}@media(max-width:650px){main{padding:14px}.grid{grid-template-columns:repeat(2,1fr)}}
</style><main><h1>The Urbz: 1×, 2×, 3× e 4×</h1>
<p>Mesmo snapshot, mesmos comandos e mesmo frame 18080. As imagens são capturas reais do renderer, sem FSR, texturas HD ou aprimoramento posterior. A comparação aplica a proporção de exibição 4:3; os arquivos originais mantêm os pixels capturados.</p>
<label>Esquerda <select id="leftSelect">OPTIONS</select></label><label>Direita <select id="rightSelect">OPTIONS</select></label>
<div class="viewer"><img id="leftImg" alt="Comparação esquerda"><img id="rightImg" alt="Comparação direita"><span class="tag" id="leftTag"></span><span class="tag right" id="rightTag"></span><div id="divider"></div></div>
<label for="slider">Divisão entre as imagens</label><input id="slider" aria-label="Divisão" type="range" min="0" max="100" value="50">
<p>Arraste a divisão para comparar bordas, cabelo e construções. As texturas continuam sendo as originais. Abra as imagens abaixo para examinar a resolução completa.</p><div class="grid">LINKS</div>
<h2>Desempenho observado</h2>VERSIONNOTE<p>Uma janela de 960×720 por vez, simulação em um thread, limite de velocidade desligado. Duas execuções de 200 atualizações medidas por escala, após aquecimento. O custo de abrir o jogo e a captura de tela ficam fora do intervalo medido. GPU: GPUINFO.</p>
<div class="scroll"><table><thead><tr><th>Escala</th><th>Pixels capturados</th><th>ms/atualização</th><th>Atualizações/s</th><th>Faixa dos ensaios</th><th>Imagens novas/s estimadas</th></tr></thead><tbody>TABLE</tbody></table></div>
<p>50 atualizações/s correspondem à velocidade PAL. Neste trecho, o jogo produz uma imagem nova a cada duas atualizações. Essas taxas não representam geração de quadros. Os ensaios são curtos e sujeitos a variação; a ordem das escalas não garante uma classificação de desempenho em outras áreas. SPEEDNOTE O modo offline com compilação durante a execução pode apresentar resultados diferentes.</p>
<img class="chart" src="desempenho.png" alt="Gráfico do desempenho medido"><p>Os filtros finais de nitidez e suavização não aparecem nas capturas brutas, mas estavam ativos na apresentação durante o teste. Relatório: <a href="report.json">JSON completo</a>. A sincronização de rede é validada separadamente; ela exige resolução interna e filtro 2D compatíveis.</p>
<script>const files=FILES;const ls=document.getElementById('leftSelect'),rs=document.getElementById('rightSelect'),slider=document.getElementById('slider');const ids=['leftImg','rightImg','leftTag','rightTag','divider'];const [leftImg,rightImg,leftTag,rightTag,divider]=ids.map(id=>document.getElementById(id));const scales=Object.keys(files);ls.value=scales[0];rs.value=scales[scales.length-1];function update(){leftImg.src=files[ls.value];rightImg.src=files[rs.value];leftTag.textContent=ls.value+'×';rightTag.textContent=rs.value+'×';rightImg.style.clipPath='inset(0 0 0 '+slider.value+'%)';divider.style.left=slider.value+'%'}ls.onchange=rs.onchange=slider.oninput=update;update();</script></main></html>'''
    links=''.join(f'<a href="{url}" target="_blank"><img src="{url}" alt="{s}×">Abrir {s}×</a>' for s,url in capture_urls.items())
    page=page.replace('VERSIONNOTE',version_note).replace('SPEEDNOTE',speed_note).replace('OPTIONS',options).replace('LINKS',links).replace('GPUINFO',html.escape(data['gpu'])).replace('TABLE',table).replace('FILES',json.dumps(capture_urls))
    (OUT/'comparacao.html').write_text(page,encoding='utf-8')
    print(OUT/'comparacao.html')


if __name__=='__main__':main()
