#!/usr/bin/env python3
"""Copia da Central JF as funções que desenham as artes (canvas) para arte/funcoes.js.

    python3 arte/extrair.py <central.html>

Rode de novo sempre que o desenho das artes mudar na Central.
"""
import pathlib, re, sys
src = pathlib.Path(sys.argv[1]).read_text()
ini = src.index("const ARTE_FMT=")
fim = src.index("async function pedirSlides(")
trecho = src[ini:fim]
# avatar do perfil é usado no cabeçalho do tweet e da notícia
out = "/* Gerado por arte/extrair.py a partir da Central JF. Não edite à mão. */\n" + trecho
pathlib.Path(__file__).with_name("funcoes.js").write_text(out)
print("ok", len(out), "bytes")
