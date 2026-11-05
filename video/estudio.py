#!/usr/bin/env python3
"""Estúdio de Reels IA do @josefernandesmarketing.

Transforma um roteiro em JSON (falas + cenas) num Reels 1080x1920, com legenda
palavra por palavra sincronizada com a narração, trilha e efeitos sonoros.

Uso:
  python3 video/estudio.py validar roteiro.json
  python3 video/estudio.py quadros roteiro.json --saida folha.jpg [--palavras palavras.json]
  python3 video/estudio.py render roteiro.json --saida reel.mp4 [--audio voz.mp3 --palavras palavras.json]

Sem --audio, o vídeo sai com tempos estimados (prévia, sem voz).
O formato do roteiro está em video/ROTEIRO.md.
"""
import json, math, os, re, subprocess, sys, unicodedata, difflib, random, wave, argparse
import numpy as np
import skia

W, H, FPS = 1080, 1920, 30
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
HANDLE = "@josefernandesmarketing"
TOPO, BASE = 250, 1360          # área das cenas
LEG_Y = 1520                    # centro da legenda

# ---------------------------------------------------------------- cores
TEMAS = {
    "escuro": dict(bg=(10, 31, 29), bg2=(19, 58, 54), txt=(255, 255, 255), sub=(160, 196, 190),
                   card=(255, 255, 255), cardtxt=(18, 32, 31), linha=(40, 84, 79)),
    "claro": dict(bg=(244, 240, 232), bg2=(228, 236, 230), txt=(18, 32, 31), sub=(92, 110, 106),
                  card=(255, 255, 255), cardtxt=(18, 32, 31), linha=(210, 215, 208)),
    "noite": dict(bg=(12, 14, 26), bg2=(32, 28, 64), txt=(255, 255, 255), sub=(170, 170, 200),
                  card=(255, 255, 255), cardtxt=(20, 20, 30), linha=(52, 50, 90)),
}
FIXAS = dict(hi=(255, 210, 63), ruim=(255, 84, 89), bom=(52, 211, 120), acc=(79, 192, 180),
             azul=(70, 140, 255), roxo=(160, 110, 255), laranja=(255, 150, 60), branco=(255, 255, 255),
             preto=(15, 15, 15), cinza=(150, 150, 150))
T = dict(TEMAS["escuro"])


def cor(nome, padrao="txt"):
    if isinstance(nome, (list, tuple)):
        return tuple(nome)
    if not nome:
        nome = padrao
    if isinstance(nome, str) and nome.startswith("#") and len(nome) == 7:
        return tuple(int(nome[i:i + 2], 16) for i in (1, 3, 5))
    return T.get(nome) or FIXAS.get(nome) or T.get(padrao) or FIXAS.get(padrao) or (255, 255, 255)


def C(rgb, a=1.0):
    r, g, b = rgb[:3]
    return skia.ColorSetARGB(int(255 * max(0, min(1, a))), int(r), int(g), int(b))


def P(rgb=(255, 255, 255), a=1.0, stroke=0, sombra=False):
    p = skia.Paint(AntiAlias=True, Color=C(rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if sombra:
        p.setImageFilter(skia.ImageFilters.DropShadow(0, 10, 18, 18, skia.ColorSetARGB(int(90 * a), 0, 0, 0)))
    return p


# ---------------------------------------------------------------- fontes e texto
_TF = {}


def tf(w=800):
    w = {400: 500, 500: 500, 600: 700, 700: 700, 800: 800, 900: 900}.get(w, 800)
    if w not in _TF:
        _TF[w] = skia.Typeface.MakeFromFile(os.path.join(AQUI, "fontes", f"Montserrat-{w}.ttf"))
    return _TF[w]


def F(size, w=800):
    f = skia.Font(tf(w), size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


EMOJI_TF = None
for _c in ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", os.path.join(AQUI, "fontes", "NotoColorEmoji.ttf")):
    if os.path.exists(_c):
        EMOJI_TF = skia.Typeface.MakeFromFile(_c)
        break


def eh_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or o in (0xFE0F, 0x200D) or 0x2B00 <= o <= 0x2BFF


def runs(s):
    out, cur, e = [], "", None
    for ch in s:
        k = eh_emoji(ch)
        if cur and k != e:
            out.append((cur, e)); cur = ""
        cur += ch; e = k
    if cur:
        out.append((cur, e))
    return out


def largura(s, size, w=800):
    f = F(size, w)
    tot = 0
    for r, e in runs(s):
        if e:
            if EMOJI_TF:
                tot += skia.Font(EMOJI_TF, size).measureText(r)
        else:
            tot += f.measureText(r)
    return tot


def desenhar_str(cv, s, x, y, size, w, paint):
    f = F(size, w)
    for r, e in runs(s):
        if e:
            if EMOJI_TF:
                fe = skia.Font(EMOJI_TF, size)
                cv.drawString(r, x, y, fe, skia.Paint(AntiAlias=True, Alphaf=paint.getAlphaf()))
                x += fe.measureText(r)
        else:
            cv.drawString(r, x, y, f, paint)
            x += f.measureText(r)
    return x


def tokens_ricos(s):
    """'texto com *destaque*.' -> [(palavra, destacada, colada_na_anterior)]"""
    out = []
    for parte in re.split(r"(\*[^*]+\*)", s or ""):
        if not parte:
            continue
        d = parte.startswith("*") and parte.endswith("*")
        corpo = parte[1:-1] if d else parte
        if not d and out and corpo[:1] and not corpo[:1].isspace():
            m = re.match(r"^(\S+)(.*)$", corpo, re.S)
            out.append((m.group(1), False, True))
            corpo = m.group(2)
        elif d and out and parte is not None and out[-1] and s and False:
            pass
        for wd in corpo.split():
            out.append((wd, d, False))
    return out


def quebrar(s, size, w, maxw):
    """Devolve linhas; cada linha é uma lista de palavras, cada palavra uma lista de pedaços (texto, destacado)."""
    palavras = []
    for t_, d, cola in tokens_ricos(s):
        if cola and palavras:
            palavras[-1].append((t_, d))
        else:
            palavras.append([(t_, d)])
    linhas, cur, curw = [], [], 0
    esp = largura(" ", size, w)
    for pw in palavras:
        lw = sum(largura(t_, size, w) for t_, _ in pw)
        if cur and curw + esp + lw > maxw:
            linhas.append(cur)
            cur, curw = [], 0
        curw += (esp if cur else 0) + lw
        cur.append(pw)
    if cur:
        linhas.append(cur)
    return linhas


def texto(cv, s, x, y, size, w=800, rgb=None, a=1.0, alinhar="c", maxw=900, hi=None, lh=1.18,
          sombra=False, caixa=False, v="c"):
    """Desenha texto com quebra de linha. y = centro do bloco (v='c') ou topo (v='t'). Retorna altura."""
    rgb = rgb or T["txt"]
    hi = hi or FIXAS["hi"]
    if caixa:
        s = s.upper()
    linhas = quebrar(s, size, w, maxw)
    alt = len(linhas) * size * lh
    y0 = y - alt / 2 if v == "c" else y
    esp = largura(" ", size, w)
    for i, ln in enumerate(linhas):
        lw = sum(largura(t_, size, w) for pw in ln for t_, _ in pw) + esp * (len(ln) - 1)
        xx = x - lw / 2 if alinhar == "c" else (x if alinhar == "e" else x - lw)
        base = y0 + i * size * lh + size * 0.86
        for pw in ln:
            for t_, d in pw:
                xx = desenhar_str(cv, t_, xx, base, size, w, P(hi if d else rgb, a, sombra=sombra))
            xx += esp
    return alt


def altura_texto(s, size, w, maxw, lh=1.18):
    return len(quebrar(s, size, w, maxw)) * size * lh


# ---------------------------------------------------------------- formas
def rrect(cv, x, y, w, h, r, rgb, a=1.0, sombra=False, stroke=0):
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), P(rgb, a, stroke, sombra))


def circulo(cv, x, y, r, rgb, a=1.0, stroke=0):
    cv.drawCircle(x, y, r, P(rgb, a, stroke))


def icone(cv, nome, x, y, s, rgb, a=1.0):
    """Ícones desenhados com traço. (x, y) = centro, s = tamanho."""
    st = max(3, s * 0.12)
    p = P(rgb, a, stroke=st)
    pa = skia.Path()
    h = s / 2
    if nome == "check":
        pa.moveTo(x - h * .7, y); pa.lineTo(x - h * .15, y + h * .55); pa.lineTo(x + h * .75, y - h * .55)
        cv.drawPath(pa, p)
    elif nome == "x":
        pa.moveTo(x - h * .6, y - h * .6); pa.lineTo(x + h * .6, y + h * .6)
        pa.moveTo(x + h * .6, y - h * .6); pa.lineTo(x - h * .6, y + h * .6)
        cv.drawPath(pa, p)
    elif nome == "relogio":
        cv.drawCircle(x, y, h * .85, p)
        pa.moveTo(x, y - h * .5); pa.lineTo(x, y); pa.lineTo(x + h * .35, y + h * .2)
        cv.drawPath(pa, p)
    elif nome == "pessoa":
        cv.drawCircle(x, y - h * .38, h * .3, P(rgb, a))
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - h * .55, y + h * .02, h * 1.1, h * .8), h * .45, h * .45), P(rgb, a))
    elif nome == "dinheiro":
        cv.drawCircle(x, y, h * .85, p)
        texto(cv, "$", x, y, s * .75, 900, rgb, a)
    elif nome == "coracao":
        pa.moveTo(x, y + h * .7)
        pa.cubicTo(x - h * 1.2, y - h * .1, x - h * .55, y - h * 1.0, x, y - h * .35)
        pa.cubicTo(x + h * .55, y - h * 1.0, x + h * 1.2, y - h * .1, x, y + h * .7)
        cv.drawPath(pa, P(rgb, a))
    elif nome == "alerta":
        pa.moveTo(x, y - h * .85); pa.lineTo(x + h * .9, y + h * .7); pa.lineTo(x - h * .9, y + h * .7); pa.close()
        cv.drawPath(pa, p)
        texto(cv, "!", x, y + h * .08, s * .6, 900, rgb, a)
    elif nome == "seta":
        pa.moveTo(x - h * .7, y); pa.lineTo(x + h * .6, y)
        pa.moveTo(x + h * .15, y - h * .45); pa.lineTo(x + h * .65, y); pa.lineTo(x + h * .15, y + h * .45)
        cv.drawPath(pa, p)
    elif nome == "calendario":
        rrect(cv, x - h * .8, y - h * .65, h * 1.6, h * 1.4, h * .2, rgb, a, stroke=st)
        pa.moveTo(x - h * .8, y - h * .2); pa.lineTo(x + h * .8, y - h * .2)
        pa.moveTo(x - h * .4, y - h * .9); pa.lineTo(x - h * .4, y - h * .5)
        pa.moveTo(x + h * .4, y - h * .9); pa.lineTo(x + h * .4, y - h * .5)
        cv.drawPath(pa, p)
    elif nome == "celular":
        rrect(cv, x - h * .5, y - h * .85, h, h * 1.7, h * .18, rgb, a, stroke=st)
        circulo(cv, x, y + h * .6, st * .6, rgb, a)
    elif nome == "grafico":
        for i, hh in enumerate((.4, .75, 1.1)):
            rrect(cv, x - h * .8 + i * h * .6, y + h * .6 - hh * h, h * .4, hh * h, 4, rgb, a)
    else:
        circulo(cv, x, y, h * .6, rgb, a)


