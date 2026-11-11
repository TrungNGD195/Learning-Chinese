"""Package generated artwork; only format conversion and atlas alignment.

No repainting, synthesized poses, chroma key or alpha removal is performed.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[2]
raw=root/'assets/plates'
source_master=raw/'continuous-climb-master-v2.png'
source_turn=raw/'bo-rear-turn-v2.png'
folder=root/'frontend/public/academy/great-wall/climb-motion-v2'
folder.mkdir(parents=True,exist_ok=True)
Image.open(source_master).save(folder/'master.webp',quality=94,method=6)
turn=Image.open(source_turn).convert('RGBA')
cells=[];records=[]
for i in range(8):
    x0=round(i%4*turn.width/4);x1=round((i%4+1)*turn.width/4)
    y0=round(i//4*turn.height/2);y1=round((i//4+1)*turn.height/2)
    cell=turn.crop((x0,y0,x1,y1));alpha=np.asarray(cell)[:,:,3]
    yy,xx=np.where(alpha>=128);bounds=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
    sole_y=int(yy.max());foot_y,foot_x=np.where((alpha>=128)&(np.indices(alpha.shape)[0]>=sole_y-4))
    root_x=float((foot_x.min()+foot_x.max())/2)
    cells.append(cell);records.append({'source_box':[x0,y0,x1,y1],'opaque_bounds':bounds,'source_foot':[root_x,float(sole_y)],'opaque_height':bounds[3]-bounds[1]})
shared_scale=min(212/max(r['opaque_height'] for r in records),230/max(r['opaque_bounds'][2]-r['opaque_bounds'][0] for r in records))
atlas=Image.new('RGBA',(1024,640))
for i,(cell,record) in enumerate(zip(cells,records)):
    scaled=cell.resize((round(cell.width*shared_scale),round(cell.height*shared_scale)),Image.Resampling.LANCZOS)
    dx=round(128-record['source_foot'][0]*shared_scale);dy=round(312-record['source_foot'][1]*shared_scale)
    frame=Image.new('RGBA',(256,320));frame.alpha_composite(scaled,(dx,dy));atlas.alpha_composite(frame,(i%4*256,i//4*320))
    record['translation']=[dx,dy];record['visible_height']=round(record['opaque_height']*shared_scale)
atlas.save(folder/'bo-turn.webp',lossless=True,method=6)
metadata={'generator':'built-in image_gen.imagegen','master_references':['assets/plates/painted-scene.png','assets/plates/painted-climb.png','assets/plates/painted-bend.png'],'turn_references':['frontend/public/academy/great-wall/bo-walk-away-v1.webp','frontend/public/academy/great-wall/bo-journey-poses-v1.webp'],'prompts':['assets/plates/continuous-climb-master-v2.prompt.txt','assets/plates/bo-rear-turn-v2.prompt.txt'],'master_source_sha256':hashlib.sha256(source_master.read_bytes()).hexdigest(),'turn_source_sha256':hashlib.sha256(source_turn.read_bytes()).hexdigest(),'master_size':Image.open(source_master).size,'turn_size':turn.size,'atlas_size':atlas.size,'shared_scale':shared_scale,'foot_anchor':[128,312],'records':records,'processing':'Opaque environment format conversion; native-alpha turn atlas cropped by equal cells, one shared isotropic scale and foot-root translation only.'}
(folder/'provenance.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
print(json.dumps({'master':metadata['master_size'],'atlas':metadata['atlas_size'],'scale':shared_scale,'visible_heights':[r['visible_height'] for r in records]},indent=2))
