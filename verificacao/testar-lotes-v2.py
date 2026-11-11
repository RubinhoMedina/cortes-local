from pathlib import Path
import hashlib,json,os,queue,sys,threading,unittest,uuid
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(r'C:/Users/Windows/edicao-ia/cortes-app')
WORK=Path(__file__).resolve().parent
os.environ['CORTES_DATA_DIR']=str(WORK/'testes-lotes-v2')
sys.path.insert(0,str(ROOT))
import storage,planning,research,batch
for name,path in json.loads((ROOT/'tools.json').read_text(encoding='utf-8-sig')).items():
    os.environ['PATH']=str(Path(path).parent)+os.pathsep+os.environ['PATH']

class BatchTests(unittest.TestCase):
    def setUp(self):
        storage.DATA=WORK/'testes-lotes-v2'/uuid.uuid4().hex
        storage.DATA.mkdir(parents=True)
        with storage.connection() as db:
            db.executescript('CREATE TABLE jobs(id TEXT PRIMARY KEY,updated TEXT,data TEXT);CREATE TABLE observations(video_id TEXT,observed REAL,views INTEGER);')
        self.engine=batch.Pipeline.__new__(batch.Pipeline)
        self.engine.cancelled=set();self.engine.paused=set();self.engine.scheduled=set()
        self.engine.lock=threading.RLock();self.engine.queue=queue.Queue();self.engine.active=None

    def job(self,target=100,**options):
        return storage.create(planning.make_plan(dict(topic='GTA6',target_clips=target,max_sources=20,**options)))

    def add(self,identifier,video,amount):
        job=storage.get(identifier)
        for n in range(min(amount,job['options']['target_clips']-len(job['clips']))):
            cid=f"{video['id']}-{len(job['clips'])}"
            path=storage.DATA/identifier/(cid+'.fixture')
            path.write_bytes(b'fixture de controle; nao e video')
            job['clips'].append({'id':cid,'source_id':video['id'],'score':80,'file':str(path),
                                 'export_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'status':'review'})
        storage.save(job)

    def test_exact_user_request(self):
        text='encontre os videos mais viralizados do gta6 me entregue 100 cortes completos prontos'
        result=planning.make_plan({'topic':text})
        self.assertEqual((result['topic'],result['target_clips'],result['max_sources']),('GTA 6',100,50))
        self.assertEqual(result['request'],text)
        self.assertEqual(planning.make_plan({'topic':'crie 100 cortes de GTA VI'})['target_clips'],100)
        self.assertEqual(planning.make_plan({'topic':'GTA6 e me entregue 100 cortes'})['topic'],'GTA 6')

    def test_limits_override_and_migration(self):
        self.assertEqual(planning.make_plan({'topic':'GTA6 100 cortes','target_clips':'2'})['target_clips'],2)
        self.assertEqual(planning.migrate({'topic':'encontre videos do GTA6 me entregue 100 cortes','max_sources':1,'max_clips':4})['target_clips'],100)
        for data in [{'topic':'GTA6','target_clips':1001},{'topic':'GTA6','target_clips':'2.5'},
                     {'topic':'GTA6','source_url':'https://example.org/test'}]:
            with self.assertRaises(ValueError):planning.make_plan(data)

    def test_hundred_with_empty_search_failed_source_and_no_overrun(self):
        job=self.job()
        pages=[[],[{'id':'bad','channel':'Falha'}]+[{'id':f'good{i}','channel':f'Canal {i}'} for i in range(8)]]
        calls=[]
        def page(options,runner,folder,notify,index,excluded):
            return pages[index] if index<len(pages) else [],[],{'query':str(index)}
        def source(identifier,video,refs,runner):
            calls.append(video['id'])
            if video['id']=='bad':raise RuntimeError('falha simulada')
            self.add(identifier,video,23)
            return 'done'
        self.engine.process_source=source
        with patch.object(research,'discover_page',side_effect=page):self.engine.process(job['id'])
        done=storage.get(job['id'])
        self.assertEqual((done['status'],len(done['clips'])),('ready',100))
        self.assertEqual(calls.count('bad'),2)
        self.assertEqual(len(calls),7)
        self.assertEqual(len({c['id'] for c in done['clips']}),100)
        self.assertEqual(done['stop_reason'],'target_reached')

    def test_pause_preserves_and_resume_continues(self):
        job=self.job(5)
        video={'id':'source','channel':'Canal'}
        storage.update(job['id'],sources=[video])
        def pause(identifier,video,refs,runner):
            self.add(identifier,video,2)
            raise batch.Paused('teste de interrupcao')
        self.engine.process_source=pause
        with self.assertRaises(batch.Paused):self.engine.process(job['id'])
        first=storage.get(job['id'])['clips']
        self.engine.process_source=lambda identifier,video,refs,runner:(self.add(identifier,video,3) or 'done')
        self.engine.process(job['id'])
        done=storage.get(job['id'])
        self.assertEqual(len(done['clips']),5)
        self.assertEqual(done['clips'][:2],first)

    def test_partial_can_search_more_and_excludes_existing(self):
        job=self.job(5)
        options=dict(job['options'],max_sources=1)
        storage.update(job['id'],options=options)
        def page(options,runner,folder,notify,index,excluded):
            return [{'id':f'source{index}','channel':'Canal'}],[],{'query':str(index)}
        self.engine.process_source=lambda identifier,video,refs,runner:(self.add(identifier,video,2) or 'done')
        with patch.object(research,'discover_page',side_effect=page):
            self.engine.process(job['id'])
            partial=storage.get(job['id'])
            self.assertEqual((partial['status'],len(partial['clips'])),('partial',2))
            storage.update(job['id'],options=dict(options,max_sources=5))
            self.engine.process(job['id'])
        self.assertEqual(len(storage.get(job['id'])['clips']),5)

    def test_dedup_by_time_and_text(self):
        old={'source_id':'a','source_ranges':[[10,30]],'source_words':batch.words('one two three four five six seven eight nine ten eleven twelve thirteen fourteen')}
        self.assertTrue(batch.duplicate(dict(old,source_ranges=[[11,31]]),[old]))
        self.assertTrue(batch.duplicate(dict(old,source_id='b'),[old]))
        self.assertFalse(batch.duplicate({'source_id':'a','source_ranges':[[50,70]],'source_words':[]},[old]))

    def test_repeated_network_failures_are_explicit(self):
        job=self.job(5)
        with patch.object(research,'discover_page',side_effect=RuntimeError('HTTP 429')):
            self.engine.process(job['id'])
        result=storage.get(job['id'])
        self.assertEqual((result['status'],result['stop_reason']),('error','service_unavailable'))
        self.assertEqual(result['search_round'],3)
        self.assertTrue(result['warnings'])

    def test_recovery_automatically_enqueues_processing_job(self):
        job=self.job(1)
        storage.update(job['id'],status='processing')
        event=threading.Event()
        def recovered(engine,identifier):
            storage.update(identifier,status='ready');event.set()
        with patch.object(batch.Pipeline,'process',new=recovered):
            engine=batch.Pipeline(recover=True)
            self.assertTrue(event.wait(5))
            engine.queue.join()
        self.assertEqual(storage.get(job['id'])['status'],'ready')

    def test_real_source_loop_stops_at_remaining_target_and_retries_a_failed_clip(self):
        job=self.job(3,avoid_duplicates=False)
        self.add(job['id'],{'id':'previous'},2)
        video={'id':'newsource01','channel':'Canal','url':'https://youtube.com/watch?v=newsource01','published_at':1}
        transcript={'language':'pt','segments':[{'start':i*20,'end':i*20+15,'text':f'Jogo pergunta e resposta número {i}.'} for i in range(5)]}
        candidates=[{'id':i+1,'start':i*20,'end':i*20+15,'edit':[[i*20,i*20+15]],
                     'lines':['É esse jogo?','Sim, agora entendi.'],'subtitle_language':'pt',
                     'selection':{'score':50,'reasons':['pergunta']}} for i in range(5)]
        self.engine.transcript=lambda *args:transcript
        attempts=[]
        def render(identifier,video,clip,options,folder,refs,runner):
            attempts.append(clip['edit'][0][0])
            if clip['edit'][0][0]==0:raise RuntimeError('candidato inviável')
            path=folder/'fixture.bin';path.write_bytes(b'fixture')
            return {'id':video['id']+'-'+str(clip['id']),'source_id':video['id'],'score':80,'file':str(path),'status':'review'}
        self.engine.render_candidate=render
        with patch.object(batch,'load_selector',return_value=SimpleNamespace(select_candidates=lambda *args:{'clips':candidates})):
            self.engine.process_source(job['id'],video,[],None)
        self.assertEqual(len(storage.get(job['id'])['clips']),3)
        self.assertEqual(attempts,[0,0,20])

    def test_manual_link_bypasses_empty_topic_search(self):
        options=planning.make_plan({'topic':'GTA6','source_url':'https://youtu.be/E07OTlhncP0','target_clips':2})
        item={'id':'E07OTlhncP0','duration':957,'is_live':False}
        with patch.object(research,'hydrate',return_value=item),patch.object(research,'search',return_value=[]):
            found,refs,evidence=research.discover_page(options,None,storage.DATA,lambda *args:None,0,set())
        self.assertEqual(len(found),1)

if __name__=='__main__':
    unittest.main(verbosity=2)
