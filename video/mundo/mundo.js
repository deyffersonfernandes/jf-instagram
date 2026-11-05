// Mundinho 3D low-poly (estilo dos vídeos de hexágonos): caminho de plataformas
// hexagonais, uma estação por ideia, câmera andando de uma para a outra.
// A página recebe a linha do tempo (window.TL) e desenha o quadro do tempo t com desenhar(t).
import * as THREE from './three.module.min.js';

const W = 1080, H = 1920;
const D = 36;          // distância entre estações
const R = 8.2;         // raio do hexágono grande
const TL = window.TL;

// ------------------------------------------------------------ utilidades
const cl = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const prog = (t, t0, d = .4) => cl((t - t0) / d);
const eOut = x => 1 - Math.pow(1 - x, 3);
const eInOut = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const eBack = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const lerp = (a, b, k) => a + (b - a) * k;
const rnd = (s => () => (s = (s * 16807) % 2147483647) / 2147483647)(42);

// ------------------------------------------------------------ cena
const gl = document.getElementById('gl');
const renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: true, preserveDrawingBuffer: true });
renderer.setSize(W, H, false);
renderer.setPixelRatio(1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#9fd3f5');
scene.fog = new THREE.Fog('#d9eefa', 70, 190);
const camera = new THREE.PerspectiveCamera(48, W / H, 0.5, 600);
scene.add(new THREE.HemisphereLight('#ffffff', '#8bbf6a', 1.6));
const sol = new THREE.DirectionalLight('#ffffff', 1.5);
sol.position.set(-30, 60, 25);
scene.add(sol);

const mat = c => new THREE.MeshLambertMaterial({ color: c, flatShading: true });
const M = {};
const m = c => (M[c] = M[c] || mat(c));

// chão e céu
const chao = new THREE.Mesh(new THREE.PlaneGeometry(900, 900), m('#86cf5e'));
chao.rotation.x = -Math.PI / 2; chao.position.set(0, -0.05, -150);
scene.add(chao);
// montanhas ao fundo
for (let i = 0; i < 9; i++) {
  const g = new THREE.ConeGeometry(40 + rnd() * 30, 30 + rnd() * 25, 5);
  const mm = new THREE.Mesh(g, m(i % 2 ? '#bfe0d0' : '#cfe8dc'));
  mm.position.set(-200 + i * 50, 8, -330 - rnd() * 40);
  scene.add(mm);
}

function hex(r, h, cor) {
  const g = new THREE.CylinderGeometry(r, r, h, 6);
  const me = new THREE.Mesh(g, m(cor));
  me.rotation.y = Math.PI / 6;
  return me;
}
function sombra(r, op = .18) {
  const g = new THREE.CircleGeometry(r, 20);
  const me = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: '#000', transparent: true, opacity: op, depthWrite: false }));
  me.rotation.x = -Math.PI / 2; me.position.y = 0.62;
  return me;
}
function arvore(x, z, s) {
  const g = new THREE.Group();
  const tr = new THREE.Mesh(new THREE.CylinderGeometry(.25 * s, .3 * s, 1.6 * s, 5), m('#8a5a35'));
  tr.position.y = .8 * s; g.add(tr);
  const cor = ['#3f9e48', '#4cae52', '#5cbd5a', '#368f40'][Math.floor(rnd() * 4)];
  const co = new THREE.Mesh(new THREE.IcosahedronGeometry(1.3 * s, 0), m(cor));
  co.position.y = 2.4 * s; co.rotation.y = rnd() * 3; g.add(co);
  if (rnd() > .5) { const c2 = new THREE.Mesh(new THREE.IcosahedronGeometry(.9 * s, 0), m(cor)); c2.position.set(.7 * s, 2.0 * s, .3 * s); g.add(c2); }
  g.position.set(x, 0, z);
  scene.add(g);
}

// caminho: estações + degraus + caminho que continua no fundo
const N = TL.estacoes.length;
const zEst = i => -i * D;
for (let i = 0; i < N + 5; i++) {
  const z = zEst(i);
  const big = hex(R, 0.6, '#f3eee4'); big.position.set(0, 0.3, z); scene.add(big);
  const borda = hex(R + .25, 0.35, '#d9d2c4'); borda.position.set(0, 0.12, z); scene.add(borda);
  for (let j = 1; j <= 6; j++) {
    const s = hex(1.9, 0.45, '#f3eee4'); s.position.set(0, 0.22, z - R + .3 - j * ((D - 2 * R + .6) / 7)); scene.add(s);
  }
}
for (let i = 0; i < 260; i++) {
  const lado = rnd() > .5 ? 1 : -1;
  const x = lado * (R + 3 + rnd() * 45);
  const z = 30 - rnd() * (N * D + 160);
  arvore(x, z, .8 + rnd() * .9);
}
for (let i = 0; i < 60; i++) { // moitas
  const b = new THREE.Mesh(new THREE.IcosahedronGeometry(.7 + rnd(), 0), m('#57b44f'));
  b.position.set((rnd() > .5 ? 1 : -1) * (R + 1.5 + rnd() * 20), .4, 20 - rnd() * (N * D + 100));
  scene.add(b);
}

