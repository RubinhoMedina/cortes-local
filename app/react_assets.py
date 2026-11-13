"""Allowlisted local Flow assets. The HTTP API accepts IDs, never file paths."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import storage

ASSETS = Path(__file__).resolve().parent / 'data/react-assets'
ASSETS.mkdir(parents=True, exist_ok=True)


def asset_path(identifier):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', str(identifier)):
        raise ValueError('Escolha um ator Flow cadastrado.')
    root = ASSETS.resolve()
    path = (root / (identifier + '.mp4')).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Ator Flow não encontrado no catálogo local.')
    return path


def catalog():
    result = []
    for path in sorted(ASSETS.glob('*.mp4')):
        try:
            asset_path(path.stem)
            result.append({'id': path.stem, 'name': path.stem.replace('-', ' ')})
        except ValueError:
            continue
    return result


def options(data):
    layout = data.get('layout', 'split')
    if layout not in {'split', 'flow_react'}:
        raise ValueError('Layout inválido.')
    if layout == 'split':
        return {'layout': 'split'}
    identifier = str(data.get('flow_actor_id', ''))
    asset_path(identifier)
    text = str(data.get('seam_text', '')).strip()
    if len(text) > 100 or any(c in text for c in '{}\\\r\n'):
        raise ValueError('Texto central: até 100 caracteres, em uma linha, sem barras ou chaves.')
    return {'layout': layout, 'flow_actor_id': identifier, 'seam_text': text}


def copy_to_job(job):
    config = job['options']
    if config.get('layout') != 'flow_react':
        return
    source = asset_path(config['flow_actor_id'])
    data = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(source)]))
    if not all(any(s['codec_type']==kind for s in data['streams']) for kind in ('video','audio')):
        raise ValueError('O ator Flow deve ter vídeo e áudio gerados no Flow.')
    destination = storage.DATA/job['id']/'assets'
    destination.mkdir(exist_ok=True)
    shutil.copy2(source, destination/'flow-actor.mp4')
    config['flow_actor_sha256'] = hashlib.sha256((destination/'flow-actor.mp4').read_bytes()).hexdigest()
    config['flow_actor_duration'] = float(data['format']['duration'])
    storage.save(job)
