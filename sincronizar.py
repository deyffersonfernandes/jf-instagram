#!/usr/bin/env python3
"""
Ponte Central JF -> fila do GitHub. Roda na tarefa agendada do Claude.

  python sincronizar.py planejar  <pasta_conteudos>
      Lê os posts agendados (JSONs exportados da Central) e imprime, em JSON,
      quais entram na fila agora e quais arquivos (ids de asset) baixar.

  python sincronizar.py montar    <pasta_conteudos> <pasta_baixados>
      Monta fila/<id>/ com post.json e as mídias já convertidas para o
      formato que o Instagram aceita (JPEG, proporção entre 4:5 e 1.91:1).

  python sincronizar.py concluidos <pasta_conteudos>
      Imprime, em JSON, os posts publicados que ainda não estão marcados
      como "postado" na Central, e os que deram erro.
"""
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import sys
from zoneinfo import ZoneInfo

RAIZ = pathlib.Path(__file__).resolve().parent
FILA, PUBLICADOS, ERROS = RAIZ / "fila", RAIZ / "publicados", RAIZ / "erros"
FUSO = ZoneInfo("America/Sao_Paulo")
JANELA_HORAS = 1.25       # entra na fila o que vence nos próximos 75 min (o GitHub espera até 85)
MAX_ATRASO_HORAS = 6


def ler_conteudos(pasta):
    docs = []
    for f in pathlib.Path(pasta).rglob("*.json"):
        d = json.loads(f.read_text())
        # aceita o documento puro (exportado com out_dir) ou o envelope {"id", "data": {...}, "version"}
        envelope = isinstance(d.get("data"), dict) and "id" in d
        dados = dict(d["data"]) if envelope else dict(d)
        dados["id"] = d["id"] if envelope else f.stem
        dados["_version"] = d.get("version") if envelope else None
        docs.append(dados)
    return docs


def horario(c):
    if not c.get("data") or not c.get("hora"):
        return None
    return dt.datetime.fromisoformat(f"{c['data']}T{c['hora']}").replace(tzinfo=FUSO)


def assinatura(c):
    base = json.dumps([c.get("legenda", ""), c.get("data"), c.get("hora"),
                       [a.get("id") for a in c.get("arquivos") or []]], ensure_ascii=False)
    return hashlib.sha1(base.encode()).hexdigest()[:12]


def eh_video(a):
    return (a.get("tipo") or "").startswith("video/") or a.get("nome", "").lower().endswith((".mp4", ".mov"))


def planejar(pasta, imprimir=True):
    agora = dt.datetime.now(FUSO)
    entrar, avisos = [], []
    for c in ler_conteudos(pasta):
        if c.get("status") != "agendado" or c.get("canal", "instagram") != "instagram":
            continue
        if c.get("uso") == "anuncio":      # criativo só de anúncio não vai para o feed
            continue
        quando = horario(c)
        pid = c["id"]
        if not quando:
            if c.get("data") == agora.strftime("%Y-%m-%d"):
                avisos.append({"id": pid, "titulo": c.get("titulo"), "aviso": "agendado para hoje sem horário"})
            continue
        if (PUBLICADOS / f"{pid}.json").exists() or (ERROS / f"{pid}.json").exists():
            continue
        if quando > agora + dt.timedelta(hours=JANELA_HORAS):
            continue
        if quando < agora - dt.timedelta(hours=MAX_ATRASO_HORAS):
            avisos.append({"id": pid, "titulo": c.get("titulo"), "aviso": "horário já passou há mais de 6 h; não será publicado"})
            continue
        arquivos = c.get("arquivos") or []
        if not arquivos:
            avisos.append({"id": pid, "titulo": c.get("titulo"), "aviso": "agendado sem arquivo"})
            continue
        existente = FILA / pid / "post.json"
        if existente.exists() and json.loads(existente.read_text()).get("assinatura") == assinatura(c):
            continue
        entrar.append({"id": pid, "titulo": c.get("titulo"), "quando": quando.isoformat(),
                       "baixar": [a["id"] for a in arquivos]})
    plano = {"entrar": entrar, "avisos": avisos}
    if imprimir:
        print(json.dumps(plano, ensure_ascii=False, indent=2))
    return plano


