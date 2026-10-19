#!/usr/bin/env node
/* Desenha as artes da Central JF sem abrir a página (usado pelo Designer).

   NODE_PATH=$(npm root -g) node arte/render.js pedido.json pasta_saida

   pedido.json:
     {"estilo": "frase" | "tweet" | "noticia",   // frase = fundo branco Montserrat com [[verde]]
      "carrossel": true|false,                    // carrossel com mais de 1 slide põe "arrasta →" no slide 1
      "slides": ["texto do slide 1", ...],
      "blocos": [null | {"tipo":"manchete",...} | {"tipo":"citacao",...}, ...]}   // só para "noticia"

   Saída: pasta_saida/1.png, 2.png ... (1080x1440), igual ao que a Central gera.
*/
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
(async () => {
  const [, , pedidoArq, saida] = process.argv;
  const pedido = JSON.parse(fs.readFileSync(pedidoArq, 'utf8'));
  const raiz = path.resolve(__dirname, '..');
  const fonte = (fam, arq, peso) => `@font-face{font-family:"${fam}";src:url("file://${raiz}/assets/fonts/${arq}");font-weight:${peso}}`;
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
    ${fonte('Montserrat', 'Montserrat.ttf', '100 900')}
    ${fonte('Instrument Sans', 'InstrumentSans.ttf', '400 700')}
    ${fonte('Gelasio', 'Gelasio.ttf', '400 700')}
  </style></head><body><div style="font-family:Montserrat">.</div><div style="font-family:'Instrument Sans'">.</div><div style="font-family:Gelasio">.</div>
  <script>const S={modelos:[]};const $=id=>document.getElementById(id);const TEM_VOZ=false;const esc=s=>String(s);</script>
  <script src="file://${raiz}/arte/funcoes.js"></script></body></html>`;
  const tmp = path.join(require('os').tmpdir(), 'arte-' + process.pid + '.html');
  fs.writeFileSync(tmp, html);
  const exe = fs.existsSync('/opt/pw-browsers/chromium') ? undefined : undefined;
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage();
  await p.goto('file://' + tmp);
  const imgs = await p.evaluate(async (ped) => {
    await fontesArte();
    await document.fonts.ready;
    const slides = ped.slides || [];
    const car = !!ped.carrossel && slides.length > 1;
    const out = [];
    for (let i = 0; i < slides.length; i++) {
      const blob = await desenharSlide(slides[i], car && i === 0, ped.estilo || 'frase', (ped.blocos || [])[i] || null);
      const buf = await blob.arrayBuffer();
      let s = ''; const u = new Uint8Array(buf);
      for (let k = 0; k < u.length; k += 0x8000) s += String.fromCharCode.apply(null, u.subarray(k, k + 0x8000));
      out.push(btoa(s));
    }
    return out;
  }, pedido);
  fs.mkdirSync(saida, { recursive: true });
  imgs.forEach((b64, i) => fs.writeFileSync(path.join(saida, `${i + 1}.png`), Buffer.from(b64, 'base64')));
  await b.close();
  fs.unlinkSync(tmp);
  console.log(JSON.stringify({ ok: true, arquivos: imgs.map((_, i) => path.join(saida, `${i + 1}.png`)) }));
})().catch(e => { console.error(e); process.exit(1); });
