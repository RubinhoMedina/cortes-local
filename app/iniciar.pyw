"""Abre o painel local; reutiliza o servidor quando já está aberto."""
from pathlib import Path
import json
import subprocess
import time
import urllib.request
import webbrowser
import ctypes

ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:3781"

def available():
    try:
        with urllib.request.urlopen(URL + "/api/health", timeout=2) as response:
            return response.status == 200 and json.load(response).get("app") == "cortes-local"
    except OSError:
        return False

if not available():
    log = (ROOT / "data/inicializacao.log").open("ab")
    subprocess.Popen([str(ROOT.parent / ".venv/Scripts/pythonw.exe"), "-X", "utf8", str(ROOT / "app.py")],
                     cwd=ROOT, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    for attempt in range(30):
        if available():
            break
        time.sleep(1)

if available():
    webbrowser.open(URL)
else:
    ctypes.windll.user32.MessageBoxW(0, "Não foi possível abrir o painel. Consulte data/inicializacao.log.", "Cortes Local", 16)
