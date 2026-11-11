"""Teste real isolado; preserva produção e mata apenas sua própria árvore de processo."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time,urllib.request,urllib.error,zipfile,io
ROOT=Path(r'C:/Users/Windows/edicao-ia/cortes-app')
WORK=Path(__file__).resolve().parent
DATA=WORK/'integracao-v2-data-jobobjects'
DATA.mkdir(exist_ok=True)
PORT=3783
BASE=f'http://127.0.0.1:{PORT}'
env=dict(os.environ,CORTES_DATA_DIR=str(DATA),CORTES_APP_PORT=str(PORT))
if not (DATA/'reference-cache').exists():
    shutil.copytree(ROOT/'data/reference-cache',DATA/'reference-cache')
def request(path,body=None):
    payload=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,data=payload,headers={'X-Cortes-Local':'1','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=20) as response:
        return json.load(response)
def launch():
    log=(WORK/'integracao-v2-servidor.log').open('ab')
    process=subprocess.Popen([sys.executable,'-X','utf8',str(ROOT/'app.py')],cwd=ROOT,env=env,stdout=log,stderr=log,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(80):
        try:
            if request('/api/health')['version']=='2.0.0':return process
        except (OSError,ValueError):pass
        if process.poll() is not None:raise RuntimeError('Servidor de teste terminou')
        time.sleep(.25)
    raise RuntimeError('Servidor não iniciou')
def stop(process):
    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    process.wait(timeout=20)
process=launch()
plan=request('/api/plan',{'topic':'encontre os videos mais viralizados do gta6 me entregue 100 cortes completos prontos'})
assert plan['topic']=='GTA 6' and plan['target_clips']==100
job=request('/api/jobs',{'topic':'GTA6','target_clips':2,'source_url':'https://youtu.be/E07OTlhncP0',
                         'avoid_duplicates':False,'max_clips':20})
identifier=job['id']
(WORK/'integracao-v2-job.json').write_text(json.dumps({'id':identifier,'port':PORT,'data':str(DATA)}),encoding='utf8')
print('Lote real de teste:',identifier,flush=True)
started=time.monotonic();first_hash=None;restarted=False;last=''
while time.monotonic()-started<1200:
    job=request('/api/jobs/'+identifier)
    label=f"{job['status']} {job['stage']} {len(job['clips'])}/2 — {job['message']}"
    if label!=last:print(label,flush=True);last=label
    if len(job['clips'])==1 and not restarted and job['status']=='processing':
        first_hash=hashlib.sha256(Path(job['clips'][0]['file']).read_bytes()).hexdigest()
        stop(process)
        process=launch()
        restarted=True
        print('Servidor interrompido e reiniciado após o primeiro corte; aguardando retomada automática.',flush=True)
    if job['status'] in {'ready','partial','error','cancelled'}:
        break
    time.sleep(1)
assert job['status']=='ready' and len(job['clips'])==2,job.get('message')
assert len({clip['id'] for clip in job['clips']})==2
assert restarted,'O teste precisa interromper um lote em execução'
assert first_hash in {hashlib.sha256(Path(clip['file']).read_bytes()).hexdigest() for clip in job['clips']}
for clip in job['clips']:
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',clip['file']],text=True,encoding='utf8'))
    video=next(item for item in data['streams'] if item['codec_type']=='video')
    assert (video['width'],video['height'])==(720,1280)
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',clip['file'],'-f','null','-'],check=True,capture_output=True)
    bundle=urllib.request.urlopen(BASE+'/api/bundle/'+identifier+'/'+clip['id'],timeout=30).read()
    assert zipfile.ZipFile(io.BytesIO(bundle)).testzip() is None
report={'job':identifier,'status':job['status'],'clips':len(job['clips']),'restart_recovery':restarted,
        'first_hash_preserved':True,'seconds':round(time.monotonic()-started,2),'data':str(DATA)}
(WORK/'integracao-v2-resultado.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PASS: dois MP4 reais decodificados; pacotes íntegros; retomada após reinício; primeiro vídeo preservado.',flush=True)
# Leave this isolated service available for rendered UI checks.
''
