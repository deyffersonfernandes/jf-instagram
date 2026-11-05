#!/usr/bin/env python3
"""Roda no GitHub Actions: tira o tempo de cada palavra da narração com o Whisper.

Uso: python3 video/tempos.py <pasta do pedido>
A pasta tem pedido.json ({"id", "rodada", "texto"}) e voz.<ext>.
Grava palavras.json ({"rodada", "duracao", "palavras": [{"w", "ini", "fim"}]}).
"""
import glob, json, os, subprocess, sys

pasta = sys.argv[1]
ped = json.load(open(os.path.join(pasta, "pedido.json"), encoding="utf-8"))
voz = [f for f in glob.glob(os.path.join(pasta, "voz.*"))][0]
wav = os.path.join(pasta, "_voz.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", voz, "-ac", "1", "-ar", "16000", wav], check=True)
from faster_whisper import WhisperModel
modelo = WhisperModel(os.environ.get("WHISPER_MODELO", "small"), device="cpu", compute_type="int8")
segs, info = modelo.transcribe(wav, language="pt", word_timestamps=True, vad_filter=False,
                               initial_prompt=(ped.get("texto") or "")[:800], beam_size=5)
pal = []
for s in segs:
    for w in (s.words or []):
        txt = w.word.strip()
        if txt:
            pal.append({"w": txt, "ini": round(w.start, 3), "fim": round(w.end, 3)})
os.remove(wav)
json.dump({"rodada": ped.get("rodada"), "duracao": round(info.duration, 3), "palavras": pal},
          open(os.path.join(pasta, "palavras.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(len(pal), "palavras,", round(info.duration, 1), "s")
