"""Fila local de pesquisa, transcrição, seleção, renderização e revisão."""

import hashlib
import importlib.util
import json
import logging
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time

import local_text
import research
import reference_analysis
import storage

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT.parent / ".venv/Scripts/python.exe"
LEGACY = Path.home() / "cortes-trabalho/001-E07OTlhncP0"


class Cancelled(Exception):
    pass


def atomic_json(path, data):
    pending = path.with_suffix(".tmp")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")
    pending.replace(path)


def load_selector():
    spec = importlib.util.spec_from_file_location("local_selector", LEGACY / "selecao.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Pipeline:
    def __init__(self):
        self.queue = queue.Queue()
        self.cancelled = set()
        self.scheduled = set()
        self.lock = threading.RLock()
        self.active = None
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()
        for job in storage.jobs():
            if job["status"] in {"queued", "processing"}:
                storage.update(job["id"], status="interrupted", message="Processamento interrompido. Retome para continuar.")

    def submit(self, identifier):
        with self.lock:
            if identifier in self.scheduled or self.active == identifier:
                raise ValueError("Este lote já está na fila")
            self.cancelled.discard(identifier)
            self.scheduled.add(identifier)
            storage.update(identifier, status="queued", error=None, message="Na fila de processamento")
            self.queue.put(identifier)

    def cancel(self, identifier):
        with self.lock:
            self.cancelled.add(identifier)
        storage.update(identifier, message="Cancelamento solicitado")

    def check(self, identifier):
        if identifier in self.cancelled:
            raise Cancelled()

    def run(self, identifier, command, directory, capture=False, timeout=180):
        self.check(identifier)
        output = directory / ("command-output.json" if capture else "processamento.log")
        started = time.monotonic()
        with output.open("wb" if capture else "ab") as log:
            with (directory / "diagnostico.log").open("ab") as errors:
                process = subprocess.Popen([str(value) for value in command], cwd=directory,
                                           stdout=log, stderr=errors,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    while process.poll() is None:
                        self.check(identifier)
                        if time.monotonic() - started > timeout:
                            raise RuntimeError(f"Tempo excedido em {Path(str(command[0])).name}")
                        time.sleep(.4)
                    if process.returncode:
                        raise RuntimeError(f"Falha em {Path(str(command[0])).name}. Consulte o diagnóstico do lote.")
                except BaseException:
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise
        return output.read_text(encoding="utf-8-sig") if capture else None

    def worker(self):
        while True:
            identifier = self.queue.get()
            with self.lock:
                self.scheduled.discard(identifier)
                self.active = identifier
            try:
                self.check(identifier)
                storage.update(identifier, status="processing")
                self.process(identifier)
            except Cancelled:
                storage.update(identifier, status="cancelled", message="Lote cancelado. Arquivos disponíveis para retomada.")
            except Exception as error:
                logging.exception("Falha no lote %s", identifier)
                storage.update(identifier, status="error", error=str(error), message=str(error))
            finally:
                self.active = None
                self.queue.task_done()

    def transcript(self, identifier, video, directory, runner):
        transcript_path = directory / "audio.json"
        if transcript_path.exists():
            return json.loads(transcript_path.read_text(encoding="utf8"))
        if video["id"] == "E07OTlhncP0" and (LEGACY / "audio.json").exists():
            shutil.copy2(LEGACY / "audio.json", transcript_path)
            return json.loads(transcript_path.read_text(encoding="utf8"))

        # Public YouTube captions avoid repeating CPU-heavy speech recognition.
        try:
            runner(["yt-dlp", "--skip-download", "--write-subs", "--write-auto-subs",
                    "--sub-langs", "pt,en", "--sub-format", "json3", "--no-playlist",
                    "-o", "captions.%(ext)s", video["url"]], directory, timeout=180)
        except RuntimeError:
            pass
        for path in sorted(directory.glob("captions.*.json3"), key=lambda p: ".pt." not in p.name):
            try:
                payload = json.loads(path.read_text(encoding="utf8"))
                segments = []
                for event in payload.get("events", []):
                    text = " ".join("".join(part.get("utf8", "") for part in event.get("segs", [])).split())
                    start = event.get("tStartMs", 0) / 1000
                    end = start + event.get("dDurationMs", 0) / 1000
                    if text and end > start:
                        segments.append({"start": start, "end": end, "text": text})
                if segments:
                    result = {"language": "pt" if ".pt." in path.name else "en", "segments": segments,
                              "provider": "legendas públicas do YouTube"}
                    atomic_json(transcript_path, result)
                    return result
            except (ValueError, TypeError):
                continue

        runner(["yt-dlp", "--no-playlist", "-f", "bestaudio/best", "-o", "audio.%(ext)s", video["url"]],
               directory, timeout=1200)
        audio_files = [path for path in directory.glob("audio.*") if path.suffix in {".m4a", ".webm", ".mp3", ".mp4", ".opus"}]
        if not audio_files:
            raise RuntimeError("O download do áudio não produziu um arquivo utilizável")
        model = storage.get(identifier)["options"].get("whisper_model", "base")
        runner([PYTHON, "-X", "utf8", ROOT / "transcribe.py", audio_files[0], transcript_path, model],
               directory, timeout=6 * 3600)
        return json.loads(transcript_path.read_text(encoding="utf8"))

    def source_catalog(self, video):
        if video["id"] != "E07OTlhncP0":
            return []
        sources = [{"path": str(LEGACY / "piloto-fonte.mp4"), "start": 918, "end": 957}]
        config = json.loads((LEGACY / "lote.json").read_text(encoding="utf8"))
        for clip in config["clips"]:
            key = hashlib.sha256(json.dumps([config["url"], clip["start"], clip["end"]]).encode()).hexdigest()[:16]
            path = LEGACY / "fontes" / f"{key}.mp4"
            if path.exists():
                sources.append({"path": str(path), "start": clip["start"], "end": clip["end"]})
        return sources

    def covers(self, identifier, clip, directory, runner):
        output = []
        signature = hashlib.sha256(Path(clip["file"]).read_bytes()).hexdigest()[:10]
        for index, fraction in enumerate([.18, .48, .78]):
            path = directory / f"cover-{clip['id']}-{signature}-{index}.jpg"
            if not path.exists():
                runner(["ffmpeg", "-v", "error", "-y", "-ss", str(clip["duration"] * fraction),
                        "-i", clip["file"], "-frames:v", "1", "-vf", "scale=720:1280", path], directory)
            output.append(str(path.relative_to(storage.DATA / identifier)).replace("\\", "/"))
        return output

    def process(self, identifier):
        job = storage.get(identifier)
        options = job["options"]
        directory = storage.DATA / identifier
        runner = lambda command, cwd, **kwargs: self.run(identifier, command, cwd, **kwargs)
        notify = lambda stage, progress, message: storage.event(identifier, stage, progress, message)
        research_file = directory / "pesquisa.json"
        if research_file.exists():
            evidence = json.loads(research_file.read_text(encoding="utf8"))
        else:
            sources, references, sample = research.discover(options, runner, directory, notify)
            evidence = {"sources": sources, "references": references, "sample": sample}
            atomic_json(research_file, evidence)
        sources = evidence["sources"]
        references = reference_analysis.analyze(evidence["references"], runner, notify)
        storage.update(identifier, sources=sources, references=references, research_sample=evidence["sample"])
        selector = load_selector()
        completed = {clip["id"]: clip for clip in job.get("clips", [])}
        errors = []
        for position, video in enumerate(sources):
            self.check(identifier)
            source_dir = directory / video["id"]
            source_dir.mkdir(exist_ok=True)
            progress = 18 + int(position / len(sources) * 65)
            notify("transcript", progress, f"Preparando a transcrição de {video['channel']}")
            try:
                transcript = self.transcript(identifier, video, source_dir, runner)
                original = {"url": video["url"], "transcript": "audio.json", "clips": []}
                if video["id"] == "E07OTlhncP0":
                    original = json.loads((LEGACY / "lote.json").read_text(encoding="utf8"))
                settings = {"minimum_seconds": 12, "maximum_seconds": 40,
                            "max_clips": options["max_clips"],
                            "terms": re.findall(r"\w+", options["topic"].lower()) + ["game", "jogo", "lucia", "franklin", "michael"]}
                selected = selector.select_candidates(original, transcript, settings)
                if not selected["clips"]:
                    raise RuntimeError("A transcrição não ofereceu candidatos com duração e contexto suficientes")
                best = max(clip["selection"]["score"] for clip in selected["clips"])
                selected["clips"] = [clip for clip in selected["clips"] if clip["selection"]["score"] >= best * .75]
                selected["sources"] = self.source_catalog(video)
                for filename in ["executor.py", "fluxo.py", "selecao.py", "enquadramento.py", "piloto-legendas.ass"]:
                    target = source_dir / filename
                    if not target.exists() or target.read_bytes() != (LEGACY / filename).read_bytes():
                        shutil.copy2(LEGACY / filename, target)
                prepared = []
                for clip in selected["clips"]:
                    self.check(identifier)
                    clip_id = video["id"] + "-" + str(clip["id"])
                    notify("packaging", progress + 12, f"Preparando hook, legenda e descrição do corte {len(prepared) + 1}")
                    metadata_path = source_dir / f"publicacao-{clip['id']}.json"
                    input_sha = hashlib.sha256(json.dumps([clip["lines"], clip["subtitle_language"], options["topic"],
                                                          local_text.PACKAGE_VERSION,
                                                          [ref.get("opening_analysis") for ref in references]], ensure_ascii=False).encode()).hexdigest()
                    package = json.loads(metadata_path.read_text(encoding="utf8")) if metadata_path.exists() else None
                    if not package or package.get("input_sha256") != input_sha:
                        package = local_text.package(options["topic"], clip["lines"], references,
                                                     clip["subtitle_language"], video["title"])
                        self.check(identifier)
                        package["input_sha256"] = input_sha
                        atomic_json(metadata_path, package)
                    if package["editorial_score"] < 50:
                        continue
                    clip["lines"] = package["translations"]
                    clip["subtitle_language"] = "pt"
                    clip["translation_status"] = "modelo local — revisar"
                    clip["title"] = package["hook"][:80]
                    prepared.append(clip)
                if not prepared:
                    raise RuntimeError("Os candidatos ficaram abaixo do limiar editorial de seleção")
                selected["clips"] = prepared
                atomic_json(source_dir / "lote.json", selected)
                notify("render", progress + 25, f"Editando {len(prepared)} cortes de {video['channel']}")
                try:
                    runner([PYTHON, "-X", "utf8", "fluxo.py", "--config", "lote.json", "--auto-frame", "--no-open"],
                           source_dir, timeout=4 * 3600)
                except RuntimeError as error:
                    errors.append(f"{video['channel']}: {error}")
                report_path = source_dir / "analise/ultima-execucao.json"
                report = json.loads(report_path.read_text(encoding="utf8")) if report_path.exists() else {"clips": []}
                valid_ids = {item["id"] for item in report["clips"] if item["status"] in {"validado", "reutilizado"}}
                for clip in prepared:
                    clip_id = video["id"] + "-" + str(clip["id"])
                    output = source_dir / "revisao-automatica" / f"auto-corte{clip['id']:02}.mp4"
                    if clip["id"] not in valid_ids or not output.exists():
                        continue
                    package = json.loads((source_dir / f"publicacao-{clip['id']}.json").read_text(encoding="utf8"))
                    result = {"id": clip_id, "title": package["title"], "hook": package["hook"],
                              "description": package["description"] + f"\n\nFonte: {video['channel']} — {video['url']}",
                              "tags": package["tags"],
                              "score": round(.7 * min(100, max(0, clip["selection"]["score"] * 1.4)) + .3 * package["editorial_score"]),
                              "reason": "Seleção do momento: " + ", ".join(clip["selection"]["reasons"]) + ". " + package["reason"],
                              "cover_prompt": package["cover_prompt"],
                              "method": package["method"], "source_id": video["id"],
                              "reference_pattern": package["reference_pattern"],
                              "source_title": video["title"], "source_channel": video["channel"],
                              "source_url": video["url"], "research_score": video.get("research_score"),
                              "duration": round(sum(end - start for start, end in clip["edit"]), 2),
                              "file": str(output), "media": str(output.relative_to(directory)).replace("\\", "/"),
                              "subtitle_language": "pt", "status": "review", "selected_cover": 0,
                              "references": references[:3], "source_ranges": clip["edit"]}
                    result["covers"] = self.covers(identifier, result, source_dir, runner)
                    if clip_id in completed and completed[clip_id].get("source_ranges") == clip["edit"]:
                        previous = completed[clip_id]
                        result.update({key: previous[key] for key in ["status", "selected_cover"]})
                        if previous.get("text_edited"):
                            result.update({key: previous[key] for key in
                                           ["title", "description", "tags", "text_edited"]})
                    completed[clip_id] = result
                    storage.update(identifier, clips=sorted(completed.values(), key=lambda item: item["score"], reverse=True))
            except Cancelled:
                raise
            except Exception as error:
                self.check(identifier)
                logging.exception("Fonte com falha %s", video["id"])
                errors.append(f"{video['channel']}: {error}")
                storage.update(identifier, warnings=errors)
        if not completed:
            raise RuntimeError("; ".join(errors) or "O lote não produziu cortes suficientes para revisão")
        notify("review", 100, f"{len(completed)} cortes prontos para sua revisão")
        storage.update(identifier, status="ready", clips=sorted(completed.values(), key=lambda item: item["score"], reverse=True),
                       warnings=errors)
