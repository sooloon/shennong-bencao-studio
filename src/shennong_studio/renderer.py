"""Shared renderer for the approved botanical editorial series (720×1280 layout grid)."""
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
import json, math, subprocess, shutil
import numpy as np

W,H=720,1280
FONT_SIZES=[28,30,32,34,36,38,40,42,44,46,48,52,56,60,64,70,78,80,90,110,150]

def project_path(root, value):
    p=(root/value).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError(f'Path escapes project: {value}')
    return p

def font_paths(root, style, profile='auto'):
    profiles=style['font_profiles']
    if profile=='auto':
        profile='macos-reference' if all(Path(x).is_file() for x in profiles['macos-reference'].values()) else 'portable'
    if profile not in profiles:raise ValueError(f'Unknown font profile: {profile}')
    import os
    chosen={}
    for key,value in profiles[profile].items():
        override=os.environ.get('SHENNONG_FONT_'+key.upper())
        cache=root/'build/font-cache'/('serif.otf' if key=='serif' else 'sans.otf')
        p=Path(override) if override else cache if profile=='portable' and cache.exists() else Path(value) if profile=='macos-reference' else project_path(root,value)
        if not p.is_file():raise FileNotFoundError(f'Missing font {p}. See docs/fonts.md.')
        chosen[key]=p
    return profile,chosen

