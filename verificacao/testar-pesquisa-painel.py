from pathlib import Path
import json,subprocess,sys,time
root=Path(r'C:/Users/Windows/edicao-ia/cortes-app')
sys.path.insert(0,str(root))
import research
directory=Path(__file__).resolve().parent/'pesquisa-painel-atual'
directory.mkdir(exist_ok=True)
def runner(command,cwd,capture=False,timeout=180):
    result=subprocess.run(command,cwd=cwd,capture_output=True,text=True,encoding='utf8',timeout=timeout)
    if result.returncode:raise RuntimeError(result.stderr[-1000:])
    return result.stdout
started=time.monotonic()
sources,refs,sample=research.discover({'topic':'GTA 6','max_sources':1,'max_duration_minutes':10},runner,directory,lambda *args:print(*args))
assert len(sources)==1 and sources[0]['duration']<=600
assert sources[0]['score_basis']['sample_size']>=2
assert sources[0]['published_at'] and sources[0]['average_views_per_hour'] is not None
assert research.canonical('Grand Theft Auto VI')==research.canonical('GTA6')=='gta 6'
result={'seconds':round(time.monotonic()-started,2),'sources':sources,'references':refs,'sample':sample}
(directory/'resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print('OK',sources[0]['id'],sources[0]['research_score'],len(refs),'referências;',result['seconds'],'segundos')
