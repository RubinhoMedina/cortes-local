"""Enquadramento por cenas amostradas, com detecção local e cache em disco."""

import hashlib
import json
import math
from pathlib import Path
import subprocess
import time


def sample_frames(source, detector, clip):
    import cv2
    import mediapipe as mp
    import numpy as np

    command = ["ffmpeg", "-v", "error", "-threads", "2", "-i", str(source),
               "-an", "-vf", "fps=1/2,scale=640:360", "-threads", "2",
               "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    samples = []
    size = 640 * 360 * 3
    previous = None
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        try:
            index = 0
            while True:
                raw = process.stdout.read(size)
                if not raw:
                    break
                if len(raw) != size:
                    raise ValueError("Amostra de vídeo incompleta")
                frame = np.frombuffer(raw, dtype=np.uint8).reshape(360, 640, 3)
                # fps=1/2 selects frames near the middle of each two-second bucket.
                timestamp = min(clip["end"] - clip["start"] - .001, 1 + index * 2)
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                small = cv2.resize(gray, (64, 36)).astype(np.float32)
                change = float(np.mean(np.abs(small - previous)) / 255) if previous is not None else 0
                previous = small
                # Detect inside the reaction area so the trailer's larger faces do not
                # suppress the participants in the short-range detector.
                reaction_area = frame[150:360, :400].copy()
                result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=reaction_area))
                boxes = []
                for detection in result.detections:
                    box = detection.bounding_box
                    x, y, width, height = [value * 3 for value in
                                          (box.origin_x, box.origin_y + 150, box.width, box.height)]
                    # Persistent lower-corner faces are possible reaction overlays.
                    if (x + width / 2 < 1100 and y + height / 2 > 500
                            and 40 <= width <= 420):
                        boxes.append([x, y, width, height])
                samples.append({"time": timestamp, "change": change, "faces": boxes})
                index += 1
            if process.wait(timeout=15):
                raise RuntimeError("Falha ao amostrar o vídeo")
        except BaseException:
            process.kill()
            process.wait()
            raise
    return samples


def reaction_crop(samples, base):
    observed = [sample["faces"] for sample in samples if sample["faces"]]
    if len(observed) < max(2, math.ceil(len(samples) * .6)):
        return list(base), "enquadramento-base por evidência insuficiente"
    boxes = [box for faces in observed for box in faces]
    # Include both participants and their gestures, using all observations in the scene.
    left = min(box[0] for box in boxes)
    right = max(box[0] + box[2] for box in boxes)
    top = min(box[1] for box in boxes)
    head = max(box[3] for box in boxes)
    x = max(0, int(left - head * .65))
    y = max(400, min(540, int(top - head * .6)))
    height = 1080 - y
    width = max(840, height, int(right - x + head * .8))
    if width > 1200:
        return list(base), "enquadramento-base para preservar contexto amplo"
    x = min(x, 1920 - width)
    crop = [width, height, x, y]
    crop = [int(value) // 2 * 2 for value in crop]
    return crop, "união das regiões dos participantes detectados"


def plan_from_samples(samples, clip):
    base = clip.get("reaction_crop", [840, 600, 0, 480])
    scene_crop = clip.get("scene_crop", [1600, 900, 160, 75])
    plan = []
    offset = 0.0
    for absolute_start, absolute_end in clip["edit"]:
        start, end = absolute_start - clip["start"], absolute_end - clip["start"]
        available = [sample for sample in samples if start <= sample["time"] < end]
        cuts = [start]
        for sample in available:
            if sample["change"] >= .18 and sample["time"] - cuts[-1] >= 4 and end - sample["time"] >= 4:
                cuts.append(sample["time"])
        cuts.append(end)
        # Bound filter-graph size on long clips and stabilize short flashes.
        if len(cuts) > 6:
            cuts = [start, end]
        for begin, finish in zip(cuts, cuts[1:]):
            group = [sample for sample in available if begin <= sample["time"] < finish]
            crop, reason = reaction_crop(group, base)
            plan.append({"start": round(offset + begin - start, 6),
                         "end": round(offset + finish - start, 6),
                         "reaction_crop": crop, "scene_crop": scene_crop,
                         "reason": reason, "samples": len(group)})
        offset += end - start
    return plan


def analyze(source, clip, digest):
    started = time.perf_counter()
    model = Path.home() / "edicao-ia" / "face.tflite"
    signature = {"source": digest(source), "edit": clip["edit"],
                 "start": clip["start"], "end": clip["end"],
                 "reaction_crop": clip.get("reaction_crop"),
                 "scene_crop": clip.get("scene_crop"),
                 "analyzer": digest(Path(__file__)), "model": digest(model)}
    key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:24]
    cache = Path("analise") / f"cenas-{key}.json"
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf8"))
            if data["signature"] == signature and data["scenes"]:
                return data["scenes"], {"cached": True, "seconds": time.perf_counter() - started}
        except (ValueError, KeyError):
            pass

    import cv2
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    cv2.setNumThreads(1)
    options = vision.FaceDetectorOptions(
        base_options=python.BaseOptions(model_asset_path=str(model)),
        min_detection_confidence=.45,
    )
    with vision.FaceDetector.create_from_options(options) as detector:
        samples = sample_frames(source, detector, clip)
    scenes = plan_from_samples(samples, clip)
    data = {"signature": signature, "scenes": scenes, "sample_count": len(samples),
            "analysis_seconds": round(time.perf_counter() - started, 3)}
    cache.parent.mkdir(exist_ok=True)
    pending = cache.with_suffix(".tmp")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")
    pending.replace(cache)
    return scenes, {"cached": False, "seconds": time.perf_counter() - started,
                    "samples": len(samples)}


