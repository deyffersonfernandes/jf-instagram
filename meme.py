#!/usr/bin/env python3
"""
Reels de meme da Central JF.

  python meme.py buscar <pedido.json> <pasta_saida>
      (roda no GitHub Actions, que tem internet livre)
      Procura vídeos de uso livre (Pexels, Pixabay e Wikimedia Commons) com os
      termos do pedido, baixa até 8 candidatos já cortados e normalizados
      (H.264, até 20 s, 720 px de largura) e gera, para cada um, uma folha com
      4 quadros para escolher. Grava candidatos.json e resultado.json.

  python meme.py montar --clipe X.mp4 --linha1 "..." --linha2 "..." [--inicio 0] [--dur 6] --saida reel.mp4 [--corte corte.mp4]
      Monta o Reels 1080x1920: cabeçalho do José (foto, nome, selo, @), texto
      em preto, virada em rosa e o vídeo em um quadro de cantos arredondados.
      Sai em MP4 H.264 + AAC, pronto para o Instagram. Com --corte, grava
      também só o trecho do vídeo usado (para a Central poder remontar).

Chaves opcionais (segredos do GitHub): PEXELS_API_KEY, PIXABAY_API_KEY.
Sem nenhuma delas, só o Wikimedia Commons é usado (acervo bem menor).
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent
FONTES = RAIZ / "assets" / "fonts"
AVATAR = RAIZ / "assets" / "avatar.jpg"
ROSA = (214, 60, 104)
PRETO = (17, 17, 17)
UA = "jf-instagram-meme/1.0 (github.com/deyffersonfernandes/jf-instagram)"


# ---------------------------------------------------------------- utilidades
def ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg não encontrado")
    return exe


def rodar(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-600:])
    return r.stdout


def sonda(arq):
    out = rodar(["ffprobe", "-v", "error", "-show_entries",
                 "stream=codec_type,width,height:format=duration", "-of", "json", str(arq)])
    d = json.loads(out)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    tem_audio = any(s.get("codec_type") == "audio" for s in d.get("streams", []))
    return {"w": int(v.get("width") or 0), "h": int(v.get("height") or 0),
            "dur": float(d.get("format", {}).get("duration") or 0), "audio": tem_audio}


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def baixar(url, destino, limite=60 * 1048576):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r, open(destino, "wb") as f:
        total = 0
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            total += len(b)
            if total > limite:
                raise RuntimeError("arquivo grande demais")
            f.write(b)


# ---------------------------------------------------------------- fontes de vídeo
def de_pexels(termo, n=6):
    chave = os.environ.get("PEXELS_API_KEY", "").strip()
    if not chave:
        return []
    q = urllib.parse.urlencode({"query": termo, "per_page": n, "size": "medium"})
    d = get_json(f"https://api.pexels.com/videos/search?{q}", {"Authorization": chave})
    out = []
    for v in d.get("videos", []):
        arqs = [a for a in v.get("video_files", []) if a.get("link") and (a.get("file_type") or "").endswith("mp4")]
        if not arqs:
            continue
        # o mais próximo de 1080 px no lado menor, sem passar muito disso
        arqs.sort(key=lambda a: abs(min(a.get("width") or 0, a.get("height") or 0) - 900))
        out.append({"fonte": "Pexels", "autor": (v.get("user") or {}).get("name", ""), "pagina": v.get("url", ""),
                    "link": arqs[0]["link"], "duracao": v.get("duration", 0), "termo": termo,
                    "licenca": "Licença Pexels (uso livre, sem atribuição obrigatória)"})
    return out


def de_pixabay(termo, n=6):
    chave = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not chave:
        return []
    q = urllib.parse.urlencode({"key": chave, "q": termo, "per_page": max(3, n), "safesearch": "true"})
    d = get_json(f"https://pixabay.com/api/videos/?{q}")
    out = []
    for h in d.get("hits", []):
        vs = h.get("videos") or {}
        v = vs.get("medium") or vs.get("small") or vs.get("large") or {}
        if not v.get("url"):
            continue
        out.append({"fonte": "Pixabay", "autor": h.get("user", ""), "pagina": h.get("pageURL", ""),
                    "link": v["url"], "duracao": h.get("duration", 0), "termo": termo,
                    "licenca": "Licença de conteúdo Pixabay (uso livre)"})
    return out


def de_wikimedia(termo, n=5):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"filetype:video {termo}", "gsrlimit": n, "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata"})
    d = get_json(f"https://commons.wikimedia.org/w/api.php?{q}")
    out = []
    for p in (d.get("query") or {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if not str(ii.get("mime", "")).startswith("video/") or not ii.get("url"):
            continue
        meta = ii.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        out.append({"fonte": "Wikimedia Commons", "autor": re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip()[:120],
                    "pagina": ii.get("descriptionurl", ""), "link": ii["url"], "duracao": 0, "termo": termo,
                    "licenca": lic or "ver página"})
    return out


# ---------------------------------------------------------------- buscar
def folha(clipe, dur, destino, idx):
    """4 quadros do vídeo em uma grade 2x2, com o número do candidato."""
    from PIL import Image, ImageDraw
    tmp = pathlib.Path(tempfile.mkdtemp())
    quadros = []
    for k, frac in enumerate((0.08, 0.35, 0.62, 0.9)):
        f = tmp / f"{k}.jpg"
        rodar([ffmpeg(), "-loglevel", "error", "-y", "-ss", f"{max(0, dur * frac):.2f}", "-i", str(clipe),
               "-frames:v", "1", "-vf", "scale=360:-2", str(f)])
        if f.exists():
            quadros.append((Image.open(f).convert("RGB"), dur * frac))
    if not quadros:
        return False
    w, h = quadros[0][0].size
    img = Image.new("RGB", (w * 2 + 6, h * 2 + 6 + 44), "white")
    dr = ImageDraw.Draw(img)
    dr.text((8, 6), f"#{idx}  ({dur:.1f}s)", fill=(0, 0, 0), font=fonte("InstrumentSans.ttf", 30, 700))
    for k, (q, t) in enumerate(quadros):
        x, y = (k % 2) * (w + 6), 44 + (k // 2) * (h + 6)
        img.paste(q.resize((w, h)), (x, y))
        dr.rectangle([x, y, x + 70, y + 30], fill=(0, 0, 0))
        dr.text((x + 6, y + 2), f"{t:.1f}s", fill=(255, 255, 255), font=fonte("InstrumentSans.ttf", 22, 600))
    img.save(destino, quality=82)
    shutil.rmtree(tmp, ignore_errors=True)
    return True


def buscar(pedido_arq, saida):
    pedido = json.loads(pathlib.Path(pedido_arq).read_text())
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    termos_en = [t for t in pedido.get("termos_en", []) if t][:4]
    termos_pt = [t for t in pedido.get("termos_pt", []) if t][:3]
    excluir = set(pedido.get("excluir", []))
    achados, erros = [], []
    for termo in termos_en + termos_pt:
        for fn in (de_pexels, de_pixabay):
            try:
                achados += fn(termo)
            except Exception as e:  # noqa: BLE001
                erros.append(f"{fn.__name__} '{termo}': {e}")
    for termo in termos_en[:2]:
        try:
            achados += de_wikimedia(termo)
        except Exception as e:  # noqa: BLE001
            erros.append(f"wikimedia '{termo}': {e}")
    # intercala por termo e tira repetidos e excluídos
    vistos, fila = set(), []
    por_termo = {}
    for a in achados:
        por_termo.setdefault(a["termo"], []).append(a)
    while any(por_termo.values()):
        for t in list(por_termo):
            if por_termo[t]:
                a = por_termo[t].pop(0)
                if a["pagina"] in vistos or a["pagina"] in excluir or a["link"] in excluir:
                    continue
                vistos.add(a["pagina"])
                fila.append(a)
    candidatos = []
    for a in fila:
        if len(candidatos) >= int(pedido.get("max", 8)):
            break
        idx = len(candidatos) + 1
        bruto = saida / f"bruto{idx}"
        final = saida / f"c{idx}.mp4"
        try:
            baixar(a["link"], bruto)
            info = sonda(bruto)
            if info["dur"] < 1.5 or not info["w"]:
                raise RuntimeError("vídeo curto ou sem imagem")
            cmd = [ffmpeg(), "-loglevel", "error", "-y", "-i", str(bruto), "-t", "20",
                   "-vf", "scale='min(720,iw)':-2,fps=30", "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
            cmd += ["-c:a", "aac", "-b:a", "128k"] if info["audio"] else ["-an"]
            rodar(cmd + [str(final)])
            info = sonda(final)
            folha(final, info["dur"], saida / f"c{idx}.jpg", idx)
            candidatos.append({**a, "idx": idx, "arquivo": final.name, "folha": f"c{idx}.jpg",
                               "duracao": round(info["dur"], 2), "w": info["w"], "h": info["h"],
                               "audio": info["audio"]})
        except Exception as e:  # noqa: BLE001
            erros.append(f"baixar {a['pagina']}: {e}")
        finally:
            bruto.unlink(missing_ok=True)
    (saida / "candidatos.json").write_text(json.dumps(candidatos, ensure_ascii=False, indent=2))
    (saida / "resultado.json").write_text(json.dumps({
        "id": pedido.get("id"), "rodada": pedido.get("rodada"), "ok": bool(candidatos),
        "candidatos": len(candidatos), "erros": erros[-15:],
        "fontes_ativas": [n for n, k in (("Pexels", "PEXELS_API_KEY"), ("Pixabay", "PIXABAY_API_KEY")) if os.environ.get(k)]
        + ["Wikimedia Commons"], "feito_em": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        ensure_ascii=False, indent=2))
    print(f"{len(candidatos)} candidatos; {len(erros)} avisos")


# ---------------------------------------------------------------- montar
def fonte(nome, tam, peso):
    from PIL import ImageFont
    f = ImageFont.truetype(str(FONTES / nome), tam)
    try:
        eixos = f.get_variation_axes()
        f.set_variation_by_axes([peso if b"eight" in e["name"] else e["default"] for e in eixos])
    except Exception:  # noqa: BLE001
        pass
    return f


def quebrar(dr, txt, f, maxw):
    linhas, cur = [], ""
    for w in txt.split():
        t = f"{cur} {w}".strip()
        if cur and dr.textlength(t, font=f) > maxw:
            linhas.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        linhas.append(cur)
    return linhas


def selo(dr, cx, cy, r1=19, r2=15):
    import math
    pts = [(cx + math.cos(i * math.pi / 8) * (r2 if i % 2 else r1), cy + math.sin(i * math.pi / 8) * (r2 if i % 2 else r1))
           for i in range(16)]
    dr.polygon(pts, fill=(29, 155, 240))
    k = r1 / 19
    dr.line([(cx - 8 * k, cy + 1 * k), (cx - 2 * k, cy + 7 * k), (cx + 9 * k, cy - 6 * k)], fill="white",
            width=max(2, round(4 * k)), joint="curve")


def layout(linha1, linha2, asp, S=2):
    """Desenha o fundo (cabeçalho + textos) em 2x e devolve (imagem 1080x1920, caixa do vídeo)."""
    from PIL import Image, ImageDraw
    W, H, X = 1080, 1920, 60
    BW = W - 2 * X
    img = Image.new("RGB", (W * S, H * S), "white")
    dr = ImageDraw.Draw(img)
    l1, l2 = (linha1 or "").strip(), (linha2 or "").strip()
    for size in range(88, 47, -4):
        f = fonte("InstrumentSans.ttf", size * S, 700)
        L1 = quebrar(dr, l1, f, (BW - 20) * S) if l1 else []
        L2 = quebrar(dr, l2, f, (BW - 20) * S) if l2 else []
        if len(L1) + len(L2) <= 4:
            break
    lh = round(size * 1.13)
    htxt = (len(L1) + len(L2)) * lh
    HEAD, g1, g2, top, bot = 124, 56, 44, 230, 1600
    bh = round(BW / (asp or 1))
    bh = max(440, min(bh, bot - top - HEAD - g1 - htxt - g2))
    y = round(top + max(0, (bot - top - (HEAD + g1 + htxt + g2 + bh)) / 2))
    # cabeçalho
    AV, ax = 124, X + 10
    if AVATAR.exists():
        av = Image.open(AVATAR).convert("RGB").resize((AV * S, AV * S))
        m = Image.new("L", (AV * S, AV * S), 0)
        ImageDraw.Draw(m).ellipse([0, 0, AV * S - 1, AV * S - 1], fill=255)
        img.paste(av, (ax * S, y * S), m)
    nx = ax + AV + 24
    fn = fonte("Montserrat.ttf", 46 * S, 700)
    dr.text((nx * S, (y + 20) * S), "José Fernandes", font=fn, fill=(15, 20, 25))
    nw = dr.textlength("José Fernandes", font=fn) / S
    selo(dr, (nx + nw + 30) * S, (y + 20 + 29) * S, 19 * S, 15 * S)
    dr.text((nx * S, (y + 76) * S), "@josefernandesmarketing", font=fonte("Montserrat.ttf", 34 * S, 400), fill=(83, 100, 113))
    y += HEAD + g1
    f = fonte("InstrumentSans.ttf", size * S, 700)
    for cor, linhas in ((PRETO, L1), (ROSA, L2)):
        for ln in linhas:
            tw = dr.textlength(ln, font=f)
            dr.text(((W * S - tw) / 2, y * S), ln, font=f, fill=cor)
            y += lh
    caixa = {"x": X, "y": y + g2, "w": BW, "h": bh, "r": 34}
    return img.resize((W, H), Image.LANCZOS), caixa


def montar(clipe, linha1, linha2, saida, inicio=0.0, dur=0.0, corte=None):
    from PIL import Image, ImageDraw
    info = sonda(clipe)
    if not info["w"]:
        raise RuntimeError("vídeo sem imagem")
    inicio = max(0.0, min(float(inicio or 0), max(0.0, info["dur"] - 0.5)))
    dur = float(dur or 0)
    if not dur or inicio + dur > info["dur"]:
        dur = max(0.5, info["dur"] - inicio)
    dur = min(dur, 90.0)
    fundo, cx = layout(linha1, linha2, info["w"] / info["h"])
    tmp = pathlib.Path(tempfile.mkdtemp())
    fundo.save(tmp / "fundo.png")
    S = 4
    m = Image.new("L", (cx["w"] * S, cx["h"] * S), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, cx["w"] * S - 1, cx["h"] * S - 1], radius=cx["r"] * S, fill=255)
    m.resize((cx["w"], cx["h"]), Image.LANCZOS).save(tmp / "mascara.png")
    filtro = (f"[1:v]scale={cx['w']}:{cx['h']}:force_original_aspect_ratio=increase,crop={cx['w']}:{cx['h']},"
              f"fps=30,format=rgba[v];[2:v]format=gray[m];[v][m]alphamerge[vr];"
              f"[0:v][vr]overlay={cx['x']}:{cx['y']}:shortest=1,format=yuv420p[out]")
    cmd = [ffmpeg(), "-loglevel", "error", "-y",
           "-loop", "1", "-framerate", "30", "-i", str(tmp / "fundo.png"),
           "-ss", f"{inicio:.2f}", "-t", f"{dur:.2f}", "-i", str(clipe),
           "-loop", "1", "-framerate", "30", "-i", str(tmp / "mascara.png")]
    if info["audio"]:
        mapa_audio = ["-map", "1:a:0"]
    else:
        cmd += ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        mapa_audio = ["-map", "3:a:0"]
    cmd += ["-filter_complex", filtro, "-map", "[out]", *mapa_audio,
            "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-movflags", "+faststart", str(saida)]
    rodar(cmd)
    if corte:
        c2 = [ffmpeg(), "-loglevel", "error", "-y", "-ss", f"{inicio:.2f}", "-t", f"{dur:.2f}", "-i", str(clipe),
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        c2 += ["-c:a", "aac", "-b:a", "128k"] if info["audio"] else ["-an"]
        rodar(c2 + [str(corte)])
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"saida": str(saida), "inicio": round(inicio, 2), "dur": round(dur, 2),
                      "bytes": pathlib.Path(saida).stat().st_size}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "buscar":
        buscar(sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 1 and sys.argv[1] == "montar":
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--clipe", required=True)
        ap.add_argument("--linha1", default="")
        ap.add_argument("--linha2", default="")
        ap.add_argument("--inicio", type=float, default=0)
        ap.add_argument("--dur", type=float, default=0)
        ap.add_argument("--saida", required=True)
        ap.add_argument("--corte")
        a = ap.parse_args()
        montar(a.clipe, a.linha1, a.linha2, a.saida, a.inicio, a.dur, a.corte)
    else:
        print(__doc__)