# ---------------------------------------------------------------- animação
def cl(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def prog(t, t0, d=0.35):
    return cl((t - t0) / d) if d > 0 else (1.0 if t >= t0 else 0.0)


def e_out(x):
    return 1 - (1 - x) ** 3


def e_inout(x):
    return 3 * x * x - 2 * x * x * x


def e_back(x, s=1.7):
    x -= 1
    return 1 + x * x * ((s + 1) * x + s)


def e_elast(x):
    if x <= 0 or x >= 1:
        return x
    return 2 ** (-10 * x) * math.sin((x * 10 - .75) * (2 * math.pi) / 3) + 1


def lerp(a, b, x):
    return a + (b - a) * x


def num_br(v, casas=0):
    s = f"{abs(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if v < 0 else "") + s


def valor_txt(v, prefixo="", sufixo="", casas=0):
    return f"{prefixo}{num_br(v, casas)}{sufixo}"


class Pop:
    """Escala de entrada com 'pulo'."""

    @staticmethod
    def aplicar(cv, t, t0, cx, cy, d=0.45, de=0.6):
        k = prog(t, t0, d)
        sc = lerp(de, 1, e_back(k)) if k < 1 else 1
        cv.translate(cx, cy)
        cv.scale(sc, sc)
        cv.translate(-cx, -cy)
        return e_out(prog(t, t0, d * 0.6))


# ---------------------------------------------------------------- normalização para alinhar a fala
def norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


def palavras_roteiro(rot):
    out = []
    for i, f in enumerate(rot["falas"]):
        for wd in f["texto"].split():
            out.append({"w": wd, "fala": i})
    return out


def estimar(rot):
    t = 0.35
    vel = float(rot.get("velocidade", 1.1))  # a voz do ElevenLabs vai em 1.1
    pal = palavras_roteiro(rot)
    ult = -1
    for p in pal:
        if p["fala"] != ult and ult != -1:
            t += 0.22
        ult = p["fala"]
        d = 0.13 + 0.047 * len(norm(p["w"]))
        if p["w"][-1:] in ",.?!:;…":
            d += 0.12
        d /= vel
        p["ini"], p["fim"] = t, t + d
        t += d
    return pal, t + 0.3


def alinhar(rot, whisper):
    """Usa os tempos do Whisper e o texto do roteiro (a legenda mostra o texto certo)."""
    pal = palavras_roteiro(rot)
    a = [norm(p["w"]) for p in pal]
    b = [norm(x["w"]) for x in whisper]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    m = {}
    for bl in sm.get_matching_blocks():
        for k in range(bl.size):
            m[bl.a + k] = bl.b + k
    for i, p in enumerate(pal):
        if i in m:
            p["ini"], p["fim"] = whisper[m[i]]["ini"], whisper[m[i]]["fim"]
    # interpola o que não casou
    n = len(pal)
    conhecidos = [i for i in range(n) if "ini" in pal[i]]
    if not conhecidos:
        return estimar(rot)
    fim_audio = whisper[-1]["fim"] if whisper else 0
    for i in range(n):
        if "ini" in pal[i]:
            continue
        ant = max([k for k in conhecidos if k < i], default=None)
        pro = min([k for k in conhecidos if k > i], default=None)
        t0 = pal[ant]["fim"] if ant is not None else 0.0
        t1 = pal[pro]["ini"] if pro is not None else fim_audio + 0.4
        lo = ant if ant is not None else -1
        hi_ = pro if pro is not None else n
        k = (i - lo) / (hi_ - lo)
        k2 = (i - lo + 1) / (hi_ - lo)
        pal[i]["ini"], pal[i]["fim"] = lerp(t0, t1, k), lerp(t0, t1, k2)
        pal[i]["ini"] = min(pal[i]["ini"], pal[i]["fim"])
    return pal, max(fim_audio, pal[-1]["fim"]) + 0.3


# ---------------------------------------------------------------- cenas
class Cena:
    tipo = "base"

    def __init__(self, dados, t0):
        self.d = dados
        self.t0 = t0
        self.passos = []        # (t, dados)
        self.seed = random.Random(hash(json.dumps(dados, sort_keys=True, ensure_ascii=False)) & 0xffff)

    def ativos(self, t):
        return [(tp, p) for tp, p in self.passos if tp <= t]

    def desenhar(self, cv, t):
        pass

    def selos(self, cv, t):
        sel = [(tp, p) for tp, p in self.ativos(t) if p.get("selo")]
        if not sel:
            return
        tp, p = sel[-1]
        if p.get("selo_ate") and t > p["selo_ate"]:
            return
        k = prog(t, tp, 0.4)
        s = p["selo"].upper()
        size = 64
        w = largura(s, size, 900) + 70
        cx, cy = 540, p.get("selo_y", BASE - 90 if self.tipo == "chat" else TOPO + 70)
        cv.save()
        cv.translate(cx, cy)
        cv.rotate(-6)
        sc = lerp(2.2, 1, e_out(k))
        cv.scale(sc, sc)
        rgb = cor(p.get("selo_cor") or p.get("cor"), "ruim")
        rrect(cv, -w / 2, -52, w, 104, 18, rgb, e_out(k), sombra=True)
        texto(cv, s, 0, 0, size, 900, (255, 255, 255), e_out(k))
        cv.restore()


class Titulo(Cena):
    """Texto grande que entra com pulo; cada passo empilha uma linha nova."""
    tipo = "titulo"

    def desenhar(self, cv, t):
        itens = [(tp, p) for tp, p in self.ativos(t) if p.get("texto")]
        itens = itens[-3:]
        if not itens:
            return
        n = len(itens)
        alturas = [altura_texto(p["texto"], p.get("tam", 100 if i == n - 1 else 70), 900, 920) for i, (tp, p) in enumerate(itens)]
        total = sum(alturas) + 50 * (n - 1)
        y = (TOPO + BASE) / 2 - total / 2
        for i, (tp, p) in enumerate(itens):
            ult = i == n - 1
            size = p.get("tam", 100 if ult else 70)
            a = 1 if ult else 0.45
            cv.save()
            al = Pop.aplicar(cv, t, tp, 540, y + alturas[i] / 2) if ult else 1
            ic = p.get("icone")
            if ic and ult:
                icone(cv, ic, 540, y - 90, 120, cor(p.get("cor"), "hi"), al)
            texto(cv, p["texto"], 540, y, size, 900, cor(p.get("cor"), "txt"), a * al, maxw=920, v="t", caixa=p.get("caixa", False))
            cv.restore()
            y += alturas[i] + 50


class Frase(Cena):
    """Estilo Apple: fundo liso, uma frase por vez, cortes secos."""
    tipo = "frase"

    def desenhar(self, cv, t):
        cv.drawColor(C(cor(self.d.get("fundo"), "preto")))
        itens = [(tp, p) for tp, p in self.ativos(t) if p.get("texto")]
        if not itens:
            return
        tp, p = itens[-1]
        k = e_out(prog(t, tp, 0.25))
        cv.save()
        sc = lerp(1.08, 1.0, k)
        cv.translate(540, 810); cv.scale(sc, sc); cv.translate(-540, -810)
        texto(cv, p["texto"], 540, 810, p.get("tam", 108), 900, cor(p.get("cor"), "branco"), k, maxw=900)
        cv.restore()


class Chat(Cena):
    """Conversa de WhatsApp animada."""
    tipo = "chat"
    BG, TOP, OUT, IN, TX, SUBT = (11, 20, 26), (32, 44, 51), (0, 92, 75), (32, 44, 51), (233, 237, 239), (134, 150, 160)

    def desenhar(self, cv, t):
        x0, y0, w, h = 70, TOPO - 40, 940, BASE - TOPO + 60
        rrect(cv, x0, y0, w, h, 46, self.BG, sombra=True)
        cv.save()
        cv.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y0, w, h), 46, 46))
        digit = self._digitando(t)
        cv.save(); cv.clipRect(skia.Rect.MakeXYWH(x0, y0 + 150, w, h - 150))
        # mensagens
        msgs = []
        for tp, p in self.passos:
            if p.get("msg"):
                apar = tp + (0.55 if p.get("de", "ele") == "ele" and p.get("digitando", True) else 0)
                if apar <= t:
                    msgs.append((apar, p))
            elif p.get("aviso") and tp <= t:
                msgs.append((tp, p))
        y = y0 + 190
        blocos = []
        for apar, p in msgs:
            if p.get("aviso"):
                hh = 70
            else:
                hh = altura_texto(p["msg"], 38, 500, 560, 1.25) + 70
            blocos.append((apar, p, hh))
        total = sum(b[2] + 22 for b in blocos)
        desloc = max(0, total - (h - 230))
        y -= desloc
        for apar, p, hh in blocos:
            k = e_back(prog(t, apar, 0.35))
            a = e_out(prog(t, apar, 0.2))
            if p.get("aviso"):
                s = p["aviso"]
                ww = largura(s, 28, 700) + 50
                rrect(cv, 540 - ww / 2, y + 10, ww, 52, 16, (24, 34, 40), a)
                texto(cv, s, 540, y + 36, 28, 700, cor(p.get("cor"), "hi"), a)
            else:
                eu = p.get("de", "ele") == "eu"
                linhas = quebrar(p["msg"], 38, 500, 560)
                f = F(38, 500)
                lw = max(sum(largura(tk, 38, 500) for pw in ln for tk, _ in pw) + f.measureText(" ") * (len(ln) - 1) for ln in linhas)
                bw = max(lw + 60, 200)
                bx = x0 + w - 40 - bw if eu else x0 + 40
                cv.save()
                cx = bx + (bw if eu else 0)
                cv.translate(cx, y + hh); cv.scale(k, k); cv.translate(-cx, -(y + hh))
                rrect(cv, bx, y, bw, hh, 26, self.OUT if eu else self.IN, a)
                texto(cv, p["msg"], bx + 30, y + 22, 38, 500, self.TX, a, alinhar="e", maxw=560, lh=1.25, v="t")
                hora = p.get("hora", "")
                info = hora + ("  ✓✓" if eu else "")
                texto(cv, hora, bx + bw - 30 - (40 if eu else 0), y + hh - 26, 24, 500, self.SUBT, a, alinhar="d")
                if eu:
                    lido = p.get("lido", False)
                    lido_t = p.get("lido_em")
                    azul = lido and (lido_t is None or t >= apar + 0.8)
                    ck = (83, 189, 235) if azul else self.SUBT
                    icone(cv, "check", bx + bw - 52, y + hh - 34, 22, ck, a)
                    icone(cv, "check", bx + bw - 40, y + hh - 34, 22, ck, a)
                marca = p.get("marca")
                if marca:
                    km = e_back(prog(t, apar + 0.5, 0.35))
                    mc = FIXAS["ruim"] if marca == "erro" else FIXAS["bom"]
                    mx = bx - 50 if eu else bx + bw + 50
                    circulo(cv, mx, y + hh / 2, 34 * km, mc)
                    icone(cv, "x" if marca == "erro" else "check", mx, y + hh / 2, 36 * km, (255, 255, 255))
                cv.restore()
            y += hh + 22
        if digit:
            yy = min(y, y0 + h - 100)
            rrect(cv, x0 + 40, yy, 150, 70, 26, self.IN)
            for i in range(3):
                ph = (t * 6 + i * 1.2) % (2 * math.pi)
                circulo(cv, x0 + 80 + i * 35, yy + 35 - 6 * max(0, math.sin(ph)), 9, self.SUBT)
        cv.restore()
        # cabeçalho
        rrect(cv, x0, y0, w, 150, 0, self.TOP)
        circulo(cv, x0 + 95, y0 + 75, 42, (100, 120, 130))
        icone(cv, "pessoa", x0 + 95, y0 + 80, 52, (200, 210, 215))
        texto(cv, self.d.get("contato", "Paciente"), x0 + 160, y0 + 58, 40, 700, self.TX, alinhar="e", maxw=700)
        on = [p for tp, p in self.ativos(t) if p.get("online") is not None]
        sub = self.d.get("status", "online")
        if on:
            sub = on[-1]["online"] if isinstance(on[-1]["online"], str) else ("online" if on[-1]["online"] else "visto por último hoje")
        texto(cv, "digitando..." if digit else sub, x0 + 160, y0 + 104, 28, 500, (0, 200, 140) if digit else self.SUBT, alinhar="e")
        cv.restore()

    def _digitando(self, t):
        for tp, p in self.passos:
            if p.get("msg") and p.get("de", "ele") == "ele" and p.get("digitando", True) and tp <= t < tp + 0.55:
                return True
            if p.get("digitando") == "sim" and tp <= t < tp + p.get("dur", 1.5):
                return True
        return False


