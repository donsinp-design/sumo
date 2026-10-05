'use strict';
// Gameplay transitions: hanging sumo banners slide in from both sides like sliding doors, cover the
// camera completely, then slide back out the same way to reveal the next state. They only tilt a
// little as they move, trailing from their top poles. Used only between bouts:
// match start, round end -> round start, match end -> results. Never in menus.
//
//   S.Banners.wall(opts)            start fully covered, hold, slide away (match start)
//   S.Banners.flood(opts)           banners slide in; once covered: opts.onCovered(), hold, slide away
//   opts: { hold: seconds, speed: 1 = normal (higher = faster), onCovered, onDone }
(function () {
  const N = 11, PIV = 0.064;          // pivot: the top pole, as a fraction of image height
  const CLOTH = [0.09, 0.994];        // rows of the image that are solid cloth (images end at the cloth: no pole feet or tassels)
  const imgs = [], dark = [];
  let ready = false;

  // preload and decode every banner up front, plus a darker copy for the back layer
  const load = Promise.all(Array.from({ length: N }, (_, i) => new Promise((res) => {
    const im = new Image();
    im.src = 'assets/banners/banner_' + String(i + 1).padStart(2, '0') + '.webp';
    const done = () => {
      imgs[i] = im;
      const c = document.createElement('canvas'); c.width = im.naturalWidth || 1; c.height = im.naturalHeight || 1;
      const x = c.getContext('2d'); x.drawImage(im, 0, 0);
      x.globalCompositeOperation = 'source-atop'; x.fillStyle = 'rgba(12,5,10,0.22)'; x.fillRect(0, 0, c.width, c.height);
      dark[i] = c; res();
    };
    let once = false; const go = () => { if (!once && im.naturalWidth) { once = true; done(); } };
    im.onload = go; im.onerror = res;
    if (im.decode) im.decode().then(go, () => {});
  }))).then(() => {
    ready = imgs.every((im) => im && im.naturalWidth); prepareSoon();
  });

  const cv = document.createElement('canvas');
  cv.id = 'bnr';
  document.body.appendChild(cv);
  const ctx = cv.getContext('2d');
  let W = 0, H = 0, dpr = 1;
  const fit = () => {
    dpr = Math.min(2, devicePixelRatio || 1); W = innerWidth; H = innerHeight;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  };
  fit(); addEventListener('resize', fit);

  const rnd = (a, b) => a + Math.random() * (b - a);
  const easeOutBack = (t) => { const c = 1.5; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
  const easeInCubic = (t) => t * t * t;

  let list = [], phase = 'idle', T = 0, run = null, last = 0, raf = 0, prepared = null;
  // build the next wall ahead of time, when the game is quiet, so a transition never starts with a stall
  const prepare = () => { if (ready && phase === 'idle') { fit(); prepared = { W, H, list: layout() }; } };
  const prepareSoon = () => setTimeout(() => (window.requestIdleCallback || ((f) => f()))(prepare), 300);

  // one banner's resting place in the wall. Three sizes, layered: small ones hang at the back,
  // medium ones make up most of the wall, and a few large ones pass close to the camera.
  const SIZE = [[0.48, 0.6], [0.66, 0.82], [0.88, 1.02]]; // cloth height as a fraction of screen height
  // banners keep their proportions (at most a slight stretch to reach below the screen). Wherever one ends
  // mid-screen, a banner hung in front covers its bottom edge, so no pole foot or tassel ever shows.
  const LOW = 1.04, STRETCH = 1.12;
  function make(layer, x, clothTop, imgI) {
    const reach = true; // every banner hangs past the bottom of the screen: no hem ever shows, even mid-slide
    const im = imgs[imgI], asp = im.naturalWidth / im.naturalHeight;
    const clothH0 = H * rnd(SIZE[layer][0], SIZE[layer][1]); let clothH = clothH0;
    if (clothTop === null) clothTop = rnd(-0.12 * H, H - clothH * 0.5);
    if (reach) clothH = Math.max(clothH, H * LOW - clothTop);        // must hang past the bottom of the screen
    else if (clothTop + clothH < H * LOW && clothTop + clothH * STRETCH >= H * LOW) clothH = H * LOW - clothTop; // close: stretch a touch
    // a longer banner also gets wider, so the art is never pulled out of shape by more than a little
    const h = clothH / (CLOTH[1] - CLOTH[0]), w = (clothH0 / (CLOTH[1] - CLOTH[0])) * asp * (clothH / clothH0) / Math.min(STRETCH, clothH / clothH0);
    const top = clothTop - h * CLOTH[0];
    return { im, dk: dark[imgI], layer, w, h, clothH, x, y: top + h * PIV, rot: 0, cx: x, cy: top + h * PIV };
  }
  // bottom edge of a banner (cloth hem, pole foot, tassels), in screen space
  const hemOf = (b) => { const top = b.y - b.h * PIV; return { x0: b.x - b.w * 0.6, x1: b.x + b.w * 0.6, y0: top + b.h * (CLOTH[1] - 0.05), y1: top + b.h * 1.0 }; };
  // after layout: find hems that still show and hang covering banners in front of them
  function coverHems(out, pick) {
    for (let pass = 0; pass < 4; pass++) {
      const shown = [];
      out.forEach((b, i) => {
        const e = hemOf(b); if (e.y0 > H || e.y1 < 0 || e.x1 < 0 || e.x0 > W) return;
        // sample along the hem; it's hidden if every sample is inside a banner drawn later
        for (let k = 0; k <= 6; k++) {
          const sx = e.x0 + (e.x1 - e.x0) * k / 6, sy = (e.y0 + e.y1) / 2;
          if (sx < 0 || sx > W || sy > H) continue;
          const hid = out.some((c, j) => j > i && Math.abs(sx - c.x) < c.w * 0.44 && sy > c.y - c.h * PIV + c.h * CLOTH[0] && sy < c.y - c.h * PIV + c.h * CLOTH[1]);
          if (!hid) { shown.push({ x: sx, y: sy }); break; }
        }
      });
      if (!shown.length) return;
      for (const p of shown) out.push(make(2, p.x + rnd(-0.15, 0.15) * W * 0.1, Math.max(-0.15 * H, p.y - H * rnd(0.25, 0.55)), pick(), true));
    }
  }

  // lay out a crowded, irregular wall with no gaps: keep hanging banners over whatever still shows
  function layout() {
    const out = [], order = [];
    for (let i = 0; i < N; i++) order.push(i);
    order.sort(() => Math.random() - 0.5);
    let k = 0; const pick = () => order[k++ % N];
    const mw = Math.min(320, Math.round(W / 3)), mh = Math.round(mw * H / W);
    const mc = document.createElement('canvas'); mc.width = mw; mc.height = mh;
    const mx = mc.getContext('2d', { willReadFrequently: true });
    // a loose scatter first, so the fill does not start from a neat grid
    const medW = make(1, 0, null, 0).w;
    for (let x = rnd(-0.3, 0.1) * medW; x < W + medW * 0.5; x += medW * rnd(0.9, 1.4)) out.push(make(Math.random() < 0.3 ? 0 : 1, x, null, pick()));
    // the mask only ever gains coverage, so each new banner is drawn onto it once
    for (const b of out) drawOne(mx, b, mw / W, true);
    for (let tries = 0; tries < 70; tries++) {
      const d = mx.getImageData(0, 0, mw, mh).data;
      const holes = [];
      for (let y = 0; y < mh; y += 2) for (let x = 0; x < mw; x += 2) if (d[(y * mw + x) * 4 + 3] < 200) holes.push(x, y);
      if (!holes.length) break;
      // cover a random hole with a banner placed loosely around it
      const q = ((Math.random() * holes.length / 2) | 0) * 2;
      const hx = (holes[q] + 0.5) * W / mw, hy = (holes[q + 1] + 0.5) * H / mh;
      const b = make(Math.random() < 0.25 ? 0 : 1, 0, hy - H * rnd(0.1, 0.6), pick());
      b.x = b.cx = hx + rnd(-0.25, 0.25) * b.w;
      out.push(b); drawOne(mx, b, mw / W, true);
    }
    // the final check must be exact, so fill any last pinholes at full resolution
    const fw = Math.min(960, Math.round(W)), fh = Math.round(fw * H / W);
    const fc = document.createElement('canvas'); fc.width = fw; fc.height = fh;
    const fx = fc.getContext('2d', { willReadFrequently: true });
    for (const b of out) drawOne(fx, b, fw / W, true);
    for (let tries = 0; tries < 20; tries++) {
      const d = fx.getImageData(0, 0, fw, fh).data;
      let gx = -1, gy = 0;
      for (let y = 0; y < fh && gx < 0; y++) for (let x = 0; x < fw; x++) if (d[(y * fw + x) * 4 + 3] < 200) { gx = x; gy = y; break; }
      if (gx < 0) break;
      const b = make(1, (gx + 0.5) * W / fw, (gy + 0.5) * H / fh - H * rnd(0.1, 0.4), pick());
      out.push(b); drawOne(fx, b, fw / W, true);
    }
    // a few large banners right in front of the camera
    const big = W > H ? 3 + ((Math.random() * 3) | 0) : 2;
    for (let i = 0; i < big; i++) out.push(make(2, (i + rnd(0.15, 0.85)) * W / big, rnd(-0.18, 0.02) * H, pick(), true));
    // back to front; within a layer keep the order they were hung
    out.forEach((b, i) => { b.ord = i; });
    out.sort((a, b) => a.layer - b.layer || a.ord - b.ord);
    coverHems(out, pick);
    return out;
  }

  function drawOne(c, b, s, solid) {
    c.save();
    c.scale(s, s);
    c.translate(b.x, b.y);
    c.rotate(b.rot);
    c.drawImage(solid || b.layer ? b.im : b.dk, -b.w / 2, -b.h * PIV, b.w, b.h);
    c.restore();
  }

  const dropCover = () => { const c = document.getElementById('bootcover'); if (c) c.remove(); };
  function start(opts, covered) {
    if (!ready || document.hidden) { // assets not there, or nobody watching: never hold the game up
      if (opts.onCovered) opts.onCovered();
      if (opts.onDone) opts.onDone();
      return;
    }
    fit();
    list = prepared && prepared.W === W && prepared.H === H ? prepared.list : layout();
    prepared = null;
    const sp = opts.speed || 1;
    run = { opts, sp, hold: opts.hold === undefined ? 0.12 : opts.hold, fired: false };
    const mid = W / 2;
    for (const b of list) {
      const edge = Math.abs(b.cx - mid) / (mid + 1);           // 0 centre .. 1 edge
      const fast = b.layer === 2 ? 0.82 : b.layer === 0 ? 1.18 : 1; // big ones in front move faster: depth
      // sliding doors: the left half comes in from the left, the right half from the right; edges arrive first
      b.dir = b.cx < mid ? -1 : 1;
      b.sx = b.cx + b.dir * (W * 0.55 + b.w * 1.2);
      b.inDelay = ((1 - edge) * 0.16 + rnd(0, 0.07) + (b.layer === 2 ? 0.06 : 0)) / sp;
      b.inDur = 0.36 * fast / sp;
      // and they slide back out the same way; the centre has furthest to go, so it clears last
      b.outDelay = (rnd(0, 0.07) + (b.layer === 2 ? 0 : 0.04)) / sp;
      b.outDur = 0.48 * fast / sp;
      b.drift = b.dir * (W * 0.55 + b.w * 1.2) + b.dir * Math.abs(b.cx - mid) * -0.3;
      b.rot = 0; b.rv = 0; b.px = b.cx;
      if (!covered) { b.x = b.sx; b.px = b.sx; }
    }
    phase = covered ? 'hold' : 'in'; T = 0;
    if (covered) dropCover();
    if (covered) { run.fired = true; if (opts.onCovered) opts.onCovered(); }
    else if (S.game && S.game.audio) S.game.audio.whoosh(0.35);
    cv.classList.add('on');
    last = performance.now();
    cancelAnimationFrame(raf); raf = requestAnimationFrame(tick);
  }

  function tick(now) {
    const dt = Math.min(0.05, (now - last) / 1000) * S.Banners.rate; last = now; T += dt;
    const A = S.game && S.game.audio;
    if (phase === 'in') {
      let all = true;
      for (const b of list) {
        const t = Math.max(0, Math.min(1, (T - b.inDelay) / b.inDur));
        if (t < 1 || Math.abs(b.rot) > 0.006) all = false; // covered only once every banner hangs straight
        b.x = b.sx + (b.cx - b.sx) * easeOutBack(t);
      }
      if (all) {
        for (const b of list) b.x = b.cx;
        phase = 'hold'; T = 0; dropCover();
        if (A) A.clack();
        if (!run.fired) { run.fired = true; if (run.opts.onCovered) run.opts.onCovered(); }
      }
    } else if (phase === 'hold') {
      if (T >= run.hold) { phase = 'out'; T = 0; if (A) A.whoosh(0.25); }
    } else if (phase === 'out') {
      let all = true;
      for (const b of list) {
        const t = Math.max(0, Math.min(1, (T - b.outDelay) / b.outDur));
        if (t < 1) all = false;
        b.x = b.cx + b.drift * easeInCubic(t);
      }
      if (all) { stop(); if (run && run.opts.onDone) run.opts.onDone(); return; }
    }
    // a slight tilt: the cloth hangs from its pole and trails behind as it slides, then settles
    for (const b of list) {
      const vx = dt > 0 ? (b.x - b.px) / dt : 0; b.px = b.x;
      const target = Math.max(-0.16, Math.min(0.16, (vx / W) * 0.055));
      for (let k = 0, n = Math.ceil(dt * 120); k < n; k++) { // small steps keep the spring stable on slow phones
        const h = dt / n; b.rv += ((target - b.rot) * 700 - b.rv * 46) * h; b.rot += b.rv * h;
      }
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.imageSmoothingQuality = 'high';
    for (const b of list) drawOne(ctx, b, dpr, false);
    raf = requestAnimationFrame(tick);
  }

  function stop() {
    cancelAnimationFrame(raf); phase = 'idle'; list = []; prepareSoon();
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, cv.width, cv.height);
    cv.classList.remove('on');
  }

  S.Banners = {
    load,
    rate: 1, // testing: slow the transition down
    get busy() { return phase !== 'idle'; },
    get covered() { return phase === 'hold'; },
    // run cb once the banner art is decoded (or after `wait` ms, whichever comes first)
    whenReady(cb, wait) { let done = false; const go = () => { if (!done) { done = true; cb(); } }; load.then(go); setTimeout(go, wait || 3000); },
    wall(opts) { start(opts || {}, true); },
    flood(opts) { start(opts || {}, false); },
    stop,
    _advance(sec) { let t = last; for (let i = 0; i < sec * 60 && phase !== 'idle'; i++) { t += 1000 / 60; tick(t); } cancelAnimationFrame(raf); }, // testing only
    _dbg: () => ({ phase, T, n: list.length, b: list.map((b) => [Math.round(b.x), Math.round(b.cx), +b.rot.toFixed(3), +(b.inDelay || 0).toFixed(2)]) }),
  };
})();
