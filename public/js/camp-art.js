'use strict';
// CAMPAIGN ART: detailed props, fish, awnings for the market. Detail lives in painted textures
// (planks, labels, stencils, scales) on simple merged shapes, so each prop is one draw call + its ink outline.
(function () {
  const W = S.R3;
  const TX = {}; // texture cache
  const tex = (key, w, h, draw) => TX[key] || (TX[key] = W.canvasTex(w, h, draw));
  const mat = (map, shade, o) => { const m = S.toon(0xffffff, Object.assign({ map, shade: shade || 0x8a7c9c, rimAmt: 0.35 }, o || {})); return m; };
  const rnd = (a, b) => a + Math.random() * (b - a);

  // ---------------------------------------------------------------- geometry helpers
  // merge geometries (each with an optional transform and a uv remap) into one non-indexed geometry
  function merge(parts) {
    const pos = [], nor = [], uv = [];
    const m3 = new THREE.Matrix3(), v = new THREE.Vector3();
    for (const p of parts) {
      let g = p.geo.index ? p.geo.toNonIndexed() : p.geo.clone();
      if (p.m) g.applyMatrix4(p.m);
      const P = g.attributes.position, N = g.attributes.normal, U = g.attributes.uv;
      for (let i = 0; i < P.count; i++) {
        pos.push(P.getX(i), P.getY(i), P.getZ(i));
        nor.push(N.getX(i), N.getY(i), N.getZ(i));
        if (p.uv) { const r = p.uv(U ? U.getX(i) : 0, U ? U.getY(i) : 0); uv.push(r[0], r[1]); } else uv.push(U ? U.getX(i) : 0, U ? U.getY(i) : 0);
      }
      void m3; void v;
    }
    const out = new THREE.BufferGeometry();
    out.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    out.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    out.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    out.computeBoundingSphere();
    return out;
  }
  const M4 = (x, y, z, rx, ry, rz, sx, sy, sz) => new THREE.Matrix4().compose(new THREE.Vector3(x || 0, y || 0, z || 0),
    new THREE.Quaternion().setFromEuler(new THREE.Euler(rx || 0, ry || 0, rz || 0)), new THREE.Vector3(sx || 1, sy || 1, sz || 1));
  const at = (u, v) => () => [u, v]; // sample one spot of the texture (solid parts)
  const region = (u0, v0, u1, v1) => (u, v) => [u0 + u * (u1 - u0), v0 + v * (v1 - v0)];
  const rbox = (w, h, d) => new THREE.BoxGeometry(w, h, d);

  // ---------------------------------------------------------------- painted textures
  const wood = (c, x, y, w, h, base, dark, seed) => {
    c.fillStyle = base; c.fillRect(x, y, w, h);
    c.strokeStyle = dark; c.globalAlpha = 0.35; c.lineWidth = 1.5;
    for (let i = 0; i < h / 5; i++) { c.beginPath(); const yy = y + i * 5 + Math.sin(i + seed) * 2; c.moveTo(x, yy); c.bezierCurveTo(x + w * 0.3, yy + rnd(-3, 3), x + w * 0.7, yy + rnd(-3, 3), x + w, yy); c.stroke(); }
    c.globalAlpha = 1;
  };
  // wooden fish crate: horizontal planks with dark gaps, corner posts, a stencilled stamp, nails
  const crateTex = (stamp) => tex('crate' + stamp, 256, 256, (c, w, h) => {
    c.fillStyle = '#3a2210'; c.fillRect(0, 0, w, h);
    const n = 4, ph = h / n;
    for (let i = 0; i < n; i++) wood(c, 6, i * ph + 4, w - 12, ph - 8, ['#c8925a', '#b98450', '#d09a62', '#bf8a55'][i], '#6a4020', i * 3);
    for (const x of [0, w - 22]) wood(c, x, 0, 22, h, '#9a6a3a', '#4a2a10', 7);
    c.fillStyle = '#2a1a10'; for (const x of [11, w - 11]) for (let i = 0; i < n; i++) { c.beginPath(); c.arc(x, i * ph + ph / 2, 2.5, 0, 7); c.fill(); }
    c.save(); c.translate(w / 2, h / 2); c.rotate(-0.04); c.globalAlpha = 0.8; c.fillStyle = '#7a1a14';
    c.font = '72px "Dela Gothic One", sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(stamp, 0, -8);
    c.font = '800 20px "Barlow Condensed", sans-serif'; c.fillText('UOGASHI · 鮮魚', 0, 46); c.restore();
  });
  const crateTopTex = () => tex('cratetop', 256, 256, (c, w, h) => {
    c.fillStyle = '#2a180a'; c.fillRect(0, 0, w, h);
    for (let i = 0; i < 5; i++) wood(c, 4, i * 51 + 3, w - 8, 45, ['#d2a06a', '#c4925c', '#d8a872', '#c99860', '#d09c66'][i], '#7a5030', i);
    c.fillStyle = '#2a1a10'; for (let i = 0; i < 5; i++) for (const x of [14, w - 14]) { c.beginPath(); c.arc(x, i * 51 + 25, 2.5, 0, 7); c.fill(); }
  });
  // styrofoam fish box: white with a blue band, a vendor sticker; top: lid pushed back, ice and a fish
  const foamTex = () => tex('foam', 256, 256, (c, w, h) => {
    c.fillStyle = '#f4f6f4'; c.fillRect(0, 0, w, h);
    for (let i = 0; i < 900; i++) { c.fillStyle = Math.random() < 0.5 ? 'rgba(200,210,215,0.5)' : 'rgba(255,255,255,0.8)'; c.fillRect(Math.random() * w, Math.random() * h, 3, 3); }
    c.fillStyle = '#2a7ad0'; c.fillRect(0, h * 0.62, w, h * 0.12);
    c.fillStyle = '#fff3c4'; c.fillRect(w * 0.12, h * 0.18, w * 0.36, h * 0.3); c.strokeStyle = '#c8231d'; c.lineWidth = 4; c.strokeRect(w * 0.12, h * 0.18, w * 0.36, h * 0.3);
    c.fillStyle = '#c8231d'; c.font = '44px "Dela Gothic One", sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('鮪', w * 0.3, h * 0.33);
    c.fillStyle = '#1a1014'; c.font = '800 22px "Barlow Condensed", sans-serif'; c.fillText('No.' + (10 + Math.floor(Math.random() * 89)), w * 0.72, h * 0.3);
  });
  const foamTopTex = () => tex('foamtop', 256, 256, (c, w, h) => {
    c.fillStyle = '#e8eef0'; c.fillRect(0, 0, w, h);
    c.fillStyle = '#cfe8f6'; c.fillRect(14, 14, w - 28, h - 28);
    for (let i = 0; i < 160; i++) { c.fillStyle = Math.random() < 0.5 ? '#ffffff' : '#a8d4ee'; const s = rnd(4, 12); c.fillRect(rnd(14, w - 28), rnd(14, h - 28), s, s * rnd(0.6, 1.2)); }
    // a fish lying on the ice
    c.save(); c.translate(w * 0.5, h * 0.52); c.rotate(-0.5);
    const gr = c.createLinearGradient(0, -24, 0, 24); gr.addColorStop(0, '#2a3e66'); gr.addColorStop(0.5, '#8ea6c4'); gr.addColorStop(1, '#e6ecf2');
    c.fillStyle = gr; c.beginPath(); c.ellipse(0, 0, 86, 24, 0, 0, 7); c.fill();
    c.fillStyle = '#2a3e66'; c.beginPath(); c.moveTo(-80, 0); c.lineTo(-112, -24); c.lineTo(-104, 0); c.lineTo(-112, 24); c.fill();
    c.fillStyle = '#111'; c.beginPath(); c.arc(64, -6, 5, 0, 7); c.fill(); c.fillStyle = '#fff'; c.beginPath(); c.arc(65, -7, 1.6, 0, 7); c.fill();
    c.restore();
    c.fillStyle = '#4a9a3a'; c.beginPath(); c.moveTo(30, h - 40); c.lineTo(90, h - 70); c.lineTo(70, h - 30); c.fill(); // a leaf of baran
  });
  // a striped awning canvas, with a scalloped valance
  const stripeTex = (c1, c2, n) => tex('stripe' + c1 + c2 + n, 512, 64, (c, w, h) => {
    for (let i = 0; i < n; i++) { c.fillStyle = i % 2 ? c1 : c2; c.fillRect(i * w / n, 0, w / n + 1, h); }
    c.fillStyle = 'rgba(0,0,0,0.07)'; for (let i = 0; i < 40; i++) c.fillRect(0, i * h / 40, w, 1); // canvas weave
  });
  const valanceTex = (c1, c2, n) => tex('val' + c1 + c2 + n, 512, 64, (c, w, h) => {
    for (let i = 0; i < n; i++) { c.fillStyle = i % 2 ? c1 : c2; c.fillRect(i * w / n, 0, w / n + 1, h); }
    // scallops: cut half-circles out of the bottom edge (alpha), a hem line above them
    c.globalCompositeOperation = 'destination-out';
    const sc = n * 2, r = w / sc / 2;
    for (let i = 0; i <= sc; i++) { c.beginPath(); c.arc(i * w / sc, h + r * 0.35, r, 0, 7); c.fill(); }
    c.globalCompositeOperation = 'source-over';
    c.fillStyle = 'rgba(0,0,0,0.25)'; c.fillRect(0, 6, w, 3);
  });
  const fishTex = (sp) => tex('fish' + sp, 256, 128, (c, w, h) => {
    const P = {
      maguro: ['#1e2a4a', '#5a6e94', '#d8e0ea'], tai: ['#c8384a', '#ec8a8a', '#fbe4dc'], saba: ['#2a6a72', '#7aa6a8', '#eef2f0'], sake: ['#4a5a6a', '#9aa8b4', '#f2ece6'],
    }[sp];
    const gr = c.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, P[0]); gr.addColorStop(0.42, P[1]); gr.addColorStop(0.6, P[2]); gr.addColorStop(1, P[2]);
    c.fillStyle = gr; c.fillRect(0, 0, w, h);
    if (sp === 'saba') { c.strokeStyle = '#123236'; c.lineWidth = 3; for (let i = 0; i < 18; i++) { c.beginPath(); c.moveTo(i * 14, 6); c.quadraticCurveTo(i * 14 + 7, 26, i * 14 - 3, 46); c.stroke(); } }
    if (sp === 'tai') { c.fillStyle = 'rgba(80,190,255,0.7)'; for (let i = 0; i < 40; i++) { c.beginPath(); c.arc(rnd(0, w), rnd(8, 48), 2, 0, 7); c.fill(); } }
    // scales sheen
    c.strokeStyle = 'rgba(255,255,255,0.18)'; c.lineWidth = 1; for (let y = 20; y < h * 0.7; y += 8) for (let x = (y / 8) % 2 * 4; x < w; x += 8) { c.beginPath(); c.arc(x, y, 4, 0, Math.PI); c.stroke(); }
    // eyes at the head end (u≈0.25 is the nose), and a gill line
    for (const u of [0.19, 0.31]) { c.fillStyle = '#f6f0c0'; c.beginPath(); c.arc(u * w, h * 0.44, 6, 0, 7); c.fill(); c.fillStyle = '#0a0a0a'; c.beginPath(); c.arc(u * w, h * 0.44, 4, 0, 7); c.fill(); }
    c.strokeStyle = 'rgba(40,20,30,0.6)'; c.lineWidth = 2; for (const u of [0.15, 0.35]) { c.beginPath(); c.moveTo(u * w, h * 0.3); c.quadraticCurveTo(u * w + (u < 0.25 ? -6 : 6), h * 0.5, u * w, h * 0.7); c.stroke(); }
    c.fillStyle = P[0]; c.fillRect(w - 8, 0, 8, 8); // solid patch for fins (u≈0.99, v≈0.98)
  });

  // ---------------------------------------------------------------- shared geometry
  const G = {};
  // a fish: elongated body (sphere, so the texture's top/belly bands follow it), forked tail and fins
  G.fish = () => G._fish || (G._fish = (() => {
    const fin = new THREE.Shape(); fin.moveTo(0, 0); fin.lineTo(-0.5, 0.55); fin.lineTo(-0.3, 0); fin.lineTo(-0.5, -0.55); fin.lineTo(0, 0);
    const dors = new THREE.Shape(); dors.moveTo(-0.3, 0); dors.lineTo(0.05, 0.42); dors.lineTo(0.3, 0); dors.lineTo(-0.3, 0);
    const finG = new THREE.ExtrudeGeometry(fin, { depth: 0.04, bevelEnabled: false }), dG = new THREE.ExtrudeGeometry(dors, { depth: 0.03, bevelEnabled: false });
    return merge([
      { geo: new THREE.SphereGeometry(1, 12, 7), m: M4(0, 0, 0, 0, 0, 0, 0.32, 0.36, 1) }, // hundreds of these on the counters: keep them light
      { geo: finG, m: M4(0, 0, -0.92, 0, Math.PI / 2, 0, 0.75, 0.75, 1), uv: at(0.99, 0.98) },
      { geo: dG, m: M4(-0.015, 0.3, -0.05, 0, Math.PI / 2, 0, 0.9, 0.55, 1), uv: at(0.99, 0.98) },
    ]);
  })());
  // red plastic market stool
  G.stool = () => G._stool || (G._stool = merge([
    { geo: new THREE.CylinderGeometry(0.22, 0.2, 0.06, 20), m: M4(0, 0.46, 0) },
    { geo: new THREE.TorusGeometry(0.21, 0.025, 6, 20), m: M4(0, 0.43, 0, Math.PI / 2) },
    ...[0, 1, 2, 3].map((i) => { const a = i * Math.PI / 2 + Math.PI / 4; return { geo: new THREE.CylinderGeometry(0.03, 0.04, 0.46, 8), m: M4(Math.cos(a) * 0.19, 0.22, Math.sin(a) * 0.19, Math.sin(a) * 0.18, 0, -Math.cos(a) * 0.18) }; }),
    { geo: new THREE.TorusGeometry(0.19, 0.018, 5, 16), m: M4(0, 0.14, 0, Math.PI / 2) },
  ]));
  // blue plastic drum with ribs and a lid
  G.drum = () => G._drum || (G._drum = (() => {
    const pts = []; const R = 0.3;
    pts.push(new THREE.Vector2(0, 0)); pts.push(new THREE.Vector2(R - 0.03, 0)); pts.push(new THREE.Vector2(R, 0.03));
    for (const y of [0.18, 0.38, 0.58]) { pts.push(new THREE.Vector2(R, y - 0.03)); pts.push(new THREE.Vector2(R + 0.025, y)); pts.push(new THREE.Vector2(R, y + 0.03)); }
    pts.push(new THREE.Vector2(R, 0.72)); pts.push(new THREE.Vector2(R - 0.02, 0.74)); pts.push(new THREE.Vector2(0, 0.74));
    return merge([{ geo: new THREE.LatheGeometry(pts, 20) }, { geo: new THREE.BoxGeometry(0.2, 0.05, 0.05), m: M4(0, 0.77, 0), uv: at(0.5, 0.1) }]);
  })());
  G.bucket = () => G._bucket || (G._bucket = merge([
    { geo: new THREE.LatheGeometry([new THREE.Vector2(0, 0), new THREE.Vector2(0.16, 0), new THREE.Vector2(0.22, 0.32), new THREE.Vector2(0.235, 0.33), new THREE.Vector2(0.2, 0.3), new THREE.Vector2(0, 0.27)], 18) },
    { geo: new THREE.TorusGeometry(0.22, 0.012, 4, 16, Math.PI), m: M4(0, 0.32, 0, 0, 0, 0) },
  ]));
  G.bottle = () => G._bottle || (G._bottle = new THREE.LatheGeometry([0, 0.065, 0.07, 0.07, 0.068, 0.04, 0.025, 0.025, 0.03, 0].map((r, i) => new THREE.Vector2(r, [0, 0, 0.01, 0.16, 0.19, 0.24, 0.27, 0.33, 0.34, 0.34][i])), 14));
  G.onigiri = () => G._oni || (G._oni = (() => {
    const s = new THREE.Shape(), r = 0.16, k = 0.05;
    const P = [0, 1, 2].map((i) => { const a = Math.PI / 2 + i * 2 * Math.PI / 3; return [Math.cos(a) * r, Math.sin(a) * r]; });
    for (let i = 0; i < 3; i++) { const p = P[i], q = P[(i + 1) % 3], n = P[(i + 2) % 3]; const a = [p[0] + (q[0] - p[0]) * 0.18, p[1] + (q[1] - p[1]) * 0.18], b = [q[0] + (p[0] - q[0]) * 0.18, q[1] + (p[1] - q[1]) * 0.18]; if (i === 0) s.moveTo(a[0], a[1]); else s.lineTo(a[0], a[1]); s.lineTo(b[0], b[1]); const c2 = [q[0] + (n[0] - q[0]) * 0.18, q[1] + (n[1] - q[1]) * 0.18]; s.quadraticCurveTo(q[0], q[1], c2[0], c2[1]); }
    const g = new THREE.ExtrudeGeometry(s, { depth: 0.08, bevelEnabled: true, bevelThickness: 0.04, bevelSize: 0.035, bevelSegments: 4, curveSegments: 6 });
    g.translate(0, 0, -0.04); g.computeVertexNormals();
    const pos = g.attributes.position, uv = g.attributes.uv; for (let i = 0; i < pos.count; i++) uv.setXY(i, 0.5, pos.getY(i) < -0.05 ? 0.1 : 0.9); // nori band at the bottom
    return g;
  })());
  // the tuna: a long spindle with a crescent tail, finlets, and frost
  G.tuna = () => G._tuna || (G._tuna = (() => {
    const pts = []; for (let i = 0; i <= 16; i++) { const t = i / 16, y = -0.95 + t * 1.9; const r = 0.3 * Math.pow(Math.sin(Math.PI * Math.min(1, t * 1.08)), 0.75) + 0.012; pts.push(new THREE.Vector2(r, y)); }
    const body = new THREE.LatheGeometry(pts, 18); body.rotateX(Math.PI / 2); body.scale(1, 0.95, 1);
    const tail = new THREE.Shape(); tail.moveTo(0, 0); tail.quadraticCurveTo(-0.15, 0.25, -0.38, 0.5); tail.quadraticCurveTo(-0.2, 0.1, -0.22, 0); tail.quadraticCurveTo(-0.2, -0.1, -0.38, -0.5); tail.quadraticCurveTo(-0.15, -0.25, 0, 0);
    const tG = new THREE.ExtrudeGeometry(tail, { depth: 0.04, bevelEnabled: false });
    const fin = new THREE.Shape(); fin.moveTo(0, 0); fin.lineTo(0.1, 0.28); fin.lineTo(0.22, 0); fin.lineTo(0, 0);
    const fG = new THREE.ExtrudeGeometry(fin, { depth: 0.025, bevelEnabled: false });
    const parts = [{ geo: body, uv: (u, v) => [u, 0.05 + v * 0.9] }, { geo: tG, m: M4(-0.02, 0, -0.95, 0, Math.PI / 2, 0), uv: at(0.75, 0.97) },
      { geo: fG, m: M4(-0.012, 0.26, -0.1, 0, Math.PI / 2, 0, 1.2, 1, 1), uv: at(0.75, 0.97) }];
    for (let i = 0; i < 6; i++) parts.push({ geo: new THREE.BoxGeometry(0.02, 0.05, 0.05), m: M4(0, 0.13 - i * 0.01, -0.45 - i * 0.07, 0.6), uv: at(0.25, 0.02) }); // yellow finlets
    for (const sd of [-1, 1]) parts.push({ geo: fG, m: M4(sd * 0.27, 0.0, 0.2, 0, Math.PI / 2 + sd * 1.2, -Math.PI / 2, 1.3, 1, 1), uv: at(0.75, 0.97) });
    return merge(parts);
  })());
  const tunaTex = () => tex('tuna', 256, 256, (c, w, h) => {
    // lathe uv: u around the body, v along it. Back (top) at u≈0.75 after rotation; paint around-the-body bands
    const gr = c.createLinearGradient(0, 0, w, 0);
    gr.addColorStop(0, '#e2e8ee'); gr.addColorStop(0.25, '#c8d0da'); gr.addColorStop(0.55, '#3c4c6e'); gr.addColorStop(0.75, '#1a2440'); gr.addColorStop(0.95, '#3c4c6e'); gr.addColorStop(1, '#c8d0da');
    c.fillStyle = gr; c.fillRect(0, 0, w, h);
    for (let i = 0; i < 500; i++) { c.fillStyle = 'rgba(240,250,255,' + rnd(0.2, 0.6) + ')'; c.fillRect(rnd(0, w), rnd(0, h), rnd(1, 4), rnd(1, 3)); } // frost
    c.fillStyle = '#f2c84a'; c.fillRect(0, 0, w, 10); c.fillStyle = '#1a2440'; c.fillRect(w * 0.7, h - 12, w * 0.1, 12);
    // a red auction lot number painted on the flank
    c.fillStyle = '#d8201a'; c.font = '800 34px "Barlow Condensed", sans-serif'; c.textAlign = 'center'; c.fillText(String(100 + Math.floor(Math.random() * 800)), w * 0.4, h * 0.45);
  });

  // ---------------------------------------------------------------- props (one mesh + outline each)
  function prop(type) {
    const g = new THREE.Group(), add = (geo, m, th, y) => { const o = W.mesh(geo, m, th === undefined ? 0.02 : th); if (y) o.position.y = y; g.add(o); return o; };
    switch (type) {
      case 'crate': {
        const geo = merge([{ geo: rbox(0.66, 0.46, 0.66), m: M4(0, 0.23, 0), uv: region(0, 0, 1, 1) }]);
        const ms = [mat(crateTex(['魚', '鮮', '海'][Math.floor(Math.random() * 3)]), 0x7a6a7a)];
        add(geo, ms[0]); const top = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.62).rotateX(-Math.PI / 2), mat(crateTopTex(), 0x7a6a7a)); top.position.y = 0.465; g.add(top);
        break;
      }
      case 'crate2': {
        const m1 = mat(crateTex('魚'), 0x7a6a7a), m2 = mat(crateTex('海'), 0x7a6a7a);
        add(rbox(0.78, 0.5, 0.78), m1, 0.022, 0.25);
        const t = add(rbox(0.72, 0.48, 0.72), m2, 0.022, 0.74); t.rotation.y = 0.18; t.position.x = 0.03;
        const top = new THREE.Mesh(new THREE.PlaneGeometry(0.68, 0.68).rotateX(-Math.PI / 2), mat(crateTopTex(), 0x7a6a7a)); top.position.y = 0.985; top.rotation.y = 0.18; g.add(top);
        break;
      }
      case 'foam': {
        add(rbox(0.62, 0.3, 0.46), mat(foamTex(), 0x9aa4b4), 0.02, 0.15);
        const top = new THREE.Mesh(new THREE.PlaneGeometry(0.6, 0.44).rotateX(-Math.PI / 2), mat(foamTopTex(), 0x8a96a8)); top.position.y = 0.302; g.add(top);
        const lid = add(rbox(0.64, 0.04, 0.48), mat(foamTex(), 0x9aa4b4), 0.014, 0.33); lid.position.z = -0.3; lid.rotation.x = -0.5; lid.position.y = 0.42;
        break;
      }
      case 'bottle': {
        const lab = tex('bottlelab', 64, 64, (c, w, h) => { c.fillStyle = '#2e7a4a'; c.fillRect(0, 0, w, h); c.fillStyle = '#f6eddc'; c.fillRect(0, h * 0.35, w, h * 0.3); c.fillStyle = '#c8231d'; c.fillRect(w * 0.2, h * 0.42, w * 0.6, h * 0.16); });
        add(G.bottle(), mat(lab, 0x1a4a2a, { spec: 0.8 }), 0.012);
        break;
      }
      case 'chair': add(G.stool(), S.toon(0xe0322a, { shade: 0x7a1414, spec: 0.35, rimAmt: 0.5 }), 0.016); break;
      case 'bin': add(G.drum(), S.toon(0x2a6ad0, { shade: 0x10285a, spec: 0.3, rimAmt: 0.45 }), 0.02); break;
      case 'bucket': {
        add(G.bucket(), S.toon(0xf2b830, { shade: 0x8a5a10, spec: 0.3 }), 0.014);
        const w = new THREE.Mesh(new THREE.CircleGeometry(0.19, 16).rotateX(-Math.PI / 2), S.toon(0x8ad0f0, { shade: 0x3a7aa0, spec: 0.8 })); w.position.y = 0.28; g.add(w);
        break;
      }
      case 'pallet': {
        const parts = [];
        for (let i = 0; i < 5; i++) parts.push({ geo: rbox(1.1, 0.03, 0.15), m: M4(0, 0.135, -0.38 + i * 0.19) });
        for (const x of [-0.48, 0, 0.48]) parts.push({ geo: rbox(0.12, 0.09, 0.9), m: M4(x, 0.06, 0) });
        const m = mat(tex('palletwood', 128, 128, (c, w, h) => wood(c, 0, 0, w, h, '#c8a070', '#6a4a2a', 1)), 0x6a5a5a);
        add(merge(parts), m, 0.014);
        break;
      }
      case 'cart': {
        // a market hand cart: steel flatbed, push handle, rubber wheels, loaded with foam boxes
        const steel = S.toon(0x9aa6b2, { shade: 0x3a4652, spec: 0.6, rimAmt: 0.5 });
        add(merge([{ geo: rbox(1.15, 0.06, 0.72), m: M4(0, 0.36, 0) },
          { geo: new THREE.TorusGeometry(0.32, 0.025, 6, 16, Math.PI), m: M4(-0.58, 0.62, 0, 0, Math.PI / 2, -0.15) },
          { geo: new THREE.CylinderGeometry(0.025, 0.025, 0.3, 6), m: M4(-0.6, 0.48, 0.32, 0, 0, -0.15) }, { geo: new THREE.CylinderGeometry(0.025, 0.025, 0.3, 6), m: M4(-0.6, 0.48, -0.32, 0, 0, -0.15) },
          ...[[-0.42, -0.3], [0.42, -0.3], [-0.42, 0.3], [0.42, 0.3]].map(([x, z]) => ({ geo: rbox(0.05, 0.22, 0.05), m: M4(x, 0.22, z) }))]), steel, 0.016);
        const tyre = S.toon(0x22222a, { shade: 0x08080c }), hub = S.toon(0xf2c14e, { shade: 0x8a6a1a });
        for (const [x, z] of [[-0.42, -0.33], [0.42, -0.33], [-0.42, 0.33], [0.42, 0.33]]) {
          const t = add(new THREE.TorusGeometry(0.075, 0.035, 8, 16), tyre, 0.01); t.position.set(x, 0.11, z);
          const h = add(new THREE.CylinderGeometry(0.045, 0.045, 0.05, 10), hub, 0); h.rotation.x = Math.PI / 2; h.position.set(x, 0.11, z);
        }
        for (const [x, y, z, r] of [[0.15, 0.54, -0.12, 0.05], [0.12, 0.54, 0.2, -0.04], [0.14, 0.84, 0.03, 0.1]]) {
          const b = add(rbox(0.6, 0.3, 0.45), mat(foamTex(), 0x9aa4b4), 0.012); b.position.set(x, y, z); b.rotation.y = r + Math.PI / 2;
        }
        break;
      }
      case 'barrier': {
        const st = tex('barrier', 256, 32, (c, w, h) => { c.fillStyle = '#f2c14e'; c.fillRect(0, 0, w, h); c.fillStyle = '#1a1a1a'; for (let i = -2; i < 14; i++) { c.beginPath(); c.moveTo(i * 24, h); c.lineTo(i * 24 + 12, h); c.lineTo(i * 24 + 24, 0); c.lineTo(i * 24 + 12, 0); c.fill(); } });
        const m = mat(st, 0x8a6a2a);
        add(merge([{ geo: rbox(1.15, 0.14, 0.05), m: M4(0, 0.78, 0.02) }, { geo: rbox(1.15, 0.14, 0.05), m: M4(0, 0.5, 0.02) }]), m, 0.014);
        const leg = S.toon(0xf6f2ea, { shade: 0x8a8a96 });
        add(merge([-0.5, 0.5].flatMap((x) => [{ geo: rbox(0.06, 0.92, 0.06), m: M4(x, 0.45, 0.12, -0.18) }, { geo: rbox(0.06, 0.92, 0.06), m: M4(x, 0.45, -0.12, 0.18) }])), leg, 0.012);
        break;
      }
      case 'tuna': add(G.tuna(), mat(tunaTex(), 0x6a7290, { spec: 0.5, rimAmt: 0.6, rim: 0xe0f0ff }), 0.025, 0.28); break;
      case 'knife': { // a fish knife (deba): wooden handle, wide steel blade. Built along +Y; lies flat on the floor until picked up
        const k = new THREE.Group();
        const handle = W.mesh(new THREE.CylinderGeometry(0.016, 0.019, 0.12, 8), S.toon(0x8a5a32, { shade: 0x3e2410 }), 0.006); handle.position.y = 0.0; k.add(handle);
        const ferrule = W.mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.018, 8), S.toon(0x2a2a2e, { shade: 0x0a0a0c }), 0); ferrule.position.y = 0.068; k.add(ferrule);
        const sh = new THREE.Shape(); sh.moveTo(-0.004, 0); sh.lineTo(0.042, 0); sh.quadraticCurveTo(0.04, 0.12, 0.004, 0.2); sh.lineTo(-0.004, 0.2); sh.lineTo(-0.004, 0);
        const bg = new THREE.ExtrudeGeometry(sh, { depth: 0.006, bevelEnabled: false }); bg.translate(-0.012, 0.076, -0.003);
        k.add(W.mesh(bg, S.toon(0xe4e8ee, { shade: 0x7a8494, spec: 0.9, rimAmt: 0.6 }), 0.006));
        k.rotation.z = Math.PI / 2; k.position.y = 0.025; g.add(k); g.userData.k = k;
        break;
      }
      case 'onigiri': {
        const t = tex('oni', 8, 64, (c, w, h) => { c.fillStyle = '#f8f4ea'; c.fillRect(0, 0, w, h); c.fillStyle = '#1a2a1e'; c.fillRect(0, h * 0.6, w, h * 0.4); });
        const o = add(G.onigiri(), mat(t, 0xb8b0a0), 0.014); o.position.y = 0.18; o.rotation.x = -0.25;
        break;
      }
    }
    return g;
  }

  // ---------------------------------------------------------------- fish displays: instanced, four species
  function fishBatch(scene) {
    const list = { maguro: [], tai: [], saba: [], sake: [] };
    return {
      meshes: {}, mats: {},
      add(sp, x, y, z, ry, s) { list[sp].push(M4(x, y, z, 0, ry, 0, s, s, s)); return [sp, list[sp].length - 1]; },
      at(sp, i) { return list[sp][i]; },
      addRandom(x, y, z, ry, s) { const k = Object.keys(list); this.add(k[Math.floor(Math.random() * k.length)], x, y, z, ry, s); },
      done() {
        for (const sp in list) {
          const L = list[sp]; if (!L.length) continue;
          const m = new THREE.InstancedMesh(G.fish(), mat(fishTex(sp), 0x6a6a8a, { spec: 0.9, rimAmt: 0.5 }), L.length);
          L.forEach((M, i) => m.setMatrixAt(i, M)); scene.add(m); this.meshes[sp] = m; this.mats[sp] = m.material;
        }
      },
    };
  }
  // ice bed for a counter
  const iceMat = () => mat(tex('ice', 256, 256, (c, w, h) => {
    c.fillStyle = '#d8eef8'; c.fillRect(0, 0, w, h);
    for (let i = 0; i < 500; i++) { c.fillStyle = Math.random() < 0.5 ? '#ffffff' : '#a9d6ee'; const s = rnd(3, 10); c.fillRect(rnd(0, w), rnd(0, h), s, s * rnd(0.5, 1.2)); }
  }), 0x8aa8c8, { spec: 0.6 });


  // ---------------------------------------------------------------- ground: seamless high-res tiles (one tile = 4 m)
  function groundTex(kind) {
    return tex('ground' + kind, 1024, 1024, (c, w, h) => {
      const P = {
        asphalt: { base: '#4c4852', lo: '#3a3640', hi: '#6a6670', agg: 0.9, joints: 0, stones: 0 },
        plaza: { base: '#6a5f66', lo: '#564c54', hi: '#827880', agg: 0.5, joints: 0, stones: 128 },
        concrete: { base: '#76868e', lo: '#62727a', hi: '#90a0a8', agg: 0.4, joints: 512, stones: 0, wet: 1 },
        bay: { base: '#6c6860', lo: '#5a564e', hi: '#86827a', agg: 0.6, joints: 512, stones: 0 },
        auction: { base: '#8c9294', lo: '#7a8082', hi: '#a4aaac', agg: 0.35, joints: 256, stones: 0, wet: 0.6 },
        roof: { base: '#5e5a5c', lo: '#4a4648', hi: '#76727a', agg: 1.0, joints: 341, stones: 0 },
        roofG: { base: '#4e6058', lo: '#3c4c44', hi: '#64786e', agg: 0.6, joints: 256, stones: 0 },
      }[kind];
      const wrap = (f) => { for (const ox of [-w, 0, w]) for (const oy of [-h, 0, h]) { c.save(); c.translate(ox, oy); f(); c.restore(); } };
      c.fillStyle = P.base; c.fillRect(0, 0, w, h);
      // paving stones with gaps and per-stone tone
      if (P.stones) for (let y = 0; y < h; y += P.stones) for (let x = 0; x < w; x += P.stones) {
        const off = (y / P.stones) % 2 ? P.stones / 2 : 0;
        c.fillStyle = Math.random() < 0.5 ? P.lo : P.hi; c.globalAlpha = 0.25 + Math.random() * 0.25; c.fillRect((x + off) % w, y, P.stones - 6, P.stones - 6); c.globalAlpha = 1;
        c.fillStyle = 'rgba(20,14,22,0.55)'; c.fillRect((x + off + P.stones - 6) % w, y, 6, P.stones); c.fillRect((x + off) % w, y + P.stones - 6, P.stones, 6);
      }
      // cel-style tone patches: a few hard-edged, flat shapes one step darker or lighter (no soft blotches)
      const blob = (x, y, r) => { const ph = Math.random() * 6, ph2 = Math.random() * 6; c.beginPath(); for (let k = 0; k <= 40; k++) { const t = k / 40 * Math.PI * 2, rr = r * (0.86 + 0.1 * Math.sin(t * 2 + ph) + 0.05 * Math.sin(t * 3 + ph2)); c.lineTo(x + Math.cos(t) * rr, y + Math.sin(t) * rr * 0.72); } c.fill(); }; // smooth, low-frequency edges
      for (let i = 0; i < 4; i++) { const x = Math.random() * w, y = Math.random() * h, r = rnd(160, 300), dark = i % 3 !== 0; wrap(() => { c.fillStyle = dark ? P.lo : P.hi; c.globalAlpha = dark ? 0.12 : 0.08; blob(x, y, r); c.globalAlpha = 1; }); }
      // stains: small flat darker shapes
      // (no small stains here: on a 4 m tile they repeat into a grid of spots; the floor's big overlay carries the grime)
      // wet patches: a crisp lighter shape with a sharp highlight stroke (hosed-down floor)
      if (P.wet) for (let i = 0; i < 0; i++) { const x = Math.random() * w, y = Math.random() * h, r = rnd(50, 120); wrap(() => { c.fillStyle = 'rgba(190,220,240,' + 0.07 * P.wet + ')'; blob(x, y, r); c.strokeStyle = 'rgba(235,248,255,' + 0.5 * P.wet + ')'; c.lineWidth = 3; c.beginPath(); c.moveTo(x - r * 0.4, y - r * 0.15); c.lineTo(x + r * 0.15, y - r * 0.35); c.stroke(); }); }
      // aggregate: sparse crisp dots
      const n = Math.round(1200 * P.agg);
      for (let i = 0; i < n; i++) { c.globalAlpha = 0.5; c.fillStyle = Math.random() < 0.6 ? P.lo : P.hi; const sz = Math.random() < 0.85 ? 1 : 2; c.fillRect(Math.round(Math.random() * w), Math.round(Math.random() * h), sz, sz); } c.globalAlpha = 1;
      // cracks
      c.strokeStyle = 'rgba(16,12,20,0.32)'; c.lineCap = 'butt'; c.lineJoin = 'miter';
      for (let i = 0; i < 3; i++) { // hairline cracks: long, mostly straight, kinked (concrete cracks, not squiggles)
        let x = Math.random() * w, y = Math.random() * h; const a0 = Math.random() * 6.28, pts = [[x, y]];
        for (let k = 0; k < 9; k++) { const a = a0 + rnd(-0.35, 0.35); const l = rnd(14, 34); x += Math.cos(a) * l; y += Math.sin(a) * l; pts.push([x, y]); }
        wrap(() => { c.lineWidth = 1.2; c.beginPath(); pts.forEach(([px, py], k) => (k ? c.lineTo(px, py) : c.moveTo(px, py))); c.stroke(); });
      }
      // expansion joints (cut lines with a lit edge)
      if (P.joints) for (let t = 0; t < w; t += P.joints) {
        c.fillStyle = 'rgba(20,24,30,0.6)'; c.fillRect(t, 0, 3, h); c.fillRect(0, t, w, 3);
        c.fillStyle = 'rgba(255,255,255,0.12)'; c.fillRect(t + 3, 0, 2, h); c.fillRect(0, t + 3, w, 2);
      }
    });
  }
  function groundMat(kind, w, d) {
    const t = groundTex(kind).clone(); t.needsUpdate = true;
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(w / 4, d / 4); t.anisotropy = 8;
    return new THREE.MeshBasicMaterial({ map: t });
  }

  // ---------------------------------------------------------------- instanced batches (many small things, one draw)
  function batch(scene, geo, material, th) {
    const L = [];
    const B = { meshes: [], add(x, y, z, rx, ry, rz, sx, sy, sz) { L.push(M4(x, y, z, rx, ry, rz, sx, sy, sz)); return L.length - 1; },
      at(i) { return L[i]; },
      done() { if (!L.length) return; const m = new THREE.InstancedMesh(geo, material, L.length); L.forEach((M, i) => m.setMatrixAt(i, M)); scene.add(m); B.meshes.push(m);
        if (th) { const o = new THREE.InstancedMesh(geo, W.mesh(geo, material, th).children[0].material, L.length); L.forEach((M, i) => o.setMatrixAt(i, M)); scene.add(o); B.meshes.push(o); } } };
    return B;
  }

  // ---------------------------------------------------------------- a fishmonger's stall
  // counter of dark planks with a steel rim, a tilted ice bed facing the aisle, sections of goods, price cards
  const plankTex = () => tex('planks', 256, 256, (c, w, h) => {
    for (let i = 0; i < 8; i++) { wood(c, i * 32, 0, 32, h, ['#5a3a22', '#4e321e', '#63402a', '#553620'][i % 4], '#2a1a0e', i); c.fillStyle = 'rgba(0,0,0,0.5)'; c.fillRect(i * 32, 0, 2, h); }
    c.fillStyle = 'rgba(0,0,0,0.35)'; c.fillRect(0, h - 26, w, 26);
  });
  const cardTex = (txt, price) => tex('card' + txt + price, 128, 96, (c, w, h) => {
    c.fillStyle = '#fbf6e8'; c.fillRect(0, 0, w, h); c.strokeStyle = '#c8231d'; c.lineWidth = 5; c.strokeRect(3, 3, w - 6, h - 6);
    c.fillStyle = '#1a1014'; c.textAlign = 'center'; c.font = '34px "Dela Gothic One", sans-serif'; c.fillText(txt, w / 2, 42);
    c.fillStyle = '#c8231d'; c.font = '800 28px "Barlow Condensed", sans-serif'; c.fillText('¥' + price, w / 2, 82);
  });
  let SB = null;
  function stallKit(scene) {
    if (SB) return SB;
    const shell = batch(scene, new THREE.SphereGeometry(1, 8, 6), S.toon(0x2a2430, { shade: 0x0e0a12, spec: 0.6, rimAmt: 0.5 }), 0);
    const shrimp = batch(scene, new THREE.TorusGeometry(0.05, 0.022, 5, 8, Math.PI * 1.2), S.toon(0xf07a4a, { shade: 0x8a3020, spec: 0.4 }), 0);
    const saku = batch(scene, new THREE.BoxGeometry(1, 1, 1), S.toon(0xd8323a, { shade: 0x7a1020, spec: 0.7, rimAmt: 0.4 }), 0.008);
    const tray = batch(scene, new THREE.BoxGeometry(1, 1, 1), S.toon(0xf4f4f0, { shade: 0xa0a8b0 }), 0.008);
    const tako = batch(scene, new THREE.SphereGeometry(1, 10, 8), S.toon(0xb83a4a, { shade: 0x5a1222, spec: 0.5, rimAmt: 0.5 }), 0.01);
    SB = { shell, shrimp, saku, tray, tako, done() { for (const k of ['shell', 'shrimp', 'saku', 'tray', 'tako']) SB[k].done(); SB = null; } };
    return SB;
  }
  function stall(g0, fishes, x, z0, z1, sd, k, table) {
    const len = Math.abs(z1 - z0), zc = (z0 + z1) / 2, za = Math.min(z0, z1), K0 = stallKit(g0);
    const g = new THREE.Group(); g0.add(g);
    const fishes0 = fishes;
    const rec = { group: g, inst: [], fish: [], fishes: fishes0 }; // everything this stall owns (a charge smashes the lot)
    const kit = {}; for (const n of ['shell', 'shrimp', 'saku', 'tray', 'tako']) kit[n] = { add: (...a) => rec.inst.push([K0[n], K0[n].add(...a), n]) };
    fishes = { add: (...a) => { const r = fishes0.add(...a); rec.fish.push(r); return r; } };
    const steel = S.toon(0xb8c2cc, { shade: 0x4a5662, spec: 0.7, rimAmt: 0.5 });
    if (!table) { const body = W.mesh(new THREE.BoxGeometry(1.7, 0.86, len), mat(plankTex(), 0x6a5060), 0.025); body.position.set(x, 0.43, zc); g.add(body); }
    else { // an open stainless table: legs, a lower shelf stacked with foam boxes
      const parts = [], n = Math.max(2, Math.round(len / 2) + 1);
      for (let i = 0; i < n; i++) for (const dx of [-0.75, 0.75]) parts.push({ geo: new THREE.BoxGeometry(0.06, 0.84, 0.06), m: M4(x + dx, 0.42, za + 0.1 + i * (len - 0.2) / (n - 1)) });
      parts.push({ geo: new THREE.BoxGeometry(1.56, 0.04, len - 0.1), m: M4(x, 0.2, zc) });
      g.add(W.mesh(merge(parts), S.toon(0x8a96a2, { shade: 0x2e3842, spec: 0.5 }), 0.01));
      for (let i = 0; i < Math.floor(len / 0.75); i++) { const b = prop('foam'); b.children.forEach((c2) => { if (c2.rotation.x) c2.visible = false; }); b.position.set(x + (i % 2 ? 0.35 : -0.35), 0.22, za + 0.4 + i * 0.75); b.rotation.y = Math.PI / 2; g.add(b); }
    }
    const rim = W.mesh(new THREE.BoxGeometry(1.8, 0.07, len + 0.08), steel, 0.012); rim.position.set(x, 0.88, zc); g.add(rim);
    // tilted ice bed: high at the back, low at the aisle (flat on a table you can walk round)
    const tilt = table ? 0 : sd * 0.16, ice = W.mesh(new THREE.BoxGeometry(1.55, 0.16, len - 0.16), iceMat(), 0.0); ice.position.set(x, 0.99, zc); ice.rotation.z = tilt; g.add(ice);
    const yAt = (dx) => 1.07 + Math.tan(tilt) * dx; // surface height, dx = offset across the counter
    // goods, in sections along the counter
    const secs = Math.max(1, Math.round(len / 1.0)), sl = len / secs;
    const kinds = ['fish', 'fish', 'saku', 'shell', 'fish', 'tako', 'shrimp'];
    for (let s = 0; s < secs; s++) {
      const kind = kinds[(s + k * 3) % kinds.length], zs = za + (s + 0.5) * sl;
      if (kind === 'fish') {
        const sp = ['maguro', 'tai', 'saba', 'sake'][(s + k) % 4], n = Math.max(2, Math.floor(sl / 0.2));
        for (let i = 0; i < n; i++) for (const dx of [-0.42, 0.0, 0.42]) {
          const zz = za + s * sl + (i + 0.5) * sl / n;
          fishes.add(sp, x + dx, yAt(dx) + 0.02, zz, (table ? (dx < 0 ? 1 : -1) : -sd) * Math.PI / 2 + rnd(-0.08, 0.08), 0.26);
        }
      } else {
        // a white tray per section
        kit.tray.add(x, yAt(0) + 0.02, zs, 0, 0, tilt, 1.2, 0.05, sl * 0.8);
        if (kind === 'saku') for (let i = 0; i < 8; i++) kit.saku.add(x + rnd(-0.45, 0.45), yAt(0) + 0.08, zs + rnd(-0.32, 0.32) * sl, 0, rnd(-0.3, 0.3), tilt, 0.26, 0.07, 0.11);
        if (kind === 'shell') for (let i = 0; i < 36; i++) { const dx = rnd(-0.5, 0.5); kit.shell.add(x + dx, yAt(dx) + 0.07, zs + rnd(-0.36, 0.36) * sl, 0, rnd(0, 6), 0, 0.07, 0.035, 0.05); }
        if (kind === 'shrimp') for (let i = 0; i < 30; i++) { const dx = rnd(-0.5, 0.5); kit.shrimp.add(x + dx, yAt(dx) + 0.07, zs + rnd(-0.36, 0.36) * sl, Math.PI / 2, rnd(0, 6), 0, 1, 1, 1); }
        if (kind === 'tako') for (let i = 0; i < 3; i++) { const dx = -0.35 + i * 0.35; kit.tako.add(x + dx, yAt(dx) + 0.12, zs + rnd(-0.1, 0.1), 0, 0, 0, 0.17, 0.12, 0.17); for (let l = 0; l < 6; l++) { const a = l / 6 * Math.PI * 2; kit.tako.add(x + dx + Math.cos(a) * 0.2, yAt(dx) + 0.06, zs + Math.sin(a) * 0.2, 0, -a, 0, 0.12, 0.035, 0.04); } }
      }
      // a price card stuck in the ice, facing the aisle and the camera
      if (s % 2 === 0) {
        const nm = { fish: '鮮魚', saku: '鮪', shell: '貝', tako: '蛸', shrimp: '海老' }[kind], pr = [380, 580, 800, 1200, 1500][(s + k) % 5];
        const cd = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 0.22), new THREE.MeshBasicMaterial({ map: cardTex(nm, pr), side: THREE.DoubleSide }));
        const cs = table ? (s % 4 ? 1 : -1) : sd; cd.position.set(x - cs * 0.62, yAt(-cs * 0.62) + 0.2, zs + sl * 0.3); cd.rotation.set(-0.55, 0, 0); g.add(cd);
      }
    }
    return rec;
  }


  // ---------------------------------------------------------------- rooftops: the city around the market, dense enough to read as Tokyo
  // blocks: [{ x0, x1, z0, z1, h, front }] (front = x of the face toward the street, for hanging signs)
  function roofs(g, blocks) {
    const kit = {
      ac: batch(g, new THREE.BoxGeometry(1, 1, 1), S.toon(0xd4d8dc, { shade: 0x707880, spec: 0.3 }), 0.012),
      fan: batch(g, new THREE.CylinderGeometry(1, 1, 1, 14), S.toon(0x30343a, { shade: 0x101216 }), 0),
      tank: batch(g, new THREE.CylinderGeometry(1, 1, 1, 16), S.toon(0x8ab0c4, { shade: 0x34505e, spec: 0.4 }), 0.02),
      leg: batch(g, new THREE.BoxGeometry(1, 1, 1), S.toon(0x5a5e66, { shade: 0x22242a }), 0),
      hut: batch(g, new THREE.BoxGeometry(1, 1, 1), S.toon(0xb8aea4, { shade: 0x5a4e48 }), 0.02),
      pipe: batch(g, new THREE.CylinderGeometry(1, 1, 1, 8), S.toon(0x9a9ea6, { shade: 0x3e424a, spec: 0.5 }), 0.008),
      dish: batch(g, new THREE.SphereGeometry(1, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2.4), S.toon(0xeeeeea, { shade: 0x8a8a92 }), 0.01),
      green: batch(g, new THREE.SphereGeometry(1, 8, 6), S.toon(0x4a8a4a, { shade: 0x1e3e24 }), 0.01),
      wall: batch(g, new THREE.BoxGeometry(1, 1, 1), S.toon(0x6a5e64, { shade: 0x2c2228 }), 0.02),
      solar: batch(g, new THREE.BoxGeometry(1, 1, 1), S.toon(0x2a3a6a, { shade: 0x101830, spec: 0.9 }), 0.006),
    };
    const neon = [['居酒屋', '#ff3a6a'], ['カラオケ', '#46f2ff'], ['寿司', '#ffd23a'], ['パチンコ', '#ff8a2a'], ['薬', '#7aff7a'], ['酒', '#ff5a5a'], ['ホテル', '#c87aff'], ['定食', '#ffffff'], ['焼鳥', '#ffb03a'], ['麻雀', '#5ab0ff']];
    const signTex = (txt, col) => tex('neon' + txt + col, 96, 384, (c, w, h) => {
      c.fillStyle = '#16101a'; c.fillRect(0, 0, w, h); c.strokeStyle = col; c.lineWidth = 6; c.strokeRect(5, 5, w - 10, h - 10);
      c.shadowColor = col; c.shadowBlur = 14; c.fillStyle = col; c.textAlign = 'center'; c.textBaseline = 'middle';
      const ch = [...txt], fs = Math.min(70, (h - 40) / ch.length); c.font = fs + 'px "Dela Gothic One", sans-serif';
      ch.forEach((k, i) => c.fillText(k, w / 2, 20 + fs / 2 + i * fs + ((h - 40) - fs * ch.length) / 2));
    });
    const board = (txt, sub, col) => tex('bb' + txt, 512, 192, (c, w, h) => {
      const gr = c.createLinearGradient(0, 0, w, h); gr.addColorStop(0, col); gr.addColorStop(1, '#1a1020'); c.fillStyle = gr; c.fillRect(0, 0, w, h);
      c.strokeStyle = 'rgba(255,255,255,0.8)'; c.lineWidth = 8; c.strokeRect(6, 6, w - 12, h - 12);
      c.fillStyle = '#fff'; c.textAlign = 'center'; c.font = '86px "Dela Gothic One", sans-serif'; c.fillText(txt, w / 2, 112); c.font = '800 30px "Barlow Condensed", sans-serif'; c.fillText(sub, w / 2, 166);
    });
    const boards = [['魚河岸', 'UOGASHI MARKET', '#c8231d'], ['ラーメン', 'NOODLE KING', '#e8572a'], ['飲料', 'COLD DRINKS', '#2a6ad0'], ['築地丸', 'MARUTOYO GROUP', '#2e9e6a'], ['銭湯', 'BATH HOUSE', '#7a4ab0']];
    let ni = 0, bi = 0;
    for (const B of blocks) {
      const w = B.x1 - B.x0, d = B.z0 - B.z1, cx = (B.x0 + B.x1) / 2, cz = (B.z0 + B.z1) / 2, h = B.h;
      // roof surface and a parapet round the edge
      const rf = new THREE.Mesh(new THREE.PlaneGeometry(w, d).rotateX(-Math.PI / 2), groundMat(Math.random() < 0.25 ? 'roofG' : 'roof', w, d)); rf.position.set(cx, h + 0.005, cz); g.add(rf);
      for (const [px, pz, sx, sz] of [[cx, B.z0 - 0.08, w, 0.16], [cx, B.z1 + 0.08, w, 0.16], [B.x0 + 0.08, cz, 0.16, d], [B.x1 - 0.08, cz, 0.16, d]]) kit.wall.add(px, h + 0.22, pz, 0, 0, 0, sx, 0.44, sz);
      const r = (a, b) => a + Math.random() * (b - a), inX = () => r(B.x0 + 0.9, B.x1 - 0.9), inZ = () => r(B.z1 + 0.9, B.z0 - 0.9);
      // AC condenser clusters (with fans on top)
      const nac = Math.max(2, Math.round(w * d / 9));
      for (let i = 0; i < nac; i++) { const x = inX(), z = inZ(), ry = Math.random() < 0.5 ? 0 : Math.PI / 2; kit.ac.add(x, h + 0.33, z, 0, ry, 0, 0.95, 0.66, 0.62); kit.fan.add(x, h + 0.67, z, 0, 0, 0, 0.26, 0.02, 0.26); if (Math.random() < 0.6) kit.pipe.add(x + 0.5, h + 0.06, z, 0, 0, Math.PI / 2, 0.035, 1.2, 0.035); }
      // a water tank on a steel stand
      if (w * d > 14 && Math.random() < 0.8) { const x = inX(), z = inZ(); for (const [ox, oz] of [[-0.5, -0.5], [0.5, -0.5], [-0.5, 0.5], [0.5, 0.5]]) kit.leg.add(x + ox, h + 0.5, z + oz, 0, 0, 0, 0.08, 1.0, 0.08); kit.tank.add(x, h + 1.55, z, 0, 0, 0, 0.75, 1.1, 0.75); }
      // a stairwell hut with a door
      if (w * d > 18 && Math.random() < 0.7) { const x = inX(), z = inZ(); kit.hut.add(x, h + 1.1, z, 0, 0, 0, 1.6, 2.2, 1.4); }
      // vents, a satellite dish, potted greenery or solar panels
      for (let i = 0; i < 3; i++) kit.pipe.add(inX(), h + 0.45, inZ(), 0, 0, 0, 0.09, 0.9, 0.09);
      if (Math.random() < 0.5) { const x = inX(), z = inZ(); kit.dish.add(x, h + 0.9, z, -0.9, r(0, 6), 0, 0.42, 0.42, 0.42); kit.leg.add(x, h + 0.45, z, 0, 0, 0, 0.05, 0.9, 0.05); }
      if (Math.random() < 0.45) for (let i = 0; i < 5; i++) kit.green.add(r(B.x0 + 0.4, B.x1 - 0.4), h + 0.25, B.z1 + 0.4 + i * 0.6, 0, 0, 0, 0.3, 0.28, 0.3);
      if (w * d > 24 && Math.random() < 0.4) { const x = inX(), z = inZ(); for (let i = 0; i < 3; i++) kit.solar.add(x, h + 0.35, z - 0.9 + i * 0.9, -0.35, 0, 0, 1.6, 0.05, 0.8); }
      // a billboard on the roof, angled up toward the camera
      if (Math.random() < 0.35 && w > 4) { const [t, sb, col] = boards[bi++ % boards.length]; const m = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 1.2), new THREE.MeshBasicMaterial({ map: board(t, sb, col), side: THREE.DoubleSide })); m.position.set(cx, h + 1.9, B.z1 + 0.6); m.rotation.set(-0.45, 0, 0); g.add(m); kit.leg.add(cx - 1.2, h + 0.7, B.z1 + 0.7, 0, 0, 0, 0.08, 1.4, 0.08); kit.leg.add(cx + 1.2, h + 0.7, B.z1 + 0.7, 0, 0, 0, 0.08, 1.4, 0.08); }
      // vertical neon signs hanging off the street face, glowing
      if (B.front !== undefined) for (let z = B.z0 - 1.2; z > B.z1 + 0.8; z -= r(2.6, 4.2)) {
        if (Math.random() < 0.3) continue;
        const [t, col] = neon[ni++ % neon.length], sx = B.front + Math.sign(B.front) * -0.05;
        const m = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 2.4), new THREE.MeshBasicMaterial({ map: signTex(t, col), side: THREE.DoubleSide }));
        m.position.set(sx - Math.sign(B.front) * 0.32, h - 0.6, z); m.rotation.set(-0.5, 0, 0); g.add(m);
        const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: S.CampMap.glowTex(), color: new THREE.Color(col), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.35 })); glow.scale.set(1.6, 3, 1); glow.position.copy(m.position); g.add(glow);
      }
    }
    for (const k in kit) kit[k].done();
  }


  // ---------------------------------------------------------------- facades: the walls you fight beside. Flat cel colours, crisp shapes.
  function facadeTex(style, v) {
    return tex('fac' + style + v, 256, 224, (c, w, h) => {
      const R = (a, b) => a + ((v * 9301 + 49297) % 233280) / 233280 * (b - a); // deterministic per variant
      if (style === 'shop') {
        const walls = ['#8a7a6a', '#6e6a78', '#7a5a4a', '#5e6a6e', '#8a8478'], wc = walls[v % walls.length];
        c.fillStyle = wc; c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(0,0,0,0.18)'; for (let y = 8; y < h * 0.36; y += 14) c.fillRect(0, y, w, 2); // siding / tile courses
        // upper floor: two windows with frames, one with an AC unit under it
        for (const x of [36, 150]) { c.fillStyle = '#2a2c38'; c.fillRect(x, 14, 70, 44); c.fillStyle = '#5e7aa0'; c.fillRect(x + 4, 18, 62, 36); c.fillStyle = '#9ab8d8'; c.fillRect(x + 6, 20, 18, 32); c.fillStyle = '#2a2c38'; c.fillRect(x + 34, 18, 3, 36); }
        if (v % 2) { c.fillStyle = '#d4d8dc'; c.fillRect(150, 62, 54, 22); c.fillStyle = '#30343a'; c.beginPath(); c.arc(166, 73, 8, 0, 7); c.fill(); }
        // shop sign band
        const sc = ['#c8231d', '#2f6fd0', '#2e9e6a', '#f2c14e', '#1a1a22'][v % 5];
        c.fillStyle = sc; c.fillRect(0, h * 0.4, w, 30); c.fillStyle = sc === '#f2c14e' ? '#1a1014' : '#fff8ec';
        c.font = '22px "Dela Gothic One", sans-serif'; c.textAlign = 'center'; c.fillText(['鮮魚店', '乾物', '刃物', '海苔', '玉子焼', '茶', '漬物', '昆布'][v % 8], w / 2, h * 0.4 + 23);
        // ground floor: shutter, lit shop window, or a door
        const gy = h * 0.4 + 30, gh = h - gy;
        const kind = v % 3;
        if (kind === 0) { c.fillStyle = '#9aa2aa'; c.fillRect(10, gy, w - 20, gh); c.fillStyle = '#6a7278'; for (let y = gy + 4; y < h; y += 7) c.fillRect(10, y, w - 20, 2); c.fillStyle = '#2a2c32'; c.fillRect(10, h - 6, w - 20, 6); }
        else if (kind === 1) { c.fillStyle = '#2a1e18'; c.fillRect(10, gy, w - 20, gh); c.fillStyle = '#f2c98a'; c.fillRect(16, gy + 6, w - 32, gh - 26); c.fillStyle = '#c88a4a'; for (let x = 24; x < w - 30; x += 34) c.fillRect(x, gy + gh * 0.45, 22, 14); c.fillStyle = '#7a1a14'; for (let i = 0; i < 5; i++) c.fillRect(20 + i * 44, gy + 6, 38, 26); }
        else { c.fillStyle = '#4a3a30'; c.fillRect(10, gy, w - 20, gh); c.fillStyle = '#c8d8e4'; c.fillRect(30, gy + 10, 70, gh - 16); c.fillRect(156, gy + 10, 70, gh - 16); c.fillStyle = '#4a3a30'; c.fillRect(64, gy + 10, 3, gh - 16); c.fillRect(190, gy + 10, 3, gh - 16); }
        c.fillStyle = '#3a3a42'; c.fillRect(w - 10, 0, 6, h); // drain pipe
      } else if (style === 'hall') {
        c.fillStyle = v % 2 ? '#7a8a96' : '#6e7e8a'; c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(0,0,0,0.16)'; for (let x = 0; x < w; x += 16) c.fillRect(x, 0, 3, h); // corrugation
        c.fillStyle = '#4a5662'; c.fillRect(0, h * 0.62, w, 10); c.fillStyle = '#e8c547'; c.fillRect(0, h - 14, w, 14);
        if (v % 3 === 0) { c.fillStyle = '#c8231d'; c.fillRect(40, h * 0.3, 40, 54); c.fillStyle = '#fff'; c.font = '800 12px "Barlow Condensed"'; c.fillText('消火栓', 44, h * 0.3 + 30); }
        if (v % 3 === 1) { c.fillStyle = '#c8ccd0'; c.fillRect(150, h * 0.25, 60, 70); c.fillStyle = '#30343a'; c.fillRect(158, h * 0.25 + 10, 44, 6); }
        c.fillStyle = '#f6f2ea'; c.font = '28px "Dela Gothic One"'; c.fillText(String(10 + v), 200, h * 0.55);
      } else if (style === 'bay') {
        c.fillStyle = '#5a626a'; c.fillRect(0, 0, w, h);
        c.fillStyle = '#9aa2a8'; c.fillRect(20, 30, w - 40, h - 30); c.fillStyle = '#7a8288'; for (let y = 34; y < h; y += 9) c.fillRect(20, y, w - 40, 3);
        c.fillStyle = '#1a1a1a'; for (let x = 0; x < w; x += 32) { c.beginPath(); c.moveTo(x, h); c.lineTo(x + 16, h); c.lineTo(x + 32, h - 16); c.lineTo(x + 16, h - 16); c.fill(); }
        c.fillStyle = '#e8c547'; c.globalCompositeOperation = 'destination-over'; c.fillRect(0, h - 16, w, 16); c.globalCompositeOperation = 'source-over';
        c.fillStyle = '#fff'; c.font = '30px "Dela Gothic One"'; c.textAlign = 'center'; c.fillText(String(v + 1), w / 2, 24);
      }
    });
  }
  // a run of facade panels along a wall face. sd: which side (the panel faces -sd * x)
  // The flat painted panel shows first; the modelled 3D module (tools/blender/facades.py -> assets/models/facades.glb)
  // replaces it as soon as that file has loaded.
  const FAC = { shop: [6, 4.0, 3.4], hall: [3, 5.0, 4.6], bay: [2, 4.0, 4.4] }; // variants, module width, module height
  function facadeModule(set, name) {
    set.cache = set.cache || {};
    if (set.cache[name] !== undefined) return set.cache[name];
    const src = set.scene.getObjectByName(name); if (!src) return (set.cache[name] = null);
    src.updateMatrixWorld(true);
    // one mesh per material: every piece sharing a material is merged, so a module costs a handful of draw calls
    const byMat = new Map(), inv = new THREE.Matrix4().copy(src.matrixWorld).invert();
    src.traverse((o) => {
      if (!o.isMesh) return;
      const geo = o.geometry.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld)).toNonIndexed();
      if (!geo.attributes.uv) geo.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(geo.attributes.position.count * 2), 2));
      if (!byMat.has(o.material)) byMat.set(o.material, []); byMat.get(o.material).push(geo);
    });
    const parts = [];
    for (const [sm, geos] of byMat) {
      const geo = new THREE.BufferGeometry();
      for (const [k, n] of [['position', 3], ['normal', 3], ['uv', 2]]) {
        const tot = geos.reduce((t, gg) => t + gg.attributes[k].count * n, 0), arr = new Float32Array(tot); let off = 0;
        for (const gg of geos) { arr.set(gg.attributes[k].array, off); off += gg.attributes[k].count * n; }
        geo.setAttribute(k, new THREE.BufferAttribute(arr, n));
      }
      const col = sm.color ? sm.color.clone().convertLinearToSRGB() : new THREE.Color(1, 1, 1);
      parts.push({ geo, mat: S.toon(col.getHex(), { shade: col.clone().multiply(new THREE.Color(0.7, 0.66, 0.76)).getHex(), map: sm.map || undefined, rimAmt: 0 }) });
    }
    return (set.cache[name] = parts);
  }
  function facade(g, x, z0, z1, h, sd, style, seg) {
    seg = seg || 4; const za = Math.min(z0, z1), len = Math.abs(z1 - z0), n = Math.max(1, Math.round(len / seg)), sl = len / n;
    const panels = [];
    for (let i = 0; i < n; i++) {
      const v = (Math.floor(Math.abs(za * 7 + i * 13 + sd * 5)) % 7);
      const m = new THREE.Mesh(new THREE.PlaneGeometry(sl, h), S.toon(0xffffff, { map: facadeTex(style, v), shade: 0x9088a0, rimAmt: 0 }));
      m.position.set(x, h / 2, za + (i + 0.5) * sl); m.rotation.y = -sd * Math.PI / 2; g.add(m); panels.push([m, v]);
    }
    S.facadeSet = S.facadeSet || new Promise((res) => new THREE.GLTFLoader().load('assets/models/facades.glb', (gl) => res({ scene: gl.scene }), undefined, () => res(null)));
    S.facadeSet.then((set) => {
      if (!set || !FAC[style]) return;
      const [nv, mw, mh] = FAC[style];
      for (const [m, v] of panels) {
        const parts = facadeModule(set, style + '_' + (v % nv)); if (!parts || !parts.length) continue;
        const grp = new THREE.Group();
        for (const p of parts) grp.add(W.mesh(p.geo, p.mat, 0)); // no ink outline: the modelled bevels carry the edges
        grp.scale.set(sl / mw, h / mh, 1); grp.position.set(m.position.x, 0, m.position.z); grp.rotation.y = -sd * Math.PI / 2;
        g.add(grp); grp.updateMatrixWorld(true); m.visible = false;
      }
    });
  }

  // ---------------------------------------------------------------- awning: curved striped canvas, scalloped valance, steel frame
  // placed along z from z0..z1, x is its back edge; sd = which side of the street (it slopes toward -sd*x)
  function awning(g, x, z0, z1, sd, c1, c2, opt) {
    opt = opt || {};
    const len = Math.abs(z1 - z0), zc = (z0 + z1) / 2, depth = opt.depth || 2.1, yb = opt.y || 2.85, drop = opt.drop || 0.55;
    const nS = Math.max(4, Math.round(len / 0.45) * 2);
    const css = (c) => '#' + new THREE.Color(c).getHexString();
    // canvas: a grid (along the street × out from the wall), convex profile
    const NU = 8, NZ = 2, pos = [], uv = [], idx = [];
    for (let i = 0; i <= NU; i++) for (let j = 0; j <= NZ; j++) {
      const u = i / NU, zz = -len / 2 + (j / NZ) * len;
      pos.push(-sd * u * depth, yb - drop * u * u, zz); uv.push(j / NZ, u);
    }
    for (let i = 0; i < NU; i++) for (let j = 0; j < NZ; j++) { const a = i * (NZ + 1) + j, b = a + 1, c = a + NZ + 1, d = c + 1; idx.push(a, c, b, b, c, d); }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); geo.setIndex(idx); geo.computeVertexNormals();
    const nrm = geo.attributes.normal; if (nrm.getY(0) < 0) for (let i = 0; i < nrm.count; i++) nrm.setXYZ(i, -nrm.getX(i), -nrm.getY(i), -nrm.getZ(i));
    const cm = mat(stripeTex(css(c1), css(c2), nS), 0x806c88, { rimAmt: 0.25 }); cm.side = THREE.DoubleSide;
    const can = new THREE.Mesh(geo, cm); can.position.set(x, 0, zc); g.add(can);
    // valance: hangs from the front edge, stripes line up, scalloped hem
    const fx = x - sd * depth, fy = yb - drop;
    const vm = mat(valanceTex(css(c1), css(c2), nS), 0x806c88, { rimAmt: 0.2 }); vm.side = THREE.DoubleSide; vm.transparent = false;
    vm.fragmentShader = vm.fragmentShader.replace('vec3 tx = uHasMap > 0.5 ? texture2D(uMap, vUv).rgb : vec3(1.0);', 'vec4 t4 = texture2D(uMap, vUv); if (t4.a < 0.5) discard; vec3 tx = t4.rgb;');
    const val = new THREE.Mesh(new THREE.PlaneGeometry(len, 0.3), vm); val.rotation.y = Math.PI / 2; val.position.set(fx, fy - 0.15, zc); g.add(val);
    // steel frame: front bar and diagonal arms back to the wall
    const steel = S.toon(0x6a6e78, { shade: 0x22242c, spec: 0.5 });
    const bar = W.mesh(new THREE.CylinderGeometry(0.025, 0.025, len, 6), steel, 0.01); bar.rotation.x = Math.PI / 2; bar.position.set(fx, fy + 0.01, zc); g.add(bar);
    return { fx, fy };
  }

  S.CampArt = { roofs, facade,
    prop, awning, fishBatch, iceMat, merge, M4, tex, mat, groundMat, batch, stall, stallKit, fishGeo: () => G.fish() };
})();
