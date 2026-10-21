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
import subprocess
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
    return (a.get("tipo") or "").startswith("video/") or a.get("nome", "").lower().endswith((".mp4", ".mov", ".webm"))


def _sondar_video(origem):
    """Lê codec, tamanho e fps do vídeo (vazio se não der para ler)."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {}
    r = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt",
                        "-of", "json", str(origem)], capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    info = {}
    for s in json.loads(r.stdout or "{}").get("streams", []):
        if s.get("codec_type") == "video" and "v" not in info:
            info["v"] = s
        elif s.get("codec_type") == "audio" and "a" not in info:
            info["a"] = s
    return info


def _pronto_para_reels(info):
    """True quando o arquivo já está no formato do Instagram e pode ir sem recomprimir."""
    v, a = info.get("v"), info.get("a")
    if not v or v.get("codec_name") != "h264" or v.get("pix_fmt") not in ("yuv420p", "yuvj420p"):
        return False
    if (v.get("width") or 0) > 1080 or (v.get("height") or 0) > 1920:
        return False
    try:
        n, d = (v.get("avg_frame_rate") or "0/1").split("/")
        fps = float(n) / float(d or 1)
    except (ValueError, ZeroDivisionError):
        return False
    if not 23 <= fps <= 60.5:
        return False
    return a is None or a.get("codec_name") == "aac"


def preparar_video(origem, destino):
    """Deixa o vídeo pronto para Reels SEM perder qualidade.
    Se já está em MP4 H.264 + AAC até 1080x1920 (o normal do celular e dos editores),
    só reorganiza o arquivo (faststart), sem recomprimir: sai idêntico ao original.
    Vídeos montados no navegador (WEBM/VP9 dos Reels de meme) são convertidos."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        if str(origem).lower().endswith(".webm"):
            raise RuntimeError("ffmpeg não encontrado para converter o vídeo WEBM em MP4")
        shutil.copy(origem, destino)
        return
    if _pronto_para_reels(_sondar_video(origem)):
        r = subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", str(origem), "-map", "0:v:0", "-map", "0:a:0?",
                            "-c", "copy", "-movflags", "+faststart", str(destino)], capture_output=True, text=True)
        if r.returncode == 0:
            return
    cmd = [ffmpeg, "-loglevel", "error", "-y", "-i", str(origem),
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
           "-vf", "scale='min(1080,iw)':-2,fps=30", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
           "-movflags", "+faststart", str(destino)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # sem faixa de áudio ou outro detalhe: tenta sem áudio antes de desistir
        sem_audio = cmd[:cmd.index("-c:a")] + ["-an", "-movflags", "+faststart", str(destino)]
        r2 = subprocess.run(sem_audio, capture_output=True, text=True)
        if r2.returncode != 0:
            raise RuntimeError("falha ao converter vídeo: " + (r.stderr or r2.stderr)[-300:])


def ids_do_arquivo(a):
    """Vídeos grandes ficam na Central em partes de até 14 MB (campo "partes", em ordem).
    Devolve todos os ids de asset que precisam ser baixados para esse arquivo."""
    partes = a.get("partes") or []
    return list(partes) if len(partes) > 1 else [a["id"]]


def localizar(baixados, a):
    """Acha o arquivo baixado; se estiver em partes, junta as partes byte a byte
    (o resultado é idêntico ao original enviado)."""
    ids = ids_do_arquivo(a)
    locais = [next(iter(baixados.glob(f"{i}*")), None) for i in ids]
    if None in locais:
        return None
    if len(locais) == 1:
        return locais[0]
    inteiro = baixados / f"inteiro-{a['id']}.mp4"
    with open(inteiro, "wb") as saida:
        for loc in locais:
            with open(loc, "rb") as parte:
                shutil.copyfileobj(parte, saida)
    if a.get("tamanho") and inteiro.stat().st_size != a["tamanho"]:
        raise RuntimeError(f"vídeo {a.get('nome')} veio incompleto ao juntar as partes")
    return inteiro


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
                       "baixar": [i for a in arquivos for i in ids_do_arquivo(a)]})
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


def ordenar(arquivos):
    """Carrossel: se todo nome começa com número (1, 02, 3-capa...), ordena por esse número; senão, ordem de upload."""
    import re
    nums = [re.match(r"\s*(\d+)", a.get("nome", "")) for a in arquivos]
    if len(arquivos) > 1 and all(nums):
        return [a for _, a in sorted(zip([int(n.group(1)) for n in nums], arquivos), key=lambda t: t[0])]
    return list(arquivos)


def montar(pasta, baixados):
    baixados = pathlib.Path(baixados)
    ids = {e["id"] for e in planejar(pasta, imprimir=False)["entrar"]}
    montados = []
    for c in ler_conteudos(pasta):
        if c["id"] not in ids:
            continue
        pid = c["id"]
        arquivos = ordenar(c.get("arquivos") or [])
        locais = [localizar(baixados, a) for a in arquivos]
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
                preparar_video(loc, destino / nome)
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
