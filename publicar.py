#!/usr/bin/env python3
"""
Publicador da Central JF -> Instagram.

Roda no GitHub Actions. Procura posts em fila/<id>/post.json cujo horário
já chegou, publica no Instagram pela API oficial da Meta e registra o
resultado em publicados/<id>.json (ou erros/<id>.json).

post.json:
{
  "id": "c07",
  "titulo": "...",
  "formato": "imagem" | "carrossel" | "reel",
  "publicar_em": "2026-10-13T18:00:00-03:00",
  "legenda": "...",
  "arquivos": ["01.jpg", "02.jpg"]      # dentro de fila/<id>/
}

Variáveis de ambiente (segredos do repositório):
  IG_USER_ID     ID da conta profissional do Instagram
  IG_TOKEN       token de acesso com instagram_business_content_publish
  GRAPH_HOST     opcional: graph.instagram.com (padrão, login do Instagram) ou graph.facebook.com
  GRAPH_VERSION  opcional: padrão v23.0
"""
import datetime as dt
import json
import os
import pathlib
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent
FILA = RAIZ / "fila"
PUBLICADOS = RAIZ / "publicados"
ERROS = RAIZ / "erros"

MAX_ATRASO_HORAS = 6       # post mais atrasado que isso não é publicado
MAX_TENTATIVAS = 3

GRAPH_HOST = os.environ.get("GRAPH_HOST", "graph.instagram.com").strip() or "graph.instagram.com"
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v23.0").strip() or "v23.0"
API = f"https://{GRAPH_HOST}/{GRAPH_VERSION}"
IG_USER_ID = os.environ.get("IG_USER_ID", "").strip()
IG_TOKEN = os.environ.get("IG_TOKEN", "").strip()

REPO = os.environ.get("GITHUB_REPOSITORY", "")
REF = os.environ.get("RAW_REF") or os.environ.get("GITHUB_SHA") or "main"
RAW_BASE = os.environ.get("RAW_BASE") or f"https://raw.githubusercontent.com/{REPO}/{REF}"


class ErroMeta(Exception):
    pass


def agora():
    return dt.datetime.now(dt.timezone.utc)


def graph(metodo, caminho, params=None):
    params = dict(params or {})
    params["access_token"] = IG_TOKEN
    url = f"{API}/{caminho}"
    dados = None
    if metodo == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        dados = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=dados, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode(errors="replace")
        try:
            msg = json.loads(corpo).get("error", {}).get("message", corpo)
        except Exception:
            msg = corpo
        raise ErroMeta(f"{metodo} {caminho}: HTTP {e.code} - {msg}") from None


def esperar_container(cid, limite_s=600):
    """Espera o container ficar FINISHED (vídeos levam um tempo para processar)."""
    inicio = time.time()
    while True:
        st = graph("GET", cid, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code in (None, "FINISHED"):
            return
        if code in ("ERROR", "EXPIRED"):
            raise ErroMeta(f"container {cid} com status {code}: {st.get('status', '')}")
        if time.time() - inicio > limite_s:
            raise ErroMeta(f"container {cid} demorou demais para processar (status {code})")
        time.sleep(float(os.environ.get("POLL_S", "10")))


def url_publica(post_id, nome):
    return f"{RAW_BASE}/fila/{urllib.parse.quote(post_id)}/{urllib.parse.quote(nome)}"


def eh_video(nome):
    return nome.lower().endswith((".mp4", ".mov"))


def criar_container(post, nome, carrossel_item=False, legenda=None):
    url = url_publica(post["id"], nome)
    p = {}
    if eh_video(nome):
        p["video_url"] = url
        p["media_type"] = "VIDEO" if carrossel_item else "REELS"
        if not carrossel_item:
            p["share_to_feed"] = "true"
    else:
        p["image_url"] = url
    if carrossel_item:
        p["is_carousel_item"] = "true"
    if legenda:
        p["caption"] = legenda
    cid = graph("POST", f"{IG_USER_ID}/media", p)["id"]
    esperar_container(cid)
    return cid


def publicar(post):
    arquivos = post.get("arquivos") or []
    formato = post.get("formato")
    legenda = post.get("legenda") or ""
    if not arquivos:
        raise ErroMeta("post sem arquivo")
    if len(legenda) > 2200:
        raise ErroMeta(f"legenda com {len(legenda)} caracteres (o Instagram aceita até 2200)")

    if formato == "carrossel" or len(arquivos) > 1:
        if not 2 <= len(arquivos) <= 10:
            raise ErroMeta(f"carrossel precisa de 2 a 10 arquivos (tem {len(arquivos)})")
        filhos = [criar_container(post, n, carrossel_item=True) for n in arquivos]
        cid = graph("POST", f"{IG_USER_ID}/media", {
            "media_type": "CAROUSEL", "children": ",".join(filhos), "caption": legenda})["id"]
        esperar_container(cid)
    else:
        cid = criar_container(post, arquivos[0], legenda=legenda)

    media_id = graph("POST", f"{IG_USER_ID}/media_publish", {"creation_id": cid})["id"]
    link = ""
    try:
        link = graph("GET", media_id, {"fields": "permalink"}).get("permalink", "")
    except ErroMeta:
        pass
    return media_id, link


def salvar(pasta, post_id, dados):
    pasta.mkdir(exist_ok=True)
    (pasta / f"{post_id}.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def main():
    if not IG_USER_ID or not IG_TOKEN:
        print("Faltam os segredos IG_USER_ID e/ou IG_TOKEN no repositório. Nada a fazer.")
        return 0
    if not FILA.exists():
        print("Fila vazia.")
        return 0

    houve_erro = False
    for pj in sorted(FILA.glob("*/post.json")):
        post = json.loads(pj.read_text())
        pid = post["id"]
        quando = dt.datetime.fromisoformat(post["publicar_em"])
        if quando > agora():
            print(f"[{pid}] aguardando {post['publicar_em']}")
            continue
        if (PUBLICADOS / f"{pid}.json").exists():
            print(f"[{pid}] já publicado, limpando da fila")
            shutil.rmtree(pj.parent)
            continue

        atraso_h = (agora() - quando).total_seconds() / 3600
        if atraso_h > MAX_ATRASO_HORAS:
            salvar(ERROS, pid, {"id": pid, "titulo": post.get("titulo", ""),
                                "erro": f"não publicado: horário passou há {atraso_h:.1f} h",
                                "em": agora().isoformat()})
            shutil.rmtree(pj.parent)
            houve_erro = True
            continue

        try:
            print(f"[{pid}] publicando '{post.get('titulo', '')}'")
            media_id, link = publicar(post)
        except Exception as e:
            post["tentativas"] = post.get("tentativas", 0) + 1
            msg = str(e)
            print(f"[{pid}] ERRO (tentativa {post['tentativas']}): {msg}")
            houve_erro = True
            if post["tentativas"] >= MAX_TENTATIVAS:
                salvar(ERROS, pid, {"id": pid, "titulo": post.get("titulo", ""), "erro": msg,
                                    "tentativas": post["tentativas"], "em": agora().isoformat()})
                shutil.rmtree(pj.parent)
            else:
                post["ultimo_erro"] = msg
                pj.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n")
            continue

        salvar(PUBLICADOS, pid, {"id": pid, "titulo": post.get("titulo", ""), "media_id": media_id,
                                 "permalink": link, "publicado_em": agora().isoformat()})
        shutil.rmtree(pj.parent)
        print(f"[{pid}] publicado: {link or media_id}")

    return 1 if houve_erro else 0


if __name__ == "__main__":
    sys.exit(main())