// ------------------------------------------------------------ texturas (desenho 2D)
const FONT = 'Montserrat';
function canvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function texto(ctx, s, x, y, size, peso = 800, cor = '#111', maxw = 9999, alinhar = 'left', lh = 1.2) {
  ctx.font = `${peso} ${size}px ${FONT}`; ctx.fillStyle = cor; ctx.textAlign = alinhar; ctx.textBaseline = 'top';
  const palavras = String(s).split(' '); let linha = ''; let yy = y;
  for (const p of palavras) {
    const t = linha ? linha + ' ' + p : p;
    if (linha && ctx.measureText(t).width > maxw) { ctx.fillText(linha, x, yy); yy += size * lh; linha = p; } else linha = t;
  }
  ctx.fillText(linha, x, yy); return yy + size * lh;
}
function nutri2d(ctx, cx, cy, r) {
  const s = r / 100;
  ctx.fillStyle = '#ffe9d2'; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fill();
  ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.clip();
  ctx.fillStyle = '#eec45c'; rr(ctx, cx - 62 * s, cy - 55 * s, 124 * s, 150 * s, 55 * s); ctx.fill();
  ctx.fillStyle = '#fafafa'; rr(ctx, cx - 80 * s, cy + 58 * s, 160 * s, 120 * s, 50 * s); ctx.fill();
  ctx.fillStyle = '#34a878'; ctx.beginPath(); ctx.moveTo(cx - 20 * s, cy + 58 * s); ctx.lineTo(cx + 20 * s, cy + 58 * s); ctx.lineTo(cx, cy + 98 * s); ctx.fill();
  ctx.fillStyle = '#f7d6ba'; ctx.beginPath(); ctx.ellipse(cx, cy + 4 * s, 46 * s, 52 * s, 0, 0, 7); ctx.fill();
  ctx.fillStyle = '#eec45c'; ctx.beginPath(); ctx.moveTo(cx - 50 * s, cy - 4 * s);
  ctx.bezierCurveTo(cx - 52 * s, cy - 70 * s, cx + 40 * s, cy - 82 * s, cx + 52 * s, cy - 8 * s);
  ctx.bezierCurveTo(cx + 30 * s, cy - 36 * s, cx - 5 * s, cy - 38 * s, cx - 28 * s, cy - 18 * s); ctx.fill();
  ctx.fillStyle = '#2a2a33'; for (const dx of [-18, 18]) { ctx.beginPath(); ctx.ellipse(cx + dx * s, cy + 6 * s, 5 * s, 6 * s, 0, 0, 7); ctx.fill(); }
  ctx.strokeStyle = '#c8464f'; ctx.lineWidth = 4 * s; ctx.beginPath(); ctx.moveTo(cx - 13 * s, cy + 28 * s); ctx.quadraticCurveTo(cx, cy + 40 * s, cx + 13 * s, cy + 28 * s); ctx.stroke();
  ctx.restore();
}
function texOutdoor(d) {
  const c = canvas(1200, 600), x = c.getContext('2d');
  const g = x.createLinearGradient(0, 0, 1200, 600); g.addColorStop(0, '#0f5e5a'); g.addColorStop(1, '#1b8a7f');
  x.fillStyle = g; x.fillRect(0, 0, 1200, 600);
  nutri2d(x, 960, 330, 230);
  texto(x, d.titulo || 'Emagreça sem dieta restritiva', 60, 70, 82, 900, '#fff', 700);
  texto(x, d.sub || 'Ana Souza · Nutricionista', 60, 380, 44, 700, '#ffe27a', 700);
  x.fillStyle = '#ffd23f'; rr(x, 60, 470, 420, 80, 40); x.fill();
  texto(x, d.botao || 'Agende sua consulta', 90, 490, 36, 800, '#123', 400);
  return c;
}
function texPlaca(d) {
  const c = canvas(800, 400), x = c.getContext('2d');
  x.fillStyle = '#ffffff'; x.fillRect(0, 0, 800, 400);
  x.fillStyle = '#34a878'; x.fillRect(0, 0, 800, 70);
  nutri2d(x, 140, 230, 110);
  texto(x, d.titulo || 'Ana Souza', 290, 130, 62, 900, '#123', 480);
  texto(x, d.sub || 'Nutricionista · CRN-3 54321', 290, 220, 36, 600, '#3b5', 480);
  texto(x, d.extra || 'Consultas com hora marcada', 290, 290, 30, 600, '#555', 480);
  return c;
}
function telaCelular(desenho) {
  const c = canvas(720, 1440), x = c.getContext('2d');
  x.fillStyle = '#fff'; x.fillRect(0, 0, 720, 1440);
  x.fillStyle = '#111'; x.font = `700 34px ${FONT}`; x.textBaseline = 'top'; x.fillText('9:41', 50, 30);
  x.fillRect(600, 36, 60, 26);
  desenho(x);
  return c;
}
function texJornal(d) {
  return telaCelular(x => {
    x.fillStyle = '#c4170c'; x.fillRect(0, 90, 720, 120);
    texto(x, d.portal || 'Notícias da Cidade', 40, 125, 46, 900, '#fff', 640);
    texto(x, (d.editoria || 'SAÚDE').toUpperCase(), 40, 250, 30, 800, '#c4170c');
    const y = texto(x, d.titulo || 'Nutricionista da cidade explica como emagrecer sem dieta restritiva', 40, 300, 50, 900, '#111', 640, 'left', 1.18);
    texto(x, d.linha || 'Especialista em emagrecimento feminino, Ana Souza atende há 8 anos e dá dicas para quem quer começar', 40, y + 20, 30, 500, '#444', 640, 'left', 1.35);
    const yi = y + 190;
    const g = x.createLinearGradient(0, yi, 0, yi + 420); g.addColorStop(0, '#e8f3ec'); g.addColorStop(1, '#cfe6d8');
    x.fillStyle = g; x.fillRect(40, yi, 640, 420);
    nutri2d(x, 360, yi + 230, 170);
    texto(x, d.credito || 'Foto: Divulgação', 40, yi + 435, 24, 500, '#888');
    texto(x, d.autor || 'Por Redação · 05/11/2026 08h12', 40, yi + 480, 28, 600, '#666');
    for (let i = 0; i < 4; i++) { x.fillStyle = '#e4e4e4'; x.fillRect(40, yi + 540 + i * 44, 640 - (i == 3 ? 220 : 0), 22); }
  });
}
function texAnuncio(d) {
  return telaCelular(x => {
    texto(x, 'Instagram', 40, 100, 46, 800, '#111');
    nutri2d(x, 80, 230, 40);
    texto(x, d.usuario || 'anasouzanutri', 140, 200, 32, 800, '#111');
    texto(x, 'Patrocinado', 140, 240, 26, 500, '#555');
    const g = x.createLinearGradient(0, 300, 0, 1020); g.addColorStop(0, '#ffe3cf'); g.addColorStop(1, '#ffc9a8');
    x.fillStyle = g; x.fillRect(0, 290, 720, 720);
    nutri2d(x, 360, 690, 260);
    x.fillStyle = 'rgba(0,0,0,.45)'; rr(x, 40, 330, 640, 190, 24); x.fill();
    texto(x, d.chamada || 'Emagreça sem dieta restritiva em [sua cidade]', 70, 355, 46, 900, '#fff', 580);
    x.fillStyle = '#0095f6'; x.fillRect(0, 1010, 720, 100);
    texto(x, d.botao || 'Agendar consulta', 40, 1040, 36, 800, '#fff');
    texto(x, '›', 660, 1030, 50, 800, '#fff');
    texto(x, '♥  💬  ➤', 40, 1140, 44, 700, '#111');
    texto(x, (d.curtidas || '1.284 curtidas'), 40, 1210, 30, 800, '#111');
    texto(x, (d.legenda || 'anasouzanutri Atendo mulheres que querem emagrecer com acompanhamento.'), 40, 1260, 28, 500, '#222', 640);
  });
}
function texWhats(d) {
  return telaCelular(x => {
    x.fillStyle = '#008069'; x.fillRect(0, 80, 720, 150);
    texto(x, d.contato || 'Juliana', 150, 120, 40, 800, '#fff');
    texto(x, 'online', 150, 170, 26, 500, '#d8f5ec');
    x.fillStyle = '#c9d6dc'; x.beginPath(); x.arc(90, 155, 40, 0, 7); x.fill();
    x.fillStyle = '#efeae2'; x.fillRect(0, 230, 720, 1210);
    let y = 270;
    for (const msg of (d.mensagens || [])) {
      x.font = `500 34px ${FONT}`;
      const eu = msg.de === 'eu';
      const linhas = []; let l = '';
      for (const p of msg.msg.split(' ')) { const tt = l ? l + ' ' + p : p; if (l && x.measureText(tt).width > 470) { linhas.push(l); l = p } else l = tt; }
      linhas.push(l);
      const w = Math.max(...linhas.map(s => x.measureText(s).width)) + 50, h = linhas.length * 42 + 50;
      const bx = eu ? 680 - w : 40;
      x.fillStyle = eu ? '#d9fdd3' : '#fff'; rr(x, bx, y, w, h, 22); x.fill();
      x.fillStyle = '#111'; linhas.forEach((s, i) => x.fillText(s, bx + 25, y + 20 + i * 42));
      y += h + 24;
    }
  });
}
function texAgenda(d) {
  return telaCelular(x => {
    texto(x, d.titulo || 'Agenda', 40, 100, 52, 900, '#111');
    const dias = ['SEG', 'TER', 'QUA', 'QUI', 'SEX'];
    dias.forEach((dd, i) => texto(x, dd, 60 + i * 130, 200, 28, 800, '#888'));
    const cheios = d.cheios ?? 14;
    let k = 0;
    for (let r = 0; r < 8; r++) for (let i = 0; i < 5; i++) {
      x.fillStyle = (((r * 5 + i) * 7) % 40) < cheios ? '#34a878' : '#eee';
      rr(x, 45 + i * 130, 260 + r * 135, 115, 115, 16); x.fill(); k++;
    }
  });
}
const TEX = { outdoor: texOutdoor, placa: texPlaca, jornal: texJornal, anuncio: texAnuncio, whats: texWhats, agenda: texAgenda };
function textura(c) { const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; }