def configure(manifest_path, root=None, font_profile='auto'):
    global CFG,ROOT,STYLE,FPS,DUR,C,cuts,assets,cover,F,B,R,K,map_fit,SELECTED_FONTS
    ROOT=Path(root or Path(__file__).resolve().parents[2]).resolve()
    CFG=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    STYLE=json.loads((ROOT/'brand.json').read_text(encoding='utf-8'));FPS=STYLE['fps']
    R=tuple(STYLE['accent']);K=tuple(STYLE['ink'])
    C=[(x['title'],x['text'],x['asset'],x['layout']) for x in CFG['scenes']]
    cuts=CFG.get('locked_cuts') or list(np.r_[0,np.cumsum([x['hold'] for x in CFG['scenes']])])
    cuts=np.array(cuts,float);DUR=float(cuts[-1])
    profile,fp=font_paths(ROOT,STYLE,font_profile);SELECTED_FONTS={'profile':profile,**{k:str(v) for k,v in fp.items()}}
    F={n:ImageFont.truetype(str(fp['serif']),n) for n in FONT_SIZES};B={n:ImageFont.truetype(str(fp['sans']),n) for n in FONT_SIZES}
    assets={};raw={}
    for name,spec in CFG['assets'].items():
        path=project_path(ROOT,spec['path'])
        if path not in raw:
            im=Image.open(path).convert('RGBA');white=Image.new('RGBA',im.size,'white');white.alpha_composite(im);raw[path]=white.convert('RGB')
        assets[name]=raw[path].crop(spec['crop']) if spec.get('crop') else raw[path].copy()
    cover=Image.open(project_path(ROOT,CFG['cover'])).convert('RGB').resize((W,H),Image.Resampling.LANCZOS)
    if CFG.get('map'):
        src=project_path(ROOT,CFG['map'])
        with Image.open(src) as source_image:size=source_image.size
        buf=subprocess.run(['ffmpeg','-v','error','-i',str(src),'-vf',r'hue=s=0,format=rgb24,lutrgb=r=255*pow(val/255\,3):g=255*pow(val/255\,3):b=255*pow(val/255\,3)','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True).stdout
        image=Image.frombytes('RGB',size,buf);image.thumbnail((660,468),Image.Resampling.LANCZOS)
        map_fit=Image.new('RGB',(660,468),'white');map_fit.paste(image,((660-image.width)//2,(468-image.height)//2))
    fit.cache_clear()
    return CFG


def build_score(output):
    """Recreate the same approved musical phrase edit, extending by crossfades if needed."""
    music=CFG['music'];edit=music['edit'];first=edit['first'];second=edit['second'];cross=edit['crossfade']
    total=first[1]-first[0];n=1
    while total<DUR+.05:total+=second[1]-second[0]-cross;n+=1
    split='[0:a]asplit='+str(n)+''.join(f'[a{i}]' for i in range(n))
    filters=[split]
    for i in range(n):
        aa,bb=first if i==0 else second
        filters.append(f'[a{i}]atrim={aa}:{bb},asetpts=PTS-STARTPTS[b{i}]')
    last='b0'
    for i in range(1,n):
        filters.append(f'[{last}][b{i}]acrossfade=d={cross}:c1=tri:c2=tri[m{i}]');last=f'm{i}'
    filters.append(f'[{last}]atrim=0:{DUR}[mix]')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(project_path(ROOT,music['path'])),'-filter_complex',';'.join(filters),'-map','[mix]',str(output)],check=True)


def legacy_frame(t):
    i=min(max(0,int(np.searchsorted(cuts,t,side='right')-1)),len(C)-1)
    a,b=cuts[i:i+2];u=t-a;p=u/(b-a);q=ease(u/.55);title,caption,name,mode=C[i];info=CFG['scenes'][i]['data']
    if mode=='cover':return cover.copy()
    im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im);sz=56 if len(title)<=12 else 48
    for k,l in enumerate(wrap(title,F[sz],600)):txt(d,(60,110+k*74+int((1-q)*18)),l,F[sz])
    if mode=='carousel':
        theta=-2*math.pi*ease(min(1,u/2.3))/3
        for k,(nm,lab) in enumerate(info['cards']):
            ang=theta+k*math.tau/3-math.pi/2;x=360+220*math.cos(ang);y=590+180*math.sin(ang)
            art(im,nm,(x-105,y-135,210,260),p,.02);d=ImageDraw.Draw(im);txt(d,(x,y+160),lab,F[40],R if k==int(min(2,u)) else K,'mm')
    elif mode=='counter':
        art(im,name,(370,385,300,360),p,.03);d=ImageDraw.Draw(im)
        value=info['value']*ease(min(1,u/1.25));txt(d,(60,490),info.get('prefix',''),B[60],R)
        txt(d,(60,610),f"{value:.{info.get('decimals',1)}f}{info.get('suffix','')}",B[110],R)
        d.line((65,755,650,755),fill=(150,150,150),width=2);d.line((65,755,65+585*ease(u/1.25),755),fill=R,width=7)
        txt(d,(65,830),info['note'],B[28])
    elif mode=='oldmodern':
        art(im,name,(420,400,260,370),p,.02);d=ImageDraw.Draw(im)
        txt(d,(60,360),info['old_label'],B[32]);txt(d,(60,450),info['old'],F[60]);d.line((60,550,370,550),fill=(150,150,150),width=2)
        txt(d,(60,645),info['new_label'],B[32]);txt(d,(60,735),info['new'],F[52],R);txt(d,(60,890),info['note'],F[34])
    elif mode=='measure':
        art(im,name,(70,270,580,430),p,.02);d=ImageDraw.Draw(im)
        for j,m in enumerate(info['measurements']):
            yy=785+j*110;reveal(im,(60,yy),m['label'],u,.2+j*.6,B[32],anchor='lm')
            reveal(im,(300,yy),m['value'],u,.4+j*.6,B[60],R,anchor='lm');reveal(im,(575,yy+8),m['unit'],u,.55+j*.6,B[32],anchor='lm')
    else:art(im,name,(55,285,610,590),p,.035)
    d=ImageDraw.Draw(im);ls=wrap(caption,F[40],600);yy=990 if len(ls)<3 else 950
    for j,l in enumerate(ls):txt(d,(60,yy+j*61),l,F[40])
    return im


def ease(q):q=max(0,min(1,q));return 1-(1-q)**3

def txt(d,p,s,f,col=None,anchor='lm'):d.text(p,s,font=f,fill=K if col is None else col,anchor=anchor)

def wrap(s,f,width):
 out=[];line=''
 for ch in s:
  if f.getlength(line+ch)>width and ch not in '。，；：！？、”’）':out.append(line);line=ch
  else:line+=ch
 if line:out.append(line)
 if len(out)>1 and len(out[-1])<4:
  n=4-len(out[-1]);out[-1]=out[-2][-n:]+out[-1];out[-2]=out[-2][:-n]
 return out

@lru_cache(maxsize=2048)
def fit(name,bw,bh,zoom):
 im=assets[name];r=min(bw/im.width,bh/im.height)*(1+zoom*.002)
 return im.resize((round(im.width*r),round(im.height*r)),Image.Resampling.LANCZOS)

def art(im,name,box,q,zoom=.03):
 x,y,bw,bh=box;layer=fit(name,int(bw),int(bh),round(zoom*q/.002));im.paste(layer,(round(x+(bw-layer.width)/2),round(y+(bh-layer.height)/2)))

def leader(d,p1,p2,q):
 d.line((*p1,p1[0]+(p2[0]-p1[0])*q,p1[1]+(p2[1]-p1[1])*q),fill=R,width=2)
 if q>.7:d.ellipse((p1[0]-5,p1[1]-5,p1[0]+5,p1[1]+5),fill=R)

def reveal(im,xy,label,u,delay=0,font=None,col=None,anchor='mm',halo=0):
 col=K if col is None else col
 q=ease((u-delay)/.32)
 if q<=0:return
 d=ImageDraw.Draw(im);c=tuple(round(255*(1-q)+v*q) for v in col)
 d.text((xy[0],xy[1]+round(8*(1-q))),label,font=font or B[34],fill=c,anchor=anchor,stroke_width=halo,stroke_fill='white')

def line_reveal(d,pts,u,delay=0,duration=.38,col=None,width=2,halo=False):
 col=R if col is None else col
 q=ease((u-delay)/duration)
 if q<=0:return
 lengths=[math.dist(a,b) for a,b in zip(pts,pts[1:])];left=sum(lengths)*q
 visible=[pts[0]]
 for a,b,le in zip(pts,pts[1:],lengths):
  if left>=le:visible.append(b);left-=le
  else:
   f=left/le if le else 0;visible.append((a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f));break
 if halo:d.line(visible,fill='white',width=width+4)
 d.line(visible,fill=col,width=width)

def poly_geometry(pts):
 lengths=[math.dist(a,b) for a,b in zip(pts,pts[1:])]
 return lengths,sum(lengths)

def point_at(pts,dist):
 lengths,total=poly_geometry(pts);dist=max(0,min(total,dist))
 for a,b,le in zip(pts,pts[1:],lengths):
  if dist<=le:
   f=dist/le if le else 0
   return (a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f)
  dist-=le
 return pts[-1]

def segment(pts,start,end):
 lengths,total=poly_geometry(pts);out=[point_at(pts,start)];walk=0
 for j,le in enumerate(lengths):
  walk+=le
  if start<walk<end:out.append(pts[j+1])
 out.append(point_at(pts,end));return out

def location_motion(im,xy,path,u,delay,phase=0):
 elapsed=u-delay
 if elapsed<=0:return
 d=ImageDraw.Draw(im);intro=ease(elapsed/.3);x,y=xy
 # A short expanding ring establishes the location. A lighter repeat keeps it alive.
 for pulse_start,strength in [(0,1.0),(2.8+phase*.12,.64),(5.0+phase*.12,.4)]:
  z=(elapsed-pulse_start)/.9
  if 0<=z<=1:
   rad=9+29*z;fade=(1-z)*strength
   col=tuple(round(255*(1-fade)+v*fade) for v in R)
   d.ellipse((x-rad,y-rad,x+rad,y+rad),outline=col,width=2)
 core=5.0*intro+.65*math.sin(elapsed*5.0)
 d.ellipse((x-core-3,y-core-3,x+core+3,y+core+3),fill='white')
 d.ellipse((x-core,y-core,x+core,y+core),fill=R)
 d.ellipse((x-1.5,y-1.5,x+1.5,y+1.5),fill='white')
 # Draw the route with a moving endpoint, then send a compact highlight along it.
 lengths,total=poly_geometry(path);progress=ease((elapsed-.13)/.68)
 if progress<=0:return
 route=segment(path,0,max(.1,total*progress))
 d.line(route,fill='white',width=7)
 d.line(route,fill=(226,135,132),width=4)
 d.line(route,fill=R,width=2)
 if progress<.995:
  head=total*progress
 else:
  head=((elapsed-.81)*.75+phase*.13)%1*total
 trail=segment(path,max(0,head-16),max(.1,head))
 d.line(trail,fill=(246,179,174),width=6)
 d.line(trail,fill=(255,244,240),width=2)
 hx,hy=point_at(path,head)
 d.ellipse((hx-3.2,hy-3.2,hx+3.2,hy+3.2),fill=R)
 d.ellipse((hx-1.2,hy-1.2,hx+1.2,hy+1.2),fill='white')

def direct_map(im,u,info,cult=False):
 im.paste(map_fit,(30,250));d=ImageDraw.Draw(im)
 if not cult:
  items=[(x['label'],x['label_position'],x['path']) for x in info['locations']]
  for j,(lab,label_xy,path) in enumerate(items):
   delay=.2+j*.56
   location_motion(im,path[0],path,u,delay,j)
  # Labels stay above every ring and moving highlight, protecting readability.
  for j,(lab,label_xy,path) in enumerate(items):
   delay=.2+j*.56
   reveal(im,label_xy,lab,u,delay+.63,B[40],R,halo=3)
  reveal(im,(60,850),info['summary'],u,.1,F[52],anchor='lm')
  reveal(im,(60,917),info['scope'],u,.35,B[32],anchor='lm')
 else:
  path=info['path']
  location_motion(im,path[0],path,u,.2,0)
  reveal(im,info['label_position'],info['label'],u,.9,B[38],R,halo=3)
  reveal(im,(60,811),info['year'],u,.2,B[32],anchor='lm')
  reveal(im,(60,895),info['quantity_label'],u,.4,B[34],anchor='lm')
  value=round(info['value']*ease((u-.9)/1.45));d=ImageDraw.Draw(im)
  txt(d,(307,885),str(value),B[110],R);txt(d,(535,909),info['unit'],B[44])

def frame(t):
 i=min(int(np.searchsorted(cuts,t,side='right')-1),len(C)-1)
 a,b=cuts[i:i+2];u=t-a;p=u/(b-a);q=ease(u/.5);title,caption,name,mode=C[i];info=CFG["scenes"][i]["data"]
 custom={'parts','wordpop','leafcount','bookindex','bookquote','oldterm','mapplaces','mapcultivation','toslice','plainpop','origins','namecompare','steps','twoPowders','grid','boundary','compound','pack','recap'}
 if mode not in custom:return legacy_frame(t)
 im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im)
 sz=56 if len(title)<=12 else 48
 for k,l in enumerate(wrap(title,F[sz],600)):txt(d,(60,110+k*74+int((1-q)*18)),l,F[sz])
 if mode in ['mapplaces','mapcultivation']:
  direct_map(im,u,info,mode=='mapcultivation')
 elif mode=='parts':
  art(im,name,(55,285,610,590),p,.035);d=ImageDraw.Draw(im)
  leader(d,(420,470),(587,470),ease(u/.4));leader(d,(395,755),(587,755),ease((u-.4)/.4))
  reveal(im,(580,420),info['labels'][0],u,.22,B[36]);reveal(im,(570,811),info['labels'][1],u,.64,B[36],R)
 elif mode=='wordpop':
  art(im,name,(290,285,375,570),p,.025)
  reveal(im,(80,430),info['words'][0],u,.1,F[78],anchor='lm');reveal(im,(80,511),info['words'][1],u,.35,B[32],anchor='lm')
  reveal(im,(80,655),info['words'][2],u,.9,F[78],R,anchor='lm');reveal(im,(80,738),info['words'][3],u,1.1,B[32],anchor='lm')
 elif mode=='leafcount':
  art(im,name,(60,280,600,555),p,.02)
  for j,xy in enumerate(info['points']):reveal(im,xy,str(j+1),u,.25+j*.35,B[44],R,halo=3)
  reveal(im,(60,898),info['summary'],u,1.15,F[44],anchor='lm')
 elif mode=='bookindex':
  art(im,name,(390,350,285,420),p,.02);d=ImageDraw.Draw(im)
  txt(d,(60,320),info['volume'],F[40]);txt(d,(60,391),info['category'],B[40])
  for j,(idx,lab) in enumerate(info['entries']):
   yy=510+j*135;delay=.2+j*.85
   reveal(im,(65,yy),idx,u,delay,B[40],R if j==info['active'] else K,anchor='lm')
   reveal(im,(150,yy),lab,u,delay+.15,B[44],R if j==info['active'] else K,anchor='lm')
   if j==info['active']:line_reveal(ImageDraw.Draw(im),[(65,yy+42),(322,yy+42)],u,delay+.4)
 elif mode=='bookquote':
  art(im,name,(385,410,300,430),p,.02);d=ImageDraw.Draw(im)
  txt(d,(60,345),info['book'],F[40]);txt(d,(60,430),info['entry'],F[40]);txt(d,(60,565),info['quote'],F[52])
  reveal(im,(60,733),info['alias_prefix'],u,.55,B[28],anchor='lm')
  reveal(im,(60,808),info['alias'],u,.75,F[52],R,anchor='lm')
  txt(d,(60,900),info['source_note'],B[28])
 elif mode=='oldterm':
  art(im,name,(415,340,260,330),p,.02);d=ImageDraw.Draw(im)
  txt(d,(60,420),info['left'],F[78]);reveal(im,(230,580),'≠',u,.4,B[80],R)
  reveal(im,(60,740),info['right'],u,.6,F[52],anchor='lm')
 elif mode=='toslice':
  art(im,info['from_asset'],(55,285,610,590),p);other=Image.new('RGB',(W,H),'white');art(other,info['to_asset'],(55,285,610,590),p)
  im.paste(Image.blend(im.crop((0,280,W,900)),other.crop((0,280,W,900)),ease((p-.2)/.5)),(0,280))
  reveal(im,(540,875),info['label'],u,.2,F[52],R)
 elif mode=='plainpop':
  art(im,name,(165,300,420,445),p)
  words=info['lines']
  reveal(im,(60,803),words[0],u,.3,B[34],anchor='lm')
  reveal(im,(60,881),words[1],u,.7,F[44],R,anchor='lm')
 elif mode=='origins':
  art(im,name,(195,280,330,450),p,.025)
  for j,(x,nm,src) in enumerate(info['columns']):
   reveal(im,(x,804),nm,u,.2+j*.3,F[48]);reveal(im,(x,890),src,u,.45+j*.3,B[34],R)
   line_reveal(ImageDraw.Draw(im),[(x,837),(x,855)],u,.35+j*.3,width=2,col=K)
 elif mode in ['namecompare','twoPowders']:
  art(im,info['left_asset'],(30,330,300,450),p,.02)
  art(im,info['right_asset'],(390,380,300,360),p,.02);d=ImageDraw.Draw(im)
  txt(d,(360,580),'≠',B[60],R,'mm')
  words=info['columns']
  for j,(nm,sub) in enumerate(words):
   reveal(im,(180+j*360,825),nm,u,.2+j*.25,F[48],R if j else K)
   reveal(im,(180+j*360,902),sub,u,.4+j*.25,B[32])
 elif mode=='steps':
  art(im,name,(260,350,415,440),p)
  for j,lab in enumerate(info['steps']):
   active=min(3,int(max(0,u-.25)/1.05));yy=342+j*151
   reveal(im,(65,yy),f'{j+1:02d}',u,j*.7,B[32],R if j==active else K,anchor='lm')
   reveal(im,(118,yy+55),lab,u,j*.7+.15,F[44],R if j==active else K,anchor='lm')
   if j<3:line_reveal(ImageDraw.Draw(im),[(78,yy+79),(78,yy+112)],u,j*.7+.3,col=(165,165,165),width=2)
 elif mode=='grid':
  x0,y0,cell,gap=70,315,27,5
  count=min(100,round(100*ease(u/1.2)))
  for k in range(count):
   x=x0+(k%10)*(cell+gap);y=y0+(k//10)*(cell+gap)
   d.rectangle((x,y,x+cell,y+cell),outline=(160,160,160),width=1)
  v=info['quantity']*ease((u-1.35)/1.55)
  for k in range(math.ceil(info['quantity'])):
   fraction=max(0,min(1,v-k))
   if fraction:d.rectangle((x0+k*(cell+gap),y0,x0+k*(cell+gap)+round(cell*fraction),y0+cell),fill=R)
  txt(d,(440,425),f"{count}{info['unit']}",B[60]);reveal(im,(495,520),'↓',u,1.15,B[60]);
  if u>1.35:txt(d,(430,620),f"{info['prefix']}{v:.1f}{info['unit']}",B[60],R)
  txt(d,(70,765),info['note'],B[28]);reveal(im,(70,840),info['part_note'],u,2.3,B[28],R,anchor='lm')
 elif mode=='boundary':
  art(im,name,(65,300,590,430),p)
  reveal(im,(60,841),info['left'],u,.2,F[44],anchor='lm')
  reveal(im,(359,841),'≠',u,.5,B[60],R)
  reveal(im,(420,841),info['right'],u,.7,F[44],anchor='lm')
 elif mode=='compound':
  art(im,name,(130,295,470,420),p)
  for j,(nm,sub) in enumerate(info['columns']):
   x=125+j*235
   reveal(im,(x,818),nm,u,.2+j*.35,F[44],R if j==0 else K)
   reveal(im,(x,895),sub,u,.4+j*.35,B[28])
 elif mode=='pack':
  art(im,name,(95,275,530,435),p)
  for j,(nm,x) in enumerate(info['fields']):
   reveal(im,(x,804),f'{j+1:02d}',u,.15+j*.65,B[28],R)
   reveal(im,(x,875),nm,u,.3+j*.65,B[36])
   if j==info['active']:line_reveal(ImageDraw.Draw(im),[(x-58,917),(x+58,917)],u,1.1,width=3)
 elif mode=='recap':
  art(im,name,(165,260,390,520),p)
  for j,lab in enumerate(info['steps']):
   x=125+j*235;reveal(im,(x,867),lab,u,.2+j*.35,F[40],R if j==info['active'] else K)
   if j<2:reveal(im,(x+118,867),'→',u,.4+j*.35,B[32])
 d=ImageDraw.Draw(im);ls=wrap(caption,F[40],600);yy=990 if len(ls)<3 else 950
 for j,l in enumerate(ls):txt(d,(60,yy+j*61),l,F[40])
 return im
