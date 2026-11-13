"""Model-independent CLI. No cloud API or account is needed to re-render supplied assets."""
import argparse,json,subprocess,sys,shutil,math,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from fontTools.ttLib import TTFont
from . import renderer as r
ROOT=Path(__file__).resolve().parents[2]
LAYOUTS={'cover','parts','cloth','wordpop','leafcount','bookindex','bookquote','oldterm','oldmodern','mapplaces','mapcultivation','toslice','zoom','plainpop','carousel','origins','namecompare','steps','twoPowders','counter','grid','boundary','compound','pack','recap','end','art_text','measure'}

def load_manifest(path):
    p=Path(path);p=p if p.is_absolute() else ROOT/p
    return p,json.loads(p.read_text(encoding='utf-8'))

def validate(path, ready=True):
    p,cfg=load_manifest(path)
    if ready and cfg.get('status')!='ready':raise ValueError('Episode is draft: verify facts, assets and sources, then set status=ready.')
    scenes=cfg.get('scenes',[])
    if not scenes or scenes[0]['layout']!='cover':raise ValueError('The first frame must use the episode cover.')
    ids=[s['id'] for s in scenes]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate scene IDs.')
    src={s['id'] for s in cfg.get('sources',[])}
    for s in scenes:
        if s['layout'] not in LAYOUTS:raise ValueError('Unknown layout: '+s['layout'])
        if s['hold']<=0:raise ValueError('Scene hold must be positive.')
        if not set(s.get('source_ids',[]))<=src:raise ValueError('Unknown source ID in '+s['id'])
        if s['asset'] not in cfg['assets']:raise ValueError('Unknown asset in '+s['id'])
        if s['layout']=='grid' and not (0<=s['data']['quantity']<=100):raise ValueError('The grid layout represents 100 cells; quantity must be within 0–100.')
    cuts=cfg.get('locked_cuts')
    if cuts and (len(cuts)!=len(scenes)+1 or cuts[0]!=0 or any(b<=a for a,b in zip(cuts,cuts[1:]))):raise ValueError('Invalid locked timing. Clear locked_cuts after changing scene holds.')
    paths=[cfg['cover']]+[v['path'] for v in cfg['assets'].values()]
    if cfg.get('map'):paths.append(cfg['map'])
    if cfg.get('music'):paths.append(cfg['music']['path'])
    for value in set(paths):
        if not r.project_path(ROOT,value).is_file():raise FileNotFoundError(value)
    return p,cfg

def collect_text(value):
    if isinstance(value,str):return value
    if isinstance(value,dict):return ''.join(collect_text(v) for v in value.values())
    if isinstance(value,list):return ''.join(map(collect_text,value))
    return ''

def doctor(path,profile='auto',hashes=False):
    p,cfg=validate(path)
    for tool in ['ffmpeg','ffprobe']:
        if not shutil.which(tool):raise RuntimeError('Missing '+tool+'; see README setup.')
    style=json.loads((ROOT/'brand.json').read_text());selected,fonts=r.font_paths(ROOT,style,profile)
    chars={ord(c) for c in collect_text(cfg['scenes']) if ord(c)>127}
    if selected=='portable':
        missing={}
        for key,font in fonts.items():
            cmap=TTFont(font,fontNumber=0).getBestCmap();miss=chars-set(cmap)
            if miss:missing[key]=''.join(chr(x) for x in sorted(miss))
        if missing:raise ValueError('Missing portable font glyphs '+json.dumps(missing,ensure_ascii=False)+'. Run python scripts/fetch_fonts.py --full or set SHENNONG_FONT_SERIF/SANS.')
    if hashes:
        registry=json.loads((ROOT/'provenance/assets.json').read_text())
        for x in registry['files']:
            b=r.project_path(ROOT,x['path']).read_bytes()
            if hashlib.sha256(b).hexdigest()!=x['sha256']:raise ValueError('Asset hash mismatch: '+x['path'])
    info={'episode':cfg['id'],'scenes':len(cfg['scenes']),'seconds':cfg.get('locked_cuts',[])[-1] if cfg.get('locked_cuts') else sum(s['hold'] for s in cfg['scenes']),'font_profile':selected,'fonts':{k:str(v) for k,v in fonts.items()},'status':'ok'}
    print(json.dumps(info,ensure_ascii=False,indent=2));return info

def init_render(path,profile):
    p,cfg=validate(path);r.configure(p,ROOT,profile);return cfg