// ------------------------------------------------------------ objetos
function pessoa(cor = '#e86f6f', opt = {}) {
  const g = new THREE.Group();
  const pele = opt.pele || ['#f1c7a3', '#d9a27c', '#a8714d', '#f6d3b5'][Math.floor(rnd() * 4)];
  const corpo = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.25, .6), m(opt.jaleco ? '#fafafa' : cor)); corpo.position.y = 1.5; g.add(corpo);
  for (const dx of [-.25, .25]) { const p = new THREE.Mesh(new THREE.BoxGeometry(.38, .9, .4), m(opt.calca || '#3c4a78')); p.position.set(dx, .45, 0); g.add(p); }
  for (const dx of [-.65, .65]) { const b = new THREE.Mesh(new THREE.BoxGeometry(.28, 1.0, .3), m(opt.jaleco ? '#fafafa' : cor)); b.position.set(dx, 1.5, 0); g.add(b); }
  const cab = new THREE.Mesh(new THREE.BoxGeometry(.85, .85, .8), m(pele)); cab.position.y = 2.6; g.add(cab);
  const cabelo = new THREE.Mesh(new THREE.BoxGeometry(.92, opt.loira ? .55 : .32, .88), m(opt.loira ? '#eec45c' : (opt.cabelo || '#3b2a1e'))); cabelo.position.y = opt.loira ? 2.92 : 3.05; g.add(cabelo);
  if (opt.loira) { const tras = new THREE.Mesh(new THREE.BoxGeometry(.92, 1.0, .25), m('#eec45c')); tras.position.set(0, 2.45, -.32); g.add(tras); }
  for (const dx of [-.18, .18]) { const o = new THREE.Mesh(new THREE.BoxGeometry(.1, .14, .05), m('#222')); o.position.set(dx, 2.65, .41); g.add(o); }
  if (opt.jaleco) { const v = new THREE.Mesh(new THREE.BoxGeometry(.3, .5, .05), m('#34a878')); v.position.set(0, 1.9, .31); g.add(v); }
  g.add(sombra(.9));
  return g;
}
function painel(canvasTex, w, h, prof = .3, moldura = '#2a2a2a') {
  const g = new THREE.Group();
  const caixa = new THREE.Mesh(new THREE.BoxGeometry(w + .4, h + .4, prof), m(moldura)); g.add(caixa);
  const tela = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: textura(canvasTex) }));
  tela.position.z = prof / 2 + .01; g.add(tela);
  return g;
}
function celular(tipo, d, alt = 9) {
  const g = new THREE.Group();
  const w = alt / 2;
  const corpo = new THREE.Mesh(new THREE.BoxGeometry(w + .5, alt + .6, .5), m('#1d1d1f'));
  corpo.position.y = alt / 2 + 1.2; g.add(corpo);
  const tela = new THREE.Mesh(new THREE.PlaneGeometry(w, alt), new THREE.MeshBasicMaterial({ map: textura(TEX[tipo](d)) }));
  tela.position.set(0, alt / 2 + 1.2, .26); g.add(tela);
  const pe = new THREE.Mesh(new THREE.BoxGeometry(2, .3, 1.6), m('#333')); pe.position.y = .75; g.add(pe);
  g.rotation.x = -.08;
  g.add(sombra(2.6, .15));
  return g;
}
function predio(nome = 'CONSULTÓRIO') {
  const g = new THREE.Group();
  const par = new THREE.Mesh(new THREE.BoxGeometry(7, 4.2, 5), m('#ece6da')); par.position.y = 2.1 + .6; g.add(par);
  const tel = new THREE.Mesh(new THREE.CylinderGeometry(0, 4.9, 2.4, 4, 1), m('#2a9d8f')); tel.rotation.y = Math.PI / 4; tel.scale.set(1.05, 1, .78); tel.position.y = 6.0; g.add(tel);
  const porta = new THREE.Mesh(new THREE.BoxGeometry(1.4, 2.4, .1), m('#7a4b2a')); porta.position.set(0, 1.8, 2.52); g.add(porta);
  for (const dx of [-2.3, 2.3]) { const j = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.2, .1), m('#9fd8f5')); j.position.set(dx, 3.0, 2.52); g.add(j); }
  const c = canvas(512, 96), x = c.getContext('2d'); x.fillStyle = '#2a9d8f'; x.fillRect(0, 0, 512, 96); texto(x, nome, 256, 22, 52, 900, '#fff', 500, 'center');
  const pl = new THREE.Mesh(new THREE.PlaneGeometry(4.2, .8), new THREE.MeshBasicMaterial({ map: textura(c) })); pl.position.set(0, 4.35, 2.56); g.add(pl);
  return g;
}
function rua(g) {
  const asf = new THREE.Mesh(new THREE.PlaneGeometry(2 * R * .95, 3.6), m('#4a4f57'));
  asf.rotation.x = -Math.PI / 2; asf.position.set(0, .62, 3.2); g.add(asf);
  for (let i = -3; i <= 3; i++) { const f = new THREE.Mesh(new THREE.PlaneGeometry(1.1, .22), m('#ffffff')); f.rotation.x = -Math.PI / 2; f.position.set(i * 2.2, .63, 3.2); g.add(f); }
  const calc = new THREE.Mesh(new THREE.BoxGeometry(2 * R * .95, .2, 1), m('#cfcfcf')); calc.position.set(0, .7, 1.0); g.add(calc);
}
function carro(cor) {
  const g = new THREE.Group();
  const b = new THREE.Mesh(new THREE.BoxGeometry(2.6, .8, 1.3), m(cor)); b.position.y = .9; g.add(b);
  const t = new THREE.Mesh(new THREE.BoxGeometry(1.4, .6, 1.2), m('#cfe9f7')); t.position.set(-.1, 1.55, 0); g.add(t);
  for (const dx of [-.85, .85]) for (const dz of [-.65, .65]) { const r = new THREE.Mesh(new THREE.CylinderGeometry(.3, .3, .25, 8), m('#222')); r.rotation.x = Math.PI / 2; r.position.set(dx, .5, dz); g.add(r); }
  return g;
}
function coracao() {
  const s = new THREE.Shape(); s.moveTo(0, -.6); s.bezierCurveTo(-1.2, .2, -.5, 1, 0, .45); s.bezierCurveTo(.5, 1, 1.2, .2, 0, -.6);
  return new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: .25, bevelEnabled: false }), m('#ef4f62'));
}