def render(source, clip, ass, pending, run, ffmpeg):
    filters = []
    pads = []
    for index, (start, end) in enumerate(clip["edit"]):
        begin, finish = start - clip["start"], end - clip["start"]
        filters.extend([
            f"[0:v]trim=start={begin}:end={finish},setpts=PTS-STARTPTS[v{index}]",
            f"[0:a]atrim=start={begin}:end={finish},asetpts=PTS-STARTPTS,"
            f"afade=d=0.008,afade=t=out:st={end-start-.008:.6f}:d=0.008[a{index}]",
        ])
        pads.append(f"[v{index}][a{index}]")
    filters.append("".join(pads) + f"concat=n={len(pads)}:v=1:a=1[cut][audio]")
    scenes = clip["scene_plan"]
    branches = "".join(f"[branch{i}]" for i in range(len(scenes)))
    filters.append(f"[cut]fps=30,scale=1920:1080,setsar=1,split={len(scenes)}{branches}")
    for index, scene in enumerate(scenes):
        first_frame = round(scene["start"] * 30)
        last_frame = round(scene["end"] * 30)
        top = ":".join(map(str, scene["scene_crop"]))
        bottom = ":".join(map(str, scene["reaction_crop"]))
        filters.extend([
            f"[branch{index}]trim=start_frame={first_frame}:end_frame={last_frame},"
            f"setpts=PTS-STARTPTS,split=2[game{index}][people{index}]",
            f"[game{index}]crop={top},scale=720:-2,pad=720:560:0:(oh-ih)/2[top{index}]",
            f"[people{index}]crop={bottom},scale=720:-2,pad=720:720:0:(oh-ih)/2[bottom{index}]",
            f"[top{index}][bottom{index}]vstack[scene{index}]",
        ])
    filters.append("".join(f"[scene{i}]" for i in range(len(scenes)))
                   + f"concat=n={len(scenes)}:v=1:a=0,fps=30,setsar=1,ass={ass.name}[video]")
    run(ffmpeg + ["-y", "-threads", "2", "-i", str(source), "-filter_complex_threads", "2",
                  "-filter_complex", ";".join(filters), "-map", "[video]", "-map", "[audio]",
                  "-c:v", "libx264", "-threads", "2", "-preset", "veryfast", "-crf", "20",
                  "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                  "-movflags", "+faststart", str(pending)])
