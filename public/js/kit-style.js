'use strict';
// KIT STYLE: the soft, simple, toy-like art direction (in the spirit of Little Kitty, Big City), as one shared system:
// a palette, one soft-toon material, rounded-box geometry, simple prop builders, daylight rig and contact shadows.
// Everything that wants to belong to this world gets made through these helpers.
(function () {
  const K = S.Kit = {};

  // ---------------------------------------------------------------- palette: muted warm neutrals, softened accents
  K.P = {
    asphalt: 0x8e8992, asphaltDk: 0x7f7a84, walk: 0xcfc6ba, kerb: 0xe9e4dc, line: 0xf2efe8,
    cream: 0xede2cf, cream2: 0xe4d6bf, grey: 0xb9b4b0, warmGrey: 0xa89f97, green: 0xa8c49e, blue: 0x9db5c8, orange: 0xe4a978, pink: 0xe8b7b2,
    roof: 0x5f5b66, window: 0x55657a, windowLt: 0x8aa4bc, frame: 0xf4efe6, shutter: 0xb8b8bc, dark: 0x3d3a44,
    wood: 0xc99a68, woodDk: 0xa97c52, ice: 0xe3f0f4, white: 0xf6f3ee, metal: 0x9aa0a8,
    red: 0xd9604f, redDk: 0xb84a3e, navy: 0x3e5a8a, teal: 0x5aa8a0, yellow: 0xeac25a, leaf: 0x7fae6a, leafDk: 0x5f9356,
    skin: 0xf0c4a2, hair: 0x3a3438,
  };

  // ---------------------------------------------------------------- one soft-toon material for everything
  // A smooth ramp (not two hard bands): shadow side is lifted and slightly cool, so forms read without going dark.
  const ramp = (() => {
    const n = 64, d = new Uint8Array(n * 4);
    for (let i = 0; i < n; i++) { const t = i / (n - 1), s = t * t * (3 - 2 * t), v = Math.round(255 * (0.5 + 0.5 * s)); d.set([v, v, v, 255], i * 4); }
    const t = new THREE.DataTexture(d, n, 1, THREE.RGBAFormat); t.minFilter = t.magFilter = THREE.LinearFilter; t.needsUpdate = true; return t;
  })();
  const cache = new Map();
  K.mat = (col, o) => {
    o = o || {};
    const key = col + '|' + (o.map ? o.map.uuid : '') + '|' + (o.side || 0) + '|' + (o.opacity || 1);
    if (!o.map && cache.has(key)) return cache.get(key);
    const m = new THREE.MeshToonMaterial({ color: new THREE.Color(col), gradientMap: ramp, map: o.map || null, side: o.side || THREE.FrontSide });
    if (o.opacity !== undefined && o.opacity < 1) { m.transparent = true; m.opacity = o.opacity; m.depthWrite = false; }
    if (!o.map) cache.set(key, m);
    return m;
  };

  // ---------------------------------------------------------------- geometry: soft rounded boxes, cylinders
  const gcache = new Map();
  K.rbox = (w, h, d, r) => {
    r = Math.min(r === undefined ? 0.06 : r, w / 2 - 0.001, h / 2 - 0.001, d / 2 - 0.001);
    const key = [w, h, d, r].map((v) => v.toFixed(3)).join(',');
    if (gcache.has(key)) return gcache.get(key);
    const s = new THREE.Shape(), x = -w / 2 + r, y = -h / 2 + r, W = w - 2 * r, H = h - 2 * r;
    s.moveTo(x, y - r); s.lineTo(x + W, y - r); s.quadraticCurveTo(x + W + r, y - r, x + W + r, y); s.lineTo(x + W + r, y + H);
    s.quadraticCurveTo(x + W + r, y + H + r, x + W, y + H + r); s.lineTo(x, y + H + r); s.quadraticCurveTo(x - r, y + H + r, x - r, y + H); s.lineTo(x - r, y); s.quadraticCurveTo(x - r, y - r, x, y - r);
    const g = new THREE.ExtrudeGeometry(s, { depth: Math.max(0.001, d - 2 * r), bevelEnabled: true, bevelSize: r * 0.999, bevelThickness: r, bevelSegments: 3, curveSegments: 3 });
    g.translate(0, 0, -(d - 2 * r) / 2); g.computeVertexNormals();
    gcache.set(key, g); return g;
  };
  K.cyl = (rt, rb, h, seg) => { const key = 'c' + [rt, rb, h, seg].join(','); if (!gcache.has(key)) gcache.set(key, new THREE.CylinderGeometry(rt, rb, h, seg || 20)); return gcache.get(key); };
  K.sph = (seg) => { const key = 's' + (seg || 16); if (!gcache.has(key)) gcache.set(key, new THREE.SphereGeometry(1, seg || 16, Math.max(8, (seg || 16) >> 1))); return gcache.get(key); };

  K.add = (parent, geo, col, x, y, z, o) => {
    o = o || {};
    const m = new THREE.Mesh(geo, o.material || K.mat(col, o));
    m.position.set(x || 0, y || 0, z || 0);
    if (o.s) m.scale.set(...o.s);
    if (o.r) m.rotation.set(...o.r);
    m.castShadow = o.cast !== false; m.receiveShadow = true;
    parent.add(m); return m;
  };
  // box resting on y0 (its bottom at y0)
  K.box = (p, w, h, d, col, x, y0, z, o) => K.add(p, K.rbox(w, h, d, (o && o.round) !== undefined ? o.round : Math.min(0.08, Math.min(w, h, d) * 0.18)), col, x, y0 + h / 2, z, o);

  // ---------------------------------------------------------------- flat graphic signs (bold type on a flat colour)
  K.signTex = (txt, sub, bg, fg, w, h) => {
    const cv = document.createElement('canvas'); cv.width = w || 512; cv.height = h || 192; const c = cv.getContext('2d');
    c.fillStyle = bg; c.fillRect(0, 0, cv.width, cv.height);
    c.fillStyle = fg; c.textAlign = 'center'; c.textBaseline = 'middle';
    c.font = 'bold ' + Math.round(cv.height * (sub ? 0.46 : 0.6)) + 'px "Dela Gothic One", "Noto Sans JP", sans-serif';
    c.fillText(txt, cv.width / 2, cv.height * (sub ? 0.42 : 0.52));
    if (sub) { c.font = '800 ' + Math.round(cv.height * 0.16) + 'px "Barlow Condensed", sans-serif'; c.fillText(sub, cv.width / 2, cv.height * 0.8); }
    const t = new THREE.CanvasTexture(cv); t.anisotropy = 4; return t;
  };
  K.stripeTex = (a, b, n) => {
    const cv = document.createElement('canvas'); cv.width = 256; cv.height = 8; const c = cv.getContext('2d');
    for (let i = 0; i < n; i++) { c.fillStyle = i % 2 ? b : a; c.fillRect(i * 256 / n, 0, 256 / n + 1, 8); }
    const t = new THREE.CanvasTexture(cv); t.magFilter = THREE.NearestFilter; return t;
  };
  const hex = (n) => '#' + new THREE.Color(n).getHexString();

  // ---------------------------------------------------------------- contact shadows: a soft dark disc under anything standing
  let blobTex = null;
  K.contact = (p, x, z, rx, rz, op) => {
    if (!blobTex) { const cv = document.createElement('canvas'); cv.width = cv.height = 64; const c = cv.getContext('2d'); const g = c.createRadialGradient(32, 32, 2, 32, 32, 31); g.addColorStop(0, 'rgba(40,32,48,1)'); g.addColorStop(0.5, 'rgba(40,32,48,0.55)'); g.addColorStop(1, 'rgba(40,32,48,0)'); c.fillStyle = g; c.fillRect(0, 0, 64, 64); blobTex = new THREE.CanvasTexture(cv); }
    const m = new THREE.Mesh(new THREE.PlaneGeometry(rx * 2, rz * 2).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false, opacity: op === undefined ? 0.45 : op }));
    m.position.set(x, 0.012, z); m.renderOrder = 2; p.add(m); return m;
  };

  // ---------------------------------------------------------------- daylight rig
  K.light = (scene, focus) => {
    const sun = new THREE.DirectionalLight(0xfff3e4, 0.72);
    sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, { left: -18, right: 18, top: 18, bottom: -18, near: 1, far: 80 });
    sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.04; sun.shadow.radius = 6;
    const hemi = new THREE.HemisphereLight(0xe6eef8, 0xc4b8aa, 0.5);
    scene.add(sun, sun.target, hemi);
    const aim = (x, z) => { sun.position.set(x - 9, 16, z + 7); sun.target.position.set(x, 0, z); };
    aim(focus ? focus.x : 0, focus ? focus.z : 0);
    return { sun, hemi, aim };
  };

  // ---------------------------------------------------------------- props: the minimum shapes that read, slightly exaggerated
  const P = K.P;
  K.prop = {
    crate(p, x, z, ry) {
      const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry || 0; p.add(g);
      K.box(g, 0.62, 0.42, 0.46, P.wood, 0, 0, 0, { round: 0.04 });
      for (const y of [0.13, 0.29]) K.box(g, 0.64, 0.035, 0.48, P.woodDk, 0, y, 0, { round: 0.012, cast: false });
      K.contact(p, x, z, 0.45, 0.38, 0.35); return g;
    },
    foam(p, x, z, ry) {
      const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry || 0; p.add(g);
      K.box(g, 0.7, 0.34, 0.44, P.white, 0, 0, 0, { round: 0.05 });
      K.box(g, 0.72, 0.06, 0.46, P.blue, 0, 0.34, 0, { round: 0.025 });
      K.contact(p, x, z, 0.48, 0.36, 0.3); return g;
    },
    bin(p, x, z) {
      const g = new THREE.Group(); g.position.set(x, 0, z); p.add(g);
      K.add(g, K.cyl(0.3, 0.26, 0.78, 22), P.teal, 0, 0.39, 0);
      K.add(g, K.cyl(0.33, 0.33, 0.07, 22), 0x4b8e88, 0, 0.8, 0);
      K.add(g, K.rbox(0.18, 0.06, 0.06, 0.02), 0x4b8e88, 0, 0.86, 0);
      K.contact(p, x, z, 0.42, 0.42, 0.4); return g;
    },
    bucket(p, x, z) {
      const g = new THREE.Group(); g.position.set(x, 0, z); p.add(g);
      K.add(g, K.cyl(0.2, 0.16, 0.34, 18), P.yellow, 0, 0.17, 0);
      K.contact(p, x, z, 0.28, 0.28, 0.35); return g;
    },
    bottle(p, x, z) {
      const g = new THREE.Group(); g.position.set(x, 0, z); p.add(g);
      K.add(g, K.cyl(0.055, 0.055, 0.2, 10), 0x6fae7e, 0, 0.1, 0); K.add(g, K.cyl(0.022, 0.04, 0.09, 8), 0x6fae7e, 0, 0.245, 0);
      return g;
    },
    chair(p, x, z) {
      const g = new THREE.Group(); g.position.set(x, 0, z); p.add(g);
      K.add(g, K.cyl(0.2, 0.2, 0.07, 18), P.red, 0, 0.46, 0);
      for (const [dx, dz] of [[0.12, 0.12], [-0.12, 0.12], [0.12, -0.12], [-0.12, -0.12]]) K.add(g, K.cyl(0.025, 0.03, 0.44, 6), P.redDk, dx, 0.22, dz, { r: [dz * 0.6, 0, -dx * 0.6] });
      K.contact(p, x, z, 0.3, 0.3, 0.3); return g;
    },
    cone(p, x, z) {
      const g = new THREE.Group(); g.position.set(x, 0, z); p.add(g);
      K.box(g, 0.42, 0.06, 0.42, P.orange, 0, 0, 0, { round: 0.02 });
      K.add(g, K.cyl(0.05, 0.17, 0.62, 18), P.orange, 0, 0.37, 0); K.add(g, K.cyl(0.1, 0.13, 0.12, 18), P.white, 0, 0.42, 0);
      K.contact(p, x, z, 0.3, 0.3, 0.3); return g;
    },
    plant(p, x, z, s) {
      s = s || 1; const g = new THREE.Group(); g.position.set(x, 0, z); g.scale.setScalar(s); p.add(g);
      K.add(g, K.cyl(0.28, 0.22, 0.5, 18), 0xd28c6a, 0, 0.25, 0);
      for (const [dx, y, dz, r] of [[0, 0.82, 0, 0.36], [0.17, 0.7, 0.1, 0.25], [-0.16, 0.72, -0.06, 0.26]]) K.add(g, K.sph(14), P.leaf, dx, y, dz, { s: [r, r * 0.9, r] });
      K.contact(p, x, z, 0.42, 0.42, 0.35); return g;
    },
    table(p, x, z) {
      const g = new THREE.Group(); g.position.set(x, 0, z); p.add(g);
      K.add(g, K.cyl(0.55, 0.55, 0.07, 26), P.wood, 0, 0.76, 0); K.add(g, K.cyl(0.06, 0.06, 0.72, 10), P.dark, 0, 0.37, 0); K.add(g, K.cyl(0.26, 0.3, 0.05, 18), P.dark, 0, 0.025, 0);
      K.contact(p, x, z, 0.6, 0.6, 0.35); return g;
    },
    cart(p, x, z) {
      const g = new THREE.Group(); g.position.set(x, 0, z); p.add(g);
      K.box(g, 1.2, 0.3, 0.7, P.blue, 0, 0.32, 0, { round: 0.06 }); K.box(g, 0.06, 0.6, 0.62, P.metal, -0.66, 0.4, 0, { round: 0.03 });
      for (const [dx, dz] of [[0.45, 0.3], [-0.45, 0.3], [0.45, -0.3], [-0.45, -0.3]]) K.add(g, K.cyl(0.13, 0.13, 0.08, 16), P.dark, dx, 0.13, dz, { r: [Math.PI / 2, 0, 0] });
      K.contact(p, x, z, 0.8, 0.5, 0.35); return g;
    },
    ac(p, x, y, z, ry) { // wall air-conditioner: chunky box, round fan grille
      const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry || 0; p.add(g);
      K.box(g, 0.95, 0.66, 0.38, P.white, 0, -0.33, 0, { round: 0.06 });
      K.add(g, K.cyl(0.22, 0.22, 0.03, 20), 0xc6c6c4, 0.16, 0, 0.19, { r: [Math.PI / 2, 0, 0] });
      return g;
    },
    vending(p, x, z, ry, col) {
      const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry || 0; p.add(g);
      K.box(g, 0.96, 1.9, 0.78, col, 0, 0, 0, { round: 0.1 });
      K.box(g, 0.78, 0.9, 0.04, 0xeef3f6, 0, 0.8, 0.39, { round: 0.03, cast: false });
      for (let r = 0; r < 3; r++) for (let i = 0; i < 5; i++) K.add(g, K.rbox(0.09, 0.2, 0.05, 0.02), [P.red, P.blue, P.yellow, P.green, P.orange][(i + r) % 5], -0.28 + i * 0.14, 0.95 + r * 0.27, 0.41, { cast: false });
      K.box(g, 0.6, 0.16, 0.04, P.dark, 0, 0.25, 0.39, { round: 0.03, cast: false });
      K.contact(p, x, z, 0.7, 0.6, 0.4); return g;
    },
    pole(p, x, z) { // utility pole: the shape that says "Japanese street"
      const g = new THREE.Group(); g.position.set(x, 0, z); p.add(g);
      K.add(g, K.cyl(0.13, 0.16, 8.4, 14), 0xb9b6b0, 0, 4.2, 0);
      K.box(g, 1.3, 0.12, 0.12, 0x9a9690, 0, 7.4, 0, { round: 0.03 }); K.box(g, 0.9, 0.1, 0.1, 0x9a9690, 0, 6.8, 0, { round: 0.03 });
      K.add(g, K.cyl(0.18, 0.18, 0.5, 14), 0x8a8780, 0.22, 6.2, 0);
      K.box(g, 0.24, 1.1, 0.05, P.yellow, 0, 0.9, 0.16, { round: 0.02, cast: false }); // the yellow-black guard strip
      for (let i = 0; i < 4; i++) K.box(g, 0.25, 0.1, 0.06, P.dark, 0, 1.0 + i * 0.26, 0.17, { round: 0.01, cast: false });
      K.contact(p, x, z, 0.35, 0.35, 0.4); return g;
    },
  };
  // a sagging cable between two points (graphic, thin, dark)
  K.cable = (p, a, b, sag) => {
    const pts = []; for (let i = 0; i <= 16; i++) { const t = i / 16; pts.push(new THREE.Vector3(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - Math.sin(Math.PI * t) * sag, a[2] + (b[2] - a[2]) * t)); }
    const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 24, 0.018, 4), K.mat(0x4a4650)); p.add(m); return m;
  };

  // ---------------------------------------------------------------- a fish stall: counter, ice bed, a neat row of fish, striped awning
  K.stall = (p, x, z0, z1, sd, c1, c2, k) => {
    const g = new THREE.Group(); p.add(g);
    const len = Math.abs(z1 - z0), zc = (z0 + z1) / 2;
    K.box(g, 1.7, 0.86, len, P.wood, x, 0, zc, { round: 0.07 });
    K.box(g, 1.76, 0.06, len + 0.06, P.woodDk, x, 0.86, zc, { round: 0.02 });
    K.box(g, 1.5, 0.1, len - 0.16, P.ice, x, 0.92, zc, { round: 0.04 });
    const fishCols = [[0x8ea6bc, 0xc9d6e2], [0xe0907a, 0xf2c2b0], [0xb0bcc8, 0xe4eaf0]][k % 3];
    const n = Math.max(2, Math.floor(len / 0.34));
    for (let i = 0; i < n; i++) for (const j of [-1, 1]) {
      const fz = zc - len / 2 + 0.26 + i * (len - 0.52) / Math.max(1, n - 1), fx = x + j * 0.36;
      K.add(g, K.sph(12), fishCols[0], fx, 1.03, fz, { s: [0.3, 0.07, 0.1], cast: false });
      K.add(g, K.cyl(0.0, 0.07, 0.12, 6), fishCols[0], fx + j * 0.33, 1.03, fz, { r: [0, 0, j * Math.PI / 2], cast: false });
    }
    // price cards
    K.box(g, 0.05, 0.22, 0.3, P.white, x - sd * 0.88, 0.9, zc - len * 0.25, { round: 0.015, cast: false });
    K.box(g, 0.05, 0.22, 0.3, 0xf4e6a8, x - sd * 0.88, 0.9, zc + len * 0.25, { round: 0.015, cast: false });
    // awning: a sloped striped slab leaning out over the street on two poles
    const tex = K.stripeTex(hex(c1), hex(c2), Math.max(6, Math.round(len / 0.45) * 2));
    const aw = new THREE.Mesh(K.rbox(2.4, 0.1, len + 0.3, 0.04), K.mat(0xffffff, { map: tex }));
    aw.position.set(x - sd * 0.75, 2.75, zc); aw.rotation.set(0, Math.PI / 2, -sd * 0.0); aw.rotation.z = 0; aw.rotation.x = 0;
    aw.geometry = aw.geometry.clone(); aw.rotation.set(0, 0, sd * 0.32); // slope down toward the street
    const uv = aw.geometry.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, (aw.geometry.attributes.position.getZ(i) / (len + 0.3)) + 0.5, 0.5);
    aw.castShadow = aw.receiveShadow = true; g.add(aw);
    for (const zz of [z0, z1]) K.add(g, K.cyl(0.04, 0.04, 2.3, 8), P.metal, x - sd * 1.75, 1.15, zz);
    K.contact(p, x, zc, 1.3, len / 2 + 0.4, 0.42);
    return g;
  };

  // ---------------------------------------------------------------- a run of simple buildings along one side of a street
  // sd: -1 left (faces +x), +1 right (faces -x). Big wall volumes, a dark shop opening, windows, an AC unit, a sign, a roofline.
  K.facades = (p, xFace, z0, z1, sd, rnd, names) => {
    const cols = [P.cream, P.green, P.blue, P.cream2, P.orange, P.pink, P.grey];
    let z = z0, i = 0;
    while (z > z1 + 0.5) {
      const w = Math.min(z - z1, 3.4 + rnd() * 1.6), zc = z - w / 2, h = 5.6 + rnd() * 3.2, depth = 3.2, col = cols[(i * 3 + (sd > 0 ? 2 : 0)) % cols.length];
      const g = new THREE.Group(); p.add(g);
      const xc = xFace + sd * depth / 2;
      K.box(g, depth, h, w - 0.08, col, xc, 0, zc, { round: 0.08 });
      K.box(g, depth + 0.24, 0.24, w + 0.04, P.roof, xc - sd * 0.06, h, zc, { round: 0.06 });       // roof edge
      // ground floor: shop opening (dark) with a shutter band, or a shutter
      const shop = (i + (sd > 0 ? 1 : 0)) % 3 !== 2;
      K.box(g, 0.12, 2.3, w - 0.7, shop ? P.dark : P.shutter, xFace - sd * 0.02, 0, zc, { round: 0.04, cast: false });
      if (shop) K.box(g, 0.14, 0.35, w - 0.6, P.shutter, xFace - sd * 0.03, 2.05, zc, { round: 0.03, cast: false });
      // sign board over the shop
      const nm = names[i % names.length];
      const st = K.signTex(nm[0], nm[1], hex(nm[2]), hex(nm[3]), 512, 160);
      const sb = new THREE.Mesh(K.rbox(0.12, 0.62, Math.min(2.8, w - 0.6), 0.04), [K.mat(nm[2]), K.mat(nm[2]), K.mat(nm[2]), K.mat(nm[2]), K.mat(0xffffff, { map: st }), K.mat(0xffffff, { map: st })]);
      sb.position.set(xFace - sd * 0.1, 2.75, zc); sb.rotation.y = sd > 0 ? -Math.PI / 2 : Math.PI / 2; sb.castShadow = true; g.add(sb);
      // upper floors: windows as simple framed dark panes
      const floors = Math.floor((h - 3.4) / 1.7);
      for (let f = 0; f < floors; f++) {
        const wy = 3.6 + f * 1.7, nw = w > 4 ? 2 : 1;
        for (let k = 0; k < nw; k++) {
          const wz = zc + (nw === 2 ? (k ? -1 : 1) * w * 0.22 : 0);
          K.box(g, 0.08, 1.0, 1.1, P.frame, xFace - sd * 0.02, wy, wz, { round: 0.03, cast: false });
          K.box(g, 0.1, 0.82, 0.92, f % 2 ? P.window : P.windowLt, xFace - sd * 0.04, wy + 0.09, wz, { round: 0.02, cast: false });
        }
        if (f === 0 && (i % 2 === 0)) K.prop.ac(g, xFace - sd * 0.22, wy + 0.1, zc + (w > 4 ? 0 : w * 0.3), sd > 0 ? -Math.PI / 2 : Math.PI / 2);
      }
      // a thick drainpipe at the seam
      K.add(g, K.cyl(0.07, 0.07, h, 10), 0xd0ccc4, xFace - sd * 0.1, h / 2, z - 0.12);
      z -= w; i++;
    }
  };
})();
