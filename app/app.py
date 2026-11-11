"""Painel local de produção e revisão de cortes."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import mimetypes
import os
from pathlib import Path
import re
import threading
import urllib.parse
import zipfile

import pipeline
import storage

ROOT = Path(__file__).resolve().parent
TOOL_PATHS = json.loads((ROOT / "tools.json").read_text(encoding="utf-8-sig"))
os.environ["PATH"] = os.pathsep.join(dict.fromkeys(
    [str(Path(path).parent) for path in TOOL_PATHS.values()] + [os.environ.get("PATH", "")]))
PORT = 3781
logging.basicConfig(filename=ROOT / "data/aplicativo.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s", encoding="utf8")
MANAGER = pipeline.Pipeline()
BUNDLE_LOCK = threading.Lock()


def validate_options(data):
    topic = str(data.get("topic", "GTA 6")).strip()
    if not 2 <= len(topic) <= 120:
        raise ValueError("Informe um tema entre 2 e 120 caracteres")
    options = {"topic": topic, "max_sources": int(data.get("max_sources", 1)),
               "max_clips": int(data.get("max_clips", 4)),
               "max_duration_minutes": int(data.get("max_duration_minutes", 30)),
               "whisper_model": data.get("whisper_model", "base")}
    if not 1 <= options["max_sources"] <= 3 or not 1 <= options["max_clips"] <= 10:
        raise ValueError("Escolha até 3 vídeos e até 10 candidatos por vídeo")
    if not 2 <= options["max_duration_minutes"] <= 120:
        raise ValueError("A duração máxima deve ficar entre 2 e 120 minutos")
    if options["whisper_model"] not in {"base", "large-v3-turbo"}:
        raise ValueError("Modelo de transcrição inválido")
    url = str(data.get("source_url", "")).strip()
    if url:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}:
            raise ValueError("Use um link HTTPS do YouTube")
        identifier = parsed.path.strip("/") if parsed.hostname == "youtu.be" else urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", identifier):
            raise ValueError("O link deve apontar para um vídeo do YouTube")
        options["source_url"] = f"https://www.youtube.com/watch?v={identifier}"
    return options


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        logging.info(format, *args)

    def json(self, value, status=200):
        payload = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def allowed(self):
        hosts = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        origin = self.headers.get("Origin")
        return self.headers.get("Host") in hosts and (not origin or origin in {"http://" + host for host in hosts})

    def media_file(self, job, relative):
        permitted = {clip["media"] for clip in job.get("clips", [])}
        permitted.update(cover for clip in job.get("clips", []) for cover in clip.get("covers", []))
        if relative not in permitted:
            raise KeyError("Arquivo não encontrado")
        root = (storage.DATA / job["id"]).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise KeyError("Arquivo não encontrado")
        return path

    def send_file(self, path, attachment=None):
        size = path.stat().st_size
        start, end = 0, size - 1
        partial = self.headers.get("Range")
        if partial:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", partial)
            if not match:
                self.json({"error": "Intervalo inválido"}, 416)
                return
            if match[1]:
                start = int(match[1])
                end = min(int(match[2]), end) if match[2] else end
            elif match[2]:
                start = max(0, size - int(match[2]))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()
        with path.open("rb") as stream:
            stream.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = stream.read(min(256 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self):
        if not self.allowed():
            self.json({"error": "Origem não permitida"}, 403)
            return
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        parts = path.strip("/").split("/")
        try:
            if path == "/api/health":
                self.json({"status": "ok", "app": "cortes-local", "version": "1.0.0"})
            elif path == "/api/system":
                self.json({"local_model_ready": (ROOT / "models/argos/translate-en_pt-1_9/model/model.bin").exists(),
                           "research_provider": "YouTube · yt-dlp", "paid_services": False,
                           "active_job": MANAGER.active, "default_topic": "GTA 6"})
            elif path == "/api/jobs":
                self.json(storage.jobs())
            elif len(parts) == 3 and parts[:2] == ["api", "jobs"]:
                self.json(storage.get(parts[2]))
            elif parts[0] == "media" and len(parts) > 2:
                job = storage.get(parts[1])
                file = self.media_file(job, "/".join(parts[2:]))
                self.send_file(file)
            elif len(parts) == 4 and parts[:2] == ["api", "bundle"]:
                self.bundle(parts[2], parts[3])
            else:
                relative = path.lstrip("/") or "index.html"
                static_root = (ROOT / "frontend/dist").resolve()
                target = (static_root / relative).resolve()
                if not target.is_relative_to(static_root):
                    raise KeyError("Arquivo não encontrado")
                if not target.is_file():
                    target = static_root / "index.html"
                self.send_file(target)
        except KeyError as error:
            self.json({"error": str(error)}, 404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception:
            logging.exception("Falha HTTP GET")
            self.json({"error": "Falha ao abrir o recurso"}, 500)

    def bundle(self, identifier, clip_id):
        with BUNDLE_LOCK:
            self.write_bundle(identifier, clip_id)

    def write_bundle(self, identifier, clip_id):
        job = storage.get(identifier)
        clip = next((item for item in job["clips"] if item["id"] == clip_id), None)
        if clip is None:
            raise KeyError("Corte não encontrado")
        target = storage.DATA / identifier / f"pacote-{clip_id}.zip"
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.write(self.media_file(job, clip["media"]), "video.mp4")
            for index, cover in enumerate(clip["covers"]):
                archive.write(self.media_file(job, cover), f"capa-{index+1}.jpg")
            text = (clip["title"] + "\n\n" + clip["description"] + "\n\n"
                    + ", ".join(clip["tags"]) + "\n\nHook\n" + clip["hook"])
            archive.writestr("publicacao.txt", text)
            archive.writestr("dados-e-referencias.json", json.dumps(clip, ensure_ascii=False, indent=2))
        self.send_file(target, attachment=f"corte-{clip_id}.zip")

    def do_POST(self):
        if not self.allowed() or self.headers.get("X-Cortes-Local") != "1":
            self.json({"error": "Origem não permitida"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 <= length <= 100_000:
                raise ValueError("Requisição muito grande")
            body = json.loads(self.rfile.read(length) or b"{}")
            parts = urllib.parse.urlparse(self.path).path.strip("/").split("/")
            if parts == ["api", "jobs"]:
                job = storage.create(validate_options(body))
                MANAGER.submit(job["id"])
                self.json(job, 201)
            elif len(parts) == 4 and parts[:2] == ["api", "jobs"]:
                job = storage.get(parts[2])
                action = parts[3]
                if action == "resume":
                    MANAGER.submit(job["id"])
                elif action == "cancel":
                    MANAGER.cancel(job["id"])
                elif action == "open":
                    os.startfile(storage.DATA / job["id"])
                else:
                    raise ValueError("Ação inválida")
                self.json(storage.get(job["id"]))
            elif len(parts) == 5 and parts[:2] == ["api", "clips"]:
                with storage.LOCK:
                    job = storage.get(parts[2])
                    clip = next(item for item in job["clips"] if item["id"] == parts[3])
                    if parts[4] == "review":
                        if body.get("status") not in {"review", "approved", "rejected"}:
                            raise ValueError("Status inválido")
                        clip["status"] = body["status"]
                    elif parts[4] == "save":
                        for key in ["title", "hook", "description", "cover_prompt"]:
                            if key in body:
                                clip[key] = str(body[key])[:6000]
                                clip["text_edited"] = True
                        if "tags" in body:
                            clip["tags"] = [str(tag)[:60] for tag in body["tags"]][:20]
                        if "selected_cover" in body:
                            selected = int(body["selected_cover"])
                            if not 0 <= selected < len(clip["covers"]):
                                raise ValueError("Capa inválida")
                            clip["selected_cover"] = selected
                    else:
                        raise ValueError("Ação inválida")
                    storage.save(job)
                self.json(clip)
            else:
                raise KeyError("Rota não encontrada")
        except (ValueError, TypeError, StopIteration) as error:
            self.json({"error": str(error) or "Dados inválidos"}, 400)
        except KeyError as error:
            self.json({"error": str(error)}, 404)
        except Exception:
            logging.exception("Falha HTTP POST")
            self.json({"error": "Falha ao executar a ação"}, 500)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    logging.info("Cortes Local em http://127.0.0.1:%s", PORT)
    server.serve_forever()
