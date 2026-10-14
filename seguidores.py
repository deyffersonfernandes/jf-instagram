#!/usr/bin/env python3
"""
Lê o número de seguidores direto da API oficial do Instagram (mesmo token
do publicador) e grava em seguidores.json. Roda no GitHub Actions.

A ponte da Central JF (tarefa agendada) lê esse arquivo e atualiza a meta
"Seguidores no Instagram".
"""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent
ARQ = RAIZ / "seguidores.json"

GRAPH_HOST = os.environ.get("GRAPH_HOST", "graph.instagram.com").strip() or "graph.instagram.com"
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v23.0").strip() or "v23.0"
IG_TOKEN = os.environ.get("IG_TOKEN", "").strip()
IG_USER_ID = os.environ.get("IG_USER_ID", "").strip() or "me"


def main():
    if not IG_TOKEN:
        sys.exit("IG_TOKEN não configurado.")
    q = urllib.parse.urlencode({"fields": "username,followers_count,media_count", "access_token": IG_TOKEN})
    url = f"https://{GRAPH_HOST}/{GRAPH_VERSION}/{IG_USER_ID}?{q}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            dados = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Erro da API do Instagram ({e.code}): {e.read().decode(errors='replace')[:300]}")

    n = dados.get("followers_count")
    if not isinstance(n, int):
        sys.exit(f"A API não devolveu followers_count: {dados}")

    antes = {}
    if ARQ.exists():
        try:
            antes = json.loads(ARQ.read_text())
        except Exception:
            antes = {}

    agora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    novo = {
        "conta": dados.get("username", ""),
        "seguidores": n,
        "posts": dados.get("media_count"),
        "lido_em": agora,
        "mudou_em": agora if antes.get("seguidores") != n else antes.get("mudou_em", agora),
        "fonte": "API oficial do Instagram",
    }
    ARQ.write_text(json.dumps(novo, ensure_ascii=False, indent=2) + "\n")
    print(f"@{novo['conta']}: {antes.get('seguidores', '?')} -> {n} seguidores")


if __name__ == "__main__":
    main()
