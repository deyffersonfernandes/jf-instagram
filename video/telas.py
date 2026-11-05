"""Cenas 'na tela do app' (estilo do vídeo 'Como atrair pacientes pelo Instagram').

O vídeo inteiro é a tela do celular: o perfil do Instagram, o WhatsApp, os Stories,
a página de links e o consultório vão sendo montados na frente de quem assiste.
Registradas no estúdio por registrar(E).
"""
import math, os, random
import skia

E = None
_SF = {}

# paleta clara de app
BR, PR, CINZA, LINHA, AZUL = (255, 255, 255), (18, 18, 18), (142, 142, 142), (219, 219, 219), (0, 149, 246)
VERDE, VERM, AMAR = (37, 211, 102), (237, 73, 86), (255, 210, 63)


def SF(size, w=500):
    w = {300: 400, 400: 400, 500: 500, 600: 600, 700: 700, 800: 700, 900: 700}.get(w, 500)
    if w not in _SF:
        _SF[w] = skia.Typeface.MakeFromFile(os.path.join(E.AQUI, "fontes", f"Sans-{w}.ttf"))
    f = skia.Font(_SF[w], size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def uw(s, size, w=500):
    tot = 0
    f = SF(size, w)
    for r, emo in E.runs(s):
        if emo:
            if E.EMOJI_TF:
                tot += skia.Font(E.EMOJI_TF, size).measureText(r)
        else:
            tot += f.measureText(r)
    return tot


def udraw(cv, s, x, y, size, w, rgb, a=1.0):
    f = SF(size, w)
    p = E.P(rgb, a)
    for r, emo in E.runs(s):
        if emo:
            if E.EMOJI_TF:
                fe = skia.Font(E.EMOJI_TF, size * 0.9)
                cv.drawString(r, x, y, fe, skia.Paint(AntiAlias=True, Alphaf=a))
                x += fe.measureText(r)
        else:
            cv.drawString(r, x, y, f, p)
            x += f.measureText(r)
    return x


def ulinhas(s, size, w, maxw):
    out = []
    for par in str(s).split("\n"):
        cur = ""
        for wd in par.split(" "):
            tst = (cur + " " + wd) if cur else wd
            if cur and uw(tst, size, w) > maxw:
                out.append(cur)
                cur = wd
            else:
                cur = tst
        out.append(cur)
    return out


def utexto(cv, s, x, y, size, w=500, rgb=PR, a=1.0, maxw=900, lh=1.3, alinhar="e", cursor=False, t=0):
    """y = topo. Retorna altura. cursor=True desenha o cursor piscando no fim."""
    ls = ulinhas(s, size, w, maxw)
    yy = y
    xe = x
    for i, ln in enumerate(ls):
        lw = uw(ln, size, w)
        xx = x if alinhar == "e" else (x - lw / 2 if alinhar == "c" else x - lw)
        xe = udraw(cv, ln, xx, yy + size * 0.95, size, w, rgb, a)
        if i < len(ls) - 1:
            yy += size * lh
    if cursor and (int(t * 2.2) % 2 == 0):
        cv.drawRect(skia.Rect.MakeXYWH(xe + 3, yy + size * 0.1, 3, size * 1.05), E.P(AZUL, a))
    return (len(ls)) * size * lh


def digitado(valor, t, t0, vel=26):
    """Parte do texto já digitada no tempo t (vel = letras por segundo)."""
    if t0 is None or t >= t0 + len(valor) / vel:
        return valor, False
    n = max(0, int((t - t0) * vel))
    return valor[:n], True


# ---------------------------------------------------------------- personagem
PELE, CABELO, JALECO, BLUSA = (247, 214, 186), (238, 196, 92), (250, 250, 250), (52, 168, 120)


def nutri_rosto(cv, cx, cy, r, piscar=0.0, sorriso=1.0):
    """Busto da nutri (cabelo loiro, jaleco) dentro de um círculo de raio r."""
    s = r / 100
    P = E.P
    # cabelo de trás
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - 62 * s, cy - 60 * s, 124 * s, 150 * s), 55 * s, 55 * s), P(CABELO))
    # corpo / jaleco
    pa = skia.Path()
    pa.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - 78 * s, cy + 52 * s, 156 * s, 120 * s), 50 * s, 50 * s))
    cv.drawPath(pa, P(JALECO))
    tri = skia.Path(); tri.moveTo(cx - 20 * s, cy + 52 * s); tri.lineTo(cx + 20 * s, cy + 52 * s); tri.lineTo(cx, cy + 95 * s); tri.close()
    cv.drawPath(tri, P(BLUSA))
    cv.drawRect(skia.Rect.MakeXYWH(cx - 3 * s, cy + 60 * s, 6 * s, 60 * s), P((200, 200, 200)))
    # pescoço e rosto
    cv.drawRect(skia.Rect.MakeXYWH(cx - 14 * s, cy + 30 * s, 28 * s, 28 * s), P((235, 196, 166)))
    cv.drawOval(skia.Rect.MakeXYWH(cx - 46 * s, cy - 50 * s, 92 * s, 104 * s), P(PELE))
    # franja
    fr = skia.Path()
    fr.moveTo(cx - 50 * s, cy - 8 * s)
    fr.cubicTo(cx - 52 * s, cy - 70 * s, cx + 40 * s, cy - 82 * s, cx + 52 * s, cy - 12 * s)
    fr.cubicTo(cx + 30 * s, cy - 40 * s, cx - 5 * s, cy - 42 * s, cx - 28 * s, cy - 22 * s)
    fr.cubicTo(cx - 36 * s, cy - 16 * s, cx - 44 * s, cy - 10 * s, cx - 50 * s, cy - 8 * s)
    cv.drawPath(fr, P(CABELO))
    # olhos
    oh = max(1.5 * s, 9 * s * (1 - piscar))
    for dx in (-18, 18):
        cv.drawOval(skia.Rect.MakeXYWH(cx + dx * s - 5 * s, cy + 2 * s - oh / 2, 10 * s, oh), P((40, 40, 50)))
    # bochechas
    for dx in (-28, 28):
        cv.drawCircle(cx + dx * s, cy + 20 * s, 7 * s, P((245, 160, 150), 0.6))
    # boca
    b = skia.Path(); b.moveTo(cx - 13 * s, cy + 26 * s); b.quadTo(cx, cy + (26 + 12 * sorriso) * s, cx + 13 * s, cy + 26 * s)
    cv.drawPath(b, P((200, 70, 80), 1, stroke=4 * s))
    # brincos
    for dx in (-46, 46):
        cv.drawCircle(cx + dx * s, cy + 18 * s, 4 * s, P((255, 215, 0)))


def avatar(cv, cx, cy, r, foto=True, anel=False, a=1.0):
    if anel:
        g = skia.GradientShader.MakeSweep(cx, cy, [E.C((254, 218, 117)), E.C((250, 126, 30)), E.C((214, 41, 118)), E.C((150, 47, 191)), E.C((254, 218, 117))])
        p = skia.Paint(AntiAlias=True); p.setShader(g)
        cv.drawCircle(cx, cy, r + 10, p)
        cv.drawCircle(cx, cy, r + 4, E.P(BR))
    cv.save()
    cv.clipRRect(skia.RRect.MakeOval(skia.Rect.MakeXYWH(cx - r, cy - r, 2 * r, 2 * r)))
    if foto:
        cv.drawCircle(cx, cy, r, E.P((255, 236, 214), a))
        nutri_rosto(cv, cx, cy + r * 0.12, r * 0.95)
    else:
        cv.drawCircle(cx, cy, r, E.P((219, 219, 219), a))
        cv.drawCircle(cx, cy - r * 0.18, r * 0.36, E.P(BR, a))
        cv.drawOval(skia.Rect.MakeXYWH(cx - r * 0.65, cy + r * 0.3, r * 1.3, r * 1.0), E.P(BR, a))
    cv.restore()


