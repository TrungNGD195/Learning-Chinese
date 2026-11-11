"""Normalize native-alpha image_gen sprite atlases; no artwork or alpha synthesis."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1] / 'public/academy/great-wall'
GEN = json.loads((ROOT / 'bo-journey-generation-v1.json').read_text(encoding='utf-8'))
RECORDS = {r['key']: r for r in GEN['records']}
CELL = (256, 320)
ANCHOR = (128, 312)
VALIDATE = ROOT.parents[3] / '.impeccable/proposals/third-person-bo/asset-validation'
VALIDATE.mkdir(parents=True, exist_ok=True)

def bounds(alpha, threshold):
    b = alpha.point(lambda a: 255 if a >= threshold else 0).getbbox()
    return None if b is None else {'x':b[0], 'y':b[1], 'width':b[2]-b[0], 'height':b[3]-b[1]}

def metadata(prompt):
    escaped = prompt.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    return ('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/" dc:description="'+escaped.replace('"','&quot;')+'"/></rdf:RDF></x:xmpmeta>').encode()

def atlas(key, filename, cols, rows, scale, anchors, xedges=None):
    rec = RECORDS[key]
    src = Image.open(rec['original']).convert('RGBA')
    output = Image.new('RGBA', (256*cols,320*rows), (0,0,0,0))
    frames, cells = [], []
    for i in range(cols*rows):
        col, row = i%cols, i//cols
        x0 = xedges[col] if xedges else round(col*src.width/cols)
        x1 = xedges[col+1] if xedges else round((col+1)*src.width/cols)
        y0,y1=round(row*src.height/rows),round((row+1)*src.height/rows)
        cell=src.crop((x0,y0,x1,y1))
        a=cell.getchannel('A')
        foot_region=a.crop((round(cell.width*.33),round(cell.height*.66),cell.width,cell.height))
        ground_box=foot_region.point(lambda v:255 if v>=128 else 0).getbbox()
        baseline=round(cell.height*.66)+ground_box[3]-1
        anchor=anchors[i] if isinstance(anchors,list) else anchors
        # One fixed scale per atlas. Only translation normalizes ground/root anchors.
        resized=cell.resize((round(cell.width*scale),round(cell.height*scale)),Image.Resampling.LANCZOS)
        tx=round(128-anchor*scale)
        ty=round(312-baseline*scale)
        target=Image.new('RGBA', CELL,(0,0,0,0))
        target.alpha_composite(resized,(tx,ty))
        output.alpha_composite(target,(col*256,row*320))
        body=bounds(target.getchannel('A'),16)
        opaque=bounds(target.getchannel('A'),128)
        frames.append({'index':i,'column':col,'row':row,'sourceBox':[x0,y0,x1,y1],'sourceFootAnchor':[anchor,baseline],
            'scale':scale,'translation':[tx,ty],'footAnchor':[128,312],'bodyBounds':body,'opaqueBounds':opaque,'opaqueHeight':opaque['height'],
            'nonzeroBounds':bounds(target.getchannel('A'),1)})
        cells.append(target)
    output.save(ROOT/filename,'WEBP',lossless=True,method=6,xmp=metadata(rec['prompt']))
    # RGB composites are validation only. Native alpha remains untouched in the shipped file.
    for label,color in [('light',(255,247,230,255)),('dark',(30,48,55,255))]:
        Image.alpha_composite(Image.new('RGBA',output.size,color),output).convert('RGB').save(VALIDATE/(filename+'.'+label+'.jpg'),quality=95)
    differences=[]
    for i in range(len(cells)):
        diff=ImageChops.difference(cells[i],cells[(i+1)%len(cells)])
        differences.append(round(sum(ImageStat.Stat(diff).mean),4))
    alpha=output.getchannel('A')
    return {'path':'/academy/great-wall/'+filename,'width':output.width,'height':output.height,'columns':cols,'rows':rows,'cellWidth':256,'cellHeight':320,
        'footAnchor':[128,312],'sharedScale':scale,'opaqueHeight':max(f['opaqueHeight'] for f in frames),'opaqueHeightRange':[min(f['opaqueHeight'] for f in frames),max(f['opaqueHeight'] for f in frames)],
        'frames':frames,'alphaExtrema':list(alpha.getextrema()),'fullyTransparentPixels':alpha.histogram()[0],
        'consecutiveFrameDifferenceRGBA':differences,'sourceOriginal':rec['original'],'sha256':hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()}

assets={}
assets['away']=atlas('away','bo-walk-away-v1.webp',4,2,.53,234)
assets['toward']=atlas('toward_retry','bo-walk-toward-v1.webp',4,2,.50,224)
assets['poses']=atlas('poses','bo-journey-poses-v1.webp',4,1,.36,[345,328,330,326],xedges=[0,530,1060,1615,2172])
cloud=Image.open(RECORDS['cloud']['original']).convert('RGBA')
cloud.save(ROOT/'journey-cloud-v1.webp','WEBP',lossless=True,method=6,xmp=metadata(RECORDS['cloud']['prompt']))
assets['cloud']={'path':'/academy/great-wall/journey-cloud-v1.webp','width':cloud.width,'height':cloud.height,
    'sourceOriginal':RECORDS['cloud']['original'],'alphaExtrema':list(cloud.getchannel('A').getextrema()),'fullyTransparentPixels':cloud.getchannel('A').histogram()[0],
    'partialAlphaPixels':sum(cloud.getchannel('A').histogram()[1:255]),'bodyBounds':bounds(cloud.getchannel('A'),16)}
metrics={'version':1,'generator':'built-in image_gen.imagegen','normalizationScript':'frontend/scripts/normalize-bo-journey-v1.py','coordinateSystem':'local cell pixels; origin top-left; row-major frame order',
    'boundsDefinition':{'bodyBounds':'tight bounds at native/resampled alpha >= 16; includes full dragon, horns, whiskers, satchel and tail','opaqueBounds':'tight bounds at alpha >= 128','opaqueHeight':'opaqueBounds.height; actual visible dragon height for runtime sizing','footAnchor':'fixed root/ground anchor for each cell. Footfalls articulate around this anchor.'},
    'normalization':'Split/crop source layouts; one shared isotropic scale per atlas; per-cell translation to fixed root and ground anchor; Pillow LANCZOS resampling; native alpha retained; no chroma-keying, painting, synthesized frames, or per-frame independent scale.',
    'scaleNote':'Full broad curled tail and centered foot root constrain actual dragon height to about 210–220px within 256px cell width; runtime should scale cell by target visible body height / opaqueHeight.',
    'assets':assets}
(ROOT/'bo-journey-metrics-v1.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
print(json.dumps({k:{'path':v['path'],'opaqueHeight':v.get('opaqueHeight'),'size':[v['width'],v['height']]} for k,v in assets.items()},indent=2))
