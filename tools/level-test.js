// LEVEL TEST: loads a level in the real game (public/, no build needed) and takes screenshots.
//   node tools/level-test.js <level> <outdir> [--mode coop|hide|tag|story] [--fpv] [--map] [--run N] [x z yaw]...
//     --map    one overhead plan of the whole level (orthographic, upper storeys hidden) -> <outdir>/map.jpg
//     --fpv    third-person camera (behind him) instead of the top-down one
//     --run N  run N seconds of play first (the computer P2 plays; prints where everyone is)
//     x z yaw  put P1 there (yaw: the way he faces, radians; -1.57 = away from the default camera) and take shot<k>.jpg
// Needs a static server on 127.0.0.1:8896 at the repo root (python3 -m http.server 8896).
const path = require('path');
const { chromium } = require(process.env.PW || 'playwright');
(async () => {
  const a = process.argv.slice(2), lv = a[0], out = path.resolve(a[1]);
  const opt = { mode: 'coop', fpv: false, map: false, run: 0 }, pts = [];
  for (let i = 2; i < a.length; i++) {
    if (a[i] === '--mode') opt.mode = a[++i]; else if (a[i] === '--fpv') opt.fpv = true; else if (a[i] === '--map') opt.map = true; else if (a[i] === '--run') opt.run = +a[++i];
    else pts.push(+a[i]);
  }
  require('fs').mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ args: ['--enable-webgl', '--ignore-gpu-blocklist', '--enable-gpu'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  p.on('pageerror', (e) => console.log('PAGEERR', e.message));
  p.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE', m.text()); });
  await p.addInitScript(() => { window.KUMITE_STYLE = 'anime'; window.KUMITE_FORK = 'kumitegame'; });
  await p.goto('http://127.0.0.1:8896/public/index.html?v=' + Date.now());
  await p.waitForFunction(() => window.S && S.Chars && S.Chars.ready && S.SoftSumo && S.SoftSumo.loaded && S.game, null, { timeout: 90000 });
  await p.waitForTimeout(2500);
  const ok = await p.evaluate(({ lv, opt }) => {
    if (lv !== 'bath' && !(S.Levels && S.Levels[lv])) return 'no level ' + lv + ' (is js/levels/' + lv + '.js in index.html?)';
    let a = 1; Math.random = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    const g = S.game; g.partyLevel = lv; g.partyCpu = true; g.partyFpv = opt.fpv;
    if (opt.mode === 'story') { if (!g.startLevelStory) return 'no story mode yet'; g.startLevelStory(lv); } else g.startParty(opt.mode);
    window.requestAnimationFrame = () => 0; return 'ok';
  }, { lv, opt });
  if (ok !== 'ok') { console.log('ERR', ok); process.exit(1); }
  await p.waitForFunction(() => S.game.camp && (S.game.camp.kit || S.game.camp.lvId === 'bath'), null, { timeout: 60000 });
  await p.evaluate(() => { const c = S.game.camp; const h = c.hud && c.hud.querySelector('.card'); if (h) { h.style.transition = 'none'; h.style.opacity = 0; } });
  const st = (lbl) => p.evaluate((lbl) => { const c = S.game.camp; const f = (q) => q.toFixed(1); return lbl + ' ' + JSON.stringify({ p1: [f(c.ps[0].x), f(c.ps[0].z)], p2: [f(c.ps[1].x), f(c.ps[1].z), c.ps[1].st, c.ps[1].maw || c.ps[1].pants || ''], staff: (c.staff || []).map((s) => s.mode + '@' + f(s.a.x) + ',' + f(s.a.z)) }); }, lbl);
  if (opt.run) { for (let s = 0; s < opt.run; s += 5) { await p.evaluate(() => { const c = S.game.camp; for (let i = 0; i < 150; i++) c.frame(1 / 30); }); console.log(await st('t=' + (s + 5))); } }
  if (opt.map) {
    await p.evaluate(() => {
      const c = S.game.camp, V = c.lv, B = V ? V.bounds : { x0: -21, x1: 24, z0: -93, z1: 5 }, r = c.R.r, W = innerWidth, H = innerHeight;
      const cx = (B.x0 + B.x1) / 2, cz = (B.z0 + B.z1) / 2, w = B.x1 - B.x0, d = B.z1 - B.z0, k = Math.max(w / W, d / H) * 1.04;
      const cam = new THREE.OrthographicCamera(-W * k / 2, W * k / 2, H * k / 2, -H * k / 2, 0.1, 400); cam.position.set(cx, 150, cz); cam.up.set(0, 0, -1); cam.lookAt(cx, 0, cz); cam.updateProjectionMatrix();
      const up = c.kit && c.kit.getObjectByName('UPPER'); if (up) up.visible = false;
      for (let i = 0; i < 10; i++) c.frame(1 / 30);
      r.setScissorTest(false); r.setViewport(0, 0, W, H); r.render(c.scene, cam);
    });
    await p.screenshot({ path: out + '/map.jpg', type: 'jpeg', quality: 88 });
    console.log('map ->', out + '/map.jpg');
  }
  for (let i = 0, k = 0; i + 2 < pts.length + 0.5 && i < pts.length; i += 3, k++) {
    await p.evaluate((s) => { const c = S.game.camp, P = c.ps[0]; c.place(P, s[0], s[1], s[2]); P.yaw = s[2]; P.cpos = null; P.camT.set(s[0], 0, s[1] - 2.6); for (let j = 0; j < 45; j++) c.frame(1 / 30); }, pts.slice(i, i + 3));
    await p.screenshot({ path: `${out}/shot${k}.jpg`, type: 'jpeg', quality: 85 });
    console.log('shot ->', `${out}/shot${k}.jpg`, pts.slice(i, i + 3).join(' '));
  }
  await b.close(); process.exit(0);
})().catch((e) => { console.log('ERR', e); process.exit(1); });