def preparar_imagem(origem, destino):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(origem))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        fundo = Image.new("RGB", im.size, (255, 255, 255))
        fundo.paste(im, mask=im.split()[-1])
        im = fundo
    else:
        im = im.convert("RGB")
    w, h = im.size
    # Instagram aceita de 4:5 (vertical) a 1.91:1 (horizontal); fora disso, completa as bordas
    if h / w > 1.25:
        nw = round(h / 1.25)
        im = completar(im, nw, h)
    elif w / h > 1.91:
        nh = round(w / 1.91)
        im = completar(im, w, nh)
    if im.width > 1440:
        im = im.resize((1440, round(im.height * 1440 / im.width)), Image.LANCZOS)
    im.save(destino, "JPEG", quality=92, optimize=True)


def completar(im, nw, nh):
    from PIL import Image
    borda = list(im.crop((0, 0, im.width, 1)).getdata()) + list(im.crop((0, im.height - 1, im.width, im.height)).getdata())
    cor = tuple(sum(p[i] for p in borda) // len(borda) for i in range(3))
    fundo = Image.new("RGB", (nw, nh), cor)
    fundo.paste(im, ((nw - im.width) // 2, (nh - im.height) // 2))
    return fundo


def montar(pasta, baixados):
    baixados = pathlib.Path(baixados)
    ids = {e["id"] for e in planejar(pasta, imprimir=False)["entrar"]}
    montados = []
    for c in ler_conteudos(pasta):
        if c["id"] not in ids:
            continue
        pid = c["id"]
        arquivos = c.get("arquivos") or []
        locais = [next(iter(baixados.glob(f"{a['id']}*")), None) for a in arquivos]
        if not arquivos or None in locais:
            continue
        quando = horario(c)
        if not quando or c.get("status") != "agendado":
            continue
        destino = FILA / pid
        if destino.exists():
            shutil.rmtree(destino)
        destino.mkdir(parents=True)
        nomes = []
        for i, (a, loc) in enumerate(zip(arquivos, locais), 1):
            if eh_video(a):
                nome = f"{i:02d}.mp4"
                shutil.copy(loc, destino / nome)
            else:
                nome = f"{i:02d}.jpg"
                preparar_imagem(loc, destino / nome)
            nomes.append(nome)
        if len(nomes) > 1:
            formato = "carrossel"
        elif nomes[0].endswith(".mp4"):
            formato = "reel"
        else:
            formato = "imagem"
        post = {"id": pid, "titulo": c.get("titulo", ""), "formato": formato,
                "publicar_em": quando.isoformat(), "legenda": c.get("legenda", ""),
                "arquivos": nomes, "assinatura": assinatura(c)}
        (destino / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n")
        montados.append(pid)
    print(json.dumps({"montados": montados}, ensure_ascii=False))


def concluidos(pasta):
    status = {c["id"]: c for c in ler_conteudos(pasta)}
    marcar, erros = [], []
    for f in sorted(PUBLICADOS.glob("*.json")) if PUBLICADOS.exists() else []:
        r = json.loads(f.read_text())
        c = status.get(r["id"])
        if c and c.get("status") != "postado":
            marcar.append({**r, "version": c.get("_version")})
    for f in sorted(ERROS.glob("*.json")) if ERROS.exists() else []:
        erros.append(json.loads(f.read_text()))
    print(json.dumps({"marcar_postado": marcar, "erros": erros}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "planejar":
        planejar(sys.argv[2])
    elif cmd == "montar":
        montar(sys.argv[2], sys.argv[3])
    elif cmd == "concluidos":
        concluidos(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)
