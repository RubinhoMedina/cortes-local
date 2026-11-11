"""Verifica e extrai o backup em uma pasta vazia, sem alterar a instalação atual."""
from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import zipfile


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
    return restored


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', type=Path, default=Path.cwd() / 'restauracao-cortes-local')
    args = parser.parse_args()
    count = restore(Path(__file__).resolve().parent, args.destino)
    print(f'{count} arquivos restaurados e conferidos em {args.destino.resolve()}')
