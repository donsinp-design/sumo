'use strict';
// Themed stages. Each one swaps the dohyo for a giant everyday object in its own surroundings, drawn in the same
// cel-shaded style. The fighting circle is always the same size and always marked, so the fighting rules are the
// same everywhere (except DJ VINYL, which turns). No crowd on themed stages.
// A builder gets (renderer, static group, spinning group) and may return a per-frame tick(T, dt, match).
(function () {
  const R = S.RING_R, RD = R + 0.7, TAU = Math.PI * 2;
  const toon = S.toon, mesh = (...a) => S.R3.mesh(...a), ctex = (...a) => S.R3.canvasTex(...a);
  const BOX = () => S.R3.GEO.box;

  S.STAGES = [
    { id: 'dohyo', name: 'DOHYO' }, { id: 'vacuum', name: 'ROBOT VACUUM' }, { id: 'cake', name: 'BIRTHDAY CAKE' }, // (poker chip, taiko drum, soda can: removed)
    { id: 'vinyl', name: 'DJ VINYL' }, { id: 'heli', name: 'HELIPAD' }, { id: 'pizza', name: 'PIZZA' },
    { id: 'watch', name: 'CLOCK' }, { id: 'earth', name: 'FLAT EARTH' },
    { id: 'lily', name: 'LILY PAD' }, { id: 'sushi', name: 'SUSHI TRAIN' },
    { id: 'random', name: 'RANDOM' },
  ];
  // RANDOM: a different stage every match, never the one you just played (the classic dohyo is in the pool too)
  let lastRandom = null;
  S.stageFor = (id) => {
    if (id !== 'random') return S.STAGES.some((s) => s.id === id) ? id : 'dohyo';
    const pool = S.STAGES.filter((s) => s.id !== 'random' && s.id !== lastRandom);
    lastRandom = pool[(Math.random() * pool.length) | 0].id; return lastRandom;
  };

  // ---------------------------------------------------------------- shared pieces
  const W = 1024, C = W / 2, RR = C * R / RD; // canvas size, centre, ring radius in pixels
  const ink = '#1a0e14';
  function top(spin, paint) {
    const tex = ctex(W, W, (g) => { paint(g); });
    const m = new THREE.Mesh(new THREE.CircleGeometry(RD, 128).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: tex }));
    m.position.y = 0.006; spin.add(m); return m;
  }
  function side(g, paint, opts) {
    opts = opts || {};
    const h = opts.h || 0.62, rad = opts.r || RD;
    const tex = paint ? ctex(1024, opts.th || 128, paint) : null;
    if (tex) { tex.wrapS = THREE.RepeatWrapping; tex.repeat.x = opts.rep || 2; }
    const cyl = mesh(new THREE.CylinderGeometry(rad, rad * (opts.taper || 1.01), h, 128, 1, true), toon(tex ? 0xffffff : opts.color, { shade: opts.shade || 0x555555, map: tex || undefined, rimAmt: 0.3 }), 0.03);
    cyl.position.y = (opts.y || 0) - h / 2; g.add(cyl); return cyl;
  }
  function edgeLine(g, y) {
    const m = new THREE.Mesh(new THREE.TorusGeometry(RD, 0.035, 6, 128), new THREE.MeshBasicMaterial({ color: 0x150b10 }));
    m.rotation.x = Math.PI / 2; m.position.y = y || 0.01; g.add(m); return m;
  }
  // the ground the stage stands on: a big textured plane
  function ground(g, y, paint, size, rep, px) {
    const tex = ctex(px || 512, px || 512, paint); tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(rep || 1, rep || 1);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(size || 90, size || 90).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: tex }));
    m.position.y = y; g.add(m); return m;
  }
  const bx = (g, sx, sy, sz, col, x, y, z, o) => { const m = mesh(BOX(), toon(col, o || {}), 0.025); m.scale.set(sx, sy, sz); m.position.set(x, y + sy / 2, z); g.add(m); return m; };
  const cy = (g, rt, rb, h, col, x, y, z, o, seg) => { const m = mesh(new THREE.CylinderGeometry(rt, rb, h, seg || 24), toon(col, o || {}), 0.02); m.position.set(x, y + h / 2, z); g.add(m); return m; };
  const sp = (g, r, col, x, y, z, o) => { const m = mesh(new THREE.SphereGeometry(r, 16, 12), toon(col, o || {}), 0.02); m.position.set(x, y, z); g.add(m); return m; };
  const circ = (g, r, fill, stroke, lw) => { g.beginPath(); g.arc(C, C, r, 0, TAU); if (fill) { g.fillStyle = fill; g.fill(); } if (stroke) { g.lineWidth = lw || 4; g.strokeStyle = stroke; g.stroke(); } };
  const ring = (g, r0, r1, col) => { g.beginPath(); g.arc(C, C, r1, 0, TAU); g.arc(C, C, r0, 0, TAU, true); g.fillStyle = col; g.fill('evenodd'); };
  const glowMat = (col, op) => new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: op === undefined ? 0.9 : op, depthWrite: false });

  S.STAGE_BUILD = {
    // ---------------------------------------------------------------- robot vacuum, roaming a living room
    vacuum(Rn, g, spin) {
      const H = 0.9;
      top(spin, (c) => {
        const gr = c.createRadialGradient(C, C, 40, C, C, C); gr.addColorStop(0, '#f6f8fb'); gr.addColorStop(1, '#d4dae2'); c.fillStyle = gr; c.fillRect(0, 0, W, W);
        ring(c, RR + 10, C, '#3a3f48');
        circ(c, 300, null, '#c3cad3', 6);
        c.save(); c.shadowColor = '#3ad8ff'; c.shadowBlur = 24; circ(c, RR, null, '#3ad8ff', 12); c.restore();
      });
      side(g, null, { color: 0x2e323a, shade: 0x101216, h: H }); edgeLine(g);
      // two spinning side brushes underneath at the front; they turn with the robot
      const front = new THREE.Group(); g.add(front);
      const brushes = [-1, 1].map((sd) => {
        const b = new THREE.Group(); b.position.set(Math.sin(sd * 0.5) * (RD - 0.35), -H + 0.06, -Math.cos(0.5) * (RD - 0.35)); front.add(b);
        cy(b, 0.25, 0.25, 0.08, 0x2b3038, 0, 0, 0, { shade: 0x101216 });
        for (let k = 0; k < 3; k++) { const p = new THREE.Group(); p.rotation.y = k * TAU / 3; b.add(p); const arm = mesh(BOX(), toon(0xe8e8e8, { shade: 0x8a8a8a }), 0.01); arm.scale.set(2.2, 0.03, 0.07); arm.position.set(1.2, 0.04, 0); p.add(arm); }
        return b;
      });
      // just floorboards with a rug; the pattern repeats every TILE units so the floor can slide forever
      const TILE = 72;
      const floor = new THREE.Group(); g.add(floor);
      ground(floor, -H, (c, w) => {
        for (let y = 0; y < w; y += 32) { c.fillStyle = (y / 32) % 2 ? '#a36e3f' : '#ba8552'; c.fillRect(0, y, w, 31); c.fillStyle = 'rgba(60,30,10,0.4)'; c.fillRect(0, y + 31, w, 1); for (let x = ((y / 32) % 2) * 80; x < w; x += 160) c.fillRect(x, y, 1, 32); }
        const rx = w * 0.3, ry = w * 0.36, rw = w * 0.34, rh = w * 0.24;
        c.fillStyle = '#5a6aa8'; c.fillRect(rx, ry, rw, rh); c.strokeStyle = '#e8d8a8'; c.lineWidth = 6; c.strokeRect(rx + 10, ry + 10, rw - 20, rh - 20); c.fillStyle = '#c84a4a'; c.fillRect(rx + 30, ry + 30, rw - 60, rh - 60);
      }, TILE * 5, 5);
      // driving: go straight for a while, stop, turn on the spot, go again
      let a = -Math.PI / 2, mode = 'drive', t = 3, turnTo = a, ox = 0, oz = 0;
      return (T, dt) => {
        brushes[0].rotation.y += dt * 10; brushes[1].rotation.y -= dt * 10;
        t -= dt;
        if (mode === 'drive') {
          ox -= Math.cos(a) * 1.6 * dt; oz -= Math.sin(a) * 1.6 * dt;
          if (t <= 0) { mode = 'turn'; turnTo = a + (Math.random() < 0.5 ? -1 : 1) * (1.0 + Math.random() * 1.6); }
        } else {
          const d = turnTo - a, step = Math.sign(d) * Math.min(Math.abs(d), dt * 1.3); a += step;
          if (Math.abs(turnTo - a) < 1e-3) { mode = 'drive'; t = 2.5 + Math.random() * 3.5; }
        }
        ox = ((ox % TILE) + TILE) % TILE; oz = ((oz % TILE) + TILE) % TILE;
        floor.position.set(ox, 0, oz);
        front.rotation.y = -a - Math.PI / 2;
      };
    },

    // ---------------------------------------------------------------- poker chip on a casino table
    chip(Rn, g, spin) {
      const H = 0.35;
      top(spin, (c) => {
        c.fillStyle = '#c8262a'; c.fillRect(0, 0, W, W);
        for (let k = 0; k < 8; k++) { const a = k / 8 * TAU; c.beginPath(); c.arc(C, C, (RR + C) / 2 + 2, a - 0.13, a + 0.13); c.lineWidth = 60; c.strokeStyle = '#f6f0e4'; c.stroke(); }
        circ(c, RR, null, '#f6f0e4', 8);
        c.setLineDash([42, 30]); circ(c, RR * 0.66, null, '#f6f0e4', 14); c.setLineDash([]);
        circ(c, RR * 0.44, '#f4ead6', '#8a1416', 10);
        c.fillStyle = '#c8262a'; c.font = 'bold 250px serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('♠', C, C + 10);
      });
      side(g, (c, w, h) => { for (let k = 0; k < 16; k++) { c.fillStyle = k % 2 ? '#f6f0e4' : '#c8262a'; c.fillRect(k * w / 16, 0, w / 16, h); } }, { rep: 1, h: H });
      edgeLine(g);
      // green felt with the betting layout, a padded rail and a few cards
      ground(g, -H, (c, w) => {
        c.fillStyle = '#1e6a3a'; c.fillRect(0, 0, w, w);
        c.strokeStyle = 'rgba(255,240,200,0.75)'; c.lineWidth = 3; c.beginPath(); c.arc(w / 2, w * 0.15, w * 0.62, 0.35, Math.PI - 0.35); c.stroke(); c.beginPath(); c.arc(w / 2, w * 0.15, w * 0.5, 0.4, Math.PI - 0.4); c.stroke();
        c.fillStyle = 'rgba(255,240,200,0.75)'; c.font = 'bold 22px serif'; c.textAlign = 'center'; c.fillText('BLACKJACK PAYS 3 TO 2', w / 2, w * 0.72); c.font = '16px serif'; c.fillText('DEALER MUST STAND ON 17', w / 2, w * 0.76);
      }, 44, 1, 1024);
      const rail = toon(0x3a1a12, { shade: 0x1a0806 });
      for (const [sx, sz, x, z] of [[46, 1.4, 0, -22], [46, 1.4, 0, 22], [1.4, 46, -22, 0], [1.4, 46, 22, 0]]) { const m = mesh(BOX(), rail, 0.03); m.scale.set(sx, 1, sz); m.position.set(x, -H + 0.5, z); g.add(m); }
      const card = (x, z, r, suit, red) => { const t = ctex(128, 180, (c, w, h) => { c.fillStyle = '#fbfaf6'; c.fillRect(0, 0, w, h); c.strokeStyle = '#999'; c.lineWidth = 4; c.strokeRect(2, 2, w - 4, h - 4); c.fillStyle = red ? '#c8262a' : '#111'; c.font = 'bold 34px serif'; c.fillText('A', 12, 40); c.font = '90px serif'; c.textAlign = 'center'; c.fillText(suit, w / 2, h / 2 + 30); }); const m = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 2.25).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: t })); m.position.set(x, -H + 0.02, z); m.rotation.y = r; g.add(m); };
      card(-6.5, 8.5, 0.3, '♠', false); card(-5.2, 8.9, -0.2, '♥', true); card(7.5, 7.8, 0.6, '♦', true);
    },

    // ---------------------------------------------------------------- taiko drum on a festival stage
    taiko(Rn, g, spin) {
      const H = 2.4;
      top(spin, (c) => {
        c.fillStyle = '#ead8b2'; c.fillRect(0, 0, W, W);
        c.strokeStyle = 'rgba(160,120,70,0.12)'; c.lineWidth = 2; for (let k = 0; k < 160; k++) { c.beginPath(); const x = Math.random() * W, y = Math.random() * W; c.moveTo(x, y); c.lineTo(x + (Math.random() - 0.5) * 80, y + (Math.random() - 0.5) * 80); c.stroke(); }
        ring(c, RR + 8, C, '#3a1d12');
        circ(c, RR, null, '#b89a6a', 6);
        for (let k = 0; k < 40; k++) { const a = k / 40 * TAU, r = (RR + C) / 2 + 4; c.beginPath(); c.arc(C + Math.cos(a) * r, C + Math.sin(a) * r, 10, 0, TAU); c.fillStyle = '#e8b84a'; c.fill(); c.lineWidth = 3; c.strokeStyle = ink; c.stroke(); }
        // mitsudomoe
        for (let k = 0; k < 3; k++) {
          const a = k / 3 * TAU;
          c.beginPath();
          for (let s = 0; s <= 30; s++) { const f = s / 30, ang = a + f * 2.3, rad = 80 + f * 90, w2 = 70 * (1 - f); c.lineTo(C + Math.cos(ang) * (rad + w2), C + Math.sin(ang) * (rad + w2)); }
          for (let s = 30; s >= 0; s--) { const f = s / 30, ang = a + f * 2.3, rad = 80 + f * 90, w2 = 70 * (1 - f); c.lineTo(C + Math.cos(ang) * (rad - w2 * 0.3), C + Math.sin(ang) * (rad - w2 * 0.3)); }
          c.closePath(); c.fillStyle = '#c0301e'; c.fill(); c.lineWidth = 5; c.strokeStyle = ink; c.stroke();
          c.beginPath(); c.arc(C + Math.cos(a) * 95, C + Math.sin(a) * 95, 62, 0, TAU); c.fillStyle = '#c0301e'; c.fill(); c.stroke();
        }
      });
      side(g, (c, w, h) => {
        c.fillStyle = '#8a4a22'; c.fillRect(0, 0, w, h);
        for (let x = 0; x < w; x += 32) { c.fillStyle = 'rgba(0,0,0,0.18)'; c.fillRect(x, 0, 3, h); }
        c.fillStyle = '#3a1d12'; c.fillRect(0, 0, w, 14); c.fillRect(0, h - 14, w, 14);
        for (let x = 10; x < w; x += 34) { for (const y of [24, h - 24]) { c.beginPath(); c.arc(x, y, 6, 0, TAU); c.fillStyle = '#e8b84a'; c.fill(); } }
      }, { rep: 3, h: H, th: 256, taper: 0.92 });
      edgeLine(g);
      // stage boards, a red-and-white curtain, a row of lanterns, the drum stand
      ground(g, -H, (c, w) => { for (let x = 0; x < w; x += 64) { c.fillStyle = (x / 64) % 2 ? '#9a6a3a' : '#a8784a'; c.fillRect(x, 0, 62, w); c.fillStyle = '#5a3a1e'; c.fillRect(x + 62, 0, 2, w); } }, 90, 8);
      const curtain = new THREE.Mesh(new THREE.PlaneGeometry(60, 9), new THREE.MeshBasicMaterial({ map: (() => { const t = ctex(1024, 64, (c, w, h) => { for (let x = 0; x < w; x += 64) { c.fillStyle = (x / 64) % 2 ? '#f6f0e4' : '#c8262a'; c.fillRect(x, 0, 64, h); } }); return t; })() }));
      curtain.position.set(0, -H + 4.5, -17); g.add(curtain);
      const lanterns = [];
      for (let k = -4; k <= 4; k++) {
        const L = new THREE.Group(); L.position.set(k * 4.2, -H + 6, -14.5); g.add(L);
        const body = mesh(new THREE.SphereGeometry(0.8, 16, 12), toon(0xe2321a, { shade: 0x7a1408, rim: 0xffd080 }), 0.02); body.scale.y = 1.25; L.add(body);
        for (const y of [1, -1]) { const cap = mesh(new THREE.CylinderGeometry(0.4, 0.4, 0.25, 12), toon(0x1a1a1a), 0.01); cap.position.y = y; L.add(cap); }
        lanterns.push(L);
      }
      for (const sd of [-1, 1]) { const leg = bx(g, 0.5, 3.4, 0.5, 0x5a2a12, sd * (RD - 0.6), -H - 1, RD * 0.3, { shade: 0x2a1006 }); leg.rotation.z = sd * 0.3; }
      return (T) => { lanterns.forEach((L, i) => { L.rotation.z = Math.sin(T * 1.3 + i) * 0.06; }); };
    },

    // ---------------------------------------------------------------- soda can in the fridge
    can(Rn, g, spin) {
      const H = RD * 2 * 1.8;
      top(spin, (c) => {
        const gr = c.createRadialGradient(C, C, 30, C, C, C); gr.addColorStop(0, '#eef1f4'); gr.addColorStop(1, '#a9b1bb'); c.fillStyle = gr; c.fillRect(0, 0, W, W);
        ring(c, RR - 4, C, '#c4cad2'); circ(c, RR, null, '#6a727c', 8);
        circ(c, RR * 0.84, null, '#8d96a1', 8); circ(c, RR * 0.84 - 8, null, 'rgba(255,255,255,0.55)', 3);
        // the opening: a scored teardrop in front of the rivet
        const ry = C + RR * 0.1, oy = C + RR * 0.62;
        const tear = (k) => { c.beginPath(); c.moveTo(C, ry + 20 * k); c.bezierCurveTo(C + 170 * k, ry + 30 * k, C + 150 * k, oy, C, oy - (1 - k) * 40); c.bezierCurveTo(C - 150 * k, oy, C - 170 * k, ry + 30 * k, C, ry + 20 * k); };
        tear(1); c.fillStyle = '#b4bcc6'; c.fill(); c.lineWidth = 7; c.strokeStyle = '#5c646e'; c.stroke();
        tear(0.86); c.lineWidth = 3; c.strokeStyle = 'rgba(255,255,255,0.7)'; c.stroke();
        // the pull tab, lying flat: nose over the opening, finger ring toward the back, riveted in the middle
        const tw = RR * 0.2, tn = C + RR * 0.2, tb = C - RR * 0.56;
        const tabPath = (dx, dy) => { c.beginPath(); c.moveTo(C - tw + dx, tn - 40 + dy); c.quadraticCurveTo(C - tw + dx, tn + dy, C + dx, tn + dy); c.quadraticCurveTo(C + tw + dx, tn + dy, C + tw + dx, tn - 40 + dy); c.lineTo(C + tw + dx, tb + 60 + dy); c.quadraticCurveTo(C + tw + dx, tb + dy, C + dx, tb + dy); c.quadraticCurveTo(C - tw + dx, tb + dy, C - tw + dx, tb + 60 + dy); c.closePath(); };
        tabPath(10, 14); c.fillStyle = 'rgba(40,46,56,0.35)'; c.fill(); // shadow
        tabPath(0, 0); const tg = c.createLinearGradient(C - tw, 0, C + tw, 0); tg.addColorStop(0, '#f4f6f8'); tg.addColorStop(0.55, '#d6dce2'); tg.addColorStop(1, '#a8b0ba'); c.fillStyle = tg; c.fill();
        c.lineWidth = 8; c.strokeStyle = '#3c434c'; c.stroke();
        // finger hole: you see the lid through it
        const hw = tw * 0.62, ht = C - RR * 0.16, hb = tb + RR * 0.08;
        c.beginPath(); c.moveTo(C - hw, ht); c.lineTo(C + hw, ht); c.lineTo(C + hw, hb + 40); c.quadraticCurveTo(C + hw, hb, C, hb); c.quadraticCurveTo(C - hw, hb, C - hw, hb + 40); c.closePath();
        c.fillStyle = '#c4cad2'; c.fill(); c.lineWidth = 7; c.strokeStyle = '#3c434c'; c.stroke();
        // rivet
        c.beginPath(); c.arc(C, C + RR * 0.02, 34, 0, TAU); c.fillStyle = '#e6eaee'; c.fill(); c.lineWidth = 6; c.strokeStyle = '#3c434c'; c.stroke();
        c.beginPath(); c.arc(C - 8, C + RR * 0.02 - 8, 12, 0, TAU); c.fillStyle = '#fff'; c.fill();
        // a lip around the tab nose
        c.beginPath(); c.arc(C, tn - 50, tw * 0.6, 0.15 * Math.PI, 0.85 * Math.PI); c.lineWidth = 4; c.strokeStyle = 'rgba(60,67,76,0.6)'; c.stroke();
      });
      const lip = mesh(new THREE.TorusGeometry(RD - 0.18, 0.16, 10, 96), toon(0xd0d6dc, { shade: 0x6a727c, spec: 0.9 }), 0.015); lip.rotation.x = Math.PI / 2; lip.position.y = 0.08; spin.add(lip);
      side(g, (c, w, h) => {
        c.fillStyle = '#d42a2a'; c.fillRect(0, 0, w, h);
        c.fillStyle = '#f6f0e4'; c.beginPath(); c.moveTo(0, h * 0.55); for (let x = 0; x <= w; x += 16) c.lineTo(x, h * 0.55 + Math.sin(x / 60) * 18); c.lineTo(w, h * 0.7); for (let x = w; x >= 0; x -= 16) c.lineTo(x, h * 0.7 + Math.sin(x / 60) * 18); c.fill();
        c.fillStyle = '#fff'; c.font = 'bold italic 72px sans-serif'; c.textBaseline = 'middle'; c.fillText('KUMITE COLA', 60, h * 0.3); c.fillText('KUMITE COLA', w / 2 + 60, h * 0.3);
        c.fillStyle = '#c4cad2'; c.fillRect(0, 0, w, 12); c.fillRect(0, h - 16, w, 16);
      }, { rep: 2, h: H, th: 512 });
      edgeLine(g, 0.2);
      // inside the fridge: a glass shelf and a lit back wall, with a wedge of cheese and a tomato next to the can
      ground(g, -H, (c, w) => { c.fillStyle = '#dfeef4'; c.fillRect(0, 0, w, w); c.fillStyle = 'rgba(255,255,255,0.6)'; for (let k = 0; k < 6; k++) c.fillRect(k * 90 + 20, 0, 30, w); }, 120, 3);
      bx(g, 120, 40, 1, 0xf4f8fa, 0, -H, -26, { shade: 0xb8c8d0 });
      const shape = new THREE.Shape(); shape.moveTo(0, 0); shape.lineTo(16, 0); shape.lineTo(0, 9); shape.closePath();
      const holes = ctex(256, 256, (c, w) => { c.fillStyle = '#f6c84a'; c.fillRect(0, 0, w, w); for (let k = 0; k < 26; k++) { c.beginPath(); c.arc(Math.random() * w, Math.random() * w, 6 + Math.random() * 16, 0, TAU); c.fillStyle = '#d8a42a'; c.fill(); } });
      const cheese = mesh(new THREE.ExtrudeGeometry(shape, { depth: 9, bevelEnabled: false }), toon(0xffffff, { shade: 0xb07a1a, map: holes }), 0.04);
      cheese.position.set(9, -H, 6); cheese.rotation.y = -0.4; g.add(cheese);
      const tomato = sp(g, 6.5, 0xe0301e, -15, -H + 6, 4, { shade: 0x7a0e08, spec: 0.7 }); tomato.scale.y = 0.85;
      for (let k = 0; k < 5; k++) { const lf = mesh(new THREE.ConeGeometry(0.7, 3.2, 4), toon(0x3a9a3a, { shade: 0x1a4a1a }), 0.01); lf.rotation.set(Math.PI / 2, k / 5 * TAU, 0); lf.position.set(-15 + Math.cos(k / 5 * TAU) * 1.4, -H + 11.6, 4 + Math.sin(k / 5 * TAU) * 1.4); g.add(lf); }
      cy(g, 0.4, 0.5, 1.6, 0x3a7a2a, -15, -H + 11.2, 4, { shade: 0x1a3a1a });
    },

    // ---------------------------------------------------------------- birthday cake on a party table
    cake(Rn, g, spin) {
      const H = 2.0;
      top(spin, (c) => {
        const gr = c.createRadialGradient(C, C, 40, C, C, C); gr.addColorStop(0, '#fff3f6'); gr.addColorStop(1, '#fbd9e5'); c.fillStyle = gr; c.fillRect(0, 0, W, W);
        const cols = ['#ff5a7a', '#5ac8ff', '#ffd23a', '#7ae07a', '#b07aff', '#ffffff'];
        for (let k = 0; k < 420; k++) { const a = Math.random() * TAU, r = Math.sqrt(Math.random()) * (RR - 20); c.save(); c.translate(C + Math.cos(a) * r, C + Math.sin(a) * r); c.rotate(Math.random() * 3); c.fillStyle = cols[k % cols.length]; c.fillRect(-9, -3, 18, 6); c.restore(); }
        ring(c, RR + 6, C, '#fff3e0');
        circ(c, RR, null, '#f07aa0', 14);
      });
      side(g, (c, w, h) => {
        const band = (y0, y1, col) => { c.fillStyle = col; c.fillRect(0, y0 * h, w, (y1 - y0) * h); };
        band(0, 1, '#f2c870'); band(0.38, 0.44, '#fff6e6'); band(0.44, 0.48, '#e0405a'); band(0.68, 0.74, '#fff6e6'); band(0.74, 0.77, '#e0405a'); band(0.93, 1, '#8a4a2a');
        c.fillStyle = '#fbd3e0'; c.fillRect(0, 0, w, h * 0.14);
        for (let x = 0; x < w; x += 46) { c.beginPath(); c.ellipse(x + 23, h * 0.14, 18, 14 + (x % 3) * 10, 0, 0, Math.PI); c.fill(); }
      }, { rep: 3, h: H, th: 256 });
      edgeLine(g);
      const white = toon(0xfff6f2, { shade: 0xd9a8b8 }), pink = toon(0xf59ab8, { shade: 0xb8506e }), berry = toon(0xe02a3a, { shade: 0x7a0e18 }), leaf = toon(0x4ab04a, { shade: 0x1e5a1e });
      for (let k = 0; k < 34; k++) {
        const a = k / 34 * TAU, r = RD - 0.28;
        const d = mesh(new THREE.SphereGeometry(0.22, 12, 10), k % 2 ? white : pink, 0.015); d.scale.y = 0.75; d.position.set(Math.cos(a) * r, 0.13, Math.sin(a) * r); g.add(d);
        if (k % 5 === 2) { const b = mesh(new THREE.ConeGeometry(0.15, 0.32, 10), berry, 0.012); b.rotation.x = Math.PI; b.position.set(Math.cos(a) * r, 0.42, Math.sin(a) * r); g.add(b); const lf = mesh(new THREE.ConeGeometry(0.1, 0.08, 6), leaf, 0.006); lf.position.y = 0.16; b.add(lf); }
      }
      const flames = [];
      for (let k = 0; k < 8; k++) {
        const a = (k + 0.5) / 8 * TAU, r = RD - 0.28;
        const cd = mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.7, 10), toon([0x5ac8ff, 0xff5a7a, 0xffd23a, 0x7ae07a][k % 4], { shade: 0x445566 }), 0.01); cd.position.set(Math.cos(a) * r, 0.5, Math.sin(a) * r); g.add(cd);
        const fl = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.22, 8), new THREE.MeshBasicMaterial({ color: 0xffb030 })); fl.position.set(Math.cos(a) * r, 0.98, Math.sin(a) * r); g.add(fl); flames.push(fl);
      }
      // the party: a gingham tablecloth with confetti, a cake stand, plates, cups, hats and balloons
      ground(g, -H - 0.3, (c, w) => { for (let y = 0; y < w; y += 32) for (let x = 0; x < w; x += 32) { c.fillStyle = ((x + y) / 32) % 2 ? '#ffffff' : '#f7b8cc'; c.fillRect(x, y, 32, 32); } const cols = ['#ff5a7a', '#5ac8ff', '#ffd23a', '#7ae07a']; for (let k = 0; k < 90; k++) { c.fillStyle = cols[k % 4]; c.fillRect(Math.random() * w, Math.random() * w, 6, 6); } }, 90, 6);
      cy(g, RD + 0.6, RD - 0.4, 0.3, 0xf2f2f6, 0, -H - 0.3, 0, { shade: 0xa8a8b8 }, 64);
      for (const [x, z] of [[-11, 9], [11, 9.5], [12, -8], [-12, -9]]) { cy(g, 2.2, 1.8, 0.15, 0xffffff, x, -H - 0.3, z, { shade: 0xb8b8c8 }, 32); }
      for (const [x, z, col] of [[-8, 12.5, 0x5ac8ff], [7, 13, 0xffd23a], [14, 3, 0xff5a7a]]) cy(g, 0.9, 0.7, 2.2, col, x, -H - 0.3, z, { shade: 0x445566 });
      for (const [x, z, col] of [[-14, 2, 0xb07aff], [9, -12, 0x7ae07a]]) { const h = mesh(new THREE.ConeGeometry(1, 2.6, 16), toon(col, { shade: 0x3a2a5a }), 0.02); h.position.set(x, -H - 0.3 + 1.3, z); g.add(h); }
      const balloons = [];
      for (let k = 0; k < 6; k++) { const b = sp(g, 1.1, [0xff5a7a, 0x5ac8ff, 0xffd23a, 0x7ae07a, 0xb07aff, 0xff9a4a][k], -12 + k * 4.8, 3, -14 - (k % 2) * 2, { shade: 0x3a2a3a, spec: 0.6 }); b.scale.y = 1.2; balloons.push(b); }
      return (T) => { flames.forEach((f, i) => { f.scale.set(1, 0.85 + 0.25 * Math.abs(Math.sin(T * 11 + i)), 1); }); balloons.forEach((b, i) => { b.position.y = 3 + Math.sin(T * 0.9 + i) * 0.4; }); };
    },

    // ---------------------------------------------------------------- DJ vinyl in the booth (it turns, and carries you)
    vinyl(Rn, g, spin) {
      const disc = top(spin, (c) => {
        c.fillStyle = '#121214'; c.fillRect(0, 0, W, W);
        for (let r = 140; r < C; r += 6) circ(c, r, null, r % 18 === 2 ? '#2a2a30' : '#1c1c21', 2);
        c.fillStyle = 'rgba(255,255,255,0.06)'; for (const a of [0.6, 0.6 + Math.PI]) { c.beginPath(); c.moveTo(C, C); c.arc(C, C, C, a - 0.25, a + 0.25); c.fill(); }
        circ(c, RR, null, '#8a8a92', 5);
        circ(c, 125, '#d23a2a', ink, 5);
        c.fillStyle = '#fff'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.font = 'bold 44px sans-serif'; c.fillText('KUMITE', C, C - 50); c.font = 'bold 22px sans-serif'; c.fillText('33 1/3 RPM', C, C + 60);
        circ(c, 14, '#d8d8de', ink, 3);
      });
      side(g, null, { color: 0x141418, shade: 0x050506, h: 0.16 });
      edgeLine(g);
      const silver = toon(0xc8ccd2, { shade: 0x5a606a, spec: 0.8 }), black = toon(0x1c1c22, { shade: 0x08080a });
      const platter = mesh(new THREE.CylinderGeometry(RD + 0.3, RD + 0.3, 0.4, 96), silver, 0.03); platter.position.y = -0.36; g.add(platter);
      // the deck, the tonearm, a mixer with knobs and faders, the other deck, speakers, lasers
      bx(g, 15, 0.8, 15, 0x26262c, 1, -1.36, 0, { shade: 0x0a0a0e }); bx(g, 15.2, 0.12, 15.2, 0xb8bcc4, 1, -0.6, 0, { shade: 0x4a4e56 });
      const arm = new THREE.Group(); arm.position.set(RD + 1.6, -0.55, -RD * 0.5); arm.rotation.y = -0.55; g.add(arm);
      const base = mesh(new THREE.CylinderGeometry(0.45, 0.55, 0.8, 20), silver, 0.02); base.position.y = 0.4; arm.add(base);
      const tube = mesh(new THREE.CylinderGeometry(0.07, 0.07, 5.2, 10), silver, 0.012); tube.rotation.z = Math.PI / 2; tube.position.set(-2.4, 0.95, 0); arm.add(tube);
      const head = mesh(BOX(), black, 0.012); head.scale.set(0.5, 0.12, 0.3); head.position.set(-5, 0.9, 0); arm.add(head);
      const mixer = new THREE.Group(); mixer.position.set(11.5, -1.4, 0); g.add(mixer);
      bx(mixer, 5, 1.2, 8, 0x2a2a30, 0, 0, 0, { shade: 0x0a0a0e });
      for (let k = 0; k < 12; k++) cy(mixer, 0.25, 0.25, 0.3, [0xd23a2a, 0x3ad8ff, 0xffd23a][k % 3], -1.4 + (k % 4) * 0.95, 1.2, -3 + Math.floor(k / 4) * 1.2, { shade: 0x222222 }, 12);
      for (let k = 0; k < 3; k++) bx(mixer, 0.3, 0.2, 2.2, 0xd8d8de, -1.2 + k * 1.2, 1.2, 1.6, { shade: 0x777777 });
      cy(g, RD + 0.3, RD + 0.3, 0.3, 0xc8ccd2, -15, -1.3, 0, { shade: 0x5a606a }, 64); cy(g, RD, RD, 0.05, 0x121214, -15, -1.0, 0, { shade: 0x050506 }, 64);
      for (const x of [-16, 18]) { const spk = bx(g, 5, 9, 5, 0x18181c, x, -6, -13, { shade: 0x060608 }); for (const y of [2.2, -2.2]) { const cone = new THREE.Mesh(new THREE.CircleGeometry(1.6, 24), new THREE.MeshBasicMaterial({ color: 0x3a3a44 })); cone.position.set(x, -6 + 4.5 + y, -10.4); g.add(cone); } }
      ground(g, -6, (c, w) => { const gr = c.createRadialGradient(w / 2, w / 2, 10, w / 2, w / 2, w / 2); gr.addColorStop(0, '#2a2030'); gr.addColorStop(1, '#0a080e'); c.fillStyle = gr; c.fillRect(0, 0, w, w); }, 120, 1);
      const lasers = [];
      for (let k = 0; k < 6; k++) { const L = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 40, 6), new THREE.MeshBasicMaterial({ color: [0x3ad8ff, 0xff3ad8, 0x6aff6a][k % 3], transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending, depthWrite: false })); L.position.set(-14 + k * 5.6, 6, -18); g.add(L); lasers.push(L); }
      return (T, dt, m) => {
        disc.rotation.y = -((m && m.stageA) || 0);
        lasers.forEach((L, i) => { L.rotation.z = Math.sin(T * 1.2 + i) * 0.9; L.rotation.x = 0.9 + Math.sin(T * 0.8 + i * 2) * 0.3; L.material.opacity = 0.35 + 0.3 * Math.abs(Math.sin(T * 3 + i)); });
      };
    },

    // ---------------------------------------------------------------- helipad on a rooftop
    heli(Rn, g, spin) {
      // a plain helipad: grey concrete, a yellow touchdown circle (the ring edge) and a big white H
      top(spin, (c) => {
        c.fillStyle = '#5a5e64'; c.fillRect(0, 0, W, W);
        for (let k = 0; k < 1500; k++) { c.fillStyle = Math.random() < 0.5 ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.08)'; c.fillRect(Math.random() * W, Math.random() * W, 3, 3); }
        circ(c, C - 10, null, '#e8e8e8', 8);
        circ(c, RR, null, '#f2c230', 22);
        c.fillStyle = '#f2f2f2'; const hw = 230, hh = 330, bar = 62;
        c.fillRect(C - hw / 2, C - hh / 2, bar, hh); c.fillRect(C + hw / 2 - bar, C - hh / 2, bar, hh); c.fillRect(C - hw / 2, C - bar / 2, hw, bar);
      });
      side(g, null, { color: 0x8b8f96, shade: 0x3a3c40, h: 0.25 });
      edgeLine(g);
      const lights = [];
      for (let k = 0; k < 16; k++) { const a = k / 16 * TAU, l = new THREE.Mesh(new THREE.SphereGeometry(0.1, 10, 8), new THREE.MeshBasicMaterial({ color: k % 2 ? 0x6aff8a : 0xffffff })); l.position.set(Math.cos(a) * (RD - 0.12), 0.06, Math.sin(a) * (RD - 0.12)); g.add(l); lights.push(l); }
      // the roof: gravel, a low wall, air-con units, a water tank, an antenna, and the city below
      ground(g, -0.25, (c, w) => { c.fillStyle = '#8a8c90'; c.fillRect(0, 0, w, w); for (let k = 0; k < 6000; k++) { const v = 100 + Math.random() * 70 | 0; c.fillStyle = `rgb(${v},${v},${v + 4})`; c.fillRect(Math.random() * w, Math.random() * w, 3, 3); } }, 30, 3);
      for (const [sx, sz, x, z] of [[31, 1, 0, -15], [31, 1, 0, 15], [1, 31, -15, 0], [1, 31, 15, 0]]) bx(g, sx, 1.2, sz, 0xb8b8bc, x, -0.25, z, { shade: 0x5a5a60 });
      for (const [x, z] of [[-11, -11], [11, -11], [-11, 11]]) { bx(g, 3.5, 1.8, 3.5, 0xd8dade, x, -0.25, z, { shade: 0x7a7c82 }); const fan = new THREE.Mesh(new THREE.CircleGeometry(1.3, 20).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x2a2c30 })); fan.position.set(x, 1.57, z); g.add(fan); }
      cy(g, 2.4, 2.4, 4, 0x9a6a3a, 11.5, -0.25, 11, { shade: 0x4a2a12 }); const roof = mesh(new THREE.ConeGeometry(2.6, 1.2, 24), toon(0x6a4a2a, { shade: 0x2a1a0a }), 0.02); roof.position.set(11.5, 4.35, 11); g.add(roof);
      cy(g, 0.1, 0.15, 7, 0xd8d8de, -12.5, -0.25, 0, { shade: 0x6a6a70 }, 8); const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.25, 10, 8), new THREE.MeshBasicMaterial({ color: 0xff2a1a })); beacon.position.set(-12.5, 6.85, 0); g.add(beacon);
      const win = ctex(64, 128, (c, w, h) => { c.fillStyle = '#1a2a44'; c.fillRect(0, 0, w, h); for (let y = 6; y < h; y += 14) for (let x = 6; x < w; x += 14) { c.fillStyle = Math.random() < 0.45 ? '#ffd88a' : '#0e1830'; c.fillRect(x, y, 8, 9); } });
      win.wrapS = win.wrapT = THREE.RepeatWrapping; win.repeat.set(2, 6);
      const city = new THREE.MeshBasicMaterial({ map: win });
      for (let k = 0; k < 26; k++) { const a = k / 26 * TAU, d = 24 + (k % 3) * 5, h = 6 + (k * 7 % 9); const b = new THREE.Mesh(new THREE.BoxGeometry(5, 40, 5), city); b.position.set(Math.cos(a) * d, -40 + h - 20 + 20, Math.sin(a) * d); g.add(b); }
      ground(g, -45, (c, w) => { c.fillStyle = '#0a1020'; c.fillRect(0, 0, w, w); }, 300, 1);
      return (T) => { lights.forEach((l, i) => { l.visible = Math.floor(T * 2.5 + i) % 3 !== 0; }); beacon.visible = Math.floor(T * 1.5) % 2 === 0; };
    },

    // ---------------------------------------------------------------- pizza on a restaurant table
    pizza(Rn, g, spin) {
      const H = 0.18;
      top(spin, (c) => {
        const gr = c.createRadialGradient(C, C, RR - 10, C, C, C); gr.addColorStop(0, '#e8b664'); gr.addColorStop(1, '#b8782e'); c.fillStyle = gr; c.fillRect(0, 0, W, W);
        for (let k = 0; k < 90; k++) { const a = Math.random() * TAU, r = RR + 14 + Math.random() * (C - RR - 24); c.beginPath(); c.ellipse(C + Math.cos(a) * r, C + Math.sin(a) * r, 9, 6, a, 0, TAU); c.fillStyle = 'rgba(120,60,20,0.45)'; c.fill(); }
        circ(c, RR, '#c8381e', '#8a2412', 8);
        for (let k = 0; k < 70; k++) { const a = Math.random() * TAU, r = Math.sqrt(Math.random()) * (RR - 40); c.beginPath(); const x = C + Math.cos(a) * r, y = C + Math.sin(a) * r; for (let j = 0; j <= 8; j++) { const b = j / 8 * TAU, rr = 34 + Math.random() * 26; c.lineTo(x + Math.cos(b) * rr, y + Math.sin(b) * rr); } c.fillStyle = '#f6d46a'; c.fill(); }
        for (let k = 0; k < 11; k++) { const a = k / 11 * TAU + 0.3, r = k % 2 ? RR * 0.62 : RR * 0.3; const x = C + Math.cos(a) * r, y = C + Math.sin(a) * r; c.beginPath(); c.arc(x, y, 44, 0, TAU); c.fillStyle = '#b02e1c'; c.fill(); c.lineWidth = 5; c.strokeStyle = '#6a160c'; c.stroke(); for (let d = 0; d < 6; d++) { c.beginPath(); c.arc(x + (Math.random() - 0.5) * 50, y + (Math.random() - 0.5) * 50, 5, 0, TAU); c.fillStyle = '#7a1a10'; c.fill(); } }
        for (let k = 0; k < 7; k++) { const a = Math.random() * TAU, r = Math.random() * RR * 0.8; c.beginPath(); c.ellipse(C + Math.cos(a) * r, C + Math.sin(a) * r, 26, 12, a, 0, TAU); c.fillStyle = '#3a9a3a'; c.fill(); c.lineWidth = 3; c.strokeStyle = '#1e5a1e'; c.stroke(); }
        c.strokeStyle = 'rgba(90,30,10,0.55)'; c.lineWidth = 5; for (let k = 0; k < 8; k++) { const a = k / 8 * TAU; c.beginPath(); c.moveTo(C, C); c.lineTo(C + Math.cos(a) * RR, C + Math.sin(a) * RR); c.stroke(); }
      });
      side(g, (c, w, h) => { c.fillStyle = '#c8893e'; c.fillRect(0, 0, w, h); }, { rep: 2, h: H });
      edgeLine(g);
      // a pizza pan on a red-and-white checked tablecloth, with plates, glasses, cutlery and a candle
      cy(g, RD + 0.5, RD + 0.4, 0.12, 0x9aa0a8, 0, -H - 0.12, 0, { shade: 0x4a4e56, spec: 0.8 }, 64);
      ground(g, -H - 0.12, (c, w) => { for (let y = 0; y < w; y += 64) for (let x = 0; x < w; x += 64) { c.fillStyle = ((x + y) / 64) % 2 ? '#ffffff' : '#d42a2a'; c.fillRect(x, y, 64, 64); } c.fillStyle = 'rgba(255,255,255,0.35)'; for (let x = 0; x < w; x += 64) { c.fillRect(x + 28, 0, 8, w); c.fillRect(0, x + 28, w, 8); } }, 80, 8);
      const gy = -H - 0.12;
      for (const [x, z] of [[-11, 8], [11, 9]]) { cy(g, 3, 2.6, 0.15, 0xffffff, x, gy, z, { shade: 0xb8b8c8 }, 32); bx(g, 0.25, 0.06, 4.2, 0xd8d8de, x + 3.6, gy, z, { shade: 0x7a7a80 }); bx(g, 0.25, 0.06, 4.2, 0xd8d8de, x - 3.6, gy, z, { shade: 0x7a7a80 }); }
      for (const [x, z] of [[-8, -10], [9, -11]]) { cy(g, 0.25, 0.6, 0.15, 0xeef6fa, x, gy, z, { shade: 0x8aa8b8 }); cy(g, 0.12, 0.12, 2.2, 0xeef6fa, x, gy + 0.15, z, { shade: 0x8aa8b8 }); const bowl = mesh(new THREE.CylinderGeometry(1.1, 0.5, 1.8, 20, 1, true), toon(0xe8f4fa, { shade: 0x8aa8b8 }), 0.015); bowl.position.set(x, gy + 3.25, z); g.add(bowl); const wine = new THREE.Mesh(new THREE.CircleGeometry(0.85, 20).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x7a0e1a })); wine.position.set(x, gy + 2.95, z); g.add(wine); }
      cy(g, 0.9, 0.9, 2.6, 0x2a6a3a, 13, gy, -2, { shade: 0x0e2a14 }); cy(g, 0.25, 0.25, 1.2, 0xfff6e0, 13, gy + 2.6, -2); const flame = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.5, 8), new THREE.MeshBasicMaterial({ color: 0xffb030 })); flame.position.set(13, gy + 4.1, -2); g.add(flame);
      cy(g, 0.9, 0.9, 2.2, 0xeef2f4, -13, gy, -3, { shade: 0x8a9aa8 }); cy(g, 0.95, 0.95, 0.6, 0xc8ccd2, -13, gy + 2.2, -3, { shade: 0x5a606a });
      return (T) => { flame.scale.y = 0.85 + 0.3 * Math.abs(Math.sin(T * 10)); };
    },

    // ---------------------------------------------------------------- watch face on a desk
    watch(Rn, g, spin) {
      // a plain wall clock on a white wall
      const H = 0.6;
      top(spin, (c) => {
        c.fillStyle = '#fbfbf8'; c.fillRect(0, 0, W, W);
        circ(c, RR, null, '#2a2a2a', 5);
        for (let k = 0; k < 60; k++) { const a = k / 60 * TAU; c.beginPath(); c.moveTo(C + Math.cos(a) * (RR - 12), C + Math.sin(a) * (RR - 12)); c.lineTo(C + Math.cos(a) * (RR - (k % 5 ? 30 : 0)), C + Math.sin(a) * (RR - (k % 5 ? 30 : 0))); c.lineWidth = k % 5 ? 3 : 8; c.strokeStyle = '#1a1a1a'; c.stroke(); }
        c.fillStyle = '#1a1a1a'; c.font = 'bold 96px sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
        for (let k = 1; k <= 12; k++) { const a = k / 12 * TAU - Math.PI / 2; c.fillText(String(k), C + Math.cos(a) * (RR - 95), C + Math.sin(a) * (RR - 95)); }
      });
      side(g, null, { color: 0x1a1a1a, shade: 0x050505, h: H });
      const frame = mesh(new THREE.TorusGeometry(RD, 0.28, 12, 96), toon(0x1a1a1a, { shade: 0x050505, spec: 0.4 }), 0.02); frame.rotation.x = Math.PI / 2; frame.position.y = 0.06; g.add(frame);
      const hand = (len, w, col) => { const p = new THREE.Group(); p.position.y = 0.03; const m = new THREE.Mesh(new THREE.BoxGeometry(w, 0.02, len), new THREE.MeshBasicMaterial({ color: col })); m.position.z = -len / 2 + 0.2; p.add(m); spin.add(p); return p; };
      const hH = hand(2.3, 0.26, 0x1a1a1a), hM = hand(3.6, 0.18, 0x1a1a1a), hS = hand(4.1, 0.06, 0xd42a2a);
      const pin = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.06, 16), new THREE.MeshBasicMaterial({ color: 0xd42a2a })); pin.position.y = 0.05; spin.add(pin);
      ground(g, -H, (c, w) => { c.fillStyle = '#f4f4f2'; c.fillRect(0, 0, w, w); }, 120, 1);
      return () => {
        const d = new Date(), s = d.getSeconds() + d.getMilliseconds() / 1000, mi = d.getMinutes() + s / 60, h = (d.getHours() % 12) + mi / 60;
        hS.rotation.y = -s / 60 * TAU; hM.rotation.y = -mi / 60 * TAU; hH.rotation.y = -h / 12 * TAU;
      };
    },

    // ---------------------------------------------------------------- flat earth, floating in space (water splashes)
    earth(Rn, g, spin) {
      const H = 1.6;
      // continents, roughly, as seen from above the north pole: radius grows with distance from the pole
      const LAND = [
        [[70, -160], [72, -120], [75, -85], [62, -62], [50, -56], [45, -66], [30, -81], [25, -80], [18, -96], [15, -88], [8, -78], [20, -105], [32, -117], [40, -124], [50, -128], [58, -136], [60, -147], [64, -166]],
        [[83, -35], [80, -20], [70, -22], [60, -43], [65, -53], [77, -70]],
        [[12, -72], [10, -62], [5, -52], [-5, -35], [-10, -37], [-23, -42], [-35, -56], [-42, -63], [-55, -68], [-52, -75], [-40, -74], [-18, -71], [-5, -81], [2, -79], [9, -78]],
        [[71, 25], [70, 40], [60, 30], [55, 20], [54, 10], [51, 2], [48, -5], [43, -9], [36, -6], [37, 0], [43, 6], [44, 13], [40, 18], [38, 24], [41, 29], [45, 30], [46, 40], [55, 40], [65, 40]],
        [[37, 10], [32, 32], [12, 43], [11, 51], [-1, 42], [-10, 40], [-26, 33], [-34, 26], [-34, 18], [-28, 15], [-17, 12], [-5, 12], [4, 8], [5, -5], [10, -15], [21, -17], [28, -13], [35, -6]],
        [[77, 105], [73, 140], [70, 180], [64, 178], [60, 163], [52, 158], [53, 141], [43, 135], [38, 128], [35, 129], [30, 122], [22, 113], [10, 106], [1, 104], [8, 98], [16, 95], [22, 90], [20, 73], [25, 66], [25, 57], [13, 44], [30, 48], [37, 36], [42, 42], [45, 52], [55, 60], [68, 68], [72, 80]],
        [[-11, 131], [-12, 142], [-25, 153], [-37, 150], [-38, 141], [-32, 133], [-35, 117], [-22, 114], [-14, 127]],
        [[58, -5], [55, -1], [51, 1], [50, -5], [54, -4]], [[45, 142], [40, 141], [35, 140], [33, 131], [35, 133], [41, 140]],
        [[-1, 110], [-4, 120], [-8, 115], [-6, 105]], [[-35, 173], [-41, 176], [-46, 168], [-40, 172]],
      ];
      const P = (lat, lon) => { const r = (90 - lat) / 150 * RR; return [C + Math.sin(lon * Math.PI / 180) * r, C + Math.cos(lon * Math.PI / 180) * r]; };
      const disc = top(spin, (c) => {
        const gr = c.createRadialGradient(C, C, 20, C, C, RR); gr.addColorStop(0, '#3a8ad8'); gr.addColorStop(1, '#1e5aa8'); c.fillStyle = gr; c.fillRect(0, 0, W, W);
        c.strokeStyle = 'rgba(255,255,255,0.12)'; c.lineWidth = 2; for (let lat = 60; lat > -60; lat -= 30) { c.beginPath(); c.arc(C, C, (90 - lat) / 150 * RR, 0, TAU); c.stroke(); }
        for (let lon = 0; lon < 360; lon += 30) { const [x, y] = P(-60, lon); c.beginPath(); c.moveTo(C, C); c.lineTo(x, y); c.stroke(); }
        for (const poly of LAND) { c.beginPath(); poly.forEach(([la, lo], i) => { const [x, y] = P(la, lo); if (i) c.lineTo(x, y); else c.moveTo(x, y); }); c.closePath(); c.fillStyle = '#5aa84a'; c.fill(); c.lineWidth = 4; c.strokeStyle = '#2e6a2a'; c.stroke(); }
        // the ice wall all round the edge
        c.beginPath(); for (let k = 0; k <= 120; k++) { const a = k / 120 * TAU, r = RR + Math.sin(k * 1.7) * 8 + (k % 3) * 4; c.lineTo(C + Math.cos(a) * r, C + Math.sin(a) * r); } c.arc(C, C, C, TAU, 0, true); c.fillStyle = '#f2f8fc'; c.fill('evenodd');
        circ(c, RR, null, '#bcd8ea', 5);
      });
      side(g, (c, w, h) => { c.fillStyle = '#7a5232'; c.fillRect(0, 0, w, h); c.fillStyle = '#5a3a20'; c.fillRect(0, h * 0.5, w, h * 0.5); c.fillStyle = '#e8f2f8'; c.fillRect(0, 0, w, h * 0.16); for (let k = 0; k < 90; k++) { c.fillStyle = 'rgba(30,18,8,0.4)'; c.beginPath(); c.arc(Math.random() * w, h * 0.3 + Math.random() * h * 0.7, 3 + Math.random() * 6, 0, TAU); c.fill(); } }, { rep: 3, h: H, th: 256, taper: 0.7 });
      edgeLine(g);
      const wall = mesh(new THREE.CylinderGeometry(RD, RD, 0.35, 96, 1, true), toon(0xf2f8fc, { shade: 0x9ab8cc }), 0.02); wall.position.y = 0.17; g.add(wall);
      // space: stars below
      ground(g, -14, (c, w) => { c.fillStyle = '#05060f'; c.fillRect(0, 0, w, w); for (let k = 0; k < 900; k++) { c.fillStyle = `rgba(255,255,255,${0.3 + Math.random() * 0.7})`; const s = Math.random() < 0.08 ? 3 : 1.5; c.fillRect(Math.random() * w, Math.random() * w, s, s); } }, 200, 2, 1024);
      // water splashes: read the painted map to see whether a foot is in the sea
      const canvas = disc.material.map.image, data = canvas.getContext('2d').getImageData(0, 0, W, W).data;
      const drops = [], v = new THREE.Vector3(), cool = [0, 0];
      const dropMat = new THREE.MeshBasicMaterial({ color: 0xbfe6ff });
      for (let k = 0; k < 60; k++) { const d = new THREE.Mesh(new THREE.SphereGeometry(0.07, 6, 5), dropMat); d.visible = false; g.add(d); drops.push({ m: d, vx: 0, vy: 0, vz: 0, life: 0 }); }
      let di = 0;
      const isWater = (x, z) => {
        v.set(x, 0, z); disc.worldToLocal(v);
        const px = Math.floor((0.5 + v.x / (2 * RD)) * W), py = Math.floor((0.5 + v.z / (2 * RD)) * W);
        if (px < 0 || py < 0 || px >= W || py >= W) return false;
        const i = (py * W + px) * 4; return data[i + 2] > 150 && data[i] < 120; // blue sea, not green land or white ice
      };
      return (T, dt, m) => {
        if (m) m.w.forEach((w, i) => {
          cool[i] -= dt;
          const spd = Math.hypot(w.vx, w.vz);
          if (cool[i] <= 0 && spd > 0.8 && w.y < 0.1 && isWater(w.x, w.z)) {
            cool[i] = 0.12;
            for (let k = 0; k < 4; k++) { const d = drops[di++ % drops.length]; const a = Math.random() * TAU; d.m.position.set(w.x + Math.cos(a) * 0.4, 0.1, w.z + Math.sin(a) * 0.4); d.vx = Math.cos(a) * 1.5 + w.vx * 0.2; d.vz = Math.sin(a) * 1.5 + w.vz * 0.2; d.vy = 2.5 + Math.random() * 1.5; d.life = 0.6; d.m.visible = true; }
            if (S.game && S.game.audio && Math.random() < 0.5) S.game.audio.scuff();
          }
        });
        for (const d of drops) { if (d.life <= 0) continue; d.life -= dt; d.vy -= 9 * dt; d.m.position.x += d.vx * dt; d.m.position.y += d.vy * dt; d.m.position.z += d.vz * dt; if (d.life <= 0 || d.m.position.y < 0) { d.m.visible = false; d.life = 0; } }
      };
    },
    // ---------------------------------------------------------------- lily pad floating on a pond
    lily(Rn, g, spin) {
      const H = 0.16;
      top(spin, (c) => {
        c.fillStyle = '#3f8f3a'; c.fillRect(0, 0, W, W);
        const gr = c.createRadialGradient(C, C, 30, C, C, C); gr.addColorStop(0, '#86cf5a'); gr.addColorStop(1, '#4fa23e'); circ(c, C, gr);
        c.strokeStyle = 'rgba(40,100,40,0.45)'; c.lineWidth = 5;
        for (let k = 0; k < 22; k++) { const a = k / 22 * TAU; c.beginPath(); c.moveTo(C, C); c.quadraticCurveTo(C + Math.cos(a + 0.12) * C * 0.5, C + Math.sin(a + 0.12) * C * 0.5, C + Math.cos(a) * C, C + Math.sin(a) * C); c.stroke(); }
        // the notch every lily pad has, cut in from the edge (outside the fighting circle)
        c.beginPath(); c.moveTo(C + RR * 0.98, C); c.lineTo(C + C, C - 70); c.lineTo(C + C, C + 70); c.closePath(); c.fillStyle = '#5ac6bc'; c.fill();
        circ(c, RR, null, 'rgba(240,255,220,0.8)', 8);
      });
      side(g, null, { color: 0x3a7a30, shade: 0x1a3a14, h: H }); edgeLine(g);
      // the pond: water, more pads, a lotus flower and reeds
      // clear pond water: turquoise shallows round the pad, deeper teal further out, caustics and sun glints
      const pond = S.Water.animate(new THREE.Mesh(new THREE.PlaneGeometry(140, 140).rotateX(-Math.PI / 2), S.Water.pond({ shoreR: RD + 0.5 })));
      pond.position.y = -H + 0.02; g.add(pond);
      const pads = [];
      for (const [x, z, r] of [[-12, -7, 3.2], [13, -9, 4.2], [-14, 8, 2.6], [11, 10, 3.4], [-4, -14, 2.2], [17, 2, 2.4], [-18, -1, 3.6]]) {
        const pd = cy(g, r, r, 0.12, 0x5aae44, x, -H - 0.04, z, { shade: 0x2a5a20 }, 32); pd.userData.ph = x * 0.7; pads.push(pd);
      }
      const pink = toon(0xf6a8c8, { shade: 0xc0507a }), white = toon(0xfff2f6, { shade: 0xd8a0b4 });
      const lotus = new THREE.Group(); lotus.position.set(13, -H + 0.1, -9); g.add(lotus);
      for (let ring2 = 0; ring2 < 2; ring2++) for (let k = 0; k < 7; k++) {
        const pt = mesh(new THREE.SphereGeometry(0.9, 12, 10), ring2 ? white : pink, 0.015); pt.scale.set(0.45, 1.3, 0.25);
        const a = k / 7 * TAU + ring2 * 0.4, rr = ring2 ? 0.45 : 0.9; pt.position.set(Math.cos(a) * rr, 1.0, Math.sin(a) * rr); pt.lookAt(Math.cos(a) * 4, 4, Math.sin(a) * 4); lotus.add(pt);
      }
      sp(lotus, 0.45, 0xf2d040, 0, 1.0, 0, { shade: 0xb08a10 });
      for (const [x, z] of [[-17, -12], [-16, -13.5], [-18.5, -12.8], [18, 12], [19.5, 11], [17, 13.5]]) {
        cy(g, 0.08, 0.1, 7, 0x4a8a2a, x, -H, z, { shade: 0x22441a }, 8);
        cy(g, 0.32, 0.32, 1.6, 0x6a3a1a, x, -H + 5.6, z, { shade: 0x2a160a }, 10);
      }
      // ripples spreading from the pad
      const ripples = [];
      for (let k = 0; k < 4; k++) { const rm = new THREE.Mesh(new THREE.RingGeometry(0.96, 1, 96).rotateX(-Math.PI / 2), glowMat(0xd8f0ff, 0)); rm.position.y = -H + 0.04; g.add(rm); ripples.push(rm); }
      return (T) => {
        ripples.forEach((rm, k) => { const f = ((T * 0.25 + k / 4) % 1); rm.scale.setScalar(RD + 0.3 + f * 6); rm.material.opacity = 0.3 * (1 - f); });
        for (const pd of pads) pd.position.y = -H - 0.04 + 0.06 * Math.sin(T * 1.3 + pd.userData.ph);
        lotus.rotation.y = Math.sin(T * 0.4) * 0.15;
      };
    },

    // ---------------------------------------------------------------- sushi plate on a conveyor belt
    // A giant glazed plate on a kaiten-zushi belt. The food, plates and table things are modelled in Blender
    // (tools/blender/sushi.py -> assets/models/sushi_set.glb) and dropped in when the file arrives.
    sushi(Rn, g, spin) {
      const H = 0.32;
      top(spin, (c) => {
        // glazed porcelain: warm white, a touch brighter in the middle where the glaze pools
        const gr = c.createRadialGradient(C, C, 10, C, C, C); gr.addColorStop(0, '#fffdf8'); gr.addColorStop(0.7, '#f6f1e6'); gr.addColorStop(1, '#ebe4d4');
        c.fillStyle = gr; c.fillRect(0, 0, W, W);
        // the rim: indigo glaze with seigaiha (overlapping wave scales), a gold line on the inside
        const r0 = RR + 22;
        ring(c, r0, C, '#203c7a');
        c.save(); c.beginPath(); c.arc(C, C, C, 0, TAU); c.arc(C, C, r0, 0, TAU, true); c.clip('evenodd');
        c.strokeStyle = 'rgba(190,210,240,0.55)'; c.lineWidth = 2.5;
        const sc = 26;
        for (let row = 0; row < 48; row++) for (let col = 0; col < 48; col++) {
          const x = col * sc * 2 + (row % 2) * sc, y = row * sc * 0.55;
          for (const k of [1, 0.7, 0.4]) { c.beginPath(); c.arc(x, y, sc * k, Math.PI, TAU); c.stroke(); }
        }
        c.restore();
        circ(c, r0, null, '#c9a24a', 4); circ(c, C - 4, null, '#162c5c', 6);
        // a big faint 寿 (celebration) glazed into the well, and the fighting circle
        c.fillStyle = 'rgba(32,60,122,0.07)'; c.font = 'bold 420px serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('寿', C, C + 10);
        circ(c, RR, null, '#203c7a', 8);
        // glaze highlight
        const hl = c.createRadialGradient(C - 190, C - 230, 5, C - 190, C - 230, 230); hl.addColorStop(0, 'rgba(255,255,255,0.55)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = hl; c.fillRect(0, 0, W, W);
      });
      side(g, (c, w, h) => { c.fillStyle = '#f2ede2'; c.fillRect(0, 0, w, h); c.fillStyle = '#203c7a'; c.fillRect(0, h * 0.12, w, h * 0.22); c.fillStyle = '#c9a24a'; c.fillRect(0, h * 0.36, w, 3); }, { shade: 0x9a98a0, h: H, th: 64, rep: 6 });
      edgeLine(g);
      const lip = mesh(new THREE.TorusGeometry(RD + 0.02, 0.07, 10, 128), toon(0xf4efe4, { shade: 0xa8a49a }), 0.02); lip.rotation.x = Math.PI / 2; lip.position.y = 0.03; g.add(lip);
      cy(g, RD * 0.72, RD * 0.66, 0.3, 0xe8e2d6, 0, -H - 0.3, 0, { shade: 0x8a8890 }, 64); // the plate's foot ring
      // the belt: brushed-steel slats with dark gaps, rails either side
      const BY = -H - 0.3, BW = 15, SL = 1.7;
      const slatM = toon(0xc9ced4, { shade: 0x6a727c, spec: 0.5 });
      const slats = new THREE.InstancedMesh(new THREE.BoxGeometry(SL - 0.07, 0.12, BW - 0.3), slatM, 120);
      const m4 = new THREE.Matrix4();
      for (let k = 0; k < 120; k++) { m4.makeTranslation(-102 + k * SL, BY - 0.06, 0); slats.setMatrixAt(k, m4); }
      g.add(slats);
      const under = ground(g, BY - 0.14, (c, w) => { c.fillStyle = '#2a2e34'; c.fillRect(0, 0, w, w); }, 1, 1); under.scale.set(210, 1, BW);
      for (const z of [-BW / 2 - 0.25, BW / 2 + 0.25]) { bx(g, 210, 0.9, 0.5, 0xb8bec6, 0, BY - 0.5, z, { shade: 0x4a5058, spec: 0.9 }); bx(g, 210, 0.12, 0.62, 0xe6eaee, 0, BY + 0.4, z, { shade: 0x8a9098, spec: 0.9 }); }
      // the counter: pale hinoki with long grain
      const counter = ground(g, BY - 1.6, (c, w) => {
        c.fillStyle = '#e2c79a'; c.fillRect(0, 0, w, w);
        for (let y = 0; y < w; y += 3) { const t = Math.sin(y * 0.05) * 0.5 + Math.sin(y * 0.013 + 1) * 0.5; c.fillStyle = 'rgba(150,96,44,' + (0.04 + 0.08 * Math.max(0, t)) + ')'; c.fillRect(0, y, w, 2); }
        c.strokeStyle = 'rgba(140,86,36,0.22)'; c.lineWidth = 2;
        for (let k = 0; k < 18; k++) { const y0 = Math.random() * w; c.beginPath(); for (let x = 0; x <= w; x += 16) c.lineTo(x, y0 + Math.sin(x * 0.01 + k) * 12 + Math.sin(x * 0.043) * 3); c.stroke(); }
        c.fillStyle = 'rgba(90,52,20,0.35)'; c.fillRect(0, w - 4, w, 4); // board joint
      }, 240, 10);
      // filled in from the Blender set: plates of sushi riding the belt, and tea, soy and ginger along the counter
      const ridePlates = [], props = [], SPAN = 120, SC = 44;
      [-20.5, -10.6, 10.6, 20.5].forEach((x) => { const pg = new THREE.Group(); pg.position.set(x, BY, 0); g.add(pg); ridePlates.push(pg); });
      S.sushiSet = S.sushiSet || new Promise((res) => new THREE.GLTFLoader().load('assets/models/sushi_set.glb', (gl) => res(gl.scene), undefined, () => res(null)));
      S.sushiSet.then((set) => {
        if (!set) return;
        const part = (name, s) => {
          const src = set.getObjectByName(name); if (!src) return null;
          const out = new THREE.Group();
          src.updateMatrixWorld(true);
          src.traverse((o) => {
            if (!o.isMesh) return;
            const sm = o.material, col = sm.color ? sm.color.clone().convertLinearToSRGB() : new THREE.Color(1, 1, 1);
            const m = mesh(o.geometry, toon(col.getHex(), { shade: col.clone().multiply(new THREE.Color(0.72, 0.66, 0.74)).getHex(), map: sm.map || undefined, rimAmt: 0.25, spec: sm.roughness < 0.35 ? 0.6 : 0 }), 0.012);
            // bake the node's transform relative to the asset root
            const rel = new THREE.Matrix4().copy(src.matrixWorld).invert().multiply(o.matrixWorld); m.applyMatrix4(rel); out.add(m);
          });
          out.scale.setScalar(s || SC); return out;
        };
        const menu = [['plate_red', ['nigiri_salmon', 'nigiri_salmon']], ['plate_yellow', ['maki_tuna', 'maki_cucumber', 'maki_tuna']], ['plate_blue', ['nigiri_tuna', 'nigiri_ebi']], ['plate_green', ['gunkan_ikura', 'nigiri_tamago']]];
        ridePlates.forEach((pg, k) => {
          const [pl, food] = menu[k], plate = part(pl); if (plate) pg.add(plate);
          food.forEach((f, i) => { const it = part(f); if (!it) return; const n = food.length, a = (i / n) * TAU + 0.6;
            it.position.set(Math.cos(a) * (n > 2 ? 0.95 : 0.7), 0.42, Math.sin(a) * (n > 2 ? 0.95 : 0.7) * 1.2); it.rotation.y = n > 2 ? a : Math.PI / 2 + 0.25 * (i ? 1 : -1); pg.add(it); });
        });
        const table = ['teacup', 'soy_dish', 'gari', 'chopsticks', 'wasabi', 'teacup', 'soy_dish', 'chopsticks', 'gari', 'teacup', 'soy_dish', 'wasabi'];
        table.forEach((name, k) => {
          const it = part(name); if (!it) return;
          const pr = new THREE.Group(); pr.add(it); it.rotation.y = k * 1.3;
          pr.position.set(-60 + k * 10, BY - 1.6, (k % 2 ? 1 : -1) * (12.5 + (k % 3) * 1.2)); pr.userData.x0 = -60 + k * 10; g.add(pr); props.push(pr);
        });
      });
      // in motion: the belt (and every plate on it, ours included) travels together, so they stay put on screen
      // and the counter beside it slides past. The fighting circle never moves.
      const V = 2.2; // world units per second
      return (T) => {
        const d = V * T;
        counter.material.map.offset.x = -(d / 24) % 1;
        for (const pr of props) { let x = (pr.userData.x0 + d) % SPAN; if (x > SPAN / 2) x -= SPAN; else if (x < -SPAN / 2) x += SPAN; pr.position.x = x; }
        ridePlates.forEach((pg, k) => { pg.position.y = BY + 0.025 * Math.sin(T * 17 + k * 1.7); }); // a little belt rumble
      };
    },
  };
})();
