"""Seleção local de candidatos, sem chamadas a serviços externos."""

import collections
import math
import re


REACTIONS = re.compile(
    r"\b(oh my god|what the|wait|really|no way|bro|damn|fuck|happy|fake|"
    r"meu deus|pera|caramba|mentira|feliz|mano|sério|porra)\b", re.I
)
SETUP = re.compile(
    r"\b(subscribe|turn sub|chat box|let.s watch|ready to watch|"
    r"can i see my screen|inscreva|ativa o sino|vamos assistir)\b", re.I
)
TRANSITION = re.compile(r"\b(let.s finish the trailer|let.s watch|vamos assistir|"
                        r"voltar (ao|pro) trailer)\b", re.I)
PAYOFF = re.compile(
    r"\b(there you go|realized|fake|that.s why|because|not|no|"
    r"agora|entendi|falso|porque|não)\b", re.I
)


def clean_segments(transcript):
    segments = []
    for segment in transcript.get("segments", []):
        start = float(segment["start"])
        end = float(segment["end"])
        text = " ".join(segment.get("text", "").split())
        if text and math.isfinite(start) and math.isfinite(end) and 0 <= start < end:
            segments.append({"start": start, "end": end, "text": text})
    return sorted(segments, key=lambda segment: segment["start"])


def evaluate(window, terms):
    text = " ".join(segment["text"] for segment in window)
    tokens = re.findall(r"\w+", text.lower())
    spoken = sum(segment["end"] - segment["start"] for segment in window)
    gaps = [max(0, right["start"] - left["end"])
            for left, right in zip(window, window[1:])]
    duration = spoken + sum(min(gap, .4) if gap > 2.5 else gap for gap in gaps)
    counts = collections.Counter(tokens)
    repeated = sum(count - 1 for word, count in counts.items() if len(word) > 3)
    questions = text.count("?")
    reactions = len(REACTIONS.findall(text))
    topic_hits = sum(bool(re.search(r"\b" + re.escape(term) + r"\b", text, re.I)) for term in terms)
    ending = bool(re.search(r"[.!?][\"']?$", window[-1]["text"]))
    opening = bool(re.match(r"^(chat|wait|is |are |what |why |how |did |do |i |"
                            r"eu |vocês|você|por que|como|será)", window[0]["text"], re.I))
    score = (
        min(topic_hits, 3) * 7 + min(questions, 3) * 4
        + min(reactions, 5) * 2 + min(repeated, 7)
        + min(len(window), 6) + 5 * ending + 4 * opening
        + 4 * bool(PAYOFF.search(window[-1]["text"]))
        - 6 * window[-1]["text"].endswith("?")
        - 9 * len(SETUP.findall(text))
        - max(0, duration - spoken - 4)
        - abs(duration - 24) * .25
    )
    reasons = []
    if topic_hits:
        reasons.append("termos do tema")
    if questions:
        reasons.append("perguntas")
    if reactions:
        reasons.append("reações verbais")
    if repeated >= 3:
        reasons.append("repetição")
    if ending:
        reasons.append("fim de frase")
    return round(score, 2), reasons


def edit_ranges(window):
    ranges = []
    start = window[0]["start"]
    for left, right in zip(window, window[1:]):
        if right["start"] - left["end"] > 2.5:
            ranges.append([start, round(left["end"] + .2, 3)])
            start = round(right["start"] - .2, 3)
    ranges.append([start, window[-1]["end"]])
    return ranges


def translation_memory(config, segments):
    memory = {}
    for clip in config.get("clips", []):
        selected = [segment for start, end in clip["edit"] for segment in segments
                    if start <= segment["start"] < end]
        if len(selected) == len(clip.get("lines", [])):
            memory.update((segment["start"], line)
                          for segment, line in zip(selected, clip["lines"]))
    return memory


def select_candidates(config, transcript, settings):
    segments = clean_segments(transcript)
    minimum = float(settings.get("minimum_seconds", 12))
    maximum = float(settings.get("maximum_seconds", 40))
    limit = int(settings.get("max_clips", 6))
    if not 0 < minimum <= maximum <= 120 or not 1 <= limit <= 50:
        raise ValueError("Duração ou quantidade inválida na configuração automática")
    terms = [str(term).lower() for term in settings.get("terms", []) if str(term).strip()]
    candidates = []
    for index, first in enumerate(segments):
        window = []
        options = []
        for segment in segments[index:]:
            duration = segment["end"] - first["start"]
            if duration > maximum or TRANSITION.search(segment["text"]):
                break
            window.append(segment)
            edited_duration = sum(end - start for start, end in edit_ranges(window))
            if duration >= minimum and edited_duration >= minimum:
                score, reasons = evaluate(window, terms)
                options.append((score, reasons, list(window)))
        if options:
            candidates.append(max(options, key=lambda option: option[0]))

    accepted = []
    for score, reasons, window in sorted(candidates, key=lambda option: option[0], reverse=True):
        start, end = window[0]["start"], window[-1]["end"]
        if score <= 0 or any(start < other[-1]["end"] + 5 and
                             other[0]["start"] < end + 5 for _, _, other in accepted):
            continue
        accepted.append((score, reasons, window))
        if len(accepted) >= limit:
            break

    memory = translation_memory(config, segments)
    first_id = max((clip["id"] for clip in config.get("clips", [])), default=0) + 1
    clips = []
    for rank, (score, reasons, window) in enumerate(accepted):
        language = transcript.get("language", "original")
        translated = language != "pt" and all(segment["start"] in memory for segment in window)
        lines = [memory[segment["start"]] if translated else segment["text"] for segment in window]
        start, end = window[0]["start"], window[-1]["end"]
        source_text = " ".join(segment["text"] for segment in window)
        title = settings.get("context_title", "REAÇÃO AO VÍDEO ORIGINAL")
        if re.search(r"\b(founded|grandpa|fundou|bisavô)\b", source_text, re.I):
            title = "RELATO DOS PARTICIPANTES"
        elif re.search(r"\b(brazilian|brasileira|brasileiro)\b", source_text, re.I):
            title = "ESPECULAÇÃO DOS PARTICIPANTES"
        elif re.search(r"\b20\d{2}\b", source_text):
            title = "REAÇÃO À DATA DO TRAILER ORIGINAL"
        clips.append({
            "id": first_id + rank,
            "start": round(max(0, start - 1), 3),
            "end": round(min(segments[-1]["end"], end + 1), 3),
            "edit": edit_ranges(window),
            "title": title,
            "lines": lines,
            "subtitle_language": "pt" if translated else language,
            "translation_status": "reutilizada" if translated else
                                  ("original" if language == "pt" else "revisar tradução"),
            "selection": {"method": "heurística local", "score": score,
                          "reasons": reasons, "review_status": "candidato"},
        })
    return {"url": config["url"], "transcript": config["transcript"], "clips": clips}