class Conta(Cena):
    """Fita de calculadora: linhas que entram e um total que conta até o valor."""
    tipo = "conta"

    def desenhar(self, cv, t):
        linhas = [(tp, p) for tp, p in self.ativos(t) if "rotulo" in p and not p.get("total")]
        tot = [(tp, p) for tp, p in self.ativos(t) if p.get("total")]
        x0, w = 110, 860
        alt = 170 + len(linhas) * 105 + (230 if tot else 0)
        y0 = (TOPO + BASE) / 2 - alt / 2 - 20
        rrect(cv, x0, y0, w, alt, 34, T["card"], sombra=True)
        texto(cv, self.d.get("titulo", "A CONTA").upper(), 540, y0 + 75, 40, 900, (120, 130, 128), maxw=780)
        y = y0 + 150
        for i, (tp, p) in enumerate(linhas):
            k = e_out(prog(t, tp, 0.35))
            yy = y + (1 - k) * 40
            op = p.get("op", "")
            texto(cv, (op + " " if op else "") + p["rotulo"], x0 + 50, yy + 35, 40, 600, T["cardtxt"], k, alinhar="e", maxw=480)
            texto(cv, self._val(p, t, tp), x0 + w - 50, yy + 35, 46, 900, cor(p.get("cor"), "cardtxt") if p.get("cor") else T["cardtxt"], k, alinhar="d", maxw=360)
            pa = skia.Path(); pa.moveTo(x0 + 40, yy + 90); pa.lineTo(x0 + w - 40, yy + 90)
            pp = P((220, 222, 220), k, stroke=3)
            pp.setPathEffect(skia.DashPathEffect.Make([14, 10], 0))
            cv.drawPath(pa, pp)
            y += 105
        if tot:
            tp, p = tot[-1]
            k = e_out(prog(t, tp, 0.3))
            rgb = cor(p.get("cor"), "ruim")
            rrect(cv, x0 + 30, y + 10, w - 60, 190, 26, rgb, 0.12 * k)
            texto(cv, p.get("rotulo", "TOTAL").upper(), 540, y + 55, 34, 800, rgb, k, maxw=760)
            cv.save()
            pulso = 1 + 0.06 * math.sin(max(0, t - tp - 0.9) * 8) * math.exp(-max(0, t - tp - 0.9) * 2) if t > tp + 0.9 else 1
            cv.translate(540, y + 135); cv.scale(pulso, pulso); cv.translate(-540, -(y + 135))
            texto(cv, self._val(p, t, tp, campo="total", d=0.9), 540, y + 135, 92, 900, rgb, k, maxw=800)
            cv.restore()

    def _val(self, p, t, tp, campo="valor", d=0.6):
        v = p.get(campo)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            k = e_out(prog(t, tp, d))
            return valor_txt(v * k, p.get("prefixo", self.d.get("prefixo", "")), p.get("sufixo", self.d.get("sufixo", "")), p.get("casas", 0))
        return str(v if v is not None else "")


class Barras(Cena):
    """Barras horizontais que crescem; passos podem trocar os valores (corrida)."""
    tipo = "barras"

    def desenhar(self, cv, t):
        bars = self.d.get("barras", [])
        if not bars:
            return
        vals0 = [b.get("valor", 0) for b in bars]
        # estado: quais aparecem e valores atuais
        vis = set()
        estados = [(self.t0, [0] * len(bars), vals0)]
        cur = list(vals0)
        dest = None
        rot = self.d.get("rotulo")
        for tp, p in self.passos:
            if tp > t:
                break
            m = p.get("mostrar")
            if m == "todas" or m == "all":
                vis.update(range(len(bars)))
            elif isinstance(m, int):
                vis.add(m)
            if p.get("valores"):
                estados.append((tp, list(cur), p["valores"]))
                cur = list(p["valores"])
            if "destacar" in p:
                dest = p["destacar"]
            if p.get("rotulo"):
                rot = p["rotulo"]
        if not self.passos or all(("mostrar" not in p) for _, p in self.passos):
            vis.update(range(len(bars)))
        tpv, de, para = estados[-1]
        k = e_inout(prog(t, tpv, 0.9))
        vals = [lerp(a, b, k) for a, b in zip(de, para)] if len(estados) > 1 else para
        mx = self.d.get("max") or max(max(v for _, _, vv in estados for v in vv), 1)
        titulo = self.d.get("titulo", "")
        if titulo:
            texto(cv, titulo, 540, TOPO + 30, 54, 900, T["txt"], maxw=940)
        if rot:
            texto(cv, rot, 540, TOPO + 110, 40, 700, FIXAS["hi"], maxw=940)
        n = len(bars)
        bh = min(190, (BASE - TOPO - 220) / n - 30)
        ordem = sorted(range(n), key=lambda i: -vals[i]) if self.d.get("ordenar") else list(range(n))
        pos = {i: r for r, i in enumerate(ordem)}
        ytop = max(TOPO + 200, (TOPO + BASE) / 2 - n * (bh + 34) / 2 + 40)
        for i, b in enumerate(bars):
            if i not in vis:
                continue
            tv = min([tp for tp, p in self.passos if p.get("mostrar") in (i, "todas", "all")] or [self.t0])
            kk = e_out(prog(t, tv, 0.7))
            y = ytop + pos[i] * (bh + 34)
            rgb = cor(b.get("cor"), "acc")
            wmax = 760
            ww = max(8, wmax * (vals[i] / mx) * kk)
            texto(cv, b.get("nome", ""), 80, y - 2, 34, 700, T["sub"], kk, alinhar="e", v="t", maxw=900)
            yb = y + 44
            a = 1 if dest is None or dest == i else 0.35
            rrect(cv, 80, yb, ww, bh - 44, 16, rgb, a * kk)
            texto(cv, valor_txt(vals[i] * kk, self.d.get("prefixo", ""), self.d.get("sufixo", "")), 80 + ww + 20, yb + (bh - 44) / 2, 40, 900, T["txt"], kk * a, alinhar="e")


