// Renderiza o mundinho 3D quadro a quadro no Chrome sem tela e grava o MP4 (sem áudio).
// Uso: node video/mundo/render3d.js linha_do_tempo.json saida.mp4 [--quadros 1.5,4,9 --folha folha.jpg]
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
let puppeteer;
try { puppeteer = require('puppeteer-core'); } catch (e) { puppeteer = require(path.join(process.cwd(), 'node_modules', 'puppeteer-core')); }
const RAIZ = path.resolve(__dirname, '..');
const [tlArq, saida] = process.argv.slice(2);
const args = process.argv.slice(4);
const quadros = args.includes('--quadros') ? args[args.indexOf('--quadros') + 1].split(',').map(Number) : null;
const TL = JSON.parse(fs.readFileSync(tlArq, 'utf8'));
const TIPOS = { '.html': 'text/html', '.js': 'text/javascript', '.ttf': 'font/ttf' };
const srv = http.createServer((q, r) => {
  const p = path.join(RAIZ, decodeURIComponent(q.url.split('?')[0]));
  if (!p.startsWith(RAIZ) || !fs.existsSync(p)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'Content-Type': TIPOS[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(r);
});
srv.listen(0, async () => {
  const porta = srv.address().port;
  const chrome = process.env.CHROME || ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'].find(f => fs.existsSync(f));
  const b = await puppeteer.launch({ executablePath: chrome, headless: 'new', args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const pg = await b.newPage();
  pg.on('pageerror', e => console.error('erro na página:', e.message));
  await pg.evaluateOnNewDocument(tl => { window.TL = tl; }, TL);
  await pg.goto(`http://127.0.0.1:${porta}/mundo/mundo.html`);
  await pg.waitForFunction('window.pronto === true', { timeout: 60000 });
  const fps = TL.fps || 30;
  if (quadros) {
    for (const t of quadros) {
      const url = await pg.evaluate(t => window.desenhar(t), t);
      fs.writeFileSync(saida.replace(/(\.\w+)?$/, `-${t}.jpg`), Buffer.from(url.split(',')[1], 'base64'));
    }
  } else {
    const n = Math.round(TL.dur * fps);
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-c:v', 'mjpeg', '-r', String(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', saida], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = 0; i < n; i++) {
      const url = await pg.evaluate(t => window.desenhar(t), i / fps);
      const ok = ff.stdin.write(Buffer.from(url.split(',')[1], 'base64'));
      if (!ok) await new Promise(r => ff.stdin.once('drain', r));
      if (i % (fps * 5) === 0) console.log(`  ${Math.round(i / fps)}s de ${Math.round(TL.dur)}s`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await b.close(); srv.close();
});