// Cada estação devolve {grupo, anim(t), ancoras{nome:[x,y,z]}}
const CONSTR = {
  outdoor(d) {
    const g = new THREE.Group(); rua(g);
    for (const dx of [-3.2, 3.2]) { const p = new THREE.Mesh(new THREE.BoxGeometry(.5, 6, .5), m('#6b6b6b')); p.position.set(dx, 3.6, -2.5); g.add(p); }
    const pn = painel(texOutdoor(d), 11, 5.5, .5, '#ffffff'); pn.position.set(0, 7.6, -2.5); g.add(pn);
    const c1 = carro('#e65a5a'), c2 = carro('#4f8cff'); g.add(c1); g.add(c2);
    const ps = [pessoa('#5b8def'), pessoa('#f2a541')]; ps[0].position.set(-5, .6, 0); ps[1].position.set(5.2, .6, -.4); ps.forEach(p => { p.rotation.y = Math.PI; g.add(p) });
    return { grupo: g, anc: { painel: [0, 11, -2.5], rua: [0, 1, 3] }, anim(t) { c1.position.set(((t * 5) % 22) - 11, .62, 3.9); c2.position.set(11 - ((t * 4 + 7) % 22), .62, 2.4); c2.rotation.y = Math.PI; ps.forEach((p, i) => p.rotation.y = Math.PI + .5 * Math.sin(t * .8 + i)); } };
  },
  placa(d) {
    const g = new THREE.Group();
    const pr = predio(d.predio || 'CONSULTÓRIO'); pr.position.set(2.2, 0, -2.5); g.add(pr);
    const poste = new THREE.Mesh(new THREE.BoxGeometry(.3, 3.4, .3), m('#555')); poste.position.set(-3.6, 2.3, 2.2); g.add(poste);
    const pl = painel(texPlaca(d), 5.2, 2.6, .25, '#ffffff'); pl.position.set(-3.6, 4.9, 2.2); pl.rotation.y = .25; g.add(pl);
    const ps = pessoa('#8e6bd8'); ps.position.set(-1.5, .6, 3.6); g.add(ps);
    return { grupo: g, anc: { placa: [-3.6, 6.9, 2.2], predio: [2.2, 7.8, -2.5] }, anim(t) { ps.position.x = -1.5 + Math.sin(t * .6) * 3; ps.rotation.y = -Math.PI / 2 * Math.sign(Math.cos(t * .6)) + Math.PI / 2; } };
  },
  jornal(d) {
    const g = new THREE.Group();
    const c = celular('jornal', d, 10); c.position.set(0, .6, -1); g.add(c);
    const ps = pessoa('#4f8cff'); ps.position.set(-4.2, .6, 2); ps.rotation.y = .6; g.add(ps);
    const ps2 = pessoa('#f2a541', { cabelo: '#111' }); ps2.position.set(4.3, .6, 2.2); ps2.rotation.y = -.6; g.add(ps2);
    return { grupo: g, anc: { tela: [0, 13, -1], pessoas: [-4.2, 3.8, 2] }, anim(t) { } };
  },
  anuncio(d) {
    const g = new THREE.Group();
    const c = celular('anuncio', d, 10); c.position.set(0, .6, -1); g.add(c);
    const gente = [];
    for (let i = 0; i < 5; i++) { const p = pessoa(['#e86f6f', '#5b8def', '#f2a541', '#46b47a', '#a07be0'][i]); p.position.set(-5 + i * 2.5, .6, 3.4 + (i % 2) * .8); p.rotation.y = Math.PI; g.add(p); gente.push(p); }
    return { grupo: g, anc: { tela: [0, 13, -1], pessoas: [0, 4, 3.6] }, anim(t) { gente.forEach((p, i) => { p.rotation.y = Math.PI + Math.sin(t * 1.2 + i) * .25; }); } };
  },
  whats(d) {
    const g = new THREE.Group();
    const c = celular('whats', d, 9.5); c.position.set(1.6, .6, -1); g.add(c);
    const n = pessoa('#fff', { jaleco: true, loira: true }); n.position.set(-4.4, .6, 1.4); n.rotation.y = .5; g.add(n);
    return { grupo: g, anc: { tela: [1.6, 12.5, -1], nutri: [-4.4, 4, 1.4] }, anim(t) { n.rotation.y = .5 + Math.sin(t * 2) * .1; } };
  },
  consultorio(d) {
    const g = new THREE.Group();
    const pr = predio(d.predio || 'CONSULTÓRIO'); pr.position.set(2.5, 0, -2.8); g.add(pr);
    const n = pessoa('#fff', { jaleco: true, loira: true }); n.position.set(-2.4, .6, 1.0); g.add(n);
    const pac = []; for (let i = 0; i < (d.pacientes || 3); i++) { const p = pessoa(['#e86f6f', '#46b47a', '#a07be0', '#5b8def'][i % 4]); g.add(p); pac.push(p); }
    const cor = []; if (d.coracoes) for (let i = 0; i < 4; i++) { const h = coracao(); h.scale.setScalar(.7); g.add(h); cor.push(h); }
    // anel de acompanhamento (os pacientes voltam)
    const anel = new THREE.Mesh(new THREE.TorusGeometry(3.2, .12, 6, 40), m('#ffd23f')); anel.rotation.x = Math.PI / 2; anel.position.set(-2.4, .7, 1.0); if (d.anel) g.add(anel);
    return { grupo: g, anc: { nutri: [-2.4, 4.2, 1], predio: [2.5, 8, -2.8] }, anim(t) {
      pac.forEach((p, i) => { const a = t * .9 + i * (Math.PI * 2 / pac.length); p.position.set(-2.4 + Math.cos(a) * 3.2, .6, 1.0 + Math.sin(a) * 3.2); p.rotation.y = -a; });
      cor.forEach((h, i) => { const k = ((t * .5 + i * .25) % 1); h.position.set(-2.4 + (i - 1.5) * 1.3, 4 + k * 4, 1); h.material.transparent = true; h.material.opacity = 1 - k; h.rotation.y = t; });
    } };
  },
  agenda(d) {
    const g = new THREE.Group();
    const c = celular('agenda', d, 9.5); c.position.set(0, .6, -1); g.add(c);
    return { grupo: g, anc: { tela: [0, 12.5, -1] }, anim() { } };
  },
  pessoas(d) {
    const g = new THREE.Group(); const gente = [];
    for (let i = 0; i < (d.n || 8); i++) { const p = pessoa(['#e86f6f', '#5b8def', '#f2a541', '#46b47a', '#a07be0'][i % 5]); p.position.set((rnd() - .5) * 10, .6, (rnd() - .5) * 7); g.add(p); gente.push(p); }
    return { grupo: g, anc: { pessoas: [0, 4.5, 0] }, anim(t) { gente.forEach((p, i) => p.rotation.y = t + i); } };
  },
};