class Split(Cena):
    """Tela dividida: erro x acerto (ou A x B)."""
    tipo = "split"

    def desenhar(self, cv, t):
        lados = {"esq": self.d.get("esq", {}), "dir": self.d.get("dir", {})}
        k0 = e_out(prog(t, self.t0, 0.4))
        for j, (lado, info) in enumerate(lados.items()):
            x = 60 + j * 500
            rgb = cor(info.get("cor"), "ruim" if lado == "esq" else "bom")
            rrect(cv, x, TOPO, 460, BASE - TOPO, 34, rgb, 0.13 * k0)
            rrect(cv, x, TOPO, 460, 120, 34, rgb, k0)
            texto(cv, info.get("titulo", "").upper(), x + 230, TOPO + 60, 44, 900, (255, 255, 255), k0, maxw=420)
            itens = [(tp, p) for tp, p in self.ativos(t) if p.get("lado") == lado and p.get("texto")]
            y = TOPO + 160
            for tp, p in itens:
                k = e_back(prog(t, tp, 0.4))
                a = e_out(prog(t, tp, 0.25))
                hh = altura_texto(p["texto"], 42, 700, 320, 1.2) + 44
                cv.save()
                cv.translate(x + 230, y + hh / 2); cv.scale(k, k); cv.translate(-(x + 230), -(y + hh / 2))
                rrect(cv, x + 20, y, 420, hh, 22, T["card"], a)
                icone(cv, "x" if lado == "esq" and not info.get("neutro") else ("check" if not info.get("neutro") else "seta"), x + 58, y + hh / 2, 36, rgb, a)
                texto(cv, p["texto"], x + 92, y + 22, 42, 700, T["cardtxt"], a, alinhar="e", maxw=320, lh=1.2, v="t")
                cv.restore()
                y += hh + 18
        res = [(tp, p) for tp, p in self.ativos(t) if p.get("resultado")]
        if res:
            tp, p = res[-1]
            for j, lado in enumerate(("esq", "dir")):
                s = p["resultado"].get(lado)
                if not s:
                    continue
                k = e_back(prog(t, tp + j * 0.35, 0.45))
                x = 60 + j * 500 + 230
                rgb = cor(lados[lado].get("cor"), "ruim" if lado == "esq" else "bom")
                cv.save(); cv.translate(x, BASE - 90); cv.scale(k, k); cv.rotate(-4)
                rrect(cv, -210, -55, 420, 110, 24, rgb, sombra=True)
                texto(cv, s.upper(), 0, 0, 40, 900, (255, 255, 255), maxw=390)
                cv.restore()


class Quiz(Cena):
    tipo = "quiz"

    def desenhar(self, cv, t):
        op = self.d.get("opcoes", [])
        certa = self.d.get("certa", 0)
        timer = next(((tp, p) for tp, p in self.ativos(t) if p.get("acao") == "timer"), None)
        rev = next(((tp, p) for tp, p in self.ativos(t) if p.get("acao") == "revelar"), None)
        expl = [(tp, p) for tp, p in self.ativos(t) if p.get("explica")]
        k0 = e_out(prog(t, self.t0, 0.4))
        hq = texto(cv, self.d.get("pergunta", ""), 540, TOPO + 40, 62, 900, T["txt"], k0, maxw=940, v="t")
        y = TOPO + 100 + hq
        letras = "ABCD"
        for i, o in enumerate(op):
            k = e_back(prog(t, self.t0 + 0.25 + i * 0.18, 0.4))
            rgb, a = T["card"], 1
            txt = T["cardtxt"]
            if rev:
                kr = prog(t, rev[0], 0.3)
                if i == certa:
                    rgb, txt = FIXAS["bom"], (255, 255, 255)
                else:
                    a = lerp(1, 0.35, kr)
            hh = altura_texto(o, 42, 700, 700) + 60
            cv.save(); cv.translate(540, y + hh / 2); cv.scale(k, k); cv.translate(-540, -(y + hh / 2))
            if rev and i == certa:
                s = 1 + 0.04 * math.sin(max(0, t - rev[0]) * 9) * math.exp(-max(0, t - rev[0]) * 2)
                cv.translate(540, y + hh / 2); cv.scale(s, s); cv.translate(-540, -(y + hh / 2))
            rrect(cv, 90, y, 900, hh, 28, rgb, a, sombra=True)
            circulo(cv, 160, y + hh / 2, 38, cor("acc") if not (rev and i == certa) else (255, 255, 255), a)
            texto(cv, letras[i], 160, y + hh / 2, 40, 900, (255, 255, 255) if not (rev and i == certa) else FIXAS["bom"], a)
            texto(cv, o, 230, y + 30, 42, 700, txt, a, alinhar="e", maxw=700, v="t")
            if rev and i != certa and self.d.get("riscar", True):
                icone(cv, "x", 930, y + hh / 2, 40, FIXAS["ruim"], prog(t, rev[0], 0.3))
            cv.restore()
            y += hh + 26
        if timer and not rev:
            tp, p = timer
            seg = p.get("seg", 3)
            rest = max(0, seg - (t - tp))
            k = rest / seg
            cx, cy = 540, y + 110
            circulo(cv, cx, cy, 80, T["linha"], 1, stroke=16)
            arc = skia.Path(); arc.addArc(skia.Rect.MakeXYWH(cx - 80, cy - 80, 160, 160), -90, 360 * k)
            cv.drawPath(arc, P(FIXAS["hi"], 1, stroke=16))
            texto(cv, str(math.ceil(rest)) if rest > 0 else "0", cx, cy, 80, 900, T["txt"])
        if expl:
            tp, p = expl[-1]
            texto(cv, p["explica"], 540, y + 90, 44, 700, FIXAS["hi"], e_out(prog(t, tp, 0.4)), maxw=900)


class Tier(Cena):
    tipo = "tier"
    CORES = {"S": (255, 110, 110), "A": (255, 180, 90), "B": (255, 225, 100), "C": (150, 220, 120), "D": (120, 170, 255)}

    def desenhar(self, cv, t):
        faixas = self.d.get("faixas", ["S", "A", "B", "C", "D"])
        titulo = self.d.get("titulo", "")
        texto(cv, titulo, 540, TOPO + 20, 52, 900, T["txt"], maxw=960)
        y0 = TOPO + 90
        rh = (BASE - y0) / len(faixas) - 14
        por = {f: [] for f in faixas}
        for tp, p in self.passos:
            if p.get("item") and p.get("faixa") in por:
                por[p["faixa"]].append((tp, p))
        for i, f in enumerate(faixas):
            y = y0 + i * (rh + 14)
            rgb = self.CORES.get(f, cor("acc"))
            rrect(cv, 40, y, 150, rh, 20, rgb)
            texto(cv, f, 115, y + rh / 2, 80, 900, (20, 20, 20))
            rrect(cv, 200, y, 840, rh, 20, T["bg2"], 0.9)
            x = 220
            for tp, p in por[f]:
                if tp > t:
                    continue
                k = prog(t, tp, 0.5)
                s = p["item"]
                size = 44
                lw = min(largura(s, size, 800), 760)
                bw = lw + 56
                if x + bw > 1030:
                    x = 220
                yy = y + rh / 2 - 40 + (1 - e_elast(k)) * -500
                rrect(cv, x, yy - 8, bw, 96, 18, T["card"], cl(k * 3), sombra=True)
                texto(cv, s, x + bw / 2, yy + 40, size, 800, T["cardtxt"], cl(k * 3), maxw=760)
                x += bw + 14


class Top(Cena):
    """Contagem regressiva: número gigante + o item."""
    tipo = "top"

    def desenhar(self, cv, t):
        itens = [(tp, p) for tp, p in self.ativos(t) if "n" in p]
        if self.d.get("titulo"):
            texto(cv, self.d["titulo"], 540, TOPO + 20, 46, 800, T["sub"], maxw=940)
        if not itens:
            return
        # chips dos que já passaram
        x = 540 - (len(itens) - 1) * 50
        for tp, p in itens[:-1]:
            circulo(cv, x, TOPO + 110, 36, T["bg2"])
            texto(cv, str(p["n"]), x, TOPO + 110, 36, 900, T["sub"])
            x += 100
        tp, p = itens[-1]
        k = prog(t, tp, 0.5)
        cv.save()
        sc = lerp(2.5, 1, e_out(k))
        cv.translate(540, 640); cv.scale(sc, sc); cv.translate(-540, -640)
        texto(cv, str(p["n"]), 540, 640, 360, 900, cor(p.get("cor"), "hi"), e_out(k))
        cv.restore()
        texto(cv, p.get("texto", ""), 540, 1030, 66, 900, T["txt"], e_out(prog(t, tp + 0.2, 0.4)), maxw=920)


class Mito(Cena):
    """Card com a frase, carimbo MITO/VERDADE e virada mostrando a verdade."""
    tipo = "mito"

    def desenhar(self, cv, t):
        fr = [(tp, p) for tp, p in self.ativos(t) if p.get("frase")]
        if not fr:
            return
        tf_, pf = fr[-1]
        ver = [(tp, p) for tp, p in self.ativos(t) if p.get("veredito") and tp >= tf_]
        vd = [(tp, p) for tp, p in self.ativos(t) if p.get("verdade") and tp >= tf_]
        cx, cy, w, h = 540, 800, 860, 820
        flip = 0
        if vd:
            flip = e_inout(prog(t, vd[-1][0], 0.6))
        sx = abs(math.cos(flip * math.pi))
        frente = flip < 0.5
        cv.save()
        k = e_back(prog(t, tf_, 0.45))
        cv.translate(cx, cy); cv.scale(sx * k, k); cv.translate(-cx, -cy)
        if frente:
            rrect(cv, cx - w / 2, cy - h / 2, w, h, 40, T["card"], sombra=True)
            texto(cv, "“" + pf["frase"] + "”", cx, cy - 30, 66, 900, T["cardtxt"], maxw=740)
            if ver:
                tp, p = ver[-1]
                v = p["veredito"].upper()
                rgb = FIXAS["ruim"] if v.startswith("MITO") else FIXAS["bom"]
                kk = prog(t, tp, 0.35)
                cv.save(); cv.translate(cx + 150, cy + 290); cv.rotate(-12)
                s2 = lerp(2.4, 1, e_out(kk)); cv.scale(s2, s2)
                rrect(cv, -200, -70, 400, 140, 20, rgb, e_out(kk), stroke=10)
                texto(cv, v, 0, 0, 80, 900, rgb, e_out(kk))
                cv.restore()
        else:
            tp, p = vd[-1]
            rrect(cv, cx - w / 2, cy - h / 2, w, h, 40, FIXAS["bom"], sombra=True)
            texto(cv, "A VERDADE", cx, cy - h / 2 + 90, 40, 900, (255, 255, 255), 0.85)
            texto(cv, p["verdade"], cx, cy + 20, 62, 900, (255, 255, 255), maxw=740)
        cv.restore()


