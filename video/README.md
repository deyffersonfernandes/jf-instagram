# Estúdio de Reels IA

- `estudio.py`: motor (skia + ffmpeg). `validar`, `quadros` (folha de prévia) e `render`.
- `ROTEIRO.md`: o formato do roteiro e todas as cenas.
- `formatos.json`: formatos do gerador (a Central tem uma cópia; mude nos dois lugares).
- `tempos.py` + `.github/workflows/video.yml`: tempo de cada palavra da voz (Whisper no GitHub).
- `exemplos/`: roteiros de teste com todas as cenas.
- `fontes/`: Montserrat em pesos fixos.

Teste rápido: `pip install --break-system-packages skia-python numpy` e
`python3 video/estudio.py quadros video/exemplos/cenas-1.json --saida /tmp/folha.jpg`.
