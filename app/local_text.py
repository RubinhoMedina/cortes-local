"""Tradução offline e redação rastreável a partir das falas."""
from pathlib import Path
import threading
ROOT = Path(__file__).resolve().parent
PACKAGE_VERSION = 5
LOCK = threading.Lock()
MODEL = None
TOKENIZER = None

def shutdown():
    global MODEL, TOKENIZER
    MODEL = TOKENIZER = None

def translate(lines, language):
    global MODEL, TOKENIZER
    if language == "pt":
        return list(lines)
    if language != "en":
        raise ValueError("A tradução local aceita fontes em inglês ou português")
    import ctranslate2
    import sentencepiece
    import re
    inputs = [re.sub(r"\bshades\b", "sunglasses", line, flags=re.I)
              if re.search(r"wear|wearing", line, re.I) else line for line in lines]
    with LOCK:
        if MODEL is None:
            folder = ROOT / "models/argos/translate-en_pt-1_9"
            TOKENIZER = sentencepiece.SentencePieceProcessor(model_file=str(folder / "sentencepiece.model"))
            MODEL = ctranslate2.Translator(str(folder / "model"), device="cpu", compute_type="int8",
                                          inter_threads=1, intra_threads=2)
        results = MODEL.translate_batch([TOKENIZER.encode(line, out_type=str) for line in inputs],
                                        beam_size=4, replace_unknowns=True, length_penalty=.2)
        translated = [TOKENIZER.decode_pieces(result.hypotheses[0]).replace("▁", " ").replace("_", " ").strip()
                      for result in results]
    for index, original in enumerate(lines):
        if re.search(r"\btrailer\b", original, re.I):
            translated[index] = re.sub(r"\b(caravana|reboque|atrelado)\b", "trailer", translated[index], flags=re.I)
        for expression, replacement in [(r"\bÉs\b", "Você é"),
                                        (r"\bTens\b", "Você tem"), (r"\bFazes\b", "Você faz"),
                                        (r"\bPuseram-me\b", "Me colocaram"), (r"\bIsto\b", "isso")]:
            translated[index] = re.sub(expression, replacement, translated[index], flags=re.I)
    if any(not text for text in translated):
        raise ValueError("A tradução produziu uma fala vazia")
    return translated


def package(topic, lines, references, language, source_title):
    import collections
    import re
    translated = translate(lines, language)
    combined = " ".join(translated)
    names = list(dict.fromkeys(match.group(0).title() for match in
                re.finditer(r"\b(Franklin|Michael|Lester|Lucia|IShowSpeed|Rockstar)\b", combined, re.I)))
    question = next((line for line in translated if "?" in line and len(line.split()) >= 3), None)
    observed = [ref.get("opening_analysis", {}).get("pattern") for ref in references]
    observed = [pattern for pattern in observed if pattern in {"pergunta", "reação verbal", "afirmação"}]
    pattern = collections.Counter(observed).most_common(1)[0][0] if observed else "sem padrão de fala disponível"
    reaction = next((line for line in translated if re.search(r"meu deus|caramba|mano|pera|não acredito", line, re.I)), None)
    substantial = [line for line in translated if len(line.split()) >= 4]
    preferred = question if pattern == "pergunta" else reaction if pattern == "reação verbal" else None
    hook = (preferred or question or (substantial[0] if substantial else translated[0])).strip()
    hook = re.sub(r"^Chat,?\s*", "", hook, flags=re.I)
    hook = hook[:70]
    correction = len(names) >= 2 and bool(re.search(r"\bnão\b", combined, re.I))
    if correction:
        hook = f"{names[0]} ou {names[-1]}?"
        title = f"{topic}: {hook}"
        description = (f"Na reação a {topic}, os nomes de {names[0]} e {names[-1]} viram uma confusão. "
                       "Confira a troca de falas e a reação dos participantes.")
    else:
        title = f"{topic}: {hook}" if topic.lower() not in hook.lower() else hook
        closing = substantial[-1] if substantial else translated[-1]
        description = f"Uma reação a {topic}: “{hook}”\nNo corte, a conversa chega a: “{closing}”"
    result = {"title": title[:100], "hook": hook, "description": description}
    tokens = re.findall(r"\w+", combined.lower())
    counts = collections.Counter(tokens)
    repeated = sum(count-1 for word,count in counts.items() if len(word)>3)
    questions = combined.count("?")
    reactions = len(re.findall(r"meu deus|pera|não|caramba|mano|sério", combined, re.I))
    score = min(95, 50 + min(questions, 2)*8 + min(repeated, 6)*2 + min(reactions, 4)*2 + 8)
    names = list(dict.fromkeys(match.group(0).title() for match in
                re.finditer(r"\b(Franklin|Michael|Lester|Lucia|IShowSpeed|Rockstar)\b", combined, re.I)))
    tags = list(dict.fromkeys([topic, "reação", "Shorts"] + names))[:8]
    result.update({
        "package_version": PACKAGE_VERSION, "translations": translated, "tags": tags, "editorial_score": score,
        "reason": f"Sinais da fala: {questions} perguntas, {min(repeated, 6)} repetições e {min(reactions, 4)} reações verbais. Revisar contexto e desfecho.",
        "cover_prompt": f"Criar capa vertical 9:16 para um corte sobre {topic}. Usar uma cena real do vídeo fornecida como referência. Texto curto: {result['hook']}. Preservar a identidade dos participantes e a cena, sem inventar acontecimentos.",
        "method": "Tradução local e redação baseada nas falas; nota heurística",
        "reference_pattern": pattern,
    })
    return result
