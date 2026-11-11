"""Entrada isolada do Whisper para liberar a memória ao terminar."""

import json
from pathlib import Path
import sys
import torch
import whisper

torch.set_num_threads(2)
audio, output, model_name = sys.argv[1:4]
opening = len(sys.argv) > 4 and sys.argv[4] == "opening"
model = whisper.load_model(model_name, device="cpu")
options = {"temperature": 0, "condition_on_previous_text": False, "sample_len": 96,
           "no_speech_threshold": .5} if opening else {}
result = model.transcribe(audio, word_timestamps=not opening, fp16=False, verbose=False, **options)
pending = Path(output).with_suffix(".tmp")
pending.write_text(json.dumps(result, ensure_ascii=False), encoding="utf8")
pending.replace(output)