def storyboard(path,out,profile):
    cfg=init_render(path,profile);out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    cols=4;thumb_w,thumb_h=270,480;rows=math.ceil(len(r.C)/cols)
    sheet=Image.new('RGB',(cols*thumb_w,rows*(thumb_h+25)),'white');d=ImageDraw.Draw(sheet)
    for i in range(len(r.C)):
        t=(r.cuts[i]+r.cuts[i+1])/2;x=i%cols*thumb_w;y=i//cols*(thumb_h+25)
        sheet.paste(r.frame(t).resize((thumb_w,thumb_h)),(x,y));d.text((x+5,y+thumb_h+4),f'{i+1:02d} {r.cuts[i]:.1f}s',fill='black')
    sheet.save(out);print(out)

def render(path,out,profile,start=0,end=None):
    cfg=init_render(path,profile);end=r.DUR if end is None else end
    if start<0 or end<=start or end>r.DUR+.001:raise ValueError('Render range must be inside the episode timeline.')
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);build=ROOT/'build'/cfg['id'];build.mkdir(parents=True,exist_ok=True)
    score=build/'score.wav';r.build_score(score)
    visual=build/'visual.mp4';first=round(start*r.FPS);last=round(end*r.FPS);duration=(last-first)/r.FPS
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','720x1280','-r',str(r.FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',str(visual)],stdin=subprocess.PIPE)
    try:
        for n in range(first,last):
            proc.stdin.write(r.frame(n/r.FPS).tobytes())
            if (n-first)%(r.FPS*15)==0:print(f'rendering {(n-first)/r.FPS:.1f}/{duration:.1f}s',flush=True)
    finally:proc.stdin.close()
    if proc.wait()!=0:raise RuntimeError('ffmpeg video encoding failed')
    edit=cfg['music']['edit'];fade=min(edit.get('fade_out',3),duration)
    af=f'[1:a]atrim=start={first/r.FPS}:duration={duration},asetpts=PTS-STARTPTS,volume={edit.get("volume",.7)},afade=t=out:st={duration-fade}:d={fade}[a]'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(visual),'-i',str(score),'-filter_complex',af,'-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(out)],check=True)
    (build/'timeline.json').write_text(json.dumps([{'id':s['id'],'start':round(float(r.cuts[i]),4),'end':round(float(r.cuts[i+1]),4),'title':s['title']} for i,s in enumerate(cfg['scenes'])],ensure_ascii=False,indent=2))
    print(json.dumps({'video':str(out),'duration':duration,'fonts':r.SELECTED_FONTS},ensure_ascii=False))

def new_episode(name,slug):
    if not slug or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in slug):raise ValueError('Use an ASCII lowercase episode slug.')
    target=ROOT/'episodes'/slug
    if target.exists():raise FileExistsError(target)
    template=json.loads((ROOT/'templates/episode.json').read_text())
    template=json.loads(json.dumps(template,ensure_ascii=False).replace('new-herb',slug))
    template.update(id=slug,title=name,status='draft')
    target.mkdir();(target/'assets').mkdir();(target/'references').mkdir()
    (target/'episode.json').write_text(json.dumps(template,ensure_ascii=False,indent=2));print(target)

def main(argv=None):
    p=argparse.ArgumentParser(description='神农本草经系列视频工作室');sub=p.add_subparsers(dest='command',required=True)
    for cmd in ['doctor','storyboard','frame','render']:
        a=sub.add_parser(cmd);a.add_argument('episode');a.add_argument('--font-profile',choices=['auto','portable','macos-reference'],default='auto')
        if cmd=='doctor':a.add_argument('--check-hashes',action='store_true')
        else:a.add_argument('--out',required=True)
        if cmd=='frame':a.add_argument('--time',type=float,required=True)
        if cmd=='render':a.add_argument('--start',type=float,default=0);a.add_argument('--end',type=float)
    a=sub.add_parser('new');a.add_argument('name');a.add_argument('--slug',required=True)
    a=p.parse_args(argv)
    try:
        if a.command=='doctor':doctor(a.episode,a.font_profile,a.check_hashes)
        elif a.command=='storyboard':storyboard(a.episode,a.out,a.font_profile)
        elif a.command=='frame':
            init_render(a.episode,a.font_profile)
            if not 0<=a.time<r.DUR:raise ValueError('Frame time outside the episode.')
            out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);r.frame(a.time).save(out);print(out)
        elif a.command=='render':render(a.episode,a.out,a.font_profile,a.start,a.end)
        else:new_episode(a.name,a.slug)
    except (ValueError,FileNotFoundError,RuntimeError) as e:p.exit(2,str(e)+'\n')

if __name__=='__main__':main()