def barra_status(cv, escuro=False):
    c = BR if escuro else PR
    udraw(cv, "9:41", 70, 92, 38, 600, c)
    E.rrect(cv, 890, 66, 70, 32, 9, c, stroke=3)
    E.rrect(cv, 896, 72, 50, 20, 4, c)
    E.rrect(cv, 963, 76, 6, 12, 2, c)
    for i in range(4):
        E.rrect(cv, 820 + i * 15, 92 - 8 - i * 6, 10, 8 + i * 6, 2, c)


def toque(cv, x, y, t, t0):
    """Círculo de dedo tocando a tela."""
    if t0 is None or not (t0 - 0.25 <= t <= t0 + 0.5):
        return
    k = E.cl((t - t0 + 0.25) / 0.75)
    r = 40 + 40 * k
    cv.drawCircle(x, y, r, E.P((120, 120, 120), 0.35 * (1 - k)))
    cv.drawCircle(x, y, 34, E.P((255, 255, 255), 0.55 * (1 - k) + 0.2, stroke=5))


def pilula(cv, s, x, y, k, rgb=PR, fundo=BR, borda=None, size=30, alinhar="c"):
    """Etiqueta curta (ex.: • QUEM VOCÊ AJUDA)."""
    if k <= 0:
        return
    s = "• " + s.upper()
    w = uw(s, size, 700) + 44
    xx = x - w / 2 if alinhar == "c" else (x if alinhar == "e" else x - w)
    sc = E.lerp(0.6, 1, E.e_back(k))
    cv.save(); cv.translate(xx + w / 2, y); cv.scale(sc, sc); cv.translate(-(xx + w / 2), -y)
    E.rrect(cv, xx, y - 30, w, 60, 30, fundo, E.e_out(k), sombra=True)
    E.rrect(cv, xx, y - 30, w, 60, 30, borda or PR, E.e_out(k), stroke=3)
    udraw(cv, s, xx + 22, y + 11, size, 700, rgb, E.e_out(k))
    cv.restore()


def confete(cv, t, t0, n=90):
    if t0 is None or t < t0 or t > t0 + 2.6:
        return
    dt = t - t0
    rng = random.Random(11)
    cores = [VERM, AMAR, AZUL, VERDE, (160, 110, 255), (255, 150, 60)]
    for i in range(n):
        x0 = rng.random() * 1080
        vx = (rng.random() - 0.5) * 300
        vy = -900 - rng.random() * 700
        x = x0 + vx * dt
        y = 1100 + vy * dt + 1400 * dt * dt
        rot = (rng.random() * 360 + dt * 400) % 360
        cv.save(); cv.translate(x, y); cv.rotate(rot)
        cv.drawRect(skia.Rect.MakeXYWH(-9, -5, 18, 10), E.P(cores[i % 6], 1 - E.cl((dt - 2) / 0.6)))
        cv.restore()


def titulo_grande(cv, s, t, t0, y=700, rgb=AMAR):
    """Título amarelo com contorno escuro (PERFIL COMPLETO!)."""
    if t0 is None or t < t0:
        return
    k = E.prog(t, t0, 0.45)
    a = 1 - E.cl((t - t0 - 2.6) / 0.4)
    if a <= 0:
        return
    sc = E.lerp(2.2, 1, E.e_back(k))
    cv.save(); cv.translate(540, y); cv.rotate(-4); cv.scale(sc, sc)
    f = E.F(96, 900)
    lw = f.measureText(s.upper())
    if lw > 980:
        cv.scale(980 / lw, 980 / lw)
    p = E.P((40, 30, 10), a, stroke=22)
    cv.drawString(s.upper(), -lw / 2, 34, f, p)
    cv.drawString(s.upper(), -lw / 2, 34, f, E.P(rgb, a))
    cv.restore()


def banner_problema(cv, s, t, t0, y=210, cor=VERM, icone="alerta"):
    """Notificação vermelha que cai do topo com o problema."""
    if t0 is None or t < t0:
        return
    k = E.e_back(E.prog(t, t0, 0.4))
    yy = y - 140 * (1 - k)
    hh = max(110, E.altura_texto(s, 40, 800, 760) + 50)
    E.rrect(cv, 60, yy, 960, hh, 30, cor, E.e_out(E.prog(t, t0, 0.2)), sombra=True)
    E.icone(cv, icone, 125, yy + hh / 2, 50, BR)
    E.texto(cv, s, 175, yy + hh / 2, 40, 800, BR, alinhar="e", maxw=780)


def notif_ios(cv, n, t, t0, y):
    if t0 is None or t < t0:
        return 0
    k = E.e_back(E.prog(t, t0, 0.4))
    yy = y - 160 * (1 - k)
    E.rrect(cv, 50, yy, 980, 150, 36, (245, 245, 245), 0.97, sombra=True)
    app = n.get("app", "WhatsApp")
    ac = {"WhatsApp": VERDE, "Instagram": (225, 48, 108), "Agenda": VERM, "Banco": (130, 80, 220)}.get(app, AZUL)
    E.rrect(cv, 85, yy + 35, 80, 80, 20, ac)
    E.icone(cv, {"WhatsApp": "celular", "Instagram": "coracao", "Agenda": "calendario"}.get(app, "pessoa"), 125, yy + 75, 46, BR)
    udraw(cv, n.get("titulo", ""), 190, yy + 65, 34, 700, PR)
    udraw(cv, n.get("texto", ""), 190, yy + 112, 32, 400, (60, 60, 60))
    udraw(cv, "agora", 900, yy + 65, 26, 400, CINZA)
    return 170


