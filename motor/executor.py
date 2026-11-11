import argparse
import hashlib
import json
import logging
import math
import msvcrt
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
FF = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-xerror"]
FORMAT = "bv*[vcodec^=avc1][height<=1080][fps<=30]+ba[ext=m4a]/bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]"


def run(command):
    logging.info("%s", subprocess.list2cmdline(list(map(str, command))))
    with open("lote.log", "ab") as log:
        subprocess.run(command, check=True, stdout=log, stderr=log)


def probe(path, duration, export=False):
    data = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ], stderr=subprocess.DEVNULL))
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio = next(s for s in data["streams"] if s["codec_type"] == "audio")
    actual = float(data["format"]["duration"])
    if not math.isfinite(actual) or abs(actual - duration) > (0.18 if export else 0.45):
        raise ValueError(f"{path}: duração {actual}, esperada {duration}")
    if export and (video["width"], video["height"], video["avg_frame_rate"],
                   video["codec_name"], audio["codec_name"]) != (720, 1280, "30/1", "h264", "aac"):
        raise ValueError(f"{path}: formato inesperado")


def decode(path):
    run(FF + ["-threads", "2", "-i", str(path), "-map", "0:v:0",
              "-map", "0:a:0", "-f", "null", "-"])


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_for(config, clip, name):
    identity = json.dumps([config["url"], clip["start"], clip["end"]])
    key = hashlib.sha256(identity.encode()).hexdigest()[:16]
    duration = clip["end"] - clip["start"]
    cache = Path("fontes")
    cache.mkdir(exist_ok=True)
    source = cache / f"{key}.mp4"
    if source.exists():
        try:
            probe(source, duration)
            decode(source)
            return source
        except (ValueError, OSError, subprocess.CalledProcessError, StopIteration):
            source.replace(source.with_name(f"{key}-falha-{time.time_ns()}.mp4"))
            logging.warning("Fonte inválida preservada. Baixando novamente: %s", name)
    pending = source.with_suffix(".download.mp4")
    for attempt in range(2):
        try:
            run(["yt-dlp", "--no-playlist", "--download-sections",
                 f"*{clip['start']}-{clip['end']}", "--force-keyframes-at-cuts",
                 "-f", FORMAT, "--merge-output-format", "mp4",
                 "-o", str(pending), config["url"]])
            probe(pending, duration)
            decode(pending)
            pending.replace(source)
            return source
        except (subprocess.CalledProcessError, ValueError, StopIteration):
            if attempt:
                raise
            if pending.exists():
                pending.replace(pending.with_name(f"{pending.stem}-{time.time_ns()}.mp4"))
            time.sleep(4)


def stamp(value):
    centis = round(value * 100)
    minutes, remainder = divmod(centis, 6000)
    hours, minutes = divmod(minutes, 60)
    seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02}:{seconds:02}.{fraction:02}"


def subtitles(clip, segments, name):
    header = Path("piloto-legendas.ass").read_text(encoding="utf-8-sig").split("Dialogue:")[0]
    rows = []
    offset = 0
    for start, end in clip["edit"]:
        for segment in segments:
            if start <= segment["start"] < end:
                rows.append((offset + segment["start"] - start,
                             offset + min(segment["end"], end) - start))
        offset += end - start
    if len(rows) != len(clip["lines"]):
        raise ValueError(f"{name}: {len(rows)} falas para {len(clip['lines'])} legendas")
    caption_y = 880 if clip.get('layout') == 'reaction' else 545
    events = []
    for (start, end), line in zip(rows, clip["lines"], strict=True):
        events.append(f"Dialogue: 0,{stamp(start)},{stamp(end)},Default,,0,0,0,,"
                      + rf"{{\pos(360,{caption_y})\q0}}" + line.upper())
    if clip.get("title"):
        events.append(f"Dialogue: 1,{stamp(0)},{stamp(offset)},Default,,0,0,0,,"
                      + r"{\pos(360,105)\fs29}" + clip["title"])
    ass = Path(f"{name}-legendas.ass")
    ass.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return ass