class Agenda(Cena):
    """Semana com horários que enchem ou esvaziam."""
    tipo = "agenda"

    def desenhar(self, cv, t):
        dias = self.d.get("dias", ["SEG", "TER", "QUA", "QUI", "SEX"])
        if isinstance(dias, int):
            dias = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB"][:dias]
        horas = self.d.get("horas", 8)
        n = len(dias) * horas
        rng = random.Random(7)
        ordem = list(range(n))
        rng.shuffle(ordem)
        cheio = {}
        base = self.d.get("cheios", 0)
        for s in ordem[:base]:
            cheio[s] = (self.t0 - 10, FIXAS["bom"])
        ponteiro = base
        rot = None
        for tp, p in self.passos:
            if tp > t:
                break
            if p.get("encher"):
                rgb = cor(p.get("cor"), "bom")
                for j in range(p["encher"]):
                    if ponteiro < n:
                        cheio[ordem[ponteiro]] = (tp + j * min(0.08, 1.2 / p["encher"]), rgb)
                        ponteiro += 1
            if p.get("esvaziar"):
                for j in range(p["esvaziar"]):
                    if ponteiro > 0:
                        ponteiro -= 1
                        s = ordem[ponteiro]
                        cheio[s] = (-(tp + j * min(0.08, 1.2 / p["esvaziar"])), cheio.get(s, (0, FIXAS["bom"]))[1])
            if p.get("rotulo"):
                rot = (tp, p)
        titulo = self.d.get("titulo", "SUA AGENDA")
        texto(cv, titulo.upper(), 540, TOPO + 20, 50, 900, T["txt"], maxw=940)
        gx, gy = 120, TOPO + 120
        cw = (960 - 40) / len(dias)
        ch = (BASE - gy - 60) / horas
        rrect(cv, 60, gy - 30, 960, BASE - gy + 10, 30, T["card"], sombra=True)
        for i, d in enumerate(dias):
            texto(cv, d, gx + 10 + i * cw + cw / 2 - 20, gy + 10, 30, 800, (120, 130, 128))
        for hh in range(horas):
            texto(cv, f"{8 + hh}h", gx - 10, gy + 70 + hh * ch + ch / 2 - 10, 24, 700, (150, 160, 158), alinhar="d")
        ocup = 0
        for s in range(n):
            i, hh = s % len(dias), s // len(dias)
            x = gx + 10 + i * cw
            y = gy + 60 + hh * ch
            rrect(cv, x, y, cw - 14, ch - 10, 12, (236, 239, 237))
            if s in cheio:
                tp, rgb = cheio[s]
                if tp >= 0:
                    k = e_back(prog(t, tp, 0.3))
                else:
                    k = 1 - e_out(prog(t, -tp, 0.25))
                if k > 0.01:
                    ocup += 1 if tp >= 0 and t >= tp else 0
                    cx, cy = x + (cw - 14) / 2, y + (ch - 10) / 2
                    cv.save(); cv.translate(cx, cy); cv.scale(k, k); cv.translate(-cx, -cy)
                    rrect(cv, x, y, cw - 14, ch - 10, 12, rgb)
                    icone(cv, "pessoa", cx, cy, min(cw, ch) * 0.45, (255, 255, 255))
                    cv.restore()
        if self.d.get("contador", True):
            texto(cv, f"{ocup} de {n} horários ocupados", 540, BASE + 50, 34, 800, T["sub"])
        if rot:
            tp, p = rot
            k = prog(t, tp, 0.4)
            rgb = cor(p.get("cor"), "ruim")
            cv.save(); cv.translate(540, (TOPO + BASE) / 2 + 40); cv.rotate(-7)
            s = lerp(2, 1, e_out(k)); cv.scale(s, s)
            ww = largura(p["rotulo"].upper(), 70, 900) + 80
            rrect(cv, -ww / 2, -65, ww, 130, 22, rgb, e_out(k), sombra=True)
            texto(cv, p["rotulo"].upper(), 0, 0, 70, 900, (255, 255, 255), e_out(k))
            cv.restore()


class Jogo(Cena):
    """HUD de videogame: barra de vida, dano, cura e nível."""
    tipo = "jogo"

    def desenhar(self, cv, t):
        vida0 = self.d.get("vida", 50)
        vmax = self.d.get("max", 100)
        hist = [(self.t0, vida0)]
        v = vida0
        nivel = self.d.get("nivel", 1)
        nivel_t = None
        fim = None
        eventos = []
        for tp, p in self.passos:
            if tp > t:
                break
            if "delta" in p:
                v = cl(v + p["delta"], 0, vmax)
                hist.append((tp, v))
                eventos.append((tp, p))
            if "nivel" in p:
                nivel, nivel_t = p["nivel"], tp
            if p.get("fim"):
                fim = (tp, p)
        tp, alvo = hist[-1]
        ant = hist[-2][1] if len(hist) > 1 else alvo
        k = e_out(prog(t, tp, 0.6))
        atual = lerp(ant, alvo, k)
        shake = 0
        if eventos and eventos[-1][1]["delta"] < 0:
            dt = t - eventos[-1][0]
            shake = 18 * math.sin(dt * 60) * math.exp(-dt * 8) if dt < 0.6 else 0
        cv.save(); cv.translate(shake, 0)
        # personagem/consultório
        cx, cy = 540, 860
        rrect(cv, cx - 230, cy - 190, 460, 380, 40, T["bg2"])
        pa = skia.Path(); pa.moveTo(cx - 270, cy - 170); pa.lineTo(cx, cy - 330); pa.lineTo(cx + 270, cy - 170); pa.close()
        cv.drawPath(pa, P(cor("acc")))
        rrect(cv, cx - 60, cy + 40, 120, 150, 14, cor("hi"))
        for dx in (-140, 140):
            rrect(cv, cx + dx - 55, cy - 110, 110, 100, 12, (190, 230, 255))
        texto(cv, self.d.get("nome", "SEU CONSULTÓRIO").upper(), 540, cy + 235, 44, 900, T["txt"], maxw=900)
        # barra
        bx, by, bw, bh = 110, TOPO + 60, 860, 70
        texto(cv, self.d.get("rotulo", "PACIENTES ATIVOS"), bx, by - 30, 32, 800, T["sub"], alinhar="e")
        texto(cv, f"NÍVEL {nivel}", bx + bw, by - 30, 32, 900, cor("hi"), alinhar="d")
        rrect(cv, bx, by, bw, bh, 20, (0, 0, 0), 0.35)
        frac = atual / vmax
        rgb = FIXAS["bom"] if frac > 0.6 else (FIXAS["hi"] if frac > 0.3 else FIXAS["ruim"])
        rrect(cv, bx + 6, by + 6, max(0, (bw - 12) * frac), bh - 12, 16, rgb)
        texto(cv, f"{int(round(atual))}/{vmax}", bx + bw / 2, by + bh / 2, 36, 900, (255, 255, 255))
        cv.restore()
        # eventos flutuando
        for tp_, p in eventos[-3:]:
            dt = t - tp_
            if dt > 2.2:
                continue
            a = 1 - cl((dt - 1.6) / 0.6)
            d = p["delta"]
            rgb = FIXAS["bom"] if d > 0 else FIXAS["ruim"]
            y = 520 - dt * 40
            texto(cv, ("+" if d > 0 else "") + str(d), 860, y, 100, 900, rgb, a)
        if eventos:
            tp_, p = eventos[-1]
            if p.get("texto"):
                k2 = e_back(prog(t, tp_, 0.4))
                d = p["delta"]
                rgb = FIXAS["bom"] if d > 0 else FIXAS["ruim"]
                hh = altura_texto(p["texto"], 44, 800, 800) + 50
                cv.save(); cv.translate(540, 1265); cv.scale(k2, k2)
                rrect(cv, -460, -hh / 2, 920, hh, 26, rgb, 0.95, sombra=True)
                texto(cv, p["texto"], 0, 0, 44, 800, (255, 255, 255), maxw=800)
                cv.restore()
        if nivel_t is not None and t - nivel_t < 1.6:
            k3 = e_back(prog(t, nivel_t, 0.4))
            al = 1 - cl((t - nivel_t - 1.2) / 0.4)
            cv.save(); cv.translate(540, 700); cv.scale(k3, k3); cv.rotate(-5)
            rrect(cv, -330, -85, 660, 170, 30, (0, 0, 0), 0.6 * al)
            texto(cv, "LEVEL UP!", 0, 0, 120, 900, cor("hi"), al)
            cv.restore()
        if fim:
            tp_, p = fim
            k4 = e_out(prog(t, tp_, 0.4))
            cv.drawColor(C((0, 0, 0), 0.65 * k4))
            texto(cv, p["fim"].upper(), 540, 800, 130, 900, FIXAS["ruim"] if "OVER" in p["fim"].upper() else cor("hi"), k4, maxw=980)


class Plantao(Cena):
    """Plantão / breaking news."""
    tipo = "plantao"

    def desenhar(self, cv, t):
        cv.drawColor(C((18, 18, 24)))
        k0 = e_out(prog(t, self.t0, 0.35))
        rrect(cv, 0, TOPO, 1080 * k0, 130, 0, (210, 20, 30))
        texto(cv, self.d.get("tag", "PLANTÃO").upper(), 60, TOPO + 65, 66, 900, (255, 255, 255), k0, alinhar="e")
        piscar = 0.5 + 0.5 * math.sin(t * 8)
        circulo(cv, 1000, TOPO + 65, 18, (255, 255, 255), piscar * k0)
        it = [(tp, p) for tp, p in self.ativos(t) if p.get("manchete")]
        if it:
            tp, p = it[-1]
            k = e_out(prog(t, tp, 0.35))
            cv.save(); cv.translate((1 - k) * 200, 0)
            rrect(cv, 50, 480, 980, 620, 20, (255, 255, 255), k)
            rrect(cv, 50, 480, 16, 620, 0, (210, 20, 30), k)
            texto(cv, p["manchete"], 110, 790, 66, 900, (20, 20, 25), k, alinhar="e", maxw=880)
            cv.restore()
        letreiro = self.d.get("letreiro", "")
        if letreiro:
            rrect(cv, 0, BASE - 110, 1080, 100, 0, (255, 210, 63))
            s = ("  •  " + letreiro.upper()) * 4
            f = F(44, 900)
            x = -((t - self.t0) * 220) % f.measureText(("  •  " + letreiro.upper()))
            cv.save(); cv.clipRect(skia.Rect.MakeXYWH(0, BASE - 110, 1080, 100))
            cv.drawString(s, x, BASE - 45, f, P((20, 20, 20)))
            cv.restore()


