from pathlib import Path
import json,os,subprocess,sys,time
ROOT=Path(r'C:/Users/Windows/edicao-ia/cortes-app')
WORK=Path(__file__).resolve().parent
os.environ['CORTES_DATA_DIR']=str(WORK/'busca-v2-data')
sys.path.insert(0,str(ROOT))
import planning,research
def runner(command,directory,capture=False,timeout=180):
    result=subprocess.run(command,cwd=directory,capture_output=True,text=True,encoding='utf8',timeout=timeout)
    if result.returncode:raise RuntimeError(result.stderr[-1000:])
    return result.stdout
request='encontre os videos mais viralizados do gta6 me entregue 100 cortes completos prontos'
options=planning.make_plan({'topic':request})
started=time.monotonic()
sources,refs,evidence=research.discover_page(options,runner,WORK,lambda *args:print(args[-1],flush=True),0,set())
assert sources and evidence['query']=='GTA 6 streamer reaction'
assert len({v['id'] for v in sources})==len(sources)
result={'topic':options['topic'],'target':options['target_clips'],'query':evidence['query'],
        'candidates':len(sources),'references':len(refs),'seconds':round(time.monotonic()-started,2),
        'sources':sources,'reference_sample':refs}
(WORK/'busca-v2-real.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print('PASS: frase original virou pesquisa GTA 6 e retornou',len(sources),'candidatos reais e',len(refs),'referências.',flush=True)
