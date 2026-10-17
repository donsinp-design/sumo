'use strict';
// SUMO PARTY: three two-player modes in the bathhouse (one keyboard, split screen; or two pads). Built on the stealth level (its walls, nav, carts, the kit).
//   CO-OP HEIST: both naked. Find your mawashi (one each, hidden about the ground floor), put it on, and get out the kitchen's back door. Staff patrol: seen, they chase;
//     caught, they hold on, and unless the other one pushes or booty-slams them off in time you're dragged back to the bath (your mawashi back where it was)
//   HIDE & SEEK: one is the bathhouse owner, one a sumo. 15 s to hide (a laundry cart, a toilet stall, under the bath water), 75 s to find him. Swap; first to 3
//   PANTS TAG: one pair of pants. Whoever has them on scores; the other steals them with a push, a slide into them, or a booty slam. First to 45
(function () {
  const L = S.StealthLib; if (!L || !S.Stealth) return;
  const { floorY, roomAt, inPool, ang, lerpA, LY, POOL, CENSOR } = L;
  const STEP = 1 / 60;
  const KEYS = [
    { up: ['KeyW'], down: ['KeyS'], left: ['KeyA'], right: ['KeyD'], run: ['ShiftLeft'], push: ['KeyF', 'KeyJ'], slide: ['Space', 'KeyL'], use: ['KeyE', 'KeyK'], hide: ['KeyQ', 'KeyI'] },   // (J K L I too: the story's keys)
    { up: ['ArrowUp'], down: ['ArrowDown'], left: ['ArrowLeft'], right: ['ArrowRight'], run: ['ShiftRight'], push: ['Period'], slide: ['Slash'], use: ['Comma'], hide: ['KeyM'] },
  ];
  const HELP = ['WASD move · SHIFT run · L or SPACE belly slide · J or F push (hold: booty slam) · K or E use · I or Q hide', 'ARROWS move · R-SHIFT run · / belly slide · . push (hold: booty slam) · , use · M hide'];
  const COL = [0x2f4b7c, 0xb9493c], CSS = ['#5a8fd0', '#dd5a42'];
  const D = { walk: 3.4, run: 5.4, runStam: 4.5, wade: 2.0, slideV: 8.0, slideRun: 1.22, slideDry: 9.5, slideWet: 4.0, getUp: 0.6, holdJ: 0.25, slam: 0.9, slamLand: 0.55,
    staffN: 5, see: 7, seeHalf: 0.65, chase: 3.7, patrol: 1.4, holdT: 3.0, downT: 3.0, hideT: 15, seekT: 75, toWin: 3, tagWin: 45, breath: 10 };
  const START = [[-0.6, 1.0], [2.6, 1.0]];
  const MAW_SPOTS = [[20.6, -58.8], [12.9, -49.5], [2.2, -54.6], [-14.4, -43.2], [-3.6, -45.4], [1.4, -38.6], [0.0, -21.6], [-8.5, -25.5]];   // (all reachable: checked against the nav)

  class Party extends S.Stealth {
    start(mode) {
      const g = this.g; this.mode = mode; this.cpu = !!g.partyCpu; this.fpv = !!g.partyFpv;   // (THIRD PERSON: a camera behind each one, Hitman / GTA style)   // (P2 played by the computer: one person can test every mode)
      this.R = g.R; this.t = 0; this.acc = 0; this.paused = false;
      this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(0xd9e6e9);
      this.cams = [0, 1].map(() => new THREE.PerspectiveCamera(this.fpv ? 60 : 38, 1, this.fpv ? 0.1 : 2.0, 120)); this.cam = this.cams[0];
      this.fx = new S.FX(this.scene); this.fx.scene = this.scene; this.fx.noMarks = true;
      this.flat = { lights: S.Flat.lights(this.scene, { r: 22 }) };
      { const Lg = this.flat.lights, sun = Lg.sun, R = 60; sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -R, right: R, top: R, bottom: -R, near: 1, far: 140 }); sun.shadow.camera.updateProjectionMatrix();
        const cx = 1, cz = -30; sun.position.set(cx - 15, 37, cz + 20); sun.target.position.set(cx, 0, cz); sun.target.updateMatrixWorld(); Lg.aim = () => {}; }
      const r = this.R.r; r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
      const vg = document.getElementById('vignette'); if (vg) vg.style.display = 'none';
      this.walls = []; this.blockers = []; this.puddles = []; this.buckets = []; this.flying = []; this.npcs = [];
      this.P = { x: 0, z: 0, y: 0, r: 0.7, st: 'free', boxHide: false };   // (the stealth level's single player: some of its helpers look at him; here he's no one)
      this.build();
      for (const m of this.marks || []) m.visible = false;   // (the story's "go here" rings: not in a party)
      this.walls.push({ x0: LY.stairs.x0, x1: LY.stairs.x1, z0: LY.stairs.z1 - 0.9, z1: LY.stairs.z1 - 0.3, tall: true });   // (the ground floor only: the stairs are shut)
      this.buildNav();
      if (this.fpv) { this.raiseWalls(); this.camWalls = LY.solids.filter((q) => !q.f && (q.k === 'wall' || q.h > 1.6)); }   // (what the camera behind him can't pass through)
      this.keys = {}; this.kd = (e) => { this.keys[e.code] = true; if (e.code === 'Escape') this.quit(); if (/Arrow|Space|Slash|Period|Comma/.test(e.code)) e.preventDefault(); }; this.ku = (e) => { this.keys[e.code] = false; };
      addEventListener('keydown', this.kd); addEventListener('keyup', this.ku);
      if (this.fpv) {   // P1 looks with the mouse (click the game to capture it)
        this.mm = (e) => { const p = this.ps && this.ps[0]; if (!p || (!document.pointerLockElement && !e.movementX && !e.movementY)) return; p.yaw = (p.yaw === undefined ? p.f : p.yaw) + e.movementX * 0.0026; p.pitch = Math.max(-0.9, Math.min(0.7, (p.pitch || 0) - e.movementY * 0.0022)); };   // (captured or not: moving the mouse turns him)
        this.mc = () => { if (document.pointerLockElement !== this.R.r.domElement && this.R.r.domElement.requestPointerLock) this.R.r.domElement.requestPointerLock(); };
        addEventListener('mousemove', this.mm); addEventListener('mousedown', this.mc); }   // (a click anywhere captures the mouse: the canvas has layers over it)
      const arch = S.ARCH[0];
      this.ps = [0, 1].map((i) => this.makePlayer(i, arch));
      this.buildHud();
      this.resize = () => {}; addEventListener('resize', this.resize);
      this.points = this.walkPoints();
      if (mode === 'coop') this.setupCoop(); else if (mode === 'hide') this.setupHide(); else this.setupTag();
    }
    stop() {
      removeEventListener('resize', this.resize); removeEventListener('keydown', this.kd); removeEventListener('keyup', this.ku);
      if (this.mm) { removeEventListener('mousemove', this.mm); removeEventListener('mousedown', this.mc); if (document.pointerLockElement && document.exitPointerLock) document.exitPointerLock(); }
      if (this.hud) this.hud.remove();
      const r = this.R.r; r.setScissorTest(false); r.setViewport(0, 0, innerWidth, innerHeight); r.shadowMap.enabled = !!this.R.flat;
      const vg = document.getElementById('vignette'); if (vg) vg.style.display = this.R.flat ? 'none' : '';
      this.scene = null;
    }
    raiseWalls() {   // first person: the level's walls are cut away at waist height (made for a camera above). Raised to the ceiling here, in their own colours, so rooms hide what's in them
      const C = { tile: 0xe6f0ee, glass: 0xc4dde8, plaster: 0xefe6d6, plaster_dk: 0xc9bfb2, wood: 0xd3ab7a, metal: 0x9aa3ab }, mats = {};
      const g = new THREE.Group(); this.G.add(g);
      for (const q of LY.solids) { if (q.k !== 'wall' || q.f || q.h > 2) continue; const col = C[q.col] || C.plaster, m = mats[col] || (mats[col] = S.Flat.mat(col, q.col === 'glass' ? { transparent: true, opacity: 0.55 } : undefined));
        const h = 3.0 - q.h, o = new THREE.Mesh(new THREE.BoxGeometry(q.x1 - q.x0, h, q.z1 - q.z0), m); o.position.set((q.x0 + q.x1) / 2, q.h + h / 2, (q.z0 + q.z1) / 2); o.castShadow = o.receiveShadow = true; o.userData.flatDone = true; g.add(o); }
      // and a ceiling over the whole ground floor (with beams), out of the sun's way: it casts no shadow, so the rooms keep their light
      const X0 = -21, X1 = 24, Z0 = -61, Z1 = 4.6, cm = new THREE.MeshBasicMaterial({ color: 0xebe4d8 }), bm = new THREE.MeshBasicMaterial({ color: 0xa97c55 });   // (unlit: a ceiling faces away from the sun, the flat light would tint it lilac)
      const ceil = new THREE.Mesh(new THREE.PlaneGeometry(X1 - X0, Z1 - Z0).rotateX(Math.PI / 2), cm); ceil.position.set((X0 + X1) / 2, 3.0, (Z0 + Z1) / 2); ceil.userData.flatDone = true; ceil.receiveShadow = false; g.add(ceil);
      for (let z = Z0 + 1.5; z < Z1; z += 3) { const b = new THREE.Mesh(new THREE.BoxGeometry(X1 - X0, 0.16, 0.22), bm); b.position.set((X0 + X1) / 2, 2.92, z); b.userData.flatDone = true; g.add(b); }
    }
    quit() { if (this.quitting) return; this.quitting = true; this.g.endCampaign(); }
    kitShown() {}
    // ---- players
    makePlayer(i, arch) {
      const v = new S.WrestlerView(this.scene, arch, this.fx, S.DEF_EQ); v.viewer = i; v.match = null;
      const w = Object.assign({}, { x: 0, z: 0, y: 0, f: 0, fx: 0, fz: 1, vx: 0, vz: 0, st: 'free', t: 0, dur: 1, fxs: {}, a: arch, idx: i, szCur: 1, squash: 0, bal: 1, tx: 0, tz: 0, power: 0, pre: null, preT: 0,
        hand: 0, windPow: 0, charges: 0, uprightT: 0, throatT: 0, lifted: false, down: false, fallX: 0, fallZ: 1, clinch: null, slideT: 0, spd: 0, crouchT: 0, lean: 0, gulpI: -1, contact: false, fwdIn: 0, ddx: 0, ddz: 0, boomT: 0, relaxed: true });
      const cv = document.createElement('canvas'); cv.width = 8; cv.height = 5; const tex = new THREE.CanvasTexture(cv); tex.magFilter = tex.minFilter = THREE.NearestFilter;
      const mz = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false })); mz.visible = false; this.scene.add(mz);
      const [x, z] = START[i];
      return { i, x, z, y: 0, f: -Math.PI / 2, vx: 0, vz: 0, r: 0.7, st: 'free', t: 0, dur: 0, sv: 0, cdir: 0, stam: 1, tired: false, v, w, kind: 'sumo', mosaic: { s: mz, cv, t: 0 },
        hidden: null, sub: false, breath: D.breath, maw: false, pants: false, score: 0, camT: new THREE.Vector3(x, 0, z - 2.6), inp: {}, prev: {}, pushHeld: 0, grabbedBy: null, lock: 0, flash: 0 };
    }
    makeSeeker(p) {   // hide and seek: the bathhouse owner's body for whoever is seeking
      if (!p.staffV) { p.staffV = new S.WorkerView(this.scene, 'staff', true, 1); p.staffV.walls = this.walls; if (p.staffV.pole && p.staffV.pole.parent) p.staffV.pole.parent.remove(p.staffV.pole); }
      p.kind = 'staff'; p.staffV.root.visible = true; p.v.root.visible = false;
    }
    makeSumo(p) { p.kind = 'sumo'; if (p.staffV) p.staffV.root.visible = false; p.v.root.visible = true; }
    place(p, x, z, f) { p.x = x; p.z = z; p.y = floorY(x, z); p.f = f === undefined ? -Math.PI / 2 : f; p.yaw = p.f; p.cpos = null; p.vx = p.vz = 0; p.st = 'free'; p.t = 0; p.hidden = null; p.sub = false; p.grabbedBy = null; p.camT.set(x, 0, z - 2.6); }
    walkPoints() {   // floor spots on the ground floor the staff can wander between (a grid, anything in a wall or the bath left out)
      const out = [];
      for (let x = -19; x <= 21; x += 2) for (let z = -60; z <= 3; z += 2) {
        const rm = roomAt(x, z); if (rm === 'stair' || rm === 'up' || rm === 'store' || inPool(x, z)) continue;
        const q = { x, z }; this.collide(q, 0.5); if (Math.hypot(q.x - x, q.z - z) > 0.05) continue; out.push([x, z]); }
      return out;
    }
    readInput(p, dt) {   // keys (and a pad, if there is one for this player); or the computer, for P2
      if (this.cpu && p.i === 1) { p.inp = this.botInput(p, dt); return; }
      const K0 = KEYS[p.i], K = this.cpu && p.i === 0 ? { up: K0.up.concat(['ArrowUp']), down: K0.down.concat(['ArrowDown']), left: K0.left.concat(['ArrowLeft']), right: K0.right.concat(['ArrowRight']), run: K0.run.concat(['ShiftRight']), push: K0.push, slide: K0.slide, use: K0.use, hide: K0.hide } : K0, k = (a) => a.some((c) => this.keys[c]);   // (alone against the computer: the arrows move P1 too)
      let mx = (k(K.right) ? 1 : 0) - (k(K.left) ? 1 : 0), mz = (k(K.down) ? 1 : 0) - (k(K.up) ? 1 : 0);
      const I = { run: k(K.run), push: k(K.push), slide: k(K.slide), use: k(K.use), hide: k(K.hide) };
      const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [], gp = pads[p.i];
      if (gp) { const ax = gp.axes[0] || 0, az = gp.axes[1] || 0; if (Math.hypot(ax, az) > 0.25) { mx = ax; mz = az; } const b = (n) => gp.buttons[n] && gp.buttons[n].pressed;
        I.slide = I.slide || b(0); I.hide = I.hide || b(1); I.push = I.push || b(2); I.use = I.use || b(3); I.run = I.run || b(5) || b(7); }
      if (this.fpv) {   // third person: the stick / keys are relative to the camera (W away from it, D to its right); he turns to face where he walks. P1: the mouse turns the camera; P2 (or a pad): left / right / right stick
        if (p.yaw === undefined) p.yaw = p.f; if (gp && Math.abs(gp.axes[2] || 0) > 0.2) p.yaw += (gp.axes[2] || 0) * 0.05; if (gp && Math.abs(gp.axes[3] || 0) > 0.2) p.pitch = Math.max(-0.9, Math.min(0.7, (p.pitch || 0) - (gp.axes[3] || 0) * 0.03));
        let side = mx; if (p.i === 1 && !gp && !(this.cpu)) { p.yaw += mx * 2.6 / 60; side = 0; }
        if (p.i === 0 && this.cpu) { const tl = this.keys.ArrowLeft ? 1 : 0, tr = this.keys.ArrowRight ? 1 : 0; if (tl || tr) { p.yaw += (tr - tl) * 2.6 / 60; side -= (tr - tl); } }   // (alone: the left / right arrows turn him, no mouse needed)
        const fwd = -mz, f = p.yaw; mx = Math.cos(f) * fwd - Math.sin(f) * side; mz = Math.sin(f) * fwd + Math.cos(f) * side; }
      const m = Math.hypot(mx, mz); if (m > 1) { mx /= m; mz /= m; }
      I.mx = mx; I.mz = mz; I.mag = Math.min(1, m);
      for (const b of ['push', 'slide', 'use', 'hide']) I[b + 'P'] = I[b] && !p.prev[b];
      I.pushR = !I.push && p.prev.push; p.prev = { push: I.push, slide: I.slide, use: I.use, hide: I.hide }; p.inp = I;
    }
    other(p) { return this.ps[1 - p.i]; }
    // ---- the computer as P2: walks the nav paths to a goal, presses what a player would press
    botInput(p, dt) {
      const B = p.bot || (p.bot = { path: null, pi: 0, repath: 0, gx: null, gz: null, prev: {}, spot: null, list: null, li: 0, flee: null, fleeT: 0 }), o = this.other(p);
      const raw = { run: false, push: false, slide: false, use: false, hide: false }; let gx = null, gz = null;
      const dist = (x, z) => Math.hypot(p.x - x, p.z - z), face = (x, z) => { p.f = Math.atan2(z - p.z, x - p.x); };
      const tap = (b) => { raw[b] = !B.prev[b]; };   // (a press: down one frame, up the next)
      const goSpot = (S0, r) => {   // walk to a hiding place (into the bath by its steps); true once there
        if (dist(S0.x, S0.z) <= r) return true;
        if (S0.via && B.viaFor !== S0 && !inPool(p.x, p.z) && dist(S0.via[0], S0.via[1]) > 0.7) { gx = S0.via[0]; gz = S0.via[1]; return false; }
        if (S0.via) B.viaFor = S0;   // (past the steps: no turning back for them)
        if (S0.via) { B.direct = [S0.x, S0.z]; return false; }
        gx = S0.x; gz = S0.z; return false; };
      if (this.mode === 'coop') {
        const grab = o.grabbedBy, chased = (this.staff || []).some((s) => s.mode === 'chase' && s.target === p && Math.hypot(s.a.x - p.x, s.a.z - p.z) < 5);
        if (p.st === 'grabbed') { /* held: wait for the other */ }
        else if (grab && grab.mode === 'hold') { gx = grab.a.x; gz = grab.a.z; raw.run = true; if (dist(gx, gz) < 1.9) { face(gx, gz); tap('push'); gx = null; } }
        else if (!p.maw) { const m = this.maw[p.i]; gx = m.x; gz = m.z; if (dist(gx, gz) < 1.3) { tap('use'); gx = null; } }
        else { gx = this.exit.x; gz = this.exit.z; if (dist(gx, gz) < 1.0) gx = null; }
        if (chased) raw.run = true;
        for (const s of this.staff || []) if (s.mode !== 'down' && s.mode !== 'hold' && Math.hypot(s.a.x - p.x, s.a.z - p.z) < 1.5) { face(s.a.x, s.a.z); tap('push'); break; }
      } else if (this.mode === 'hide') {
        const seeking = this.ps[this.seeker] === p;
        if (!seeking) {   // the sumo: off to a hiding place, in, and still
          if (this.ph === 'hide' || this.ph === 'seek') { if (!B.spot || B.round !== this.round) { B.round = this.round; const sp = this.hideSpots().filter((t) => dist(t.x, t.z) < 40).sort((a, b) => dist(a.x, a.z) - dist(b.x, b.z)); B.spot = sp[(Math.random() * Math.min(4, sp.length)) | 0] || this.hideSpots()[0]; }   // (one of the nearest few he can reach: there are only 15 seconds)   // (one of the nearest few: there are only 15 seconds)
            if (!p.hidden && !p.sub) { raw.run = this.ph === 'hide'; if (goSpot(B.spot, B.spot.k === 'pool' ? 0.9 : 1.3)) tap('hide'); } }
        } else if (this.ph === 'seek') {   // the owner: every hiding place in turn, nearest first; straight for him if he's in sight
          if (!B.list || B.round !== this.round) { B.round = this.round; B.list = this.hideSpots().sort((a, b) => dist(a.x, a.z) - dist(b.x, b.z)); B.li = 0; }
          if (!o.hidden && !o.sub && this.clear(p.x, p.z, o.x, o.z) && dist(o.x, o.z) < 9) { gx = o.x; gz = o.z; raw.run = true; }
          else { const t = B.list[B.li % B.list.length]; B.stuck = (B.stuck || 0) + (Math.hypot(p.vx, p.vz) < 0.3 ? dt : -B.stuck); if (B.stuck > 2.5) { B.stuck = 0; B.li++; }   // (stuck: on to the next)
            else if (goSpot(t, t.k === 'stall' ? 0.6 : 1.4)) { face(t.x - (t.k === 'stall' ? 2 : 0), t.z); tap('use'); B.li++; B.stuck = 0; } }
        }
      } else {   // pants tag
        const P = this.pantsM;
        if (p.pants) { B.fleeT -= dt; if (!B.flee || B.fleeT <= 0 || dist(B.flee[0], B.flee[1]) < 1.5) { B.fleeT = 2.5; let best = null, bd = -1; for (let k = 0; k < 40; k++) { const q = this.points[(Math.random() * this.points.length) | 0], d = Math.hypot(q[0] - o.x, q[1] - o.z); if (d > bd) { bd = d; best = q; } } B.flee = best; }
          gx = B.flee[0]; gz = B.flee[1]; raw.run = dist(o.x, o.z) < 7; }
        else if (P.free) { gx = P.x; gz = P.z; raw.run = true; }
        else if (o.pants) { gx = o.x; gz = o.z; raw.run = true; const d = dist(o.x, o.z);
          if (d < 1.7) { face(o.x, o.z); tap('push'); } else if (d < 4 && p.st === 'free' && Math.random() < dt * 1.5 && this.clear(p.x, p.z, o.x, o.z)) { face(o.x, o.z); raw.slide = !B.prev.slide; } }
      }
      let mx = 0, mz = 0;
      if (gx !== null || B.direct) { B.st = (B.st || 0) + (Math.hypot(p.vx, p.vz) < 0.35 && p.st === 'free' ? dt : -(B.st || 0)); } else B.st = 0;   // (stuck against something: a new route, then a step to the side)
      if (B.st > 1.2) { B.st = 0; B.noDirect = 2.5; B.path = null; B.unstick = 0.7; B.side = Math.random() < 0.5 ? 1 : -1; }
      B.noDirect = Math.max(0, (B.noDirect || 0) - dt);
      if (B.unstick > 0) { B.unstick -= dt; const a = Math.atan2(gz === null ? 0 : gz - p.z, gx === null ? 1 : gx - p.x) + B.side * Math.PI / 2; mx = Math.cos(a); mz = Math.sin(a); B.direct = null; gx = null; }
      if (B.unstick > 0) { /* stepping aside */ }
      else if (B.direct) { const dx = B.direct[0] - p.x, dz = B.direct[1] - p.z, d = Math.hypot(dx, dz) || 1; mx = dx / d; mz = dz / d; B.direct = null; }   // (straight there: down the bath steps)
      else if (gx !== null && !B.noDirect && Math.hypot(gx - p.x, gz - p.z) < 8 && this.clear(p.x, p.z, gx, gz) && !this.segInWall(p.x, p.z, gx, gz)) { const dx = gx - p.x, dz = gz - p.z, d = Math.hypot(dx, dz) || 1; mx = dx / d; mz = dz / d; B.path = null; }   // (in plain sight: straight there)
      else if (gx !== null) {
        if (B.gx === null || Math.hypot(gx - B.gx, gz - B.gz) > 1.5 || (B.repath -= dt) <= 0 || !B.path) { B.repath = 0.6; B.gx = gx; B.gz = gz; B.path = this.navPath(p.x, p.z, gx, gz) || [[gx, gz]]; B.pi = 0; }
        let pt = B.path[B.pi]; while (pt && Math.hypot(pt[0] - p.x, pt[1] - p.z) < 0.45 && B.pi < B.path.length - 1) { B.pi++; pt = B.path[B.pi]; }
        if (pt) { const dx = pt[0] - p.x, dz = pt[1] - p.z, d = Math.hypot(dx, dz) || 1; mx = dx / d; mz = dz / d; }
      } else B.gx = null;
      if (raw.slide) { mx = Math.cos(p.f); mz = Math.sin(p.f); }
      const I = Object.assign({ mx, mz, mag: Math.hypot(mx, mz) }, raw);
      for (const b of ['push', 'slide', 'use', 'hide']) I[b + 'P'] = I[b] && !B.prev[b];
      I.pushR = !I.push && B.prev.push; B.prev = { push: raw.push, slide: raw.slide, use: raw.use, hide: raw.hide };
      return I;
    }
    hideSpots() {   // where a sumo can hide: the carts, the toilet stalls, a few places in the bath
      const out = this.carts.map((c) => ({ k: 'cart', x: c.x + 0.9, z: c.z })).concat(LY.stalls.map((q) => ({ k: 'stall', x: q.x + 2.3, z: q.z })));   // (stalls: from the walkway in front, clear of the doors)
      const sx = (POOL.steps[0] + POOL.steps[1]) / 2; for (const [x, z] of [[sx, -5.5], [sx + 2.5, -7.5]]) out.push({ k: 'pool', x, z, via: [sx, POOL.z1 + 0.9] });   // (into the bath by its steps: the paths don't go through water)
      return out;
    }
    wetAt(x, z) { return !!{ bath: 1, shower: 1 }[roomAt(x, z)] || this.puddles.some((q) => ((x - q.x) / q.rx) ** 2 + ((z - q.z) / q.rz) ** 2 < 1); }
    stepPlayer(p, dt) {
      const I = p.inp; p.t += dt; p.lock = Math.max(0, p.lock - dt); p.flash = Math.max(0, p.flash - dt);
      if (this.frozen(p)) { p.vx = p.vz = 0; return; }
      const wet = inPool(p.x, p.z);
      if (p.st === 'grabbed') { p.vx = p.vz = 0; return; }
      // hiding: a cart, a toilet stall, under the bath water
      if (p.hidden || p.sub) {
        if (p.sub) { p.breath -= dt; if (p.breath <= 0 || I.hideP || (I.mag > 0.5 && p.t > 0.4)) { p.sub = false; p.breath = D.breath; this.fx.water && this.fx.water(p.x, p.z, 2, POOL.water); } else { if (Math.random() < dt * 0.6 && this.fx.water) this.fx.water(p.x, p.z, 0.4, POOL.water); } return; }
        if (I.hideP || (I.mag > 0.5 && p.t > 0.4)) this.unhide(p); else return;
      }
      if (I.hideP && p.kind === 'sumo' && !p.pants && (p.st === 'free' || p.st === 'slide' || p.st === 'getup')) { if (this.tryHide(p, p.st !== 'free')) return; }
      p.sneak = I.hide && p.st === 'free' && p.kind === 'sumo';   // (hold I in the open: crouched, slow, harder to spot)
      // push (tap) / booty slam (hold)
      if (p.kind === 'sumo' && p.st === 'free') {
        if (I.push) p.pushHeld += dt; if (p.pushHeld > D.holdJ && I.push) { p.pushHeld = -99; p.st = 'slam'; p.t = 0; p.slamDone = false; }
        else if (I.pushR && p.pushHeld > 0) { this.push(p); }
        if (!I.push) p.pushHeld = 0;
      }
      if (p.kind === 'staff' && I.useP) this.search(p);
      if (p.kind === 'staff' && I.pushP) this.search(p);
      // the belly slide
      if (p.kind === 'sumo' && I.slideP && p.st === 'free' && !wet && !p.grabbedBy) { p.st = 'slide'; p.t = 0; p.cdir = I.mag > 0.3 && !this.fpv ? Math.atan2(I.mz, I.mx) : I.mag > 0.3 ? Math.atan2(I.mz, I.mx) : p.f; p.f = p.cdir; p.sv = D.slideV * (p.running ? D.slideRun : 1); this.sfx('whoosh', 0.5); }
      if (I.useP && p.kind === 'sumo' && p.st === 'free') this.use2(p);
      let spd = 0, mx = I.mx, mz = I.mz;
      p.running = p.st === 'free' && I.run && I.mag > 0.3 && !p.tired && !wet;
      if (p.running) { p.stam -= dt / D.runStam; if (p.stam <= 0) { p.stam = 0; p.tired = true; } } else { p.stam = Math.min(1, p.stam + dt * 0.3); if (p.tired && p.stam > 0.45) p.tired = false; }
      if (p.st === 'free') spd = wet ? D.wade : p.sneak ? 1.7 : p.running ? D.run : D.walk;
      if (p.st === 'slide') { if (I.mag > 0.3) p.cdir = lerpA(p.cdir, Math.atan2(I.mz, I.mx), dt * 1.4); p.f = p.cdir; const wf = this.wetAt(p.x, p.z); p.sv = Math.max(0, p.sv - (wf ? D.slideWet : D.slideDry) * dt);
        if (wf && this.fx.water && Math.random() < dt * 10) this.fx.water(p.x, p.z, 0.4, p.y); mx = Math.cos(p.cdir); mz = Math.sin(p.cdir); spd = p.sv;
        if (p.sv < 0.6) { p.st = 'getup'; p.t = 0; } if (inPool(p.x, p.z)) { p.st = 'free'; p.sv = 0; this.fx.water && this.fx.water(p.x, p.z, 4, POOL.water); this.sfx('thump', 4); } }
      if (p.st === 'getup' && p.t > D.getUp) { p.st = 'free'; p.t = 0; }
      if (p.st === 'busy' && p.t > 0.3) { p.st = 'free'; p.t = 0; }   // (a push, a look: over in a moment)
      if (p.st === 'slam') { if (!p.slamDone && p.t > D.slamLand) { p.slamDone = true; this.slamLand(p); } if (p.t > D.slam) { p.st = 'free'; p.t = 0; } }
      const go = p.st === 'slide' || (p.st === 'free' && I.mag > 0.3), rk = p.st === 'slide' ? 30 : 10;
      p.vx += ((go ? mx : 0) * spd - p.vx) * Math.min(1, dt * rk); p.vz += ((go ? mz : 0) * spd - p.vz) * Math.min(1, dt * rk);
      if (p.st === 'free' && I.mag > 0.3) p.f = lerpA(p.f, Math.atan2(I.mz, I.mx), dt * 12);
      p.x += p.vx * dt; p.z += p.vz * dt;
      const hit = this.collide(p, p.kind === 'staff' ? 0.4 : p.r); if (hit && p.st === 'slide') { p.st = 'getup'; p.t = 0; p.vx *= -0.3; p.vz *= -0.3; }
      const ty = inPool(p.x, p.z) ? (p.kind === 'staff' ? -0.55 : -0.62) : floorY(p.x, p.z); p.y += (ty - p.y) * Math.min(1, dt * 10);
      // two sumos don't pass through each other
      const o = this.other(p); if (!o.hidden && !o.sub && o.st !== 'grabbed' && !(this.mode === 'hide' && this.ph === 'hide')) { const dx = p.x - o.x, dz = p.z - o.z, d = Math.hypot(dx, dz), R = 1.1; if (d < R && d > 1e-4) { p.x = o.x + dx / d * R; p.z = o.z + dz / d * R; }
        if (p.st === 'slide' && d < 1.4) this.slideHit(p, o); }
    }
    frozen(p) { return (this.mode === 'hide' && this.ph === 'hide' && p.kind === 'staff') || this.ph === 'end'; }
    tryHide(p, fromSlide) {
      const near = (x, z, r) => Math.hypot(p.x - x, p.z - z) < r;
      for (const c of this.carts) if (near(c.x, c.z, fromSlide ? 2.1 : 1.8) && !this.ps.some((q) => q.hidden === c)) { p.hidden = c; p.st = 'free'; p.t = 0; p.vx = p.vz = 0; p.x = c.x; p.z = c.z; c.off = true; this.cartBox(c); this.sfx('whoosh', 0.3); return true; }
      for (let k = 0; k < LY.stalls.length; k++) { const q = LY.stalls[k]; if (near(q.x + 0.4, q.z, 1.6) && !this.ps.some((o) => o.hidden === 'stall' + k)) { p.hidden = 'stall' + k; p.st = 'free'; p.t = 0; p.vx = p.vz = 0; p.x = q.x + 0.2; p.z = q.z; const Dd = this.stallDoors && this.stallDoors[k]; if (Dd) Dd.rotation.y = 0; return true; } }
      if (inPool(p.x, p.z)) { p.sub = true; p.breath = D.breath; p.t = 0; p.vx = p.vz = 0; this.fx.water && this.fx.water(p.x, p.z, 2.5, POOL.water); return true; }
      return false;
    }
    unhide(p) {
      const h = p.hidden; p.hidden = null; p.t = 0;
      if (h && h.w) { h.off = false; this.cartBox(h); const a = p.f; p.x = h.x + Math.cos(a) * 1.5; p.z = h.z + Math.sin(a) * 1.5; this.collide(p, p.r); }
      else if (typeof h === 'string') { const k = +h.slice(5), q = LY.stalls[k], Dd = this.stallDoors && this.stallDoors[k]; if (Dd) Dd.rotation.y = -1.4; p.x = q.x + 1.7; p.z = q.z; p.f = 0; this.collide(p, p.r); }
    }
    push(p) {   // two hands, in front: staff go down; in pants tag, the pants come off
      p.st = 'busy'; p.t = 0; p.w.hand = 1;
      const fx = Math.cos(p.f), fz = Math.sin(p.f), inFront = (x, z, r) => { const dx = x - p.x, dz = z - p.z, d = Math.hypot(dx, dz); return d < r && (dx * fx + dz * fz) / (d || 1) > 0.2; };
      this.miniPuff(p.x + fx * 1.5, p.y + 0.5, p.z + fz * 1.5, 0.45, 8);   // (a puff off his palms: you see every push)
      for (const s of this.staff || []) if (s.mode !== 'down' && inFront(s.a.x, s.a.z, 2.0)) this.knock(s, fx, fz);
      { const o2 = this.other(p); if (this.mode !== 'tag' && !o2.hidden && !o2.sub && o2.st !== 'grabbed' && inFront(o2.x, o2.z, 1.9)) { o2.vx += fx * 6; o2.vz += fz * 6; } }   // (and the other sumo gets shoved along)
      const fr = this.other(p).grabbedBy; if (fr && fr.mode === 'hold' && Math.hypot(fr.a.x - p.x, fr.a.z - p.z) < 2.2) this.knock(fr, fr.a.x - p.x, fr.a.z - p.z);   // (a friend held: any push near his grabber knocks it off)
      const o = this.other(p); if (this.mode === 'tag' && o.pants && !o.hidden && inFront(o.x, o.z, 1.8)) this.steal(o, p);
      this.sfx('whoosh', 0.2);
    }
    slideHit(p, o) { if (this.mode === 'tag' && o.pants) this.steal(o, p); }
    slamLand(p) {   // down on his booty: everyone close is knocked over, a held friend is freed, the pants fly off whoever's wearing them
      this.miniPuff(p.x, p.y, p.z, 1.2, 12); this.sfx('thump', 9);
      for (const s of this.staff || []) if (s.mode !== 'down' && Math.hypot(s.a.x - p.x, s.a.z - p.z) < 2.4) this.knock(s, s.a.x - p.x, s.a.z - p.z);
      const o = this.other(p); if (this.mode === 'tag' && o.pants && !o.hidden && Math.hypot(o.x - p.x, o.z - p.z) < 2.4) this.steal(o, p);
    }
    knock(s, dx, dz) { const l = Math.hypot(dx, dz) || 1; if (s.target && s.target.grabbedBy === s) { s.target.grabbedBy = null; s.target.st = 'free'; s.target.t = 0; this.banner(s.target, 'FREE!', '#3a9a5e'); }
      s.mode = 'down'; s.t = 0; s.a.st = 'down'; s.a.t = 0; s.a.dur = D.downT; s.a.fallX = dx / l; s.a.fallZ = dz / l; s.path = null; this.puff(s.a.x, 0.4, s.a.z, 5, 0.3); }
    use2(p) {   // E: pick up your mawashi (co-op), the pants (tag)
      if (this.mode === 'coop') { const m = this.maw[p.i]; if (!p.maw && m && !m.taken && Math.hypot(p.x - m.x, p.z - m.z) < 1.5) { m.taken = true; m.g.visible = false; p.maw = true; this.banner(p, 'MAWASHI ON!', CSS[p.i]); this.sfx('whoosh', 0.4); } }
    }
    // ---- CO-OP HEIST
    setupCoop() {
      const spots = MAW_SPOTS.slice().sort(() => Math.random() - 0.5);
      this.maw = [0, 1].map((i) => { const [x, z] = spots[i], g = new THREE.Group(); g.position.set(x, floorY(x, z), z); this.G.add(g);
        const belt = new THREE.Mesh(new THREE.TorusGeometry(0.32, 0.1, 8, 18), S.Flat.mat(COL[i])); belt.rotation.x = Math.PI / 2; belt.position.y = 0.12; belt.castShadow = true; belt.userData.flatDone = true; g.add(belt);
        const ring = new THREE.Mesh(new THREE.RingGeometry(0.62, 0.78, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: COL[i], transparent: true, opacity: 0.8, depthWrite: false })); ring.position.y = 0.03; g.add(ring);
        return { x, z, hx: x, hz: z, g, taken: false }; });
      this.exit = { x: LY.backdoor.x - 2.2, z: (LY.backdoor.z0 + LY.backdoor.z1) / 2 };
      { const g = new THREE.Group(); g.position.set(this.exit.x, 0, this.exit.z); this.G.add(g); const ring = new THREE.Mesh(new THREE.RingGeometry(1.3, 1.6, 40).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x3a9a5e, transparent: true, opacity: 0.8, depthWrite: false })); ring.position.y = 0.04; g.add(ring); this.exitM = g; }
      this.staff = []; const kinds = ['fighter', 'grappler', 'rusher', 'thrower', 'staff'];
      for (let k = 0; k < D.staffN; k++) { let pt; do { pt = this.points[(Math.random() * this.points.length) | 0]; } while (pt[1] > -16);
        const a = { kind: kinds[k], x: pt[0], z: pt[1], y: 0, f: 0, vx: 0, vz: 0, st: 'free', t: 0, hp: 1, maxHp: 1, dead: false, engage: false };
        const v = new S.WorkerView(this.scene, kinds[k], k === 1, k % 4); v.walls = this.walls; if (v.pole && v.pole.parent) v.pole.parent.remove(v.pole);
        const ex = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.bangTex(), transparent: true, depthTest: false })); ex.scale.set(0.6, 0.6, 1); ex.visible = false; ex.renderOrder = 8; this.scene.add(ex);
        this.staff.push({ a, v, mode: 'patrol', t: 0, path: null, pi: 0, target: null, last: null, ex, repath: 0 }); }
      this.ph = 'play'; this.caughtN = 0; this.tStart = this.t;
      this.title('CO-OP HEIST', 'Find your mawashi (your colour), put it on (use), and both get out the kitchen back door');
    }
    bangTex() { if (this._bang) return this._bang; const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d'); x.fillStyle = '#dd5a42'; x.font = '900 56px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('!', 32, 34); this._bang = new THREE.CanvasTexture(c); return this._bang; }
    staffStep(s, dt) {
      const a = s.a; s.t += dt; a.t += dt;
      if (s.mode === 'down') { a.vx = a.vz = 0; if (s.t > D.downT) { s.mode = 'patrol'; s.t = 0; a.st = 'free'; s.path = null; } return; }
      if (s.mode === 'hold') { const p = s.target; a.vx = a.vz = 0; a.f = Math.atan2(p.z - a.z, p.x - a.x); a.st = 'act'; a.atk = 'grab';
        p.holdT = (p.holdT || 0) + dt; if (p.holdT > D.holdT) this.caught(p, s); return; }
      // who can he see?
      let seen = null, sd = 1e9;
      for (const p of this.ps) { if (p.hidden || p.sub || p.st === 'grabbed') continue; const dx = p.x - a.x, dz = p.z - a.z, d = Math.hypot(dx, dz);
        if (d > D.see * (p.st === 'slide' ? 0.6 : p.sneak ? 0.7 : 1) || Math.abs(p.y - a.y) > 1.2) continue; if (d > 0.8 && Math.abs(ang(Math.atan2(dz, dx) - a.f)) > D.seeHalf) continue; if (!this.clear(a.x, a.z, p.x, p.z)) continue;
        if (d < sd) { sd = d; seen = p; } }
      if (!seen) for (const p of this.ps) if (p.running && !p.hidden && Math.hypot(p.x - a.x, p.z - a.z) < 5 && s.mode === 'patrol') { s.mode = 'search'; s.t = 0; s.last = [p.x, p.z]; s.path = null; }   // (heard running)
      if (seen) { if (s.mode !== 'chase') { s.ex.visible = true; this.sfx('whoosh', 0.2); } s.mode = 'chase'; s.target = seen; s.last = [seen.x, seen.z]; s.lost = 0; }
      else if (s.mode === 'chase') { s.lost = (s.lost || 0) + dt; if (s.lost > 2.2 || (s.target && (s.target.hidden || s.target.sub))) { s.mode = 'search'; s.t = 0; s.path = null; } }
      s.ex.visible = s.mode === 'chase'; s.ex.position.set(a.x, a.y + 2.5, a.z);
      let tx = null, tz = null, sp = D.patrol;
      if (s.mode === 'chase') { const p = s.target; tx = p.x; tz = p.z; sp = D.chase;
        if (Math.hypot(p.x - a.x, p.z - a.z) < 1.0 && (p.st === 'free' || p.st === 'getup' || p.st === 'busy') && !p.grabbedBy) { s.mode = 'hold'; s.t = 0; p.st = 'grabbed'; p.grabbedBy = s; p.holdT = 0; p.vx = p.vz = 0; this.banner(p, 'GRABBED! Get your friend to push it off', '#dd5a42'); this.sfx('thump', 3); return; } }
      else if (s.mode === 'search') { [tx, tz] = s.last || [a.x, a.z]; sp = 2.2; if (Math.hypot(tx - a.x, tz - a.z) < 0.8) { a.f += dt * 1.6; if (s.t > 3.5) { s.mode = 'patrol'; s.path = null; } tx = null; } }
      else { if (!s.path || s.pi >= s.path.length) { const pt = this.points[(Math.random() * this.points.length) | 0]; s.path = this.navPath(a.x, a.z, pt[0], pt[1]) || [pt]; s.pi = 0; s.wait = Math.random() * 1.5; } }
      if (tx !== null && (s.repath -= dt) <= 0) { s.repath = 0.4; s.path = this.navPath(a.x, a.z, tx, tz) || [[tx, tz]]; s.pi = 0; }
      if (s.wait > 0 && s.mode === 'patrol') { s.wait -= dt; a.vx = a.vz = 0; return; }
      const pt = s.path && s.path[s.pi]; if (!pt) { a.vx = a.vz = 0; return; }
      const dx = pt[0] - a.x, dz = pt[1] - a.z, d = Math.hypot(dx, dz); if (d < 0.25) { s.pi++; return; }
      a.vx = dx / d * sp; a.vz = dz / d * sp; a.x += a.vx * dt; a.z += a.vz * dt; this.collide(a, 0.35); a.f = lerpA(a.f, Math.atan2(dz, dx), dt * 8); a.y = floorY(a.x, a.z); a.st = 'free';
    }
    caught(p, s) {
      s.mode = 'down'; s.t = D.downT - 1; s.a.st = 'free'; p.grabbedBy = null; p.holdT = 0; this.caughtN++;
      if (p.maw) { p.maw = false; const m = this.maw[p.i]; m.taken = false; m.g.visible = true; }
      this.place(p, START[p.i][0], START[p.i][1]); this.banner(p, 'CAUGHT! Back to the bath', '#dd5a42');
    }
    stepCoop(dt) {
      for (const s of this.staff) this.staffStep(s, dt);
      for (const m of this.maw) if (!m.taken) m.g.rotation.y += dt * 1.5;
      const out = this.ps.every((p) => p.maw && Math.hypot(p.x - this.exit.x, p.z - this.exit.z) < 2.0);
      if (out && this.ph === 'play') { this.ph = 'end'; const secs = Math.round(this.t - this.tStart); this.bigText('ESCAPED!', 'Both out in ' + secs + ' s · caught ' + this.caughtN + ' time' + (this.caughtN === 1 ? '' : 's') + ' · ' + this.again()); for (const p of this.ps) { p.st = 'win'; p.t = 0; } }
      for (const p of this.ps) this.hudSide(p, (p.maw ? 'MAWASHI ✓ · get to the back door (kitchen)' : 'Find your ' + (p.i ? 'RED' : 'BLUE') + ' mawashi') + (p.st === 'grabbed' ? ' · GRABBED ' + Math.max(0, D.holdT - (p.holdT || 0)).toFixed(1) : ''));
    }
    // ---- HIDE & SEEK
    setupHide() { this.round = 0; this.seeker = 0; for (const p of this.ps) p.score = 0; this.title('HIDE & SEEK', 'The owner counts to 15. Sumo: hide (a laundry cart, a toilet stall, under the bath water). Owner: find him (use / push to search)'); this.newRound(); }
    newRound() {
      this.round++; const sk = this.ps[this.seeker], hd = this.other(sk);
      this.makeSeeker(sk); this.makeSumo(hd);
      for (const p of this.ps) { if (p.hidden) this.unhide(p); }
      this.place(hd, 1.0, 1.0); this.place(sk, -6.0, 1.2, Math.PI / 2);   // (the owner counts off to one side, out of the way)
      this.ph = 'hide'; this.phT = D.hideT; this.found = false;
    }
    search(p) {   // the owner looks in the cart / stall / water right in front of him
      const hd = this.other(p); if (this.mode !== 'hide' || this.ph !== 'seek') return;
      const near = (x, z, r) => Math.hypot(p.x - x, p.z - z) < r;
      let f = false; if (hd.hidden && hd.hidden.w && near(hd.hidden.x, hd.hidden.z, 1.9)) f = true;
      if (typeof hd.hidden === 'string') { const q = LY.stalls[+hd.hidden.slice(5)]; if (near(q.x + 0.6, q.z, 2.6) && Math.abs(p.z - q.z) < 1.0) f = true; }   // (the stall right in front of him)
      if (hd.sub && near(hd.x, hd.z, 2.6)) f = true;
      p.st = 'busy'; p.t = 0;
      if (f) this.foundHim(p, hd);
    }
    foundHim(sk, hd) { if (this.found) return; this.found = true; if (hd.hidden) this.unhide(hd); hd.sub = false; sk.score++; this.ph = 'end'; this.phT = 3.2; this.bigText('FOUND!', (sk.i ? 'P2' : 'P1') + ' found the sumo'); this.sfx('thump', 6); }
    stepHide(dt) {
      const sk = this.ps[this.seeker], hd = this.other(sk);
      this.phT -= dt;
      if (this.ph === 'hide' && this.phT <= 0) { this.ph = 'seek'; this.phT = D.seekT; this.bigText('READY OR NOT!', ''); }
      else if (this.ph === 'seek') { if (!hd.hidden && !hd.sub && Math.hypot(sk.x - hd.x, sk.z - hd.z) < 1.2) this.foundHim(sk, hd);
        if (this.phT <= 0 && !this.found) { hd.score++; this.ph = 'end'; this.phT = 3.2; this.bigText('SAFE!', (hd.i ? 'P2' : 'P1') + ' stayed hidden'); } }
      else if (this.ph === 'end' && this.phT <= 0) {
        if (this.ps.some((p) => p.score >= D.toWin)) { const w = this.ps.find((p) => p.score >= D.toWin); this.ph = 'over'; this.bigText((w.i ? 'P2' : 'P1') + ' WINS', this.ps[0].score + ' – ' + this.ps[1].score + ' · ' + this.again()); }
        else { this.seeker = 1 - this.seeker; this.newRound(); } }
      const tm = Math.max(0, Math.ceil(this.phT));
      this.hudSide(sk, 'OWNER · ' + (this.ph === 'hide' ? 'COUNTING… ' + tm : this.ph === 'seek' ? 'FIND HIM · ' + tm + 's' : '') + ' · score ' + sk.score);
      this.hudSide(hd, 'SUMO · ' + (this.ph === 'hide' ? 'HIDE! ' + tm + 's' : this.ph === 'seek' ? 'STAY HIDDEN · ' + tm + 's' + (hd.sub ? ' · breath ' + hd.breath.toFixed(0) : '') : '') + ' · score ' + hd.score);
      this.cover(sk.i, this.ph === 'hide' ? 'COUNTING… ' + tm : '');
    }
    // ---- PANTS TAG
    setupTag() {
      for (const p of this.ps) p.score = 0;
      const g = new THREE.Group(); this.G.add(g); const belt = new THREE.Mesh(new THREE.TorusGeometry(0.32, 0.1, 8, 18), S.Flat.mat(0xf2cf4a)); belt.rotation.x = Math.PI / 2; belt.position.y = 0.12; belt.castShadow = true; belt.userData.flatDone = true; g.add(belt);
      this.pantsM = { g, x: 1.0, z: -20.0, free: true }; g.position.set(1.0, floorY(1, -20), -20);
      this.ph = 'play'; this.title('PANTS TAG', 'Wear the golden pants to score. Steal them with a push, a belly slide into them, or a booty slam. First to ' + D.tagWin);
    }
    steal(from, by) { if (by.lock > 0) return; from.pants = false; from.lock = 1.2; const a = Math.random() * 6.28, x = from.x + Math.cos(a) * 2.2, z = from.z + Math.sin(a) * 2.2, q = { x, z }; this.collide(q, 0.5);
      const P = this.pantsM; P.free = true; P.x = q.x; P.z = q.z; P.g.position.set(q.x, floorY(q.x, q.z), q.z); P.g.visible = true; this.banner(from, 'PANTS GONE!', '#dd5a42'); this.sfx('thump', 5); this.puff(from.x, 0.6, from.z, 6, 0.3); }
    stepTag(dt) {
      const P = this.pantsM;
      if (P.free) { P.g.rotation.y += dt * 2; for (const p of this.ps) if (p.lock <= 0 && !p.hidden && !p.sub && Math.hypot(p.x - P.x, p.z - P.z) < 1.0) { P.free = false; P.g.visible = false; p.pants = true; this.banner(p, 'PANTS ON! Run!', '#e2b85e'); this.sfx('whoosh', 0.4); break; } }
      for (const p of this.ps) { if (p.pants && !p.hidden && !p.sub && this.ph === 'play') p.score += dt;
        this.hudSide(p, (p.pants ? 'WEARING THE PANTS' : 'GET THE PANTS') + ' · ' + Math.floor(p.score) + ' / ' + D.tagWin); }
      if (this.ph === 'play') { const w = this.ps.find((p) => p.score >= D.tagWin); if (w) { this.ph = 'over'; this.bigText((w.i ? 'P2' : 'P1') + ' WINS', this.again()); for (const p of this.ps) { p.st = p === w ? 'win' : 'free'; p.t = 0; } } }
    }
    again() { return 'ENTER: play again · ESC: menu'; }
    // ---- the loop
    frame(dt) {
      if (!this.scene) return;
      this.acc += Math.min(dt, 0.1); let k = 0;
      while (this.acc >= STEP && k < 8) { this.step2(STEP); this.acc -= STEP; k++; }
      if ((this.ph === 'over' || (this.mode === 'coop' && this.ph === 'end')) && this.keys.Enter) { this.keys.Enter = false; const m = this.mode; this.stop(); this.g.camp = null; this.g.startParty(m); return; }
      this.draw2(dt);
    }
    step2(dt) {
      this.t += dt; this.puffStep(dt);
      for (const p of this.ps) { this.readInput(p, dt); this.stepPlayer(p, dt); }
      if (this.mode === 'coop') this.stepCoop(dt); else if (this.mode === 'hide') this.stepHide(dt); else this.stepTag(dt);
      for (const c of this.carts) if (!this.ps.some((p) => p.hidden === c)) { if (c.off) { c.off = false; this.cartBox(c); } }
    }
    // ---- drawing: two cameras, side by side
    draw2(dt) {
      const T = this.t;
      for (const p of this.ps) this.drawPlayer(p, dt, T);
      for (const s of this.staff || []) { s.v.update(s.a, Math.max(dt, 1e-4), T); }
      this.fx.update && this.fx.update(dt);
      const r = this.R.r, W = innerWidth, H = innerHeight, hw = this.cpu ? W : Math.floor(W / 2);
      r.setScissorTest(true);
      for (const p of this.cpu ? [this.ps[0]] : this.ps) {
        const cam = this.cams[p.i]; cam.aspect = hw / H; cam.updateProjectionMatrix();
        if (this.fpv) this.behindCam(p, cam, dt);
        else { const tgt = new THREE.Vector3(p.x, Math.max(0, p.y), p.z - 2.6); p.camT.lerp(tgt, 1 - Math.exp(-dt * 4));
          const dist = 15, ch = 0.64, cz = Math.sqrt(1 - ch * ch); cam.position.set(p.camT.x, p.camT.y + dist * ch, p.camT.z + dist * cz); cam.lookAt(p.camT.x, p.camT.y + 0.6, p.camT.z); }
        cam.updateMatrixWorld();
        for (const q of this.ps) this.placeMosaic(q, cam);
        const x = p.i * hw; r.setViewport(x, 0, hw, H); r.setScissor(x, 0, hw, H); r.render(this.scene, cam);
      }
      r.setScissorTest(false); r.setViewport(0, 0, W, H);
    }
    behindCam(p, cam, dt) {   // third person: behind him and a little above, pulled in when a wall gets between; the mouse (or arrows / right stick) swings it round
      if (p.yaw === undefined) p.yaw = p.f;
      const yaw = p.yaw, pt = p.pitch || 0, lay = p.st === 'slide' || (p.st === 'getup' && p.t < D.getUp * 0.55), s = p.v.s || 1;
      let tx = p.x, tz = p.z, ty = p.y + (p.kind === 'staff' ? 1.5 : 1.55 * s) - (lay ? 0.8 : 0);
      if (p.hidden && p.hidden.w) { tx = p.hidden.x; tz = p.hidden.z; ty = 1.3; } if (p.sub) ty = 0.4;
      const BACK = 4.2; let d = BACK; while (d > 0.8 && this.camHit(tx, tz, tx - Math.cos(yaw) * d, tz - Math.sin(yaw) * d)) d -= 0.3;
      const up = (1.25 - pt * 2.2) * (0.45 + 0.55 * d / BACK), want = new THREE.Vector3(tx - Math.cos(yaw) * d, ty + up, tz - Math.sin(yaw) * d);
      if (!p.cpos) p.cpos = want.clone(); p.cpos.lerp(want, 1 - Math.exp(-dt * 12));
      cam.position.copy(p.cpos); cam.lookAt(tx + Math.cos(yaw) * 2.4, ty - 0.15 + pt * 2.2, tz + Math.sin(yaw) * 2.4);
    }
    camHit(x0, z0, x1, z1) { for (let k = 1; k <= 12; k++) { const t = k / 12, x = x0 + (x1 - x0) * t, z = z0 + (z1 - z0) * t; for (const q of this.camWalls) if (x > q.x0 - 0.25 && x < q.x1 + 0.25 && z > q.z0 - 0.25 && z < q.z1 + 0.25) return true; } return false; }
    drawPlayer(p, dt, T) {
      if (p.kind === 'staff') {
        const sv = p.staffV, a = p.a || (p.a = { kind: 'staff', x: 0, z: 0, y: 0, f: 0, vx: 0, vz: 0, st: 'free', t: 0, hp: 1, maxHp: 1, dead: false, engage: false });
        a.x = p.x; a.z = p.z; a.y = p.y; a.f = p.f; a.vx = p.vx; a.vz = p.vz; a.st = p.st === 'busy' ? 'act' : 'free'; a.atk = 'grab'; a.t = p.t;
        sv.update(a, Math.max(dt, 1e-4), T); sv.root.visible = !(this.mode === 'hide' && this.ph === 'hide' && false);
        p.mosaic.s.visible = false; return; }
      const v = p.v, w = p.w;
      if (S.SoftSumo && S.SoftSumo.loaded && !v.soft) { S.SoftSumo.attach(v, { noBlob: true, booty: 2.2 }); for (const m of v.soft.mats) if (/mawashi/i.test(m.name || '')) m.color.set(this.mode === 'tag' ? 0xe2b85e : COL[p.i]); }
      const dressed = p.maw || p.pants;
      if (v.soft) for (const m of v.soft.mats) if (/mawashi/i.test(m.name || '')) m.visible = dressed;
      w.x = p.x; w.z = p.z; w.y = 0; w.f = p.f; w.fx = Math.cos(p.f); w.fz = Math.sin(p.f); w.vx = p.vx; w.vz = p.vz; w.spd = Math.hypot(p.vx, p.vz);
      const lay = p.st === 'slide' || (p.st === 'getup' && p.t < D.getUp * 0.55);
      const nst = p.st === 'win' ? 'win' : lay ? 'charge' : p.st === 'getup' ? 'recover' : p.st === 'grabbed' ? 'stun' : p.st === 'busy' ? 'palm' : p.st === 'slam' ? (p.t < 0.27 ? 'brace' : 'bslam') : 'free';
      if (w.st !== nst) { w.st = nst; w.t = 0; } else w.t = p.t;
      w.torpedo = lay; w.slide = lay; w.slamAir = p.st === 'slam' && p.t < D.slamLand; w.fxs = {}; w.hunch = p.sneak ? 0.55 : 0; w.tiptoe = p.sneak ? 1 : 0; w.crouchT = 0; w.relaxed = true; w.carry = null; w.armHeld = null;
      v.update(w, Math.max(dt, 1e-4), T);
      let y = p.y; if (lay) y -= 0.55 * v.s * Math.min(1, (v.tilt || 0) / 1.4);
      if (p.st === 'slam') { const u = p.t / D.slamLand; if (u > 0.3 && u < 1) y += 1.1 * v.s * Math.sin(Math.PI * Math.pow((u - 0.3) / 0.7, 0.7)); else if (u >= 1) y -= 0.42 * v.s * Math.max(0, 1 - (p.t - D.slamLand) / 0.35); }
      if (p.sub) y = -1.7;
      v.root.position.y += y; v.root.visible = !p.hidden && !(this.mode === 'hide' && p.kind === 'staff');
      if (v.soft) { const want = lay ? 0.3 : p.st === 'slam' && p.t > D.slamLand ? 0.14 : 0; p.jig = (p.jig || 0) + (want - (p.jig || 0)) * Math.min(1, dt * 10); if (p.jig > 0.002 || p.jigOn) { const ph = T * 22, bo = (x) => Math.max(0, Math.sin(x)) * 1.3; S.SoftSumo.jiggle(v, p.jig * bo(ph), p.jig * bo(ph + Math.PI)); p.jigOn = p.jig > 0.002; } }
      // a booty out of the cart he's hiding in
      if (p.hidden && p.hidden.w) { if (!p.cb) { p.cb = this.bootyProp(); p.cb.scale.setScalar(0.9); } const c = p.hidden; if (p.cb.parent !== c.m) c.m.add(p.cb); p.cb.visible = true; p.cb.position.set(0.05, 1.0, 0); p.cb.rotation.set(-Math.PI / 2 + 0.25, 0, Math.sin(T * 2.2) * 0.06); p.cb.userData.strip.visible = p.cb.userData.band.visible = dressed; }
      else if (p.cb) p.cb.visible = false;
      p.mosaic.s.visible = p.mosaicOn = !dressed && v.root.visible && p.y > -0.3 && !lay;
    }
    placeMosaic(p, cam) {
      const m = p.mosaic; if (p.mosaicOn === undefined) p.mosaicOn = m.s.visible; m.s.visible = p.mosaicOn; if (!m.s.visible) return; const v = p.v;
      if ((cam.position.x - p.x) * Math.cos(p.f) + (cam.position.z - p.z) * Math.sin(p.f) < 0) { m.s.visible = false; return; }   // (seen from behind: his booty, no censor)
      if ((m.t -= 0.016) <= 0) { m.t = 0.1; const g = m.cv.getContext('2d'), sk = ['#e9b894', '#d9a07c', '#f0c8a8', '#c98a6a', '#e0ac88']; g.clearRect(0, 0, 8, 5);
        for (let y = 0; y < 5; y++) for (let x = 0; x < 8; x++) { if ((x === 0 || x === 7) && Math.random() < 0.6) continue; g.fillStyle = sk[(Math.random() * sk.length) | 0]; g.fillRect(x, y, 1, 1); } m.s.material.map.needsUpdate = true; }
      const s = v.s, hip = new THREE.Vector3(0, CENSOR.y * s, 0); v.body.updateWorldMatrix(true, false); v.body.localToWorld(hip); const to = cam.position.clone().sub(hip).normalize();
      m.s.position.copy(hip).addScaledVector(to, 0.95 * s); m.s.scale.set(CENSOR.w * s, CENSOR.h * s, 1);
    }
    // ---- HUD: one panel per player, a title card, big result text, a cover for the counting owner
    buildHud() {
      const h = this.hud = document.createElement('div'); h.id = 'partyHud';
      h.innerHTML = '<style>#partyHud{position:fixed;inset:0;pointer-events:none;z-index:6;font-family:"Barlow Condensed",sans-serif;color:#3a3440}' +
        '#partyHud .mid{position:absolute;left:50%;top:0;bottom:0;width:4px;margin-left:-2px;background:#3a3440}' +
        '#partyHud .side{position:absolute;top:14px;padding:6px 12px;border-radius:10px;background:rgba(255,250,240,.92);font-weight:800;font-size:19px}#partyHud .s0{left:16px}#partyHud .s1{left:calc(50% + 16px)}' +
        '#partyHud .bn{position:absolute;top:58px;font-weight:900;font-size:22px;opacity:0;transition:opacity .25s;text-shadow:0 2px 0 rgba(255,255,255,.8)}#partyHud .b0{left:16px}#partyHud .b1{left:calc(50% + 16px)}#partyHud .bn.on{opacity:1}' +
        '#partyHud .big{position:absolute;left:0;right:0;top:34%;text-align:center;font-weight:900;font-size:76px;color:#d8262e;text-shadow:0 4px 0 #fff;opacity:0;transition:opacity .3s}#partyHud .big.on{opacity:1}#partyHud .big small{display:block;font-size:24px;color:#3a3440;text-shadow:none}' +
        '#partyHud .card{position:absolute;left:50%;bottom:24px;transform:translateX(-50%);background:rgba(30,26,36,.88);color:#f4efe6;padding:12px 18px;border-radius:12px;font-size:17px;font-weight:700;text-align:center;max-width:88vw;transition:opacity .5s}#partyHud .card b{color:#f2cf4a;font-size:24px;display:block}' +
        '#partyHud .cov{position:absolute;top:0;bottom:0;width:50%;background:#1d2236;color:#f4efe6;display:none;align-items:center;justify-content:center;font-weight:900;font-size:54px}#partyHud .c0{left:0}#partyHud .c1{left:50%}</style>' +
        (this.cpu ? '<style>#partyHud .mid,#partyHud .c1{display:none!important}#partyHud .c0{width:100%}#partyHud .s1,#partyHud .b1{left:auto;right:16px}</style>' : '') + '<div class="cov c0"></div><div class="cov c1"></div><div class="mid"></div><div class="side s0"></div><div class="side s1"></div><div class="bn b0"></div><div class="bn b1"></div><div class="big"></div><div class="card"></div>';
      document.body.appendChild(h);
    }
    title(name, how) { const c = this.hud.querySelector('.card'); c.innerHTML = '<b>' + name + '</b>' + how + (this.fpv ? '<br><span style="color:#f2cf4a">THIRD PERSON: the mouse turns the camera (click to capture it) · P2 turns it with left / right</span>' : '') + '<br><span style="color:#5a8fd0">P1: ' + HELP[0] + '</span><br><span style="color:#dd5a42">P2: ' + (this.cpu ? 'COMPUTER' : HELP[1]) + '</span><br>ESC: menu';
      c.style.opacity = 1; clearTimeout(this.cardT); this.cardT = setTimeout(() => { if (this.hud) c.style.opacity = 0; }, 9000); }
    hint(p) {   // under each panel: what the buttons do right here
      const near = (x, z, r) => Math.hypot(p.x - x, p.z - z) < r, K = p.i === 0 ? { use: 'K', hide: 'I', push: 'J' } : { use: ',', hide: 'M', push: '.' };
      if (p.kind === 'staff') return this.ph === 'seek' ? K.use + ': search the cart / stall / water in front of you' : '';
      if (p.hidden || p.sub) return K.hide + ': come out' + (p.sub ? ' (breath ' + p.breath.toFixed(0) + ')' : '');
      if (p.st === 'grabbed') return 'GRABBED: your friend has to push it off!';
      const o = this.other(p); if (o.grabbedBy && near(o.x, o.z, 3)) return K.push + ': push them off your friend!';
      if (this.mode === 'coop' && !p.maw && this.maw && near(this.maw[p.i].x, this.maw[p.i].z, 1.6)) return K.use + ': put on your mawashi';
      if (!p.pants && (this.carts.some((c) => near(c.x, c.z, 1.8)) || LY.stalls.some((q) => near(q.x + 0.4, q.z, 1.6)) || inPool(p.x, p.z))) return K.hide + ': hide here';
      return '';
    }
    hudSide(p, txt) { const h = this.hint(p); if (h) txt += '  ·  ' + h; const e = this.hud.querySelector('.s' + p.i); if (e.textContent !== txt) e.textContent = txt; e.style.borderLeft = '6px solid ' + CSS[p.i]; }
    banner(p, txt, col) { const e = this.hud.querySelector('.b' + p.i); e.textContent = txt; e.style.color = col || '#3a3440'; e.classList.add('on'); clearTimeout(e._t); e._t = setTimeout(() => e.classList.remove('on'), 1800); }
    bigText(t, sub) { const e = this.hud.querySelector('.big'); e.innerHTML = t + (sub ? '<small>' + sub + '</small>' : ''); e.classList.add('on'); clearTimeout(this.bigT); if (this.ph !== 'over' && !(this.mode === 'coop' && this.ph === 'end')) this.bigT = setTimeout(() => { if (this.hud) e.classList.remove('on'); }, 2200); }
    cover(i, txt) { for (const k of [0, 1]) { const e = this.hud.querySelector('.c' + k); const on = k === i && !!txt; e.style.display = on ? 'flex' : 'none'; if (on && e.textContent !== txt) e.textContent = txt; } }
  }
  S.Party = Party;
})();