class Timeline(Cena):
    tipo = "timeline"

    def desenhar(self, cv, t):
        it = [(tp, p) for tp, p in self.ativos(t) if p.get("marco")]
        if self.d.get("titulo"):
            texto(cv, self.d["titulo"], 540, TOPO + 10, 50, 900, T["txt"], maxw=940)
        y0 = TOPO + 110
        passo = 250
        tot = len(it) * passo
        desl = max(0, tot - (BASE - y0 - 60))
        alvo_desl = desl
        if it:
            k = e_inout(prog(t, it[-1][0], 0.5))
            prev = max(0, (len(it) - 1) * passo - (BASE - y0 - 60))
            desl = lerp(prev, alvo_desl, k)
        x = 130
        cv.save(); cv.clipRect(skia.Rect.MakeXYWH(0, y0 - 20, 1080, BASE - y0 + 40)); cv.translate(0, -desl)
        if it:
            yl = y0 + 40 + (len(it) - 1) * passo * 1 + e_out(prog(t, it[-1][0], 0.4)) * 0
            pa = skia.Path(); pa.moveTo(x, y0 + 40); pa.lineTo(x, yl)
            cv.drawPath(pa, P(T["linha"], 1, stroke=10))
        for i, (tp, p) in enumerate(it):
            y = y0 + 40 + i * passo
            k = e_back(prog(t, tp, 0.4))
            rgb = cor(p.get("cor"), "acc")
            circulo(cv, x, y, 34 * k, rgb)
            texto(cv, p["marco"].upper(), x + 70, y - 12, 48, 900, rgb, e_out(k), alinhar="e", maxw=760)
            if p.get("texto"):
                texto(cv, p["texto"], x + 70, y + 24, 52, 700, T["txt"], e_out(prog(t, tp + 0.15, 0.3)), alinhar="e", maxw=850, v="t")
        cv.restore()


class Funil(Cena):
    tipo = "funil"

    def desenhar(self, cv, t):
        et = self.d.get("etapas", [])
        n = len(et)
        if not n:
            return
        vis = set()
        for tp, p in self.ativos(t):
            m = p.get("mostrar")
            if m in ("todas", "all"):
                vis.update(range(n))
            elif isinstance(m, int):
                vis.add(m)
        if not any("mostrar" in p for _, p in self.passos):
            vis.update(range(n))
        y0, alt = TOPO + 40, BASE - TOPO - 80
        eh = alt / n
        for i, e in enumerate(et):
            if i not in vis:
                continue
            tv = min([tp for tp, p in self.passos if p.get("mostrar") in (i, "todas", "all")] or [self.t0])
            k = e_out(prog(t, tv, 0.5))
            wt = 980 - i * (600 / max(1, n - 1)) if n > 1 else 900
            wb = 980 - (i + 1) * (600 / max(1, n - 1)) if n > 1 else 700
            wb = max(wb, 300)
            y = y0 + i * eh
            pa = skia.Path()
            pa.moveTo(540 - wt / 2, y); pa.lineTo(540 + wt / 2, y); pa.lineTo(540 + wb / 2, y + eh - 16); pa.lineTo(540 - wb / 2, y + eh - 16); pa.close()
            rgb = cor(e.get("cor"), "acc")
            cv.save(); cv.translate(540, y); cv.scale(k, 1); cv.translate(-540, -y)
            cv.drawPath(pa, P(rgb, lerp(1, 0.55, i / max(1, n))))
            cv.restore()
            texto(cv, e.get("nome", ""), 540, y + eh * 0.36, 40, 800, (255, 255, 255), k, maxw=wb - 40)
            if e.get("valor") is not None:
                v = e["valor"]
                vt = valor_txt(v * e_out(prog(t, tv, 0.8)), self.d.get("prefixo", ""), self.d.get("sufixo", "")) if isinstance(v, (int, float)) else str(v)
                texto(cv, vt, 540, y + eh * 0.66, 50, 900, (255, 255, 255), k, maxw=wb - 40)
            # bolinhas caindo pelos lados (gente que se perde)
            if i > 0 and i in vis:
                rng = random.Random(i)
                for q in range(6):
                    ph = ((t - tv) * 0.7 + rng.random()) % 1
                    lado = -1 if q % 2 else 1
                    xx = 540 + lado * (wt / 2 + 30 + ph * 60)
                    circulo(cv, xx, y - 10 + ph * 220, 12, T["sub"], 0.6 * (1 - ph) * k)


class Celular(Cena):
    """Tela de celular com notificações ou um número grande."""
    tipo = "celular"

    def desenhar(self, cv, t):
        x0, y0, w, h = 150, TOPO - 30, 780, BASE - TOPO + 40
        rrect(cv, x0 - 16, y0 - 16, w + 32, h + 32, 90, (20, 20, 20), sombra=True)
        g = skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y0 + h)], [C((40, 90, 120)), C((110, 60, 140))])
        p = skia.Paint(AntiAlias=True); p.setShader(g)
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y0, w, h), 76, 76), p)
        rrect(cv, 540 - 90, y0 + 22, 180, 44, 22, (10, 10, 10))
        texto(cv, self.d.get("hora", "09:41"), 540, y0 + 190, 130, 700, (255, 255, 255), 0.95)
        texto(cv, self.d.get("data", "segunda-feira"), 540, y0 + 290, 32, 600, (255, 255, 255), 0.8)
        nots = [(tp, p) for tp, p in self.ativos(t) if p.get("notif")]
        y = y0 + 380
        for tp, pp in nots[-5:]:
            nn = pp["notif"]
            k = e_back(prog(t, tp, 0.4))
            hh = 200
            cv.save(); cv.translate(0, (1 - k) * -80)
            rrect(cv, x0 + 30, y, w - 60, hh, 32, (255, 255, 255), 0.92 * cl(k * 2), sombra=True)
            app = nn.get("app", "WhatsApp")
            ac = {"WhatsApp": (37, 211, 102), "Instagram": (225, 48, 108), "Agenda": (255, 90, 80), "Banco": (130, 80, 220)}.get(app, cor("acc"))
            rrect(cv, x0 + 60, y + 30, 56, 56, 14, ac)
            texto(cv, app.upper(), x0 + 135, y + 46, 26, 800, (120, 120, 120), alinhar="e")
            texto(cv, nn.get("titulo", ""), x0 + 135, y + 86, 38, 800, (20, 20, 20), alinhar="e", maxw=w - 200)
            texto(cv, nn.get("texto", ""), x0 + 60, y + 150, 36, 500, (60, 60, 60), alinhar="e", maxw=w - 120)
            cv.restore()
            y += hh + 20
        st = [(tp, p) for tp, p in self.ativos(t) if p.get("numero") is not None]
        if st:
            tp, pp = st[-1]
            k = e_out(prog(t, tp, 1.0))
            v = pp["numero"]
            rrect(cv, x0 + 40, y0 + h - 420, w - 80, 360, 40, (0, 0, 0), 0.35)
            texto(cv, pp.get("rotulo", "").upper(), 540, y0 + h - 340, 34, 800, (255, 255, 255), 0.85, maxw=w - 120)
            texto(cv, valor_txt(v * k, pp.get("prefixo", ""), pp.get("sufixo", "")) if isinstance(v, (int, float)) else str(v), 540, y0 + h - 220, 110, 900, cor(pp.get("cor"), "hi"), maxw=w - 100)


class AntesDepois(Cena):
    tipo = "antes_depois"

    def _lado(self, cv, info, rgb):
        rrect(cv, 80, TOPO, 920, BASE - TOPO, 36, rgb)
        texto(cv, info.get("titulo", "").upper(), 540, TOPO + 80, 56, 900, (255, 255, 255), maxw=860)
        y = TOPO + 170
        for ln in info.get("linhas", []):
            hh = altura_texto(ln, 44, 700, 760) + 40
            rrect(cv, 130, y, 820, hh, 22, (255, 255, 255), 0.95)
            texto(cv, ln, 160, y + 20, 44, 700, (25, 25, 25), alinhar="e", maxw=760, v="t")
            y += hh + 20

    def desenhar(self, cv, t):
        rev = next((tp for tp, p in self.ativos(t) if p.get("revelar")), None)
        k = e_inout(prog(t, rev, 1.0)) if rev is not None else 0
        self._lado(cv, self.d.get("antes", {}), FIXAS["ruim"])
        if k > 0:
            xc = 1000 - 920 * k
            cv.save(); cv.clipRect(skia.Rect.MakeXYWH(xc, 0, 1080, H))
            self._lado(cv, self.d.get("depois", {}), FIXAS["bom"])
            cv.restore()
            if k < 1:
                rrect(cv, xc - 6, TOPO - 20, 12, BASE - TOPO + 40, 6, (255, 255, 255))
                circulo(cv, xc, (TOPO + BASE) / 2, 50, (255, 255, 255))
                icone(cv, "seta", xc, (TOPO + BASE) / 2, 50, (30, 30, 30))


