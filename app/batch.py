"""Controlador durável de metas, pesquisa incremental e produção serial."""
import ctypes
import hashlib
import json
import logging
from pathlib import Path
import queue
import re
import shutil
import threading
import time
import unicodedata

import planning
import research
import reference_analysis
import local_text
import storage
from pipeline import Pipeline as BasePipeline, Cancelled, atomic_json, load_selector, ROOT, PYTHON, LEGACY


class Paused(Exception):
    pass


def words(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii','ignore').decode().lower()
    return re.findall(r'[a-z0-9]+', text)


def duplicate(candidate, existing):
    for previous in existing:
        if previous.get('source_id') == candidate.get('source_id'):
            for left, right in candidate['source_ranges']:
                for start, end in previous.get('source_ranges', []):
                    common = max(0, min(right,end)-max(left,start))
                    if common / max(.001,min(right-left,end-start)) >= .6:
                        return True
        a, b = candidate.get('source_words', []), previous.get('source_words', [])
        if len(a) >= 12 and len(b) >= 12:
            aa = {tuple(a[i:i+5]) for i in range(len(a)-4)}
            bb = {tuple(b[i:i+5]) for i in range(len(b)-4)}
            if len(aa) >= 5 and len(bb) >= 5 and len(aa & bb)/max(1,len(aa | bb)) >= .82:
                return True
    return False


class Pipeline(BasePipeline):
    def __init__(self, recover=True):
        self.queue = queue.Queue()
        self.cancelled, self.paused, self.scheduled = set(), set(), set()
        self.lock = threading.RLock()
        self.active = None
        self.thread = threading.Thread(target=self.worker, daemon=True)
        if recover:
            for job in reversed(storage.jobs()):
                if job['status'] in {'queued','processing','interrupted'}:
                    self.submit(job['id'])
        self.thread.start()

    def submit(self, identifier):
        with self.lock:
            if identifier in self.scheduled or self.active == identifier:
                raise ValueError('Este lote já está na fila.')
            job = storage.get(identifier)
            options = planning.migrate(job['options'])
            if job['status'] in {'error','cancelled','paused'}:
                for state in job.get('source_states',{}).values():
                    if state['status']=='failed':
                        state.update(status='pending',attempts=0)
                storage.save(job)
            if job.get('stop_reason')=='service_unavailable':
                storage.update(identifier,discovery=[page for page in job.get('discovery',[]) if not page.get('error')])
            self.cancelled.discard(identifier)
            self.paused.discard(identifier)
            self.scheduled.add(identifier)
            storage.update(identifier, options=options, topic=options['topic'], status='queued', error=None,
                           stop_reason=None, message='Na fila; meta de %d cortes' % options['target_clips'])
            self.queue.put(identifier)

    def pause(self, identifier):
        with self.lock:
            self.paused.add(identifier)
            if self.active != identifier:
                storage.update(identifier, status='paused', message='Lote pausado; arquivos preservados.')
            else:
                storage.update(identifier, message='Pausando a operação atual; arquivos prontos preservados.')

    def check(self, identifier):
        super().check(identifier)
        if identifier in self.paused:
            raise Paused()

    def run(self, identifier, command, directory, capture=False, timeout=180):
        label = 'Executando etapa local'
        if str(command[0]) == 'yt-dlp':
            label = 'Consultando o YouTube' if capture or '--skip-download' in command else 'Baixando mídia da fonte'
        elif any(str(part).endswith('transcribe.py') for part in command):
            label = 'Transcrevendo o áudio neste computador'
        elif 'fluxo.py' in command:
            label = 'Editando e validando o vídeo'
        elif str(command[0]) == 'ffmpeg':
            label = 'Preparando mídia e capas'
        storage.update(identifier,active_operation={'label':label,'started_at':storage.now(),'timeout_seconds':timeout})
        try:
            return super().run(identifier,command,directory,capture=capture,timeout=timeout)
        except RuntimeError as error:
            tail = getattr(error,'stderr','').lower()
            if '429' in tail or 'too many requests' in tail:
                raise RuntimeError('O YouTube limitou temporariamente os pedidos (429). A etapa pode ser retomada.') from error
            if 'not a bot' in tail or 'confirm your age' in tail or 'sign in to' in tail:
                raise RuntimeError('O YouTube exigiu uma verificação para esta fonte. Ela foi marcada para nova tentativa ou substituição.') from error
            raise
        finally:
            storage.update(identifier,active_operation=None)

    def worker(self):
        while True:
            identifier = self.queue.get()
            with self.lock:
                self.scheduled.discard(identifier)
                self.active = identifier
            try:
                self.check(identifier)
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
                storage.update(identifier, status='processing')
                self.process(identifier)
            except Paused as error:
                storage.update(identifier, status='paused', message=str(error) or 'Lote pausado; pode retomar.', error=None)
            except Cancelled:
                storage.update(identifier, status='cancelled', message='Cancelado; cortes prontos e arquivos preservados.')
            except Exception as error:
                logging.exception('Falha no lote %s', identifier)
                storage.update(identifier, status='error', error=str(error), message=str(error))
            finally:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
                with self.lock:
                    self.active = None
                self.queue.task_done()

    def notify(self, identifier, stage, message):
        job = storage.get(identifier)
        target = job['options']['target_clips']
        count = len(job['clips'])
        storage.event(identifier, stage, min(99, round(100*count/target)), message)

    def warn(self, identifier, message):
        with storage.LOCK:
            job = storage.get(identifier)
            if message not in job['warnings']:
                job['warnings'].append(message)
            storage.save(job)

    def source_state(self, identifier, video_id, **changes):
        with storage.LOCK:
            job = storage.get(identifier)
            states = job.setdefault('source_states', {})
            state = states.setdefault(video_id, {'status':'pending','attempts':0})
            state.update(changes)
            storage.save(job)
            return dict(state)

    def stats(self, identifier, **changes):
        with storage.LOCK:
            job = storage.get(identifier)
            job.setdefault('stats', {}).update(changes)
            states = job.get('source_states', {}).values()
            job['stats'].update(produced=len(job['clips']), target=job['options']['target_clips'],
                                sources_examined=sum(s['status'] in {'done','failed','empty'} for s in states),
                                sources_failed=sum(s['status']=='failed' for s in job.get('source_states',{}).values()),
                                search_rounds=job.get('search_round',0))
            storage.save(job)

    def transcript(self, identifier, video, directory, runner):
        if not (directory/'audio.json').exists():
            for job in storage.jobs():
                cached = storage.DATA/job['id']/video['id']/'audio.json'
                if job['id'] == identifier or not cached.exists():
                    continue
                if job['options'].get('whisper_model','base') != storage.get(identifier)['options']['whisper_model']:
                    continue
                try:
                    data = json.loads(cached.read_text(encoding='utf8'))
                    if data.get('segments') and data['segments'][-1]['end'] <= (video.get('duration') or 0)+5:
                        shutil.copy2(cached,directory/'audio.json')
                        break
                except (ValueError,OSError,KeyError):
                    continue
        return super().transcript(identifier,video,directory,runner)

    def source_catalog(self, video):
        catalog = super().source_catalog(video)
        for job in storage.jobs():
            folder = storage.DATA/job['id']/video['id']
            for path in (folder/'revisao-automatica').glob('*.json'):
                try:
                    receipt = json.loads(path.read_text(encoding='utf8'))
                    clip = receipt['signature']['clip']
                    key = hashlib.sha256(json.dumps([video['url'],clip['start'],clip['end']]).encode()).hexdigest()[:16]
                    source = folder/'fontes'/f'{key}.mp4'
                    if source.is_file():
                        catalog.append({'path':str(source),'start':clip['start'],'end':clip['end']})
                except (KeyError,ValueError,OSError):
                    continue
        return catalog

    def render_candidate(self, identifier, video, clip, config, directory, references, runner):
        self.check(identifier)
        if shutil.disk_usage(storage.DATA).free < 1536*1024*1024:
            raise Paused('Pouco espaço no disco. Lote pausado; libere espaço com backup validado antes de retomar.')
        metadata = directory/f'publicacao-{clip["id"]}.json'
        signature = hashlib.sha256(json.dumps([clip['lines'],clip['subtitle_language'],config['topic'],
                local_text.PACKAGE_VERSION,[ref.get('opening_analysis') for ref in references]],ensure_ascii=False).encode()).hexdigest()
        package = json.loads(metadata.read_text(encoding='utf8')) if metadata.exists() else None
        if not package or package.get('input_sha256') != signature:
            self.notify(identifier,'packaging',f'Preparando legenda e textos de {video["channel"]}')
            package = local_text.package(config['topic'],clip['lines'],references,clip['subtitle_language'],video['title'])
            package['input_sha256'] = signature
            atomic_json(metadata,package)
        self.check(identifier)
        render_clip = dict(clip,lines=package['translations'],subtitle_language='pt',
                           translation_status='automática; revisar',title=package['hook'][:80])
        if config.get('layout') == 'flow_react':
            actor = storage.DATA/identifier/'assets/flow-actor.mp4'
            if not actor.is_file() or hashlib.sha256(actor.read_bytes()).hexdigest() != config.get('flow_actor_sha256'):
                raise RuntimeError('Ator Flow do lote ausente ou alterado. Inicie um novo lote com o ativo correto.')
            (directory/'assets').mkdir(exist_ok=True)
            shutil.copy2(actor,directory/'assets/flow-actor.mp4')
            render_clip.update(layout='flow_react',flow_actor='assets/flow-actor.mp4',
                               seam_text=config.get('seam_text') or package['hook'][:100])
        render_config = {'url':video['url'],'transcript':'audio.json','clips':[render_clip],
                         'sources':self.source_catalog(video)}
        atomic_json(directory/'lote.json',render_config)
        self.notify(identifier,'render',f'Editando corte de {video["channel"]}; {len(storage.get(identifier)["clips"])}/{config["target_clips"]} prontos')
        runner([PYTHON,'-X','utf8','fluxo.py','--config','lote.json','--auto-frame','--no-open','--only',clip['id']],directory,timeout=4*3600)
        output = directory/'revisao-automatica'/f'auto-corte{clip["id"]:02}.mp4'
        receipt = json.loads(output.with_suffix('.json').read_text(encoding='utf8'))
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        if receipt.get('export_sha256') != digest or receipt['signature']['clip']['lines'] != package['translations']:
            raise RuntimeError('A exportação não corresponde às legendas ou à integridade esperada.')
        result = {'id':video['id']+'-'+str(clip['id']),'title':package['title'],'hook':package['hook'],
                  'description':package['description']+f'\n\nFonte: {video["channel"]} — {video["url"]}',
                  'tags':package['tags'],'score':round(.7*min(100,max(0,clip['selection']['score']*1.4))+.3*package['editorial_score']),
                  'reason':'Seleção: '+', '.join(clip['selection']['reasons'])+'. '+package['reason'],
                  'cover_prompt':package['cover_prompt'],'method':package['method'],
                  'reference_pattern':package['reference_pattern'],'references':references[:3],
                  'source_id':video['id'],'source_title':video['title'],'source_channel':video['channel'],
                  'source_url':video['url'],'research_score':video.get('research_score'),
                  'source_ranges':clip['edit'],'source_words':clip['source_words'],
                  'duration':round(sum(b-a for a,b in clip['edit']),2),'file':str(output),
                  'media':output.relative_to(storage.DATA/identifier).as_posix(),
                  'layout':render_clip.get('layout','split'),'audio_source':'flow' if config.get('layout')=='flow_react' else 'source',
                  'export_sha256':digest,'subtitle_language':None if config.get('layout')=='flow_react' else 'pt',
                  'caption_mode':'seam_title' if config.get('layout')=='flow_react' else 'source_subtitles','status':'review','selected_cover':0}
        result['covers'] = self.covers(identifier,result,directory,runner)
        return result

    def process_source(self, identifier, video, references, runner):
        options = storage.get(identifier)['options']
        folder = storage.DATA/identifier/video['id']
        folder.mkdir(exist_ok=True)
        self.notify(identifier,'transcript',f'Preparando fonte: {video["channel"]}')
        if not video.get('published_at'):
            details = research.hydrate(video,runner,folder)
            if not details or details['is_live'] or not 12 <= (details['duration'] or 0) <= options['max_duration_minutes']*60:
                raise RuntimeError('Fonte indisponível ou fora dos limites de duração.')
            video.update({key:value for key,value in details.items() if key not in {'research_score','score_basis'}})
            with storage.LOCK:
                latest = storage.get(identifier)
                latest['sources'] = [video if item['id']==video['id'] else item for item in latest['sources']]
                storage.save(latest)
        transcript = self.transcript(identifier,video,folder,runner)
        if transcript.get('language') not in {'en','pt'}:
            self.warn(identifier,f'{video["channel"]}: idioma {transcript.get("language","desconhecido")} não disponível no tradutor local; fonte ignorada.')
            return 'empty'
        original = {'url':video['url'],'transcript':'audio.json','clips':[]}
        if video['id']=='E07OTlhncP0':
            original = json.loads((LEGACY/'lote.json').read_text(encoding='utf8'))
        selector = load_selector()
        settings = {'minimum_seconds':12,'maximum_seconds':40,'max_clips':options['max_clips'],
                    'terms':re.findall(r'\w+',options['topic'].lower())+['game','jogo','lucia','franklin','michael']}
        selection = selector.select_candidates(original,transcript,settings)
        for filename in ['executor.py','fluxo.py','selecao.py','enquadramento.py','piloto-legendas.ass']:
            if not (folder/filename).exists() or (folder/filename).read_bytes() != (LEGACY/filename).read_bytes():
                shutil.copy2(LEGACY/filename,folder/filename)
        candidates = selection['clips']
        if options.get('layout') == 'flow_react':
            candidates = [clip for clip in candidates if sum(b-a for a,b in clip['edit']) <= options.get('flow_actor_duration',0)+.08]
            if not candidates:
                self.warn(identifier,'Nenhum candidato cabe na duração do ator Flow. Gere uma fala maior no Flow ou use uma fonte com cortes menores.')
        best = max((clip['selection']['score'] for clip in candidates),default=0)
        made, failures, duplicates = 0, [], 0
        for clip in candidates:
            self.check(identifier)
            job = storage.get(identifier)
            if len(job['clips']) >= options['target_clips']:
                break
            if clip['selection']['score'] < max(25,best*.7):
                continue
            raw = ' '.join(segment['text'] for segment in transcript['segments']
                           if any(a <= segment['start'] < b for a,b in clip['edit']))
            clip['source_words'] = words(raw)
            clip['id'] = int(hashlib.sha256(json.dumps([video['id'],clip['edit']]).encode()).hexdigest()[:8],16)
            identifier_clip = video['id']+'-'+str(clip['id'])
            if any(item['id']==identifier_clip for item in job['clips']):
                continue
            seen = [item for previous in storage.jobs() for item in previous['clips']]
            if video['id']=='E07OTlhncP0':
                seen.extend({'source_id':video['id'],'source_ranges':item['edit']} for item in original.get('clips',[]))
            if options['avoid_duplicates'] and duplicate({'source_id':video['id'],'source_ranges':clip['edit'],'source_words':clip['source_words']},seen):
                duplicates += 1
                self.stats(identifier,duplicate_skips=job.get('stats',{}).get('duplicate_skips',0)+1)
                continue
            for attempt in range(2):
                try:
                    result = self.render_candidate(identifier,video,clip,options,folder,references,runner)
                    with storage.LOCK:
                        latest = storage.get(identifier)
                        latest['clips'].append(result)
                        latest['clips'].sort(key=lambda item:item['score'],reverse=True)
                        storage.save(latest)
                    made += 1
                    self.stats(identifier)
                    break
                except (Cancelled,Paused):
                    raise
                except Exception as error:
                    if attempt:
                        failures.append(str(error))
                    else:
                        self.notify(identifier,'render','Uma etapa falhou; repetindo o corte sem perder os resultados prontos.')
        if failures:
            self.warn(identifier,f'{video["channel"]}: {len(failures)} candidatos falharam. {failures[-1]}')
        if failures and made == 0:
            raise RuntimeError(failures[-1])
        return 'done' if made or any(c['source_id']==video['id'] for c in storage.get(identifier)['clips']) else 'empty'

    def process(self, identifier):
        required = [PYTHON, LEGACY/'executor.py', LEGACY/'fluxo.py', LEGACY/'selecao.py',
                    LEGACY/'enquadramento.py', LEGACY/'piloto-legendas.ass',
                    ROOT/'models/argos/translate-en_pt-1_9/model/model.bin', Path.home()/'edicao-ia/face.tflite']
        missing = [str(path) for path in required if not path.is_file()]
        missing.extend(name for name in ['yt-dlp','ffmpeg','ffprobe','deno'] if not shutil.which(name))
        if missing:
            raise RuntimeError('Componentes necessários não encontrados: '+', '.join(missing))
        folder = storage.DATA/identifier
        runner = lambda command,cwd,**kwargs:self.run(identifier,command,cwd,**kwargs)
        notify = lambda stage,progress,message:self.notify(identifier,stage,message)
        # Old successful results remain available; only corrupt/missing exports are reprocessed.
        job = storage.get(identifier)
        valid = []
        for clip in job['clips']:
            path = Path(clip['file'])
            if path.exists() and (not clip.get('export_sha256') or hashlib.sha256(path.read_bytes()).hexdigest()==clip['export_sha256']):
                valid.append(clip)
            else:
                self.source_state(identifier,clip['source_id'],status='pending',attempts=0)
        storage.update(identifier,clips=valid)
        while True:
            self.check(identifier)
            job = storage.get(identifier)
            options = job['options']
            self.stats(identifier)
            if len(job['clips']) >= options['target_clips']:
                reason = 'target_reached'
                break
            states = job.get('source_states',{})
            pending = [video for video in job['sources'] if states.get(video['id'],{}).get('status','pending') in {'pending','processing'}]
            if pending:
                video = pending[0]
                state = states.get(video['id'],{'attempts':0})
                self.source_state(identifier,video['id'],status='processing',attempts=state['attempts'])
                references = job['references']
                if references and not job.get('references_analyzed'):
                    references = reference_analysis.analyze(references,runner,notify)
                    self.check(identifier)
                    storage.update(identifier,references=references,references_analyzed=True)
                try:
                    result = self.process_source(identifier,video,references,runner)
                    self.source_state(identifier,video['id'],status=result,last_error=None)
                except (Cancelled,Paused):
                    self.source_state(identifier,video['id'],status='pending')
                    raise
                except Exception as error:
                    self.check(identifier)
                    logging.exception('Fonte %s falhou',video['id'])
                    retry = state['attempts'] < 1
                    self.source_state(identifier,video['id'],status='pending' if retry else 'failed',attempts=state['attempts']+1,last_error=str(error))
                    if not retry:
                        self.warn(identifier,f'{video["channel"]}: {error}; o lote continuou nas outras fontes.')
                continue
            examined = len(job['sources'])
            round_index = job.get('search_round',0)
            if len(job.get('discovery',[])) >= 3 and all(page.get('error') for page in job['discovery'][-3:]):
                reason = 'service_unavailable'
                break
            if examined >= options['max_sources']:
                reason = 'source_budget'
                break
            if round_index >= options['max_search_rounds']:
                reason = 'search_budget'
                break
            error = None
            for attempt in range(2):
                try:
                    found, references, evidence = research.discover_page(options,runner,folder,notify,round_index,
                                                                        {v['id'] for v in job['sources']})
                    error = None
                    break
                except (Cancelled,Paused):
                    raise
                except Exception as failure:
                    error = str(failure)
            if error:
                found, references, evidence = [], [], {'error':error}
                self.warn(identifier,f'Pesquisa {round_index+1} falhou: {error}. Outras consultas serão tentadas.')
            with storage.LOCK:
                latest = storage.get(identifier)
                latest.setdefault('discovery',[]).append(evidence)
                latest['search_round'] = round_index+1
                seen = {video['id'] for video in latest['sources']}
                for video in found:
                    if video['id'] not in seen and len(latest['sources']) < options['max_sources']:
                        latest['sources'].append(video)
                        seen.add(video['id'])
                if references and not latest['references']:
                    latest['references'] = references
                storage.save(latest)
            atomic_json(folder/'pesquisa.json',{'sources':storage.get(identifier)['sources'],
                                               'references':storage.get(identifier)['references'],
                                               'discovery':storage.get(identifier).get('discovery',[])})
        job = storage.get(identifier)
        count, target = len(job['clips']), job['options']['target_clips']
        explanations = {'target_reached':'Meta atingida.',
                        'source_budget':'O limite de fontes deste plano foi alcançado.',
                        'service_unavailable':'O serviço de pesquisa falhou repetidamente. Os resultados prontos foram preservados; tente retomar mais tarde.',
                        'search_budget':'As rodadas deste plano terminaram sem candidatos novos suficientes.'}
        message = f'{count}/{target} cortes prontos. '+explanations[reason]
        if count < target:
            message += ' Você pode ampliar a pesquisa; cortes repetidos ou fracos não foram usados para completar a meta.'
        storage.update(identifier,status='ready' if count >= target else 'error' if reason=='service_unavailable' and not count else 'partial',stage='review',
                       progress=100 if count>=target else round(100*count/target),message=message,stop_reason=reason,error=None)
        self.stats(identifier)
