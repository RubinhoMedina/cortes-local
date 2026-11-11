"""Modo automático local que reutiliza o executor validado do projeto."""

import argparse
import copy
import hashlib
import json
import logging
import msvcrt
import os
from pathlib import Path
import subprocess
import time

import executor
from selecao import clean_segments, select_candidates


ROOT = Path(__file__).resolve().parent


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    pending.replace(path)


def prepare_config(config, transcript, settings):
    signature = {"config": config, "transcript_sha256": executor.digest(Path(config["transcript"])),
                 "settings": settings, "selector_sha256": executor.digest(ROOT / "selecao.py")}
    path = Path("analise/lote-automatico.json")
    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf8"))
            if previous.get("selection_signature") == signature:
                return previous
        except ValueError:
            pass
    selected = select_candidates(config, transcript, settings)
    selected["sources"] = list(settings.get("sources", []))
    for clip in config.get("clips", []):
        identity = json.dumps([config["url"], clip["start"], clip["end"]])
        key = hashlib.sha256(identity.encode()).hexdigest()[:16]
        source = Path("fontes") / f"{key}.mp4"
        if source.exists():
            selected["sources"].append({"path": str(source), "start": clip["start"], "end": clip["end"]})
    selected["selection_signature"] = signature
    write_json(path, selected)
    return selected


def resolve_source(config, clip):
    for source in sorted(config.get("sources", []), key=lambda item: item["end"] - item["start"]):
        path = Path(source["path"])
        if (source["start"] <= clip["start"] and clip["end"] <= source["end"] and path.exists()):
            try:
                executor.probe(path, source["end"] - source["start"])
                signature = {"sha256": executor.digest(path), "duration": source["end"] - source["start"]}
                validation = Path("analise") / f"fonte-{signature['sha256'][:24]}.json"
                try:
                    previous = json.loads(validation.read_text(encoding="utf8")) if validation.exists() else None
                except ValueError:
                    previous = None
                if previous != signature:
                    executor.decode(path)
                    write_json(validation, signature)
            except (ValueError, OSError, subprocess.SubprocessError, StopIteration):
                continue
            clip["requested_window"] = [clip["start"], clip["end"]]
            clip["start"], clip["end"] = source["start"], source["end"]
            logging.info("Fonte local reutilizada: %s", path)
            return path
    source = executor.source_for(config, clip, f"corte{clip['id']:02}")
    signature = {"sha256": executor.digest(source), "duration": clip["end"] - clip["start"]}
    write_json(Path("analise") / f"fonte-{signature['sha256'][:24]}.json", signature)
    return source


def process_clip(config, original, segments, auto_frame):
    started = time.perf_counter()
    clip = copy.deepcopy(original)
    name = f"auto-corte{clip['id']:02}"
    duration = sum(end - start for start, end in clip["edit"])
    if not clip["edit"] or any(not clip["start"] <= start < end <= clip["end"]
                               for start, end in clip["edit"]):
        raise ValueError(f"{name}: intervalos fora da janela da fonte")
    source = resolve_source(config, clip)
    timings = {"source_seconds": round(time.perf_counter() - started, 3)}
    analysis = {"status": "layout configurado"}
    if auto_frame and clip.get("layout", "split") == "split":
        import enquadramento
        phase = time.perf_counter()
        try:
            clip["scene_plan"], analysis = enquadramento.analyze(source, clip, executor.digest)
        except (ImportError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            # Optional image analysis can fail while the configured layout remains usable.
            logging.warning("%s: análise de imagem indisponível: %s", name, error)
            analysis = {"status": "layout configurado", "reason": str(error)}
        timings["analysis_seconds"] = round(time.perf_counter() - phase, 3)
    ass = executor.subtitles(clip, segments, name)
    output = Path("revisao-automatica") / f"{name}.mp4"
    receipt = output.with_suffix(".json")
    signature = {
        "url": config["url"], "clip": clip, "source_sha256": executor.digest(source),
        "ass_sha256": executor.digest(ass), "executor_sha256": executor.digest(ROOT / "executor.py"),
        "flow_sha256": executor.digest(Path(__file__)),
    }
    if clip.get("scene_plan"):
        signature["framing_sha256"] = executor.digest(ROOT / "enquadramento.py")
    if output.exists() and receipt.exists():
        try:
            previous = json.loads(receipt.read_text(encoding="utf8"))
            if (previous.get("signature") == signature
                    and previous.get("export_sha256") == executor.digest(output)):
                executor.probe(output, duration, export=True)
                logging.info("%s reutilizado", output)
                return {"id": clip["id"], "status": "reutilizado", "analysis": analysis,
                        "total_seconds": round(time.perf_counter() - started, 3), **timings}
        except (ValueError, KeyError):
            pass
    pending = output.with_suffix(".render.mp4")
    phase = time.perf_counter()
    if clip.get("scene_plan"):
        enquadramento.render(source, clip, ass, pending, executor.run, executor.FF)
    else:
        executor.render(source, clip, ass, pending)
    timings["render_seconds"] = round(time.perf_counter() - phase, 3)
    phase = time.perf_counter()
    executor.probe(pending, duration, export=True)
    executor.decode(pending)
    timings["validation_seconds"] = round(time.perf_counter() - phase, 3)
    pending.replace(output)
    write_json(receipt, {"signature": signature, "export_sha256": executor.digest(output),
                         "analysis": analysis, "timings": timings})
    logging.info("%s validado, duração %.2fs", output, duration)
    return {"id": clip["id"], "status": "validado", "analysis": analysis,
            "total_seconds": round(time.perf_counter() - started, 3), **timings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="lote.json")
    parser.add_argument("--settings", default="automacao.json")
    parser.add_argument("--auto-select", action="store_true")
    parser.add_argument("--auto-frame", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--only", nargs="+", type=int)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler("automatico.log", encoding="utf8"),
                                  logging.StreamHandler()])
    with open("lote.lock", "a+b") as lock:
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            logging.error("Já existe um lote em execução nesta pasta")
            return 1
        config = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
        transcript = json.loads(Path(config["transcript"]).read_text(encoding="utf-8-sig"))
        phase = time.perf_counter()
        if args.auto_select:
            settings = json.loads(Path(args.settings).read_text(encoding="utf-8-sig"))
            config = prepare_config(config, transcript, settings)
        selection_seconds = round(time.perf_counter() - phase, 3)
        clips = [clip for clip in config["clips"] if not args.only or clip["id"] in args.only]
        if not clips:
            raise ValueError("Nenhum candidato corresponde à seleção solicitada")
        logging.info("%d candidatos, seleção %.3fs", len(clips), selection_seconds)
        if args.analyze_only:
            return 0
        Path("revisao-automatica").mkdir(exist_ok=True)
        results = []
        segments = clean_segments(transcript) if any("selection" in clip for clip in clips) else transcript["segments"]
        for clip in clips:
            try:
                results.append(process_clip(config, clip, segments, args.auto_frame))
            except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, StopIteration):
                logging.exception("Falha no candidato %s", clip["id"])
                results.append({"id": clip["id"], "status": "falha"})
        write_json(Path("analise/ultima-execucao.json"),
                   {"selection_seconds": selection_seconds, "clips": results})
        if not args.no_open and any(result["status"] != "falha" for result in results):
            os.startfile(ROOT / "revisao-automatica")
        return int(any(result["status"] == "falha" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
