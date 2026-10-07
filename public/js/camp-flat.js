'use strict';
// The campaign in the FLAT look (flat.js): soft sun with real shadows, one master material, pale pastel colours,
// and the first street (z -9 .. -31) rebuilt from the Blender kit (assets/models/street_a.glb). The rest of the
// market keeps its layout and is converted to the same material and palette until it gets its own rebuild.
(function () {
  const REGION = { x0: -12, x1: 12, z0: -31.2, z1: -8.6 };          // the rebuilt street
  const DROP = /^(CORNER_Market|BLD_Backdrop_0[89]|BLD_Backdrop_10|PROP_(?!Table))/;   // the test's closed end, and props the game spawns itself
  const PROP_SWAP = { crate: 'PROP_Crate_K', bin: 'PROP_Bin_A', bucket: 'PROP_Bucket_A', chair: 'PROP_Chair_A' };
  let seg = null, protos = null;
  const ready = new Promise((res) => {
    if (!THREE.GLTFLoader) return res(null);
    new THREE.GLTFLoader().load('assets/models/street_a.glb', (g) => { seg = g.scene; prep(); res(seg); }, undefined, () => res(null));
  });
  // the approved palette tweaks (option 2): paler warm street greys, soft grey-violet darks instead of near-black
  const RECOLOR = { 0: '#4d4756', 1: '#524b5a', 2: '#b3aba2', 3: '#bdb5ab', 4: '#a0978e', 8: '#cbbfb1', 9: '#b3a698' };
  function recolor(tex) {
    const im = tex.image; if (!im || !im.width) return;
    const cv = document.createElement('canvas'); cv.width = im.width; cv.height = im.height;
    const c = cv.getContext('2d'); c.drawImage(im, 0, 0);
    const cw = im.width / 8, ch = im.height / 8;                                  // 8 x 8 swatches, swatch 0 in the bottom-left
    for (const [i, col] of Object.entries(RECOLOR)) { c.fillStyle = col; c.fillRect((i % 8) * cw, (7 - Math.floor(i / 8)) * ch, cw, ch); }
    tex.image = cv; tex.needsUpdate = true;
  }
  function prep() {
    const flatOf = new Map(), done = new Set();
    const conv = (m) => {
      if (flatOf.has(m)) return flatOf.get(m);
      let f;
      if (m.map) { if (!done.has(m.map)) { done.add(m.map); recolor(m.map); } m.map.encoding = THREE.LinearEncoding; m.map.needsUpdate = true; f = S.Flat.mat(0xffffff, { map: m.map, side: m.side }); }
      else f = S.Flat.mat(m.color.clone().convertLinearToSRGB(), { side: m.side });
      flatOf.set(m, f); return f;
    };
    seg.traverse((o) => {
      if (!o.isMesh) return;
      o.material = Array.isArray(o.material) ? o.material.map(conv) : conv(o.material);
      o.castShadow = true; o.receiveShadow = true;
      if (/^ROAD_/.test(rootName(o))) o.castShadow = false;
    });
    // the kit's props become the game's props (one look for the whole market)
    protos = {};
    for (const [type, name] of Object.entries(PROP_SWAP)) {
      const r = seg.children.find((c) => c.name === name); if (!r) continue;
      const p = r.clone(); p.position.set(0, 0, 0); p.rotation.set(0, 0, 0); p.updateMatrix(); protos[type] = p;
    }
    const pud = seg.children.find((c) => c.name === 'ROAD_Puddle_A');
    if (pud) { const q = pud.clone(), bb = new THREE.Box3().setFromObject(q), c = bb.getCenter(new THREE.Vector3()), sz = bb.getSize(new THREE.Vector3());
      const w = new THREE.Group(); q.position.sub(c); q.position.y = 0; w.add(q); w.userData.size = sz; protos.puddle = w; }
    for (const c of seg.children.slice()) if (DROP.test(c.name)) seg.remove(c);
    const gnd = seg.children.find((c) => c.name === 'ROAD_Ground');
    if (gnd) { gnd.position.y -= 0.03; gnd.traverse((o) => { if (o.isMesh) o.material = S.Flat.mat(0xd3c7b5); }); }   // pale paving, under the old floors where they still are
    seg.position.y = 0.012;                                                                                    // over them inside the street
  }
  // a texture's average colour (the floor as one flat colour)
  function avgColour(tex) {
    const im = tex.image, c = new THREE.Color(0.7, 0.7, 0.7); if (!im || !im.width) return c;
    const cv = document.createElement('canvas'); cv.width = cv.height = 8; const x = cv.getContext('2d'); x.drawImage(im, 0, 0, 8, 8);
    const d = x.getImageData(0, 0, 8, 8).data; let r = 0, g = 0, b = 0;
    for (let i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; b += d[i + 2]; }
    return c.setRGB(r / 64 / 255, g / 64 / 255, b / 64 / 255);
  }
  function rootName(o) { while (o.parent && o.parent.parent) o = o.parent; return o.name || ''; }

  // ---------------------------------------------------------------- set up a campaign run
  function setup(camp) {
    const sc = camp.scene, map = camp.map, R = camp.R.r;
    camp.flat = { lights: S.Flat.lights(sc, { r: 22 }), seen: 0 };
    R.shadowMap.enabled = true; R.shadowMap.type = THREE.PCFSoftShadowMap; R.localClippingEnabled = true;
    const vg = document.getElementById('vignette'); if (vg) vg.style.display = 'none';   // no dark corners: a bright, clean frame
    sc.background = new THREE.Color(0xcfe0ee); sc.fog = new THREE.Fog(0xdfe4ee, 34, 95);
    // the rebuilt street: its stalls do not come apart (they are scenery now); its puddles are where the kit has them
    const inR = (x, z) => x > REGION.x0 && x < REGION.x1 && z > REGION.z0 && z < REGION.z1;
    for (let i = map.breakables.length - 1; i >= 0; i--) { const b = map.breakables[i]; if (b.kind !== 'vend' && inR(b.x, b.z)) { map.breakables.splice(i, 1); b.w.brk = null; } }
    map.puddles = map.puddles.filter((p) => !inR(p.x, p.z)).concat([{ x: 1.55, z: -19.25, r: 1.35, sx: 1.9 }, { x: 2.05, z: -26.5, r: 1.05, sx: 1.45 }, { x: -9.15, z: -24.85, r: 0.9, sx: 0.95 }]);
    // the kit's corner stalls at the street's mouth stand in the old plaza: give them their solid fronts
    for (const sd of [-1, 1]) map.walls.push({ x0: sd > 0 ? 4.7 : -9.4, x1: sd > 0 ? 9.4 : -4.7, z0: -13.5, z1: -4.6 });
    const go = () => {
      if (!camp.scene) return;
      hideOld(camp, inR);
      if (seg && seg.parent !== sc) { sc.add(seg); seg.traverse((o) => { o.matrixAutoUpdate = true; }); seg.updateMatrixWorld(true); }
      S.Flat.convert(sc, { pastel: 0.85 });
      if (protos && camp.props) for (const p of camp.props) swapProp(camp, p);
    };
    go();
    Promise.all([ready, S.facadeSet || Promise.resolve()]).then(() => setTimeout(go, 0));
    // the market hall / bay / auction lighting rigs are not part of this look
    for (const d of map.decor) if (d.kind === 'vglow' || d.kind === 'tube' || d.kind === 'puddle') { d.m.visible = false; }
    // floors: the painted base a lot paler; the grime layer over it goes (flat colour, no dirt)
    map.group.traverse((o) => {
      const m = o.material; if (!o.isMesh || !m || !m.isMeshBasicMaterial || !m.map || o.geometry.type !== 'PlaneGeometry') return;
      if (m.blending === THREE.AdditiveBlending) { o.visible = false; return; }                          // light pools: no glow on the floor
      const flatOnFloor = Math.abs(o.geometry.attributes.normal.getY(0)) > 0.9 && o.position.y < 0.05;
      if (!flatOnFloor) return;
      if (m.transparent && Math.abs(o.position.y % 1 - 0.002) < 0.0015 && m.blending !== THREE.AdditiveBlending) o.visible = false;
      else if (!m.transparent) { o.material = S.Flat.mat(S.Flat.pastel(avgColour(m.map), 0.8)); o.receiveShadow = true; }   // one flat colour
    });
    // wet patches outside the rebuilt street: the kit's flat pale-blue puddle
    const addPuddles = () => {
      if (!protos || !protos.puddle || camp.flatPuddles) return; camp.flatPuddles = true;
      const sz = protos.puddle.userData.size;
      for (const p of map.puddles) {
        if (inR(p.x, p.z)) continue;
        const m = protos.puddle.clone(); m.position.set(p.x, 0.013, p.z); m.scale.set(2 * p.r * p.sx / sz.x, 1, 2 * p.r / sz.z); sc.add(m);
      }
    };
    addPuddles(); ready.then(() => camp.scene && addPuddles());
    // behind the start line: rooftops and billboards there sit between the camera and the player (they hid him)
    { const bb = new THREE.Box3(); map.group.updateMatrixWorld(true);
      map.group.traverse((o) => { if (!o.isMesh || o.isInstancedMesh) return; bb.setFromObject(o); if (!bb.isEmpty() && bb.min.z > 4.4 && bb.max.y > 3) o.visible = false; }); }
    // instanced scenery (fish on ice, stall kit) inside the rebuilt street: those instances go
    const zero = new THREE.Matrix4().makeScale(0, 0, 0), M = new THREE.Matrix4(), P = new THREE.Vector3();
    sc.traverse((o) => {
      if (!o.isInstancedMesh) return;
      let n = 0;
      for (let i = 0; i < o.count; i++) { o.getMatrixAt(i, M); P.setFromMatrixPosition(M); if (inR(P.x, P.z)) { o.setMatrixAt(i, zero); n++; } }
      if (n) { o.instanceMatrix.needsUpdate = true; o.computeBoundingSphere && o.computeBoundingSphere(); }
    });
  }
  // old scenery inside the rebuilt street goes; long pieces that run on past it are cut at its end
  const clip = [new THREE.Plane(new THREE.Vector3(0, 0, -1), REGION.z0 - 0.3)];   // keeps z < -31.5
  function hideOld(camp, inR) {
    const g = camp.map.group, bb = new THREE.Box3(), c = new THREE.Vector3(), sz = new THREE.Vector3();
    g.updateMatrixWorld(true);
    for (const o of g.children) {
      if (o.userData.flatRegion) continue;
      bb.setFromObject(o); if (bb.isEmpty()) continue;
      bb.getCenter(c); bb.getSize(sz);
      const overlaps = bb.max.z > REGION.z0 && bb.min.z < REGION.z1 && bb.max.x > REGION.x0 && bb.min.x < REGION.x1;
      if (!overlaps) continue;
      o.userData.flatRegion = true;
      if (bb.min.z >= REGION.z0 - 0.5 && bb.max.z <= REGION.z1 + 3.6) { o.visible = false; continue; }   // wholly in the street
      if (bb.min.z < REGION.z0 && bb.max.z <= REGION.z1 + 3.6 && sz.x < 30) {                                // runs on into street B: cut
        o.traverse((q) => {
          if (!q.isMesh) return;
          const ms = Array.isArray(q.material) ? q.material : [q.material];
          const cm = ms.map((m) => { const m2 = m.clone(); if (m.onBeforeCompile) { m2.onBeforeCompile = m.onBeforeCompile; m2.customProgramCacheKey = m.customProgramCacheKey; } m2.userData = Object.assign({}, m.userData); m2.clippingPlanes = clip; return m2; });
          q.material = Array.isArray(q.material) ? cm : cm[0];
        });
      }
    }
  }
  function swapProp(camp, p) {
    const pr = protos && protos[p.type]; if (!pr || p.flatSwap || p.dead) return;
    const old = p.mesh, m = pr.clone(); p.flatSwap = true;
    m.position.copy(old.position); m.rotation.copy(old.rotation);
    if (old.parent) { old.parent.add(m); old.parent.remove(old); }
    p.mesh = m;
  }
  // ---------------------------------------------------------------- every frame
  function frame(camp) {
    const F = camp.flat; if (!F) return;
    F.lights.aim(camp.camT.x, camp.camT.z - 3);
    const n = camp.scene.children.length;                     // new things (debris, effects, spawns): same material
    if (n !== F.seen) { F.seen = n; S.Flat.convert(camp.scene, { pastel: 0.85 }); }
  }
  S.CampFlat = { setup, frame, ready, swapProp, get protos() { return protos; } };
})();
