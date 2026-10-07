'use strict';
// TEST LEVEL: THE BATHHOUSE. The sumo wakes up by the bath with no mawashi (pixel-censored). The bath and showers are
// safe (everyone's naked there); the locker room, the lobby and reception are not.
//   1 find your locker  ->  it's locked: the key must be in the bath where you woke up
//   2 back to the bath  ->  not there: forget it, smash the locker open (hold L: charge into it)
//   3 the crash brings the staff running, and nothing in there fits  ->  maybe the storage room behind reception
//   4 throw a bucket to draw the receptionist away, slip behind the counter into storage  ->  a cardboard box: pants
// Staff walk fixed routes; their view is a cone on the floor, blocked by walls, lockers, counters, carts and plants.
// I: crouch (slow, and they have to be closer). Running over a puddle: you slip, and the splash carries.
(function () {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ang = (a) => Math.atan2(Math.sin(a), Math.cos(a));
  const lerpA = (a, b, k) => a + ang(b - a) * Math.min(1, k);
  const STEP = 1 / 60;
  const SAFE_Z = -27;          // north of this: the bath and the showers (nobody minds a naked man there)
  // restart points nobody is looking at: the shower side of the locker door, the corner just inside the lobby door
  const CP = { lockN: { x: 5.8, z: -25.6, f: -Math.PI / 2 }, lockS: { x: -11.2, z: -46.1, f: Math.PI / 2 }, lobby: { x: -11.2, z: -48.1, f: -Math.PI / 2 } };
  const CENSOR = { w: 0.8, h: 0.5, y: -0.55 };   // hip height below the body centre (the box-pants sit at -0.62)   // the pixel block: his bottom / crotch only

  class Stealth {
    constructor(game) { this.g = game; }

    // ============================================================== setup / teardown
    start() {
      const g = this.g;
      this.R = g.R; this.t = 0; this.acc = 0; this.paused = false; this.over = null; this.spotted = 0;
      this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(0xd9e6e9);
      this.cam = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 200);
      this.fx = new S.FX(this.scene); this.fx.scene = this.scene; this.fx.noMarks = true;
      this.flat = { lights: S.Flat.lights(this.scene, { r: 22 }) };
      const r = this.R.r; r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
      const vg = document.getElementById('vignette'); if (vg) vg.style.display = 'none';
      this.walls = []; this.blockers = []; this.puddles = []; this.buckets = [];
      this.build(); this.buildNav(); this.flying = []; this.grace = 0;
      this.ctrl = new S.Controller(new S.KeySource(S.MAPS.solo, 0));
      this.keys = {};
      this.kd = (e) => { this.keys[e.code] = true; }; this.ku = (e) => { this.keys[e.code] = false; };
      addEventListener('keydown', this.kd); addEventListener('keyup', this.ku);
      // the player: the soft sumo, no mawashi
      const arch = S.ARCH[g.sel && g.sel.c1 !== undefined ? g.sel.c1 : 0];
      this.P = { x: -8.4, z: 1.4, f: -Math.PI / 2, vx: 0, vz: 0, r: 0.7, st: 'free', t: 0, dur: 0, crouch: 0, chargeT: 0, cd: 0, held: null };
      this.view = new S.WrestlerView(this.scene, arch, this.fx, S.DEF_EQ); this.view.viewer = 0; this.view.match = null;
      this.w = { x: 0, z: 0, y: 0, f: 0, fx: 0, fz: 1, vx: 0, vz: 0, st: 'free', t: 0, dur: 1, fxs: {}, a: arch, idx: 0, szCur: 1, squash: 0, bal: 1, tx: 0, tz: 0, power: 0, pre: null, preT: 0,
        hand: 0, windPow: 0, charges: 0, uprightT: 0, throatT: 0, lifted: false, down: false, fallX: 0, fallZ: 1, clinch: null, slideT: 0, spd: 0, crouchT: 0, lean: 0, gulpI: -1, contact: false, fwdIn: 0, ddx: 0, ddz: 0, boomT: 0, relaxed: true };
      this.mosaic = this.makeMosaic();
      this.npcs = this.makeNpcs();
      this.stage = 'locker'; this.cp = { x: this.P.x, z: this.P.z, f: this.P.f };
      this.camT = new THREE.Vector3(this.P.x * 0.65, 0, this.P.z - 2.6);
      this.buildHud();
      this.resize = () => { this.cam.aspect = innerWidth / innerHeight; this.cam.updateProjectionMatrix(); if (this.fx.pmat) this.fx.pmat.uniforms.uScale.value = innerHeight * r.getPixelRatio() / (2 * Math.tan(this.cam.fov * Math.PI / 360)); };
      addEventListener('resize', this.resize); this.resize();
      this.objective('Find your LOCKER (through the showers)');
      this.think('...Huh? I fell asleep in the bath... and where is my mawashi?!', 3.4);
      this.later(3.6, () => this.think('In here nobody minds. Out by the lockers, nobody can see me like this.', 3.6));
      if (g.audio && g.audio.swell) g.audio.swell(0.3, 1.2);
    }
    stop() {
      removeEventListener('resize', this.resize); removeEventListener('keydown', this.kd); removeEventListener('keyup', this.ku);
      if (this.hud) this.hud.remove();
      this.R.r.shadowMap.enabled = !!this.R.flat;
      const vg = document.getElementById('vignette'); if (vg) vg.style.display = this.R.flat ? 'none' : '';
      this.scene = null;
    }
    later(sec, fn) { (this.timers || (this.timers = [])).push({ t: sec, fn }); }

    // ============================================================== the bathhouse
    build() {
      const M = (c, o) => S.Flat.mat(c, o), G = new THREE.Group(); this.scene.add(G); this.G = G;
      const box = (x0, x1, z0, z1, y0, h, col, o) => {
        o = o || {};
        const m = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, h, z1 - z0), M(col, o.mat)); m.position.set((x0 + x1) / 2, y0 + h / 2, (z0 + z1) / 2);
        m.castShadow = o.cast !== false; m.receiveShadow = true; G.add(m);
        if (o.solid !== false) { const w = { x0: Math.min(x0, x1), x1: Math.max(x0, x1), z0: Math.min(z0, z1), z1: Math.max(z0, z1), tall: !!o.tall }; this.walls.push(w); m.userData.wall = w; }
        return m;
      };
      const floor = (x0, x1, z0, z1, col, y) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, z1 - z0).rotateX(-Math.PI / 2), M(col)); m.position.set((x0 + x1) / 2, y || 0, (z0 + z1) / 2); m.receiveShadow = true; G.add(m); return m; };
      // cut-away walls: low, so the high camera always sees him, but nobody sees through them
      const wall = (x0, x1, z0, z1, col) => { const m = box(x0, x1, z0, z1, 0, 1.15, col || 0xe8ddc9, { tall: true });
        box(x0 - 0.03, x1 + 0.03, z0 - 0.03, z1 + 0.03, 1.15, 0.07, new THREE.Color(col || 0xe8ddc9).multiplyScalar(0.72).getHex(), { solid: false }); return m; };
      // a doorway in a wall along x at z: dark wooden posts, a mat on the floor
      const door = (gx0, gx1, z, col) => {
        for (const x of [gx0 - 0.14, gx1 + 0.14]) box(x - 0.16, x + 0.16, z - 0.3, z + 0.3, 0, 1.55, 0x7a5a44);
        const mat = new THREE.Mesh(new THREE.PlaneGeometry(gx1 - gx0 - 0.4, 0.9).rotateX(-Math.PI / 2), M(col || 0x8fb0a8)); mat.position.set((gx0 + gx1) / 2, 0.012, z); G.add(mat);
      };
      const label = (text, sub, x, z, w, h, bg, fg, rz) => {
        const cv = document.createElement('canvas'); cv.width = 512; cv.height = 256; const c = cv.getContext('2d');
        c.fillStyle = bg; c.fillRect(0, 0, 512, 256); c.fillStyle = fg; c.textAlign = 'center'; c.textBaseline = 'middle';
        c.font = '120px "Dela Gothic One", sans-serif'; c.fillText(text, 256, sub ? 100 : 128); if (sub) { c.font = '800 46px "Barlow Condensed", sans-serif'; c.fillText(sub, 256, 205); }
        const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), M(0xffffff, { map: new THREE.CanvasTexture(cv) })); m.position.set(x, 0.02, z); m.rotation.set(-Math.PI / 2, 0, rz || 0); G.add(m); return m;
      };
      const plant = (x, z, s) => { const p = new THREE.Mesh(new THREE.SphereGeometry(0.8 * s, 14, 10), M(0x6aa55a)); p.position.set(x, 1.15 * s, z); p.castShadow = true; G.add(p); box(x - 0.42, x + 0.42, z - 0.42, z + 0.42, 0, 0.6, 0xcf7a5a); this.blockers.push({ x, z, r: 0.8 * s }); };
      const puddle = (x, z, rx, rz) => {
        const sh = new THREE.Shape(); for (let k = 0; k <= 24; k++) { const a = k / 24 * Math.PI * 2, rr = 1 + 0.12 * Math.sin(a * 3 + x) + 0.08 * Math.sin(a * 5 + z); const px = Math.cos(a) * rx * rr, pz = Math.sin(a) * rz * rr; if (k) sh.lineTo(px, pz); else sh.moveTo(px, pz); }
        const m = new THREE.Mesh(new THREE.ShapeGeometry(sh).rotateX(Math.PI / 2), M(0xa8cdea, { side: THREE.DoubleSide })); m.position.set(x, 0.015, z); m.receiveShadow = true; G.add(m);
        const hl = new THREE.Mesh(new THREE.PlaneGeometry(rx * 0.7, 0.08).rotateX(-Math.PI / 2), M(0xe3f1fb)); hl.position.set(x - rx * 0.1, 0.02, z - rz * 0.25); G.add(hl);
        this.puddles.push({ x, z, rx, rz });
      };
      const bucket = (x, z) => { const b = new THREE.Group(); const m = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.24, 0.42, 16), M(0xd3ab7a)); m.position.y = 0.21; m.castShadow = true; b.add(m);
        const band = new THREE.Mesh(new THREE.CylinderGeometry(0.31, 0.31, 0.06, 16), M(0x8c6648)); band.position.y = 0.3; b.add(band); b.position.set(x, 0, z); G.add(b); this.buckets.push({ m: b, x, z, y: 0, state: 'floor', x0: x, z0: z }); };

      // ---------------------------------------------------------------- floors and the outer shell
      floor(-30, 30, -80, 20, 0xcfd8d4, -0.02);   // outside the building: a plain base, never a void
      floor(-12, 12, -16, 4.4, 0xd7dfdc); floor(-12, 12, -27, -16, 0xdde5e3); floor(-12, 12, -47, -27, 0xd9be92); floor(-12, 12, -60, -47, 0xe2d2b4); floor(6, 12, -68, -60, 0xcbb79a);
      for (let z = 3.4; z > -27; z -= 1.6) floor(-12, 12, z - 0.03, z + 0.03, 0xc5d0cc, 0.002);   // tile joints
      wall(-12.4, -12, -60, 4.4); wall(12, 12.4, -68, 4.4); wall(-12.4, 12.4, 4.4, 4.8);
      // ---- BATH HALL (safe): the big bath, wash stools, plants. The spot he woke up on.
      box(-3.2, 9.2, -12.2, -1.8, 0, 0.55, 0xc9a06a, { tall: false });                                  // the hinoki rim (nobody walks through the water)
      const water = new THREE.Mesh(new THREE.PlaneGeometry(11.6, 9.6).rotateX(-Math.PI / 2), M(0x9cc6e8)); water.position.set(3, 0.57, -7); G.add(water);
      const towel = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.06, 0.8), M(0xf6eddc)); towel.position.set(-8.4, 0.03, 1.4); G.add(towel);   // where he woke up
      for (const z of [-2, -5, -8, -11, -14]) { const st = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.3, 0.32, 14), M(0xe2b85e)); st.position.set(-11, 0.16, z); st.castShadow = true; G.add(st);
        const bk = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.18, 0.3, 14), M(0xd3ab7a)); bk.position.set(-11.4, 0.15, z + 0.6); G.add(bk); }
      plant(10.6, 2.8, 1); plant(10.6, -14.6, 0.9); plant(-10.8, 3.2, 0.8);
      wall(-12, -2.2, -16.2, -15.8, 0xbcd3d6); wall(2.2, 12, -16.2, -15.8, 0xbcd3d6); door(-2.2, 2.2, -16);   // to the showers: x -2.2 .. 2.2
      // his wash bucket (the yellow plastic kind every bathhouse has), by the towel he slept on: where he left the key... he thinks
      this.washB = new THREE.Group(); { const y = M(0xf2cf4a), w = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.22, 0.34, 18, 1, true), M(0xf2cf4a, { side: THREE.DoubleSide })); w.position.y = 0.17; w.castShadow = true;
        const bt = new THREE.Mesh(new THREE.CircleGeometry(0.22, 18).rotateX(-Math.PI / 2), M(0xf2cf4a, { side: THREE.DoubleSide })); bt.position.y = 0.01; const rim = new THREE.Mesh(new THREE.TorusGeometry(0.3, 0.025, 6, 20).rotateX(Math.PI / 2), M(0xe0b43a)); rim.position.y = 0.34;
        const tw = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.05, 0.22), M(0xf6eddc)); tw.position.set(0, 0.35, 0); tw.rotation.y = 0.5; this.washB.add(w, bt, rim, tw); this.washTowel = tw; }
      this.washB.position.set(-6.9, 0, 2.3); G.add(this.washB); this.washSpot = { x: -6.9, z: 2.3 };
      label('男湯', 'BATH', 0, -14.6, 2.4, 1.1, '#2f4b7c', '#f6f1e6');
      // ---- SHOWERS (safe): stalls with low dividers, stools, a bench down the middle
      for (const sd of [-1, 1]) for (const z of [-18, -21, -24]) box(sd > 0 ? 9.6 : -12, sd > 0 ? 12 : -9.6, z - 0.12, z + 0.12, 0, 1.0, 0xc4d8dc);
      for (const sd of [-1, 1]) for (const z of [-19.5, -22.5, -25.5]) { const st = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.3, 0.32, 14), M(0xa8dcc6)); st.position.set(sd * 10.6, 0.16, z); G.add(st); }
      box(-2.5, 2.5, -21.9, -21.1, 0, 0.45, 0xbb8b5e);                                                  // bench (solid)
      wall(-12, 4, -27.2, -26.8, 0xe6d6bb); wall(7.6, 12, -27.2, -26.8, 0xe6d6bb); door(4, 7.6, -27, 0xcf9a7a);   // to the lockers: x 4 .. 7.6
      label('シャワー', 'SHOWERS', 0, -17.4, 2.6, 1.1, '#84b5ad', '#ffffff');
      // ---- LOCKER ROOM (sneak): banks of lockers, benches, puddles
      const lockerTex = (() => { const cv = document.createElement('canvas'); cv.width = 256; cv.height = 128; const c = cv.getContext('2d');
        c.fillStyle = '#9db5cb'; c.fillRect(0, 0, 256, 128); c.fillStyle = '#86a2bc'; for (let x = 0; x < 256; x += 64) c.fillRect(x, 0, 3, 128); c.fillRect(0, 62, 256, 3);
        c.fillStyle = '#f2ece0'; for (let x = 0; x < 256; x += 64) for (const y of [24, 88]) c.fillRect(x + 44, y, 10, 14); const t = new THREE.CanvasTexture(cv); t.wrapS = THREE.RepeatWrapping; return t; })();
      const bank = (x0, x1, z0, z1) => { const t = lockerTex.clone(); t.needsUpdate = true; t.repeat.set(Math.max(1, (x1 - x0) / 2), 1); return box(x0, x1, z0, z1, 0, 1.75, 0xffffff, { mat: { map: t }, tall: true }); };
      this.banks = [bank(-9, -1, -31.7, -31), bank(2, 10, -31.7, -31), bank(-7, 1, -36.7, -36), bank(4, 12, -36.7, -36), bank(-12, -4, -41.7, -41), bank(-1, 8, -41.7, -41)];
      box(-6, -2, -34.2, -33.6, 0, 0.45, 0xbb8b5e); box(5, 9, -39.4, -38.8, 0, 0.45, 0xbb8b5e); box(-9, -5, -39.4, -38.8, 0, 0.45, 0xbb8b5e);   // benches (solid)
      puddle(-1.2, -29.2, 1.0, 0.6); puddle(6.2, -44.4, 1.2, 0.7); puddle(-9.6, -44.6, 0.9, 0.6); puddle(9.8, -33.6, 0.8, 0.55);
      this.locker = { x: 8.6, z: -35.25 };                                                              // his locker: number 8, on the bank at z -36
      label('8', null, 8.6, -34.7, 0.7, 0.5, '#f6d55e', '#4d4756');
      wall(-12, -11.6, -47.2, -46.8, 0xe6d6bb); wall(-8.4, 12, -47.2, -46.8, 0xe6d6bb); door(-11.6, -8.4, -47, 0xcf9a7a);   // to the lobby: x -11.6 .. -8.4
      label('脱衣所', 'LOCKERS', 5.8, -28.4, 2.4, 1.1, '#cf7a5a', '#fff6e6');
      plant(-6.0, -46.0, 0.7);
      bucket(-4.4, -45.6); bucket(0.6, -38.6);
      // ---- LOBBY / RECEPTION (sneak): the counter, a vending machine, benches; the storage door behind the counter
      this.counter = box(3, 9.6, -55.6, -54.4, 0, 1.15, 0xbb8b5e, { tall: false });   // she sees over it
      box(3, 9.6, -55.7, -55.5, 1.15, 0.08, 0xd3ab7a, { solid: false });
      label('受付', 'RECEPTION', 6.3, -53.2, 2.4, 1.0, '#4d4756', '#f6f1e6');
      box(-11.8, -10.6, -56, -54.8, 0, 1.9, 0xdd5a42, { tall: true });                                  // vending machine (cover)
      box(-6, -2, -52.6, -52.0, 0, 0.45, 0x9db5cb); plant(-1.2, -58.6, 0.9);
      wall(-12, 9.4, -60.2, -59.8, 0xd2c8ba); wall(11.6, 12, -60.2, -59.8, 0xd2c8ba); door(9.4, 11.6, -60, 0x9a8a7a);   // back wall; the storage door x 9.4 .. 11.6
      for (const x of [-2.6, 0, 2.6]) box(x - 1.2, x + 1.2, -59.95, -59.85, 0, 1.1, 0xbfe0f2, { solid: false, cast: false });   // the glass front doors (shut)
      label('倉庫', 'STAFF ONLY', 10.5, -58.8, 2.0, 0.9, '#4d4756', '#f6f1e6');
      puddle(-4, -49.4, 1.1, 0.6); puddle(1.6, -57.4, 0.9, 0.5);
      bucket(-9.6, -50.6);
      // ---- STORAGE (behind reception): shelves, and THE box
      wall(5.6, 6, -68, -60); wall(5.6, 12.4, -68.4, -68);
      for (const [x0, x1, z0, z1] of [[6.2, 7.2, -67.6, -62], [10.8, 11.8, -67.6, -63]]) {
        box(x0, x1, z0, z1, 0, 1.8, 0xbb8b5e, { tall: true });
        for (let y = 0.45; y < 1.8; y += 0.6) box(x0 + 0.05, x1 - 0.05, z0 + 0.05, z1 - 0.05, y, 0.22, [0xf3b9c7, 0xa8dcc6, 0xf6eddc][Math.floor(y * 2) % 3], { solid: false });
      }
      this.boxSpot = { x: 9, z: -65.2 };
      this.pantsBox = this.cardboard(1.0); this.pantsBox.position.set(this.boxSpot.x, 0, this.boxSpot.z); this.pantsBox.rotation.y = 0.4; G.add(this.pantsBox);
      // sparkles that mark the next thing to do
      // the "go here" marker: a soft ring on the floor and a small rounded arrow bobbing above it
      const sp = (x, z) => { const g = new THREE.Group(); g.position.set(x, 0, z); g.visible = false; G.add(g);
        const ring = new THREE.Mesh(new THREE.RingGeometry(0.62, 0.78, 40).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85, depthWrite: false }));
        ring.position.y = 0.03; ring.renderOrder = 3; g.add(ring);
        const ar = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.arrowTex(), transparent: true, depthWrite: false, depthTest: false })); ar.scale.set(0.62, 0.62, 1); ar.position.y = 2.3; ar.renderOrder = 7; g.add(ar);
        g.userData = { ring, ar }; return g; };
      this.spLocker = sp(this.locker.x, this.locker.z); this.spKey = sp(this.washSpot.x, this.washSpot.z); this.spBox = sp(this.boxSpot.x, this.boxSpot.z);
      this.spLocker.visible = true;
      G.traverse((o) => { if (o.isMesh) o.userData.flatDone = true; });
    }
    arrowTex() {
      if (this._arrow) return this._arrow;
      const cv = document.createElement('canvas'); cv.width = cv.height = 128; const c = cv.getContext('2d');
      const tri = () => { c.beginPath(); c.moveTo(64, 104); c.lineTo(22, 40); c.quadraticCurveTo(14, 26, 30, 26); c.lineTo(98, 26); c.quadraticCurveTo(114, 26, 106, 40); c.closePath(); };
      c.lineJoin = 'round'; tri(); c.lineWidth = 16; c.strokeStyle = '#fffaf0'; c.stroke(); c.fillStyle = '#f08a5d'; c.fill();
      return (this._arrow = new THREE.CanvasTexture(cv));
    }
    // a cardboard box, open at the top: k = 1 on the floor; worn, sized round his hips
    cardboard(k) {
      const g = new THREE.Group(), card = S.Flat.mat(0xd3a96e), dark = S.Flat.mat(0xb98c52), tape = S.Flat.mat(0xe9d6a8);
      const W = 1.6 * k, H = 0.8 * k, D = 1.4 * k, T = 0.05 * k;
      const side = (w, h, d, x, y, z, m) => { const s = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m || card); s.position.set(x, y, z); s.castShadow = true; s.receiveShadow = true; g.add(s); return s; };
      side(W, H, T, 0, H / 2, D / 2); side(W, H, T, 0, H / 2, -D / 2); side(T, H, D, W / 2, H / 2, 0, dark); side(T, H, D, -W / 2, H / 2, 0, dark); side(W, T, D, 0, T / 2, 0, dark);
      for (const [z, rx] of [[D / 2 + 0.18 * k, 0.5], [-D / 2 - 0.18 * k, -0.5]]) { const f = side(W, T, 0.38 * k, 0, H + 0.06 * k, z); f.rotation.x = rx; }
      side(0.3 * k, H * 0.9, T * 1.2, 0, H / 2, D / 2 + 0.01, tape);
      return g;
    }
    makeMosaic() {
      const cv = document.createElement('canvas'); cv.width = 8; cv.height = 5;
      const tex = new THREE.CanvasTexture(cv); tex.magFilter = tex.minFilter = THREE.NearestFilter;
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false })); s.renderOrder = 5; this.scene.add(s);
      return { s, cv, t: 0 };
    }

    // ============================================================== the staff: fixed routes, cones of view
    // route points: [x, z, wait, look]. They walk between points (and to any noise) by the shortest way round
    // lockers, benches and walls (a grid path), wait, and look the given way, swaying their head a little.
    makeNpcs() {
      const mk = (kind, route, o) => {
        o = o || {};
        const a = { kind, x: route[0][0], z: route[0][1], y: 0, f: route[0][3] || 0, vx: 0, vz: 0, st: 'free', t: 0, hp: 1, maxHp: 1, dead: false, engage: false };
        const v = new S.WorkerView(this.scene, kind, !!o.fat, o.pick); v.walls = this.walls;
        const cone = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial({ color: 0xffcf3a, transparent: true, opacity: 0.4, depthWrite: false, side: THREE.DoubleSide }));
        cone.renderOrder = 2; this.scene.add(cone);
        return { a, v, route, i: 0, wait: route[0][2], mode: 'route', alarm: 0, cone, range: o.range || 6.4, half: o.half || 0.62, room: o.room, speed: o.speed || 1.35, sway: o.sway || 0.6, ear: o.ear || 0, path: null, pi: 0 };
      };
      const P = Math.PI, U = P / 2;
      return [
        // LOCKER ROOM. The attendant walks the two middle aisles, stopping at the ends to look along them
        mk('fighter', [[-10.4, -33.0, 1.6, 0], [10.6, -33.0, 1.4, P], [2.5, -33.4, 0, 0], [2.5, -38.2, 0, 0], [10.6, -38.2, 1.4, P], [-10.4, -38.2, 1.6, 0]], { room: 'lock' }),
        // a cleaner mopping along the far aisle
        mk('grappler', [[-1.0, -44.4, 2.2, -U], [10.6, -44.4, 2.2, -U]], { room: 'lock', fat: true, speed: 0.9, range: 5.4 }),
        // a customer getting changed at his locker by the shower door: mostly facing it, now and then looking round
        mk('rusher', [[-5.0, -30.0, 4.2, -U], [-5.0, -30.0, 1.8, P], [-5.0, -30.0, 3.6, -U], [-5.0, -30.0, 1.8, 0.15]], { room: 'lock', pick: 1, range: 5.2, sway: 0.3 }),
        // an old regular shuffling up and down by the lobby door
        mk('thrower', [[-7.0, -43.8, 2.6, U], [-3.0, -43.8, 2.2, U]], { room: 'lock', pick: 3, speed: 0.7, range: 4.6 }),
        // LOBBY. The receptionist, behind the counter right by the storage door: she hears anyone that close
        mk('technical', [[8.6, -57.2, 999, U]], { room: 'lobby', sway: 0.9, range: 8.2, half: 0.66, ear: 3.0 }),
        // someone straightening the benches
        mk('staff', [[-3.6, -50.4, 1.8, -U], [4.6, -50.4, 1.8, -U]], { room: 'lobby', speed: 1.1 }),
        // a customer at the drinks machine, deciding (forever)
        mk('thrower', [[-9.4, -55.2, 4.0, P], [-9.4, -55.2, 2.2, 0.35]], { room: 'lobby', pick: 2, range: 5.6, sway: 0.25 }),
      ];
    }
    sees(n, x, z, range) {
      const a = n.a, dx = x - a.x, dz = z - a.z, d = Math.hypot(dx, dz);
      if (d > range) return false;
      if (d > 0.9 && Math.abs(ang(Math.atan2(dz, dx) - a.f)) > n.half) return false;
      return this.clear(a.x, a.z, x, z);
    }
    clear(x0, z0, x1, z1) {
      for (const w of this.walls) { if (!w.tall) continue; if (segBoxT(x0, z0, x1, z1, w.x0 - 0.05, w.z0 - 0.05, w.x1 + 0.05, w.z1 + 0.05) !== null) return false; }
      for (const b of this.blockers) if (segCircleT(x0, z0, x1, z1, b.x, b.z, b.r) !== null) return false;
      return true;
    }
    reach(x0, z0, a, L) {
      const x1 = x0 + Math.cos(a) * L, z1 = z0 + Math.sin(a) * L; let t = 1;
      for (const w of this.walls) { if (!w.tall) continue; const h = segBoxT(x0, z0, x1, z1, w.x0, w.z0, w.x1, w.z1); if (h !== null && h < t) t = h; }
      for (const b of this.blockers) { const h = segCircleT(x0, z0, x1, z1, b.x, b.z, b.r); if (h !== null && h < t) t = h; }
      return t * L;
    }
    // ---------------------------------------------------------------- walking: a grid over the floor, A*, then the corners cut
    buildNav() {
      const cs = 0.4, x0 = -12.6, z0 = -68.8, nx = Math.ceil(25.2 / cs), nz = Math.ceil((5.2 - z0) / cs), free = new Uint8Array(nx * nz), R = 0.5;
      for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
        const x = x0 + (i + 0.5) * cs, z = z0 + (j + 0.5) * cs; let ok = true;
        for (const w of this.walls) if (x > w.x0 - R && x < w.x1 + R && z > w.z0 - R && z < w.z1 + R) { ok = false; break; }
        if (ok) for (const b of this.blockers) if (Math.hypot(x - b.x, z - b.z) < b.r * 0.55 + R) { ok = false; break; }
        free[j * nx + i] = ok ? 1 : 0;
      }
      this.nav = { cs, x0, z0, nx, nz, free };
    }
    cell(x, z) { const N = this.nav; return [clamp(Math.floor((x - N.x0) / N.cs), 0, N.nx - 1), clamp(Math.floor((z - N.z0) / N.cs), 0, N.nz - 1)]; }
    walkable(x, z) { const N = this.nav, [i, j] = this.cell(x, z); return !!N.free[j * N.nx + i]; }
    lineWalk(x0, z0, x1, z1) { const d = Math.hypot(x1 - x0, z1 - z0), n = Math.ceil(d / 0.15); for (let k = 1; k <= n; k++) if (!this.walkable(x0 + (x1 - x0) * k / n, z0 + (z1 - z0) * k / n)) return false; return true; }
    nearestFree(i, j) {
      const N = this.nav; if (N.free[j * N.nx + i]) return [i, j];
      for (let r = 1; r < 12; r++) for (let dj = -r; dj <= r; dj++) for (let di = -r; di <= r; di++) { if (Math.max(Math.abs(di), Math.abs(dj)) !== r) continue; const a = i + di, b = j + dj; if (a >= 0 && b >= 0 && a < N.nx && b < N.nz && N.free[b * N.nx + a]) return [a, b]; }
      return null;
    }
    // the way from (x0,z0) to (x1,z1) as a list of points (the end snapped onto the floor), or null
    navPath(x0, z0, x1, z1) {
      const N = this.nav, cs = N.cs, s0 = this.nearestFree(...this.cell(x0, z0)), s1 = this.nearestFree(...this.cell(x1, z1));
      if (!s0 || !s1) return null;
      const id = (i, j) => j * N.nx + i, goal = id(s1[0], s1[1]), start = id(s0[0], s0[1]), W = (k) => [N.x0 + (k % N.nx + 0.5) * cs, N.z0 + (Math.floor(k / N.nx) + 0.5) * cs];
      const end = this.walkable(x1, z1) ? [x1, z1] : W(goal);
      if (start === goal || this.lineWalk(x0, z0, end[0], end[1])) return [end];
      const g = new Float32Array(N.nx * N.nz).fill(1e9), from = new Int32Array(N.nx * N.nz).fill(-1), shut = new Uint8Array(N.nx * N.nz);
      const h = (k) => { const dx = Math.abs(k % N.nx - s1[0]), dz = Math.abs(Math.floor(k / N.nx) - s1[1]); return Math.max(dx, dz) + 0.414 * Math.min(dx, dz); };
      const heap = [], push = (k, f) => { heap.push([f, k]); let c = heap.length - 1; while (c) { const p = (c - 1) >> 1; if (heap[p][0] <= heap[c][0]) break; [heap[p], heap[c]] = [heap[c], heap[p]]; c = p; } };
      const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let c = 0; for (;;) { const l = 2 * c + 1, r = l + 1; let m = c; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === c) break; [heap[m], heap[c]] = [heap[c], heap[m]]; c = m; } } return top; };
      g[start] = 0; push(start, h(start)); let found = false;
      while (heap.length) {
        const [, k] = pop(); if (shut[k]) continue; shut[k] = 1; if (k === goal) { found = true; break; }
        const i = k % N.nx, j = Math.floor(k / N.nx);
        for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++) {
          if (!di && !dj) continue; const a = i + di, b = j + dj; if (a < 0 || b < 0 || a >= N.nx || b >= N.nz) continue;
          const q = id(a, b); if (!N.free[q] || shut[q]) continue; if (di && dj && (!N.free[id(i + di, j)] || !N.free[id(i, j + dj)])) continue;
          const ng = g[k] + (di && dj ? 1.414 : 1); if (ng < g[q]) { g[q] = ng; from[q] = k; push(q, ng + h(q)); }
        }
      }
      if (!found) return null;
      const pts = []; for (let k = goal; k !== -1 && k !== start; k = from[k]) pts.push(W(k)); pts.reverse(); pts[pts.length - 1] = end;
      // cut the corners: from each point, jump to the furthest one in a straight walkable line
      const out = []; let cx = x0, cz = z0, k = 0;
      while (k < pts.length) { let far = k; for (let m = pts.length - 1; m > k; m--) if (this.lineWalk(cx, cz, pts[m][0], pts[m][1])) { far = m; break; } out.push(pts[far]); cx = pts[far][0]; cz = pts[far][1]; k = far + 1; }
      return out;
    }
    goTo(n, x, z) { n.path = this.navPath(n.a.x, n.a.z, x, z) || [[x, z]]; n.pi = 0; n.stuckT = 0; }
    // a noise: anyone in earshot (in that room: walls muffle it) walks over the shortest way to look, searches, goes back
    noise(x, z, radius, msg) {
      this.fx.ring(x, z, radius * 0.4, 0.6); this.fx.ring(x, z, radius * 0.7, 0.9);
      const room = z > -47 ? 'lock' : 'lobby';
      for (const n of this.npcs) {
        if (n.room !== room || Math.hypot(n.a.x - x, n.a.z - z) > radius) continue;
        const path = this.navPath(n.a.x, n.a.z, x, z); if (!path) continue;
        n.path = path; n.pi = 0; n.stuckT = 0; n.mode = 'goto'; n.noiseAt = [x, z];
        this.popAt(n.a, msg || '?!', 1.6);
      }
    }
    npcStep(n, dt) {
      const a = n.a; a.t += dt;
      let tx = null, tz = null, sp = n.speed;
      if (n.mode === 'search') {
        n.wait -= dt; a.f += Math.sin(a.t * 1.7) * dt * 1.8;
        if (n.wait <= 0) { n.mode = 'return'; this.goTo(n, n.route[n.i][0], n.route[n.i][1]); }
      } else if (n.mode === 'route' && n.wait > 0) {
        const p = n.route[n.i]; n.wait -= dt; a.f = lerpA(a.f, p[3] + Math.sin(a.t * 0.8) * n.sway, dt * 2.5);
        if (n.wait <= 0) { n.i = (n.i + 1) % n.route.length; this.goTo(n, n.route[n.i][0], n.route[n.i][1]); }
      } else {
        if (!n.path) this.goTo(n, n.route[n.i][0], n.route[n.i][1]);
        const p = n.path[n.pi];
        if (p) { tx = p[0]; tz = p[1]; sp = n.mode === 'goto' ? 2.5 : n.mode === 'return' ? 1.4 : n.speed; if (Math.hypot(tx - a.x, tz - a.z) < 0.25) { n.pi++; if (!n.path[n.pi]) tx = null; } }
        if (!n.path[n.pi]) { // arrived
          n.path = null;
          if (n.mode === 'goto') { n.mode = 'search'; n.wait = 4.2; if (n.noiseAt) a.f = Math.atan2(n.noiseAt[1] - a.z, n.noiseAt[0] - a.x); }
          else { n.mode = 'route'; n.wait = n.route[n.i][2] || 0.01; }
        }
      }
      if (tx !== null) { const dx = tx - a.x, dz = tz - a.z, d = Math.hypot(dx, dz) || 1; a.vx = dx / d * sp; a.vz = dz / d * sp; a.f = lerpA(a.f, Math.atan2(dz, dx), dt * 7); }
      else { a.vx *= 0.8; a.vz *= 0.8; }
      const ox = a.x, oz = a.z; a.x += a.vx * dt; a.z += a.vz * dt;
      this.collide(a, 0.4);
      // never stuck: if walking gets nowhere for a moment, find the way again
      if (tx !== null) { n.stuckT = Math.hypot(a.x - ox, a.z - oz) < sp * dt * 0.3 ? (n.stuckT || 0) + dt : 0; if (n.stuckT > 0.8 && n.path) { const e = n.path[n.path.length - 1]; this.goTo(n, e[0], e[1]); } }
    }
    // push a circle out of every wall and blocker it overlaps (a few passes, so corners can't squeeze it through)
    collide(p, r) {
      let hit = false;
      for (let pass = 0; pass < 3; pass++) {
        let moved = false;
        for (const w of this.walls) {
          const cx = clamp(p.x, w.x0, w.x1), cz = clamp(p.z, w.z0, w.z1), dx = p.x - cx, dz = p.z - cz, d = Math.hypot(dx, dz);
          if (d >= r) continue;
          if (d > 1e-6) { p.x = cx + dx / d * r; p.z = cz + dz / d * r; }
          else { // centre inside the box: out by the nearest side
            const o = [[w.x0 - r - p.x, 0], [w.x1 + r - p.x, 0], [0, w.z0 - r - p.z], [0, w.z1 + r - p.z]].sort((A, B) => Math.abs(A[0] + A[1]) - Math.abs(B[0] + B[1]))[0];
            p.x += o[0]; p.z += o[1];
          }
          moved = hit = true;
        }
        for (const b of this.blockers) { const dx = p.x - b.x, dz = p.z - b.z, d = Math.hypot(dx, dz), m = b.r * 0.55 + r; if (d < m && d > 1e-6) { p.x = b.x + dx / d * m; p.z = b.z + dz / d * m; moved = hit = true; } }
        if (!moved) break;
      }
      return hit;
    }

    // ============================================================== the frame
    frame(dt) {
      if (!this.scene) return;
      if (!this.paused && !this.over && !this.freeze) {
        this.acc += Math.min(dt, 0.1); let k = 0;
        while (this.acc >= STEP && k < 8 && !this.freeze) { this.ctrl.update(STEP); this.step(STEP); this.acc -= STEP; k++; }
      } else if (this.paused || this.over) { this.ctrl.update(dt); }
      if (this.freeze) { this.freeze -= dt; if (this.freeze <= 0) { this.freeze = 0; this.respawn(); } }
      S.kb && S.kb.flush && S.kb.flush();
      this.draw(dt);
    }
    step(dt) {
      this.t += dt;
      if (this.timers) this.timers = this.timers.filter((q) => { q.t -= dt; if (q.t <= 0) { if (this.scene) q.fn(); return false; } return true; });
      const P = this.P, c = this.ctrl;
      P.t += dt; P.cd = Math.max(0, P.cd - dt);
      let mx = c.mx, mz = c.mz; const mag = Math.hypot(mx, mz); if (mag > 1) { mx /= mag; mz /= mag; }
      const crouchKey = !!(this.keys.KeyI);
      P.crouch += ((crouchKey && P.st === 'free' ? 1 : 0) - P.crouch) * Math.min(1, dt * 10);
      // L + direction: CHARGE (as everywhere in the game)
      if (P.st === 'free' && c.dash.held && mag > 0.3 && P.cd <= 0) { P.st = 'charge'; P.t = 0; P.dur = 0.85; P.cdir = Math.atan2(mz, mx); P.f = P.cdir; }
      let spd = 0;
      if (P.st === 'free') spd = P.crouch > 0.5 ? 1.7 : 3.4;
      if (P.st === 'charge') { mx = Math.cos(P.cdir); mz = Math.sin(P.cdir); spd = 7.2; if (!c.dash.held && P.t > 0.25) P.t = P.dur; }
      const dir = P.st === 'charge' || mag > 0.3;
      P.vx += ((dir ? mx : 0) * spd - P.vx) * Math.min(1, dt * (P.st === 'charge' ? 14 : 10)); P.vz += ((dir ? mz : 0) * spd - P.vz) * Math.min(1, dt * (P.st === 'charge' ? 14 : 10));
      if (P.st === 'slip' || P.st === 'busy' || P.st === 'wear') { P.vx *= 0.9; P.vz *= 0.9; }
      if (mag > 0.3 && P.st === 'free') P.f = lerpA(P.f, Math.atan2(mz, mx), dt * 12);
      P.x += P.vx * dt; P.z += P.vz * dt;
      const hit = this.collide(P, P.r);
      if (P.st === 'charge') {
        if (this.stage === 'smash' && Math.hypot(P.x - this.locker.x, P.z - this.locker.z) < 1.25) { this.smashLocker(); P.st = 'busy'; P.t = 0; P.dur = 0.5; }
        else if (hit) { P.st = 'busy'; P.t = 0; P.dur = 0.35; P.vx *= -0.3; P.vz *= -0.3; this.fx.dust && this.fx.dust(P.x, 0.5, P.z, 5, 0.3, 0.5, 0.3); if (P.z < SAFE_Z) this.noise(P.x, P.z, 5, '?'); }
      }
      if (P.st !== 'free' && P.t > P.dur) { const was = P.st; P.st = 'free'; P.t = 0; if (was === 'charge') P.cd = 0.5; if (was === 'wear') this.win(); }
      // puddles: walking over them is fine; RUNNING (the charge) over one, you slip
      if (P.st === 'charge') for (const q of this.puddles) if (((P.x - q.x) / q.rx) ** 2 + ((P.z - q.z) / q.rz) ** 2 < 1) {
        P.st = 'slip'; P.t = 0; P.dur = 1.3; P.fall = Math.atan2(P.vz, P.vx); P.vx *= 0.6; P.vz *= 0.6;
        this.think(['WHOA—!', 'Waaah!', 'Slippery!!'][(this.t * 3 | 0) % 3], 1.2); this.fx.water && this.fx.water(P.x, P.z, 5);
        if (P.z < SAFE_Z) this.noise(P.x, P.z, 7, '?!');
        break;
      }
      // the room you're in: checkpoints at each doorway
      const room = P.z > -16 ? 'bath' : P.z > SAFE_Z ? 'shower' : P.z > -47 ? 'lock' : P.z > -60 ? 'lobby' : 'store';
      if (room !== this.room) {
        const from = this.room; this.room = room;
        // checkpoints sit somewhere nobody is looking: the shower side of the locker door, the corner beside the lobby door
        if (room === 'lock') { this.cp = from === 'lobby' ? CP.lockS : CP.lockN; if (!this.saidOut) { this.saidOut = true; this.think('Out here I\'m the only one naked... sneak. (Hold I to crouch)', 3.2); } }
        if (room === 'lobby') this.cp = CP.lobby;
        if (room === 'shower' || room === 'bath') this.cp = { x: P.x, z: P.z, f: P.f };
        if (room === 'store' && this.stage === 'storage') { this.stage = 'box'; this.spBox.visible = true; this.think('A cardboard box... it\'ll have to do!', 2.8); this.objective('Put on the BOX (K next to it)'); }
      }
      // K: use (locker, look for the key, pick up / throw a bucket, wear the box)
      if (c.grab.pressed && P.st === 'free') this.use();
      if (P.held) { const b = P.held, s = this.view.s; b.m.position.set(P.x + Math.cos(P.f) * 0.75 * s, 1.15 * s, P.z + Math.sin(P.f) * 0.75 * s); }
      for (const b of this.buckets) if (b.state === 'fly') {
        b.t += dt; const k = Math.min(1, b.t / b.dur); b.x = b.sx + (b.tx - b.sx) * k; b.z = b.sz + (b.tz - b.sz) * k; b.y = 1.2 * (1 - k) + Math.sin(Math.PI * k) * 1.6;
        b.m.position.set(b.x, b.y, b.z); b.m.rotation.x += dt * 9;
        if (k >= 1) { b.state = 'floor'; b.m.rotation.set(Math.PI / 2, 0, 0.4); b.m.position.y = 0.3; this.noise(b.x, b.z, 16, '?!'); if (this.g.audio && this.g.audio.thump) this.g.audio.thump(6); this.think('*CLATTER*', 1); }
      }
      for (const f of this.flying) { // locker doors and clothes bursting out
        if (f.t >= f.dur) continue; f.t = Math.min(f.dur, f.t + dt); const k = f.t / f.dur;
        f.m.position.set(f.sx + (f.tx - f.sx) * k, f.sy + (f.ty - f.sy) * k + Math.sin(Math.PI * k) * f.h, f.sz + (f.tz - f.sz) * k);
        f.m.rotation.set(f.r0[0] + (f.r1[0] - f.r0[0]) * k, f.r0[1] + (f.r1[1] - f.r0[1]) * k, f.r0[2] + (f.r1[2] - f.r0[2]) * k);
      }
      // the staff (nobody minds you in the bath or the showers; just after a restart they get a moment too)
      this.grace = Math.max(0, this.grace - dt);
      for (const n of this.npcs) {
        this.npcStep(n, dt);
        if (P.z > SAFE_Z || this.grace > 0) { n.alarm = Math.max(0, n.alarm - dt); continue; }
        const range = this.range(n), d = Math.hypot(P.x - n.a.x, P.z - n.a.z), sameRoom = (P.z > -47) === (n.a.z > -47) && (P.z > -60) === (n.a.z > -60);
        // right next to someone they hear you, whichever way they face (crouching gets you closer; the receptionist hears everything near her)
        const ear = n.ear || (P.crouch > 0.5 ? 0.9 : 1.7);
        if (d < ear && sameRoom && this.clear(n.a.x, n.a.z, P.x, P.z)) { n.alarm += dt * 2.4; if (n.mode === 'route' && n.wait > 0) n.a.f = lerpA(n.a.f, Math.atan2(P.z - n.a.z, P.x - n.a.x), dt * 5); }
        else if (this.sees(n, P.x, P.z, range)) { n.alarm += dt * (1.0 + 2.2 * (1 - d / range)) * (P.crouch > 0.5 ? 0.8 : 1.15) * (P.st === 'charge' ? 2 : 1); if (d < 1.8) n.alarm = 1; }
        else n.alarm = Math.max(0, n.alarm - dt * 0.6);
        if (n.alarm >= 1) { this.caught(n); break; }
      }
    }
    range(n) { return n.range * (this.P.crouch > 0.5 ? 0.6 : 1) * (n.mode === 'search' || n.mode === 'goto' ? 1.2 : 1); }
    use() {
      const P = this.P, near = (x, z, r) => Math.hypot(P.x - x, P.z - z) < r;
      if (P.held) { // throw it where you face
        const b = P.held; P.held = null; b.state = 'fly'; b.t = 0; b.sx = b.m.position.x; b.sz = b.m.position.z;
        let tx = P.x + Math.cos(P.f) * 8, tz = P.z + Math.sin(P.f) * 8; const L = Math.max(1, this.reach(P.x, P.z, P.f, 8) - 0.6); tx = P.x + Math.cos(P.f) * L; tz = P.z + Math.sin(P.f) * L;
        b.tx = tx; b.tz = tz; b.dur = 0.35 + L * 0.05; P.st = 'busy'; P.t = 0; P.dur = 0.3; this.w.hand = 1; return;
      }
      if (this.stage === 'locker' && near(this.locker.x, this.locker.z, 1.7)) {
        P.st = 'busy'; P.t = 0; P.dur = 0.8; this.stage = 'key'; this.spLocker.visible = false; this.spKey.visible = true;
        this.think('Locked. The key... it must be in my wash bucket, back by the bath where I woke up!', 3.4);
        this.objective('Go back to the BATH and check your WASH BUCKET for the KEY'); return;
      }
      if (this.stage === 'key' && near(this.washSpot.x, this.washSpot.z, 1.6)) {
        P.st = 'busy'; P.t = 0; P.dur = 1.0; this.stage = 'smash'; this.spKey.visible = false; this.spLocker.visible = true;
        P.f = Math.atan2(this.washSpot.z - P.z, this.washSpot.x - P.x);
        const wb = this.washB; this.G.attach(this.washTowel); this.washTowel.position.set(wb.position.x + 0.7, 0.03, wb.position.z + 0.35); this.washTowel.rotation.set(0, 0.3, 0); this.flying.push({ m: wb, sx: wb.position.x, sy: 0, sz: wb.position.z, tx: wb.position.x + 0.3, ty: 0.34, tz: wb.position.z + 0.2, h: 0.5, t: 0, dur: 0.45, r0: [0, 0, 0], r1: [Math.PI, 0.6, 0] });   // tipped out: nothing
        this.think('Empty?! No key... Forget it. I\'ll just smash the locker open!', 3.2);
        this.objective('CHARGE into your locker (hold L + direction)'); return;
      }
      if (this.stage === 'box' && near(this.boxSpot.x, this.boxSpot.z, 1.9)) { P.st = 'wear'; P.t = 0; P.dur = 0.9; return; }
      for (const b of this.buckets) if (b.state === 'floor' && near(b.m.position.x, b.m.position.z, 1.4)) { b.state = 'held'; P.held = b; this.think('A bucket. If I throw this, someone will go and look...', 2.2); return; }
    }
    smashLocker() {
      this.stage = 'storage'; this.spLocker.visible = false;
      const L = this.banks[3]; L.rotation.z = 0.012;
      const lx = this.locker.x, fz = -35.98, M = (c) => S.Flat.mat(c);
      // the open lockers: dark inside. His (upper, number 8) is EMPTY; the ones either side spill their clothes
      const hole = (x, y0) => { const h = new THREE.Mesh(new THREE.PlaneGeometry(0.44, 0.7), M(0x4d4756)); h.position.set(x, y0 + 0.37, fz + 0.012); this.G.add(h); };
      const doorOff = (x, y0, sd, k) => { const d = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.74, 0.04), M(0x9db5cb)); d.castShadow = true; this.G.add(d);
        this.flying.push({ m: d, sx: x, sy: y0 + 0.37, sz: fz + 0.05, tx: x + sd * (0.5 + k), ty: 0.03, tz: fz + 1.0 + k, h: 0.6, t: 0, dur: 0.45 + 0.1 * k, r0: [0, 0, 0], r1: [-Math.PI / 2, sd * 0.8, sd * 0.3] }); };
      const opens = [[lx, 0.95, 0], [lx - 0.62, 0.95, -1], [lx + 0.62, 0.15, 1], [lx - 1.24, 0.15, -1], [lx + 1.24, 0.95, 1]];
      opens.forEach(([x, y0, sd], k) => { hole(x, y0); doorOff(x, y0, sd || 1, k * 0.25); });
      // tiny clothes (a child's shirt, small shorts, socks) flying out of the neighbours' lockers onto the floor
      const shirt = (c) => { const sh = new THREE.Shape([[-0.09, -0.13], [0.09, -0.13], [0.09, 0.05], [0.16, 0.02], [0.19, 0.08], [0.1, 0.14], [-0.1, 0.14], [-0.19, 0.08], [-0.16, 0.02], [-0.09, 0.05]].map((p) => new THREE.Vector2(p[0], p[1])));
        const m = new THREE.Mesh(new THREE.ShapeGeometry(sh), S.Flat.mat(c, { side: THREE.DoubleSide })); m.castShadow = true; return m; };
      const shorts = (c) => { const sh = new THREE.Shape([[-0.11, 0.08], [0.11, 0.08], [0.12, -0.1], [0.02, -0.1], [0, -0.02], [-0.02, -0.1], [-0.12, -0.1]].map((p) => new THREE.Vector2(p[0], p[1])));
        const m = new THREE.Mesh(new THREE.ShapeGeometry(sh), S.Flat.mat(c, { side: THREE.DoubleSide })); m.castShadow = true; return m; };
      const items = [shirt(0xf3b9c7), shorts(0x6f8fc8), shirt(0xa8dcc6), shorts(0xf6d55e), shirt(0xf2f2ec), shorts(0xcf7a5a), shirt(0x9db5cb)];
      items.forEach((m, k) => { const [x, y0] = opens[1 + (k % 4)]; this.G.add(m);
        this.flying.push({ m, sx: x, sy: y0 + 0.4, sz: fz + 0.1, tx: x + (k % 2 ? 0.5 : -0.5) * (0.5 + (k % 3) * 0.4), ty: 0.02, tz: fz + 0.7 + (k % 4) * 0.35, h: 0.7 + (k % 3) * 0.2, t: 0, dur: 0.5 + k * 0.06, r0: [0, 0, 0], r1: [-Math.PI / 2, 0, k * 1.3] }); });
      this.fx.dust && this.fx.dust(lx, 0.8, this.locker.z, 10, 0.4, 0.6, 0.4); this.flash = 0.6;
      this.noise(lx, this.locker.z, 26, '!?');
      if (this.g.audio) { this.g.audio.thump && this.g.audio.thump(9); this.later(0.15, () => this.g.audio.thump && this.g.audio.thump(5)); }
      this.think('...EMPTY?! Someone took my clothes!', 2.2);
      this.later(2.3, () => { if (this.stage === 'storage') this.think('And everyone else\'s are TINY. Nothing here fits me...', 2.6); });
      this.later(5.0, () => { if (this.stage === 'storage') { this.think('They heard that! The STORAGE room behind reception... there must be something there.', 3.6); this.objective('Get into STORAGE behind RECEPTION. Throw a bucket to distract the staff (K pick up, K throw)'); } });
      this.cp = CP.lockN;
    }
    caught(n) {
      this.spotted++; this.freeze = 1.6; this.P.vx = this.P.vz = 0;
      this.popAt(n.a, ['KYAAA!', 'PERVERT!', 'HEY! YOU THERE!', 'MY EYES!'][this.spotted % 4], 1.5, true);
      if (this.g.audio && this.g.audio.whoosh) this.g.audio.whoosh(0.4);
      this.flash = 1;
    }
    respawn() {
      const P = this.P; P.x = this.cp.x; P.z = this.cp.z; P.f = this.cp.f; P.vx = P.vz = 0; P.st = 'free';
      if (P.held) { const b = P.held; P.held = null; b.state = 'floor'; b.m.position.set(b.x0, 0, b.z0); b.m.rotation.set(0, 0, 0); }
      for (const n of this.npcs) { n.alarm = 0; n.mode = 'route'; n.i = 0; n.wait = n.route[0][2]; n.path = null; n.a.x = n.route[0][0]; n.a.z = n.route[0][1]; n.a.f = n.route[0][3] || 0; }
      this.grace = 2.0;
      this.think(['Too close... try again.', 'Wait for them to look away.', 'Stay behind cover, then move.', 'Crouch (I) when they\'re near.'][this.spotted % 4], 2.2);
    }
    win() {
      this.over = 'win'; this.wearing = true; this.pantsBox.visible = false; this.spBox.visible = false;
      const b = this.cardboard(0.95); b.position.set(0, -0.62 * this.view.s, 0.02 * this.view.s); this.view.body.add(b);
      this.think('Perfect fit. Nobody will ever know.', 3);
      if (this.g.audio && this.g.audio.swell) this.g.audio.swell(0.6, 1.4);
      setTimeout(() => { if (!this.scene) return; const e = this.el('.st-over'); e.innerHTML = '<h2 data-jp="成功">BOX PANTS ACQUIRED</h2><p>Time ' + fmtT(this.t) + ' · Spotted ' + this.spotted + ' time' + (this.spotted === 1 ? '' : 's') + '</p><button data-c="retry">PLAY AGAIN</button><button data-c="quit">QUIT TO TITLE</button><p class="k">Enter / J play again · Esc quit</p>'; e.classList.add('on'); this.overI = 0; this.markMenu('.st-over', 0); }, 1800);
    }

    // ============================================================== drawing
    draw(dt) {
      const P = this.P, T = this.t, w = this.w, v = this.view;
      if (S.SoftSumo && S.SoftSumo.loaded && !v.soft) S.SoftSumo.attach(v, { noBlob: true });
      if (v.soft && !v.pantsOff) { v.pantsOff = true; for (const m of v.soft.mats) if (/mawashi/i.test(m.name || '')) m.visible = false; }
      w.x = P.x; w.z = P.z; w.y = 0; w.f = P.f; w.fx = Math.cos(P.f); w.fz = Math.sin(P.f); w.vx = P.vx; w.vz = P.vz; w.spd = Math.hypot(P.vx, P.vz);
      const nst = P.st === 'charge' ? 'charge' : P.st === 'slip' ? 'fall' : P.st === 'busy' ? 'palm' : P.st === 'wear' ? 'brace' : 'free';
      if (w.st !== nst) { w.st = nst; w.t = 0; } else w.t = P.t;
      if (nst === 'fall') { w.fallX = Math.cos(P.fall); w.fallZ = Math.sin(P.fall); w.down = P.t > 0.3 && P.t < 1.0; } else w.down = false;
      w.hand = 1; w.hunch = P.crouch; w.relaxed = true; w.fxs = {}; w.carry = P.held ? { small: false } : null;
      if (this.freeze) w.fxs.dizzy = 1;
      v.update(w, Math.max(dt, 1e-4), T);
      for (const n of this.npcs) { n.v.update(n.a, Math.max(dt, 1e-4), T); this.drawCone(n); }
      // censored: a jittering pixel block over his hips, kept between him and the camera
      const m = this.mosaic; m.s.visible = !this.wearing;
      if (!this.wearing) {
        m.t -= dt;
        if (m.t <= 0) { m.t = 0.1; const g = m.cv.getContext('2d'), sk = ['#e9b894', '#d9a07c', '#f0c8a8', '#c98a6a', '#e0ac88'];
          g.clearRect(0, 0, 8, 5); for (let y = 0; y < 5; y++) for (let x = 0; x < 8; x++) { if ((x === 0 || x === 7) && Math.random() < 0.6) continue; g.fillStyle = sk[(Math.random() * sk.length) | 0]; g.fillRect(x, y, 1, 1); }
          m.s.material.map.needsUpdate = true; }
        const s = v.s, hip = (this._hip || (this._hip = new THREE.Vector3())).set(0, (CENSOR.y + 0.2 * P.crouch) * s, 0);
        v.body.updateWorldMatrix(true, false); v.body.localToWorld(hip); const to = this.cam.position.clone().sub(hip).normalize();
        m.s.position.copy(hip).addScaledVector(to, 0.95 * s); m.s.scale.set(CENSOR.w * s, CENSOR.h * s, 1);
      }
      for (const sp of [this.spLocker, this.spKey, this.spBox]) if (sp.visible) { const u = sp.userData, k = (T * 0.9) % 1;
        u.ar.position.y = 2.3 + Math.abs(Math.sin(T * 3.2)) * 0.22; u.ring.scale.setScalar(0.8 + 0.35 * k); u.ring.material.opacity = 0.85 * (1 - k * k); }
      this.fx.update(dt); this.fx.updateWater && this.fx.updateWater(dt);
      // camera: high, behind, following (as in the campaign); closer for the ending
      this.camT.lerp(new THREE.Vector3(this.over ? P.x + 2.2 : clamp(P.x * 0.8, -10, 10), 0, P.z - (this.over ? 0.6 : 2.6)), 1 - Math.exp(-dt * 4));
      const dist = this.over ? 9 : 15, sh = this.flash ? this.flash * 0.25 : 0; this.flash = Math.max(0, (this.flash || 0) - dt * 2);
      this.cam.position.set(this.camT.x + (Math.random() - 0.5) * sh, dist * 0.64, this.camT.z + dist * 0.77);
      this.cam.lookAt(this.camT.x, 0.6, this.camT.z); this.cam.updateMatrixWorld();
      this.flat.lights.aim(this.camT.x, this.camT.z - 3);
      if ((this.cvN = (this.cvN || 0) + 1) % 30 === 1) S.Flat.convert(this.scene, { pastel: 0.6 });
      this.R.r.shadowMap.enabled = true;
      this.R.r.render(this.scene, this.cam);
      this.drawHud(dt);
    }
    drawCone(n) {
      const a = n.a, N = 22, safe = this.P.z > SAFE_Z;
      n.cone.visible = !safe; if (safe) return;
      const range = this.range(n), pos = new Float32Array((N + 2) * 3); pos[0] = a.x; pos[1] = 0.03; pos[2] = a.z;
      for (let i = 0; i <= N; i++) { const t = a.f - n.half + (2 * n.half) * i / N, L = this.reach(a.x, a.z, t, range); pos[(i + 1) * 3] = a.x + Math.cos(t) * L; pos[(i + 1) * 3 + 1] = 0.03; pos[(i + 1) * 3 + 2] = a.z + Math.sin(t) * L; }
      const idx = []; for (let i = 1; i <= N; i++) idx.push(0, i + 1, i);
      const g = n.cone.geometry; g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setIndex(idx); g.computeBoundingSphere();
      const k = clamp(n.alarm, 0, 1); n.cone.material.color.setRGB(1, 0.81 - 0.5 * k, 0.23 - 0.1 * k); n.cone.material.opacity = 0.36 + 0.24 * k;
    }

    // ============================================================== HUD
    buildHud() {
      const h = this.hud = document.createElement('div'); h.id = 'stealthHud';
      h.innerHTML = '<style>#stealthHud{position:fixed;inset:0;pointer-events:none;z-index:6;font-family:"Barlow Condensed",sans-serif;color:#3a3440}' +
        '#stealthHud .st-obj{position:absolute;left:24px;top:20px;background:rgba(255,250,240,.9);padding:8px 14px;border-radius:10px;font-weight:700;font-size:20px;letter-spacing:.02em;max-width:60vw}' +
        '#stealthHud .st-obj b{color:#cf5a4a}#stealthHud .st-safe{position:absolute;right:24px;top:20px;background:#a8dcc6;color:#2f4b4a;padding:6px 12px;border-radius:10px;font-weight:800;font-size:18px;display:none}' +
        '#stealthHud .st-think{position:absolute;transform:translate(-50%,-100%);background:#fffaf0;border-radius:18px;padding:8px 16px;font-weight:700;font-size:20px;max-width:360px;text-align:center;box-shadow:0 3px 0 rgba(60,50,70,.15);opacity:0;transition:opacity .2s}' +
        '#stealthHud .st-think.on{opacity:1}#stealthHud .st-think:after{content:"";position:absolute;left:50%;bottom:-12px;width:14px;height:14px;border-radius:50%;background:#fffaf0;transform:translateX(-50%)}' +
        '#stealthHud .st-pop{position:absolute;transform:translate(-50%,-100%);font:400 26px "Dela Gothic One",sans-serif;color:#cf3a3a;text-shadow:0 2px 0 #fff;white-space:nowrap}' +
        '#stealthHud .st-q{position:absolute;transform:translate(-50%,-100%);font:400 24px "Dela Gothic One",sans-serif;color:#e2a13a;text-shadow:0 2px 0 #fff}' +
        '#stealthHud .st-help{position:absolute;left:24px;bottom:18px;font-size:16px;opacity:.8;background:rgba(255,250,240,.75);padding:4px 10px;border-radius:8px}' +
        '#stealthHud .st-pause,#stealthHud .st-over{position:absolute;left:0;top:0;bottom:0;width:min(520px,92vw);display:none;pointer-events:auto;background:linear-gradient(90deg,rgba(30,24,36,.92),rgba(30,24,36,.6) 80%,transparent);padding:80px 60px;color:#f4efe6}' +
        '#stealthHud .st-over{left:auto;right:0;text-align:right;background:linear-gradient(270deg,rgba(30,24,36,.92),rgba(30,24,36,.6) 80%,transparent)}#stealthHud .st-over button{margin-left:auto}' +
        '#stealthHud .on{display:block}#stealthHud h2{font:400 56px "Dela Gothic One",sans-serif;margin:0 0 20px}#stealthHud h2:before{content:attr(data-jp);display:block;font-size:15px;letter-spacing:.5em;color:#d8262e;margin-bottom:8px}' +
        '#stealthHud .st-pause button,#stealthHud .st-over button{display:block;background:none;border:0;color:rgba(244,239,230,.55);font:700 30px "Barlow Condensed",sans-serif;padding:6px 0;cursor:pointer}' +
        '#stealthHud .st-pause button.sel{color:#f4efe6;padding-left:22px;border-left:5px solid #d8262e}#stealthHud .st-over button.sel{color:#f4efe6;padding-right:22px;border-right:5px solid #d8262e}#stealthHud .k{font-size:15px;opacity:.6}</style>' +
        '<div class="st-obj"></div><div class="st-safe">SAFE: everyone\'s naked here</div><div class="st-think"></div><div class="st-pops"></div><div class="st-help">WASD move · hold I crouch · hold L + direction charge · K use / pick up / throw · Esc pause</div>' +
        '<div class="st-pause"><h2 data-jp="一時停止">PAUSED</h2><button data-c="resume">RESUME</button><button data-c="retry">RESTART LEVEL</button><button data-c="quit">QUIT TO TITLE</button><p class="k">W / S choose · Enter or J select</p></div><div class="st-over"></div>';
      document.body.appendChild(h);
      h.addEventListener('click', (e) => { const b = e.target.closest('[data-c]'); if (b) this.command(b.dataset.c); });
      this.pops = [];
    }
    el(q) { return this.hud.querySelector(q); }
    objective(t) { this.el('.st-obj').innerHTML = 'GOAL: <b>' + t + '</b>'; }
    think(t, dur) { this.thinkT = dur || 2.5; const e = this.el('.st-think'); e.textContent = t; e.classList.add('on'); }
    popAt(a, txt, dur, big) { const d = document.createElement('div'); d.className = 'st-pop'; d.textContent = txt; if (!big) d.style.fontSize = '22px'; this.el('.st-pops').appendChild(d); this.pops.push({ d, a, t: dur || 1.4 }); }
    project(x, y, z) { const v = new THREE.Vector3(x, y, z).project(this.cam); return { x: (v.x * 0.5 + 0.5) * innerWidth, y: (-v.y * 0.5 + 0.5) * innerHeight }; }
    drawHud(dt) {
      const P = this.P, s = this.view.s;
      this.el('.st-safe').style.display = P.z > SAFE_Z && !this.over ? 'block' : 'none';
      if (this.thinkT > 0) { this.thinkT -= dt; const p = this.project(P.x, 2.9 * s, P.z), e = this.el('.st-think'); e.style.left = p.x + 'px'; e.style.top = p.y + 'px'; if (this.thinkT <= 0) e.classList.remove('on'); }
      this.pops = this.pops.filter((q) => { q.t -= dt; const p = this.project(q.a.x, 2.6 + (1.4 - q.t) * 0.3, q.a.z); q.d.style.left = p.x + 'px'; q.d.style.top = p.y + 'px'; if (q.t <= 0) { q.d.remove(); return false; } return true; });
      if (!this.qs) this.qs = this.npcs.map(() => { const d = document.createElement('div'); d.className = 'st-q'; this.el('.st-pops').appendChild(d); return d; });
      this.npcs.forEach((n, i) => { const d = this.qs[i]; if (n.alarm > 0.08 && !this.freeze) { const p = this.project(n.a.x, 2.4, n.a.z); d.style.left = p.x + 'px'; d.style.top = p.y + 'px'; d.textContent = n.alarm > 0.6 ? '?!' : '?'; d.style.display = ''; d.style.transform = 'translate(-50%,-100%) scale(' + (0.8 + n.alarm * 0.6) + ')'; } else d.style.display = 'none'; });
    }
    markMenu(q, i) { this.el(q).querySelectorAll('button').forEach((b, k) => b.classList.toggle('sel', k === i)); }
    setPause(on) { this.paused = on; this.el('.st-pause').classList.toggle('on', on); if (on) { this.pauseI = 0; this.markMenu('.st-pause', 0); } }
    command(c) {
      if (c === 'resume') this.setPause(false);
      else if (c === 'retry') { const g = this.g; this.stop(); g.camp = new S.Stealth(g); g.camp.start(); }
      else if (c === 'quit') this.g.endCampaign();
    }
    onKey(e) {
      const menu = this.paused ? '.st-pause' : this.over && this.el('.st-over').classList.contains('on') ? '.st-over' : null;
      if (menu) {
        if (e.repeat) return true;
        const bs = this.el(menu).querySelectorAll('button'), key = menu === '.st-pause' ? 'pauseI' : 'overI';
        if (e.code === 'ArrowUp' || e.code === 'KeyW') { this[key] = (this[key] - 1 + bs.length) % bs.length; this.markMenu(menu, this[key]); }
        else if (e.code === 'ArrowDown' || e.code === 'KeyS') { this[key] = (this[key] + 1) % bs.length; this.markMenu(menu, this[key]); }
        else if (e.code === 'Enter' || e.code === 'NumpadEnter' || e.code === 'KeyJ') this.command(bs[this[key]].dataset.c);
        else if (e.code === 'Escape') { if (this.paused) this.setPause(false); else this.command('quit'); }
        return true;
      }
      if (e.code === 'Escape' || e.code === 'KeyP') { if (!this.over) this.setPause(true); return true; }
      return false;
    }
  }

  // ---------------------------------------------------------------- geometry helpers
  function segBoxT(x0, z0, x1, z1, bx0, bz0, bx1, bz1) {
    let t0 = 0, t1 = 1; const dx = x1 - x0, dz = z1 - z0;
    for (const [p, q] of [[-dx, x0 - bx0], [dx, bx1 - x0], [-dz, z0 - bz0], [dz, bz1 - z0]]) {
      if (Math.abs(p) < 1e-9) { if (q < 0) return null; continue; }
      const r = q / p; if (p < 0) { if (r > t1) return null; if (r > t0) t0 = r; } else { if (r < t0) return null; if (r < t1) t1 = r; }
    }
    return t0;
  }
  function segCircleT(x0, z0, x1, z1, cx, cz, r) {
    const dx = x1 - x0, dz = z1 - z0, fx = x0 - cx, fz = z0 - cz, A = dx * dx + dz * dz, B = 2 * (fx * dx + fz * dz), C = fx * fx + fz * fz - r * r;
    if (C < 0) return 0; const D = B * B - 4 * A * C; if (D < 0) return null; const t = (-B - Math.sqrt(D)) / (2 * A); return t >= 0 && t <= 1 ? t : null;
  }
  const fmtT = (t) => Math.floor(t / 60) + ':' + String(Math.floor(t % 60)).padStart(2, '0');

  S.Stealth = Stealth;
})();
