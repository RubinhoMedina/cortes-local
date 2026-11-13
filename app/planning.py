"""Converte tema ou pedido simples em um plano explícito e limitado de produção."""
import react_assets
import math
import re
import urllib.parse

VERSION = 2


def interpret(text):
    original = ' '.join(str(text).split()).strip()
    if not 2 <= len(original) <= 600:
        raise ValueError('Informe um tema ou pedido entre 2 e 600 caracteres.')
    counts = re.findall(r'\b(\d+)\s+(?:cortes?|shorts?|clipes?|vídeos?\s+curtos)\b', original, re.I)
    target = int(counts[-1]) if counts else None
    tail = re.search(r'\b(?:me\s+)?(?:entregue|gere|crie|produza|faça|quero receber)\b', original, flags=re.I)
    topic = original[:tail.start()] if tail and tail.start()>0 else original
    topic = re.sub(r'\b\d+\s+(?:cortes?|shorts?|clipes?)\b', '', topic, flags=re.I)
    prefix = r'(?:por|favor|eu|quero|preciso|encontre|encontrar|busque|buscar|procure|procurar|pesquise|pesquisar|ache|crie|gere|produza|faça|entregue|me|os|as|um|uma|vídeos|videos|mais|viralizados|viralizadas|virais|melhores|cortes|sobre|do|da|de|a|respeito)'
    topic = re.sub(r'^(?:' + prefix + r'\b[\s,:;]*)+', '', topic, flags=re.I).strip(' .,;:!?')
    topic = re.sub(r'\s+(?:e|para|então|com)$','',topic,flags=re.I)
    topic = re.sub(r'\b(?:gta\s*(?:6|vi)|grand\s+theft\s+auto\s+(?:vi|6))\b', 'GTA 6', topic, flags=re.I)
    topic = re.sub(r'\b(?:gta\s*(?:5|v)|grand\s+theft\s+auto\s+(?:v|5))\b', 'GTA 5', topic, flags=re.I)
    if not 2 <= len(topic) <= 160:
        raise ValueError('Não identifiquei o assunto. Exemplo: encontre vídeos de GTA 6 e me entregue 100 cortes.')
    return original, topic, target


def make_plan(data):
    original, topic, inferred = interpret(data.get('request') or data.get('topic', 'GTA 6'))
    explicit = data.get('target_clips')
    if explicit not in (None,'') and not re.fullmatch(r'\d+',str(explicit)):
        raise ValueError('A meta precisa ser um número inteiro de cortes.')
    target = int(explicit) if explicit not in (None, '') else inferred or 12
    if not 1 <= target <= 1000:
        raise ValueError('A meta deve ficar entre 1 e 1000 cortes. A quantidade depende dos momentos adequados encontrados.')
    per_video = int(data.get('max_clips') or 20)
    sources = int(data.get('max_sources') or min(200, max(12, math.ceil(target / 2))))
    rounds = int(data.get('max_search_rounds') or 12)
    duration = int(data.get('max_duration_minutes') or 30)
    model = data.get('whisper_model', 'base')
    if not 1 <= per_video <= 50 or not 1 <= sources <= 200 or not 1 <= rounds <= 40:
        raise ValueError('Use até 50 candidatos por vídeo, 200 fontes e 40 rodadas de pesquisa.')
    if not 2 <= duration <= 120 or model not in {'base', 'large-v3-turbo'}:
        raise ValueError('Duração ou modelo de transcrição inválido.')
    url = str(data.get('source_url', '')).strip()
    if url:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in {'youtube.com','www.youtube.com','m.youtube.com','youtu.be'}:
            raise ValueError('Use um link HTTPS do YouTube.')
        identifier = parsed.path.strip('/') if parsed.hostname == 'youtu.be' else urllib.parse.parse_qs(parsed.query).get('v',[''])[0]
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', identifier):
            raise ValueError('O link precisa apontar para um vídeo do YouTube.')
        url = 'https://www.youtube.com/watch?v=' + identifier
        sources = rounds = 1
    notes = ['A meta não força cortes sem contexto ou repetidos. O lote pode terminar abaixo dela e explicar o motivo.',
             'Processamento local, um vídeo e um corte por vez. Lotes grandes podem levar várias horas.']
    if url:
        notes.append('Com uma fonte específica, o limite é o conteúdo desse vídeo; outras fontes não serão pesquisadas.')
    layout_options = react_assets.options(data)
    return {**layout_options, 'planner_version': VERSION, 'request': original, 'topic': topic, 'target_clips': target,
            'max_sources': sources, 'max_clips': per_video, 'max_search_rounds': rounds,
            'max_duration_minutes': duration, 'whisper_model': model, 'source_url': url,
            'avoid_duplicates': bool(data.get('avoid_duplicates', True)), 'notes': notes}


def migrate(options):
    if options.get('planner_version') == VERSION:
        return dict(options)
    data = dict(options)
    _, _, requested = interpret(data.get('topic', 'GTA 6'))
    if requested:
        # Old releases silently kept the default 1 source / 4 clips on a request for 100.
        data.pop('max_sources', None)
        data.pop('max_clips', None)
    else:
        data['target_clips'] = options.get('target_clips') or options.get('max_sources',1)*options.get('max_clips',4)
    return make_plan(data)