# ---------------------------------------------------------------- base das cenas de tela
def registrar(Emod):
    global E
    E = Emod

    class Tela(E.Cena):
        """Base: fundo branco de app, barra de status e as camadas por cima (problema, etiqueta, toque, confete)."""
        tipo = "tela_base"
        escuro = False
        alvos = {}

        def ultimo(self, t, chave):
            v = None
            for tp, p in self.passos:
                if tp <= t and chave in p:
                    v = (tp, p)
            return v

        def desenhar(self, cv, t):
            cv.drawColor(E.C(BR))
            self.app(cv, t)
            barra_status(cv, self.escuro)
            self.camadas(cv, t)

        def app(self, cv, t):
            pass

        def ponto(self, alvo):
            if isinstance(alvo, (list, tuple)):
                return alvo
            return self.alvos.get(alvo, (540, 900))

        def camadas(self, cv, t):
            # etiquetas (ficam enquanto a cena dura; no máximo 3 visíveis)
            rots = [(tp, p) for tp, p in self.passos if tp <= t and p.get("rotulo")]
            for j, (tp, p) in enumerate(rots[-1:]):
                pt = self.ponto(p.get("alvo", "centro"))
                x, y = pt[0], pt[1]
                yb = pt[2] if len(pt) > 2 else y + 40
                k = E.prog(t, tp, 0.35)
                ult = True
                if ult and len(pt) > 2 and p.get("caixa", True):
                    hh = (yb - y) * 2 + 16
                    E.rrect(cv, 40, y - hh / 2, 1000, hh, 18, AMAR, E.e_out(k) * (0.9 if ult else 0.4), stroke=7)
                lado = p.get("lado", "d")
                pilula(cv, p["rotulo"], 1030 if lado == "d" else (50 if lado == "e" else x), yb + 34, k,
                       alinhar={"d": "d", "e": "e", "c": "c"}[lado])
            for tp, p in self.passos:
                if p.get("tap"):
                    x, y = self.ponto(p["tap"])[:2]
                    toque(cv, x, y, t, tp)
            pr = self.ultimo(t, "problema")
            if pr and pr[1]["problema"] and t < pr[0] + pr[1].get("dur", 3.2):
                banner_problema(cv, pr[1]["problema"], t, pr[0])
            ok = self.ultimo(t, "resolvido")
            if ok and ok[1]["resolvido"] and t < ok[0] + ok[1].get("dur", 2.6):
                banner_problema(cv, ok[1]["resolvido"], t, ok[0], cor=(34, 170, 90), icone="check")
            y = 200
            for tp, p in [(tp, p) for tp, p in self.passos if tp <= t < tp + p.get("dur", 3.0) and p.get("notif")][-3:]:
                y += notif_ios(cv, p["notif"], t, tp, y)
            cm = self.ultimo(t, "comemora")
            if cm:
                confete(cv, t, cm[0])
                titulo_grande(cv, cm[1]["comemora"], t, cm[0], y=cm[1].get("y", 760))
            gl = self.ultimo(t, "glitch")
            if gl and gl[0] <= t < gl[0] + 0.45:
                k = (t - gl[0]) / 0.45
                for i in range(6):
                    yy = random.Random(int(t * 30) + i).random() * 1920
                    cv.drawRect(skia.Rect.MakeXYWH(0, yy, 1080, 30 + 40 * random.Random(i).random()), E.P((255, 0, 80) if i % 2 else (0, 200, 255), 0.35 * (1 - k)))

    # ------------------------------------------------ perfil do Instagram
    class Perfil(Tela):
        """Perfil do Instagram sendo montado. Campos: usuario, nome, bio, crn, foto, verificado,
        posts, seguidores, seguindo, link, botao, destaques[], fixados[]."""
        tipo = "perfil"

        def estado(self, t):
            st = dict(usuario="ana8392017", nome="", bio="", cta="", crn="", foto=False, verificado=False, posts=0,
                      seguidores=0, seguindo=12, link="", botao="", destaques=[], fixados=[], grade=0)
            st.update({k: v for k, v in self.d.items() if k in st})
            quando = {}
            for tp, p in self.passos:
                if tp > t:
                    break
                for k, v in (p.get("set") or {}).items():
                    antigo = st.get(k)
                    st[k] = v
                    quando[k] = (tp, antigo)
            return st, quando

        def app(self, cv, t):
            st, q = self.estado(t)
            al = {}
            # cabeçalho
            us, dig = digitado(st["usuario"], t, q.get("usuario", (None,))[0])
            udraw(cv, us or " ", 60, 210, 50, 700, PR)
            if st["verificado"] and not dig:
                kx = 60 + uw(us, 50, 700) + 32
                kk = E.e_back(E.prog(t, q.get("verificado", (-9,))[0], 0.4))
                E.circulo(cv, kx, 190, 17 * kk, AZUL)
                E.icone(cv, "check", kx, 191, 20 * kk, BR)
            al["usuario"] = (60 + uw(us, 50, 700) / 2, 192, 225)
            E.rrect(cv, 930, 168, 46, 46, 10, PR, stroke=4)
            cv.drawRect(skia.Rect.MakeXYWH(951, 178, 4, 26), E.P(PR)); cv.drawRect(skia.Rect.MakeXYWH(940, 189, 26, 4), E.P(PR))
            for i in range(3):
                cv.drawRect(skia.Rect.MakeXYWH(995, 175 + i * 14, 36, 4), E.P(PR))
            # foto
            kf = E.prog(t, q.get("foto", (-9,))[0], 0.5)
            avatar(cv, 170, 355, 112, foto=st["foto"] and kf > 0.5, anel=st["foto"])
            if st["foto"] and kf < 1:
                cv.drawCircle(170, 355, 112 + 30 * kf, E.P(AZUL, 0.5 * (1 - kf), stroke=8))
            al["foto"] = (170, 355, 475)
            # números
            nm, _ = digitado(st["nome"], t, q.get("nome", (None,))[0])
            udraw(cv, nm, 330, 300, 40, 600, PR)
            al["nome"] = (330 + uw(nm, 40, 600) / 2, 286, 315)
            for i, (k, lab) in enumerate((("posts", "posts"), ("seguidores", "seguidores"), ("seguindo", "seguindo"))):
                v = st[k]
                if k in q and isinstance(v, (int, float)):
                    v0 = q[k][1] if isinstance(q[k][1], (int, float)) else 0
                    v = int(E.lerp(v0, v, E.e_out(E.prog(t, q[k][0], 1.0))))
                x = 330 + i * 235
                udraw(cv, E.num_br(v) if isinstance(v, (int, float)) else str(v), x, 380, 46, 700, PR)
                udraw(cv, lab, x, 425, 32, 400, PR)
            al["seguidores"] = (565, 390, 440)
            # bio
            y = 500
            linhas = []
            if st["crn"]:
                linhas.append(("crn", st["crn"]))
            if st["bio"]:
                linhas.append(("bio", st["bio"]))
            if st["cta"]:
                linhas.append(("cta", st["cta"]))
            if st["link"]:
                linhas.append(("link", st["link"]))
            al["bio"] = (540, 520, 560)
            for k, v in linhas:
                tp = q.get(k, (None, None))[0]
                antigo = q.get(k, (None, None))[1]
                txt, dig = digitado(v, t, tp)
                if dig and antigo and k == "bio":
                    # apaga o antigo rápido antes de digitar o novo
                    pass
                rgb = (0, 55, 107) if k == "link" else PR
                hh = utexto(cv, txt, 60, y, 40, 600 if k == "crn" else 400, rgb, maxw=960, lh=1.28, cursor=dig, t=t)
                if tp is not None and t - tp < 1.2:
                    E.rrect(cv, 45, y - 6, 990, max(hh, 46) + 10, 12, AZUL, 0.18 * (1 - E.cl((t - tp - 0.6) / 0.6)))
                al[k] = (540, y + max(hh, 50) / 2, y + max(hh, 50))
                y += max(hh, 50) + 6
            y += 20
            # botões
            bot = st["botao"]
            bw = 300 if bot else 455
            E.rrect(cv, 60, y, bw, 76, 16, (239, 239, 239))
            udraw(cv, "Editar perfil", 60 + bw / 2 - uw("Editar perfil", 30, 600) / 2, y + 49, 30, 600, PR)
            E.rrect(cv, 75 + bw, y, bw, 76, 16, (239, 239, 239))
            s2 = "Compartilhar perfil"
            udraw(cv, s2 if not bot else "Mensagem", 75 + bw + bw / 2 - uw(s2 if not bot else "Mensagem", 30, 600) / 2, y + 49, 30, 600, PR)
            al["editar"] = (60 + bw / 2, y + 38)
            if bot:
                kb = E.e_back(E.prog(t, q.get("botao", (-9,))[0], 0.4))
                x3 = 90 + 2 * bw
                cv.save(); cv.translate(x3 + 150, y + 38); cv.scale(kb, kb); cv.translate(-(x3 + 150), -(y + 38))
                E.rrect(cv, x3, y, 1020 - x3, 76, 16, AZUL)
                udraw(cv, bot, x3 + (1020 - x3) / 2 - uw(bot, 30, 700) / 2, y + 49, 30, 700, BR)
                cv.restore()
                al["botao"] = (x3 + (1020 - x3) / 2, y + 38)
            y += 110
            # destaques
            ds = st["destaques"]
            x = 70
            for i in range(len(ds) + 1):
                cx = x + 75 + i * 190
                if cx > 1100:
                    break
                if i < len(ds):
                    kd = E.e_back(E.prog(t, q.get("destaques", (-9,))[0] + i * 0.25, 0.4))
                    cv.save(); cv.translate(cx, y + 75); cv.scale(kd, kd); cv.translate(-cx, -(y + 75))
                    cv.drawCircle(cx, y + 75, 75, E.P(LINHA, 1, stroke=4))
                    cv.drawCircle(cx, y + 75, 64, E.P((240, 246, 255)))
                    E.icone(cv, ["calendario", "alerta", "coracao", "pessoa", "celular", "check"][i % 6], cx, y + 75, 56, AZUL)
                    nm_ = ds[i]
                    udraw(cv, nm_, cx - uw(nm_, 26, 500) / 2, y + 190, 26, 500, PR)
                    cv.restore()
                else:
                    cv.drawCircle(cx, y + 75, 75, E.P(LINHA, 1, stroke=4))
                    cv.drawRect(skia.Rect.MakeXYWH(cx - 3, y + 50, 6, 50), E.P(PR)); cv.drawRect(skia.Rect.MakeXYWH(cx - 25, y + 72, 50, 6), E.P(PR))
                    udraw(cv, "Novo", cx - uw("Novo", 26, 500) / 2, y + 190, 26, 500, PR)
            al["destaques"] = (540, y + 75)
            y += 230
            # abas
            for i in range(3):
                cx = 180 + i * 360
                if i == 0:
                    for a_ in range(3):
                        for b_ in range(3):
                            cv.drawRect(skia.Rect.MakeXYWH(cx - 22 + a_ * 16, y + 18 + b_ * 16, 12, 12), E.P(PR))
                    cv.drawRect(skia.Rect.MakeXYWH(cx - 180, y + 78, 360, 4), E.P(PR))
                else:
                    E.rrect(cv, cx - 22, y + 18, 44, 44, 8, CINZA, stroke=4)
            y += 86
            # grade
            fx = st["fixados"]
            tile = 358
            cores = [(255, 236, 214), (52, 168, 120), (252, 246, 220), (220, 240, 228), (255, 220, 205), (214, 232, 250)]
            al["grade"] = (540, y + tile / 2)
            total = max(st["grade"], len(fx))
            for i in range(max(6, total)):
                r_, c_ = divmod(i, 3)
                xx, yy = c_ * (tile + 3), y + r_ * (tile + 3)
                if yy > 1920:
                    break
                if i < len(fx):
                    kk = E.e_back(E.prog(t, q.get("fixados", (-9,))[0] + i * 0.35, 0.45))
                    cv.save(); cv.translate(xx + tile / 2, yy + tile / 2); cv.scale(kk, kk); cv.translate(-(xx + tile / 2), -(yy + tile / 2))
                    rgb = cores[i % 3]
                    cv.drawRect(skia.Rect.MakeXYWH(xx, yy, tile, tile), E.P(rgb))
                    dark = rgb == (52, 168, 120)
                    utexto(cv, fx[i], xx + 26, yy + 36, 40, 700, BR if dark else PR, maxw=tile - 52, lh=1.12)
                    if i == 0:
                        avatar(cv, xx + tile / 2, yy + tile - 90, 70, foto=True)
                    # alfinete
                    E.icone(cv, "seta", xx + tile - 40, yy + 38, 26, BR if dark else PR)
                    cv.restore()
                    al["fixado%d" % i] = (xx + tile / 2, yy + tile / 2)
                elif i < total:
                    cv.drawRect(skia.Rect.MakeXYWH(xx, yy, tile, tile), E.P(cores[3 + i % 3]))
                else:
                    cv.drawRect(skia.Rect.MakeXYWH(xx, yy, tile, tile), E.P((250, 250, 250)))
            al["centro"] = (540, 900)
            self.alvos = al

    # ------------------------------------------------ editar perfil
    class Editar(Tela):
        """Tela 'Editar perfil' com os campos sendo digitados."""
        tipo = "editar"

        def app(self, cv, t):
            st = dict(nome="", usuario="", bio="", links="", foto=False)
            st.update({k: v for k, v in self.d.items() if k in st})
            q = {}
            foco = None
            for tp, p in self.passos:
                if tp > t:
                    break
                for k, v in (p.get("set") or {}).items():
                    st[k] = v
                    q[k] = tp
                    foco = k
            udraw(cv, "Cancelar", 60, 210, 34, 400, PR)
            udraw(cv, "Editar perfil", 540 - uw("Editar perfil", 38, 700) / 2, 210, 38, 700, PR)
            udraw(cv, "Concluir", 1020 - uw("Concluir", 34, 700), 210, 34, 700, AZUL)
            kf = E.prog(t, q.get("foto", -9), 0.5)
            avatar(cv, 540, 400, 120, foto=st["foto"] and kf > 0.5, anel=True)
            udraw(cv, "Editar foto", 540 - uw("Editar foto", 32, 600) / 2, 590, 32, 600, AZUL)
            al = {"foto": (540, 400)}
            y = 670
            for k, lab in (("nome", "Nome"), ("usuario", "Nome de usuário"), ("bio", "Bio"), ("links", "Links")):
                udraw(cv, lab, 60, y + 30, 32, 400, CINZA)
                v, dig = digitado(st[k], t, q.get(k))
                if not v and not dig:
                    udraw(cv, "Adicionar " + lab.lower(), 60, y + 88, 42, 400, (190, 190, 190))
                    hh = 56
                else:
                    hh = utexto(cv, v, 60, y + 46, 42, 400, PR, maxw=950, cursor=dig or foco == k, t=t)
                cv.drawRect(skia.Rect.MakeXYWH(60, y + 60 + max(hh, 50), 960, 3 if foco == k else 2), E.P(PR if foco == k else LINHA))
                al[k] = (540, y + 40 + max(hh, 50) / 2, y + 66 + max(hh, 50))
                y += 120 + max(hh, 50)
            al["centro"] = (540, 900)
            self.alvos = al

    # ------------------------------------------------ WhatsApp claro
    class Whats(Tela):
        """WhatsApp (tema claro), com a mensagem sendo digitada na caixa antes de enviar."""
        tipo = "whats"
        escuro = True

        def app(self, cv, t):
            cv.drawColor(E.C((239, 234, 226)))
            rng = random.Random(5)
            for i in range(60):
                cv.drawCircle(rng.random() * 1080, rng.random() * 1920, 6 + rng.random() * 10, E.P((225, 218, 206), 0.7, stroke=3))
            E.rrect(cv, 0, 0, 1080, 300, 0, (0, 128, 105))
            E.icone(cv, "seta", 60, 225, 40, BR)  # (seta de voltar estilizada)
            cv.drawCircle(150, 225, 50, E.P((200, 214, 220)))
            E.icone(cv, "pessoa", 150, 232, 60, BR)
            udraw(cv, self.d.get("contato", "Paciente"), 225, 215, 40, 600, BR)
            # mensagens
            msgs = []
            digit_ele = None
            entrada = None
            for tp, p in self.passos:
                if not p.get("msg") and not p.get("aviso"):
                    continue
                if p.get("aviso"):
                    if tp <= t:
                        msgs.append((tp, p))
                    continue
                eu = p.get("de", "ele") == "eu"
                if eu:
                    dt = min(1.4, len(p["msg"]) / 40) if p.get("digitar", True) else 0
                    if tp <= t < tp + dt:
                        entrada = (p["msg"], tp, dt)
                    if t >= tp + dt:
                        msgs.append((tp + dt, p))
                else:
                    dt = 0.6 if p.get("digitando", True) else 0
                    if tp <= t < tp + dt:
                        digit_ele = True
                    if t >= tp + dt:
                        msgs.append((tp + dt, p))
            udraw(cv, "digitando..." if digit_ele else self.d.get("status", "online"), 225, 262, 28, 400, (220, 248, 240))
            topo, fundo = 330, 1700
            blocos = []
            for apar, p in msgs:
                if p.get("aviso"):
                    blocos.append((apar, p, 80))
                else:
                    blocos.append((apar, p, len(ulinhas(p["msg"], 46, 400, 700)) * 46 * 1.3 + 80))
            total = sum(b[2] + 20 for b in blocos)
            y = topo - max(0, total - (fundo - topo - 60))
            cv.save(); cv.clipRect(skia.Rect.MakeXYWH(0, 300, 1080, fundo - 300))
            for apar, p, hh in blocos:
                k = E.e_back(E.prog(t, apar, 0.3))
                if p.get("aviso"):
                    s = p["aviso"]
                    w = uw(s, 34, 600) + 56
                    E.rrect(cv, 540 - w / 2, y + 6, w, 66, 18, (255, 244, 200))
                    udraw(cv, s, 540 - w / 2 + 28, y + 51, 34, 600, (90, 80, 40))
                else:
                    eu = p.get("de", "ele") == "eu"
                    ls = ulinhas(p["msg"], 46, 400, 700)
                    lw = max(uw(l, 46, 400) for l in ls)
                    bw = max(lw + 60, 220)
                    bx = 1040 - bw if eu else 40
                    cx = bx + (bw if eu else 0)
                    cv.save(); cv.translate(cx, y + hh); cv.scale(k, k); cv.translate(-cx, -(y + hh))
                    E.rrect(cv, bx, y, bw, hh, 22, (217, 253, 211) if eu else BR, sombra=True)
                    utexto(cv, p["msg"], bx + 28, y + 16, 46, 400, PR, maxw=700, lh=1.3)
                    hora = p.get("hora", "")
                    udraw(cv, hora, bx + bw - 30 - uw(hora, 26, 400) - (46 if eu else 0), y + hh - 16, 26, 400, CINZA)
                    if eu:
                        azul = p.get("lido", False) and t > apar + 0.8
                        ck = (83, 189, 235) if azul else CINZA
                        E.icone(cv, "check", bx + bw - 58, y + hh - 26, 22, ck)
                        E.icone(cv, "check", bx + bw - 46, y + hh - 26, 22, ck)
                    m = p.get("marca")
                    if m:
                        km = E.e_back(E.prog(t, apar + 0.4, 0.35))
                        mc = VERM if m == "erro" else (34, 170, 90)
                        mx = bx - 55 if eu else bx + bw + 55
                        E.circulo(cv, mx, y + hh / 2, 36 * km, mc)
                        E.icone(cv, "x" if m == "erro" else "check", mx, y + hh / 2, 38 * km, BR)
                    cv.restore()
                y += hh + 20
            if digit_ele:
                E.rrect(cv, 40, y, 160, 74, 22, BR)
                for i in range(3):
                    ph = (t * 6 + i * 1.2) % (2 * math.pi)
                    E.circulo(cv, 85 + i * 35, y + 37 - 6 * max(0, math.sin(ph)), 9, CINZA)
            cv.restore()
            # caixa de digitar
            E.rrect(cv, 30, 1730, 870, 100, 50, BR)
            if entrada:
                txt, tp, dt = entrada
                n = int(len(txt) * E.cl((t - tp) / dt))
                ls = ulinhas(txt[:n], 34, 400, 760)
                udraw(cv, ls[-1] if ls else "", 80, 1792, 34, 400, PR)
                if int(t * 2.2) % 2 == 0:
                    cv.drawRect(skia.Rect.MakeXYWH(84 + uw(ls[-1] if ls else "", 34, 400), 1762, 3, 40), E.P((0, 128, 105)))
            else:
                udraw(cv, "Mensagem", 80, 1792, 34, 400, CINZA)
            E.circulo(cv, 980, 1780, 50, (0, 168, 132))
            E.icone(cv, "seta" if entrada else "celular", 980, 1780, 44, BR)
            self.alvos = {"centro": (540, 900), "enviar": (980, 1780), "caixa": (450, 1780)}

    # ------------------------------------------------ Stories
    class Stories(Tela):
        """Stories: cada passo {"story": {...}} abre um story novo. {"grade": true} mostra os 3 lado a lado."""
        tipo = "stories"
        escuro = True

        def _story(self, cv, s, x, y, w, h, t, tp):
            g = skia.GradientShader.MakeLinear([skia.Point(x, y), skia.Point(x + w, y + h)], [E.C(E.cor(s.get("cor1", "#F58529"))), E.C(E.cor(s.get("cor2", "#DD2A7B")))])
            p = skia.Paint(AntiAlias=True); p.setShader(g)
            cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 30 * w / 1080, 30 * w / 1080), p)
            sc = w / 1080
            cv.save(); cv.translate(x, y); cv.scale(sc, sc)
            tipo = s.get("tipo", "texto")
            if tipo == "foto":
                # foto ilustrada (café, mesa)
                rr = s.get("objeto", "cafe")
                if rr == "cafe":
                    E.rrect(cv, 380, 700, 320, 300, 40, BR)
                    E.rrect(cv, 400, 720, 280, 90, 30, (120, 70, 40))
                    cv.drawCircle(720, 850, 70, E.P(BR, 1, stroke=24))
                    E.rrect(cv, 300, 1000, 480, 30, 15, (240, 240, 240))
                else:
                    E.rrect(cv, 140, 900, 800, 60, 20, (170, 120, 80))
                    E.rrect(cv, 300, 640, 480, 280, 20, (40, 40, 50))
                    E.rrect(cv, 320, 660, 440, 220, 10, (110, 190, 255))
                    cv.drawCircle(850, 860, 50, E.P((52, 168, 120)))
            elif tipo == "bastidor":
                E.rrect(cv, 140, 960, 800, 50, 20, (170, 120, 80))
                E.rrect(cv, 220, 760, 300, 200, 14, BR)
                for i in range(5):
                    E.rrect(cv, 250, 790 + i * 32, 240, 12, 6, (200, 210, 220))
                E.rrect(cv, 600, 820, 200, 140, 14, (52, 168, 120))
                E.texto(cv, "PLANO", 700, 890, 36, 900, BR)
                nutri_rosto(cv, 540, 560, 150)
            elif tipo == "caixinha":
                E.rrect(cv, 140, 700, 800, 420, 40, BR, sombra=True)
                E.rrect(cv, 140, 700, 800, 170, 40, (40, 40, 40))
                E.rrect(cv, 140, 800, 800, 70, 0, (40, 40, 40))
                E.texto(cv, s.get("titulo", "Me pergunte"), 540, 790, 46, 800, BR, maxw=720)
                E.rrect(cv, 200, 930, 680, 120, 24, (240, 240, 240))
                udraw(cv, "Escreva algo...", 240, 1005, 36, 400, CINZA)
            elif tipo == "link":
                E.rrect(cv, 240, 900, 600, 120, 30, BR, sombra=True)
                E.icone(cv, "seta", 320, 960, 50, AZUL)
                udraw(cv, s.get("titulo", "Agendar consulta"), 370, 975, 44, 700, AZUL)
            frase = s.get("texto")
            if frase:
                yy = 380 if tipo != "texto" else 900
                E.rrect(cv, 90, yy - 110, 900, E.altura_texto(frase, 64, 900, 800) + 100, 30, (0, 0, 0), 0.35)
                E.texto(cv, frase, 540, yy - 60, 64, 900, BR, maxw=800, v="t")
            cv.restore()

        def app(self, cv, t):
            sts = [(tp, p["story"]) for tp, p in self.passos if tp <= t and p.get("story")]
            gr = self.ultimo(t, "grade")
            cv.drawColor(E.C((20, 20, 20)))
            if gr and gr[1]["grade"]:
                k = E.e_out(E.prog(t, gr[0], 0.6))
                todas = [s for tp, p in self.passos if p.get("story") for s in [p["story"]]]
                n = len(todas)
                w = 320; h = w * 16 / 9; gap = 30
                x0 = 540 - (n * w + (n - 1) * gap) / 2
                for i, s in enumerate(todas):
                    kk = E.e_back(E.prog(t, gr[0] + i * 0.2, 0.45))
                    x = x0 + i * (w + gap)
                    cv.save(); cv.translate(x + w / 2, 900); cv.scale(kk, kk); cv.translate(-(x + w / 2), -900)
                    self._story(cv, s, x, 900 - h / 2, w, h, t, gr[0])
                    E.texto(cv, ["COMEÇO", "MEIO", "FIM", "4", "5"][i], x + w / 2, 900 + h / 2 + 60, 40, 900, AMAR)
                    cv.restore()
                self.alvos = {"centro": (540, 900)}
                return
            if not sts:
                # tela da câmera vazia
                E.texto(cv, self.d.get("vazio", "O que eu vou postar hoje?"), 540, 900, 64, 900, BR, maxw=860)
                cv.drawCircle(540, 1650, 90, E.P(BR, 1, stroke=12))
                self.alvos = {"centro": (540, 900)}
                return
            tp, s = sts[-1]
            k = E.e_out(E.prog(t, tp, 0.3))
            cv.save(); cv.translate((1 - k) * 300, 0)
            self._story(cv, s, 0, 140, 1080, 1780, t, tp)
            cv.restore()
            n = max(len([1 for _, p in self.passos if p.get("story")]), 1)
            w = (1000 - (n - 1) * 10) / n
            for i in range(n):
                x = 40 + i * (w + 10)
                E.rrect(cv, x, 160, w, 8, 4, BR, 0.4)
                if i < len(sts) - 1:
                    E.rrect(cv, x, 160, w, 8, 4, BR)
                elif i == len(sts) - 1:
                    E.rrect(cv, x, 160, w * E.cl((t - tp) / 3), 8, 4, BR)
            avatar(cv, 90, 230, 36, foto=True)
            udraw(cv, "anasouzanutri", 145, 242, 30, 700, BR)
            self.alvos = {"centro": (540, 900)}

    # ------------------------------------------------ página de links
    class Links(Tela):
        tipo = "links"

        def app(self, cv, t):
            cv.drawColor(E.C((246, 241, 233)))
            bots = list(self.d.get("botoes", []))
            q = None
            dest = None
            for tp, p in self.passos:
                if tp > t:
                    break
                if "botoes" in p:
                    bots = p["botoes"]; q = tp
                if "destaque" in p:
                    dest = (tp, p["destaque"])
            avatar(cv, 540, 330, 110, foto=True)
            udraw(cv, self.d.get("nome", "Ana Souza | Nutricionista"), 540 - uw(self.d.get("nome", "Ana Souza | Nutricionista"), 36, 700) / 2, 510, 36, 700, PR)
            n = len(bots)
            alt = min(120, (1750 - 600) / max(1, n) - 18)
            size = 34 if alt > 90 else 28
            y = 590
            al = {"centro": (540, 900)}
            for i, b in enumerate(bots):
                kk = E.e_back(E.prog(t, (q or self.t0) + i * 0.06, 0.35))
                big = dest is not None and dest[1] == i
                h = alt * (1.5 if big else 1)
                cv.save(); cv.translate(540, y + h / 2); cv.scale(kk, kk); cv.translate(-540, -(y + h / 2))
                if big:
                    pul = 1 + 0.03 * math.sin(t * 6)
                    cv.translate(540, y + h / 2); cv.scale(pul, pul); cv.translate(-540, -(y + h / 2))
                    E.rrect(cv, 90, y, 900, h, h / 2, (34, 170, 90), sombra=True)
                    udraw(cv, b, 540 - uw(b, 46, 700) / 2, y + h / 2 + 16, 46, 700, BR)
                else:
                    E.rrect(cv, 90, y, 900, h, h / 2, BR, sombra=True)
                    udraw(cv, b, 540 - uw(b, size, 600) / 2, y + h / 2 + size * 0.35, size, 600, PR)
                cv.restore()
                al["botao%d" % i] = (540, y + h / 2)
                y += h + 18
            self.alvos = al

    # ------------------------------------------------ consultório ilustrado
    class Consultorio(Tela):
        """Consultório: a nutri na mesa, balão de pensamento, paciente entrando/saindo, agenda na parede."""
        tipo = "consultorio"

        def app(self, cv, t):
            cv.drawColor(E.C((232, 222, 200)))
            cv.drawRect(skia.Rect.MakeXYWH(0, 1250, 1080, 670), E.P((205, 180, 140)))
            for i in range(2):
                E.rrect(cv, 160 + i * 300, 330, 220, 160, 8, (90, 70, 50), stroke=14)
                cv.drawRect(skia.Rect.MakeXYWH(205 + i * 300, 400, 130, 10), E.P((52, 168, 120)))
            # estante
            E.rrect(cv, 820, 500, 200, 650, 10, (150, 110, 75))
            for j in range(4):
                for i in range(5):
                    cores = [(52, 120, 200), (220, 80, 70), (240, 190, 60), (60, 160, 100), (140, 90, 180)]
                    E.rrect(cv, 835 + i * 36, 520 + j * 150, 28, 120, 4, cores[(i + j) % 5])
            # porta
            E.rrect(cv, 40, 650, 220, 600, 10, (160, 120, 80))
            cv.drawCircle(230, 960, 12, E.P((240, 200, 80)))
            # agenda na parede
            ag = None
            for tp, p in self.passos:
                if tp <= t and "agenda" in p:
                    ag = (tp, p["agenda"])
            if ag:
                k = E.e_back(E.prog(t, ag[0], 0.4))
                cv.save(); cv.translate(560, 300); cv.scale(k, k); cv.translate(-560, -300)
                E.rrect(cv, 420, 160, 280, 300, 16, BR, sombra=True)
                E.rrect(cv, 420, 160, 280, 60, 16, VERM)
                E.texto(cv, "AGENDA", 560, 190, 30, 900, BR)
                cheia = ag[1] if isinstance(ag[1], int) else (8 if ag[1] == "cheia" else 0)
                for i in range(8):
                    E.rrect(cv, 440 + (i % 2) * 125, 235 + (i // 2) * 55, 115, 42, 8, (52, 168, 120) if i < cheia else (236, 236, 236))
                cv.restore()
            # mesa + computador + nutri
            nutri_rosto(cv, 640, 860, 170, piscar=1.0 if (t % 3.2) < 0.12 else 0)
            E.rrect(cv, 300, 1080, 760, 60, 10, BR)
            E.rrect(cv, 330, 1140, 40, 280, 6, (220, 220, 220)); E.rrect(cv, 990, 1140, 40, 280, 6, (220, 220, 220))
            E.rrect(cv, 760, 880, 260, 180, 10, (30, 30, 40)); E.rrect(cv, 870, 1060, 40, 30, 4, (30, 30, 40))
            cv.drawCircle(420, 1060, 24, E.P(VERM)); cv.drawCircle(465, 1062, 20, E.P((120, 200, 80)))
            # paciente
            pac = None
            for tp, p in self.passos:
                if tp <= t and "paciente" in p:
                    pac = (tp, p["paciente"])
            if pac:
                tp, acao = pac
                k = E.e_inout(E.prog(t, tp, 1.0))
                if acao == "entra":
                    x = E.lerp(-150, 190, k)
                elif acao == "senta":
                    x = 190
                else:
                    x = E.lerp(190, -200, k)
                y = 900
                E.rrect(cv, x - 85, y, 170, 380, 60, (230, 110, 120))
                E.rrect(cv, x - 70, y + 360, 55, 200, 20, (60, 70, 110)); E.rrect(cv, x + 15, y + 360, 55, 200, 20, (60, 70, 110))
                cv.drawCircle(x, y - 60, 75, E.P((210, 160, 120)))
                cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - 80, y - 150, 160, 85), 40, 40), E.P((70, 45, 30)))
                for dx in (-25, 25):
                    cv.drawCircle(x + dx, y - 55, 7, E.P((40, 40, 50)))
            # balão
            bal = None
            for tp, p in self.passos:
                if tp <= t and ("pensa" in p or "fala" in p):
                    bal = (tp, p)
            if bal:
                tp, p = bal
                k = E.e_back(E.prog(t, tp, 0.4))
                s = p.get("pensa") or p.get("fala")
                quem_pac = p.get("quem") == "paciente"
                bx = 360 if quem_pac else 560
                hh = E.altura_texto(s, 44, 700, 560) + 70
                cv.save(); cv.translate(bx, 620); cv.scale(k, k); cv.translate(-bx, -620)
                E.rrect(cv, bx - 320, 620 - hh, 640, hh, 50, BR, sombra=True)
                E.texto(cv, s, bx, 620 - hh / 2, 44, 700, PR, maxw=560)
                if "pensa" in p:
                    cv.drawCircle(bx + 60, 650, 22, E.P(BR)); cv.drawCircle(bx + 80, 695, 12, E.P(BR))
                cv.restore()
            pop = self.ultimo(t, "popup")
            if pop:
                tp, p = pop
                k = E.e_back(E.prog(t, tp, 0.4))
                info = p["popup"]
                ls = info.get("linhas", [])
                hh = 140 + 90 * len(ls)
                cv.save(); cv.translate(540, 1560); cv.scale(k, k); cv.translate(-540, -1560); cv.translate(0, 60)
                E.rrect(cv, 140, 1500 - hh / 2, 800, hh, 36, BR, sombra=True)
                E.icone(cv, "calendario", 220, 1500 - hh / 2 + 70, 56, VERM)
                udraw(cv, info.get("titulo", "Retorno"), 280, 1500 - hh / 2 + 85, 44, 700, PR)
                for i, l in enumerate(ls):
                    yy = 1500 - hh / 2 + 140 + i * 90
                    E.rrect(cv, 190, yy, 700, 70, 20, (236, 246, 240))
                    udraw(cv, l, 230, yy + 47, 34, 600, (20, 110, 70))
                cv.restore()
            zz = self.ultimo(t, "zoom")
            self.alvos = {"centro": (540, 900), "nutri": (640, 860), "paciente": (330, 1000)}

    # ------------------------------------------------ uma ideia, três conteúdos
    class Conteudos(Tela):
        """Uma dúvida vira Reels, carrossel e Stories: passos {"duvida": "..."} e {"mostrar": "reels"|"carrossel"|"stories"}."""
        tipo = "conteudos"

        def app(self, cv, t):
            cv.drawColor(E.C((246, 246, 246)))
            dv = self.ultimo(t, "duvida")
            if dv:
                k = E.e_back(E.prog(t, dv[0], 0.4))
                cv.save(); cv.translate(540, 360); cv.scale(k, k); cv.translate(-540, -360)
                hh = E.altura_texto(dv[1]["duvida"], 50, 800, 820) + 90
                E.rrect(cv, 90, 360 - hh / 2, 900, hh, 40, BR, sombra=True)
                E.texto(cv, "“" + dv[1]["duvida"] + "”", 540, 360, 50, 800, PR, maxw=820)
                cv.restore()
            mostr = [(tp, p["mostrar"]) for tp, p in self.passos if tp <= t and p.get("mostrar")]
            ordem = ["reels", "carrossel", "stories"]
            for tp, nome in mostr:
                if nome not in ordem:
                    continue
                i = ordem.index(nome)
                k = E.e_back(E.prog(t, tp, 0.45))
                x = 60 + i * 330
                y = 640
                w, h = 300, 560
                cv.save(); cv.translate(x + w / 2, y + h / 2); cv.scale(k, k); cv.translate(-(x + w / 2), -(y + h / 2))
                E.rrect(cv, x - 10, y - 10, w + 20, h + 20, 40, (20, 20, 20), sombra=True)
                if nome == "reels":
                    g = skia.GradientShader.MakeLinear([skia.Point(x, y), skia.Point(x, y + h)], [E.C((60, 60, 90)), E.C((20, 20, 30))])
                    p_ = skia.Paint(AntiAlias=True); p_.setShader(g)
                    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 30, 30), p_)
                    nutri_rosto(cv, x + w / 2, y + 230, 110)
                    tri = skia.Path(); tri.moveTo(x + w / 2 - 30, y + 420); tri.lineTo(x + w / 2 + 40, y + 460); tri.lineTo(x + w / 2 - 30, y + 500); tri.close()
                    cv.drawPath(tri, E.P(BR, 0.9))
                elif nome == "carrossel":
                    E.rrect(cv, x, y, w, h, 30, (52, 168, 120))
                    E.texto(cv, self.d.get("carrossel", "Pão engorda?"), x + w / 2, y + 200, 40, 900, BR, maxw=250)
                    for j in range(3):
                        E.rrect(cv, x + 40, y + 300 + j * 50, w - 80, 20, 10, BR, 0.7)
                    for j in range(5):
                        cv.drawCircle(x + w / 2 - 60 + j * 30, y + h - 40, 9, E.P(BR, 1 if j == 0 else 0.4))
                else:
                    g = skia.GradientShader.MakeLinear([skia.Point(x, y), skia.Point(x + w, y + h)], [E.C((245, 133, 41)), E.C((221, 42, 123))])
                    p_ = skia.Paint(AntiAlias=True); p_.setShader(g)
                    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 30, 30), p_)
                    E.rrect(cv, x + 30, y + 200, w - 60, 200, 24, BR)
                    E.rrect(cv, x + 30, y + 200, w - 60, 80, 24, (40, 40, 40))
                    E.texto(cv, "Dúvidas?", x + w / 2, y + 240, 32, 800, BR)
                    E.rrect(cv, x + 50, y + 300, w - 100, 70, 14, (240, 240, 240))
                cv.restore()
                E.texto(cv, {"reels": "REELS", "carrossel": "CARROSSEL", "stories": "STORIES"}[nome], x + w / 2, y + h + 70, 42, 900, PR, E.e_out(E.prog(t, tp, 0.4)))
            self.alvos = {"centro": (540, 900)}

    # ------------------------------------------------ CTA final (comentar ou salvar)
    class CTA(Tela):
        """Final: aba de comentários com a palavra (modo comentar) ou o post sendo salvo (modo salvar)."""
        tipo = "cta"
        escuro = True

        def app(self, cv, t):
            modo = self.d.get("modo", "comentar")
            palavra = self.d.get("palavra", "QUERO")
            cv.drawColor(E.C((24, 52, 40)))
            k0 = E.e_out(E.prog(t, self.t0, 0.4))
            if modo == "salvar":
                E.texto(cv, self.d.get("titulo", "SALVA ESSE VÍDEO"), 540, 330, 84, 900, AMAR, k0, maxw=960)
                # post com o ícone de salvar
                E.rrect(cv, 140, 520, 800, 1000, 40, BR, k0, sombra=True)
                avatar(cv, 220, 600, 44, foto=True)
                udraw(cv, "josefernandesmarketing", 285, 612, 30, 700, PR, k0)
                E.rrect(cv, 140, 670, 800, 680, 0, (52, 168, 120), k0)
                E.texto(cv, self.d.get("post", "Confira hoje"), 540, 1010, 60, 900, BR, k0, maxw=700)
                kt = E.prog(t, self.t0 + 1.0, 0.4)
                x, y = 870, 1420
                pa = skia.Path(); pa.moveTo(x - 24, y - 34); pa.lineTo(x + 24, y - 34); pa.lineTo(x + 24, y + 34); pa.lineTo(x, y + 14); pa.lineTo(x - 24, y + 34); pa.close()
                if kt > 0.3:
                    cv.drawPath(pa, E.P(PR))
                else:
                    cv.drawPath(pa, E.P(PR, 1, stroke=6))
                toque(cv, x, y, t, self.t0 + 1.0)
                if kt > 0.3:
                    kk = E.e_back(E.prog(t, self.t0 + 1.2, 0.4))
                    cv.save(); cv.translate(540, 1660); cv.scale(kk, kk)
                    E.rrect(cv, -300, -55, 600, 110, 30, (40, 40, 40))
                    udraw(cv, "Salvo na sua coleção", -250, 14, 36, 600, BR)
                    cv.restore()
                return
            E.texto(cv, "COMENTE: " + palavra.upper(), 540, 330, 90, 900, AMAR, k0, maxw=980)
            E.rrect(cv, 0, 520, 1080, 1400, 50, BR, k0)
            E.rrect(cv, 490, 545, 100, 10, 5, LINHA)
            udraw(cv, "Comentários", 540 - uw("Comentários", 36, 700) / 2, 620, 36, 700, PR)
            nomes = ["nutri.carlamendes", "dra.julianutri", "nutribeatrizlima", "marinanutricao", "nutri.paulaalves", "lu.nutricionista"]
            extra = ["", "", " 😍", "", " 💚", " 🙌"]
            for i, nm in enumerate(nomes):
                tp = self.t0 + 0.4 + i * 0.35
                k = E.e_back(E.prog(t, tp, 0.35))
                if k <= 0:
                    continue
                y = 700 + i * 150
                cv.save(); cv.translate(0, (1 - k) * 60)
                avatar(cv, 110, y + 40, 40, foto=True)
                udraw(cv, nm, 175, y + 30, 28, 700, PR, E.e_out(k))
                udraw(cv, palavra.upper() + extra[i], 175, y + 75, 34, 400, PR, E.e_out(k))
                cv.restore()
            E.rrect(cv, 40, 1700, 1000, 100, 50, BR, stroke=3)
            E.rrect(cv, 40, 1700, 1000, 100, 50, LINHA, stroke=3)
            avatar(cv, 110, 1750, 36, foto=True)
            dt = t - (self.t0 + 1.2)
            n = int(E.cl(dt / 0.8) * len(palavra))
            udraw(cv, palavra.upper()[:n], 170, 1763, 36, 600, PR)
            udraw(cv, "Publicar", 1000 - uw("Publicar", 32, 700), 1762, 32, 700, AZUL)

    # ------------------------------------------------ mundinho (caminho com estações)
    class Caminho(E.Cena):
        """Mundinho visto de cima: caminho de etapas numeradas que acendem. Passos {"etapa": i} acende; {"final": true} mostra tudo."""
        tipo = "caminho"

        def desenhar(self, cv, t):
            et = self.d.get("etapas", [])
            n = max(1, len(et))
            cv.drawColor(E.C((128, 202, 96)))
            rng = random.Random(4)
            for i in range(70):
                x, y = rng.random() * 1080, rng.random() * 1920
                E.circulo(cv, x, y, 18 + rng.random() * 16, (60, 140, 70))
                E.rrect(cv, x - 4, y + 10, 8, 20, 2, (110, 80, 50))
            on = -1
            fim = None
            for tp, p in self.passos:
                if tp <= t and "etapa" in p:
                    on = max(on, p["etapa"])
                if tp <= t and p.get("final"):
                    fim = tp
            ys = [1660 - i * (1180 / max(1, n - 1)) for i in range(n)] if n > 1 else [900]
            zig = n >= 4
            xs = [(320 if i % 2 == 0 else 760) if zig else 540 for i in range(n)]
            r = 150 if zig else 210
            for i in range(n - 1):
                for j in range(4):
                    k_ = (j + 1) / 5
                    E.rrect(cv, E.lerp(xs[i], xs[i + 1], k_) - 45, E.lerp(ys[i], ys[i + 1], k_) - 16, 90, 32, 16, (240, 235, 222))
            for i, e in enumerate(et):
                y, x = ys[i], xs[i]
                lit = i <= on or fim is not None
                tp = min([tp for tp, p in self.passos if p.get("etapa") == i] or [fim or 99])
                k = E.e_back(E.prog(t, tp, 0.4)) if lit else 0
                pa = skia.Path()
                for a_ in range(6):
                    ang = math.radians(60 * a_ + 30)
                    px, py = x + r * math.cos(ang), y + r * 0.55 * math.sin(ang)
                    pa.moveTo(px, py) if a_ == 0 else pa.lineTo(px, py)
                pa.close()
                cv.save(); cv.translate(0, 18); cv.drawPath(pa, E.P((200, 190, 170))); cv.restore()
                cv.drawPath(pa, E.P(AMAR if lit else (240, 235, 222)))
                E.icone(cv, e.get("icone", "check"), x, y - 10, 100 if not zig else 76, (60, 60, 60) if lit else (190, 185, 175))
                if lit:
                    nome_ = f"{i + 1}. {e.get('nome', '').upper()}"
                    sz = (58 if not zig else 46) * (0.6 + 0.4 * k)
                    fz = E.F(sz, 900); lw_ = fz.measureText(nome_)
                    cv.save(); cv.translate(x, y - r * 0.8)
                    mx = 1000 if not zig else 520
                    if lw_ > mx:
                        cv.scale(mx / lw_, mx / lw_)
                    cv.drawString(nome_, -lw_ / 2, sz * 0.35, fz, E.P((40, 30, 10), 1, stroke=14))
                    cv.drawString(nome_, -lw_ / 2, sz * 0.35, fz, E.P(AMAR))
                    cv.restore()
                    if e.get("rotulo"):
                        pilula(cv, e["rotulo"], x, y + r * 0.75, E.prog(t, tp + 0.3, 0.35), alinhar="c", size=28)
            if fim is not None:
                titulo_grande(cv, self.d.get("titulo", "PRONTO!"), t, fim, y=200)
            cm = [(tp, p) for tp, p in self.passos if tp <= t and p.get("comemora")]
            if cm:
                tp, p = cm[-1]
                confete(cv, t, tp)
                cv.drawColor(E.C((0, 0, 0), 0.35 * E.e_out(E.prog(t, tp, 0.3))))
                titulo_grande(cv, p["comemora"], t, tp, y=p.get("y", 760))
            self.selos(cv, t)

    for cls in (Perfil, Editar, Whats, Stories, Links, Consultorio, Conteudos, CTA, Caminho):
        E.CENAS[cls.tipo] = cls
    E.TELAS = {"perfil", "editar", "whats", "stories", "links", "consultorio", "conteudos", "cta", "caminho"}
