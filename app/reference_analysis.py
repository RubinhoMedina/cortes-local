"""Analisa até vinte segundos da abertura de referências públicas, com cache."""
import hashlib
import json
from pathlib import Path
import re

import local_text
import storage

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT.parent / ".venv/Scripts/python.exe"
VERSION = 2


def analyze(references, runner, notify):
    results = []
    for index, reference in enumerate(references):
        item = dict(reference)
        if index >= 3:
            results.append(item)
            continue
        notify("references", 14 + index, f"Analisando a abertura da referência {index + 1} de {min(3, len(references))}")
        folder = storage.DATA / "reference-cache" / item["id"]
        folder.mkdir(parents=True, exist_ok=True)
        cached = folder / "abertura.json"
        try:
            analysis = json.loads(cached.read_text(encoding="utf8")) if cached.exists() else None
            if not analysis or analysis.get("version") != VERSION:
                runner(["yt-dlp", "--no-playlist", "--max-filesize", "40M", "-f", "bestaudio/best",
                        "-o", "referencia.%(ext)s", item["url"]], folder, timeout=180)
                audio = next(path for path in folder.glob("referencia.*") if path.suffix in {".webm", ".m4a", ".mp3", ".mp4", ".opus"})
                sample = folder / "primeiros-20s.wav"
                runner(["ffmpeg", "-v", "error", "-y", "-i", audio, "-t", "20", "-ac", "1", "-ar", "16000", sample], folder)
                transcript_path = folder / "fala.json"
                runner([PYTHON, "-X", "utf8", ROOT / "transcribe.py", sample, transcript_path, "base", "opening"], folder, timeout=120)
                transcript = json.loads(transcript_path.read_text(encoding="utf8"))
                speech = [segment for segment in transcript.get("segments", [])
                          if segment["start"] < 12 and segment.get("no_speech_prob", 0) < .6
                          and segment.get("avg_logprob", 0) > -1]
                # An excerpt is evidence of the opening only, not of the entire Short.
                excerpt = " ".join(" ".join(segment["text"] for segment in speech).split()[:22])
                language = transcript.get("language")
                question = bool(re.search(r"\?|\b(what|why|how|did|is that|are you|por que|como|será|você)\b", excerpt, re.I))
                reaction = bool(re.search(r"\b(oh my|wow|wait|no way|bro|meu deus|caramba|mano|pera)\b", excerpt, re.I))
                pattern = "pergunta" if excerpt and question else "reação verbal" if excerpt and reaction else "afirmação" if excerpt else "sem fala identificada"
                translated = local_text.translate([excerpt], language)[0] if excerpt and language in {"en", "pt"} else excerpt
                analysis = {"version": VERSION, "analyzed_seconds": min(20, item.get("duration") or 20),
                            "excerpt": excerpt, "excerpt_pt": translated, "language": language,
                            "pattern": pattern, "method": "Whisper base local; abertura de áudio, sem análise visual",
                            "audio_sha256": hashlib.sha256(sample.read_bytes()).hexdigest()}
                pending = cached.with_suffix(".tmp")
                pending.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf8")
                pending.replace(cached)
            item["opening_analysis"] = analysis
        except Exception as error:
            # Production can continue when a reference is unavailable.
            item["opening_analysis"] = {"error": str(error), "pattern": "não analisada"}
        results.append(item)
    return results