// monta as estações
const EST = TL.estacoes.map((e, i) => {
  const f = CONSTR[e.tipo] || CONSTR.pessoas;
  const o = f(e.dados || {});
  o.grupo.position.set(0, 0, zEst(i));
  o.grupo.scale.setScalar(.001);
  scene.add(o.grupo);
  o.z = zEst(i);
  return o;
});

// ------------------------------------------------------------ câmera
function camEm(i) { const z = zEst(i); return { p: [0, 14, z + 27], a: [0, 5.6, z - 2] }; }
function camFinal() { const zm = zEst((N - 1) / 2); const L = (N - 1) * D; return { p: [0, 40 + L * 1.05, zm + 30 + L * .35], a: [0, 0, zm - 20] }; }
function camera_t(t) {
  let cur = camEm(0);
  for (let i = 0; i < N; i++) {
    const e = TL.estacoes[i];
    if (t >= e.t - .55) {
      const k = eInOut(prog(t, e.t - .55, 1.0));
      const de = i > 0 ? camEm(i - 1) : camEm(0), para = camEm(i);
      cur = { p: de.p.map((v, j) => lerp(v, para.p[j], k)), a: de.a.map((v, j) => lerp(v, para.a[j], k)) };
      cur.p[1] += Math.sin(k * Math.PI) * 11;  // sobe por cima da estação anterior
    }
  }
  if (TL.final && t >= TL.final.t) {
    const k = eInOut(prog(t, TL.final.t, 2.2));
    const f = camFinal();
    cur = { p: cur.p.map((v, j) => lerp(v, f.p[j], k)), a: cur.a.map((v, j) => lerp(v, f.a[j], k)) };
    scene.fog.near = lerp(70, 300, k); scene.fog.far = lerp(190, 700, k);
  }
  // respiração leve
  cur.p[0] += Math.sin(t * .5) * .25;
  camera.position.set(...cur.p); camera.lookAt(...cur.a);
}