class Final(Cena):
    tipo = "final"
    _av = None

    def desenhar(self, cv, t):
        k = e_out(prog(t, self.t0, 0.5))
        rrect(cv, 90, 560, 900, 640, 50, T["card"], k, sombra=True)
        if Final._av is None:
            try:
                Final._av = skia.Image.open(os.path.join(RAIZ, "assets", "avatar.jpg"))
            except Exception:
                Final._av = False
        cy = 560
        if Final._av:
            cv.save()
            cv.clipRRect(skia.RRect.MakeOval(skia.Rect.MakeXYWH(540 - 110, cy - 110, 220, 220)))
            cv.drawImageRect(Final._av, skia.Rect.MakeXYWH(540 - 110, cy - 110, 220, 220), skia.SamplingOptions(skia.FilterMode.kLinear), P(a=k))
            cv.restore()
            circulo(cv, 540, cy, 112, (255, 255, 255), k, stroke=8)
        texto(cv, self.d.get("titulo", "Segue para a próxima"), 540, 820, 64, 900, T["cardtxt"], k, maxw=800)
        texto(cv, self.d.get("sub", "Marketing e vendas para nutricionistas"), 540, 960, 36, 600, (100, 110, 108), k, maxw=800)
        rrect(cv, 220, 1050, 640, 100, 50, cor("acc"), k)
        texto(cv, HANDLE, 540, 1100, 40, 800, (255, 255, 255), k, maxw=600)


CENAS = {c.tipo: c for c in [Titulo, Frase, Chat, Conta, Barras, Split, Quiz, Tier, Top, Mito, Agenda, Jogo, Plantao, Timeline, Funil, Celular, AntesDepois, Final]}
TELAS = set()
sys.path.insert(0, AQUI)
import telas as _telas  # noqa: E402  (cenas na tela do app)
_telas.registrar(sys.modules[__name__])


# ---------------------------------------------------------------- montagem
class Video:
    def __init__(self, rot, palavras=None, duracao_audio=None):
        global T
        T = dict(TEMAS.get(rot.get("tema", "escuro"), TEMAS["escuro"]))
        self.rot = rot
        if palavras:
            self.pal, self.dur = alinhar(rot, palavras)
        else:
            self.pal, self.dur = estimar(rot)
            if duracao_audio and self.pal:
                # sem tempos do Whisper: estica a estimativa até o tamanho do áudio
                k = max(0.3, duracao_audio - 0.15) / max(0.1, self.pal[-1]["fim"])
                for p in self.pal:
                    p["ini"] *= k; p["fim"] *= k
                self.dur = duracao_audio + 0.3
        if duracao_audio:
            self.dur = max(self.dur, duracao_audio + 0.2)
        self.falas = []
        for i, f in enumerate(rot["falas"]):
            ps = [p for p in self.pal if p["fala"] == i]
            self.falas.append(dict(f, ini=ps[0]["ini"] if ps else 0, fim=ps[-1]["fim"] if ps else 0, pal=ps))
        self.destaques = {norm(d) for d in rot.get("destaques", [])}
        self.cenas = []
        self.eventos = []    # (t, tipo de som)
        atual = None
        for f in self.falas:
            if f.get("cena"):
                dados = dict(f["cena"])
                tipo = dados.get("tipo", "titulo")
                cls = CENAS.get(tipo, Titulo)
                atual = cls(dados, max(0, f["ini"] - 0.12))
                self.cenas.append(atual)
                self.eventos.append((atual.t0, "whoosh"))
                if dados.get("passo"):
                    self._passo(atual, dados["passo"], f)
            if atual is None:
                atual = Titulo({"tipo": "titulo"}, 0)
                self.cenas.append(atual)
            ps = f.get("passo")
            if ps:
                for p in (ps if isinstance(ps, list) else [ps]):
                    self._passo(atual, p, f)
        fim_final = rot.get("final", {"titulo": "Segue para mais", "sub": "Marketing e vendas para nutricionistas"})
        if fim_final and not any(c.tipo == "final" for c in self.cenas):
            c = Final(fim_final, self.dur)
            self.cenas.append(c)
            self.eventos.append((c.t0, "ding"))
            self.dur += 2.2
        elif self.cenas and self.cenas[-1].tipo == "final":
            self.dur = max(self.dur, self.cenas[-1].t0 + 2.2)
        for i, c in enumerate(self.cenas):
            c.t1 = self.cenas[i + 1].t0 if i + 1 < len(self.cenas) else self.dur + 1

    def _passo(self, cena, p, f):
        tp = f["ini"]
        if p.get("em"):
            alvo = norm(str(p["em"]).split()[0])
            for w in f["pal"]:
                if norm(w["w"]).startswith(alvo):
                    tp = w["ini"]
                    break
        tp += p.get("atraso", 0)
        cena.passos.append((tp, p))
        cena.passos.sort(key=lambda x: x[0])
        som = p.get("som")
        if som is None:
            if p.get("selo") or p.get("veredito") or p.get("total") or p.get("acao") == "revelar" or p.get("rotulo") and cena.tipo == "agenda":
                som = "ding" if not (p.get("veredito", "").upper().startswith("MITO") or p.get("cor") == "ruim" or p.get("selo_cor") == "ruim") else "buzz"
            elif p.get("msg"):
                som = "msg"
            elif p.get("delta") is not None:
                som = "buzz" if p["delta"] < 0 else "coin"
            elif p.get("acao") == "timer":
                som = "tick"
            else:
                som = "pop"
        if som:
            self.eventos.append((tp + (0.55 if p.get("msg") and p.get("de", "ele") == "ele" and p.get("digitando", True) else 0), som))

    # ---- desenho de um quadro
    def fundo(self, cv, t):
        g = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, H)], [C(T["bg"]), C(T["bg2"])])
        p = skia.Paint(); p.setShader(g)
        cv.drawRect(skia.Rect.MakeWH(W, H), p)
        # pontinhos de textura que se mexem devagar
        rng = random.Random(3)
        for i in range(36):
            x = (rng.random() * W + t * (8 + rng.random() * 10)) % W
            y = (rng.random() * H - t * (5 + rng.random() * 8)) % H
            circulo(cv, x, y, 3 + rng.random() * 5, T["txt"], 0.05)

    def legenda_palavra(self, cv, t):
        """Uma palavra por vez, branca com contorno preto (estilo do vídeo do perfil)."""
        atual = None
        for x in self.pal:
            if x["ini"] - 0.03 <= t <= x["fim"] + 0.12:
                atual = x
        if atual is None:
            return
        s = re.sub(r"^[\"'“”(]+|[\"'“”).,;:!?…]+$", "", atual["w"])
        s = "".join(ch for ch in s if not eh_emoji(ch))
        if not s:
            return
        dest = norm(atual["w"]) in self.destaques
        k = e_back(prog(t, atual["ini"] - 0.03, 0.16))
        size = 104
        fnt = F(size, 900)
        lw = fnt.measureText(s)
        sc = min(1.0, 960 / lw) * lerp(0.75, 1, k)
        y = self.rot.get("legenda_y", 1330)
        cv.save(); cv.translate(540, y); cv.scale(sc, sc)
        cv.drawString(s, -lw / 2, size * 0.35, fnt, P((0, 0, 0), 1, stroke=22))
        cv.drawString(s, -lw / 2, size * 0.35, fnt, P(FIXAS["hi"] if dest else (255, 255, 255)))
        cv.restore()

    def legenda(self, cv, t):
        if self.rot.get("estilo") == "tela":
            return self.legenda_palavra(cv, t)
        f = None
        for x in self.falas:
            if x["ini"] - 0.05 <= t <= x["fim"] + 0.35:
                f = x
        if not f or not f["pal"]:
            return
        # blocos de até 4 palavras / 24 letras
        blocos, cur = [], []
        for w in f["pal"]:
            if cur and (len(cur) >= 4 or sum(len(x["w"]) for x in cur) + len(w["w"]) > 22 or cur[-1]["w"][-1:] in ".?!,:"):
                blocos.append(cur); cur = []
            cur.append(w)
        if cur:
            blocos.append(cur)
        bl = None
        for b in blocos:
            if b[0]["ini"] - 0.05 <= t:
                bl = b
        if bl is None or t > bl[-1]["fim"] + 0.35 and bl is blocos[-1] and t > f["fim"] + 0.3:
            return
        size = 68
        fnt = F(size, 900)
        esp = fnt.measureText(" ") * 1.6
        ws = ["".join(ch for ch in w["w"].upper() if not eh_emoji(ch)) for w in bl]
        lw = sum(fnt.measureText(s) for s in ws) + esp * (len(ws) - 1)
        sc = min(1, 960 / lw)
        x = 540 - lw * sc / 2
        cv.save(); cv.translate(x, LEG_Y); cv.scale(sc, sc)
        xx = 0
        for w, s in zip(bl, ws):
            ativo = w["ini"] - 0.03 <= t
            agora = w["ini"] - 0.03 <= t <= w["fim"] + 0.05
            dest = norm(w["w"]) in self.destaques
            k = e_back(prog(t, w["ini"] - 0.03, 0.18))
            rgb = FIXAS["hi"] if dest else (255, 255, 255)
            a = 1 if ativo else 0.0
            if a > 0:
                cw = fnt.measureText(s)
                cv.save()
                s_ = lerp(0.7, 1.0, k) * (1.08 if agora else 1)
                cv.translate(xx + cw / 2, 0); cv.scale(s_, s_); cv.translate(-(xx + cw / 2), 0)
                if agora and not dest:
                    rrect(cv, xx - 12, -size * 0.62, cw + 24, size * 1.2, 16, cor("acc"), 0.95)
                pc = P((0, 0, 0), 0.85, stroke=14)
                cv.drawString(s, xx, size * 0.35, fnt, pc)
                cv.drawString(s, xx, size * 0.35, fnt, P(rgb, 1))
                cv.restore()
            xx += fnt.measureText(s) + esp
        cv.restore()

    def moldura(self, cv, t):
        if self.rot.get("estilo") == "tela":
            return
        # marca d'água e barra de progresso
        texto(cv, HANDLE, 540, 150, 30, 700, T["txt"], 0.55)
        rrect(cv, 0, 0, W * cl(t / self.dur), 10, 0, cor("acc"), 0.9)

    def quadro(self, cv, t):
        self.fundo(cv, t)
        ativas = [c for c in self.cenas if c.t0 - 0.0 <= t < c.t1 + 0.3]
        for c in ativas:
            sai = prog(t, c.t1, 0.3) if t >= c.t1 else 0
            entra = prog(t, c.t0, 0.3)
            if sai >= 1:
                continue
            cv.save()
            a = 1 - sai
            if a < 1:
                cv.saveLayer(None, skia.Paint(Alphaf=a))
            dx = (1 - e_out(entra)) * 120 - e_out(sai) * 120
            sc = 1 + (1 - e_out(entra)) * 0.04
            cv.translate(540 + dx, 810); cv.scale(sc, sc); cv.translate(-540, -810)
            c.desenhar(cv, t)
            c.selos(cv, t)
            if a < 1:
                cv.restore()
            cv.restore()
        self.moldura(cv, t)
        self.legenda(cv, t)

    def png(self, t, caminho, escala=1.0):
        s = skia.Surface(W, H)
        self.quadro(s.getCanvas(), t)
        img = s.makeImageSnapshot()
        if escala != 1:
            s2 = skia.Surface(int(W * escala), int(H * escala))
            s2.getCanvas().drawImageRect(img, skia.Rect.MakeWH(W * escala, H * escala), skia.SamplingOptions(skia.FilterMode.kLinear))
            img = s2.makeImageSnapshot()
        img.save(caminho)


