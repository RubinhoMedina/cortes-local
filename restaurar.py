"""Verifica e extrai o backup em uma pasta vazia, sem alterar a instalação atual."""
from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import zipfile
import base64
import io
import shutil


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def restore(repository, destination):
    manifest = json.loads((repository / 'backup/manifesto.json').read_text(encoding='utf8'))
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('O destino precisa estar vazio; a instalação atual não será sobrescrita.')
    # Verify every part before materializing any restored file.
    for archive in manifest['archives']:
        for part in archive['parts']:
            path = repository / 'backup' / part['name']
            if path.stat().st_size != part['bytes'] or digest(path) != part['sha256']:
                raise ValueError('Parte ausente ou corrompida: ' + part['name'])
    destination.mkdir(parents=True, exist_ok=True)
    restored = 0
    for archive in manifest['archives']:
        with tempfile.TemporaryFile() as combined:
            checksum = hashlib.sha256()
            for part in archive['parts']:
                with (repository / 'backup' / part['name']).open('rb') as source:
                    for block in iter(lambda: source.read(1024 * 1024), b''):
                        combined.write(block)
                        checksum.update(block)
            if checksum.hexdigest() != archive['sha256']:
                raise ValueError('Arquivo combinado corrompido: ' + archive['name'])
            combined.seek(0)
            with zipfile.ZipFile(combined) as package:
                if package.testzip():
                    raise ValueError('ZIP com falha: ' + archive['name'])
                for member in package.infolist():
                    target = (destination / member.filename).resolve()
                    if not target.is_relative_to(destination):
                        raise ValueError('Caminho inseguro no backup')
                    package.extract(member, destination)
                for item in archive['files']:
                    path = destination / item['path']
                    if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
                        raise ValueError('Falha de integridade: ' + item['path'])
                    restored += 1
        print(archive['name'] + ': íntegro', flush=True)
    # Volumes preserve the baseline; tracked source is the current application version.
    overlays = [('app','edicao-ia/cortes-app'),('motor','cortes-trabalho/001-E07OTlhncP0'),
                ('integracoes/youtube-mcp','edicao-ia/youtube-mcp')]
    for source_name,target_name in overlays:
        source_root=repository/source_name
        if not source_root.is_dir():
            continue
        for source in source_root.rglob('*'):
            if source.is_file() and source.name not in {'bundle.zip.b64','bundle.sha256'}:
                target=destination/target_name/source.relative_to(source_root)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target)
    bundle=repository/'app/frontend/bundle.zip.b64'
    if bundle.exists():
        payload=base64.b64decode(bundle.read_text(encoding='ascii'),validate=True)
        expected=(bundle.parent/'bundle.sha256').read_text(encoding='ascii').strip()
        if hashlib.sha256(payload).hexdigest()!=expected:
            raise ValueError('Interface compilada corrompida.')
        target=destination/'edicao-ia/cortes-app/frontend/dist'
        target.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(payload)) as package:
            if package.testzip():raise ValueError('ZIP da interface inválido.')
            if any(not (target/name).resolve().is_relative_to(target.resolve()) for name in package.namelist()):
                raise ValueError('Caminho inseguro no pacote da interface.')
            package.extractall(target)
    print('Código atual e interface compilada aplicados; volumes originais preservados.',flush=True)
    return restored


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', type=Path, default=Path.cwd() / 'restauracao-cortes-local')
    args = parser.parse_args()
    count = restore(Path(__file__).resolve().parent, args.destino)
    print(f'{count} arquivos restaurados e conferidos em {args.destino.resolve()}')