// ------------------------------------------------------------ camada 2D (títulos, etiquetas, legenda)
const ov = document.getElementById('ov'); const o = ov.getContext('2d');
function contorno(s, x, y, size, cor = '#fff', borda = '#111', bw = 16, peso = 900, alinhar = 'center', maxw = 1000) {
  o.font = `${peso} ${size}px ${FONT}`; o.textAlign = alinhar; o.textBaseline = 'middle';
  const w = o.measureText(s).width; const sc = Math.min(1, maxw / w);
  o.save(); o.translate(x, y); o.scale(sc, sc);
  o.lineJoin = 'round'; o.strokeStyle = borda; o.lineWidth = bw; o.strokeText(s, 0, 0); o.fillStyle = cor; o.fillText(s, 0, 0);
  o.restore();
}
function projetar(v) { const p = new THREE.Vector3(...v).project(camera); return [(p.x + 1) / 2 * W, (1 - p.y) / 2 * H, p.z]; }
function pilula(s, x, y, k, cor = '#111', ponto = '#e5484d') {
  if (k <= 0) return;
  s = s.toUpperCase();
  o.font = `800 34px ${FONT}`; const w = o.measureText(s).width + 80;
  x = Math.max(w / 2 + 24, Math.min(W - w / 2 - 24, x));
  const sc = lerp(.5, 1, eBack(k));
  o.save(); o.translate(x, y); o.scale(sc, sc); o.globalAlpha = eOut(k);
  o.fillStyle = '#fff'; o.shadowColor = 'rgba(0,0,0,.25)'; o.shadowBlur = 14; o.shadowOffsetY = 4;
  o.beginPath(); o.roundRect(-w / 2, -32, w, 64, 32); o.fill(); o.shadowColor = 'transparent';
  o.lineWidth = 4; o.strokeStyle = '#111'; o.stroke();
  o.fillStyle = ponto; o.beginPath(); o.arc(-w / 2 + 30, 0, 9, 0, 7); o.fill();
  o.fillStyle = cor; o.textAlign = 'left'; o.textBaseline = 'middle'; o.fillText(s, -w / 2 + 50, 2);
  o.restore();
}
function legenda(t) {
  let atual = null;
  for (const p of TL.palavras) if (p.ini - .03 <= t && t <= p.fim + .12) atual = p;
  if (!atual) return;
  const s = atual.w.replace(/^[“"'(]+|[”"').,;:!?…]+$/g, '');
  if (!s) return;
  const k = eBack(prog(t, atual.ini - .03, .16));
  o.save(); o.translate(540, TL.legenda_y || 1250); o.scale(lerp(.75, 1, k), lerp(.75, 1, k));
  contorno(s, 0, 0, 104, atual.dest ? '#ffd23f' : '#fff', '#111', 22, 900, 'center', 960);
  o.restore();
}

// ------------------------------------------------------------ quadro
window.desenhar = function (t) {
  camera_t(t);
  EST.forEach((e, i) => {
    const ed = TL.estacoes[i];
    const k = prog(t, ed.aparece ?? ed.t, .6);
    const s = k <= 0 ? .001 : eBack(k);
    e.grupo.scale.setScalar(Math.max(.001, s));
    e.anim && e.anim(t);
  });
  renderer.render(scene, camera);
  o.clearRect(0, 0, W, H);
  o.drawImage(gl, 0, 0);
  // títulos numerados (o da estação atual fica grande no topo)
  const fim = TL.final && t >= TL.final.t;
  TL.estacoes.forEach((ed, i) => {
    if (!ed.titulo || t < ed.t_titulo) return;
    const k = eBack(prog(t, ed.t_titulo, .45));
    if (!fim) {
      const prox = TL.estacoes[i + 1];
      if (prox && t > prox.t - .15) return;
      o.save(); o.translate(540, 215); o.rotate(-.03); o.scale(lerp(1.8, 1, k), lerp(1.8, 1, k));
      contorno(`${i + 1}. ${ed.titulo}`, 0, 0, 88, '#ffd23f', '#3a2a08', 20, 900, 'center', 980);
      o.restore();
    } else {
      const [x, y] = projetar([0, 4, zEst(i)]);
      contorno(`${i + 1}. ${ed.titulo}`, x, y - 70, 46, '#ffd23f', '#3a2a08', 12, 900, 'center', 600);
    }
  });
  // etiquetas presas no 3D
  if (!fim) TL.estacoes.forEach((ed, i) => {
    const prox = TL.estacoes[i + 1];
    if (prox && t > prox.t + .2) return;
    (ed.rotulos || []).forEach((r, j) => {
      if (t < r.t) return;
      const a = EST[i].anc[r.alvo] || [0, 6, 0];
      const [x, y, z] = projetar([a[0], a[1] + (r.dy || 0), a[2] + EST[i].z]);
      if (z > 1) return;
      pilula(r.texto, x, y - j * 0, prog(t, r.t, .35), '#111', r.cor || '#e5484d');
    });
  });
  if (fim) {
    const k = eBack(prog(t, TL.final.t_titulo ?? (TL.final.t + 1.2), .5));
    if (k > 0) {
      o.save(); o.translate(540, 250); o.rotate(-.04); o.scale(lerp(1.4, 1, k), lerp(1.4, 1, k));
      const ls = (TL.final.titulo || '').split('\n');
      ls.forEach((l, i) => contorno(l, 0, (i - (ls.length - 1) / 2) * 120, 110, '#ffd23f', '#3a2a08', 24, 900, 'center', 1000));
      o.restore();
    }
  }
  legenda(t);
  return ov.toDataURL('image/jpeg', .9);
};
window.pronto = true;