# ---------------------------------------------------------------- áudio
SR = 44100


def _env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))
    return e


def som(nome):
    rng = np.random.default_rng(abs(hash(nome)) % 1000)
    if nome == "whoosh":
        n = int(SR * .55); x = rng.standard_normal(n)
        x = np.convolve(x, np.ones(30) / 30, mode="same")
        tt = np.arange(n) / n
        return x * np.sin(np.pi * tt) ** 2 * 0.9
    if nome == "pop":
        n = int(SR * .12); t = np.arange(n) / SR
        f = 900 * np.exp(-t * 30) + 300
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, .002, .04) * .5
    if nome == "msg":
        n = int(SR * .25); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 1320 * t) * (t < .09) + np.sin(2 * np.pi * 1760 * t) * (t >= .09)) * _env(n, .002, .12) * .3
    if nome == "ding":
        n = int(SR * .9); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 1046 * t) + .5 * np.sin(2 * np.pi * 1568 * t) + .25 * np.sin(2 * np.pi * 2093 * t)) * _env(n, .003, .3) * .28
    if nome == "buzz":
        n = int(SR * .35); t = np.arange(n) / SR
        return np.sign(np.sin(2 * np.pi * 110 * t)) * _env(n, .005, .12) * .18
    if nome == "coin":
        n = int(SR * .4); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 988 * t) * (t < .08) + np.sin(2 * np.pi * 1319 * t) * (t >= .08)) * _env(n, .002, .15) * .3
    if nome == "tick":
        out = np.zeros(int(SR * 3.1))
        for k in range(3):
            n = int(SR * .05); t = np.arange(n) / SR
            s = np.sin(2 * np.pi * 2000 * t) * _env(n, .001, .01) * .35
            out[int(k * SR):int(k * SR) + n] += s
        return out
    return np.zeros(10)


def trilha(dur, estilo="leve"):
    """Trilha discreta gerada aqui (sem direitos autorais): acordes suaves + batida leve."""
    n = int(SR * (dur + 1))
    t = np.arange(n) / SR
    out = np.zeros(n)
    bpm = 96
    beat = 60 / bpm
    acordes = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7), (164.8, 207.7, 246.9)]
    dur_acorde = beat * 8
    for i in range(int(dur / dur_acorde) + 2):
        a = acordes[i % 4]
        i0 = int(i * dur_acorde * SR)
        i1 = min(n, int((i + 1) * dur_acorde * SR) + int(SR * .5))
        if i0 >= n:
            break
        tt = t[i0:i1] - t[i0]
        env = np.minimum(1, tt / .6) * np.minimum(1, (tt[-1] - tt + 1e-3) / .6)
        for f in a:
            out[i0:i1] += (np.sin(2 * np.pi * f * tt) + .3 * np.sin(2 * np.pi * f * 2 * tt)) * env * .05
    # batida
    for k in range(int(dur / beat) + 1):
        i0 = int(k * beat * SR)
        if i0 >= n:
            break
        m = int(SR * .18)
        tt = np.arange(min(m, n - i0)) / SR
        if k % 2 == 0:
            out[i0:i0 + len(tt)] += np.sin(2 * np.pi * (55 + 80 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 18) * .22
        hh = np.random.default_rng(k).standard_normal(len(tt)) * np.exp(-tt * 60) * .03
        j0 = i0 + int(beat / 2 * SR)
        if j0 + len(hh) < n:
            out[j0:j0 + len(hh)] += hh
    fade = np.minimum(1, t / 1.0) * np.minimum(1, (dur + 1 - t) / 1.5)
    return out * fade


def ler_audio(caminho):
    tmp = caminho + ".wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", caminho, "-ac", "1", "-ar", str(SR), tmp], check=True)
    with wave.open(tmp) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    os.remove(tmp)
    return x


def mixar(v, caminho_wav, voz=None):
    n = int(SR * (v.dur + 0.5))
    mix = np.zeros(n)
    tem_voz = voz is not None
    mus = trilha(v.dur) * (0.55 if tem_voz else 1.0)
    mix[:min(n, len(mus))] += mus[:n]
    cache = {}
    for tp, nome in v.eventos:
        if nome not in cache:
            cache[nome] = som(nome)
        s = cache[nome]
        i0 = int(max(0, tp - (0.25 if nome == "whoosh" else 0)) * SR)
        if i0 >= n:
            continue
        j = min(n, i0 + len(s))
        mix[i0:j] += s[:j - i0] * (0.7 if tem_voz else 1.0)
    if tem_voz:
        vz = voz[:n]
        mix[:len(vz)] += vz * 1.0
    pico = np.max(np.abs(mix)) or 1
    mix = mix / max(1.0, pico / 0.95)
    pcm = (mix * 32000).astype(np.int16)
    with wave.open(caminho_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- render
def render(v, saida, voz_path=None):
    voz = ler_audio(voz_path) if voz_path else None
    if voz is not None:
        v.dur = max(v.dur, len(voz) / SR + 0.3)
    wav = saida + ".wav"
    mixar(v, wav, voz)
    nfr = int(v.dur * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", saida]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    s = skia.Surface(W, H)
    cv = s.getCanvas()
    for i in range(nfr):
        t = i / FPS
        cv.clear(skia.ColorBLACK)
        v.quadro(cv, t)
        pr.stdin.write(s.makeImageSnapshot().tobytes())
        if i % (FPS * 10) == 0:
            print(f"  {t:.0f}s de {v.dur:.0f}s", flush=True)
    pr.stdin.close()
    pr.wait()
    os.remove(wav)
    if pr.returncode != 0:
        raise SystemExit("ffmpeg falhou")
    return v.dur


def folha(v, saida, tempos=None, colunas=4):
    if not tempos:
        # um quadro no meio de cada cena + o fim
        tempos = []
        for c in v.cenas:
            fim = min(c.t1, v.dur)
            ult = max([tp for tp, _ in c.passos if tp < fim] or [c.t0])
            tempos.append(min(fim - 0.05, max(c.t0 + 0.8, ult + 0.9)))
    esc = 0.25
    w, h = int(W * esc), int(H * esc)
    lin = math.ceil(len(tempos) / colunas)
    S2 = skia.Surface(w * colunas, (h + 40) * lin)
    cv2 = S2.getCanvas()
    cv2.clear(C((255, 255, 255)))
    s = skia.Surface(W, H)
    for i, t in enumerate(tempos):
        s.getCanvas().clear(skia.ColorBLACK)
        v.quadro(s.getCanvas(), t)
        img = s.makeImageSnapshot()
        x, y = (i % colunas) * w, (i // colunas) * (h + 40)
        cv2.drawImageRect(img, skia.Rect.MakeXYWH(x, y + 40, w, h), skia.SamplingOptions(skia.FilterMode.kLinear))
        cv2.drawString(f"{t:.1f}s", x + 8, y + 30, F(24, 700), P((0, 0, 0)))
    S2.makeImageSnapshot().save(saida, skia.kJPEG, 85)
    return tempos


# ---------------------------------------------------------------- validação
def validar(rot):
    erros = []
    if not rot.get("falas"):
        erros.append("roteiro sem falas")
    for i, f in enumerate(rot.get("falas", [])):
        if not f.get("texto"):
            erros.append(f"fala {i + 1} sem texto")
        c = f.get("cena")
        if c and c.get("tipo") not in CENAS:
            erros.append(f"fala {i + 1}: cena '{c.get('tipo')}' não existe ({', '.join(CENAS)})")
    if rot.get("falas") and not rot["falas"][0].get("cena"):
        erros.append("a primeira fala precisa abrir uma cena")
    return erros


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["validar", "quadros", "render", "png"])
    ap.add_argument("roteiro")
    ap.add_argument("--saida")
    ap.add_argument("--audio")
    ap.add_argument("--palavras")
    ap.add_argument("--tempos", help="tempos separados por vírgula (quadros/png)")
    a = ap.parse_args()
    rot = json.load(open(a.roteiro, encoding="utf-8"))
    if "roteiro" in rot and "falas" not in rot:
        rot = rot["roteiro"]
    er = validar(rot)
    if er:
        print("ERROS:\n- " + "\n- ".join(er))
        sys.exit(1)
    if a.acao == "validar":
        print("ok")
        return
    pal = json.load(open(a.palavras, encoding="utf-8")) if a.palavras else None
    if isinstance(pal, dict):
        pal = pal.get("palavras")
    dur_audio = None
    if a.audio:
        dur_audio = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.audio],
                                         capture_output=True, text=True).stdout.strip() or 0) or None
    v = Video(rot, pal, dur_audio)
    if a.acao == "quadros":
        ts = [float(x) for x in a.tempos.split(",")] if a.tempos else None
        ts = folha(v, a.saida or "folha.jpg", ts)
        print("duração", round(v.dur, 1), "s; quadros em", ", ".join(f"{x:.1f}" for x in ts))
    elif a.acao == "png":
        for x in a.tempos.split(","):
            v.png(float(x), (a.saida or "q") + f"-{x}.png")
    else:
        d = render(v, a.saida or "reel.mp4", a.audio)
        print("ok", round(d, 1), "s")


if __name__ == "__main__":
    main()
