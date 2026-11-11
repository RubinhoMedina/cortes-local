import hashlib
import json
from pathlib import Path
import sys

project=Path(r'C:/Users/Windows/cortes-trabalho/001-E07OTlhncP0')
sys.path.insert(0,str(project))
from selecao import select_candidates, edit_ranges, clean_segments
from enquadramento import plan_from_samples, reaction_crop

config=json.loads((project/'lote.json').read_text(encoding='utf8'))
transcript=json.loads((project/'audio.json').read_text(encoding='utf8'))
settings=json.loads((project/'automacao.json').read_text(encoding='utf8'))
result=select_candidates(config,transcript,settings)
assert len(result['clips'])==6
assert result==select_candidates(config,transcript,settings)
for clip in result['clips']:
    assert 12 <= sum(b-a for a,b in clip['edit']) <= 40
    assert all(clip['start']<=a<b<=clip['end'] for a,b in clip['edit'])
    selected=[s for a,b in clip['edit'] for s in transcript['segments'] if a<=s['start']<b]
    assert len(selected)==len(clip['lines'])
    words=' '.join(clip['lines']).lower()
    if 'brazilian' in words:
        assert clip['title']=='ESPECULAÇÃO DOS PARTICIPANTES'
assert edit_ranges([{'start':1,'end':3},{'start':10,'end':12}])==[[1,3.2],[9.8,12]]
assert not clean_segments({'segments':[{'start':0,'end':0,'text':'empty'}]})
portuguese={'language':'pt','segments':[
    {'start':0,'end':6,'text':'Eu estou no jogo!'},
    {'start':6,'end':14,'text':'Meu Deus, eu estou no jogo!'}
]}
pt=select_candidates({'url':'local','transcript':'audio.json','clips':[]},portuguese,
                     {'minimum_seconds':12,'maximum_seconds':40,'max_clips':1,'terms':['jogo']})
assert pt['clips'][0]['translation_status']=='original'
assert pt['clips'][0]['subtitle_language']=='pt'
base=[840,600,0,480]
assert reaction_crop([],base)[0]==base
samples=[{'time':t,'change':0,'faces':[[100,670,160,160],[500,710,150,150]]}
         for t in [1,3,5,7,9,11,13,15]]
crop,_=reaction_crop(samples,base)
w,h,x,y=crop
assert x<=100 and y<=670 and x+w>=650 and y+h>=860
plan=plan_from_samples(samples,{'start':100,'end':116,'edit':[[101,106],[110,115]]})
assert plan[0]['start']==0 and plan[-1]['end']==10
assert all(a['end']==b['start'] for a,b in zip(plan,plan[1:]))
assert all(all(v%2==0 for v in scene['reaction_crop']) for scene in plan)
baseline=json.loads(Path(__file__).with_name('baseline-melhorias.json').read_text())
for filename,expected in baseline.items():
    assert hashlib.sha256(Path(filename).read_bytes()).hexdigest()==expected, filename
print('PASS: seleção determinística, tempos, legendas, idioma, rótulos de contexto, cenas e preservação de 15 arquivos do lote original.')
