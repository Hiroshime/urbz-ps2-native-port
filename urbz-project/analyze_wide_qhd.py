#!/usr/bin/env python3
"""Measure a scene-specific 3D hair landmark and export the real aspect comparison.

Uses the two magenta-haired avatars in the local first-district fixture. This is
not a general detector or evidence that every HUD element has a corrected layout.
"""
import json
import os
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'games/urbz-pal/validation/wide-qhd'
os.environ.setdefault('MPLCONFIGDIR',str(OUT/'matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def hair_boxes(image,aspect):
    image=image.convert('RGB');w,h=image.size
    boxes=[]
    for low,high in [(0,w//2),(w//2,w)]:
        points=[]
        for y in range(h*3//4):
            for x in range(low,high):
                r,g,b=image.getpixel((x,y))
                if r>75 and b>70 and r>g*1.8 and b>g*1.8:points.append((x,y))
        if len(points)<100:raise RuntimeError('Fixture landmark absent; inspect captures instead of trusting this measurement.')
        xs,ys=zip(*points);box=[min(xs),min(ys),max(xs),max(ys)]
        # Display both scenes at equal height. Each split-screen remains half of
        # the full scene's width, so source x scale uses the full output aspect.
        display_width=(box[2]-box[0]+1)*h*aspect/w
        display_height=box[3]-box[1]+1
        boxes.append({'source_bbox':box,'detected_pixels':len(points),'display_width_at_native_height':round(display_width,3),
                      'display_height':display_height,'display_width_height_ratio':round(display_width/display_height,4)})
    return boxes



def hud_text_boxes(image, aspect, wide):
    """Measure the two clock strings in this exact fixture, excluding the world."""
    image = image.convert('RGB')
    boxes = []
    for x0,y0,x1,y1 in [(180,378,248,396),(500,378,570,396)]:
        if wide:
            x0,x1 = int(x0*.75+80), int(x1*.75+80)
        points = []
        for y in range(y0,y1):
            for x in range(x0,x1):
                rgb = image.getpixel((x,y))
                if min(rgb)>175 and max(rgb)-min(rgb)<60:
                    points.append((x,y))
        if len(points)<100:
            raise RuntimeError('HUD clock landmark absent; inspect the fixture.')
        xs,ys = zip(*points)
        box = [min(xs),min(ys),max(xs),max(ys)]
        ratio = (box[2]-box[0]+1)*image.height*aspect/image.width/(box[3]-box[1]+1)
        boxes.append({'source_bbox':box, 'detected_pixels':len(points),
                      'display_width_height_ratio':round(ratio,4)})
    return boxes

def main():
    source=json.loads((OUT/'report.json').read_text())
    images=[Image.open(ROOT/case['capture']) for case in source['cases']]
    aspects=[4/3,16/9]
    landmarks=[hair_boxes(im,aspect) for im,aspect in zip(images,aspects)]
    ratios=[]
    for a,b in zip(*landmarks):
        ratios.append(b['display_width_height_ratio']/a['display_width_height_ratio'])
    hud=[hud_text_boxes(im,aspect,wide) for im,aspect,wide in zip(images,aspects,[False,True])]
    hud_ratios=[b['display_width_height_ratio']/a['display_width_height_ratio'] for a,b in zip(*hud)]
    valid=all(.85<=r<=1.15 for r in ratios) and all(.95<=r<=1.05 for r in hud_ratios)
    report={'geometry_landmark_ratios_wide_over_original':ratios,'within_15_percent_of_original_shape':valid,
            'landmarks':landmarks,'hud_clock_ratios_wide_over_original':hud_ratios,'hud_clock_landmarks':hud,'scope':'Scene-specific magenta hair and two HUD clock strings, displayed at equal height. Does not certify other cameras, UI screens or full campaign.'}
    (OUT/'geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(16,7),gridspec_kw={'width_ratios':aspects},layout='constrained')
    for ax,image,aspect,title in zip(axes,images,aspects,['Original 4:3','Widescreen 16:9 — projeção corrigida']):
        ax.imshow(image,aspect='auto',interpolation='nearest');ax.set_box_aspect(1/aspect);ax.axis('off');ax.set_title(title)
    fig.suptitle('Mesmo snapshot e frame 18080 — capturas internas com a proporção de exibição aplicada\nTexturas e elementos de interface originais',fontsize=14)
    fig.savefig(OUT/'comparacao-aspecto.png',dpi=120);plt.close(fig)
    print(json.dumps(report,indent=2))
    return 0 if valid else 1


if __name__=='__main__':raise SystemExit(main())
