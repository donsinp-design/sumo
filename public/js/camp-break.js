'use strict';
// BREAK: everything in the market can be wrecked. Charge (or throw someone) through a stall and it comes apart:
// planks and steel fly, the ice bed bursts into cubes that skate across the floor (and leave it slippery), the fish
// and shellfish go everywhere. Drink machines dent, then topple and spill cans you can throw. Slams crater the floor,
// heavy landings crack it, bodies driven into walls crack the plaster.
//
//   const B = new S.CampBreak(camp)   B.smash(brk, by, vx, vz)   B.crack(x, z, size)   B.crater(x, z)   B.wallCrack(w, x, z, nx, nz)   B.update(dt)
(function () {
  const W = S.R3, rnd = (a, b) => a + Math.random() * (b - a), TAU = Math.PI * 2;
  const ZERO = new THREE.Matrix4().makeScale(0, 0, 0);
  const tmpM = new THREE.Matrix4(), tmpQ = new THREE.Quaternion(), tmpE = new THREE.Euler(), tmpV = new THREE.Vector3(), tmpS = new THREE.Vector3();

  // a pool of flying pieces: one instanced draw (plus its ink outline) however many are in the air
  class Pool {
    constructor(scene, geo, mat, n, ol) {
      this.n = n; this.items = []; this.next = 0;
      this.m = new THREE.InstancedMesh(geo, mat, n); this.m.frustumCulled = false; this.m.count = 0; scene.add(this.m);
      if (ol) { this.o = new THREE.InstancedMesh(geo, W.mesh(geo, mat, ol).children[0].material, n); this.o.frustumCulled = false; this.o.count = 0; scene.add(this.o); }
    }
    spawn(x, y, z, vx, vy, vz, s, opt) {
      opt = opt || {};
      let it;
      if (this.items.length < this.n) { it = {}; it.i = this.items.length; this.items.push(it); this.m.count = this.o ? (this.o.count = this.items.length) : this.items.length; }
      else { it = this.items[this.next]; this.next = (this.next + 1) % this.n; } // full: recycle the oldest
      Object.assign(it, { x, y, z, vx, vy, vz, rx: rnd(0, TAU), ry: rnd(0, TAU), rz: rnd(0, TAU), wx: rnd(-12, 12), wy: rnd(-8, 8), wz: rnd(-12, 12),
        sx: s[0], sy: s[1], sz: s[2], h: opt.h !== undefined ? opt.h : s[1] * 0.5, bounce: opt.bounce || 0.3, slide: opt.slide || 0, rest: false, flat: opt.flat });
      if (opt.rot) { it.rx = opt.rot[0]; it.ry = opt.rot[1]; it.rz = opt.rot[2]; }
      this.write(it); return it;
    }
    write(it) {
      tmpE.set(it.rx, it.ry, it.rz); tmpQ.setFromEuler(tmpE); tmpM.compose(tmpV.set(it.x, it.y, it.z), tmpQ, tmpS.set(it.sx, it.sy, it.sz));
      this.m.setMatrixAt(it.i, tmpM); if (this.o) this.o.setMatrixAt(it.i, tmpM); this.dirty = true;
    }
    update(dt, solid) {
      for (const it of this.items) {
        if (it.rest) continue;
        it.vy -= 18 * dt; it.x += it.vx * dt; it.y += it.vy * dt; it.z += it.vz * dt;
        it.rx += it.wx * dt; it.ry += it.wy * dt; it.rz += it.wz * dt;
        if (solid) solid(it);
        if (it.y <= it.h) {
          it.y = it.h;
          if (Math.abs(it.vy) > 1.6) { it.vy = -it.vy * it.bounce; it.vx *= 0.7; it.vz *= 0.7; it.wx *= 0.6; it.wz *= 0.6; }
          else {
            it.vy = 0; const f = Math.exp(-dt * (it.slide ? 1.6 : 9)); it.vx *= f; it.vz *= f; it.wx *= f; it.wz *= f; it.wy *= f;
            if (it.flat) { it.rx += (0 - it.rx) * Math.min(1, dt * 10); it.rz += (0 - it.rz) * Math.min(1, dt * 10); } // lands lying down
            if (Math.hypot(it.vx, it.vz) < 0.05) it.rest = true;
          }
        }
        this.write(it);
      }
      if (this.dirty) { this.m.instanceMatrix.needsUpdate = true; if (this.o) this.o.instanceMatrix.needsUpdate = true; this.dirty = false; }
    }
  }

  // cel decals: cracks, craters, ice patches. Flat, crisp edges, no gradients
  const decTex = {};
  const canvasTex = (k, w, h, fn) => decTex[k] || (decTex[k] = W.canvasTex(w, h, fn));
  const crackTex = (v) => canvasTex('crack' + v, 256, 256, (c) => {
    c.lineCap = 'round'; c.lineJoin = 'round';
    const branch = (x, y, a, len, wid, d) => {
      const pts = [[x, y]]; let px = x, py = y;
      for (let i = 0; i < 5; i++) { a += rnd(-0.5, 0.5); px += Math.cos(a) * len / 5; py += Math.sin(a) * len / 5; pts.push([px, py]); }
      for (const [col, ww] of [['rgba(230,224,232,0.55)', wid + 3], ['rgba(18,12,20,0.92)', wid]]) { c.strokeStyle = col; c.lineWidth = ww; c.beginPath(); pts.forEach((p, i) => (i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]))); c.stroke(); }
      if (d < 2) for (let i = 0; i < 2; i++) { const p = pts[2 + i * 2]; branch(p[0], p[1], a + rnd(-1.2, 1.2), len * 0.5, wid * 0.6, d + 1); }
    };
    const n = 5 + v; for (let i = 0; i < n; i++) branch(128, 128, i / n * TAU + rnd(-0.3, 0.3), rnd(60, 110), 5, 0);
    c.fillStyle = 'rgba(18,12,20,0.9)'; c.beginPath(); for (let i = 0; i < 9; i++) { const a = i / 9 * TAU, r = rnd(8, 16); c.lineTo(128 + Math.cos(a) * r, 128 + Math.sin(a) * r); } c.fill();
  });
  const craterTex = () => canvasTex('crater', 256, 256, (c) => {
    const ring = (R, col, j) => { c.fillStyle = col; c.beginPath(); for (let i = 0; i <= 18; i++) { const a = i / 18 * TAU, r = R * (1 + rnd(-j, j)); c.lineTo(128 + Math.cos(a) * r, 128 + Math.sin(a) * r * 0.9); } c.fill(); };
    ring(104, 'rgba(26,20,28,0.55)', 0.12); ring(78, 'rgba(36,30,40,0.95)', 0.14); ring(52, 'rgba(14,10,16,0.98)', 0.16);
    c.strokeStyle = 'rgba(220,214,224,0.5)'; c.lineWidth = 3; c.beginPath(); c.arc(128, 128, 78, 3.6, 5.6); c.stroke();
    c.lineCap = 'round';
    for (let i = 0; i < 12; i++) { const a = i / 12 * TAU + rnd(-0.2, 0.2); c.strokeStyle = 'rgba(14,10,16,0.92)'; c.lineWidth = 4; c.beginPath(); c.moveTo(128 + Math.cos(a) * 70, 128 + Math.sin(a) * 63); let x = 128 + Math.cos(a) * 70, y = 128 + Math.sin(a) * 63; for (let k = 0; k < 3; k++) { x += Math.cos(a + rnd(-0.5, 0.5)) * 18; y += Math.sin(a + rnd(-0.5, 0.5)) * 18; c.lineTo(x, y); } c.stroke(); }
  });
  const iceTex = (v) => canvasTex('icepatch' + v, 256, 256, (c) => {
    const blob = (R, col) => { c.fillStyle = col; c.beginPath(); for (let i = 0; i <= 40; i++) { const a = i / 40 * TAU; let r = R; for (let k = 1; k <= 3; k++) r += Math.sin(a * (k + 1) + v * (k + 2)) * R * 0.14 / k; c.lineTo(128 + Math.cos(a) * r, 128 + Math.sin(a) * r * 0.8); } c.fill(); };
    blob(108, 'rgba(178,222,244,0.62)'); blob(84, 'rgba(214,240,252,0.7)');
    c.strokeStyle = 'rgba(255,255,255,0.95)'; c.lineCap = 'round'; c.lineWidth = 5; c.beginPath(); c.moveTo(70, 100); c.lineTo(120, 80); c.stroke();
    c.lineWidth = 3; c.beginPath(); c.moveTo(140, 160); c.lineTo(172, 146); c.stroke();
    for (let i = 0; i < 26; i++) { c.fillStyle = Math.random() < 0.5 ? 'rgba(255,255,255,0.9)' : 'rgba(150,200,232,0.9)'; const x = 128 + rnd(-90, 90), y = 128 + rnd(-70, 70); c.fillRect(x, y, rnd(4, 9), rnd(4, 9)); } // cubes
  });

  class CampBreak {
    constructor(camp) {
      const c = this.c = camp, sc = camp.scene, A = S.CampArt;
      const toon = (col, sh, o) => S.toon(col, Object.assign({ shade: sh }, o || {}));
      this.pools = {
        plank: new Pool(sc, new THREE.BoxGeometry(1, 1, 1), toon(0x6a4a30, 0x2e1c10), 70, 0.01),
        steel: new Pool(sc, new THREE.BoxGeometry(1, 1, 1), toon(0xb8c2cc, 0x4a5662, { spec: 0.7, rimAmt: 0.5 }), 50, 0.008),
        ice: new Pool(sc, new THREE.BoxGeometry(1, 1, 1), toon(0xdcf2fc, 0x7ab4d4, { spec: 0.9, rimAmt: 0.6 }), 360, 0),
        fish: new Pool(sc, (A.fishGeo && A.fishGeo()) || new THREE.SphereGeometry(1, 10, 6), (camp.map.fishMat) || toon(0x8a9ab8, 0x3a4a68, { spec: 0.8 }), 160, 0),
        bits: new Pool(sc, new THREE.SphereGeometry(1, 6, 4), toon(0xe8784a, 0x7a2a14, { spec: 0.4 }), 200, 0),
        glass: new Pool(sc, new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial({ color: 0xd8f0ff, transparent: true, opacity: 0.8 }), 90, 0),
        rubble: new Pool(sc, new THREE.DodecahedronGeometry(1, 0), toon(0x6e6a72, 0x2a262e), 140, 0.008),
        cloth: new Pool(sc, new THREE.BoxGeometry(1, 1, 1), toon(0xe2322b, 0x6e1018), 40, 0),
      };
      this.decals = []; this.falling = [];
      this.decalGeo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
    }
    // a flat cel decal on the floor (oldest recycled)
    decal(tex, x, z, s, y, ry) {
      let m;
      if (this.decals.length >= 48) { m = this.decals.shift(); }
      else { m = new THREE.Mesh(this.decalGeo, new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 })); m.renderOrder = 1; this.c.scene.add(m); }
      m.material.map = tex; m.material.needsUpdate = true;
      m.position.set(x, y || 0.015 + this.decals.length * 0.0004, z); m.scale.set(s, 1, s); m.rotation.set(0, ry !== undefined ? ry : rnd(0, TAU), 0); m.quaternion.setFromEuler(m.rotation);
      m.updateMatrix(); this.decals.push(m); return m;
    }
    crack(x, z, s) { this.decal(crackTex(Math.floor(rnd(0, 3))), x, z, s || 1.6); }
    crater(x, z) {
      this.decal(craterTex(), x, z, 2.2); this.crack(x, z, 3.2);
      for (let i = 0; i < 14; i++) { const a = rnd(0, TAU), sp = rnd(2, 5.5), s = rnd(0.05, 0.12); this.pools.rubble.spawn(x + Math.cos(a) * 0.3, 0.1, z + Math.sin(a) * 0.3, Math.cos(a) * sp, rnd(3, 7), Math.sin(a) * sp, [s, s * 0.8, s]); }
    }
    // a crack on a wall face where a body hit it (n = the face's outward normal)
    wallCrack(x, z, nx, nz, y) {
      const m = this.decal(crackTex(Math.floor(rnd(0, 3))), x + nx * 0.02, z + nz * 0.02, 1.5, y || 1.1, 0);
      m.rotation.set(Math.PI / 2, 0, rnd(0, TAU)); // the plane stands up...
      m.quaternion.setFromEuler(m.rotation); m.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.atan2(nx, nz))); // ...and faces out of the wall
      m.updateMatrix();
      for (let i = 0; i < 6; i++) { const s = rnd(0.04, 0.09); this.pools.rubble.spawn(x + nx * 0.1, (y || 1.1) + rnd(-0.3, 0.3), z + nz * 0.1, nx * rnd(1, 3) + rnd(-1, 1), rnd(0, 2), nz * rnd(1, 3) + rnd(-1, 1), [s, s, s]); }
    }
    hideInst(B, i) { for (const m of B.meshes) { m.setMatrixAt(i, ZERO); m.instanceMatrix.needsUpdate = true; } }
    // smash a breakable: brk from the map, by = who hit it, (vx, vz) = their velocity
    smash(b, by, vx, vz) {
      const c = this.c, P = this.pools; if (b.broken) return true;
      const sp = Math.hypot(vx, vz) || 1, dx = vx / sp, dz = vz / sp;
      if (b.kind === 'vend') {
        b.hp--; c.shake = Math.max(c.shake || 0, 0.35); c.g.audio.thump(9); c.fx.spark(by.x + dx * 0.5, 1.1, by.z + dz * 0.5, 1.2);
        for (let i = 0; i < 10; i++) { const s = rnd(0.03, 0.07); P.glass.spawn(b.x, rnd(0.9, 1.6), b.z, -dx * rnd(1, 3) + rnd(-1.5, 1.5), rnd(1, 4), -dz * rnd(1, 3) + rnd(-1.5, 1.5), [s, s * 0.3, s * 1.4], { bounce: 0.2 }); }
        if (b.hp > 0) { b.group.rotation.z = rnd(-0.06, 0.06); b.group.position.x += dx * 0.08; b.group.position.z += dz * 0.08; b.group.updateMatrix(); b.group.updateMatrixWorld(true); c.popAt(by, 'DENT!'); return false; }
        b.broken = true; this.dropWall(b);
        this.falling.push({ g: b.group, t: 0, ax: new THREE.Vector3(-dz, 0, dx), q0: b.group.quaternion.clone(), p0: b.group.position.clone(), dx, dz });
        if (b.glow) b.glow.visible = false;
        c.popAt(by, 'SMASH!'); c.hitstop = Math.max(c.hitstop || 0, 0.06); return true;
      }
      // a stall or a steel table: the whole thing goes
      b.broken = true; this.dropWall(b);
      const R = b.rec; if (R.group.parent) R.group.parent.remove(R.group);
      const z0 = b.z - b.len / 2;
      // its goods, launched from where they lay
      for (const [B, i, n] of R.inst) {
        const M = B.at(i); M.decompose(tmpV, tmpQ, tmpS); this.hideInst(B, i);
        if (Math.random() < (n === 'shell' || n === 'shrimp' ? 0.35 : 0.8)) {
          const pool = n === 'tray' ? P.steel : P.bits, s = n === 'tray' ? [0.5, 0.03, 0.3] : n === 'saku' ? [0.2, 0.07, 0.1] : [0.06, 0.04, 0.05];
          pool.spawn(tmpV.x, tmpV.y, tmpV.z, dx * rnd(2, 6) + rnd(-2, 2), rnd(2, 6), dz * rnd(2, 6) + rnd(-2, 2), s, { flat: n === 'tray' });
        }
      }
      for (const [sp2, i] of R.fish) {
        const M = R.fishes.at(sp2, i); M.decompose(tmpV, tmpQ, tmpS);
        const fm = R.fishes.meshes[sp2]; if (fm) { fm.setMatrixAt(i, ZERO); fm.instanceMatrix.needsUpdate = true; }
        if (Math.random() < 0.7) P.fish.spawn(tmpV.x, tmpV.y + 0.1, tmpV.z, dx * rnd(2, 7) + rnd(-2.5, 2.5), rnd(2.5, 7), dz * rnd(2, 7) + rnd(-2.5, 2.5), [0.26, 0.26, 0.26], { h: 0.05, flat: true, bounce: 0.35, slide: 1 });
      }
      // the counter / table itself
      const wood = b.kind === 'stall';
      for (let i = 0; i < (wood ? 14 : 8); i++) {
        const zz = z0 + rnd(0, b.len);
        (wood ? P.plank : P.steel).spawn(b.x + rnd(-0.7, 0.7), rnd(0.3, 0.9), zz, dx * rnd(2, 7) + rnd(-2, 2), rnd(2, 6), dz * rnd(2, 7) + rnd(-2, 2), wood ? [rnd(0.1, 0.18), 0.04, rnd(0.5, 1.1)] : [0.05, 0.05, rnd(0.4, 0.8)], { flat: true });
      }
      if (wood) for (let i = 0; i < 6; i++) P.cloth.spawn(b.x + b.sd * rnd(0.5, 1.8), 2.6, z0 + rnd(0, b.len), dx * rnd(1, 3), rnd(0, 2), dz * rnd(1, 3), [rnd(0.3, 0.5), 0.01, rnd(0.3, 0.5)], { flat: true, bounce: 0 });
      // the ice bed bursts: cubes skate everywhere, and the floor under it turns to ice
      const nIce = Math.round(b.len * 22);
      for (let i = 0; i < nIce; i++) { const s = rnd(0.04, 0.09); P.ice.spawn(b.x + rnd(-0.7, 0.7), 1.0, z0 + rnd(0, b.len), dx * rnd(1, 6) + rnd(-3, 3), rnd(1.5, 5), dz * rnd(1, 6) + rnd(-3, 3), [s, s, s], { slide: 1, bounce: 0.25 }); }
      const cx = b.x + dx * 0.9, cz = b.z + dz * 0.4, r = Math.max(1.2, b.len * 0.42);
      c.map.puddles.push({ x: cx, z: cz, r, sx: 1.25, ice: true });
      this.decal(iceTex(Math.floor(rnd(0, 3))), cx, cz, r * 2.4, 0.016, 0).scale.set(r * 2.5 * 1.25, 1, r * 2.4 * 1.1);
      this.decals[this.decals.length - 1].updateMatrix();
      c.fx.dust(b.x, 0.6, b.z, 16, 0.6, 1.0, 0.5, dx * 2, dz * 2); c.fx.spark(b.x, 0.9, b.z, 1.4);
      c.shake = Math.max(c.shake || 0, 0.55); c.hitstop = Math.max(c.hitstop || 0, 0.07);
      c.g.audio.thump(11); c.g.audio.slap(7); c.g.audio.scuff();
      c.popAt(by, b.kind === 'stall' ? 'STALL SMASHED!' : 'TABLE SMASHED!');
      // anyone standing next to it gets caught in the wreckage
      for (const e of c.actors) if (e !== by && e.team === 1 && !e.dead && e.st !== 'held' && Math.abs(e.x - b.x) < 1.6 && e.z < b.z + b.len / 2 + 0.6 && e.z > z0 - 0.6) c.damage(e, 10, by, dx * 6, dz * 6, true);
      return true;
    }
    dropWall(b) { const L = this.c.map.walls, i = L.indexOf(b.w); if (i >= 0) L.splice(i, 1); }
    update(dt) {
      const walls = this.c.map.walls, solid = (it) => { // debris bounces off walls and counters instead of flying through them
        if (it.y > 3.4) return;
        for (const w of walls) {
          if (it.x < w.x0 || it.x > w.x1 || it.z < w.z0 || it.z > w.z1) continue;
          const o = [it.x - w.x0, w.x1 - it.x, it.z - w.z0, w.z1 - it.z], m = Math.min(...o), k = o.indexOf(m);
          if (k === 0) { it.x = w.x0 - 0.01; it.vx = -Math.abs(it.vx) * 0.3; } else if (k === 1) { it.x = w.x1 + 0.01; it.vx = Math.abs(it.vx) * 0.3; }
          else if (k === 2) { it.z = w.z0 - 0.01; it.vz = -Math.abs(it.vz) * 0.3; } else { it.z = w.z1 + 0.01; it.vz = Math.abs(it.vz) * 0.3; }
        }
      };
      for (const k in this.pools) this.pools[k].update(dt, solid);
      for (const f of this.falling) { // a toppling drink machine
        if (f.done) continue;
        f.t += dt; const p = Math.min(1, f.t / 0.55), a = p * p * Math.PI / 2 * 0.97;
        f.g.quaternion.copy(f.q0).premultiply(new THREE.Quaternion().setFromAxisAngle(f.ax, a));
        f.g.position.set(f.p0.x + f.dx * Math.sin(a) * 0.1, 0.35 * Math.sin(a) * 0.4, f.p0.z + f.dz * Math.sin(a) * 0.1);
        f.g.updateMatrix(); f.g.updateMatrixWorld(true);
        if (p >= 1) { // down: the front pops open and the cans roll out (throwable, like bottles)
          const fx = f.p0.x - f.dx * 1.0, fz = f.p0.z - f.dz * 1.0;
          for (let i = 0; i < 6; i++) { const q = this.c.addProp('can', fx + rnd(-0.4, 0.4), fz + rnd(-0.4, 0.4)); q.vx = -f.dx * rnd(1.5, 4) + rnd(-2, 2); q.vz = -f.dz * rnd(1.5, 4) + rnd(-2, 2); q.y = 0.4; q.vy = rnd(2, 4); q.hop = true; }
          f.done = true; this.c.shake = Math.max(this.c.shake || 0, 0.45); this.c.g.audio.thump(12); this.crack(f.p0.x + f.dx * 1.0, f.p0.z + f.dz * 1.0, 2.0); this.c.fx.dust(f.p0.x + f.dx, 0.2, f.p0.z + f.dz, 10, 0.5, 0.6, 0.4); }
      }
    }
  }
  S.CampBreak = CampBreak;
})();
