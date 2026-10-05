'use strict';
// CAMPAIGN MAP: the Uogashi fish market (a made-up Tokyo wholesale market), built for a high-angle action camera.
// The route runs from +z (entrance) to -z (tuna auction):
//   entrance plaza (gacha machine) -> outdoor street (stalls, restaurants, alley) -> market hall (vendor rows)
//   -> loading bay -> tuna auction floor (boss).
// Everything here is static scenery plus data for campaign.js: wall boxes, prop spawns, puddles, combat zones.
(function () {
  const W = S.R3;

  // flat-shaded toon box with an ink outline
  function box(g, w, h, d, col, shade, x, y, z, ol, ry) {
    const m = W.mesh(W.GEO.box, S.toon(col, { shade, rimAmt: 0 }), ol === undefined ? 0.02 : ol); // no rim light: walls are matte, not glossy
    m.scale.set(w, h, d); m.position.set(x, y, z); if (ry) m.rotation.y = ry; g.add(m); return m;
  }
  function cyl(g, rt, rb, h, col, shade, x, y, z, seg, ol) {
    const m = W.mesh(new THREE.CylinderGeometry(rt, rb, h, seg || 16), S.toon(col, { shade, rimAmt: 0.1 }), ol === undefined ? 0.02 : ol);
    m.position.set(x, y, z); g.add(m); return m;
  }
  // a flat painted plane on the ground
  function floor(g, w, d, x, z, draw, y) {
    if (draw && draw.kind) { // tiled ground (4 m tiles, 1024 px) plus a transparent layer for paint, grates, numbers
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d).rotateX(-Math.PI / 2), S.CampArt.groundMat(draw.kind, w, d));
      m.position.set(x, y || 0, z); g.add(m);
      if (draw.lines) {
        const tex = W.canvasTex(1024, Math.max(64, Math.round(1024 * d / w)), draw.lines);
        const o = new THREE.Mesh(new THREE.PlaneGeometry(w, d).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
        o.position.set(x, (y || 0) + 0.004, z); o.renderOrder = 0; g.add(o);
      }
      return m;
    }
    const tex = W.canvasTex(512, Math.max(64, Math.round(512 * d / w)), draw);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: tex }));
    m.position.set(x, y || 0, z); g.add(m); return m;
  }
  // a sign: coloured board with big readable lettering (kanji + small english)
  function sign(g, text, sub, w, h, bg, fg, x, y, z, ry, tilt) {
    const tex = W.canvasTex(512, Math.round(512 * h / w), (c, cw, ch) => {
      c.fillStyle = bg; c.fillRect(0, 0, cw, ch);
      c.strokeStyle = 'rgba(0,0,0,0.55)'; c.lineWidth = 10; c.strokeRect(5, 5, cw - 10, ch - 10);
      c.fillStyle = fg; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.font = (sub ? ch * 0.5 : ch * 0.62) + 'px "Dela Gothic One", sans-serif';
      c.fillText(text, cw / 2, sub ? ch * 0.4 : ch * 0.52);
      if (sub) { c.font = '800 ' + ch * 0.2 + 'px "Barlow Condensed", sans-serif'; c.fillText(sub, cw / 2, ch * 0.8); }
    });
    const m = W.mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide }), 0);
    m.position.set(x, y, z); m.rotation.set(tilt || 0, ry || 0, 0); g.add(m); return m;
  }
  // concrete / asphalt with grain, drains and painted lines
  const GK = { '#6b5f63': 'plaza', '#58525c': 'asphalt', '#4a4450': 'asphalt', '#7e8c92': 'concrete', '#6e6a62': 'bay', '#8a8e90': 'auction' };
  const ground = (base, speck, lines) => ({ kind: GK[base] || 'concrete', lines });

  function build(scene) {
    const g = new THREE.Group(); scene.add(g);
    const walls = [], props = [], puddles = [], decor = [];
    const A = S.CampArt, fishes = A.fishBatch(g);
    const tbox = (m, w, h, d, x, y, z, ol) => { const o = W.mesh(W.GEO.box, m, ol === undefined ? 0.02 : ol); o.scale.set(w, h, d); o.position.set(x, y, z); g.add(o); return o; };
    const wall = (x0, x1, z0, z1) => { const w = { x0: Math.min(x0, x1), x1: Math.max(x0, x1), z0: Math.min(z0, z1), z1: Math.max(z0, z1) }; walls.push(w); return w; };
    const breakables = []; // stalls, tables and drink machines a charge (or a thrown body) smashes through
    const breakable = (b) => { b.w.brk = b; breakables.push(b); return b; };
    const prop = (type, x, z, ry) => props.push({ type, x, z, ry: ry || 0 });
    const puddle = (x, z, r, sx) => puddles.push({ x, z, r, sx: sx || 1 });

    // ================================================================ 1. ENTRANCE PLAZA  (z 4 .. -12)
    floor(g, 18, 16, 0, -4, ground('#6b5f63', ['#5a4f54', '#7c7076'], (c, w, h) => {
      c.fillStyle = '#e8c547'; for (let i = 0; i < 9; i++) c.fillRect(i * w / 9 + 10, h * 0.9, w / 18, 10); // painted kerb
    }));
    wall(-10, 10, 3.2, 5); // behind the start
    box(g, 20, 3, 1.2, 0x3a2c34, 0x1a1218, 0, 1.5, 4.2, 0.03);
    // the GACHA vending machine (left, glowing): guaranteed, right at the start
    const gacha = { x: -6.2, z: -3.2 };
    const gm = new THREE.Group(); gm.position.set(gacha.x, 0, gacha.z); g.add(gm);
    box(gm, 1.3, 2.1, 0.9, 0xe2322b, 0x7a1418, 0, 1.05, 0, 0.03);
    box(gm, 1.05, 1.1, 0.06, 0xfff4cc, 0xc8b070, 0.0, 1.35, 0.46, 0.0);
    for (let i = 0; i < 6; i++) { const b = W.mesh(W.GEO.sphere, S.toon([0xf2c14e, 0x3fc2b4, 0x4d8de6, 0xe8579c, 0x9be15d, 0xffffff][i], { shade: 0x6a5a6a, spec: 0.5 }), 0.01); b.scale.setScalar(0.13); b.position.set(-0.32 + (i % 3) * 0.32, 1.15 + Math.floor(i / 3) * 0.32, 0.5); gm.add(b); }
    box(gm, 0.5, 0.25, 0.1, 0x2a1a22, 0x100810, 0.3, 0.55, 0.47, 0.01);
    sign(gm, 'ガチャ', 'GACHA · 1 FREE', 1.25, 0.5, '#f2c14e', '#2a1218', 0, 2.35, 0.2, 0, -0.5);
    wall(gacha.x - 0.7, gacha.x + 0.7, gacha.z - 0.5, gacha.z + 0.5);
    // Japanese drink machines: body, lit display of bottles, coin slot and pickup tray. Breakable: dent, then over it goes.
    const vending = (x, z, ry, col) => {
      const vm = new THREE.Group(); vm.position.set(x, 0, z); vm.rotation.y = ry; g.add(vm);
      box(vm, 0.8, 1.85, 0.7, col, mul3(col, 0.5), 0, 0.925, 0, 0.025);
      const face = new THREE.Mesh(new THREE.PlaneGeometry(0.7, 1.05), new THREE.MeshBasicMaterial({ map: vendTex() }));
      face.position.set(0, 1.28, 0.352); vm.add(face);
      box(vm, 0.5, 0.16, 0.06, 0x1a1a22, 0x050508, 0, 0.32, 0.36, 0.01);
      box(vm, 0.12, 0.2, 0.04, 0xc8ccd0, 0x6a7078, 0.24, 0.72, 0.36, 0.006);
      const fx = Math.sin(ry), fz = Math.cos(ry); // the way its front faces
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color: 0xc8e8ff, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.4 })); glow.scale.set(1.6, 1.8, 1); glow.position.set(x + fx * 0.4, 1.3, z + fz * 0.4); g.add(glow);
      const hx = Math.abs(fx) > 0.5 ? 0.45 : 0.5, hz = Math.abs(fx) > 0.5 ? 0.5 : 0.45;
      breakable({ kind: 'vend', x, z, ry, group: vm, glow, hp: 2, w: wall(x - hx, x + hx, z - hz, z + hz) });
    };
    vending(6.4, -2.2, -Math.PI / 2, 0x2f7fd8); vending(6.4, -3.6, -Math.PI / 2, 0xf6f2ea);
    vending(6.6, -39.5, -Math.PI / 2, 0xe2322b); vending(-6.6, -34.2, Math.PI / 2, 0x2e9e6a); vending(11.65, -77.5, -Math.PI / 2, 0x2f7fd8);
    // entrance arch: two red posts and a big sign
    for (const x of [-6.6, 6.6]) { cyl(g, 0.22, 0.25, 4.2, 0xc8231d, 0x6e1018, x, 2.1, -9.5); wall(x - 0.3, x + 0.3, -9.8, -9.2); }
    box(g, 14, 0.35, 0.4, 0xc8231d, 0x6e1018, 0, 4.15, -9.5, 0.03);
    sign(g, '魚河岸 市場', 'UOGASHI FISH MARKET', 7.2, 1.5, '#f6eddc', '#1a0e14', 0, 3.3, -9.3, 0, -0.35);
    const lantern = () => {}; // no lanterns in the market
    for (const x of [-4.5, -1.5, 1.5, 4.5]) lantern(x, 3.55, -9.5);

    // ================================================================ 2. OUTDOOR STREET  (z -12 .. -48)
    floor(g, 18, 36, 0, -30, ground('#58525c', ['#4a454f', '#68616c'], (c, w, h) => {
      c.strokeStyle = 'rgba(30,26,34,0.5)'; c.lineWidth = 3; for (let i = 1; i < 9; i++) { c.beginPath(); c.moveTo(0, i * h / 9); c.lineTo(w, i * h / 9); c.stroke(); }
      for (let i = 0; i < 6; i++) { const gx = w * 0.475, gy = i * h / 6 + 20, gw = w * 0.05, gh = 26; c.fillStyle = '#6a6470'; c.fillRect(gx - 2, gy - 2, gw + 4, gh + 4); c.fillStyle = '#26222c'; c.fillRect(gx, gy, gw, gh); c.fillStyle = '#7a7480'; for (let b = 1; b < 6; b++) c.fillRect(gx, gy + b * gh / 6, gw, 2); } // gutter grates
    }));
    // building fronts along both sides (the street's walls)
    wall(-11, -7.2, -12, -48); wall(7.2, 11, -12, -48);
    for (const sd of [-1, 1]) { box(g, 1.2, 3.4, 36, 0x3e3038, 0x1c1418, sd * 7.8, 1.7, -30, 0.03); S.CampArt.facade(g, sd * 7.19, -12, -48, 3.4, sd, 'shop'); }
    // market stalls: counter, awning, display of fish on ice; restaurant fronts with noren curtains
    const awningCols = [[0xe2322b, 0xf6eddc], [0x2f6fd0, 0xf6eddc], [0xf2c14e, 0x3a2c34], [0x2e9e6a, 0xf6eddc]];
    const stall = (sd, z0, z1, k) => {
      const x = sd * 6.1, zc = (z0 + z1) / 2, len = Math.abs(z1 - z0);
      const rec = A.stall(g, fishes, x, z0, z1, sd, k); void len;
      const [c1, c2] = awningCols[k % awningCols.length];
      const aw = A.awning(rec.group, x + sd * 0.95, z0, z1, sd, c1, c2, { depth: 2.2, y: 2.95, drop: 0.6 });
      for (const zz of [z0, z1]) cyl(rec.group, 0.04, 0.04, aw.fy, 0x6a6e78, 0x22242c, aw.fx, aw.fy / 2, zz, 6, 0.01);
      breakable({ kind: 'stall', x, z: zc, len, sd, rec, w: wall(x - 0.9, x + 0.9, z0, z1) });
    };
    const restaurant = (sd, z0, z1, name, sub, col) => {
      const zc = (z0 + z1) / 2, len = Math.abs(z1 - z0), x = sd * 7.0;
      // noren curtain strips over the door
      for (let i = 0; i < 4; i++) box(g, 0.05, 0.9, len / 4.6, col, 0x2a1418, x - sd * 0.05, 2.0, z0 + (i + 0.5) * (z1 - z0) / 4, 0.01);
      sign(g, name, sub, 2.6, 0.95, '#1a0e14', '#f6eddc', x - sd * 1.0, 3.25, zc, 0, -0.55); // billboard facing the camera
      lantern(x - sd * 0.6, 2.4, z0 + 0.3 * Math.sign(z1 - z0), 0xe2322b); lantern(x - sd * 0.6, 2.4, z1 - 0.3 * Math.sign(z1 - z0), 0xe2322b);
    };
    // street A (z -12 .. -30): stalls left and right, a restaurant patio pocket on the right
    stall(-1, -13, -17.5, 0); stall(1, -13, -16.5, 1);
    stall(-1, -19.5, -22.5, 2);
    restaurant(1, -17.5, -24, 'すし大', 'SUSHI DAI', 0x1a3a7a);
    stall(-1, -26.5, -30, 3); stall(1, -25.5, -30, 0);
    // side alley pocket on the left (z -22.5 .. -26.5): bins and crates, good for a fight in the corner
    floor(g, 4, 4, -9, -24.5, ground('#4a4450', ['#3c3742', '#5a5460']));
    wall(-13, -11, -22.5, -26.5); box(g, 1.2, 3.2, 4.4, 0x3a2c34, 0x1a1218, -11.6, 1.6, -24.5, 0.03);
    wall(-11, -7.2, -12, -22.5); wall(-11, -7.2, -26.5, -48);  // (re-cut the left wall around the alley)
    walls.splice(walls.findIndex((w) => w.x0 === -11 && w.z0 === -48 && w.z1 === -12), 1);
    // patio: a table (solid) with chairs and bottles to throw
    cyl(g, 0.5, 0.5, 0.08, 0x8a5a3a, 0x4a2a1a, 3.3, 0.75, -21, 18); cyl(g, 0.07, 0.07, 0.72, 0x3a2a20, 0x1a1008, 3.3, 0.37, -21, 6);
    wall(2.9, 3.7, -21.4, -20.6);
    prop('chair', 2.4, -20.6); prop('chair', 4.1, -21.5); prop('chair', 3.0, -22.0);
    prop('bottle', 3.2, -20.9); prop('bottle', 3.45, -21.15);
    prop('crate', -4.3, -14.2); prop('crate', -4.4, -15.0); prop('foam', 4.3, -14.0); prop('foam', 4.4, -16.0);
    prop('bin', -9.5, -23.2); prop('bin', -9.8, -25.8); prop('crate', -10.0, -24.4); prop('crate', -8.6, -26.0); prop('bucket', -8.4, -23.0);
    prop('bottle', -4.3, -20.4); prop('bottle', -4.3, -21.2); prop('bottle', -4.4, -21.9);
    prop('crate', 4.4, -27.0); prop('foam', -4.4, -28.6);
    puddle(-0.8, -16.2, 1.4, 1.5); puddle(2.2, -26.5, 1.1, 1.2); puddle(-9.2, -24.8, 0.8);
    // street B (z -30 .. -48): restaurants and stacked crates make pockets; carts in the lane
    restaurant(-1, -31, -37, 'ラーメン', 'RAMEN', 0x7a1a14);
    stall(1, -31, -35, 2);
    restaurant(1, -36.5, -42.5, '天ぷら', 'TEMPURA', 0x2a5a3a);
    stall(-1, -38.5, -42, 1); stall(-1, -43.5, -47, 0); stall(1, -44, -47.5, 3);
    prop('crate2', -1.9, -35.2); prop('crate', -1.2, -35.4); prop('crate2', 2.6, -40.2); prop('crate', 3.2, -39.6);
    prop('cart', -3.4, -43.4); prop('foam', 4.3, -32.5); prop('foam', 4.3, -33.4); prop('bin', 4.3, -43.2);
    prop('chair', -4.6, -33.0); prop('chair', -4.4, -34.6); prop('bottle', -4.5, -36.0); prop('bottle', -4.6, -36.5);
    prop('bucket', 0.6, -45.5);
    // fish knives left lying about, and spare bottles near the throwers
    for (const [x, z] of [[-4.6, -18.8], [4.7, -29.0], [-4.9, -41.0], [4.6, -46.2], [-2.4, -60.5], [6.9, -69.0], [-6.8, -84.0], [2.4, -92.0], [-7.6, -104.5], [7.2, -108.0]]) prop('knife', x, z, Math.random() * 6);
    for (const [x, z] of [[-1.6, -44.0], [3.0, -44.6], [4.6, -47.0], [8.2, -70.4], [9.6, -73.6], [-2.2, -95.6], [-4.0, -98.0], [-1.0, -62.0]]) prop('bottle', x, z);
    puddle(1.0, -33.8, 1.2, 1.4); puddle(-2.4, -45.2, 1.3, 1.1);
    for (const z of [-15, -28, -38, -46]) { lantern(-6.9, 3.0, z, 0xf2c14e); lantern(6.9, 3.0, z, 0xf2c14e); }

    // ================================================================ hall facade (z -48 .. -50)
    wall(-14, -3.2, -48.2, -50); wall(3.2, 14, -48.2, -50);
    box(g, 10.8, 4.5, 1.8, 0x5a6a78, 0x2a3440, -8.6, 2.25, -49.1, 0.035); box(g, 10.8, 4.5, 1.8, 0x5a6a78, 0x2a3440, 8.6, 2.25, -49.1, 0.035);
    box(g, 28, 0.8, 1.8, 0x5a6a78, 0x2a3440, 0, 4.9, -49.1, 0.035);
    sign(g, '魚市場', 'MARKET HALL  ↑', 6.4, 1.4, '#e2322b', '#fff8ec', 0, 4.4, -48.15, 0, -0.25);
    for (let i = 0; i < 8; i++) box(g, 6.2, 0.1, 0.05, 0x9aa4b0, 0x4a5460, 0, 4.0 - i * 0.08, -49.9, 0.0); // rolled-up shutter

    // ================================================================ 3. MARKET HALL  (z -50 .. -100)
    floor(g, 26, 50, 0, -75, ground('#7e8c92', ['#6e7b82', '#8e9ca2'], (c, w, h) => {
      c.strokeStyle = 'rgba(40,60,70,0.35)'; c.lineWidth = 2;
      c.fillStyle = 'rgba(230,200,60,0.85)'; for (let i = 0; i < 50; i += 2) { c.fillRect(w * 0.05, i * h / 50, 6, h / 60); c.fillRect(w * 0.95, i * h / 50, 6, h / 60); }
    }));
    wall(-15, -12.2, -48, -100); wall(12.2, 15, -48, -100);
    for (const sd of [-1, 1]) { box(g, 1.4, 4.6, 52, 0x6a7884, 0x2e3a44, sd * 12.9, 2.3, -74, 0.035); S.CampArt.facade(g, sd * 12.19, -48, -100, 4.6, sd, 'hall', 5); }
    // vendor rows: three rows of tables, broken by cross-aisles so fights move between rows
    const tableRow = (x, z0, z1, k) => {
      const zc = (z0 + z1) / 2, len = Math.abs(z1 - z0);
      const rec = A.stall(g, fishes, x, z0, z1, 0, k, true);                                    // steel tables with displays
      breakable({ kind: 'table', x, z: zc, len, sd: 0, rec, w: wall(x - 0.8, x + 0.8, z1, z0) });
      // a hanging vendor sign over each segment
      const names = [['丸豊', 'MARUTOYO'], ['魚河岸', 'UOGASHI'], ['鮮魚', 'FRESH FISH'], ['海老', 'EBI · SHRIMP'], ['鮪', 'MAGURO'], ['貝', 'SHELLFISH']];
      const [n, sb] = names[k % names.length];
      sign(g, n, sb, 2.0, 0.75, ['#2f6fd0', '#e2322b', '#2e9e6a', '#f2c14e'][k % 4], '#fff8ec', x, 2.9, z0 - 0.4, 0, -0.55); // hangs over the row's end, facing the camera
    };
    let k = 0;
    for (const [z0, z1] of [[-53, -61.5], [-64.5, -76], [-79, -88.5], [-91.5, -97.5]]) {
      tableRow(-6, z0, z1, k++); tableRow(0.0, z0 - (k % 2 ? 0 : 1.5), z1, k++); tableRow(6, z0, z1, k++);
    }
    // fluorescent tubes (cool light inside vs warm lanterns outside)
    for (let z = -54; z > -99; z -= 6) for (const x of [-9, -3, 3, 9]) {
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color: 0xb8e8ff, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.22 }));
      glow.scale.set(3.2, 1.6, 1); glow.position.set(x, 4.2, z); g.add(glow);
    }
    // floor clutter in the aisles: foam boxes, crates, buckets (all usable)
    for (const [t, x, z] of [['foam', -3, -55], ['foam', -2.7, -55.8], ['crate', 3.1, -58], ['bucket', -9.5, -57], ['crate', 9.2, -60], ['foam', 9.6, -60.8],
      ['crate', -3.0, -67], ['crate2', 3.0, -70.5], ['bucket', 2.6, -66], ['foam', -9.4, -69], ['foam', -9.0, -70], ['bin', 9.6, -66],
      ['cart', -9.2, -82], ['foam', 3.1, -83], ['foam', 3.4, -84], ['crate', -2.8, -85], ['bucket', 9.4, -80.5], ['crate2', 9.0, -87.5],
      ['foam', -3.1, -94], ['crate', 3.0, -95.5], ['bin', -9.5, -96]]) prop(t, x, z);
    puddle(-3, -58.5, 1.2, 1.6); puddle(3, -71, 1.5, 1.2); puddle(-9.2, -74, 1.3, 1.4); puddle(9.0, -85.5, 1.2, 1.5); puddle(0.2, -90, 1.6, 1.8); puddle(-3.2, -95.5, 1.0);

    // ================================================================ 4. LOADING BAY  (z -100 .. -112)
    floor(g, 22, 12, 0, -106, ground('#6e6a62', ['#5e5a52', '#7e7a72'], (c, w, h) => {
      c.fillStyle = '#e8c547'; c.fillRect(0, h * 0.04, w, 8); c.fillRect(0, h * 0.94, w, 8);
      c.fillStyle = '#1a1a1a'; for (let i = 0; i < 20; i += 2) { c.fillRect(i * w / 20, h * 0.94, w / 20, 8); }
    }));
    wall(-15, -10.2, -100, -112); wall(10.2, 15, -100, -112);
    for (const sd of [-1, 1]) { box(g, 1.2, 4.4, 12, 0x4e5660, 0x22282e, sd * 10.8, 2.2, -106, 0.035); S.CampArt.facade(g, sd * 10.19, -100, -112, 4.4, sd, 'bay', 4); }
    for (const [t, x, z] of [['pallet', -6.5, -102.5], ['pallet', 6.8, -104], ['cart', 5.8, -108.5], ['crate2', -7.2, -108], ['crate', -6.4, -109], ['barrier', -2.6, -103.5], ['barrier', 3.0, -107], ['foam', 0.4, -110.2]]) prop(t, x, z);
    puddle(-3.5, -106.5, 1.2, 1.5);
    sign(g, 'セリ場', 'TUNA AUCTION  ↑', 5.6, 1.3, '#1a0e14', '#f2c14e', 0, 4.3, -111.6, 0, -0.25);
    // strip curtains at the auction door
    for (let i = 0; i < 14; i++) { const s = new THREE.Mesh(new THREE.PlaneGeometry(0.42, 3.4), new THREE.MeshBasicMaterial({ color: 0xc8e8f0, transparent: true, opacity: 0.28, side: THREE.DoubleSide, depthWrite: false })); s.position.set(-2.9 + i * 0.45, 1.7, -112); g.add(s); }
    wall(-15, -3.2, -111.6, -113); wall(3.2, 15, -111.6, -113);
    box(g, 11.8, 4.4, 1.2, 0x4e5660, 0x22282e, -9.0, 2.2, -112.3, 0.035); box(g, 11.8, 4.4, 1.2, 0x4e5660, 0x22282e, 9.0, 2.2, -112.3, 0.035);

    // ================================================================ 5. TUNA AUCTION  (z -112 .. -142)
    floor(g, 28, 30, 0, -127, ground('#8a8e90', ['#7a7e80', '#9a9ea0'], (c, w, h) => {
      c.strokeStyle = '#e2322b'; c.lineWidth = 8; c.strokeRect(w * 0.08, h * 0.08, w * 0.84, h * 0.84);
      c.fillStyle = 'rgba(255,255,255,0.35)'; c.font = '900 18px "Barlow Condensed", sans-serif';
      for (let i = 0; i < 12; i++) c.fillText(String(101 + i), w * 0.12 + (i % 6) * w * 0.13, i < 6 ? h * 0.3 : h * 0.62); // lot numbers
    }));
    wall(-16, -13.2, -112, -142); wall(13.2, 16, -112, -142); wall(-16, 16, -141.2, -144);
    for (const sd of [-1, 1]) { box(g, 1.2, 5, 30, 0x50505a, 0x22222a, sd * 13.8, 2.5, -127, 0.035); S.CampArt.facade(g, sd * 13.19, -112, -142, 5, sd, 'hall', 5); }
    box(g, 28, 5, 1.2, 0x50505a, 0x22222a, 0, 2.5, -141.8, 0.035);
    // the auctioneer's stand at the back
    box(g, 3.4, 1.4, 1.6, 0x8a5a3a, 0x4a2a1a, 0, 0.7, -139.2, 0.03); box(g, 3.6, 0.15, 1.8, 0xc8a070, 0x6a4a2a, 0, 1.45, -139.2, 0.02);
    wall(-1.8, 1.8, -140.1, -138.3);
    sign(g, '競り', 'AUCTION', 3.0, 1.0, '#e2322b', '#fff8ec', 0, 3.0, -141.1, 0, 0);
    // big lights over the floor: the arena should feel like the climax
    for (const [x, z] of [[-6, -120], [6, -120], [-6, -132], [6, -132], [0, -126]]) {
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color: 0xfff0d0, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.35 }));
      glow.scale.setScalar(4); glow.position.set(x, 5.1, z); g.add(glow);
    }
    // frozen tuna laid out in rows (you can pick one up as a heavy weapon), carts, crates, barriers, pallets
    for (const z of [-121, -133]) for (const x of [-8.5, -6.5, 6.5, 8.5]) prop('tuna', x, z, Math.PI / 2);
    for (const [t, x, z] of [['cart', -10.5, -126], ['cart', 10.5, -128], ['crate', -2.5, -137.5], ['crate', 2.6, -137.2], ['barrier', -10.6, -116.5], ['barrier', 10.6, -117],
      ['pallet', 0, -116.5], ['foam', -11, -138], ['bucket', 11.2, -138.5], ['crate2', 11, -122]]) prop(t, x, z);
    puddle(-4.5, -127, 1.4, 1.4); puddle(5.0, -124.5, 1.2, 1.7);

    // ================================================================ SURROUNDINGS: rooftops past the walls, so the camera never sees void
    {
      const ground = new THREE.Mesh(new THREE.PlaneGeometry(120, 220).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x2a2228 }));
      ground.position.set(0, -0.03, -70); g.add(ground);
      const roofs = [0x6a4c52, 0x5a5a6a, 0x7a5a48, 0x4e5a62, 0x6e6458, 0x584858];
      const city = [];
      const block = (x0, x1, z0, z1, h, col, steel, front) => {
        const w = x1 - x0, d = z0 - z1, cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
        box(g, w, h, d, col, mul3(col, 0.45), cx, h / 2, cz, 0.03);
        if (steel) { for (let i = 0; i < Math.floor(d / 1.6); i++) box(g, w * 0.98, 0.06, 0.08, mul3(col, 1.25), mul3(col, 0.5), cx, h + 0.03, z0 - 0.8 - i * 1.6, 0.0); return; }
        city.push({ x0, x1, z0, z1, h, front });
      };
      // the street: a row of small buildings each side, varied heights and roof colours
      for (const sd of [-1, 1]) {
        let z = 5;
        while (z > -48) {
          let z1 = Math.max(-48.5, z - (4 + Math.random() * 4));
          // the side alley on the left (z -22.5 .. -26.5) stays open: break the row around it
          if (sd < 0 && z > -22.5 && z1 < -22.5) z1 = -22.5;
          const alley = sd < 0 && z <= -22.5 && z > -26.5; if (alley) z1 = -26.5;
          // split the row into narrow buildings of different heights (a Tokyo street is many thin buildings)
          const xa = sd > 0 ? 8.4 : -30, xb = sd > 0 ? 30 : alley ? -12.2 : -8.4, inner = sd > 0 ? xa : xb, mid = inner + sd * (5 + Math.random() * 3);
          block(Math.min(inner, mid), Math.max(inner, mid), z, z1, 3.6 + Math.random() * 2.6, roofs[(Math.random() * roofs.length) | 0], false, alley ? undefined : inner);
          block(Math.min(mid, sd > 0 ? xb : xa), Math.max(mid, sd > 0 ? xb : xa), z, z1, 5 + Math.random() * 4, roofs[(Math.random() * roofs.length) | 0]); z = z1;
        }
      }
      block(-30, 30, 14, 5, 4.2, 0x5a4a52);                                   // behind the entrance
      S.CampArt.roofs(g, city);
      // big steel roofs around the market hall, loading bay and auction
      block(-30, -13.6, -48.5, -100, 5.2, 0x5e6a76, true); block(13.6, 30, -48.5, -100, 5.2, 0x5e6a76, true);
      block(-30, -11.4, -100, -112, 4.6, 0x545e68, true); block(11.4, 30, -100, -112, 4.6, 0x545e68, true);
      block(-30, -14.4, -112, -144, 5.6, 0x4e5660, true); block(14.4, 30, -112, -144, 5.6, 0x4e5660, true);
      block(-30, 30, -142.4, -160, 5.6, 0x4e5660, true);
    }

    // puddles: irregular wet patches. A darker wet stain, a lighter sky reflection inside it, a couple of glints.
    // No outline: water has no edge line, just a change in tone.
    const blob = (c, cx, cy, R, n, seed) => {
      c.beginPath();
      const pts = 48;
      for (let i = 0; i <= pts; i++) {
        const a = i / pts * Math.PI * 2;
        let r = R;
        for (let k = 1; k <= n; k++) r += Math.sin(a * (k + 1) + seed * (k + 3)) * R * 0.18 / k;
        const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r * 0.78;
        i ? c.lineTo(x, y) : c.moveTo(x, y);
      }
      c.closePath();
    };
    // cel puddle: one solid dark water shape with a crisp edge, a flat sky-reflection band clipped inside it, sharp glints
    const pudTexs = [0, 1, 2, 3].map((v) => W.canvasTex(256, 256, (c) => {
      const sd = v * 1.7 + 0.4;
      blob(c, 128, 128, 100, 2, sd); c.fillStyle = 'rgba(70,88,124,0.72)'; c.fill();
      c.strokeStyle = 'rgba(28,32,52,0.75)'; c.lineWidth = 4; c.stroke();                                   // edge line
      c.save(); blob(c, 128, 128, 97, 2, sd); c.clip();
      c.fillStyle = 'rgba(128,152,198,0.9)'; c.beginPath(); c.moveTo(0, 150 - v * 8); c.lineTo(256, 70 - v * 8); c.lineTo(256, 112 - v * 8); c.lineTo(0, 196 - v * 8); c.fill(); // sky band
      c.fillStyle = 'rgba(186,208,240,0.92)'; c.beginPath(); c.moveTo(0, 168 - v * 8); c.lineTo(256, 88 - v * 8); c.lineTo(256, 98 - v * 8); c.lineTo(0, 178 - v * 8); c.fill(); // its bright core
      c.restore();
      c.strokeStyle = '#ffffff'; c.lineCap = 'round';
      c.lineWidth = 6; c.beginPath(); c.moveTo(70, 104); c.lineTo(116, 86); c.stroke();
      c.lineWidth = 3.5; c.beginPath(); c.moveTo(150, 158); c.lineTo(176, 148); c.stroke();
    }));
    for (const p of puddles) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(p.r * 2.3 * p.sx, p.r * 2.3).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: pudTexs[(Math.random() * 4) | 0], transparent: true, depthWrite: false }));
      m.rotation.y = Math.random() * Math.PI; m.position.set(p.x, 0.012, p.z); m.renderOrder = 1; g.add(m); decor.push({ m, kind: 'puddle', p: Math.random() * 6 });
    }

    // COMBAT ZONES: you enter at z0; the exit at z1 stays shut until every enemy in the zone is down
    const zones = [
      { name: 'STREET', z0: -12, z1: -30, cam: 7, spawns: [['fighter', -1, -22], ['fighter', 2, -24], ['rusher', 0, -28], ['fighter', -2.5, -27, 'fat']] },
      { name: 'RESTAURANT ROW', z0: -30, z1: -48, cam: 7, spawns: [['thrower', -1, -45], ['thrower', 3.5, -46], ['grappler', 0, -38, 'fat'], ['fighter', -3, -40], ['technical', 2, -42]] },
      { name: 'MARKET HALL', z0: -50, z1: -77, cam: 12, spawns: [['technical', -3, -63], ['fighter', 3, -66], ['grappler', -9, -68, 'fat'], ['thrower', 9, -72], ['rusher', 3, -73], ['fighter', -3, -74]] },
      { name: 'BACK ROWS', z0: -77, z1: -100, cam: 12, spawns: [['commander', 0, -92], ['staff', -3, -86], ['fighter', 3, -88], ['fighter', -9, -90], ['rusher', 9, -94], ['thrower', -3, -97], ['grappler', 3, -96, 'fat']] },
      { name: 'LOADING BAY', z0: -100, z1: -112, cam: 10, spawns: [['sumo', 0, -109, 'fat'], ['commander', -6, -110], ['grappler', 6, -110, 'fat'], ['staff', 3, -109]] },
      { name: 'TUNA AUCTION', z0: -113, z1: -141, cam: 13, boss: { x: 0, z: -131 } },
    ];
    // how wide the walkable space is at a depth (camera keeps it framed)
    const halfWidth = (z) => (z > -12 ? 9 : z > -48 ? 7 : z > -100 ? 12 : z > -112 ? 10 : 13);

    fishes.done(); A.stallKit(g).done();
    return {
      group: g, walls, props, puddles, zones, gacha, breakables, fishMat: fishes.mats.maguro, start: { x: 0, z: -0.5 }, halfWidth, decor,
      update(t) {
        for (const d of decor) {
          if (d.kind === 'lantern') d.m.rotation.z = Math.sin(t * 1.3 + d.p) * 0.06;
          else if (d.kind === 'tube') d.m.visible = !(Math.sin(t * 23 + d.p * 7) > 0.995); // the odd flicker
        }
      },
    };
  }

  let vt = null;
  function vendTex() {
    if (!vt) vt = W.canvasTex(140, 210, (c, w, h) => {
      c.fillStyle = '#e8f4ff'; c.fillRect(0, 0, w, h);
      const cols = ['#e2322b', '#2f6fd0', '#2e9e6a', '#f2c14e', '#8a4ab0', '#f6f2ea', '#1a1a1a', '#e8572a'];
      for (let r = 0; r < 4; r++) for (let k = 0; k < 5; k++) { const x = 10 + k * 25, y = 12 + r * 48; c.fillStyle = cols[(r * 5 + k * 3) % cols.length]; c.fillRect(x + 4, y + 6, 14, 30); c.fillStyle = '#ddd'; c.fillRect(x + 7, y, 8, 7); c.fillStyle = '#c8231d'; c.fillRect(x + 2, y + 40, 18, 5); }
      c.fillStyle = 'rgba(255,255,255,0.35)'; c.fillRect(0, 0, w * 0.18, h);
    });
    return vt;
  }
  function mul3(c, k) { const C = new THREE.Color(c); C.multiplyScalar(k); return C.getHex(); }
  let gt = null;
  function glowTex() {
    if (!gt) gt = W.canvasTex(64, 64, (c) => { const gr = c.createRadialGradient(32, 32, 0, 32, 32, 31); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = gr; c.fillRect(0, 0, 64, 64); });
    return gt;
  }

  S.CampMap = { build, box, cyl, sign, glowTex };
})();