def render(source, clip, ass, pending):
    filters = []
    pads = []
    for index, (start, end) in enumerate(clip["edit"]):
        begin = start - clip["start"]
        finish = end - clip["start"]
        filters.extend([
            f"[0:v]trim=start={begin}:end={finish},setpts=PTS-STARTPTS[v{index}]",
            f"[0:a]atrim=start={begin}:end={finish},asetpts=PTS-STARTPTS,"
            f"afade=d=0.008,afade=t=out:st={end-start-0.008:.6f}:d=0.008[a{index}]",
        ])
        pads.append(f"[v{index}][a{index}]")
    filters.append("".join(pads) + f"concat=n={len(pads)}:v=1:a=1[cut][audio]")
    layout = clip.get("layout", "split")
    scene_crop = clip.get("scene_crop", [1600, 900, 160, 75])
    reaction_crop = clip.get("reaction_crop", [840, 600, 0, 480])
    scene = ":".join(str(int(value)) for value in scene_crop)
    reaction = ":".join(str(int(value)) for value in reaction_crop)
    if layout == "split":
        filters.extend([
            "[cut]scale=1920:1080,setsar=1,split=2[scene][react]",
            f"[scene]crop={scene},scale=720:-2,pad=720:560:0:(oh-ih)/2[top]",
            f"[react]crop={reaction},scale=720:-2,pad=720:720:0:(oh-ih)/2[bottom]",
            "[top][bottom]vstack[vertical]",
        ])
    elif layout == "reaction":
        filters.append(f"[cut]scale=1920:1080,crop={reaction},scale=720:-2,"
                       "pad=720:1280:0:360[vertical]")
    elif layout == "full":
        filters.append("[cut]scale=720:404,pad=720:1280:0:130[vertical]")
    else:
        raise ValueError(f"layout desconhecido: {layout}")
    filters.append(f"[vertical]fps=30,setsar=1,ass={ass.name}[video]")
    run(FF + ["-y", "-threads", "2", "-i", str(source), "-filter_complex_threads", "2",
              "-filter_complex", ";".join(filters), "-map", "[video]", "-map", "[audio]",
              "-c:v", "libx264", "-threads", "2", "-preset", "veryfast", "-crf", "20",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
              "-movflags", "+faststart", str(pending)])


def process(config, clip, segments):
    name = f"corte{clip['id']:02}"
    duration = sum(end - start for start, end in clip["edit"])
    if not clip["edit"] or any(not clip["start"] <= start < end <= clip["end"]
                               for start, end in clip["edit"]):
        raise ValueError(f"{name}: intervalos editados fora da fonte")
    ass = subtitles(clip, segments, name)
    source = source_for(config, clip, name)
    output = Path("revisao") / f"{name}.mp4"
    receipt = output.with_suffix(".json")
    signature = {
        "url": config["url"], "clip": clip, "source_sha256": digest(source),
        "ass_sha256": digest(ass), "executor_sha256": digest(Path(__file__)),
    }
    if output.exists() and receipt.exists():
        previous = json.loads(receipt.read_text(encoding="utf-8"))
        if previous == {**signature, "export_sha256": digest(output)}:
            probe(output, duration, export=True)
            logging.info("%s já validado", output)
            return
    pending = output.with_suffix(".render.mp4")
    render(source, clip, ass, pending)
    probe(pending, duration, export=True)
    decode(pending)
    pending.replace(output)
    receipt.write_text(json.dumps({**signature, "export_sha256": digest(output)},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("%s validado (%.2f s)", output, duration)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="lote.json")
    parser.add_argument("--only", nargs="+", type=int)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler("lote.log", encoding="utf-8"),
                                  logging.StreamHandler()])
    config = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
    segments = json.loads(Path(config["transcript"]).read_text(encoding="utf-8-sig"))["segments"]
    clips = [clip for clip in config["clips"] if not args.only or clip["id"] in args.only]
    if not clips:
        parser.error("nenhum corte corresponde à seleção")
    Path("revisao").mkdir(exist_ok=True)
    with open("lote.lock", "a+b") as lock:
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            logging.error("Já existe um lote em execução nesta pasta.")
            return 1
        return process_batch(config, clips, segments, args.no_open)


def process_batch(config, clips, segments, no_open):
    failures = []
    for clip in clips:
        try:
            process(config, clip, segments)
        except (ValueError, OSError, subprocess.CalledProcessError, StopIteration):
            logging.exception("Falha no corte %s", clip["id"])
            failures.append(clip["id"])
    if not no_open and len(failures) < len(clips):
        os.startfile(ROOT / "revisao")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())


