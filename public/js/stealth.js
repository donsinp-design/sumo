'use strict';
// TEST LEVEL: THE BATHHOUSE. The sumo wakes up in a public bath with no mawashi (censored), and has to sneak to the
// locker room for pants without being seen. Smashing the lockers makes noise (staff come to look) and there's nothing
// his size, so he tries the storage room, where a cardboard box becomes his pants.
// Stealth rules: a few staff walk fixed routes (learnable), their view is a cone on the floor; walls, locker banks,
// tall screens and steam block it. Hold L to crouch: slower, and they have to be closer to notice you. Being in a cone
// fills their alarm; full = spotted, back to the start of the room.
(function () {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ang = (a) => Math.atan2(Math.sin(a), Math.cos(a));
  const STEP = 1 / 60;

  class Stealth {
    constructor(game) { this.g = game; }

    // ============================================================== setup / teardown
    start() {
      const g = this.g;
      this.R = g.R; this.t = 0; this.acc = 0; this.paused = false; this.over = null; this.spotted = 0;
      this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(0xd9e6e9); this.scene.fog = new THREE.Fog(0xe4ecee, 40, 90);
      this.cam = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 200);
      this.fx = new S.FX(this.scene); this.fx.scene = this.scene; this.fx.noMarks = true;
      this.flat = { lights: S.Flat.lights(this.scene, { r: 22 }) };
      const r = this.R.r; r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
      const vg = document.getElementById('vignette'); if (vg) vg.style.display = 'none';
      this.walls = []; this.blockers = []; this.steam = []; this.markers = [];
      this.build();
      this.ctrl = new S.Controller(new S.KeySource(S.MAPS.solo, 0));
      // the player: the soft sumo, no mawashi (a pixel mosaic does the decent thing)
      const arch = S.ARCH[g.sel && g.sel.c1 !== undefined ? g.sel.c1 : 0];
      this.P = { x: -6.2, z: 0.6, f: -Math.PI / 2, vx: 0, vz: 0, r: 0.7, st: 'free', t: 0, crouch: 0 };
      this.view = new S.WrestlerView(this.scene, arch, this.fx, S.DEF_EQ); this.view.viewer = 0; this.view.match = null;
      this.w = { x: 0, z: 0, y: 0, f: 0, fx: 0, fz: 1, vx: 0, vz: 0, st: 'free', t: 0, dur: 1, fxs: {}, a: arch, idx: 0, szCur: 1, squash: 0, bal: 1, tx: 0, tz: 0, power: 0, pre: null, preT: 0,
        hand: 0, windPow: 0, charges: 0, uprightT: 0, throatT: 0, lifted: false, down: false, fallX: 0, fallZ: 1, clinch: null, slideT: 0, spd: 0, crouchT: 0, lean: 0, gulpI: -1, contact: false, fwdIn: 0, ddx: 0, ddz: 0, boomT: 0, relaxed: true };
      this.mosaic = this.makeMosaic();
      this.npcs = this.makeNpcs();
      this.stage = 'hall'; this.cp = { x: this.P.x, z: this.P.z, f: this.P.f };
      this.camT = new THREE.Vector3(this.P.x, 0, this.P.z - 2.6);
      this.buildHud();
      this.resize = () => { this.cam.aspect = innerWidth / innerHeight; this.cam.updateProjectionMatrix(); if (this.fx.pmat) this.fx.pmat.uniforms.uScale.value = innerHeight * r.getPixelRatio() / (2 * Math.tan(this.cam.fov * Math.PI / 360)); };
      addEventListener('resize', this.resize); this.resize();
      this.objective('Sneak to the LOCKER ROOM and find some pants');
      this.think('...Huh? Where... where is my mawashi?!', 3.2);
      setTimeout(() => this.scene && !this.over && this.think('Nobody can see me like this. Stay out of their sight. (Hold L to crouch)', 4), 3400);
      if (g.audio && g.audio.swell) g.audio.swell(0.3, 1.2);
    }
    stop() {
      removeEventListener('resize', this.resize);
      if (this.hud) this.hud.remove();
      this.R.r.shadowMap.enabled = !!this.R.flat;
      const vg = document.getElementById('vignette'); if (vg) vg.style.display = this.R.flat ? 'none' : '';
      this.scene = null;
    }

    // ============================================================== the bathhouse
    build() {
      const sc = this.scene, M = (c, o) => S.Flat.mat(c, o), G = new THREE.Group(); sc.add(G); this.G = G;
      const box = (x0, x1, z0, z1, y0, h, col, o) => {
        o = o || {};
        const m = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, h, z1 - z0), M(col, o.mat)); m.position.set((x0 + x1) / 2, y0 + h / 2, (z0 + z1) / 2);
        m.castShadow = o.cast !== false; m.receiveShadow = true; G.add(m);
        if (o.solid !== false) { const w = { x0: Math.min(x0, x1), x1: Math.max(x0, x1), z0: Math.min(z0, z1), z1: Math.max(z0, z1), tall: o.tall !== undefined ? o.tall : (y0 + h) > 1.1 }; this.walls.push(w); m.userData.wall = w; }
        return m;
      };
      const floor = (x0, x1, z0, z1, col, y) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, z1 - z0).rotateX(-Math.PI / 2), M(col)); m.position.set((x0 + x1) / 2, y || 0, (z0 + z1) / 2); m.receiveShadow = true; G.add(m); return m; };
      const wall = (x0, x1, z0, z1, col) => box(x0, x1, z0, z1, 0, 1.15, col || 0xe8ddc9, { tall: true });   // cut-away walls: low, so the camera sees over them, but nobody sees through them
      const sign = (text, sub, x, y, z, ry, bg, fg, w, h) => {
        const cv = document.createElement('canvas'); cv.width = 512; cv.height = 256; const c = cv.getContext('2d');
        c.fillStyle = bg; c.fillRect(0, 0, 512, 256); c.fillStyle = fg; c.textAlign = 'center'; c.textBaseline = 'middle';
        c.font = '120px "Dela Gothic One", sans-serif'; c.fillText(text, 256, sub ? 100 : 128); if (sub) { c.font = '800 46px "Barlow Condensed", sans-serif'; c.fillText(sub, 256, 205); }
        const t = new THREE.CanvasTexture(cv); const m = new THREE.Mesh(new THREE.PlaneGeometry(w || 2.4, h || 1.2), M(0xffffff, { map: t })); m.position.set(x, 0.02, z); m.rotation.set(-Math.PI / 2, 0, ry || 0); G.add(m); return m;   // painted on the floor by the door
      };
      // floors: pale stone tiles in the bath, warm wood in the corridor and locker room, plain boards in storage
      floor(-9, 9, -14, 2.4, 0xd7dfdc); floor(-9, 9, -21, -14, 0xdcc49e); floor(-9, 9, -36.4, -21, 0xd9be92); floor(-17, -9, -36.4, -26.6, 0xcbb79a);
      for (let z = 1.6; z > -14; z -= 1.6) floor(-9, 9, z - 0.03, z + 0.03, 0xc5d0cc, 0.002);   // tile joints
      // outer walls
      wall(-9.4, -9, -26.6, 2.4); wall(9, 9.4, -36.4, 2.4); wall(-9.4, 9.4, 2.4, 2.8); wall(-17.4, 9.4, -36.8, -36.4);
      wall(-9.4, -9, -36.4, -34.6); wall(-9.4, -9, -32.2, -26.6);                          // locker room left wall, the storage door gap between
      wall(-17.4, -17, -36.4, -26.6); wall(-17.4, -9, -26.6, -26.2);                       // storage room
      // ---- the bath hall
      wall(-9, -5, -14.2, -13.8, 0xbcd3d6); wall(-2.6, 9, -14.2, -13.8, 0xbcd3d6);        // door to the corridor at x -5 .. -2.6
      sign('男湯', 'MEN', -3.8, 0, -12.9, 0, '#2f4b7c', '#f6f1e6', 2.2, 1.0);
      // the big bath: a hinoki rim round pale blue water, with a mural of Mt Fuji on the back wall
      box(-2.2, 6.2, -10.8, -2.4, 0, 0.55, 0xc9a06a, { solid: true });
      const water = new THREE.Mesh(new THREE.PlaneGeometry(7.9, 7.9).rotateX(-Math.PI / 2), M(0x9cc6e8)); water.position.set(2, 0.58, -6.6); G.add(water); this.water = water;
      for (const [x, z, L, ry] of [[0.3, -4.5, 1.6, 0.2], [3.4, -8.6, 2.0, -0.1], [4.6, -5.2, 1.2, 0.4]]) { const s = new THREE.Mesh(new THREE.PlaneGeometry(L, 0.16).rotateX(-Math.PI / 2), M(0xe6f2ff)); s.position.set(x, 0.59, z); s.rotation.y = ry; G.add(s); }
      const fuji = (() => { const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 256; const c = cv.getContext('2d');
        const gr = c.createLinearGradient(0, 0, 0, 256); gr.addColorStop(0, '#bfe0f2'); gr.addColorStop(1, '#e8f4f8'); c.fillStyle = gr; c.fillRect(0, 0, 1024, 256);
        c.fillStyle = '#7d9cc4'; c.beginPath(); c.moveTo(250, 256); c.lineTo(512, 40); c.lineTo(774, 256); c.fill(); c.fillStyle = '#f6f6f2'; c.beginPath(); c.moveTo(452, 90); c.lineTo(512, 40); c.lineTo(572, 90); c.lineTo(540, 104); c.lineTo(512, 92); c.lineTo(482, 106); c.fill();
        c.fillStyle = '#9cc4e8'; for (let x = 0; x < 1024; x += 64) { c.beginPath(); c.arc(x + 32, 250, 34, Math.PI, 0); c.fill(); } return new THREE.CanvasTexture(cv); })();
      const mural = new THREE.Mesh(new THREE.PlaneGeometry(10, 2.5).rotateX(-Math.PI / 2), M(0xffffff, { map: fuji })); mural.position.set(2, 0.02, -6.6); mural.visible = false; G.add(mural);   // (behind the camera: not shown)
      // wash stations down the left wall: low stools, wooden buckets, mirrors, and tall tiled screens between them (cover)
      for (const z of [-2.8, -6.6, -10.4]) box(-9, -7.0, z - 0.15, z + 0.15, 0, 1.35, 0xc4d8dc, { tall: true });
      for (const z of [-1.0, -4.7, -8.5, -12.2]) {
        box(-8.9, -8.7, z - 0.6, z + 0.6, 1.0, 0.8, 0xdfeef4, { solid: false, cast: false });
        const st = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.3, 0.32, 14), M(0xe2b85e)); st.position.set(-7.9, 0.16, z); st.castShadow = true; G.add(st);
        const bk = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.18, 0.3, 14), M(0xd3ab7a)); bk.position.set(-8.4, 0.15, z + 0.55); bk.castShadow = true; G.add(bk);
      }
      // the rock garden corner and a few plants (tall: cover)
      for (const [x, z, s] of [[7.6, -12.6, 1.0], [7.2, 1.2, 0.8]]) { const p = new THREE.Mesh(new THREE.SphereGeometry(0.9 * s, 14, 10), M(0x6aa55a)); p.position.set(x, 1.2 * s, z); p.castShadow = true; G.add(p); box(x - 0.45, x + 0.45, z - 0.45, z + 0.45, 0, 0.6, 0xcf7a5a); this.blockers.push({ x, z, r: 0.9 * s }); }
      // steam drifting off the bath: soft white clouds that block the view
      for (const [x, z, r0] of [[-0.6, -6.2, 1.5], [3.4, -11.6, 1.4], [5.2, -1.6, 1.3]]) {
        const m = new THREE.Mesh(new THREE.SphereGeometry(r0, 18, 12), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.55, depthWrite: false }));
        m.scale.y = 0.75; m.position.set(x, 1.3, z); G.add(m); this.steam.push({ m, x, z, x0: x, z0: z, r: r0 * 0.9, ph: Math.random() * 6 });
      }
      // ---- the corridor: noren curtains, benches, laundry carts and tall plants (cover)
      wall(-9, 2, -21.2, -20.8, 0xe6d6bb); wall(4.4, 9, -21.2, -20.8, 0xe6d6bb);              // door to the locker room at x 2 .. 4.4
      sign('脱衣所', 'LOCKERS', 3.2, 0, -19.9, 0, '#cf7a5a', '#fff6e6', 2.4, 1.1);
      for (let i = 0; i < 4; i++) box(-4.85 + i * 0.6, -4.35 + i * 0.6, -14.0, -13.9, 0.7, 0.45, 0x3f7fc2, { solid: false, cast: false }); // noren over the bath door
      for (const [x, z] of [[-6.4, -16.2], [5.6, -15.6], [-1.6, -19.8]]) { box(x - 0.7, x + 0.7, z - 0.45, z + 0.45, 0, 1.25, 0xb6c0c8, { tall: true }); this.markers.push(null); }  // laundry carts
      box(-0.6, 1.8, -17.3, -16.9, 0, 0.45, 0xbb8b5e, { solid: false });                                                 // a bench
      for (const [x, z] of [[2.2, -15.2], [-3.4, -19.9]]) { const p = new THREE.Mesh(new THREE.SphereGeometry(0.75, 14, 10), M(0x4f8a4c)); p.position.set(x, 1.1, z); p.castShadow = true; G.add(p); box(x - 0.4, x + 0.4, z - 0.4, z + 0.4, 0, 0.5, 0xcf7a5a); this.blockers.push({ x, z, r: 0.75 }); }
      // ---- the locker room: banks of lockers (tall: they block the view), benches between
      const lockerTex = (() => { const cv = document.createElement('canvas'); cv.width = 256; cv.height = 128; const c = cv.getContext('2d');
        c.fillStyle = '#9db5cb'; c.fillRect(0, 0, 256, 128); c.fillStyle = '#86a2bc'; for (let x = 0; x < 256; x += 64) { c.fillRect(x, 0, 3, 128); } c.fillRect(0, 62, 256, 3);
        c.fillStyle = '#f2ece0'; for (let x = 0; x < 256; x += 64) for (const y of [24, 88]) { c.fillRect(x + 44, y, 10, 14); } return new THREE.CanvasTexture(cv); })();
      lockerTex.wrapS = THREE.RepeatWrapping;
      const bank = (x0, x1, z0, z1) => { const m = box(x0, x1, z0, z1, 0, 1.75, 0xffffff, { mat: { map: lockerTex } }); lockerTex.repeat.set(Math.max(1, (x1 - x0) / 2), 1); return m; };
      this.banks = [bank(-6, 0, -25.3, -24.6), bank(2, 8.6, -25.3, -24.6), bank(-6.5, -1, -30.3, -29.6), bank(0, 6, -30.3, -29.6), bank(-5, 2, -34.1, -33.4)];
      for (const [x0, x1, z] of [[-5, -1, -27.4], [2.6, 7, -32.0]]) box(x0, x1, z - 0.22, z + 0.22, 0, 0.45, 0xbb8b5e, { solid: false });
      // the locker to smash: a sparkle marks it (north face of the right-hand middle bank)
      this.target = { x: 4.6, z: -29.2 };
      this.door = box(-9.3, -9.1, -34.6, -32.2, 0, 1.4, 0xc4a77a, { tall: true });                                     // the storage door (locked)
      sign('倉庫', 'STAFF ONLY', -7.9, 0, -33.4, Math.PI / 2, '#4d4756', '#f6f1e6', 2.0, 1.0);
      // ---- storage: tall shelves of towels and buckets, and THE box
      for (const [x0, x1, z0, z1] of [[-16.8, -15.8, -35.8, -28], [-13.6, -10.6, -27.4, -26.8], [-13.6, -10.6, -36.2, -35.6]]) {
        box(x0, x1, z0, z1, 0, 1.8, 0xbb8b5e);
        for (let y = 0.45; y < 1.8; y += 0.6) box(x0 + 0.05, x1 - 0.05, z0 + 0.05, z1 - 0.05, y, 0.22, [0xf3b9c7, 0xa8dcc6, 0xf6eddc, 0x9db5cb][Math.floor(y * 2) % 4], { solid: false });
      }
      this.boxSpot = { x: -12.6, z: -31.4 };
      const bx = this.pantsBox = this.cardboard(1.0); bx.position.set(this.boxSpot.x, 0, this.boxSpot.z); bx.rotation.y = 0.4; G.add(bx);
      // the sparkles that mark things to do
      const sp = (x, z) => { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.sparkTex(), transparent: true, depthWrite: false, color: 0xffe08a })); s.position.set(x, 1.6, z); s.scale.setScalar(1.1); s.renderOrder = 6; G.add(s); return s; };
      this.spLocker = sp(this.target.x, this.target.z); this.spBox = sp(this.boxSpot.x, this.boxSpot.z); this.spBox.visible = false;
      G.traverse((o) => { if (o.isMesh) o.userData.flatDone = true; });
    }
    sparkTex() {
      if (this._spark) return this._spark;
      const cv = document.createElement('canvas'); cv.width = cv.height = 64; const c = cv.getContext('2d');
      c.fillStyle = '#fff'; c.beginPath(); for (let k = 0; k < 8; k++) { const a = k / 8 * Math.PI * 2, r = k % 2 ? 9 : 30; c.lineTo(32 + Math.cos(a) * r, 32 + Math.sin(a) * r); } c.fill();
      return (this._spark = new THREE.CanvasTexture(cv));
    }
    // a cardboard box, open at the top (the flaps fold out): k = 1 on the floor, worn it's sized to his hips
    cardboard(k) {
      const g = new THREE.Group(), card = S.Flat.mat(0xd3a96e), dark = S.Flat.mat(0xb98c52), tape = S.Flat.mat(0xe9d6a8);
      const W = 1.6 * k, H = 0.8 * k, D = 1.4 * k, T = 0.05 * k;
      const side = (w, h, d, x, y, z, m) => { const s = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m || card); s.position.set(x, y, z); s.castShadow = true; s.receiveShadow = true; g.add(s); return s; };
      side(W, H, T, 0, H / 2, D / 2); side(W, H, T, 0, H / 2, -D / 2); side(T, H, D, W / 2, H / 2, 0, dark); side(T, H, D, -W / 2, H / 2, 0, dark);
      side(W, T, D, 0, T / 2, 0, dark);
      for (const [x, z, ry, w] of [[0, D / 2 + 0.18 * k, 0.5, W], [0, -D / 2 - 0.18 * k, -0.5, W]]) { const f = side(w, T, 0.38 * k, x, H + 0.06 * k, z); f.rotation.x = ry; }
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
    makeNpcs() {
      const mk = (kind, route, o) => {
        o = o || {};
        const a = { kind, x: route[0][0], z: route[0][1], y: o.y || 0, f: o.f || 0, vx: 0, vz: 0, st: 'free', t: 0, hp: 1, maxHp: 1, dead: false, engage: false };
        const v = new S.WorkerView(this.scene, kind, !!o.fat, o.pick); v.walls = this.walls;
        const cone = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial({ color: 0xffcf3a, transparent: true, opacity: 0.4, depthWrite: false, side: THREE.DoubleSide }));
        cone.renderOrder = 2; this.scene.add(cone);
        return { a, v, route, i: 0, wait: 0, mode: 'route', alarm: 0, cone, range: o.range || 6.2, half: o.half || 0.62, spin: o.spin || 0, alarmRoute: o.alarmRoute || null, room: o.room, speed: o.speed || 1.35, look: 0 };
      };
      return [
        // the bath attendant walks round the bath, stopping at each corner to look about
        mk('fighter', [[7.6, -1.6, 2.0, Math.PI], [7.6, -12.4, 1.6, -Math.PI / 2], [-0.4, -12.6, 2.6, Math.PI * 0.95], [-0.6, -1.4, 1.8, Math.PI * 0.8]], { room: 'hall' }),
        // a bather soaking in the bath, slowly looking all the way round
        mk('grappler', [[2.2, -6.6, 999, 0]], { y: -0.85, spin: 0.42, range: 7.2, half: 0.5, room: 'hall', fat: true }),
        // the corridor: someone shuttling laundry from one end to the other
        mk('technical', [[-7.6, -18.0, 1.4, Math.PI], [7.0, -18.0, 1.4, 0]], { room: 'corr', alarmRoute: [[3.2, -18.4], [3.2, -23.2], [5.0, -27.6]] }),
        // the locker room attendant patrols the aisles
        mk('fighter', [[-7.6, -27.6, 1.6, Math.PI], [7.6, -27.6, 1.2, 0], [7.6, -32.0, 1.2, -Math.PI / 2], [-7.6, -32.0, 1.8, Math.PI]], { room: 'lock', pick: 1, alarmRoute: [[7.4, -27.6], [5.4, -27.9]] }),
      ];
    }
    // can this NPC see that point? (inside the cone, nothing tall in between)
    sees(n, x, z, range) {
      const a = n.a, dx = x - a.x, dz = z - a.z, d = Math.hypot(dx, dz);
      if (d > range || d < 0.01) return d < 0.9;
      if (Math.abs(ang(Math.atan2(dz, dx) - a.f)) > n.half) return false;
      return this.clear(a.x, a.z, x, z);
    }
    clear(x0, z0, x1, z1) {
      for (const w of this.walls) { if (!w.tall) continue; if (segBox(x0, z0, x1, z1, w.x0 - 0.05, w.z0 - 0.05, w.x1 + 0.05, w.z1 + 0.05)) return false; }
      for (const b of this.blockers.concat(this.steam)) if (segCircle(x0, z0, x1, z1, b.x, b.z, b.r)) return false;
      return true;
    }
    // how far the view reaches along a ray (for drawing the cone, clipped by walls)
    reach(x0, z0, a, L) {
      const x1 = x0 + Math.cos(a) * L, z1 = z0 + Math.sin(a) * L; let t = 1;
      for (const w of this.walls) { if (!w.tall) continue; const h = segBoxT(x0, z0, x1, z1, w.x0, w.z0, w.x1, w.z1); if (h !== null && h < t) t = h; }
      for (const b of this.blockers.concat(this.steam)) { const h = segCircleT(x0, z0, x1, z1, b.x, b.z, b.r); if (h !== null && h < t) t = h; }
      return t * L;
    }
    npcStep(n, dt) {
      const a = n.a; a.t += dt;
      let tx = null, tz = null, sp = n.speed;
      if (n.mode === 'alarm' || n.mode === 'back') {
        const R = n.mode === 'alarm' ? n.alarmRoute : n.alarmRoute.slice().reverse();
        const p = R[n.ai];
        if (p) { tx = p[0]; tz = p[1]; sp = n.mode === 'alarm' ? 2.6 : 1.5; if (Math.hypot(tx - a.x, tz - a.z) < 0.25) { n.ai++; if (n.ai >= R.length) { if (n.mode === 'alarm') { n.mode = 'search'; n.wait = 4.5; } else { n.mode = 'route'; n.i = n.alarmI || 0; } } } }
      } else if (n.mode === 'search') { // looking round where the noise was
        n.wait -= dt; a.f += Math.sin(a.t * 1.6) * dt * 1.6;
        if (n.wait <= 0) { n.mode = 'back'; n.ai = 0; }
      } else {
        const p = n.route[n.i];
        if (n.wait > 0) { n.wait -= dt; a.f = lerpA(a.f, p[3] + Math.sin(a.t * 0.9) * 0.6, dt * 2.5); if (n.wait <= 0) n.i = (n.i + 1) % n.route.length; }
        else { tx = p[0]; tz = p[1]; if (Math.hypot(tx - a.x, tz - a.z) < 0.2) { n.wait = p[2]; tx = null; } }
      }
      if (n.spin) a.f += n.spin * dt;
      if (tx !== null) {
        const dx = tx - a.x, dz = tz - a.z, d = Math.hypot(dx, dz) || 1;
        a.vx = dx / d * sp; a.vz = dz / d * sp; a.f = lerpA(a.f, Math.atan2(dz, dx), dt * 7);
      } else { a.vx *= 0.8; a.vz *= 0.8; }
      a.x += a.vx * dt; a.z += a.vz * dt;
    }
    alarmAt(x, z) { // the noise: whoever has an alarm route comes to look (and the cones go orange)
      for (const n of this.npcs) if (n.alarmRoute) { n.alarmI = n.i; n.mode = 'alarm'; n.ai = 0; n.wait = 0; this.popAt(n.a, '?!', 1.6); }
      this.fx.ring(x, z, 3.2, 0.7); this.fx.ring(x, z, 5, 0.9);
      if (this.g.audio) { this.g.audio.thump && this.g.audio.thump(8); setTimeout(() => this.g.audio && this.g.audio.thump && this.g.audio.thump(5), 140); }
    }

    // ============================================================== the frame
    frame(dt) {
      if (!this.scene) return;
      if (!this.paused && !this.over && !this.freeze) {
        this.acc += Math.min(dt, 0.1); let k = 0;
        while (this.acc >= STEP && k < 8 && !this.freeze) { this.ctrl.update(STEP); this.step(STEP); this.acc -= STEP; k++; }
      } else if (this.paused || this.over) { this.ctrl.update(dt); if (this.over && this.ctrl.push.pressed) this.command('retry'); }
      if (this.freeze) { this.freeze -= dt; if (this.freeze <= 0) { this.freeze = 0; this.respawn(); } }
      S.kb && S.kb.flush && S.kb.flush();
      this.draw(dt);
    }
    step(dt) {
      this.t += dt;
      const P = this.P, c = this.ctrl;
      P.t += dt;
      // moving: crouched (hold L) is slow and low
      let mx = c.mx, mz = c.mz; const mag = Math.hypot(mx, mz); if (mag > 1) { mx /= mag; mz /= mag; }
      P.crouch += ((c.dash.held ? 1 : 0) - P.crouch) * Math.min(1, dt * 10);
      const busy = P.st === 'smash' || P.st === 'wear';
      const spd = busy ? 0 : P.crouch > 0.5 ? 1.7 : 3.4;
      P.vx += (mx * spd - P.vx) * Math.min(1, dt * 10); P.vz += (mz * spd - P.vz) * Math.min(1, dt * 10);
      if (mag > 0.3 && !busy) P.f = lerpA(P.f, Math.atan2(mz, mx), dt * 12);
      P.x += P.vx * dt; P.z += P.vz * dt;
      for (const w of this.walls) { const cx = clamp(P.x, w.x0, w.x1), cz = clamp(P.z, w.z0, w.z1), dx = P.x - cx, dz = P.z - cz, d = Math.hypot(dx, dz); if (d < P.r && d > 1e-6) { P.x = cx + dx / d * P.r; P.z = cz + dz / d * P.r; } }
      for (const b of this.blockers) { const dx = P.x - b.x, dz = P.z - b.z, d = Math.hypot(dx, dz), m = b.r * 0.6 + P.r; if (d < m && d > 1e-6) { P.x = b.x + dx / d * m; P.z = b.z + dz / d * m; } }
      if (busy && P.t > P.dur) { const was = P.st; P.st = 'free'; P.t = 0; if (was === 'smash') this.afterSmash(); if (was === 'wear') this.win(); }
      // the room you're in: checkpoints at each doorway
      const room = P.x < -9.1 ? 'store' : P.z > -14 ? 'hall' : P.z > -21 ? 'corr' : 'lock';
      if (room !== this.room) {
        this.room = room;
        if (room === 'corr' && this.stage === 'hall') { this.stage = 'corr'; this.cp = { x: -3.8, z: -14.9, f: -Math.PI / 2 }; }
        if (room === 'lock' && this.stage === 'corr') { this.stage = 'lock'; this.cp = { x: 3.2, z: -21.9, f: -Math.PI / 2 }; this.think('The lockers! There must be something in there...', 2.6); }
        if (room === 'store' && this.stage === 'noise') { this.stage = 'store'; this.cp = { x: -9.9, z: -33.4, f: Math.PI }; this.spBox.visible = true; this.think('A cardboard box... it\'ll have to do!', 2.8); this.objective('Put on the BOX (press K next to it)'); }
      }
      // K: smash the marked locker / put on the box
      if (c.grab.pressed && P.st === 'free') {
        if (this.stage === 'lock' && Math.hypot(P.x - this.target.x, P.z - this.target.z) < 1.7) { P.st = 'smash'; P.t = 0; P.dur = 0.55; P.f = Math.atan2(-29.95 - P.z, this.target.x - P.x); this.smashT = 0; }
        else if (this.stage === 'store' && Math.hypot(P.x - this.boxSpot.x, P.z - this.boxSpot.z) < 1.8) { P.st = 'wear'; P.t = 0; P.dur = 0.9; }
      }
      if (P.st === 'smash' && P.t > 0.2 && !this.smashed) { this.smashed = true; this.smashLocker(); }
      // the staff
      for (const n of this.npcs) {
        this.npcStep(n, dt);
        const range = n.range * (P.crouch > 0.5 ? 0.62 : 1) * (n.mode === 'search' || n.mode === 'alarm' ? 1.25 : 1);
        if (this.sees(n, P.x, P.z, range)) { const d = Math.hypot(P.x - n.a.x, P.z - n.a.z); n.alarm += dt * (1.0 + 2.2 * (1 - d / range)) * (P.crouch > 0.5 ? 0.8 : 1.15); if (d < 1.8) n.alarm = 1; }   // right in front of them: no way they miss it
        else n.alarm = Math.max(0, n.alarm - dt * 0.6);
        if (n.alarm >= 1) { this.caught(n); break; }
      }
      for (const s of this.steam) { s.x = s.x0 + Math.sin(this.t * 0.3 + s.ph) * 0.6; s.z = s.z0 + Math.cos(this.t * 0.23 + s.ph) * 0.4; }
    }
    smashLocker() {
      // the door caves in, bits fly, a crash the whole building hears
      const L = this.banks[3]; L.position.z += 0.06; L.rotation.z = 0.02;
      for (let k = 0; k < 3; k++) { const d = new THREE.Mesh(new THREE.BoxGeometry(0.6, 1.0, 0.05), S.Flat.mat(0x9db5cb)); d.position.set(this.target.x - 0.6 + k * 0.6, 1.2, -29.5); d.rotation.set(-0.8 - k * 0.3, k * 0.4, 0.3); d.castShadow = true; this.G.add(d); }
      this.fx.dust && this.fx.dust(this.target.x, 0.8, this.target.z, 10, 0.4, 0.6, 0.4);
      this.alarmAt(this.target.x, this.target.z);
      this.spLocker.visible = false;
    }
    afterSmash() {
      this.stage = 'noise'; this.cp = { x: 3.2, z: -21.9, f: -Math.PI / 2 };
      this.think('Ugh... nothing my size in here.', 2.2);
      setTimeout(() => { if (this.scene && this.stage === 'noise') { this.think('...Someone\'s coming! Maybe there\'s something in the STORAGE room.', 3.4); this.objective('Sneak into the STORAGE room (back left of the locker room)'); } }, 2300);
      // the storage door: unlocked (slides open)
      const w = this.door.userData.wall; this.walls.splice(this.walls.indexOf(w), 1); this.door.position.z += 2.2;
    }
    caught(n) {
      this.spotted++; this.freeze = 1.6; this.P.vx = this.P.vz = 0;
      this.popAt(n.a, ['KYAAA!', 'PERVERT!', 'HEY! YOU THERE!', 'MY EYES!'][this.spotted % 4], 1.5, true);
      if (this.g.audio && this.g.audio.whoosh) this.g.audio.whoosh(0.4);
      this.flash = 1;
    }
    respawn() {
      const P = this.P; P.x = this.cp.x; P.z = this.cp.z; P.f = this.cp.f; P.vx = P.vz = 0; P.st = 'free';
      for (const n of this.npcs) { n.alarm = 0; if (n.mode !== 'route') { n.mode = 'route'; } n.i = 0; n.wait = 0; n.a.x = n.route[0][0]; n.a.z = n.route[0][1]; n.a.f = n.route[0][3] || 0; }
      this.think(['Too close... try again.', 'Wait for them to look away.', 'Stay behind cover, then move.'][this.spotted % 3], 2.2);
    }
    win() {
      this.over = 'win'; this.wearing = true; this.pantsBox.visible = false; this.spBox.visible = false;
      const b = this.cardboard(0.95); b.position.set(0, -0.62 * this.view.s, 0.02 * this.view.s); this.view.body.add(b); this.worn = b;
      this.think('Perfect fit. Nobody will ever know.', 3);
      if (this.g.audio && this.g.audio.swell) this.g.audio.swell(0.6, 1.4);
      setTimeout(() => { if (!this.scene) return; const e = this.el('.st-over'); e.innerHTML = '<h2 data-jp="成功">BOX PANTS ACQUIRED</h2><p>Time ' + fmtT(this.t) + ' · Spotted ' + this.spotted + ' time' + (this.spotted === 1 ? '' : 's') + '</p><button data-c="retry">PLAY AGAIN</button><button data-c="quit">QUIT TO TITLE</button><p class="k">Enter / J play again · Esc quit</p>'; e.classList.add('on'); this.overI = 0; this.markMenu('.st-over', 0); }, 1800);
    }

    // ============================================================== drawing
    draw(dt) {
      const P = this.P, T = this.t, w = this.w, v = this.view;
      if (S.SoftSumo && S.SoftSumo.loaded && !v.soft) S.SoftSumo.attach(v, { noBlob: true });
      if (v.soft && !v.pantsOff) { v.pantsOff = true; for (const m of v.soft.mats) if (/mawashi/i.test(m.name || '')) m.visible = false; }
      // the wrestler view, as the campaign drives it
      w.x = P.x; w.z = P.z; w.y = 0; w.f = P.f; w.fx = Math.cos(P.f); w.fz = Math.sin(P.f); w.vx = P.vx; w.vz = P.vz; w.spd = Math.hypot(P.vx, P.vz);
      const nst = P.st === 'smash' ? 'palm' : P.st === 'wear' ? 'brace' : 'free';
      if (w.st !== nst) { w.st = nst; w.t = 0; } else w.t = P.t;
      w.hand = 1; w.hunch = P.crouch; w.relaxed = true; w.fxs = {};
      if (this.freeze) { w.fxs.dizzy = 1; }
      v.update(w, Math.max(dt, 1e-4), T);
      for (const n of this.npcs) { n.v.update(n.a, Math.max(dt, 1e-4), T); this.drawCone(n); }
      // censorship: a jittering pixel block over his hips, kept between him and the camera
      const m = this.mosaic; m.s.visible = !this.wearing;
      if (!this.wearing) {
        m.t -= dt;
        if (m.t <= 0) { m.t = 0.1; const g = m.cv.getContext('2d'), sk = ['#e9b894', '#d9a07c', '#f0c8a8', '#c98a6a', '#e0ac88'];
          g.clearRect(0, 0, 8, 5); for (let y = 0; y < 5; y++) for (let x = 0; x < 8; x++) { if ((x === 0 || x === 7) && Math.random() < 0.6) continue; g.fillStyle = sk[(Math.random() * sk.length) | 0]; g.fillRect(x, y, 1, 1); }
          m.s.material.map.needsUpdate = true; }
        const s = v.s, cx = this.cam.position.x - P.x, cz = this.cam.position.z - P.z, cl = Math.hypot(cx, cz) || 1;
        m.s.position.set(P.x + cx / cl * 0.55 * s, (0.62 - 0.22 * P.crouch) * s, P.z + cz / cl * 0.55 * s); m.s.scale.set(1.45 * s, 0.82 * s, 1);
      }
      // sparkles bob
      for (const sp of [this.spLocker, this.spBox]) if (sp.visible) { sp.position.y = 1.6 + Math.sin(T * 3) * 0.12; sp.material.rotation = T * 0.8; }
      for (const s of this.steam) { s.m.position.x = s.x; s.m.position.z = s.z; s.m.material.opacity = 0.45 + 0.12 * Math.sin(T * 0.7 + s.ph); }
      this.fx.update(dt); this.fx.updateSalt && this.fx.updateSalt(dt);
      // camera: high, behind, following (as in the campaign)
      this.camT.lerp(new THREE.Vector3(clamp(P.x * 0.65, -9, 9) + (this.over ? -2.2 : 0), 0, P.z - (this.over ? 0.6 : 2.6)), 1 - Math.exp(-dt * 4));
      const dist = this.over ? 9 : 14, sh = this.flash ? this.flash * 0.25 : 0; this.flash = Math.max(0, (this.flash || 0) - dt * 2);
      this.cam.position.set(this.camT.x + (Math.random() - 0.5) * sh, dist * 0.64, this.camT.z + dist * 0.77);
      this.cam.lookAt(this.camT.x, 0.6, this.camT.z); this.cam.updateMatrixWorld();
      this.flat.lights.aim(this.camT.x, this.camT.z - 3);
      if ((this.cvN = (this.cvN || 0) + 1) % 30 === 1) S.Flat.convert(this.scene, { pastel: 0.6 });
      this.R.r.shadowMap.enabled = true;
      this.R.r.render(this.scene, this.cam);
      this.drawHud(dt);
    }
    drawCone(n) {
      const a = n.a, N = 22, P = this.P, range = n.range * (P.crouch > 0.5 ? 0.62 : 1) * (n.mode === 'search' || n.mode === 'alarm' ? 1.25 : 1);
      const pos = new Float32Array((N + 2) * 3); pos[0] = a.x; pos[1] = 0.03; pos[2] = a.z;
      for (let i = 0; i <= N; i++) { const t = a.f - n.half + (2 * n.half) * i / N, L = this.reach(a.x, a.z, t, range); pos[(i + 1) * 3] = a.x + Math.cos(t) * L; pos[(i + 1) * 3 + 1] = 0.03; pos[(i + 1) * 3 + 2] = a.z + Math.sin(t) * L; }
      const idx = []; for (let i = 1; i <= N; i++) idx.push(0, i + 1, i);
      const g = n.cone.geometry; g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setIndex(idx); g.computeBoundingSphere();
      const k = clamp(n.alarm, 0, 1); n.cone.material.color.setRGB(1, 0.81 - 0.5 * k, 0.23 - 0.1 * k); n.cone.material.opacity = 0.36 + 0.24 * k;
      n.cone.visible = a.y > -0.5 || true;
    }

    // ============================================================== HUD
    buildHud() {
      const h = this.hud = document.createElement('div'); h.id = 'stealthHud';
      h.innerHTML = '<style>#stealthHud{position:fixed;inset:0;pointer-events:none;z-index:6;font-family:"Barlow Condensed",sans-serif;color:#3a3440}' +
        '#stealthHud .st-obj{position:absolute;left:24px;top:20px;background:rgba(255,250,240,.88);padding:8px 14px;border-radius:10px;font-weight:700;font-size:20px;letter-spacing:.02em}' +
        '#stealthHud .st-obj b{color:#cf5a4a}' +
        '#stealthHud .st-think{position:absolute;transform:translate(-50%,-100%);background:#fffaf0;border-radius:18px;padding:8px 16px;font-weight:700;font-size:20px;max-width:340px;text-align:center;box-shadow:0 3px 0 rgba(60,50,70,.15);opacity:0;transition:opacity .2s}' +
        '#stealthHud .st-think.on{opacity:1}#stealthHud .st-think:after{content:"";position:absolute;left:50%;bottom:-12px;width:14px;height:14px;border-radius:50%;background:#fffaf0;transform:translateX(-50%)}' +
        '#stealthHud .st-pop{position:absolute;transform:translate(-50%,-100%);font:400 26px "Dela Gothic One",sans-serif;color:#cf3a3a;text-shadow:0 2px 0 #fff;white-space:nowrap}' +
        '#stealthHud .st-q{position:absolute;transform:translate(-50%,-100%);font:400 24px "Dela Gothic One",sans-serif;color:#e2a13a;text-shadow:0 2px 0 #fff}' +
        '#stealthHud .st-help{position:absolute;left:24px;bottom:18px;font-size:16px;opacity:.75;background:rgba(255,250,240,.7);padding:4px 10px;border-radius:8px}' +
        '#stealthHud .st-pause,#stealthHud .st-over{position:absolute;left:0;top:0;bottom:0;width:min(520px,92vw);display:none;pointer-events:auto;background:linear-gradient(90deg,rgba(30,24,36,.92),rgba(30,24,36,.6) 80%,transparent);padding:80px 60px;color:#f4efe6}#stealthHud .st-over{left:auto;right:0;text-align:right;background:linear-gradient(270deg,rgba(30,24,36,.92),rgba(30,24,36,.6) 80%,transparent)}#stealthHud .st-over button{margin-left:auto}#stealthHud .st-over button.sel{padding-left:0;padding-right:22px;border-left:0;border-right:5px solid #d8262e}' +
        '#stealthHud .on{display:block}#stealthHud h2{font:400 56px "Dela Gothic One",sans-serif;margin:0 0 20px}#stealthHud h2:before{content:attr(data-jp);display:block;font-size:15px;letter-spacing:.5em;color:#d8262e;margin-bottom:8px}' +
        '#stealthHud .st-pause button,#stealthHud .st-over button{display:block;background:none;border:0;color:rgba(244,239,230,.55);font:700 30px "Barlow Condensed",sans-serif;padding:6px 0;cursor:pointer}' +
        '#stealthHud button.sel{color:#f4efe6;padding-left:22px;border-left:5px solid #d8262e}#stealthHud .k{font-size:15px;opacity:.6}</style>' +
        '<div class="st-obj"></div><div class="st-think"></div><div class="st-pops"></div><div class="st-help">WASD move · hold L crouch (harder to spot) · K smash / pick up · Esc pause</div>' +
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
      if (this.thinkT > 0) { this.thinkT -= dt; const p = this.project(P.x, 2.9 * s, P.z), e = this.el('.st-think'); e.style.left = p.x + 'px'; e.style.top = p.y + 'px'; if (this.thinkT <= 0) e.classList.remove('on'); }
      this.pops = this.pops.filter((q) => { q.t -= dt; const p = this.project(q.a.x, 2.6 + (1.4 - q.t) * 0.3, q.a.z); q.d.style.left = p.x + 'px'; q.d.style.top = p.y + 'px'; if (q.t <= 0) { q.d.remove(); return false; } return true; });
      // a "?" over anyone who has half-noticed you
      if (!this.qs) this.qs = this.npcs.map(() => { const d = document.createElement('div'); d.className = 'st-q'; this.el('.st-pops').appendChild(d); return d; });
      this.npcs.forEach((n, i) => { const d = this.qs[i]; if (n.alarm > 0.08 && !this.freeze) { const p = this.project(n.a.x, 2.4 + (n.a.y || 0), n.a.z); d.style.left = p.x + 'px'; d.style.top = p.y + 'px'; d.textContent = n.alarm > 0.6 ? '?!' : '?'; d.style.display = ''; d.style.transform = 'translate(-50%,-100%) scale(' + (0.8 + n.alarm * 0.6) + ')'; } else d.style.display = 'none'; });
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
  const lerpA = (a, b, k) => a + ang(b - a) * Math.min(1, k);
  function segBoxT(x0, z0, x1, z1, bx0, bz0, bx1, bz1) {
    let t0 = 0, t1 = 1; const dx = x1 - x0, dz = z1 - z0;
    for (const [p, q] of [[-dx, x0 - bx0], [dx, bx1 - x0], [-dz, z0 - bz0], [dz, bz1 - z0]]) {
      if (Math.abs(p) < 1e-9) { if (q < 0) return null; continue; }
      const r = q / p; if (p < 0) { if (r > t1) return null; if (r > t0) t0 = r; } else { if (r < t0) return null; if (r < t1) t1 = r; }
    }
    return t0;
  }
  const segBox = (...a) => segBoxT(...a) !== null;
  function segCircleT(x0, z0, x1, z1, cx, cz, r) {
    const dx = x1 - x0, dz = z1 - z0, fx = x0 - cx, fz = z0 - cz, A = dx * dx + dz * dz, B = 2 * (fx * dx + fz * dz), C = fx * fx + fz * fz - r * r;
    if (C < 0) return 0; const D = B * B - 4 * A * C; if (D < 0) return null; const t = (-B - Math.sqrt(D)) / (2 * A); return t >= 0 && t <= 1 ? t : null;
  }
  const segCircle = (...a) => segCircleT(...a) !== null;
  const fmtT = (t) => Math.floor(t / 60) + ':' + String(Math.floor(t % 60)).padStart(2, '0');

  S.Stealth = Stealth;
})();
