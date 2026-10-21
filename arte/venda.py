#!/usr/bin/env python3
"""Card de venda (último slide dos carrosséis de competência). Decisão do José, 21/10.

   python3 arte/venda.py "Gancho em negrito ligado ao tema do carrossel." saida.png

Layout: cabeçalho com avatar (assets/venda/header.png), gancho em negrito, texto fixo do
Método Nutri+, "Diagnóstico gratuito no link da bio." e o print da página (assets/venda/lp.png).
"""
import base64, sys, os, html
from playwright.sync_api import sync_playwright
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')
b64 = lambda p: base64.b64encode(open(os.path.join(R, p), 'rb').read()).decode()
FIXO = ["No Método Nutri+, eu e meu time montamos a estratégia completa do seu consultório: "
        "posicionamento, anúncios, conversão e fidelização dos seus pacientes.",
        "Diagnóstico gratuito no link da bio."]
def pagina(gancho):
    ps = ''.join(f'<p class="{"b" if i == 0 else ""}">{html.escape(t)}</p>' for i, t in enumerate([gancho] + FIXO))
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
@font-face{{font-family:G;src:url(data:font/ttf;base64,{b64('fonts/Gelasio.ttf')});font-weight:400 700}}
html,body{{margin:0;width:1080px;height:1440px;background:#fff}}
.wrap{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center}}
.h{{display:block;width:1080px}} .txt{{padding:0 84px;margin-top:34px}}
p{{font-family:G;font-size:43px;line-height:1.42;color:#111;margin:0 0 26px}} p.b{{font-weight:700}}
.ban{{margin:14px 84px 0;border-radius:26px;overflow:hidden;background:#141a6e;box-shadow:0 10px 30px rgba(20,26,110,.25)}}
.ban img{{display:block;width:100%}}
</style></head><body><div class="wrap"><img class="h" src="data:image/png;base64,{b64('venda/header.png')}">
<div class="txt">{ps}</div><div class="ban"><img src="data:image/png;base64,{b64('venda/lp.png')}"></div></div></body></html>"""
if __name__ == '__main__':
    gancho, saida = sys.argv[1], sys.argv[2]
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1080, 'height': 1440})
        pg.set_content(pagina(gancho)); pg.wait_for_timeout(300)
        h = pg.evaluate("document.querySelector('.wrap').scrollHeight")
        hc = pg.evaluate("[...document.querySelectorAll('.wrap>*')].reduce((s,e)=>s+e.offsetHeight,0)+34+14")
        pg.screenshot(path=saida); b.close()
        print(saida, 'ok' if hc <= 1440 else 'TEXTO GRANDE DEMAIS: encurte o gancho')
