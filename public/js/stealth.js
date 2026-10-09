'use strict';
// TEST LEVEL: THE BATHHOUSE (a sento in two floors). The sumo dozes off IN the bath and wakes up with no mawashi.
// GROUND FLOOR  bath hall (Mt Fuji mural) -> wash area / showers -> changing room (lockers) -> back corridor (the boiler)
//               -> a dead end: a cracked wall. Charge through it -> the back stairs
// UPSTAIRS      lounge (tatami, massage chairs, milk fridge) -> the front hall: the genkan with its shoe lockers, the
//               front desk, the storage room behind it, the FIRE EXIT
// The building is a Blender kit (tools/blender/bathhouse_kit.py -> bathhouse_kit.glb); its floor plan, and so every
// collider here, comes from tools/blender/bathhouse_layout.py (-> js/bath-layout.js, S.BathLayout).
//   1 his locker is locked -> the key must be in his wash bucket by the bath -> it isn't -> smash the locker open
//   2 his locker is EMPTY, everyone else's clothes are tiny; the crash brings the staff -> try storage, upstairs
//   3 the back corridor dead-ends at a cracked wall: charge through, up the stairs
//   4 throw something to draw the receptionist away, into storage: a cardboard box (pants!)
//   5 in the box, out by the fire exit (still unseen)
// The bath and the wash area are safe (everyone's naked there); everywhere else, staff and customers walk fixed patterns,
// their view a cone on the floor. Walking is heard by anyone close; I: tiptoe (silent, slow, and he's too heavy to keep
// it up for long); L: charge (loud). K: use / pick up / throw (buckets, wash stools).
(function () {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ang = (a) => Math.atan2(Math.sin(a), Math.cos(a));
  const lerpA = (a, b, k) => a + ang(b - a) * Math.min(1, k);
  const STEP = 1 / 60;
  const UP = 3;                // the upstairs floor height
  // restart points nobody is looking at
  const CP = { lockN: { x: 5.8, z: -25.6, f: -Math.PI / 2 }, lockS: { x: -11.0, z: -45.9, f: Math.PI / 2 }, corr: { x: -10.2, z: -48.4, f: -Math.PI / 2 },
    stair: { x: 9, z: -56.5, f: -Math.PI / 2 },
    store: { x: 9.8, z: -89.4, f: Math.PI / 2 }, laundry: { x: 10.9, z: -49.5, f: 0 }, kitchen: { x: 4.4, z: -51.2, f: -Math.PI / 2 }, toilet: { x: -13.4, z: -37.9, f: Math.PI } };
  const CENSOR = { w: 0.8, h: 0.5, y: -0.55 };   // the pixel block, at hip height below the body centre (the box-pants sit at -0.62)
  const POOL = S.BathLayout.pool;
  const LY = S.BathLayout, EXIT = LY.exit;
  // which room a point is in (noise carries round its own room only; walls muffle it)
  function roomAt(x, z) {
    if (x > 12.4 && z < -43.6 && z > -61) return 'laundry';
    if (x < -12.4 && z < -30.6 && z > -45.4) return 'toilet';
    if (z > -16) return 'bath'; if (z > -27) return 'shower'; if (z > -47) return 'lock';
    if (z > -53.2) return 'corr'; if (z > -61) return x < 6.4 ? 'kitchen' : 'stair';
    if (z > -86) return 'up'; return x > 4 ? 'store' : 'up';
  }
  const SAFE = { bath: 1, shower: 1 };
  function floorY(x, z) {
    if (x < -12.4 && z > -66) return 0;   // the back alley (outside the kitchen) is ground level all the way to its end
    if (z < -61) return x > -12 && x < -4 && z > -70 && z < -62 ? UP + 0.15 : UP;   // the tatami platform, a step up
    if (z < -53 && x > 6.4 && x < 11.6) return UP * clamp((-53 - z) / 8, 0, 1);
    return 0;
  }
  const inPool = (x, z) => x > POOL.x0 && x < POOL.x1 && z > POOL.z0 && z < POOL.z1;

  class Stealth {
    constructor(game) { this.g = game; }

    // ============================================================== setup / teardown
    start(intro) {
      const g = this.g;
      this.R = g.R; this.t = 0; this.acc = 0; this.paused = false; this.over = null; this.spotted = 0;
      this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(0xd9e6e9);
      this.cam = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 2.0, 120);   // (a tight near/far: no flicker where surfaces meet)
      this.fx = new S.FX(this.scene); this.fx.scene = this.scene; this.fx.noMarks = true;
      this.flat = { lights: S.Flat.lights(this.scene, { r: 22 }) };
      const r = this.R.r; r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
      const vg = document.getElementById('vignette'); if (vg) vg.style.display = 'none';
      this.walls = []; this.blockers = []; this.puddles = []; this.buckets = []; this.flying = []; this.grace = 0;
      this.build(); this.buildNav();
      this.ctrl = new S.Controller(new S.KeySource(S.MAPS.solo, 0));
      this.keys = {};
      this.kd = (e) => { if (this.asleep) { if (!e.repeat) this.wake(); return; } this.keys[e.code] = true; if (e.code === 'KeyI' && !e.repeat) this.iPress = true; }; this.ku = (e) => { this.keys[e.code] = false; };
      addEventListener('keydown', this.kd); addEventListener('keyup', this.ku);
      // the player: the soft sumo, no mawashi, up to his chest in the bath
      const arch = S.ARCH[g.sel && g.sel.c1 !== undefined ? g.sel.c1 : 0];
      this.P = { x: 1.2, z: -6.2, y: -0.62, f: Math.PI / 2, vx: 0, vz: 0, r: 0.7, st: 'free', t: 0, dur: 0, crouch: 0, tip: 0, stam: 1, tired: false, chargeT: 0, cd: 0, held: null };
      this.view = new S.WrestlerView(this.scene, arch, this.fx, S.DEF_EQ); this.view.viewer = 0; this.view.match = null;
      this.w = { x: 0, z: 0, y: 0, f: 0, fx: 0, fz: 1, vx: 0, vz: 0, st: 'free', t: 0, dur: 1, fxs: {}, a: arch, idx: 0, szCur: 1, squash: 0, bal: 1, tx: 0, tz: 0, power: 0, pre: null, preT: 0,
        hand: 0, windPow: 0, charges: 0, uprightT: 0, throatT: 0, lifted: false, down: false, fallX: 0, fallZ: 1, clinch: null, slideT: 0, spd: 0, crouchT: 0, lean: 0, gulpI: -1, contact: false, fwdIn: 0, ddx: 0, ddz: 0, boomT: 0, relaxed: true };
      // THE BOSS: the bathhouse's owner, a retired yokozuna (湯乃富士). Grey topknot, his own dark mawashi; ours, he's found
      this.bossOn = !/[?&]noboss/.test(location.search);
      { const ai = Math.max(0, S.ARCH.indexOf(arch)), bA = Object.assign({}, S.ARCH[(ai + 2) % S.ARCH.length], { belt: 0x3b3346 });
        const bv = new S.WrestlerView(this.scene, bA, this.fx, S.DEF_EQ); bv.viewer = 1; bv.match = null; bv.root.visible = false;
        const bw = Object.assign({}, this.w, { a: bA, idx: 1, fxs: {}, carry: null });
        this.boss = { v: bv, w: bw, x: 3, z: -7, y: -2.6, f: Math.PI / 2, on: false, hold: false, st: 'free', t: 0, belt: arch.belt }; }
      this.mosaic = this.makeMosaic();
      this.npcs = this.makeNpcs();
      this.stage = 'locker'; this.cp = { x: 1.2, z: 0.2, f: Math.PI / 2 }; this.room = 'bath';
      this.camT = new THREE.Vector3(this.P.x * 0.8, 0, this.P.z - 2.6);
      this.buildHud();
      this.resize = () => { this.cam.aspect = innerWidth / innerHeight; this.cam.updateProjectionMatrix(); if (this.fx.pmat) this.fx.pmat.uniforms.uScale.value = innerHeight * r.getPixelRatio() / (2 * Math.tan(this.cam.fov * Math.PI / 360)); };
      addEventListener('resize', this.resize); this.resize();
      // straight from the title (the ninja's smoke): he's fast asleep in the bath until a key is pressed
      this.asleep = !!intro;
      if (this.asleep) { this.el('.st-obj').style.display = 'none'; this.el('.st-wake').style.display = 'block'; this.el('.st-zzz').style.display = 'block'; }
      else this.wake();
      if (g.audio && g.audio.swell) g.audio.swell(0.3, 1.2);
    }
    stop() {
      removeEventListener('resize', this.resize); removeEventListener('keydown', this.kd); removeEventListener('keyup', this.ku);
      if (this.hud) this.hud.remove();
      this.R.r.shadowMap.enabled = !!this.R.flat;
      const vg = document.getElementById('vignette'); if (vg) vg.style.display = this.R.flat ? 'none' : '';
      this.scene = null;
    }
    wake() {
      this.asleep = false; this.el('.st-obj').style.display = ''; this.el('.st-wake').style.display = 'none'; this.el('.st-zzz').style.display = 'none';
      this.objective('Get out of the BATH (the steps, towards you)');
      this.think('Zzz... mm? I fell asleep in the bath again...', 3.0);
    }
    later(sec, fn) { (this.timers || (this.timers = [])).push({ t: sec, fn }); }

    // ============================================================== the bathhouse
    // colliders from the shared floor plan; the look is the Blender kit, loaded on top (items wait for it to arrive)
    build() {
      const G = new THREE.Group(); this.scene.add(G); this.G = G;
      const add = (x0, x1, z0, z1, tall) => { const w = { x0: Math.min(x0, x1), x1: Math.max(x0, x1), z0: Math.min(z0, z1), z1: Math.max(z0, z1), tall: !!tall }; this.walls.push(w); return w; };
      // breakable pieces collide segment by segment (each can be smashed on its own)
      // the back alley outside the kitchen door: its concrete apron only (invisible kerbs; never out into the void)
      add(-19.2, -16.4, -64.8, -53.6, true); add(-19.2, -12.4, -64.8, -62.0, true); add(-19.2, -12.4, -56.0, -53.6, true);   // (thick: he's wide, a thin kerb could be squeezed through)
      this.solidW = LY.solids.map((s) => { if (!s.brk || s.n < 2) return [add(s.x0, s.x1, s.z0, s.z1, s.tall)];
        return [...Array(s.n)].map((_, k) => s.ax === 'x' ? add(s.x0 + (s.x1 - s.x0) * k / s.n, s.x0 + (s.x1 - s.x0) * (k + 1) / s.n, s.z0, s.z1, s.tall)
          : add(s.x0, s.x1, s.z0 + (s.z1 - s.z0) * k / s.n, s.z0 + (s.z1 - s.z0) * (k + 1) / s.n, s.tall)); });
      for (const d of LY.doors) {
        if (d.kind === 'slide') { add(d.x0, (d.x0 + d.x1) / 2 + 0.1, d.z - 0.24, d.z - 0.14, true); continue; }
        if (d.kind === 'zframe') { for (const z of [d.z0 - 0.14, d.z1 + 0.14]) add(d.x - 0.28, d.x + 0.28, z - 0.15, z + 0.15, true); continue; }
        for (const x of [d.x0 - 0.14, d.x1 + 0.14]) add(x - 0.15, x + 0.15, d.z - 0.28, d.z + 0.28, true);
      }
      // dressing in the kit that stands in the way: the back counter behind the desk, boxes on the storage floor
      add(0, 8.6, -85.8, -85.2, false); add(4.45, 5.15, -87.25, -86.55, false); add(5.95, 6.85, -91.85, -90.95, false); add(10.6, 11.4, -87.4, -86.6, false);
      const C = LY.crack; this.crackW = add(C.x0, C.x1, C.z0, C.z1, true); this.crack = { x: C.x, z: C.z };
      this.blockerB = LY.blockers.map((b) => { const o = { x: b.x, z: b.z, r: b.r }; this.blockers.push(o); return o; });
      for (const q of LY.puddles) this.puddles.push({ x: q.x, z: q.z, rx: q.rx, rz: q.rz, y: q.f ? UP : 0 });
      this.locker = { x: LY.locker.x, z: LY.locker.z };
      this.washSpot = { x: LY.washb.x, z: LY.washb.z }; this.boxSpot = { x: LY.box.x, z: LY.box.z };
      // things he can pick up and throw (the kit's prototypes are cloned in when it arrives)
      const holder = (x, y, z) => { const g = new THREE.Group(); g.position.set(x, y, z); G.add(g); return g; };
      for (const it of LY.items) { const y = it.f ? UP : 0, m = holder(it.x, y, it.z); m.rotation.y = (it.x * 7 + it.z * 3) % 6.28; this.buckets.push({ m, kind: it.k, x: it.x, z: it.z, y, state: 'floor', x0: it.x, z0: it.z, base: y }); }
      this.washB = holder(this.washSpot.x, 0, this.washSpot.z);
      this.pantsBox = holder(this.boxSpot.x, UP, this.boxSpot.z); this.pantsBox.rotation.y = LY.box.ry;
      // "go here" markers: a soft ring on the floor and a small rounded arrow bobbing above it
      const sp = (x, z) => { const g = new THREE.Group(); g.position.set(x, floorY(x, z), z); g.visible = false; G.add(g);
        const ring = new THREE.Mesh(new THREE.RingGeometry(0.62, 0.78, 40).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85, depthWrite: false }));
        ring.position.y = 0.03; ring.renderOrder = 3; g.add(ring);
        const ar = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.arrowTex(), transparent: true, depthWrite: false, depthTest: false })); ar.scale.set(0.62, 0.62, 1); ar.position.y = 2.3; ar.renderOrder = 7; g.add(ar);
        g.userData = { ring, ar }; return g; };
      this.spOut = sp(1, -0.9); this.spLocker = sp(this.locker.x, this.locker.z + 0.6); this.spKey = sp(this.washSpot.x, this.washSpot.z); this.spCrack = sp(LY.crack.x, LY.crack.z1 + 0.9);
      { const q = LY.solids.find((o) => o.k === 'vending' && !o.f); if (q) { this.spVend = sp(q.x0 - 0.75, (q.z0 + q.z1) / 2); this.spVend.userData.ar.visible = false; this.spVend.visible = true; } }   // (just the ring: something to use here)
      this.spBox = sp(this.boxSpot.x, this.boxSpot.z); this.spTowel = sp(LY.towel.x, LY.towel.z); this.spExit = sp((LY.entrance.x0 + LY.entrance.x1) / 2, LY.entrance.z + 1.2);
      const ST = LY.stalls[LY.stall_use]; this.spKitchen = sp(LY.kdoor.x, LY.kdoor.z + 0.9); this.spOni = sp(LY.onigiri.x, LY.onigiri.z - 1.3); this.spStall = sp(ST.x + 1.6, ST.z);
      this.spTP = sp(LY.tp.x, LY.tp.z); this.spBack = sp(LY.backdoor.x + 0.8, (LY.backdoor.z0 + LY.backdoor.z1) / 2);
      // the onigiri plate (the chef fills it), the rats that raid it, the mousetraps (set out once the food has gone missing)
      const O = LY.onigiri; this.oni = { n: 0, eaten: 0, g: holder(O.x, O.y, O.z), pieces: [] };
      const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.3, 0.04, 24), S.Flat.mat(0xf2ede4)); plate.position.y = 0.02; plate.castShadow = true; plate.userData.flatDone = true; this.oni.g.add(plate);
      this.rats = [0, 1, 2].map((i) => { const h = LY.ratholes[0]; return { hx: h.x, hz: h.z, x: h.x, z: h.z, st: 'home', t: 5 + i * 4, m: holder(h.x, 0, h.z), carry: false, wi: 0 }; });   // three rats, one hole
      for (const r of this.rats) r.m.visible = false;
      this.traps = LY.traps.map((q) => ({ x: q.x, z: q.z, armed: true, m: holder(q.x, 0, q.z) }));
      for (const t of this.traps) { t.m.visible = false; t.m.rotation.y = (t.x * 3) % 6.28; }
      this.marks = [this.spOut, this.spLocker, this.spKey, this.spCrack, this.spBox, this.spExit, this.spTowel, this.spKitchen, this.spOni, this.spStall, this.spTP, this.spBack]; if (this.spVend) this.marks.push(this.spVend);
      this.spOut.visible = true;
      // laundry carts: push them about (K), hide inside (I, standing still next to one)
      this.carts = (LY.carts || []).map((q) => { const c = { x: q.x, z: q.z, f: q.r || 0, hx: q.x, hz: q.z, hf: q.r || 0, vx: 0, vz: 0, m: holder(q.x, 0, q.z), w: add(0, 0, 0, 0, false) }; this.cartBox(c); return c; });
      S.loadBathKit().then((root) => { if (this.scene && root) this.dress(root.clone(true)); });   // (fetched in the background at start-up; each play gets its own copy)
    }
    // the cart's collider: the box round it, turned (1.3 long, 0.9 wide)
    cartBox(c) {
      const ca = Math.abs(Math.cos(c.f)), sa = Math.abs(Math.sin(c.f)), hx = ca * 0.66 + sa * 0.46, hz = sa * 0.66 + ca * 0.46, w = c.w;
      if (c.off) { w.x0 = w.x1 = w.z0 = w.z1 = 1e4; return; }
      w.x0 = c.x - hx; w.x1 = c.x + hx; w.z0 = c.z - hz; w.z1 = c.z + hz;
      c.m.position.set(c.x, 0, c.z); c.m.rotation.y = -c.f;
    }
    cartStep(dt) {
      const P = this.P;
      for (const c of this.carts) {
        if (c === P.cart) { c.ret = null; continue; }
        if (c.ret) {   // a worker wheels it back where it belongs, round the walls, walking behind it (him inside too, if he's hiding in it)
          const r = c.ret; r.t += dt; c.off = true; this.cartBox(c);
          if (!r.path) { r.path = (this.navPath(c.x, c.z, c.hx, c.hz) || []).concat([[c.hx, c.hz]]); r.pi = 0; }
          const tgt = r.path[r.pi]; let vx = 0, vz = 0;
          if (tgt) {
            const dx = tgt[0] - c.x, dz = tgt[1] - c.z, d = Math.hypot(dx, dz), sp = 1.1;
            if (d < 0.15) r.pi++; else { vx = dx / d * sp; vz = dz / d * sp; c.f = lerpA(c.f, Math.atan2(dz, dx), dt * 5); }
            const q = { x: c.x + vx * dt, z: c.z + vz * dt }; if (r.pi < r.path.length - 1) this.collide(q, 0.5); c.x = q.x; c.z = q.z;
          } else { c.f = lerpA(c.f, c.hf, dt * 5); if (Math.abs(ang(c.f - c.hf)) < 0.05 || r.t > 25) { c.f = c.hf; c.ret = null; if (r.n) { r.n.hold = 0; r.n.pushing = false; } } }
          if (r.t > 25 && c.ret) { c.x = c.hx; c.z = c.hz; c.f = c.hf; c.ret = null; if (r.n) { r.n.hold = 0; r.n.pushing = false; } }   // (never stuck for good)
          if (r.n) { const n = r.n.a, fx = Math.cos(c.f), fz = Math.sin(c.f); n.x = c.x - fx * 1.15; n.z = c.z - fz * 1.15; this.collide(n, 0.35); n.f = c.f; n.vx = vx; n.vz = vz; r.n.pushing = true; }
          c.off = false; this.cartBox(c); if (P.hidden === c) { P.x = c.x; P.z = c.z; }
          continue;
        }
        if (Math.abs(c.vx) + Math.abs(c.vz) > 0.05) {   // sent rolling by a charge
          c.off = true; this.cartBox(c); c.x += c.vx * dt; c.z += c.vz * dt; c.vx *= 0.96; c.vz *= 0.96; c.f += (c.spin || 0) * dt;
          const q = { x: c.x, z: c.z }; if (this.collide(q, 0.55)) { c.vx *= -0.4; c.vz *= -0.4; } c.x = q.x; c.z = q.z; c.off = false; this.cartBox(c);
        }
      }
      if (P.cart) {   // pushing: the cart rolls in front of him; he steers it
        const c = P.cart, d = 1.35 * this.view.s / 1.15; c.off = true; this.cartBox(c);
        const f0 = c.f; c.f = lerpA(c.f, P.f, dt * 8); let q = { x: P.x + Math.cos(c.f) * d, z: P.z + Math.sin(c.f) * d }; this.collide(q, 0.55);
        if (!this.clear(P.x, P.z, q.x, q.z) || Math.hypot(q.x - P.x, q.z - P.z) < d * 0.7) { c.f = f0; q = { x: c.x, z: c.z }; }   // (it won't swing round into, or through, a wall)
        c.x = q.x; c.z = q.z; const pp = { x: c.x - Math.cos(c.f) * d, z: c.z - Math.sin(c.f) * d }; this.collide(pp, P.r);
        if (this.clear(c.x, c.z, pp.x, pp.z) && this.clear(P.x, P.z, pp.x, pp.z)) { P.x = pp.x; P.z = pp.z; }   // (and he's never put inside one behind it)
        c.m.position.set(c.x, 0, c.z); c.m.rotation.y = -c.f;
      }
      if (P.hidden) { const c = P.hidden; if (c.mesh) { c.mesh.scale.y = 1 + Math.sin(this.t * 2.2) * 0.02; } }
    }
    dress(root) {
      this.kit = root; this.scene.add(root);
      const get = (n) => root.getObjectByName(n), proto = {};
      for (const n of ['ITEM_STOOL', 'ITEM_OKE', 'ITEM_BUCKET', 'ITEM_WASHB', 'BOX', 'CLOTH_SHIRT', 'CLOTH_SHORTS', 'ITEM_CAN0', 'ITEM_CAN1', 'ITEM_CAN2']) { const o = get(n); if (o) { o.visible = false; proto[n] = o; } }
      this.proto = proto;
      const clone = (n) => { const o = proto[n].clone(); o.visible = true; o.position.set(0, 0, 0); o.rotation.set(0, 0, 0); o.traverse((q) => { if (q.isMesh) q.castShadow = true; }); return o; };
      this.cloneP = (n) => proto[n] ? clone(n) : null;
      for (const b of this.buckets) if (proto['ITEM_' + b.kind.toUpperCase()]) { const o = clone('ITEM_' + b.kind.toUpperCase()); b.m.add(o);
        if (b.kind === 'oke' || b.kind === 'bucket') {   // every tub and bucket has water in it (thrown or smashed: a puddle)
          const bb = new THREE.Box3().setFromObject(o), sz = bb.getSize(new THREE.Vector3()), r = Math.min(sz.x, sz.z) * 0.42;
          const w = new THREE.Mesh(new THREE.CircleGeometry(r, 20), new THREE.MeshBasicMaterial({ color: 0x8fcdf0, transparent: true, opacity: 0.85 })); w.rotation.x = -Math.PI / 2; w.position.y = bb.max.y - b.m.position.y - sz.y * 0.22; w.userData.flatDone = true;
          o.add(w); b.waterM = w; b.water = true; } }
      if (proto.ITEM_WASHB) this.washB.add(clone('ITEM_WASHB'));
      if (proto.BOX) this.pantsBox.add(clone('BOX'));
      if (proto.ITEM_ONIGIRI || get('ITEM_ONIGIRI')) { const op = get('ITEM_ONIGIRI'); op.visible = false; proto.ITEM_ONIGIRI = op;
        for (let k = 0; k < 4; k++) { const o = op.clone(); o.visible = false; o.position.set((k % 2 - 0.5) * 0.24, 0.04, (Math.floor(k / 2) - 0.5) * 0.2); o.rotation.y = k * 0.7; this.oni.g.add(o); this.oni.pieces.push(o); }
        this.oniDraw(); }
      const ratP = get('ITEM_RAT'); if (ratP) { ratP.visible = false; for (const r of this.rats) { const o = ratP.clone(); o.visible = true; o.position.set(0, 0, 0); r.m.add(o); } }
      const trapP = get('ITEM_TRAP'); if (trapP) { trapP.visible = false; for (const t of this.traps) { const o = trapP.clone(); o.visible = true; o.position.set(0, 0, 0); t.m.add(o); t.mesh = o; } }
      this.stallDoors = LY.stalls.map((q, k) => get('STALLDOOR_' + k)).filter(Boolean);
      if (proto.BOX) { this.squatBox = clone('BOX'); this.squatBox.visible = false; this.scene.add(this.squatBox); }
      const cartP = get('ITEM_CART'); if (cartP) { cartP.visible = false; for (const c of this.carts) { const o = cartP.clone(); o.visible = true; o.position.set(0, 0, 0); c.m.add(o); c.mesh = o; } }
      this.water = get('WATER'); this.crackM = get('CRACK_WALL'); this.rubble = get('CRACK_RUBBLE'); this.holes = get('LKHOLES');
      if (this.rubble) this.rubble.visible = false; if (this.holes) this.holes.visible = false;
      this.lkDoors = [0, 1, 2, 3, 4].map((k) => get('LKDOOR_' + k)).filter(Boolean);
      // everything but the walls breaks under a charge (his own locker only dents: see the charge)
      const pad = (i) => String(i).padStart(2, '0'); this.breakables = [];
      const vi = LY.solids.findIndex((q) => q.k === 'vending' && !q.f);
      if (vi >= 0) { const q = LY.solids[vi], o = get('SOLID_' + pad(vi) + '_0'); this.vend = { o, x0: q.x0, x1: q.x1, z0: q.z0, z1: q.z1, z: (q.z0 + q.z1) / 2, hits: 0, broke: false, shake: 0, cd: 0 }; }
      LY.solids.forEach((sd, i) => { if (!sd.brk || i === vi) return;
        for (let k = 0; k < sd.n; k++) { const o = get('SOLID_' + pad(i) + '_' + k), w = this.solidW[i][k]; if (!o) continue;
          this.breakables.push({ o, w, s: { k: sd.k, x0: w.x0, x1: w.x1, z0: w.z0, z1: w.z1, h: sd.h, f: sd.f } }); } });
      LY.blockers.forEach((b, i) => { const o = get('PLANT_' + pad(i)); if (o) this.breakables.push({ o, bl: this.blockerB[i], s: { k: 'plant', x0: b.x - b.r * 0.6, x1: b.x + b.r * 0.6, z0: b.z - b.r * 0.6, z1: b.z + b.r * 0.6, h: 1.4 * (b.s || 1), f: b.f } }); });
      if (this.crackDone) { if (this.crackM) this.crackM.visible = false; if (this.rubble) this.rubble.visible = true; }
      if (this.wearing && !this.boxWorn) this.wearBox();
    }
    arrowTex() {
      if (this._arrow) return this._arrow;
      const cv = document.createElement('canvas'); cv.width = cv.height = 128; const c = cv.getContext('2d');
      const tri = () => { c.beginPath(); c.moveTo(64, 104); c.lineTo(22, 40); c.quadraticCurveTo(14, 26, 30, 26); c.lineTo(98, 26); c.quadraticCurveTo(114, 26, 106, 40); c.closePath(); };
      c.lineJoin = 'round'; tri(); c.lineWidth = 16; c.strokeStyle = '#fffaf0'; c.stroke(); c.fillStyle = '#f08a5d'; c.fill();
      return (this._arrow = new THREE.CanvasTexture(cv));
    }
    makeMosaic() {
      const cv = document.createElement('canvas'); cv.width = 8; cv.height = 5;
      const tex = new THREE.CanvasTexture(cv); tex.magFilter = tex.minFilter = THREE.NearestFilter;
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false })); s.renderOrder = 5; s.visible = false; this.scene.add(s);
      return { s, cv, t: 0 };
    }

    // ============================================================== the staff and customers: fixed patterns, cones of view
    // route points: [x, z, wait, look]. They walk between points (and to any noise) by the shortest way round
    // lockers, benches and walls (a grid path), wait, and look the given way, swaying their head a little.
    makeNpcs() {
      const mk = (kind, route, o) => {
        o = o || {};
        const a = { kind, x: route[0][0], z: route[0][1], y: floorY(route[0][0], route[0][1]), f: route[0][3] || 0, vx: 0, vz: 0, st: 'free', t: 0, hp: 1, maxHp: 1, dead: false, engage: false };
        const v = new S.WorkerView(this.scene, kind, !!o.fat, o.pick); v.walls = this.walls; if (v.pole && v.pole.parent) v.pole.parent.remove(v.pole);   // (the market staff's hook-pole: not in a bathhouse)
        const cone = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial({ color: 0xffcf3a, transparent: true, opacity: 0.4, depthWrite: false, side: THREE.DoubleSide }));
        cone.renderOrder = 2; this.scene.add(cone);
        return { a, v, route, i: 0, wait: route[0][2], mode: 'route', alarm: 0, cone, onigiri: !!o.onigiri, range: o.range || 6.4, half: o.half || 0.62, room: o.room, speed: o.speed || 1.35, sway: o.sway || 0.6, ear: o.ear || 0, path: null, pi: 0 };
      };
      const P = Math.PI, U = P / 2;
      return [
        // CHANGING ROOM. The attendant walks the two middle aisles, stopping at the ends to look along them
        mk('fighter', [[-10.4, -33.0, 1.6, 0], [10.6, -33.0, 1.4, P], [2.5, -33.4, 0, 0], [2.5, -38.2, 0, 0], [10.6, -38.2, 1.4, P], [-3.6, -38.2, 1.8, P], [2.5, -38.2, 0, 0], [2.5, -33.4, 0, 0]], { room: 'lock' }),
        mk('grappler', [[-1.0, -44.4, 2.2, -U], [10.6, -44.4, 2.2, -U]], { room: 'lock', fat: true, speed: 0.9, range: 5.4 }),
        mk('rusher', [[-5.0, -30.0, 4.2, -U], [-5.0, -30.0, 1.8, P], [-5.0, -30.0, 3.6, -U], [-5.0, -30.0, 1.8, 0.15]], { room: 'lock', pick: 1, range: 5.2, sway: 0.3 }),
        mk('thrower', [[-7.0, -43.8, 2.6, U], [-3.0, -43.8, 2.2, U]], { room: 'lock', pick: 3, speed: 0.7, range: 4.6 }),
        // BACK CORRIDOR. The old boilerman stokes the furnace, and every so often turns to look down the corridor
        mk('grappler', [[-2.8, -50.9, 5.0, -U], [-2.8, -50.9, 2.4, 0.25], [-2.8, -50.9, 4.0, -U], [-2.8, -50.9, 2.0, P - 0.25]], { room: 'corr', fat: true, pick: 3, range: 6.6, sway: 0.25 }),
        // LOUNGE. A man trying the massage chairs, a woman choosing a milk, someone on the tatami
        mk('rusher', [[2.7, -63.6, 4.0, -U], [2.7, -63.6, 2.0, 0.4], [2.7, -63.6, 3.0, -U], [2.7, -63.6, 2.0, P - 0.4]], { room: 'up', pick: 0, range: 5.6, sway: 0.3 }),
        mk('thrower', [[9.8, -64.8, 4.4, 0], [9.8, -64.8, 2.2, P - 0.3]], { room: 'up', pick: 2, range: 5.4, sway: 0.25 }),
        mk('fighter', [[-7.8, -66.2, 3.4, 0.3], [-7.8, -66.2, 3.0, -0.6]], { room: 'up', pick: 1, range: 5.4, sway: 0.4 }),
        // FRONT HALL. The receptionist at the desk (she hears anyone that close), a hall attendant, the shoe-locker lady at the entrance
        mk('technical', [[8.0, -84.6, 999, U]], { room: 'up', sway: 0.9, range: 8.2, half: 0.66, ear: 3.6 }),
        mk('staff', [[-2.6, -77.4, 2.2, U], [9.6, -77.4, 2.2, U]], { room: 'up', speed: 1.1 }),
        mk('staff', [[-6.2, -88.8, 999, U]], { room: 'up', pick: 2, sway: 0.7, range: 6.0 }),
        // LAUNDRY ROOM. Two working the aisles between the machines, one folding at the table by the door
        // (they're loading the machines, faces to the washers; every so often they carry a basket along and look down the aisle)
        mk('fighter', [[17.0, -52.62, 5.5, U], [17.0, -52.9, 1.6, 0]], { room: 'laundry', pick: 2, speed: 0.9, range: 4.0, half: 0.48, sway: 0.15 }),
        mk('grappler', [[17.6, -56.88, 5.5, -U], [17.6, -56.6, 1.6, P]], { room: 'laundry', pick: 3, fat: true, speed: 0.8, range: 3.8, half: 0.48, sway: 0.15 }),
        mk('staff', [[17.8, -48.2, 5.0, U], [17.8, -48.2, 2.0, 0.2]], { room: 'laundry', pick: 4, sway: 0.25, range: 3.8, half: 0.5 }),   // folding, back to the door
        // KITCHEN. The onigiri chef goes between his counter (making a few each time) and the stove; one at the stove; one at prep and the pantry
        mk('chef', [[LY.onigiri.chef[0], LY.onigiri.chef[1], 3.0, U], [-3.2, -59.3, 4.5, -U]], { room: 'kitchen', range: 5.6, onigiri: true }),
        mk('chef', [[-6.0, -59.3, 3.0, -U], [0.4, -59.3, 3.0, -U]], { room: 'kitchen', pick: 1, speed: 1.0, range: 5.2 }),
        mk('chef', [[3.4, -55.4, 2.5, P], [3.6, -58.4, 2.5, 0]], { room: 'kitchen', pick: 3, fat: true, range: 5.0 }),
        // TOILETS. A man at the urinals (facing the wall), the cleaner mopping by the sinks
        mk('rusher', [[-14.8, -32.2, 999, U]], { room: 'toilet', pick: 0, range: 4.0, sway: 0.1 }),
        mk('thrower', [[-17.4, -42.6, 2.2, P], [-13.6, -42.6, 2.2, 0]], { room: 'toilet', pick: 2, speed: 0.8, range: 4.8 }),
      ];
    }
    cook(n, dt) {   // true while he's at it (the rest of npcStep is skipped)
      const a = n.a, C = LY.onigiri.chef, d = Math.hypot(a.x - C[0], a.z - C[1]);
      if (n.mode !== 'cook') { if (d > 0.3) { if (!n.path || !n.cookGo) { this.goTo(n, C[0], C[1]); n.cookGo = true; } return false; } n.mode = 'cook'; n.path = null; n.cookGo = false; n.ck = { ph: n.cooked && this.oni.n === 0 ? 'shock' : 'make', t: 0, k: 0 }; }   // (back with more rice to an EMPTY plate: a double take)
      a.vx = a.vz = 0; a.x += (C[0] - a.x) * Math.min(1, dt * 5); a.z += (C[1] - a.z) * Math.min(1, dt * 5); a.y = floorY(a.x, a.z); a.st = 'free';
      const K = n.ck; K.t += dt;
      if (!n.rice && this.proto && this.proto.ITEM_ONIGIRI) { n.rice = this.proto.ITEM_ONIGIRI.clone(); n.rice.visible = false; this.G.add(n.rice); }
      if (K.ph === 'make') {   // kneading at the counter: both hands low in front, a ball of rice pressed between them; one onto the plate every ~1.6 s
        a.f = lerpA(a.f, Math.PI / 2, dt * 6); n.busy = true;
        if (n.rice) { const fx = Math.cos(a.f), fz = Math.sin(a.f), q = Math.sin(K.t * 7.5); n.rice.visible = true; n.rice.scale.set(1.5 * (1 + 0.12 * q), 1.5 * (1 - 0.15 * q), 1.5 * (1 + 0.12 * q)); n.rice.rotation.y = a.f; }
        if (K.t > 1.6) { K.t = 0; K.k++; this.oni.n = Math.min(4, this.oni.n + 1); this.oniDraw(); n.cooked = true; }
        if (K.k >= 3 || this.oni.n >= 4) { K.ph = 'look'; K.t = 0; K.k = 0; this.cookStop(n); }
      } else if (K.ph === 'shock') {   // the plate's empty: a jump, a stare at the plate, a long scratch of the head... then back to work
        a.f = lerpA(a.f, Math.PI / 2, dt * 6); n.busy = false; if (n.rice) n.rice.visible = false;
        if (!K.said) { K.said = true; a.shock = 1; this.popAt(a, 'えっ!?', 1.0); }
        if (K.t > 0.7) { a.shock = 0; n.scratch = true; if (!K.said2) { K.said2 = true; this.popAt(a, ['あれ…?', 'おかしいな…', '…ネズミか?'][(this.t * 3 | 0) % 3], 1.6); } }
        if (K.t > 3.2) { n.scratch = false; K.ph = 'make'; K.t = 0; K.k = 0; }
      } else {   // looks up from the counter, round the kitchen; then off to the rice pot by the stove for more rice
        a.f = lerpA(a.f, -Math.PI / 2 + Math.sin(K.t * 1.2) * 0.7, dt * 3);
        if (K.t > 2.4) { this.cookStop(n); n.mode = 'route'; n.i = 1; this.goTo(n, n.route[1][0], n.route[1][1]); n.ckAway = 9; return false; }
      }
      return true;
    }
    // running (hurrying over, or chasing him) across a puddle: their feet go every time. Walking is fine
    slipCheck(n) {
      const a = n.a, spd = Math.hypot(a.vx, a.vz); if (spd < 1.7 || n.slipCd || a.st !== 'free') return false;
      for (const q of this.puddles) if (Math.abs((q.y !== undefined ? q.y : floorY(q.x, q.z)) - a.y) < 1 && ((a.x - q.x) / (q.rx + 0.15)) ** 2 + ((a.z - q.z) / (q.rz + 0.15)) ** 2 < 1) {
        a.st = 'down'; a.t = 0; a.dur = 1.6; a.slipFall = true; a.fallX = -a.vx / spd; a.fallZ = -a.vz / spd; a.vx *= 0.7; a.vz *= 0.7; n.slipCd = 4; n.alarm = 0; n.pushing2 = false;
        this.popAt(a, ['うわっ!', 'おっと—!', 'いてっ!'][(this.t * 3 | 0) % 3], 1.2); this.fx.water && this.fx.water(a.x, a.z, 5);
        if (this.g.audio && this.g.audio.thump) this.g.audio.thump(5);
        return true;
      }
      return false;
    }
    // straining: drops of sweat fly off their forehead/temples and fall to the floor
    sweat(n, dt) {
      if ((n.dropT = (n.dropT || 0) - dt) > 0) return; n.dropT = 0.07 + Math.random() * 0.08;
      if (!this.drops) { this.drops = []; this.dropGeo = new THREE.SphereGeometry(0.045, 8, 6); this.dropGeo.scale(1, 1.5, 1);
        this.dropMat = new THREE.MeshBasicMaterial({ color: 0x4fb0ff }); }
      const B = n.v.body, h = B && B.bones && B.bones.Head, a = n.a, p = new THREE.Vector3(a.x, a.y + 1.62, a.z);
      if (h) { h.updateMatrixWorld(true); p.setFromMatrixPosition(h.matrixWorld); p.y += 0.12; }
      const sd = Math.random() < 0.5 ? -1 : 1, rx = -Math.sin(a.f) * sd, rz = Math.cos(a.f) * sd;   // off one temple or the other
      let d = this.drops.find((q) => !q.visible);
      if (!d) { if (this.drops.length > 40) return; d = new THREE.Mesh(this.dropGeo, this.dropMat); d.userData.flatDone = true; this.G.add(d); this.drops.push(d); }
      d.visible = true; d.position.set(p.x + rx * 0.09, p.y, p.z + rz * 0.09); d.scale.setScalar(0.8 + Math.random() * 0.5);
      d.userData.v = [rx * (0.7 + Math.random() * 0.6) - Math.cos(a.f) * 0.3, 1.0 + Math.random() * 0.7, rz * (0.7 + Math.random() * 0.6) - Math.sin(a.f) * 0.3]; d.userData.fy = a.y;
    }
    sweatStep(dt) {
      if (!this.drops) return;
      for (const d of this.drops) if (d.visible) { const v = d.userData.v; v[1] -= 9 * dt;
        d.position.x += v[0] * dt; d.position.y += v[1] * dt; d.position.z += v[2] * dt;
        if (d.position.y < d.userData.fy + 0.02) d.visible = false; }
    }
    // the onigiri chef's hands: forearms out over the counter, hands meeting in front, pressing the rice in turn
    knead(n, T, push, w) {
      if (w === undefined) w = 1; n.armT = n.armSeen === this.drawN - 1 ? 1 : 0; n.armSeen = this.drawN;
      const B = n.v.body; if (!B || !B.bones || !B.bones.RightArm) return;
      const V = THREE.Vector3, Q = THREE.Quaternion, f = n.a.f, fw = new V(Math.cos(f), 0, Math.sin(f)), rt = new V(-Math.sin(f), 0, Math.cos(f)), dn = new V(0, -1, 0);
      const aim = (b, c, dir) => { const q00 = b.quaternion.clone(); b.quaternion.identity(); b.updateMatrixWorld(true);   // (always from the same start pose: the walk swing can't flip the twist about frame to frame)
        const bp = new V().setFromMatrixPosition(b.matrixWorld), cp = new V().setFromMatrixPosition(c.matrixWorld);
        const q = new Q().setFromUnitVectors(cp.sub(bp).normalize(), dir.normalize()), wq = b.getWorldQuaternion(new Q()); const q0 = q00; b.quaternion.copy(b.parent.getWorldQuaternion(new Q()).invert().multiply(q.multiply(wq))); if (w < 1) b.quaternion.copy(q0.slerp(b.quaternion, w));
        const sm = n.armQ || (n.armQ = {}), pq = sm[b.name]; if (pq && n.armT > 0) b.quaternion.copy(pq.slerp(b.quaternion, Math.min(1, (this.kdt || 0.016) * 14))); sm[b.name] = b.quaternion.clone(); b.updateMatrixWorld(true); };   // (eased frame to frame: never a snap)
      const press = Math.sin(T * 7.5);
      for (const [sd, up, lo, hd, k] of [[1, 'RightArm', 'RightForeArm', 'RightHand', 1], [-1, 'LeftArm', 'LeftForeArm', 'LeftHand', -1]]) {
        const bu = B.bones[up], bl = B.bones[lo], bh = B.bones[hd]; if (!bu || !bl || !bh) continue;
        if (push) {   // both arms straight out, palms on the box, leaning into it
          aim(bu, bl, fw.clone().multiplyScalar(0.9).add(dn.clone().multiplyScalar(0.6)).add(rt.clone().multiplyScalar(sd * 0.18)));
          aim(bl, bh, fw.clone().multiplyScalar(1).add(dn.clone().multiplyScalar(0.3 + 0.05 * press * k)).add(rt.clone().multiplyScalar(sd * 0.08)));
          continue;
        }
        aim(bu, bl, fw.clone().multiplyScalar(0.55).add(dn.clone().multiplyScalar(0.8)).add(rt.clone().multiplyScalar(sd * 0.12)));
        aim(bl, bh, fw.clone().multiplyScalar(0.75).add(rt.clone().multiplyScalar(-sd * 0.6)).add(dn.clone().multiplyScalar(0.15 + 0.22 * press * k)));
      }
      if (!push && n.rice && B.handPos) { const a = new V(), b = new V(); if (B.handPos('R', a) && B.handPos('L', b)) { n.rice.position.copy(a.add(b).multiplyScalar(0.5)); n.rice.position.y -= 0.04; } }
    }
    cookStop(n) { n.busy = false; n.scratch = false; n.a.shock = 0; if (n.rice) n.rice.visible = false; }
    sees(n, x, z, range) {
      const a = n.a, dx = x - a.x, dz = z - a.z, d = Math.hypot(dx, dz);
      if (d > range) return false;
      if (d > 0.6 && Math.abs(ang(Math.atan2(dz, dx) - a.f)) > n.half) return false;   // (right up against them, they feel you there)
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
      const cs = 0.4, x0 = -15.6, z0 = -93.2, nx = Math.ceil(39.2 / cs), nz = Math.ceil((5.2 - z0) / cs), free = new Uint8Array(nx * nz), R = 0.5;
      for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
        const x = x0 + (i + 0.5) * cs, z = z0 + (j + 0.5) * cs; let ok = true;
        for (const w of this.walls) if (x > w.x0 - R && x < w.x1 + R && z > w.z0 - R && z < w.z1 + R) { ok = false; break; }
        if (ok) for (const b of this.blockers) if (Math.hypot(x - b.x, z - b.z) < b.r * 0.55 + R) { ok = false; break; }
        if (ok && inPool(x, z)) ok = false;
        free[j * nx + i] = ok ? 1 : 0;
      }
      this.nav = { cs, x0, z0, nx, nz, free };
    }
    cell(x, z) { const N = this.nav; return [clamp(Math.floor((x - N.x0) / N.cs), 0, N.nx - 1), clamp(Math.floor((z - N.z0) / N.cs), 0, N.nz - 1)]; }
    walkable(x, z) { const N = this.nav, [i, j] = this.cell(x, z); return !!N.free[j * N.nx + i]; }
    lineWalk(x0, z0, x1, z1) { const d = Math.hypot(x1 - x0, z1 - z0), n = Math.ceil(d / 0.15), bw = this.P && this.P.boxHide && this.boxW && this.boxW.x0 < 1e3 ? this.boxW : null;
      const inB = (x, z) => bw && x > bw.x0 - 0.45 && x < bw.x1 + 0.45 && z > bw.z0 - 0.45 && z < bw.z1 + 0.45, from = inB(x0, z0);   // (and not through the box he's crouched in)
      for (let k = 1; k <= n; k++) { const x = x0 + (x1 - x0) * k / n, z = z0 + (z1 - z0) * k / n; if (!this.walkable(x, z) || (!from && inB(x, z))) return false; } return true; }
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
      // the box he's crouched in is in the way too (the grid itself is fixed): they plan round it
      const bw = this.P.boxHide && this.boxW && this.boxW.x0 < 1e3 ? this.boxW : null, inB = (x, z) => bw && x > bw.x0 - 0.45 && x < bw.x1 + 0.45 && z > bw.z0 - 0.45 && z < bw.z1 + 0.45;
      const segB = () => { if (!bw) return false; const L = Math.hypot(end[0] - x0, end[1] - z0), n = Math.ceil(L / 0.2); for (let k = 1; k <= n; k++) if (inB(x0 + (end[0] - x0) * k / n, z0 + (end[1] - z0) * k / n)) return true; return false; };
      if (start === goal || (this.lineWalk(x0, z0, end[0], end[1]) && !segB())) return [end];
      const M = N.nx * N.nz; if (!N.g) { N.g = new Float32Array(M); N.from = new Int32Array(M); N.seen = new Uint32Array(M); N.shut = new Uint32Array(M); N.gen = 0; }
      const gen = ++N.gen, G = N.g, from = N.from, seen = N.seen, shutA = N.shut, gq = (q) => (seen[q] === gen ? G[q] : 1e9);
      const shut = { get: (k) => shutA[k] === gen, set: (k) => { shutA[k] = gen; } };
      const h = (k) => { const dx = Math.abs(k % N.nx - s1[0]), dz = Math.abs(Math.floor(k / N.nx) - s1[1]); return Math.max(dx, dz) + 0.414 * Math.min(dx, dz); };
      const heap = [], push = (k, f) => { heap.push([f, k]); let c = heap.length - 1; while (c) { const p = (c - 1) >> 1; if (heap[p][0] <= heap[c][0]) break; [heap[p], heap[c]] = [heap[c], heap[p]]; c = p; } };
      const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let c = 0; for (;;) { const l = 2 * c + 1, r = l + 1; let m = c; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === c) break; [heap[m], heap[c]] = [heap[c], heap[m]]; c = m; } } return top; };
      G[start] = 0; seen[start] = gen; from[start] = -1; push(start, h(start)); let found = false;
      while (heap.length) {
        const [, k] = pop(); if (shut.get(k)) continue; shut.set(k); if (k === goal) { found = true; break; }
        const i = k % N.nx, j = Math.floor(k / N.nx);
        for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++) {
          if (!di && !dj) continue; const a = i + di, b = j + dj; if (a < 0 || b < 0 || a >= N.nx || b >= N.nz) continue;
          const q = id(a, b); if (!N.free[q] || shut.get(q)) continue; if (bw && q !== goal) { const [wx, wz] = W(q); if (inB(wx, wz) && !inB(x0, z0)) continue; } if (di && dj && (!N.free[id(i + di, j)] || !N.free[id(i, j + dj)])) continue;
          const ng = G[k] + (di && dj ? 1.414 : 1); if (ng < gq(q)) { G[q] = ng; seen[q] = gen; from[q] = k; push(q, ng + h(q)); }
        }
      }
      if (!found) return null;
      const pts = []; for (let k = goal; k !== -1 && k !== start; k = from[k]) pts.push(W(k)); pts.reverse(); pts[pts.length - 1] = end;
      const out = []; let cx = x0, cz = z0, k = 0;
      while (k < pts.length) { let far = k; for (let m = pts.length - 1; m > k; m--) if (this.lineWalk(cx, cz, pts[m][0], pts[m][1])) { far = m; break; } out.push(pts[far]); cx = pts[far][0]; cz = pts[far][1]; k = far + 1; }
      return out;
    }
    goTo(n, x, z) { n.path = this.navPath(n.a.x, n.a.z, x, z) || [[x, z]]; n.pi = 0; n.stuckT = 0; }
    // a noise: anyone in earshot (in that room) walks over the shortest way to look, searches, goes back
    noise(x, z, radius, msg, soft) {   // soft: footsteps (no ripples on the floor; they walk over to look)
      (this.mapRings || (this.mapRings = [])).push({ x, z, r: radius, t: 0, y: this.P.y }); if (this.mapRings.length > 12) this.mapRings.shift();
      if (!soft) { this.ringAt(x, z, radius * 0.4, 0.6); this.ringAt(x, z, radius * 0.7, 0.9); }
      const room = roomAt(x, z); let rank = 0;
      for (const n of this.npcs) {
        if (n.room !== room || Math.hypot(n.a.x - x, n.a.z - z) > radius || n.a.st !== 'free' || n.hold > 0 || (n.raid && n.mode === 'raid')) continue;
        // several coming to look: each stops at their own spot round it (not all on the same tile)
        const ra = rank ? 1.25 + 0.25 * rank : 0, aa = rank * 2.3 + Math.atan2(n.a.z - z, n.a.x - x), q = { x: x + Math.cos(aa) * ra, z: z + Math.sin(aa) * ra }; if (rank) this.collide(q, 0.4); rank++;
        const path = this.navPath(n.a.x, n.a.z, q.x, q.z) || this.navPath(n.a.x, n.a.z, x, z); if (!path) continue;
        if (n.mode !== 'goto') this.popAt(n.a, msg || '?!', 1.6);
        n.path = path; n.pi = 0; n.stuckT = 0; n.mode = 'goto'; n.noiseAt = [x, z]; n.inv = !!soft;
      }
    }
    ringAt(x, z, size, dur) { this.fx.ring(x, z, size, dur); const r = (this.fx.rings || []).find((o) => o.t === 0 && o.m.position.x === x && o.m.position.z === z); if (r) r.m.position.y = floorY(x, z) + 0.04; }
    npcStep(n, dt) {
      const a = n.a; a.t += dt; n.slipCd = Math.max(0, (n.slipCd || 0) - dt);
      if (n.onigiri) {
        if (n.ckAway > 0) n.ckAway -= dt;
        if (this.stage === 'onigiri' && (n.mode === 'route' || n.mode === 'cook') && !(n.ckAway > 0)) { if (this.cook(n, dt)) return; }
        else if (n.mode === 'cook') { n.mode = 'route'; this.cookStop(n); }
        if (this.stage !== 'onigiri' && n.busy) this.cookStop(n);
      }
      if (n.shock > 0) {   // startled: a hop backwards, frozen a beat staring at him, then they come for him
        n.shock -= dt; const k = Math.max(0, n.shock - 0.75) / 0.35; a.vx = n.shockV[0] * k; a.vz = n.shockV[1] * k;
        a.x += a.vx * dt; a.z += a.vz * dt; this.collide(a, 0.4); a.f = lerpA(a.f, Math.atan2(this.P.z - a.z, this.P.x - a.x), dt * 8);
        if (n.shock <= 0) { a.shock = 0; a.vx = a.vz = 0; if (!this.P.hidden && !this.P.boxHide) this.startChase(n); else { n.mode = 'search'; n.wait = 2; } }
        return;
      }
      if (a.st === 'act' && a.t >= a.dur) a.st = 'free';   // (a punch or a grab finishes: never left gliding about in a fighting pose)
      if (n.mode === 'chase' && a.st !== 'down' && a.st !== 'getup') { this.chaseStep(n, dt); this.slipCheck(n); return; }   // (after him: a puddle still takes their feet; see slipCheck)
      if (a.st === 'act') { a.vx = a.vz = 0; return; }
      // he ducked into the box while they came to look: they stop short, peer at the box... and wander off
      if (n.mode === 'goto' && this.P.boxHide && Math.hypot(this.P.x - a.x, this.P.z - a.z) < 1.9) { n.mode = 'search'; n.wait = 2.2; n.path = null; a.vx = a.vz = 0; a.f = Math.atan2(this.P.z - a.z, this.P.x - a.x); this.popAt(a, '…箱?', 1.2); return; }
      if (n.hold > 0) { n.hold -= dt; if (!n.pushing) a.vx = a.vz = 0; a.y = floorY(a.x, a.z); if (n.hold <= 0 && n.path) { const e = n.path[n.path.length - 1]; this.goTo(n, e[0], e[1]); } return; }   // wheeling a cart back
      // down on a puddle: slide to a stop, lie there a moment, get up, carry on (and see nothing meanwhile)
      if (a.st === 'down' || a.st === 'getup') {
        a.vx *= 0.9; a.vz *= 0.9; a.x += a.vx * dt; a.z += a.vz * dt; this.collide(a, 0.4);
        if (a.st === 'down' && a.t >= a.dur) { a.st = 'getup'; a.t = 0; a.dur = 1.2; }
        else if (a.st === 'getup' && a.t >= a.dur && n.ko) { n.ko = false; n.mode = 'search'; n.wait = 4; n.path = null; this.popAt(a, '誰だ…殴ったのは!?', 1.6); }
        else if (a.st === 'getup' && a.t >= a.dur) { a.st = 'free'; a.t = 0; a.slipFall = false; }
        return;
      }
      let tx = null, tz = null, sp = n.speed;
      if (n.mode === 'search') {
        n.wait -= dt; a.f += Math.sin(a.t * 1.7) * dt * (n.raid ? 1.0 : 1.8);
        if (n.wait <= 0) { if (n.raid) { n.raid = false; n.looked = false; } n.mode = 'return'; this.goTo(n, n.route[n.i][0], n.route[n.i][1]); }
      } else if (n.mode === 'route' && n.wait > 0) {
        const p = n.route[n.i]; n.wait -= dt; a.f = lerpA(a.f, p[3] + Math.sin(a.t * 0.8) * n.sway, dt * 2.5);
        if (n.wait <= 0) { n.i = (n.i + 1) % n.route.length; this.goTo(n, n.route[n.i][0], n.route[n.i][1]); }
      } else {
        if (!n.path) this.goTo(n, n.route[n.i][0], n.route[n.i][1]);
        const p = n.path[n.pi];
        if (p) { tx = p[0]; tz = p[1]; sp = n.mode === 'goto' ? (n.inv ? 1.9 : 2.5) : n.mode === 'raid' ? 2.3 : n.mode === 'return' ? 1.4 : n.speed; if (Math.hypot(tx - a.x, tz - a.z) < 0.25) { n.pi++; if (!n.path[n.pi]) tx = null; } }
        if (!n.path[n.pi]) { // arrived
          n.path = null;
          if (n.mode === 'goto') { n.mode = 'search'; n.wait = 4.2; if (n.noiseAt) a.f = Math.atan2(n.noiseAt[1] - a.z, n.noiseAt[0] - a.x); }
          else if (n.mode === 'raid') { n.mode = 'search'; n.wait = 3.5; a.f = Math.atan2((POOL.z0 + POOL.z1) / 2 - a.z, (POOL.x0 + POOL.x1) / 2 - a.x); n.looked = true; this.popAt(a, ['どこ行った…?', '誰かいるのか?'][this.raid && this.raid.k++ % 2 || 0], 1.6); }
          else { n.mode = 'route'; n.wait = n.route[n.i][2] || 0.01; if (n.onigiri && n.i === 0) this.chefMakes(); }
        }
      }
      if (tx !== null) { let dx = tx - a.x, dz = tz - a.z, d = Math.hypot(dx, dz) || 1; dx /= d; dz /= d;
        const P = this.P;   // a box on the floor in the way: they put their shoulder to it and shove it along (sweating); stuck fast, they turn back
        if (!P.boxHide) { n.pushing2 = false; n.tug = 0; n.clr = null; }
        n.clrCd = Math.max(0, (n.clrCd || 0) - dt);
        // the box sat in their way: shove it off to the side of their route (or, no room either side, drag it back
        // towards themselves), then carry on along their way. They don't push it any further than that
        if (P.boxHide) { const bx = P.x - a.x, bz = P.z - a.z, bd = Math.hypot(bx, bz), PS = 0.6, st = 0.85 + 0.42;
          if (!n.clr && !(n.tug > 0) && !n.clrCd && bd < 1.5 && (bx * dx + bz * dz) / (bd || 1) > 0.3) {
            // which side? the one with room for the box, that leaves it furthest from the way they're going
            const pts = [[a.x, a.z]].concat((n.path || []).slice(n.pi, n.pi + 4)), segD = (x, z) => { let m = 1e9;
              for (let k = 0; k + 1 < pts.length; k++) { const [x0, z0] = pts[k], [x1, z1] = pts[k + 1], ex = x1 - x0, ez = z1 - z0, l2 = ex * ex + ez * ez || 1e-6, t = clamp(((x - x0) * ex + (z - z0) * ez) / l2, 0, 1); m = Math.min(m, Math.hypot(x - x0 - ex * t, z - z0 - ez * t)); }
              return pts.length > 1 ? m : Math.hypot(x - a.x, z - a.z); };
            let best = null;
            for (const sd of [1, -1]) { const ux = -dz * sd, uz = dx * sd, tx = P.x + ux * 1.6, tz = P.z + uz * 1.6; let ok = true;
              for (const f of [0.5, 1]) { const q = { x: P.x + ux * 1.6 * f, z: P.z + uz * 1.6 * f, boxProbe: true }; this.collide(q, P.r); if (Math.hypot(q.x - P.x - ux * 1.6 * f, q.z - P.z - uz * 1.6 * f) > 0.06) ok = false; }
              const sc = segD(tx, tz); if (ok && (!best || sc > best.sc)) best = { ux, uz, sc }; }
            if (best) { n.clr = { ux: best.ux, uz: best.uz, left: 1.6, t: 0, on: false, stuck: 0 }; this.popAt(a, ['邪魔だな…', 'なんだこの箱…', 'よいしょ…'][(this.t * 3 | 0) % 3], 1.2); }
            else { n.tug = 1.3; n.tugU = [dx, dz]; this.popAt(a, 'ぐぬぬ…!', 1.0); }
          }
          if (n.tug > 0) {   // no room to shove it aside: they grab it and drag it back towards themselves, walking backwards, then go round
            const [ux, uz] = n.tugU || [dx, dz]; n.pushing2 = true; this.boxYaw = Math.atan2(uz, ux);
            n.tug -= dt; const q = { x: P.x - ux * PS * dt, z: P.z - uz * PS * dt, boxProbe: true }; this.collide(q, P.r); P.x = q.x; P.z = q.z;
            a.x += (P.x - ux * st - a.x) * Math.min(1, dt * 8); a.z += (P.z - uz * st - a.z) * Math.min(1, dt * 8); this.collide(a, 0.4); a.vx = -ux * PS; a.vz = -uz * PS; a.f = lerpA(a.f, Math.atan2(uz, ux), dt * 6);
            if (n.tug <= 0) { n.pushing2 = false; n.clrCd = 2.5; if (n.path) { const e = n.path[n.path.length - 1]; this.goTo(n, e[0], e[1]); } this.popAt(a, 'ふぅ…', 1.0); }
            return;
          }
          if (n.clr) { const C = n.clr; C.t += dt;
            const gx = P.x - C.ux * st, gz = P.z - C.uz * st;
            if (!C.on) {   // step round to the side of it first
              const ex = gx - a.x, ez = gz - a.z, ed = Math.hypot(ex, ez);
              if (ed > 0.12 && C.t < 2.5) { a.vx = ex / ed * 1.1; a.vz = ez / ed * 1.1; a.x += a.vx * dt; a.z += a.vz * dt; this.collide(a, 0.4); a.f = lerpA(a.f, Math.atan2(P.z - a.z, P.x - a.x), dt * 6); return; }
              C.on = true; }
            n.pushing2 = true; this.boxYaw = Math.atan2(C.uz, C.ux);
            const q = { x: P.x + C.ux * PS * dt, z: P.z + C.uz * PS * dt, boxProbe: true }; this.collide(q, P.r);
            const mv = Math.hypot(q.x - P.x, q.z - P.z);
            if (mv > PS * 0.4 * dt && mv < PS * 3 * dt) { P.x = q.x; P.z = q.z; C.left -= mv; C.stuck = 0; } else C.stuck += dt;
            a.x += (P.x - C.ux * st - a.x) * Math.min(1, dt * 8); a.z += (P.z - C.uz * st - a.z) * Math.min(1, dt * 8); this.collide(a, 0.4); a.vx = C.ux * PS; a.vz = C.uz * PS; a.f = lerpA(a.f, Math.atan2(C.uz, C.ux), dt * 6);
            if ((n.sweatT = (n.sweatT || 0) - dt) <= 0) { n.sweatT = 1.4; this.popAt(a, ['ふんっ…!', '重っ…!'][(this.t * 2 | 0) % 2], 1.0); }
            if (C.left <= 0 || C.stuck > 0.6 || C.t > 7) {   // out of the way (or as far as it'll go): back to what they were doing
              n.clr = null; n.pushing2 = false; n.clrCd = 3; if (n.path) { const e = n.path[n.path.length - 1]; this.goTo(n, e[0], e[1]); } }
            return;
          }
          n.pushing2 = false; }
        a.vx = dx * sp; a.vz = dz * sp; a.f = lerpA(a.f, Math.atan2(dz, dx), dt * 7); }
      else { a.vx *= 0.8; a.vz *= 0.8; }
      const ox = a.x, oz = a.z; a.x += a.vx * dt; a.z += a.vz * dt;
      this.collide(a, 0.4); a.y = floorY(a.x, a.z);
      if (this.slipCheck(n)) return;
      // a colleague out cold: anyone who sees them goes over; whoever gets there shakes them awake
      if ((n.kChk = (n.kChk || 0) - dt) <= 0) { n.kChk = 0.3;
        for (const m of this.npcs) if (m !== n && m.ko && m.a.st === 'down' && Math.abs(m.a.y - a.y) < 1) {
          const d = Math.hypot(m.a.x - a.x, m.a.z - a.z);
          if (d < 1.5) { m.a.t = m.a.dur; n.mode = 'search'; n.wait = 3; n.path = null; this.popAt(a, ['おい!起きろ!', '大丈夫か!?', 'しっかりしろ!'][(this.t * 3 | 0) % 3], 1.5); break; }
          if (n.mode !== 'goto' && d < 9 && this.sees(n, m.a.x, m.a.z, 9)) { this.goTo(n, m.a.x, m.a.z); n.mode = 'goto'; n.inv = false; n.noiseAt = [m.a.x, m.a.z]; this.popAt(a, '!?', 1.2); break; }
        } }
      if (tx !== null) { n.stk = Math.hypot(a.x - ox, a.z - oz) < sp * dt * 0.2 ? (n.stk || 0) + dt : 0; if (n.stk > 3) { n.stk = 0; this.unstick(n); }
        n.stuckT = Math.hypot(a.x - ox, a.z - oz) < sp * dt * 0.3 ? (n.stuckT || 0) + dt : 0;
        // walking into a colleague: if they're standing on the very spot, this is close enough; otherwise step round them
        if (n.stuckT > 0.45) { const o = this.npcs.find((m) => m !== n && Math.hypot(m.a.x - a.x, m.a.z - a.z) < 1.05);
          if (o) { const e = n.path && n.path[n.path.length - 1];
            if (e && Math.hypot(e[0] - o.a.x, e[1] - o.a.z) < 1.2 && Math.hypot(e[0] - a.x, e[1] - a.z) < 2.2) { n.path = [[a.x, a.z]]; n.pi = 0; }
            else { const dx = tx - a.x, dz = tz - a.z, d = Math.hypot(dx, dz) || 1; a.x += -dz / d * 0.4; a.z += dx / d * 0.4; this.collide(a, 0.4); }
            n.stuckT = 0; } }
        // blocked by a cart someone moved: "tsk", and they wheel it back where it belongs
        if (n.stuckT > 0.5 || ((n.mode === 'route' || n.mode === 'return') && (n.cChk = (n.cChk || 0) - dt) <= 0 && (n.cChk = 0.25))) { const c = this.carts.find((cc) => !cc.ret && cc !== this.P.cart && Math.hypot(cc.x - a.x, cc.z - a.z) < (n.stuckT > 0.5 ? 1.9 : 1.45) && Math.hypot(cc.x - cc.hx, cc.z - cc.hz) > 0.6);
          if (c) { c.ret = { t: 0, x0: c.x, z0: c.z, f0: c.f, n }; n.hold = 99; n.stuckT = 0; this.popAt(a, ['チッ…誰だ、ここに置いたの', 'これはあっちだろ', 'まったく…'][(this.t * 7 | 0) % 3], 1.6); return; } }
        if (n.stuckT > 0.8 && this.P.boxHide && Math.hypot(this.P.x - a.x, this.P.z - a.z) < 1.8 && n.mode === 'route') { n.i = (n.i + n.route.length - 1) % n.route.length; this.goTo(n, n.route[n.i][0], n.route[n.i][1]); this.popAt(a, '…?', 1.0); }
        else if (n.stuckT > 0.8 && n.path) { const e = n.path[n.path.length - 1]; this.goTo(n, e[0], e[1]); } }
    }
    // push a circle out of every wall and blocker it overlaps (a few passes, so corners can't squeeze it through)
    collide(p, r) {
      let hit = false;
      for (let pass = 0; pass < 3; pass++) {
        let moved = false;
        for (const w of this.walls) {
          if (w.box && (p === this.P || p.boxProbe)) continue;   // (his own box: never collide the box with itself)
          const cx = clamp(p.x, w.x0, w.x1), cz = clamp(p.z, w.z0, w.z1), dx = p.x - cx, dz = p.z - cz, d = Math.hypot(dx, dz);
          if (d >= r) continue;
          if (d > 1e-6) { p.x = cx + dx / d * r; p.z = cz + dz / d * r; }
          else { const o = [[w.x0 - r - p.x, 0], [w.x1 + r - p.x, 0], [0, w.z0 - r - p.z], [0, w.z1 + r - p.z]].sort((A, B) => Math.abs(A[0] + A[1]) - Math.abs(B[0] + B[1]))[0]; p.x += o[0]; p.z += o[1]; }
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
      if (this.sf) { if (this.timers && this.timers.length) { const due = []; this.timers = this.timers.filter((q) => { q.t -= dt; if (q.t <= 0) { due.push(q); return false; } return true; }); for (const q of due) if (this.scene) q.fn(); } this.sfStep(dt); return; }
      if (this.timers && this.timers.length) { const due = []; this.timers = this.timers.filter((q) => { q.t -= dt; if (q.t <= 0) { due.push(q); return false; } return true; }); for (const q of due) if (this.scene) q.fn(); }   // (run after: a timer may set new ones)
      const P = this.P, c = this.ctrl;
      P.t += dt; P.cd = Math.max(0, P.cd - dt);
      let mx = c.mx, mz = c.mz; const mag = Math.hypot(mx, mz); if (mag > 1) { mx /= mag; mz /= mag; }
      if (this.asleep) { this.npcsOnly(dt); return; }
      const wet = inPool(P.x, P.z), iPress = this.iPress; this.iPress = false; const px0 = P.x, pz0 = P.z;
      // in a toilet stall, door shut: nobody sees him. Any move and he comes out
      if (P.stallHide !== undefined) { P.vx = P.vz = 0; P.hideT = (P.hideT || 0) + dt; P.stam = Math.min(1, P.stam + dt * 0.3); if (P.tired && P.stam > 0.45) P.tired = false;
        if ((mag > 0.5 || iPress) && P.hideT > 0.3) this.stallOut(); else { this.npcsOnly(dt); return; } }
      if (iPress && !this.hideCd && P.st === 'free' && !P.held && !P.cart && roomAt(P.x, P.z) === 'toilet') {
        const k = LY.stalls.findIndex((q) => Math.abs(P.z - q.z) < 1.0 && P.x < q.x + 2.6 && P.x > q.x - 0.5);
        if (k >= 0) { const q = LY.stalls[k], D = this.stallDoors && this.stallDoors[k]; this.markWitness(); P.stallHide = k; P.inStall = true; P.hideT = 0; P.x = q.x + 0.2; P.z = q.z; P.f = 0; P.vx = P.vz = 0; P.tip = 0; if (D) D.rotation.y = 0; this.dropShorts(true);
          if (!this.saidStallHide) { this.saidStallHide = true; this.think('Occupied! ...nobody checks an occupied stall.', 2.2); } return; } }
      // hidden in a cart: still as a heap of towels. Any move (or I) and he climbs out
      if (P.hidden) {
        P.vx = P.vz = 0;
        if (mag > 0.5 && P.hideT > 0.25) { const hc = P.hidden; P.hidden = null; this.view.root.visible = true; hc.off = false; this.cartBox(hc);
          // out the side he pushes towards (the nearest free side to it, if that one's against a wall)
          // (just clear of the cart's edge, in the same room, never through a wall; no free side: he stays put)
          const a0 = Math.atan2(mz, mx), room = roomAt(hc.x, hc.z), ca = Math.cos(hc.f), sa = Math.sin(hc.f); let spot = null;
          for (const da of [0, 0.5, -0.5, 1.0, -1.0, 1.57, -1.57, 2.2, -2.2, 3.14]) {
            const dx = Math.cos(a0 + da), dz = Math.sin(a0 + da), ext = Math.abs(dx * ca + dz * sa) * 0.66 + Math.abs(-dx * sa + dz * ca) * 0.46;
            const q = { x: hc.x + dx * (ext + P.r + 0.05), z: hc.z + dz * (ext + P.r + 0.05) }, ox = q.x, oz = q.z; this.collide(q, P.r);
            if (Math.hypot(q.x - ox, q.z - oz) < 0.45 && roomAt(q.x, q.z) === room && this.clear(hc.x, hc.z, q.x, q.z)) { spot = q; break; }
          }
          if (!spot) { P.hidden = hc; this.view.root.visible = false; hc.off = true; this.cartBox(hc); this.cartStep(dt); this.npcsOnly(dt); return; }
          P.x = spot.x; P.z = spot.z; P.f = a0; this.noGuard = true;
          // out with I held: straight onto his toes, silent. And a pair of towel-cart shorts over his shoulder (falls off after a few steps)
          P.tip = this.keys.KeyI && !P.tired ? 1 : 0; this.hideCd = 0.6; this.shoulderShorts(); }
        else { P.hideT = (P.hideT || 0) + dt; P.stam = Math.min(1, P.stam + dt * 0.3); if (P.tired && P.stam > 0.45) P.tired = false; this.cartStep(dt); this.grace = Math.max(this.grace, 0); this.npcsOnly(dt); return; }
      }
      this.hideCd = Math.max(0, (this.hideCd || 0) - dt); this.hitCd = Math.max(0, (this.hitCd || 0) - dt);
      if (this.shove) { this.shove.t -= dt; P.x += this.shove.x * dt; P.z += this.shove.z * dt; this.collide(P, P.r); if (this.shove.t <= 0) this.shove = null; }
      if (this.hits && !this.chasing()) { this.calmT = (this.calmT || 0) + dt; if (this.calmT > 10) { this.hits = Math.max(0, this.hits - 1); this.calmT = 0; } }
      // holding I and walking right into a cart: in he goes, too
      let walkIn = false;
      if (!iPress && this.keys.KeyI && mag > 0.5 && !this.hideCd && P.st === 'free' && !wet && !P.held && !P.cart)
        for (const cc of this.carts) { const w = cc.w, ex = clamp(P.x, w.x0, w.x1), ez = clamp(P.z, w.z0, w.z1), d = Math.hypot(P.x - ex, P.z - ez) - P.r;
          if (d < 0.12 && !cc.ret && ((ex - P.x) * mx + (ez - P.z) * mz) / (Math.hypot(ex - P.x, ez - P.z) || 1) > 0.5) { walkIn = true; break; } }
      if ((iPress || walkIn) && !this.hideCd && P.st === 'free' && !wet && !P.held) {   // I next to a cart (walking or not): climb in
        let near = null, nd = 0.3; for (const cc of this.carts) { const w = cc.w, d = Math.hypot(P.x - clamp(P.x, w.x0, w.x1), P.z - clamp(P.z, w.z0, w.z1)) - P.r; if (d < nd && !cc.ret && this.clear(P.x, P.z, cc.x, cc.z) && !this.inWall(cc.x, cc.z, cc.w)) { nd = d; near = cc; } }   // (right up against it; never one through a wall, nor one jammed into one)
        if (P.cart && iPress && this.clear(P.x, P.z, P.cart.x, P.cart.z) && !this.inWall(P.cart.x, P.cart.z, P.cart.w)) near = P.cart;   // (the one he's pushing: straight in)
        if (near) { this.markWitness(); if (P.cart) P.cart = null; this.noGuard = true; P.hidden = near; P.hideT = 0; near.off = true; this.cartBox(near); P.x = near.x; P.z = near.z; P.vx = P.vz = 0; this.view.root.visible = false; P.tip = 0; this.dropShorts(true);
          if (!this.saidCart) { this.saidCart = true; this.think('...just a cart of towels. Nothing to see.', 2.0); } return; }
      }
      // I: TIPTOE. Silent, slow, and tiring: about six seconds on his toes, then the heels come down with a thud
      const tipOn = !!this.keys.KeyI && P.st === 'free' && !wet && !P.tired && !P.cart;
      // in the bath, I: duck right under (just bubbles on the water)
      P.sub = wet && !!this.keys.KeyI && P.st === 'free' && !P.tired;
      if (P.sub) { P.stam -= dt / 8; if (P.stam <= 0) { P.stam = 0; P.tired = true; P.sub = false; this.popAt({ x: P.x, z: P.z, y: P.y + 0.6 }, 'ぷはっ!', 1.2); this.fx.water && this.fx.water(P.x, P.z, 3, POOL.water); this.noise(P.x, P.z, 9, '!?'); this.think('*gasp* ...can\'t hold my breath that long!', 1.8); } }
      if (P.sub) { this.bubT = (this.bubT || 0) - dt; if (this.bubT <= 0) { this.bubT = 0.45; this.fx.water && this.fx.water(P.x + (Math.random() - 0.5) * 0.4, P.z + (Math.random() - 0.5) * 0.4, 0.15, POOL.water); }
        if (!this.saidSub) { this.saidSub = true; this.think('Blub... blub...', 1.4); } }
      P.tip += ((tipOn ? 1 : 0) - P.tip) * Math.min(1, dt * 10);
      if (P.sub) { /* holding his breath (above) */ } else if (tipOn && Math.hypot(P.vx, P.vz) <= 0.4) { P.stam = Math.min(1, P.stam + dt * 0.3); if (P.tired && P.stam > 0.45) P.tired = false; }   // crouched still: he gets his breath back
      else if (tipOn) { P.stam -= dt / 6.4;
 if (P.stam <= 0) { P.stam = 0; P.tired = true; this.heelsDown(); } }
      else { P.stam = Math.min(1, P.stam + dt * 0.3); if (P.tired && P.stam > 0.45) P.tired = false; }
      // L + direction: CHARGE (as everywhere in the game); not while wading
      if (!c.dash.held) this.lRel = true;   // (one charge per press: let go of L before the next, no endless re-charging)
      if (P.st === 'free' && c.dash.held && this.lRel !== false && mag > 0.3 && P.cd <= 0 && !wet && !P.cart) { this.lRel = false; P.st = 'wind'; P.t = 0; P.dur = 0.3; P.cdir = Math.atan2(mz, mx); P.f = P.cdir; }   // a wind-up first: he braces, then launches
      let spd = 0;
      if (P.st === 'free') spd = wet ? (P.sub ? 1.2 : 2.0) : P.cart ? 2.6 : P.tip > 0.5 ? (this.wearing ? 1.5 : 1.7) : (this.wearing ? 3.0 : 3.4);
      P.chT = P.st === 'charge' ? (P.chT || 0) + dt : 0; if (P.chT > 0.95) { P.st = 'free'; P.t = 0; P.cd = 0.5; P.chT = 0; }   // (a charge can never run on)
      if (P.st === 'charge') { mx = Math.cos(P.cdir); mz = Math.sin(P.cdir); spd = 7.2; P.run = (P.run || 0) + Math.hypot(P.vx, P.vz) * dt; if (!c.dash.held && P.t > 0.25) P.t = P.dur; if (P.t > 0.85) P.t = P.dur + 0.01; }   // (never longer than 0.85 s)
      if (P.st === 'wind' && mag > 0.3) { P.cdir = lerpA(P.cdir, Math.atan2(mz, mx), dt * 8); P.f = P.cdir; }
      const power = P.st === 'charge' && P.run > 1.0;   // it needs a run-up: from right next to something he just bumps it
      const dir = P.st === 'charge' || mag > 0.3;
      P.vx += ((dir ? mx : 0) * spd - P.vx) * Math.min(1, dt * (P.st === 'charge' ? 14 : 10)); P.vz += ((dir ? mz : 0) * spd - P.vz) * Math.min(1, dt * (P.st === 'charge' ? 14 : 10));
      if (P.st === 'slip' || P.st === 'busy' || P.st === 'wear' || P.st === 'wind') { P.vx *= 0.85; P.vz *= 0.85; }
      if (mag > 0.3 && P.st === 'free') P.f = lerpA(P.f, Math.atan2(mz, mx), dt * (P.cart ? 4 : 12));
      P.x += P.vx * dt; P.z += P.vz * dt;
      if (!P.hidden && !P.boxHide) for (const n of this.npcs) {   // bodies: he bumps into people (a charge bowls them over: see below)
        const a = n.a; if (a.st === 'down' || Math.abs(a.y - P.y) > 1) continue;
        const dx = P.x - a.x, dz = P.z - a.z, d = Math.hypot(dx, dz), R2 = P.r * 0.8 + 0.4;
        if (d < R2 && d > 1e-4 && !(P.st === 'charge' && n.mode !== 'chase' && n.alarm < 1 && a.st === 'free')) { P.x = a.x + dx / d * R2; P.z = a.z + dz / d * R2; if (P.st === 'charge') { P.t = P.dur + 0.01; P.vx *= -0.2; P.vz *= -0.2; } }
      }
      // the cracked wall gives way to a charge
      const CK = LY.crack;
      if (power && !this.crackDone && P.z < CK.z1 + P.r + 0.25 && P.z > CK.z0 - 0.2 && P.x > CK.x0 && P.x < CK.x1) this.smashCrack();
      if (power) for (const n of this.npcs) {   // a charge bowls over anyone he hits who hadn't made him out yet (not someone already after him)
        if (n.a.st !== 'free' || n.alarm >= 1 || n.mode === 'chase' || Math.abs(n.a.y - P.y) > 1) continue;
        const dx = n.a.x - P.x, dz = n.a.z - P.z, d = Math.hypot(dx, dz);
        if (d < P.r + 0.55 && (dx * Math.cos(P.f) + dz * Math.sin(P.f)) / (d || 1) > 0.2) this.knockOut(n, Math.cos(P.f), Math.sin(P.f), ['ドーン!', 'ドスン!'][(this.t * 3 | 0) % 2], 4.5);
      }
      if (this.vend) { const V = this.vend; V.cd = Math.max(0, V.cd - dt);
        if (power && !V.broke && !V.cd && P.y < 1 && P.x > V.x0 - P.r - 0.2 && P.z > V.z0 - 0.3 && P.z < V.z1 + 0.3) { V.cd = 0.6; this.hitVend(); P.t = P.dur + 0.01; P.vx *= -0.3; P.vz *= -0.3; } }
      P.brkCd = Math.max(0, (P.brkCd || 0) - dt); this.runupCd = Math.max(0, (this.runupCd || 0) - dt);
      if (P.st === 'charge' && !power && this.breakables && !this.runupCd && this.breakables.some((B) => !B.done && Math.abs((B.s.f ? UP : 0) - P.y) < 1.2 && Math.hypot(P.x - clamp(P.x, B.s.x0, B.s.x1), P.z - clamp(P.z, B.s.z0, B.s.z1)) < P.r + 0.15)) {
        this.runupCd = 8; this.think('Too close... I need a RUN-UP to smash through that!', 2); }   // (from right up against it he only bumps it)
      if (power && this.breakables && !P.brkCd) {   // one piece at a time: the nearest one he hits
        let best = null, bd = P.r + 0.15;
        for (const B of this.breakables) {
          if (B.done) continue; const sd = B.s; if (Math.abs((sd.f ? UP : 0) - P.y) > 1.2) continue;
          // his own locker (the mission one) never shatters: it only dents and bursts open, three charges (hitLocker)
          if (sd.k === 'lockers' && Math.abs((sd.z0 + sd.z1) / 2 - (LY.locker.bz0 + 0.35)) < 0.6 && sd.x1 > LY.locker.bx0 - 0.1 && sd.x0 < LY.locker.bx0 + 8.1) continue;   // (the whole bank)
          const cx = clamp(P.x, sd.x0, sd.x1), cz = clamp(P.z, sd.z0, sd.z1), d = Math.hypot(P.x - cx, P.z - cz); if (d < bd) { bd = d; best = B; }
        }
        if (best) { this.breakThing(best); P.brkCd = 0.3; }
      }
      if (power) for (const cc of this.carts) {
        if (cc === P.cart || cc === P.hidden || Math.hypot(cc.x - P.x, cc.z - P.z) > P.r + 0.75 || (Math.abs(cc.vx) + Math.abs(cc.vz)) > 1) continue;
        cc.vx = Math.cos(P.cdir) * 6; cc.vz = Math.sin(P.cdir) * 6; cc.spin = (Math.random() - 0.5) * 4; this.noise(cc.x, cc.z, 8, '?!');
        if (this.g.audio && this.g.audio.thump) this.g.audio.thump(5);
      }
      if (power) for (const b of this.buckets) {
        if (b.state !== 'floor' || Math.abs(b.m.position.y - P.y) > 1.2 || Math.hypot(b.m.position.x - P.x, b.m.position.z - P.z) > P.r + 0.35) continue;
        const dx = b.m.position.x - P.x, dz = b.m.position.z - P.z, dl = Math.hypot(dx, dz) || 1, a = Math.atan2(0.5 * dz / dl + Math.sin(P.cdir), 0.5 * dx / dl + Math.cos(P.cdir));
        const L = clamp(this.reach(b.m.position.x, b.m.position.z, a, 6) - 0.5, 0.8, 5.5);
        b.state = 'fly'; b.t = 0; b.sx = b.m.position.x; b.sz = b.m.position.z; b.sy = b.m.position.y; b.tx = b.sx + Math.cos(a) * L; b.tz = b.sz + Math.sin(a) * L;
        b.wet = inPool(b.tx, b.tz); b.ty = b.wet ? POOL.water - 0.12 : floorY(b.tx, b.tz); b.dur = 0.3 + L * 0.05;
      }
      this.cartStep(dt);
      const hit = this.collide(P, P.r);
      if (this.noGuard) this.noGuard = false; else if ((P.x !== px0 || P.z !== pz0) && Math.hypot(P.x - px0, P.z - pz0) < 2.5 && this.segInWall(px0, pz0, P.x, P.z)) { P.x = px0; P.z = pz0; }   // (never squeezed through a wall: a shove, a punch, a crowd pushing)
      // how high he stands: in the bath up to his chest, the stairs, the floor above
      const ty = wet ? (P.sub ? -1.6 : P.z > -3.4 && P.x > 0 && P.x < 2 ? -0.3 : -0.62) : floorY(P.x, P.z);
      P.y = Math.abs(ty - P.y) > 1 && !wet ? ty : P.y + (ty - P.y) * Math.min(1, dt * (wet || P.y < -0.05 ? 6 : 20));
      if (!wet && !this.outOfBath && P.y > -0.2) this.leaveBath();
      // splashing: wading through the bath, or stepping through a puddle
      const moving = Math.hypot(P.vx, P.vz) > 0.6, inPud = this.puddles.some((q) => Math.abs(floorY(q.x, q.z) - P.y) < 1 && ((P.x - q.x) / q.rx) ** 2 + ((P.z - q.z) / q.rz) ** 2 < 1);
      if (moving && (wet || inPud)) { this.splT = (this.splT || 0) - dt; if (this.splT <= 0) { this.splT = wet ? 0.24 : 0.32;
        const s = this.view.s, sd = (this.stepSd = -(this.stepSd || 1)); this.fx.water && this.fx.water(P.x + Math.cos(P.f + sd * 1.2) * 0.45 * s, P.z + Math.sin(P.f + sd * 1.2) * 0.45 * s, wet ? 0.8 : 0.35, wet ? POOL.water : P.y);
        if (!wet && !SAFE[roomAt(P.x, P.z)]) this.noise(P.x, P.z, P.tip > 0.5 ? 2.4 : 4.5, '?', true); } }
      else this.splT = 0;
      if (wet !== this.wasWet) { if (this.wasWet !== undefined) this.fx.water && this.fx.water(P.x, P.z, 1.6, POOL.water); this.wasWet = wet; }
      if (P.st === 'charge') {
        if (power && this.stage === 'smash' && !this.chasing() && Math.hypot(P.x - this.locker.x, P.z - this.locker.z) < 1.25) { this.hitLocker(); P.st = 'busy'; P.t = 0; P.dur = 0.5; }
        else if (hit) { P.st = 'busy'; P.t = 0; P.dur = 0.35; P.vx *= -0.3; P.vz *= -0.3; this.fx.dust && this.fx.dust(P.x, 0.5 + P.y, P.z, 5, 0.3, 0.5, 0.3); if (!SAFE[roomAt(P.x, P.z)]) this.noise(P.x, P.z, 5, '?'); }
      }
      if (P.st !== 'free' && P.t > P.dur) { const was = P.st; P.st = was === 'wind' ? 'charge' : 'free'; P.t = 0; if (was === 'wind') { P.dur = 0.85; P.run = 0; } if (was === 'charge') P.cd = 0.5; if (was === 'wear') this.putOnBox(); }
      // puddles: walking over them is fine; RUNNING (the charge) over one, you slip
      if (P.st === 'charge') for (const q of this.puddles) if (((P.x - q.x) / q.rx) ** 2 + ((P.z - q.z) / q.rz) ** 2 < 1) {
        P.st = 'slip'; P.t = 0; P.dur = 1.3; P.fall = Math.atan2(P.vz, P.vx); P.vx *= 0.6; P.vz *= 0.6;
        this.think(['WHOA—!', 'Waaah!', 'Slippery!!'][(this.t * 3 | 0) % 3], 1.2); this.fx.water && this.fx.water(P.x, P.z, 5);
        if (!SAFE[roomAt(P.x, P.z)]) this.noise(P.x, P.z, 7, '?!');
        break;
      }
      // the room you're in: checkpoints at each doorway
      const room = roomAt(P.x, P.z);
      if (room !== this.room) {
        const from = this.room; this.room = room; const cp0 = this.cp; this.later(0, () => { if (this.chasing()) this.cp = cp0; });
        if (room === 'lock') { this.cp = from === 'corr' ? CP.lockS : CP.lockN; if (!this.saidOut) { this.saidOut = true; this.think('No tattoos allowed in here... and mine says INVINCIBLE. Nobody can see me. (Hold I to tiptoe)', 3.6); } }
        if (room === 'laundry' || (room === 'corr' && from === 'laundry')) this.cp = CP.laundry;
        if (room === 'laundry' && this.stage === 'towel' && !this.saidLaundry) { this.saidLaundry = true; this.think('The towels are on the shelf at the far end... past all these machines.', 3.0); }
        if (room === 'corr' && from !== 'laundry') { this.cp = CP.corr; if (this.stage === 'storage' && !this.saidCorr) { this.saidCorr = true; this.think('The back corridor... staff use it to get upstairs, I bet.', 2.6); } }
        if (room === 'stair' || (room === 'up' && from === 'stair')) this.cp = CP.stair;
        if (room === 'up' && from === 'stair' && !this.saidUp) { this.saidUp = true; this.think('The lounge... and the front desk is past it. The storage must be behind the desk.', 3.4); }
        if (room === 'store') this.cp = CP.store;
        if (SAFE[room]) this.cp = { x: P.x, z: P.z, f: P.f };
        if (room === 'kitchen' || (room === 'corr' && from === 'kitchen')) this.cp = CP.kitchen;
        if (room === 'toilet' || (room === 'lock' && from === 'toilet')) this.cp = CP.toilet;
        if (room === 'kitchen' && this.stage === 'kitchen') this.hungry();
        if (room === 'store' && this.stage === 'storage') { this.stage = 'box'; this.spBox.visible = true; this.think('A cardboard box... it\'ll have to do!', 2.8); this.objective('Put on the BOX (K next to it)'); }
      }
      if (!this.crackDone && !this.saidCrack && room === 'corr' && P.x > 4 && this.stage === 'storage') {   // (only once he needs to get upstairs: after the towels) this.saidCrack = true; this.spCrack.visible = true;
        this.think('The stairs! ...buried under a heap of delivery boxes. One good charge (hold L) should clear them.', 3.4); }
      // fire exit
      if (P.x < EXIT.x + 0.4 && P.z < EXIT.z1 && P.z > EXIT.z0 && !this.saidChain) { this.saidChain = true; this.think('The fire exit... chained shut?!', 2.0); }
      const En = LY.entrance;
      if (this.stage === 'exit' && !this.chasing() && P.z < En.z + 1.9 && P.x > En.x0 - 0.2 && P.x < En.x1 + 0.2 && P.y > UP - 0.5) this.frontDoor();
      const BD = LY.backdoor;
      if (this.stage === 'escape' && P.x < BD.x - 0.3 && P.z < BD.z1 && P.z > BD.z0) { this.win(); return; }
      // in the box, hold I standing still: he squats right down inside it. Just a box
      P.boxHide = this.wearing && !!this.keys.KeyI && mag < 0.3 && P.st === 'free' && !wet && !(this.noDuck > 0); this.noDuck = Math.max(0, (this.noDuck || 0) - dt);
      if (!this.boxW) { this.boxW = { x0: 1e4, x1: 1e4, z0: 1e4, z1: 1e4, tall: false, box: true }; this.walls.push(this.boxW); }
      if (P.boxHide && !this.wasBoxHide) this.markWitness();
      if (!P.boxHide && this.wasBoxHide) for (const n of this.npcs) if ((n.pushing2 || (n.mode !== 'chase' && !n.pullOut && n.a.st === 'free' && !n.busy)) && !n.ko && Math.abs(n.a.y - P.y) < 1.2 && Math.hypot(n.a.x - P.x, n.a.z - P.z) < (n.pushing2 ? 2.2 : 2.8)) {   // (anyone close who wasn't expecting a box to stand up)   // the box they were shoving stands up: they leap back
        const d = Math.hypot(n.a.x - P.x, n.a.z - P.z) || 1; n.shock = 1.1; n.a.shock = 1; n.shockV = [(n.a.x - P.x) / d * 2.6, (n.a.z - P.z) / d * 2.6];
        n.pushing2 = false; n.tug = 0; n.path = null; n.a.push = false; this.popAt(n.a, ['うわぁっ!?', 'ひぃっ!?', 'えっ!?'][(this.t * 3 | 0) % 3], 1.1, true); }
      this.wasBoxHide = P.boxHide;
      if (P.boxHide) { const W = this.boxW; W.x0 = P.x - 0.85; W.x1 = P.x + 0.85; W.z0 = P.z - 0.85; W.z1 = P.z + 0.85; }   /* (flaps and all) */ else this.boxW.x0 = this.boxW.x1 = this.boxW.z0 = this.boxW.z1 = 1e4;
      this.ratStep(dt);
      if (this.stage === 'escape') for (const t of this.traps) if (t.armed && Math.hypot(t.x - P.x, t.z - P.z) < 0.5 && (P.st === 'free' || P.st === 'charge')) {
        t.armed = false; if (t.mesh) t.mesh.rotation.z = 0.5; P.st = 'busy'; P.t = 0; P.dur = 1.2; P.vx = P.vz = 0;
        this.think(['SNAP! OW OW OW!!', 'YEOWCH! A mousetrap!', '...my toe!!'][(this.t * 3 | 0) % 3], 1.6); this.noise(P.x, P.z, 9, '?!'); this.flash = 0.4;
        if (this.g.audio && this.g.audio.thump) this.g.audio.thump(6);
      }
      // J: a slap. Rats go flying; things get knocked about; hitting a person is NOT allowed
      if (c.push.pressed && P.st === 'free' && !P.held && !P.cart) this.slap();
      else if (c.push.pressed && P.st === 'free' && P.held && P.held.kind === 'can') this.drink();
      // K: use (locker, wash bucket, pick up / throw, put on the box)
      // (holding something: tap K to throw it, hold K to smash it down at your feet)
      if (c.grab.pressed && P.st === 'free') { if (P.held) this.kArm = true; else this.use(); }
      if (this.kArm) { if (!P.held || P.st !== 'free') this.kArm = false; else if (c.grab.held && c.grab.t > 0.32) { this.kArm = false; this.smashHeld(); } else if (!c.grab.held) { this.kArm = false; this.use(); } }
      // a charge is loud: heavy running footsteps carry round the room
      // footsteps: walking is heard by anyone close by (they come and look), the charge further; tiptoe is silent
      const proom = roomAt(P.x, P.z), loud = (SAFE[proom] ? 0 : P.st === 'charge' ? 5 : P.st === 'free' && P.tip < 0.5 && Math.hypot(P.vx, P.vz) > 1.2 ? 2.8 : 0) * (proom === 'laundry' ? 0.45 : 1);   // (the machines drown footsteps out)
      if (loud) { this.stompT = (this.stompT || 0) - dt; if (this.stompT <= 0) { this.stompT = P.st === 'charge' ? 0.35 : 0.5; this.noise(P.x, P.z, loud, '?', true); } } else this.stompT = 0;
      for (const b of this.buckets) if (b.state === 'fly') {
        b.t += dt; const k = Math.min(1, b.t / b.dur); b.x = b.sx + (b.tx - b.sx) * k; b.z = b.sz + (b.tz - b.sz) * k; b.y = b.sy + (b.ty - b.sy) * k + Math.sin(Math.PI * k) * (b.arc === undefined ? 1.6 : b.arc);
        b.m.position.set(b.x, b.y, b.z); b.m.rotation.x += dt * 9;
        // coming down on someone's head: out cold, and it drops at their feet
        if (k > 0.45 && k < 1 && !b.wet) { const hit = this.npcs.find((n) => !n.ko && n.a.st !== 'down' && Math.hypot(n.a.x - b.x, n.a.z - b.z) < 0.6 && b.y < n.a.y + 2.0 && b.y > n.a.y + 0.15);
          if (hit) { const fx = b.tx - b.sx, fz = b.tz - b.sz, fl = Math.hypot(fx, fz) || 1; hit.shock = 0; hit.a.shock = 0; hit.pushing2 = false; if (hit.mode === 'chase') hit.mode = 'route';
            if (b.water) { b.water = false; this.spill(hit.a.x, hit.a.z, hit.a.y); }
            this.knockOut(hit, fx / fl, fz / fl, ['ゴンッ!', 'ガツン!', 'ボコッ!'][(this.t * 5 | 0) % 3], 1.2);
            b.tx = b.x + fx / fl * 0.5; b.tz = b.z + fz / fl * 0.5; b.ty = floorY(b.tx, b.tz); b.sx = b.x; b.sz = b.z; b.sy = b.y; b.t = 0; b.dur = 0.25; b.arc = 0.15; } }
        if (k >= 1) { b.state = 'floor'; b.arc = undefined; if (b.water) { b.water = false; if (!b.wet) this.spill(b.tx, b.tz, b.ty); } if (b.soda) { b.soda = false; if (!b.wet) this.spill(b.tx, b.tz, b.ty, 'soda'); }
          const pud = this.puddles.some((q) => ((b.x - q.x) / q.rx) ** 2 + ((b.z - q.z) / q.rz) ** 2 < 1.4);
          if (b.wet) { this.fx.water && (this.fx.water(b.x, b.z, 2.4, POOL.water), this.fx.water(b.x + 0.2, b.z - 0.1, 1.4, POOL.water)); b.m.rotation.set(0.3, 0.4, 0.2); b.m.position.y = b.ty; }
          else { if (pud && this.fx.water) this.fx.water(b.x, b.z, 1.4, b.ty); b.m.rotation.set(Math.PI / 2, 0, 0.4); b.m.position.y = b.ty + (b.kind === 'can' ? 0.1 : 0.3); if (b.kind === 'can') b.m.children[0].position.y = -0.085; } if (!SAFE[roomAt(b.x, b.z)]) this.noise(b.x, b.z, 16, '?!'); else this.ringAt(b.x, b.z, 2, 0.5); if (this.g.audio && this.g.audio.thump) this.g.audio.thump(6); this.think(b.wet ? '*SPLOOSH*' : '*CLATTER*', 1); }
      }
      this.canStep(dt); this.printStep(dt); this.bossStep(dt);
      for (const f of this.flying) {
        if (f.t >= f.dur) continue; f.t = Math.min(f.dur, f.t + dt); const k = f.t / f.dur;
        f.m.position.set(f.sx + (f.tx - f.sx) * k, f.sy + (f.ty - f.sy) * k + Math.sin(Math.PI * k) * f.h, f.sz + (f.tz - f.sz) * k);
        f.m.rotation.set(f.r0[0] + (f.r1[0] - f.r0[0]) * k, f.r0[1] + (f.r1[1] - f.r0[1]) * k, f.r0[2] + (f.r1[2] - f.r0[2]) * k);
      }
      // the staff (nobody minds you in the bath or the wash area; just after a restart they get a moment too)
      this.grace = Math.max(0, this.grace - dt);
      const pr = roomAt(P.x, P.z);
      for (const n of this.npcs) {
        this.npcStep(n, dt);
        if (n.mode === 'chase') continue;   // (on his tail: see npcStep)
        // big wet footprints across the floor: whoever spots a fresh trail follows it to see where it goes
        if (this.prints && this.prints.length && n.mode === 'route' && n.a.st === 'free' && !n.busy && !n.ko && (n.fpT = (n.fpT || 0) - dt) <= 0) { n.fpT = 0.4; n.trails = n.trails || new Set();
          const f = this.prints.find((q) => q.t < 26 && !n.trails.has(q.trail) && Math.abs(q.y - n.a.y) < 1 && Math.hypot(q.x - n.a.x, q.z - n.a.z) < 6.5 && this.sees(n, q.x, q.z, 6.5));
          if (f) { n.trails.add(f.trail); const tr = this.prints.filter((q) => q.trail === f.trail && q.i >= f.i).sort((u, v) => u.i - v.i), last = tr[tr.length - 1];
            this.goTo(n, f.x, f.z); n.path = n.path.concat(tr.slice(1).map((q) => [q.x, q.z])); n.mode = 'goto'; n.inv = true; n.noiseAt = [last.x + (last.x - f.x) * 0.2, last.z + (last.z - f.z) * 0.2];
            this.popAt(n.a, ['…足跡?', 'なんだこの足跡…', 'でかい足…!?'][(this.t * 3 | 0) % 3], 1.4); } }
        if ((SAFE[pr] && !n.raid) || this.grace > 0 || n.a.st !== 'free' || n.busy || P.hidden || P.boxHide || P.inStall || P.sub) { n.alarm = Math.max(0, n.alarm - dt); continue; }
        const range = this.range(n), d = Math.hypot(P.x - n.a.x, P.z - n.a.z), same = roomAt(n.a.x, n.a.z) === pr;
        // right next to someone they hear you, whichever way they face; on tiptoe you can get much closer
        // (the receptionist, at her desk, still catches a tiptoe that comes right up behind her)
        const ear = (P.tip > 0.5 ? (n.ear ? 1.2 : 0.6) : (n.ear || 1.7)) * (pr === 'laundry' ? 0.5 : 1);
        let noticed = false;
        if (d < ear && same && this.clear(n.a.x, n.a.z, P.x, P.z)) { noticed = true; n.alarm += dt * 2.4; if (n.mode === 'route' && n.wait > 0) n.a.f = lerpA(n.a.f, Math.atan2(P.z - n.a.z, P.x - n.a.x), dt * 5); }
        else if (this.stinky && same && d < 2.8 && Math.abs(n.a.y - P.y) < 1.5) { noticed = true; n.alarm = Math.min(0.9, n.alarm + dt * 0.75);
          if (!n.smelt) { n.smelt = true; this.popAt(n.a, ['くさっ!?', '…何の匂い?', 'うっ…!'][(this.t * 3 | 0) % 3], 1.4); } if (this.sees(n, P.x, P.z, range)) n.alarm += dt * 2; }
        else if (same && this.sees(n, P.x, P.z, range)) { noticed = true; n.alarm += dt * (1.0 + 2.2 * (1 - d / range)) * 1.15 * (P.st === 'charge' ? 2 : 1); if (d < 1.8) n.alarm = 1; }
        else n.alarm = Math.max(0, n.alarm - dt * 0.6);
        // "?": something's there. They walk over to where they saw it (following it while it stays in view), then look round
        if (noticed && n.alarm > 0.3 && n.alarm < 1 && !n.raid) {   // (the bath searchers just keep looking at the water)
          if (n.mode !== 'goto' || !n.inv) { const path = this.navPath(n.a.x, n.a.z, P.x, P.z); if (path) { n.path = path; n.pi = 0; n.stuckT = 0; n.mode = 'goto'; n.inv = true; n.noiseAt = [P.x, P.z]; n.invT = 0.5; this.popAt(n.a, '?', 1.2); } }
          else if ((n.invT -= dt) <= 0) { n.invT = 0.5; n.noiseAt = [P.x, P.z]; this.goTo(n, P.x, P.z); }
        }
        if (n.alarm >= 1) { this.startChase(n); continue; }
      }
      this.sepNpcs(); this.raidStep(dt);
    }
    npcsOnly(dt) { this.grace = Math.max(0, this.grace - dt); for (const n of this.npcs) { this.npcStep(n, dt); n.alarm = Math.max(0, n.alarm - dt); } this.sepNpcs(); }
    // ======================================================= the chase
    // Spotted, they come after him: shouting, cutting him off, shoving him back and slapping him (three hits: out cold,
    // back to the checkpoint). Break their line of sight and hide (cart, box, stall, under the bath water) and they lose
    // him, search where he was last seen, and go back to work. Nothing gets done with them on his tail.
    chasing() { return this.npcs.some((n) => n.mode === 'chase'); }
    chaseGoal() {   // while they're after him, the goal line says what matters (then puts the real goal back)
      const ch = this.chasing(), e = this.el('.st-obj'); if (!e) return;
      if (ch && !this.chaseObj) { this.chaseObj = e.innerHTML; e.innerHTML = '<b>RUN!</b> HIDE (laundry cart · box · toilet stall: I) ' + (this.wearing ? '' : 'or get back to the BATH!'); e.classList.add('chase'); }
      else if (!ch && this.chaseObj) { e.innerHTML = this.chaseObj; this.chaseObj = null; e.classList.remove('chase'); }
    }
    startChase(n) {
      if (n.mode === 'chase' || n.ko) return;
      const first = !this.chasing(), P = this.P;
      n.mode = 'chase'; n.path = null; n.alarm = 0; n.lostT = 0; n.rp = 0; n.last = [P.x, P.z]; n.raid = false;
      this.popAt(n.a, this.wearing ? ['箱が…動いてる!?', 'おい!その箱!', '歩く箱!?'][this.spotted % 3] : ['イレズミ!?', '変態!', '刺青だ!', 'おい!待て!'][this.spotted % 4], 1.5, true);
      if (first) { this.spotted++; this.bonusLose('seen'); if (this.g.audio && this.g.audio.whoosh) this.g.audio.whoosh(0.4); this.flash = 0.5; }
      for (const m of this.npcs) if (m !== n && m.mode !== 'chase' && !m.ko && m.a.st === 'free' && !m.busy && Math.abs(m.a.y - n.a.y) < 1.5 && Math.hypot(m.a.x - n.a.x, m.a.z - n.a.z) < 9) {
        m.mode = 'chase'; m.path = null; m.alarm = 0; m.lostT = 0; m.rp = 0.2; m.last = [P.x, P.z]; m.raid = false; this.popAt(m.a, '!', 1.0); }
    }
    // anyone who watched him climb in knows exactly where he is
    markWitness() {
      const P = this.P;
      for (const n of this.npcs) if (!n.ko && n.a.st !== 'down' && Math.abs(n.a.y - P.y) < 1.5 && this.sees(n, P.x, P.z, n.mode === 'chase' ? 11 : this.range(n))) {   // (only someone actually watching him go in)
        n.pullOut = true; if (n.mode !== 'chase') this.startChase(n); }
    }
    stallOut() {   // out of the stall: door open, a step out in front of it
      const P = this.P, k = P.stallHide, q = LY.stalls[k], D = this.stallDoors && this.stallDoors[k]; if (k === undefined) return;
      this.noGuard = true; P.stallHide = undefined; P.inStall = false; P.x = q.x + 1.7; P.z = q.z; P.f = 0; this.collide(P, P.r); if (D) D.rotation.y = -1.4; this.hideCd = 0.6;
    }
    pullOut(n) {   // dragged out of his hiding place
      const P = this.P, a = n.a; this.popAt(a, '見つけた!', 1.2, true);
      if (P.hidden) { const hc = P.hidden; P.hidden = null; this.view.root.visible = true; hc.off = false; this.cartBox(hc); const ang = Math.atan2(a.z - hc.z, a.x - hc.x) + 0.6; P.x = hc.x + Math.cos(ang) * 1.5; P.z = hc.z + Math.sin(ang) * 1.5; this.collide(P, P.r); this.shoulderShorts(); }
      if (P.boxHide) { this.noDuck = 1.5; }
      if (P.stallHide !== undefined) this.stallOut();
      for (const m of this.npcs) m.pullOut = false;
    }
    chaseStep(n, dt) {
      const a = n.a, P = this.P;
      if (a.st === 'act' && a.t >= a.dur) a.st = 'free';
      const d = Math.hypot(P.x - a.x, P.z - a.z);
      if (SAFE[roomAt(P.x, P.z)] && !this.wearing) { n.mode = 'return'; this.goTo(n, n.route[n.i][0], n.route[n.i][1]); if (!this.saidBathSafe) { this.saidBathSafe = true; this.popAt(a, '…風呂か。', 1.4); } return; }   // back in the bath: they give up
      const seenHide = n.pullOut && (P.hidden || P.boxHide || P.stallHide !== undefined);
      const inCone = d < 2.2 || Math.abs(ang(Math.atan2(P.z - a.z, P.x - a.x) - a.f)) < 1.25;
      const seen = seenHide || (!P.hidden && !P.boxHide && !P.inStall && !P.sub && !this.freeze && Math.abs(P.y - a.y) < 1.5 && d < 11 && inCone && this.clear(a.x, a.z, P.x, P.z));
      if (seenHide && d < 1.6 && a.st === 'free') { this.pullOut(n); a.st = 'act'; a.atk = 'grab'; a.t = 0; a.dur = 0.5; return; }
      if (seen) { n.lostT = 0; n.last = [P.x, P.z]; } else n.lostT += dt;
      if (n.lostT > 1.6) {   // lost him: off to where he was last seen, and a good look round
        n.mode = 'goto'; n.inv = false; n.noiseAt = n.last; this.goTo(n, n.last[0], n.last[1]); n.mode = 'goto'; this.popAt(a, ['どこだ…?', '消えた…?'][(this.t * 2 | 0) % 2], 1.4); return;
      }
      // run at him, aiming a little ahead (to cut him off), round the walls
      if ((n.rp -= dt) <= 0) { const tx = n.last[0] + (seen ? P.vx * 0.45 : 0), tz = n.last[1] + (seen ? P.vz * 0.45 : 0);
        if (this.lineWalk(a.x, a.z, tx, tz)) { n.path = [[tx, tz]]; n.rp = 0.2; } else { n.path = this.navPath(a.x, a.z, tx, tz) || [[tx, tz]]; n.rp = 0.8 + Math.random() * 0.3; } n.pi = 0; }
      const w = n.path && n.path[n.pi]; let tx = w ? w[0] : n.last[0], tz = w ? w[1] : n.last[1];
      if (w && Math.hypot(tx - a.x, tz - a.z) < 0.3 && n.pi < n.path.length - 1) n.pi++;
      const dx = tx - a.x, dz = tz - a.z, dd = Math.hypot(dx, dz);
      if (!seen && !n.pullOut && P.boxHide && d < 1.9) { a.vx = a.vz = 0; a.f = lerpA(a.f, Math.atan2(P.z - a.z, P.x - a.x), dt * 4); return; }   // (stops short of the box he ducked into)
      if (a.st === 'free' && dd > 0.2) { const sp = 3.2; a.vx = dx / dd * sp; a.vz = dz / dd * sp; a.f = lerpA(a.f, Math.atan2(dz, dx), dt * 9); } else { a.vx *= 0.8; a.vz *= 0.8; }
      const cx0 = a.x, cz0 = a.z; a.x += a.vx * dt; a.z += a.vz * dt; this.collide(a, 0.4); a.y = floorY(a.x, a.z);
      n.stk = a.st === 'free' && dd > 0.5 && Math.hypot(a.x - cx0, a.z - cz0) < 0.4 * dt ? (n.stk || 0) + dt : 0; if (n.stk > 3) { n.stk = 0; this.unstick(n); n.rp = 0; }
      if (seen && d < 1.3 && !(this.hitCd > 0) && a.st === 'free' && P.st !== 'charge') this.hitBy(n);
    }
    hitBy(n) {   // a shove and a slap: he staggers back. Three and he's out cold
      const P = this.P, a = n.a; this.hitCd = 1.1; this.hits = (this.hits || 0) + 1; this.calmT = 0; this.bonusLose('hit');
      a.st = 'act'; a.atk = 'jab'; a.t = 0; a.dur = 0.45; a.f = Math.atan2(P.z - a.z, P.x - a.x);
      const dx = P.x - a.x, dz = P.z - a.z, d = Math.hypot(dx, dz) || 1;
      this.shove = { x: dx / d * 5.5, z: dz / d * 5.5, t: 0.3 }; this.lRel = false; P.st = 'busy'; P.t = 0; P.dur = 0.45; P.vx = P.vz = 0;
      this.flash = 0.35; if (this.g.audio && this.g.audio.thump) this.g.audio.thump(6);
      if (this.hits >= 3) {   // out cold: one clean card, no pile of speech bubbles
        this.catcher = n; this.freeze = 2.2; this.P.vx = this.P.vz = 0; this.clearPops(); this.el('.st-think').classList.remove('on'); this.thinkT = 0;
        const k = this.el('.st-ko'); k.textContent = 'KNOCKED OUT';
        k.style.cssText = 'position:absolute;left:0;top:0;right:0;bottom:0;display:flex;align-items:center;justify-content:center;background:rgba(30,24,36,.28);color:#fffaf0;z-index:60;pointer-events:none;font:400 72px "Dela Gothic One",sans-serif;letter-spacing:3px;text-shadow:none;opacity:1;transition:none';
        setTimeout(() => { k.style.display = 'none'; }, 2100);
      } else this.popAt(a, ['バシッ!', 'ドン!', 'パーン!'][this.hits % 3], 0.8);
    }
    // is this spot inside a wall (not skirting its edge)? and does a short move pass into one?
    inWall(x, z, skip) { for (const w of this.walls) if (w !== skip && x > w.x0 + 0.05 && x < w.x1 - 0.05 && z > w.z0 + 0.05 && z < w.z1 - 0.05) return true; return false; }
    segInWall(x0, z0, x1, z1) { const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, z1 - z0) / 0.05)); for (let k = 1; k <= n; k++) if (this.inWall(x0 + (x1 - x0) * k / n, z0 + (z1 - z0) * k / n)) return true; return false; }
    unstick(n) {   // wedged somewhere for 3 s: hop to the nearest clear spot (away from anyone else) and work out the way again
      const a = n.a, N = this.nav; let best = null, bd = 1e9;
      for (let k = 0; k < 10; k++) { const r = 0.5 + k * 0.12, an = k * 2.4 + Math.random(), x = a.x + Math.cos(an) * r, z = a.z + Math.sin(an) * r; if (!this.walkable(x, z) || !this.clear(a.x, a.z, x, z)) continue;
        const crowd = this.npcs.reduce((s2, m) => s2 + (m !== n && Math.hypot(m.a.x - x, m.a.z - z) < 1 ? 1 : 0), 0), sc = crowd * 3 + r; if (sc < bd) { bd = sc; best = [x, z]; } }
      if (!best) { const c = this.nearestFree(...this.cell(a.x, a.z)); if (c) best = [N.x0 + (c[0] + 0.5) * N.cs, N.z0 + (c[1] + 0.5) * N.cs]; }
      if (best) { a.x = best[0]; a.z = best[1]; this.collide(a, 0.4); }
      if (n.path && n.path.length && n.mode !== 'chase') { const e = n.path[n.path.length - 1]; this.goTo(n, e[0], e[1]); }
    }
    sepNpcs() {   // people don't walk through each other: nudge apart anyone overlapping
      const N = this.npcs;
      for (let i = 0; i < N.length; i++) for (let j = i + 1; j < N.length; j++) {
        const a = N[i].a, b = N[j].a; if (Math.abs(a.y - b.y) > 1) continue;
        const dx = b.x - a.x, dz = b.z - a.z, d = Math.hypot(dx, dz);
        if (d < 0.8 && d > 1e-4) { const k = (0.8 - d) / 2 / d; a.x -= dx * k; a.z -= dz * k; b.x += dx * k; b.z += dz * k; this.collide(a, 0.4); this.collide(b, 0.4); }
      }
    }
    range(n) { if (n.raid && n.looked) return 10; return n.range * (n.mode === 'search' || n.mode === 'goto' ? 1.2 : 1); }   // (the bath searchers look right across the water)
    breakThing(B) {
      this.bonusLose('broke');
      const P = this.P, sd = B.s; B.done = true; B.o.visible = false;
      if (B.w) this.walls.splice(this.walls.indexOf(B.w), 1); if (B.bl) this.blockers.splice(this.blockers.indexOf(B.bl), 1);
      this.buildNav(); P.vx *= 0.7; P.vz *= 0.7;
      // pieces in its own colours (its most common palette swatch), flung away from him, left lying where they land
      let mat = null, uv = null;
      B.o.traverse((q) => { if (!q.isMesh || mat) return; mat = q.material; const a = q.geometry.attributes.uv; if (!a) return;
        const cnt = {}, st = Math.max(1, (a.count / 80) | 0); for (let k = 0; k < a.count; k += st) { const key = a.getX(k).toFixed(3) + ',' + a.getY(k).toFixed(3); cnt[key] = (cnt[key] || 0) + 1; }
        uv = Object.entries(cnt).sort((x, y) => y[1] - x[1])[0][0].split(',').map(Number); });
      const y0 = sd.f ? UP : 0, cx = (sd.x0 + sd.x1) / 2, cz = (sd.z0 + sd.z1) / 2, area = (sd.x1 - sd.x0) * (sd.z1 - sd.z0), n = clamp(Math.round(area * 2.5), 6, 18), h = Math.min(sd.h || 1, 1.9);
      const ax = cx - P.x, az = cz - P.z, al = Math.hypot(ax, az) || 1;
      for (let k = 0; k < n; k++) {
        const r = 0.12 + Math.random() * 0.16, g = new THREE.DodecahedronGeometry(r);
        if (uv) { const a = g.attributes.uv; for (let q = 0; q < a.count; q++) a.setXY(q, uv[0], uv[1]); }
        const m = new THREE.Mesh(g, mat || S.Flat.mat(0xbb8b5e)); m.castShadow = true; m.userData.flatDone = true; this.G.add(m);
        const sx = sd.x0 + Math.random() * (sd.x1 - sd.x0), sz = sd.z0 + Math.random() * (sd.z1 - sd.z0), d = 0.6 + Math.random() * 1.6, sp = (Math.random() - 0.5) * 1.6;
        this.flying.push({ m, sx, sy: y0 + Math.random() * h, sz, tx: sx + (ax / al) * d - (az / al) * sp, ty: y0 + r * 0.6, tz: sz + (az / al) * d + (ax / al) * sp, h: 0.4 + Math.random() * 0.6, t: 0, dur: 0.35 + Math.random() * 0.3, r0: [0, 0, 0], r1: [Math.random() * 6, Math.random() * 6, Math.random() * 6] });
      }
      this.fx.dust && this.fx.dust(cx, y0 + 0.6, cz, 10, 0.5, 0.7, 0.5); this.flash = 0.5;
      if (this.g.audio && this.g.audio.thump) this.g.audio.thump(8);
      if (!SAFE[roomAt(cx, cz)]) this.noise(cx, cz, 12, '!?');
      this.think(['*CRASH*', 'Oops.', '...that was loud.', 'Sorry!'][(this.t * 3 | 0) % 4], 1.2);
    }
    heelsDown() {   // out of puff on tiptoe: the heels come down, THUD
      const P = this.P; this.think(['Hff... too heavy...', 'Ugh, my calves...', 'Can\'t... stay up...'][(this.t * 2 | 0) % 3], 1.4);
    }   // (no thud, nobody hears it: he just has to come down off his toes)
    use() {
      const P = this.P, near = (x, z, r) => Math.hypot(P.x - x, P.z - z) < r;
      if (P.held) { // throw it where you face
        const b = P.held; this.waterOff(b); P.held = null; b.state = 'fly'; b.t = 0; b.sx = b.m.position.x; b.sz = b.m.position.z; b.sy = b.m.position.y;
        const L = Math.max(1, this.reach(P.x, P.z, P.f, 8) - 0.6); b.tx = P.x + Math.cos(P.f) * L; b.tz = P.z + Math.sin(P.f) * L;
        b.wet = inPool(b.tx, b.tz); b.ty = b.wet ? POOL.water - 0.12 : floorY(b.tx, b.tz);   // into the bath: it floats
        b.dur = 0.35 + L * 0.05; P.st = 'busy'; P.t = 0; P.dur = 0.3; this.w.hand = 1; return;
      }
      if (this.chasing() && !P.cart && !this.carts.some((cc) => near(cc.x, cc.z, 2.0)) && !this.buckets.some((b) => b.state === 'floor' && near(b.m.position.x, b.m.position.z, 1.4))) { this.think('No time! They\'re right behind me!', 1.4); return; }
      if (this.stage === 'locker' && near(this.locker.x, this.locker.z, 1.7)) {
        P.st = 'busy'; P.t = 0; P.dur = 0.8; this.stage = 'key'; this.spLocker.visible = false; this.spKey.visible = true;
        this.think('Locked. The key... it must be in my wash bucket, by the bath!', 3.2);
        this.objective('Go back to the BATH and check your WASH BUCKET for the KEY'); return;
      }
      if (this.stage === 'key' && near(this.washSpot.x, this.washSpot.z, 1.6)) {
        P.st = 'busy'; P.t = 0; P.dur = 1.0; this.stage = 'smash'; this.spKey.visible = false; this.spLocker.visible = true;
        P.f = Math.atan2(this.washSpot.z - P.z, this.washSpot.x - P.x);
        const wb = this.washB;
        this.flying.push({ m: wb, sx: wb.position.x, sy: 0, sz: wb.position.z, tx: wb.position.x + 0.3, ty: 0.34, tz: wb.position.z + 0.2, h: 0.5, t: 0, dur: 0.45, r0: [0, 0, 0], r1: [Math.PI, 0.6, 0] });
        this.think('Empty?! No key... Forget it. I\'ll just smash the locker open!', 3.2);
        this.objective('CHARGE into your locker (hold L + direction). It will take a few hits: hide when they come running'); return;
      }
      if (this.stage === 'onigiri' && near(LY.onigiri.x, LY.onigiri.z, 1.7) && this.oni.n > 0) {
        const nEat = Math.min(this.oni.n, LY.onigiri.need - this.oni.eaten);
        P.st = 'busy'; P.t = 0; P.dur = 0.7 + nEat * 0.18; P.f = Math.atan2(LY.onigiri.z - P.z, LY.onigiri.x - P.x);
        // the whole plate at once: a long inhale, and they come off one after another, spinning into his mouth
        const pieces = this.oni.pieces.slice(0, this.oni.n).map((o, k) => { const w = o.getWorldPosition(new THREE.Vector3()), m = this.proto && this.proto.ITEM_ONIGIRI ? this.proto.ITEM_ONIGIRI.clone() : null; if (m) { m.visible = true; m.scale.setScalar(1.3); m.position.copy(w); this.G.add(m); } return { m, sx: w.x, sy: w.y, sz: w.z, d: 0.1 + k * 0.18 }; });
        this.oni.n -= nEat; this.oni.eaten += nEat; this.oniDraw(); this.eatAnim = { t: 0, pieces, dur: P.dur };
        this.think(nEat > 1 ? '*SHLUUURP* ...all of them!' : ['Nom!', '*munch munch*', 'Mmm!', 'So good...'][this.oni.eaten % 4], 1.1); this.noise(P.x, P.z, 2.2, '?', true);
        if (this.oni.eaten >= LY.onigiri.need) { this.stage = 'toilet'; this.spOni.visible = false; this.el('.st-oni').style.display = 'none';
          this.later(1.2, () => { this.think('...oh no. Oh NO. My stomach... TOILET!', 2.6); this.objective('Get to the TOILETS (through the door in the changing room\'s west wall), into a stall'); this.spStall.visible = true; }); }
        return;
      }
      const ST = LY.stalls[LY.stall_use];
      if ((this.stage === 'toilet' || this.stage === 'toilet2') && Math.abs(P.z - ST.z) < 1.1 && P.x < ST.x + 2.2) { this.stall(this.stage === 'toilet2'); return; }
      if (this.stage === 'paper' && near(LY.tp.x, LY.tp.z, 1.8)) {
        P.st = 'busy'; P.t = 0; P.dur = 0.6; this.stage = 'toilet2'; this.spTP.visible = false; this.spStall.visible = true;
        this.think('PAPER! ...now, back to that stall. Quickly.', 2.2); this.objective('Back to the TOILET stall (with the paper)'); return;
      }
      if (this.stage === 'towel' && near(LY.towel.x, LY.towel.z, 1.8)) {
        P.st = 'busy'; P.t = 0; P.dur = 1.0; this.stage = 'storage'; this.spTowel.visible = false; if (!this.crackDone) this.spCrack.visible = true; P.f = -Math.PI / 2;   // (the way up is under the box heap: its ring and arrow come on now)
        this.think('A towel! ...it wouldn\'t even cover one cheek.', 2.6);
        this.later(2.8, () => { if (this.stage === 'storage') { this.think('Hand towels. ALL of them. ...The STORAGE room, upstairs behind the front desk. Up the back stairs!', 3.6); this.objective('Get UPSTAIRS (the back stairs, past the boxes), into STORAGE behind the FRONT DESK'); } });
        return;
      }
      if (P.cart) { P.cart.off = false; this.cartBox(P.cart); P.cart = null; return; }   // let go of the cart
      if (!P.held) { const cc = this.carts.find((q) => Math.hypot(q.x - P.x, q.z - P.z) < 2.0 && (Math.abs(q.vx) + Math.abs(q.vz)) < 0.3);
        if (cc) { P.cart = cc; P.f = Math.atan2(cc.z - P.z, cc.x - P.x); if (!this.saidPush) { this.saidPush = true; this.think('Rolling... (K let go · I hop inside and hide)', 2.4); } return; } }
      // the test box: K next to it puts it on (the story doesn't move); K again (wearing it, away from anything else) puts it back down
      if (this.testBox && !this.wearing && this.testBox.visible && near(this.testBoxAt.x, this.testBoxAt.z, 1.9)) { this.testBox.visible = false; this.wearing = true; this.testWear = true; this.wearBox(); P.st = 'busy'; P.t = 0; P.dur = 0.5; this.think('A box! (just to try it out: K to take it off)', 1.8); return; }
      if (this.testWear && this.wearing && this.stage !== 'box' && this.stage !== 'exit' && !this.buckets.some((b) => b.state === 'floor' && near(b.m.position.x, b.m.position.z, 1.4) && Math.abs(b.m.position.y - P.y) < 1.2)) { this.wearing = false; this.testWear = false; if (this.boxWorn) { this.boxWorn.parent && this.boxWorn.parent.remove(this.boxWorn); this.boxWorn = null; } this.boxDown = false; this.testBoxAt = { x: P.x + Math.cos(P.f) * 1.4, z: P.z + Math.sin(P.f) * 1.4 }; this.testBox.position.set(this.testBoxAt.x, P.y, this.testBoxAt.z); this.testBox.visible = true; P.st = 'busy'; P.t = 0; P.dur = 0.4; return; }
      if (this.stage === 'box' && near(this.boxSpot.x, this.boxSpot.z, 1.9)) { this.putOnBox(); P.st = 'busy'; P.t = 0; P.dur = 0.35; return; }   // (on at once: no wait)
      for (const b of this.buckets) if (b.state === 'floor' && near(b.m.position.x, b.m.position.z, 1.4) && Math.abs(b.m.position.y - P.y) < 1.2) {
        b.state = 'held'; b.wet = false; P.held = b; b.m.rotation.set(0, 0, 0); if (b.kind === 'can') b.m.children[0].position.y = 0;
        if (b.water && !this.saidWater) { this.saidWater = true; this.think('Full of water... throw it (K) or smash it (hold K): a puddle. Anyone running over it goes flying!', 3); }
        else if (b.kind === 'can') { if (!this.saidCan) { this.saidCan = true; this.think(b.soda ? 'A cold one! (J drink it · K throw · hold K smash)' : 'Empty. Still... (K throw · hold K smash)', 2.6); } }
        else if (!this.saidItem) { this.saidItem = true; this.think('If I throw this (K), whoever hears it will go and look...', 2.4); }
        return;
      }
      const V = this.vend; if (V && P.y < 1 && Math.hypot(P.x - (V.x0 - 0.6), P.z - clamp(P.z, V.z0, V.z1)) < 1.0 && Math.abs(P.z - V.z) < 1.3) {
        this.think(V.broke ? 'It\'s had it.' : ['No money. Not ONE yen... I\'m naked. (J: give it a thump?)', 'Still no coins. Maybe a good THUMP... (J)'][this.vendAsk = ((this.vendAsk || 0) + 1) % 2], 2.6); return; }
    }
    leaveBath() {
      this.outOfBath = true; this.spOut.visible = false; this.mosaic.pop = 0.5;
      if (this.stage !== 'locker') return;
      this.spLocker.visible = true;
      this.think('...WAIT. Where is my MAWASHI?!', 2.6);
      this.later(2.8, () => this.think('In the bath nobody minds. Out by the lockers, nobody can see me like this.', 3.2));
      this.objective('Find your LOCKER (through the wash area)');
    }
    // his locker takes three charges: a dent, a bad dent, then the doors burst. Each one is heard across the room
    slap() {
      const P = this.P, fx = Math.cos(P.f), fz = Math.sin(P.f); P.st = 'busy'; P.t = 0; P.dur = 0.35; this.w.hand = 1;
      const inFront = (x, z, r) => { const dx = x - P.x, dz = z - P.z, d = Math.hypot(dx, dz); return d < r && (dx * fx + dz * fz) / (d || 1) > 0.3; };
      const V = this.vend; if (V && !V.broke && P.y < 1 && inFront(V.x0 - 0.1, clamp(P.z, V.z0, V.z1), 1.5)) { this.hitVend(); return; }
      for (const n of this.npcs) if (n.a.st === 'free' && Math.abs(n.a.y - P.y) < 1 && inFront(n.a.x, n.a.z, 1.7)) {
        // J: a slap that knocks them out cold. Out for ten seconds, or until someone comes and shakes them awake.
        // The thud is heard: anyone near comes running to look
        this.knockOut(n, fx, fz, ['バシッ!', 'ゴツン!', 'パーン!'][(this.t * 5 | 0) % 3]); return;
      }
      for (const r of this.rats) if (r.st !== 'home' && r.st !== 'fly' && inFront(r.x, r.z, 1.6)) {
        if (r.carry) { r.carry = false; this.oni.n = Math.min(4, this.oni.n + 1); this.oniDraw(); }
        r.st = 'fly'; r.t = 0.6; r.vx = (r.x - P.x) * 4; r.vz = (r.z - P.z) * 4; this.popAt({ x: r.x, z: r.z, y: 0 }, 'チュー!', 1.0);
        if (this.g.audio && this.g.audio.thump) this.g.audio.thump(3);
      }
      for (const b of this.buckets) if (b.state === 'floor' && Math.abs(b.m.position.y - P.y) < 1 && inFront(b.m.position.x, b.m.position.z, 1.4)) {
        const L = clamp(this.reach(b.m.position.x, b.m.position.z, P.f, 3) - 0.4, 0.5, 2.5);
        this.waterOff(b); b.state = 'fly'; b.t = 0; b.sx = b.m.position.x; b.sz = b.m.position.z; b.sy = b.m.position.y; b.tx = b.sx + fx * L; b.tz = b.sz + fz * L; b.wet = inPool(b.tx, b.tz); b.ty = b.wet ? POOL.water - 0.12 : floorY(b.tx, b.tz); b.dur = 0.3 + L * 0.05;
      }
      let any = false; for (const cc of this.carts) if (cc !== P.cart && inFront(cc.x, cc.z, 1.9)) { cc.vx = fx * 3; cc.vz = fz * 3; cc.spin = 0; any = true; }
      any = any || this.rats.some((r) => r.st === 'fly' && r.t > 0.5) || this.buckets.some((b) => b.state === 'fly' && b.t < 0.05);
      // nothing to hit, a wall right there: he knocks on it. Anyone in earshot comes over to see who's knocking (a lure)
      const rr = this.reach(P.x, P.z, P.f, 1.7); if (!any && rr < 1.6) { const kx = P.x + fx * rr, kz = P.z + fz * rr;
        this.think(['*knock knock*', '*KNOCK KNOCK*', '*bonk bonk*'][(this.t * 3 | 0) % 3], 1.0); this.ringAt(kx, kz, 1.2, 0.5);
        if (!SAFE[roomAt(P.x, P.z)]) this.noise(kx - fx * 0.6, kz - fz * 0.6, 7.5, '?'); if (this.g.audio && this.g.audio.thump) this.g.audio.thump(3);
        if (!this.saidKnock) { this.saidKnock = true; this.later(1.2, () => this.think('...that\'ll bring someone over to look. Then I go the other way.', 2.6)); } }
    }
    // hold K with something in hand: he slams it down on the floor in front of him (loud; water goes everywhere)
    smashHeld() {
      const P = this.P, b = P.held; if (!b) return; this.bonusLose('smash'); P.held = null; this.waterOff(b);
      const fx = Math.cos(P.f), fz = Math.sin(P.f), L = Math.max(0.3, Math.min(0.7, this.reach(P.x, P.z, P.f, 2) - 0.4)), x = P.x + fx * L, z = P.z + fz * L, y = floorY(x, z);
      P.st = 'busy'; P.t = 0; P.dur = 0.45; this.w.hand = 1; this.flash = 0.2;
      // in pieces: the thing is gone, splinters fly out across the floor
      b.m.visible = false; b.state = 'gone';
      const col = b.col || { stool: 0xe2b85e, oke: 0xe8cb98, bucket: 0x84b5ad }[b.kind] || 0xbb8b5e, mat = S.Flat ? S.Flat.mat(col) : new THREE.MeshLambertMaterial({ color: col });
      if (!this.shardGeo) this.shardGeo = [new THREE.TetrahedronGeometry(0.09).scale(1.2, 0.45, 1), new THREE.BoxGeometry(0.15, 0.04, 0.08), new THREE.TetrahedronGeometry(0.07).scale(1, 0.5, 1.5)];
      for (let k = 0; k < 9; k++) { const m = new THREE.Mesh(this.shardGeo[k % 3], mat); m.userData.flatDone = true; m.castShadow = true; m.scale.setScalar(0.7 + Math.random() * 0.9); this.G.add(m);
        const a = Math.random() * 6.28, r = 0.4 + Math.random() * 1.0, tx = x + Math.cos(a) * r, tz = z + Math.sin(a) * r;
        this.flying.push({ m, sx: x, sy: y + 0.3, sz: z, tx, ty: floorY(tx, tz) + 0.02, tz, h: 0.25 + Math.random() * 0.4, t: 0, dur: 0.3 + Math.random() * 0.25, r0: [0, 0, 0], r1: [Math.random() * 8, Math.random() * 8, Math.random() * 8] }); }
      if (b.water && !inPool(x, z)) { b.water = false; this.spill(x, z, y); }
      if (b.soda && !inPool(x, z)) { b.soda = false; this.spill(x, z, y, 'soda'); }
      this.think(['*CRASH!*', '*SMASH!*', '*KRAKK!*'][(this.t * 3 | 0) % 3], 1);
      if (!SAFE[roomAt(x, z)]) this.noise(x, z, 14, '?!'); else this.ringAt(x, z, 2, 0.5);
      if (this.g.audio && this.g.audio.thump) this.g.audio.thump(9);
    }
    // the water in a tub shows only while it's carried upright / standing; a spill leaves a puddle that staff can slip on
    waterOff(b) { if (b.waterM) b.waterM.visible = false; }
    // a puddle the way the kit draws them: an irregular blob, pale water (or fizzy orange), a little glint on it
    spill(x, z, y, kind) {
      const soda = kind === 'soda', fy = floorY(x, z);
      if (this.fx.water) { this.fx.water(x, z, 2.2, fy + 0.05); this.fx.water(x + 0.25, z - 0.15, 1.4, fy + 0.05); }
      const rx = (soda ? 0.6 : 0.75) + Math.random() * 0.2, rz = (soda ? 0.42 : 0.5) + Math.random() * 0.15, sh = new THREE.Shape(), N = 14, ph = Math.random() * 6;
      const rr = [...Array(N)].map((_, k) => 0.82 + 0.18 * Math.sin(k * 2.3 + ph) + 0.08 * Math.sin(k * 5.1 + ph * 2));
      for (let k = 0; k <= N; k++) { const a = k / N * Math.PI * 2, r = rr[k % N]; k ? sh.lineTo(Math.cos(a) * r * rx, Math.sin(a) * r * rz) : sh.moveTo(Math.cos(a) * r * rx, Math.sin(a) * r * rz); }
      const g = new THREE.Group(); g.position.set(x, fy + 0.01, z); g.rotation.y = Math.random() * 3; this.G.add(g);
      const m = new THREE.Mesh(new THREE.ShapeGeometry(sh, 2), S.Flat ? S.Flat.mat(soda ? 0xe8b866 : 0xcfe6f5) : new THREE.MeshLambertMaterial({ color: soda ? 0xe8b866 : 0xcfe6f5 }));
      m.rotation.x = -Math.PI / 2; m.userData.flatDone = true; m.receiveShadow = true; g.add(m);
      const gl = new THREE.Mesh(new THREE.PlaneGeometry(rx * 0.55, rz * 0.12), S.Flat ? S.Flat.mat(0xfaf8f2) : new THREE.MeshBasicMaterial({ color: 0xfaf8f2 }));
      gl.rotation.x = -Math.PI / 2; gl.position.set(-rx * 0.1, 0.004, -rz * 0.25); gl.userData.flatDone = true; g.add(gl);
      this.puddles.push({ x, z, rx, rz, y: fy, m: g, soda });
    }
    // ---- the minimap: round, north up (the camera never turns), this floor only. You, the goal, and staff only when they're close or after you
    mapDraw(T) {
      const cv = this.el('.st-map'); if (!cv) return; if ((this.mapN = (this.mapN || 0) + 1) % 2) return;
      const x = cv.getContext('2d'), W = cv.width, R = W / 2, k = 6.2, P = this.P, fl = P.y > 1.6 ? 1 : 0, X = (wx) => R + (wx - P.x) * k, Z = (wz) => R + (wz - P.z) * k;
      x.save(); x.clearRect(0, 0, W, W); x.beginPath(); x.arc(R, R, R, 0, Math.PI * 2); x.clip();
      x.fillStyle = '#f3ead8'; x.fillRect(0, 0, W, W);
      if (!fl) { x.fillStyle = '#a9d3ef'; x.fillRect(X(POOL.x0), Z(POOL.z0), (POOL.x1 - POOL.x0) * k, (POOL.z1 - POOL.z0) * k); }
      for (const q of LY.solids) { if ((q.f ? 1 : 0) !== fl) continue; const near = Math.abs((q.x0 + q.x1) / 2 - P.x) < 26 && Math.abs((q.z0 + q.z1) / 2 - P.z) < 26; if (!near) continue;
        x.fillStyle = q.k === 'wall' ? '#6b5f66' : '#d6c6aa'; x.fillRect(X(q.x0), Z(q.z0), Math.max(1.5, (q.x1 - q.x0) * k), Math.max(1.5, (q.z1 - q.z0) * k)); }
      // noise: how far it carried (footsteps, knocks, crashes), a ring that fades
      for (const q of this.mapRings || []) { q.t += 1 / 30; if (q.t > 1.2 || Math.abs(q.y - P.y) > 1.5) continue; x.strokeStyle = 'rgba(216,38,46,' + (0.55 * (1 - q.t / 1.2)) + ')'; x.lineWidth = 1.5; x.beginPath(); x.arc(X(q.x), Z(q.z), q.r * k * (0.6 + 0.4 * Math.min(1, q.t * 3)), 0, Math.PI * 2); x.stroke(); }
      // staff on this floor within the map: where they're looking (their cone), and a dot
      for (const n of this.npcs) { const a = n.a; if (Math.abs(a.y - P.y) > 1.5 || n.ko || a.st === 'down') continue; if (Math.hypot(a.x - P.x, a.z - P.z) > R / k + 6) continue;
        const rr = this.range(n) * k, h = n.half || 0.62; x.fillStyle = n.mode === 'chase' ? 'rgba(216,38,46,0.22)' : 'rgba(242,190,60,0.3)';
        x.beginPath(); x.moveTo(X(a.x), Z(a.z)); x.arc(X(a.x), Z(a.z), rr, a.f - h, a.f + h); x.closePath(); x.fill(); }
      for (const n of this.npcs) { const a = n.a; if (Math.abs(a.y - P.y) > 1.5) continue; const d = Math.hypot(a.x - P.x, a.z - P.z);
        if (d > R / k + 2) continue;
        x.fillStyle = n.ko ? '#a49c94' : n.mode === 'chase' ? '#d8262e' : (n.mode === 'goto' || n.mode === 'search' || n.alarm > 0.3) ? '#e0a020' : '#ffffff';
        x.strokeStyle = '#3a3340'; x.lineWidth = 1.5; x.beginPath(); x.arc(X(a.x), Z(a.z), 4.5, 0, Math.PI * 2); x.fill(); x.stroke(); }
      // the goal: a pulsing ring (or, off the edge, a little arrow pointing to it)
      for (const m of this.marks) { if (!m.visible || !m.userData.ar || !m.userData.ar.visible) continue;
        let gx = X(m.position.x), gz = Z(m.position.z); const dx = gx - R, dz = gz - R, dd = Math.hypot(dx, dz), up = (m.position.y > 1.6 ? 1 : 0) !== fl;
        x.strokeStyle = '#d8262e'; x.fillStyle = '#d8262e'; x.lineWidth = 2.5;
        if (dd > R - 12) { const ux = dx / dd, uz = dz / dd; gx = R + ux * (R - 10); gz = R + uz * (R - 10); x.beginPath(); x.moveTo(gx + ux * 7, gz + uz * 7); x.lineTo(gx - uz * 6 - ux * 4, gz + ux * 6 - uz * 4); x.lineTo(gx + uz * 6 - ux * 4, gz - ux * 6 - uz * 4); x.closePath(); x.fill(); }
        else { x.beginPath(); x.arc(gx, gz, 6 + 2 * Math.sin(T * 5), 0, Math.PI * 2); x.stroke(); }
        if (up) { x.font = '700 13px "Barlow Condensed",sans-serif'; x.textAlign = 'center'; x.fillText(fl ? '▼' : '▲', Math.min(W - 10, Math.max(10, gx)), Math.min(W - 6, Math.max(14, gz - 9))); } }
      // him: an arrow, the way he faces
      const f = P.f; x.translate(R, R); x.rotate(f); x.fillStyle = '#f2cf4a'; x.strokeStyle = '#3a3340'; x.lineWidth = 2;
      x.beginPath(); x.moveTo(9, 0); x.lineTo(-6, 6); x.lineTo(-3, 0); x.lineTo(-6, -6); x.closePath(); x.fill(); x.stroke();
      x.restore();
    }
    // ---- testing: jump straight to any goal (set up the way the story would have left things)
    jumpTo(k) {
      const P = this.P, B = this.boss, at = (x, z, y, f) => { P.x = x; P.z = z; P.y = y || 0; P.f = f === undefined ? 0 : f; P.vx = P.vz = 0; P.st = 'free'; P.t = 0; P.dur = 0; this.noGuard = true; this.camT.set(Math.max(-18, Math.min(18, x * 0.8)), P.y, z - 2.6); };
      // clean slate
      this.sf && this.sfHide(false); this.sf = null; this.hud.classList.remove('sf'); this.camFocus = null; this.camD = 15; this.camH = 0.64; this.choiceCb = null; this.el('.st-choice').classList.remove('on'); this.el('.st-sub').style.display = 'none';
      this.timers = []; this.doorPound = null; this.freeze = 0; this.over = false; this.hits = 0; this.shove = null; this.chaseObj = null; this.el('.st-hp').style.display = 'none'; this.el('.st-ko').style.display = 'none';
      this.marks.forEach((m) => { m.visible = false; }); this.dropShorts(true); this.stinky = false; this.grace = 4;
      if (P.hidden) { P.hidden.off = false; this.cartBox(P.hidden); P.hidden = null; this.view.root.visible = true; } if (P.cart) { P.cart.off = false; this.cartBox(P.cart); P.cart = null; } if (P.stallHide !== undefined) this.stallOut(); P.inStall = false; P.held = null; P.hidden = null;
      for (const n of this.npcs) { n.alarm = 0; n.pullOut = false; if (n.mode === 'chase' || n.mode === 'raid') { n.mode = 'route'; n.path = null; n.wait = 1; } }
      this.outOfBath = k !== 'locker' ? true : this.outOfBath; this.spOut.visible = false; this.stage = k;
      const late = ['towel', 'storage', 'box', 'exit', 'kitchen', 'onigiri', 'toilet', 'paper', 'toilet2', 'bossgo', 'fight', 'sumo', 'escape'].includes(k), upstairs = ['box', 'exit', 'kitchen'].includes(k);
      if (late) { this.crackDone || k === 'storage' || this.smashCrack(); if (this.holes) this.holes.visible = true; this.hitsL = 3; }
      if (['towel', 'storage', 'box', 'exit', 'kitchen', 'onigiri', 'toilet', 'paper', 'toilet2', 'bossgo', 'fight', 'sumo', 'escape'].includes(k)) this.saidOut = true;
      if (['locker', 'key', 'smash', 'towel', 'storage', 'box'].includes(k) && this.wearing) { this.wearing = false; this.boxDown = false; if (this.boxWorn) { this.boxWorn.parent && this.boxWorn.parent.remove(this.boxWorn); this.boxWorn = null; } this.pantsBox.visible = true; }   // (back before the box: not wearing it)
      if (k !== 'escape') this.gotMawashi = false;
      switch (k) {
        case 'locker': this.stage = 'locker'; at(CP.lockN.x, CP.lockN.z, 0, CP.lockN.f); this.spLocker.visible = true; this.objective('Find your LOCKER (through the wash area)'); break;
        case 'key': at(CP.lockN.x, CP.lockN.z, 0, CP.lockN.f); this.spKey.visible = true; this.objective('Go back to the BATH and check your WASH BUCKET for the KEY'); break;
        case 'smash': at(-10.5, -34.5, 0, -Math.PI / 2); this.spLocker.visible = true; this.objective('CHARGE into your locker (hold L + direction). It will take a few hits: hide when they come running'); break;
        case 'towel': at(CP.corr.x, CP.corr.z, 0, CP.corr.f); this.spTowel.visible = true; this.objective('Get a TOWEL from the LAUNDRY room (through the staff door, along the back corridor)'); break;
        case 'storage': at(CP.corr.x + 8, CP.corr.z, 0, 0); this.spCrack.visible = !this.crackDone; this.objective('Get UPSTAIRS (the back stairs, past the boxes), into STORAGE behind the FRONT DESK'); break;
        case 'box': at(CP.store.x, CP.store.z, UP, CP.store.f); this.spBox.visible = true; this.objective('Put on the BOX (K next to it)'); break;
        case 'exit': at(CP.store.x, CP.store.z, UP, CP.store.f); this.putOnBox(); this.stage = 'exit'; break;
        case 'kitchen': if (!this.wearing) { this.wearing = true; this.pantsBox.visible = false; this.wearBox(); } at(CP.store.x, CP.store.z, UP, CP.store.f); this.spKitchen.visible = true; this.objective('Leave by the back door: the KITCHEN (downstairs, off the back corridor)'); break;
        case 'onigiri': at(CP.kitchen.x, CP.kitchen.z, 0, CP.kitchen.f); this.hungry(); break;
        case 'toilet': this.oni.eaten = LY.onigiri.need; at(CP.toilet.x + 3, CP.toilet.z, 0, Math.PI); this.spStall.visible = true; this.objective('Get to the TOILETS (through the door in the changing room\'s west wall), into a stall'); break;
        case 'paper': this.stinky = true; at(CP.store.x, CP.store.z, UP, CP.store.f); this.spTP.visible = true; this.objective('Get TOILET PAPER from the STORAGE room (upstairs, behind the front desk)'); break;
        case 'toilet2': at(CP.toilet.x + 3, CP.toilet.z, 0, Math.PI); this.spStall.visible = true; this.objective('Back to the TOILET stall (with the paper)'); break;
        case 'bossgo': at(1, 1.6, 0, -Math.PI / 2); this.cp = CP.toilet; this.spOut.visible = true; this.objective('Your MAWASHI is in the BATH! Back to the bath steps, where you woke up'); this.stage = 'bossgo'; B.rise = null; B.on = false; B.done = false; B.sink = undefined; break;
        case 'fight': at(5.6, 0.6, 0, 0); B.on = true; B.rise = { t: 9, gone: true }; this.stage = 'bossfight'; this.sfStart(); break;
        case 'sumo': at(5.6, 0.6, 0, 0); B.on = true; B.rise = { t: 9, gone: true }; this.stage = 'bossfight'; this.g.startBossBout(this); break;
        case 'escape': this.gotMawashi = true; at(CP.toilet.x + 3, CP.toilet.z, 0, Math.PI); this.escapeStage(); break;
      }
      this.cp = { x: P.x, z: P.z, f: P.f };
      if (this.g.audio && this.g.audio.blip) this.g.audio.blip(true);
    }
    // ================================================================ THE BOSS: the questions, the fight, the sumo bout
    choice(jp, en, opts, cb) {
      const e = this.el('.st-choice'); e.innerHTML = '<h3>' + jp + '</h3><p>' + en + '</p>' + opts.map((o, k) => '<button class="' + (k ? '' : 'sel') + '">' + o + '</button>').join('');
      e.classList.add('on'); this.choiceI = 0; this.choiceCb = cb; this.keys = {};
    }
    // the training offer: asked, and if he's turned down, asked again (as him teaching you)
    bossAsk(n) {
      const B = this.boss; B.hold = false; if (this.mawM) this.mawM.visible = false;   // (the mawashi's tucked in his belt: the fight's for it)
      const q = n === 0 ? [{ who: '親方', jp: '…その前に。稽古をつけてやろうか?', en: '...Before that. Shall I put you through some training?', t: 3.2 }]
        : [{ who: '親方', jp: '…ふむ。必要になると思うがな。', en: 'Hm. I think you\'ll need it.', t: 2.8 }, { who: '親方', jp: 'では、このわしが直々に教えてやろう。…どうだ?', en: 'Then I\'ll teach you myself. The champion in person. ...Well?', t: 3.4 }];
      this.say(q, () => this.choice(n === 0 ? '稽古?' : '直々に教えよう', n === 0 ? 'TRAINING?' : 'LET ME TEACH YOU', ['YES: learn to play', 'NO: just fight'], (i) => {
        if (i === 0) { this.say([{ who: '親方', jp: 'よし。ついてこい。', en: 'Good. Follow me.', t: 1.8 }], () => this.g.startBossTraining(this)); }
        else if (n === 0) this.bossAsk(1);
        else this.say([{ who: '親方', jp: '…よかろう。かかってこい!', en: '...Very well. Come at me!', t: 2.4 }], () => this.sfStart());
      }));
    }
    // back from the versus screen (a sumo bout, or the training)
    resumeFromBoss(res) {
      this.keys = {}; this.over = false; this.paused = false; this.acc = 0;
      if (res === 'quit') { this.g.endCampaign(); return; }
      if (res === 'trained') { this.say([{ who: '親方', jp: 'どうだ、わかったか。…では、いくぞ。', en: 'There. Understood? ...Then let\'s begin.', t: 3.0 }], () => this.sfStart()); return; }
      if (res === 'lost') { this.say([{ who: '親方', jp: 'まだまだ青いな。もう一番!', en: 'Still green. Again!', t: 2.6 }], () => this.g.startBossBout(this)); return; }
      // won: the mawashi comes back
      this.boss.on = true; this.boss.y = -0.12; this.boss.hold = false;
      this.say([
        { who: '親方', jp: '…見事だ。', en: '...Magnificent.', t: 2.2 },
        { who: '親方', jp: 'ところで、その背中の…「半額豆腐」とは何だ?', en: 'By the way. That thing on your back... "HALF-PRICE TOFU"?', t: 3.4 },
        { who: '', jp: '…「無敵」と頼んだんだ。', en: '...I asked for "INVINCIBLE".', t: 2.8 },
        { who: '親方', jp: 'まあいい。持っていけ。だが、その刺青を見られる前に出ていくんだぞ。', en: 'Never mind. Take it. But get out before anyone sees that tattoo.', t: 4.0 },
      ], () => { this.gotMawashi = true; this.boss.sink = 0; this.think('My MAWASHI! ...still can\'t go out the front door like this.', 2.8); this.escapeStage(); });
    }
    // ---- stage 1: a Street Fighter style bout in front of the Mt Fuji mural (best of three rounds)
    sfHide(on) {   // potted plants and the like out of the arena while they fight
      if (on) this.sfHidden = []; for (const q of this.breakables || []) if (q.s && q.s.k === 'plant' && !q.done && q.o) { if (on && Math.abs((q.s.x0 + q.s.x1) / 2 - 7) < 9 && q.s.z0 > -6 && !q.s.f) { q.o.visible = false; this.sfHidden.push(q); } }
      if (!on) { for (const q of this.sfHidden || []) if (!q.done) q.o.visible = true; this.sfHidden = []; }
    }
    sfFighter(x, dir) { return { x, dir, hp: 100, st: 'idle', t: 0, done: false, stun: 0, inv: 0, vx: 0, ai: 0, mv: 0, blockT: 0 }; }
    sfStart() {
      const P = this.P, B = this.boss, bn = S.Banners;
      const go = () => { this.hud.classList.add('sf'); this.stage = 'bossfight'; this.camD = 10.5; this.camH = 0.27; this.camT.set(7, 1.1, -0.9); this.sfHide(true); this.sf = { round: 1, wins: [0, 0], ph: 'none', t: 0, you: this.sfFighter(5.2, 1), boss: this.sfFighter(8.8, -1), timer: 60, pose: null, shake: 0 };
        B.on = true; B.hold = false; B.sink = undefined; B.rise = B.rise || { t: 9, gone: true }; if (this.mawM) this.mawM.visible = false; this.sfHud(true); this.sfReset(); };
      if (bn && !bn.busy) bn.flood({ hold: 0.15, speed: 1.4, onCovered: go }); else go();
    }
    sfHud(init) {
      const e = this.el('.st-sf'), f = this.sf;
      if (init) e.innerHTML = '<div class="bars"><div class="bar l"><b></b><i></i></div><div class="tm">60</div><div class="bar r"><b></b><i></i></div></div><div class="nm l">YOU</div><div class="nm r">YUNOFUJI</div><div class="pips l"></div><div class="pips r"></div><div class="big"></div><div class="keys">A / D move · J slap · K shove (slow, heavy) · hold I block</div>';
      const y = f.you, b = f.boss, q = (c) => e.querySelector(c), pc = (h) => Math.max(0, h) + '%';
      f.dy = (f.dy === undefined ? 100 : f.dy + (y.hp - f.dy) * 0.08); f.db = (f.db === undefined ? 100 : f.db + (b.hp - f.db) * 0.08);
      q('.bar.l i').style.width = pc(y.hp); q('.bar.l b').style.width = pc(f.dy); q('.bar.r i').style.width = pc(b.hp); q('.bar.r b').style.width = pc(f.db);
      q('.tm').textContent = Math.max(0, Math.ceil(f.timer)); q('.pips.l').textContent = '★'.repeat(f.wins[0]) + '☆'.repeat(2 - f.wins[0]); q('.pips.r').textContent = '★'.repeat(f.wins[1]) + '☆'.repeat(2 - f.wins[1]);
    }
    sfText(t) { const b = this.el('.st-sf .big'); if (!b) return; b.classList.remove('on'); if (!t) return; b.textContent = t; void b.offsetWidth; b.classList.add('on'); }
    sfReset() {
      const f = this.sf; Object.assign(f.you, this.sfFighter(5.2, 1)); Object.assign(f.boss, this.sfFighter(8.8, -1));
      f.dy = f.db = 100; f.timer = 60; f.ph = 'intro'; f.t = 0; f.pose = null; f.fightShown = false; this.sfApply(); this.sfText('ROUND ' + f.round); this.sfHud();
    }
    sfApply() {   // the two fighters onto the real characters
      const f = this.sf, P = this.P, B = this.boss, y = f.you, b = f.boss, pose = { idle: 'free', jab: 'busy', heavy: 'charge', block: 'wind', hit: 'free', ko: 'slip', win: 'free', lose: 'slip' };
      P.x = y.x; P.z = -0.9; P.y = 0; P.f = y.dir > 0 ? 0 : Math.PI; P.vx = P.vz = 0; P.st = pose[y.st]; P.t = y.t; P.dur = 9; P.fall = y.dir > 0 ? Math.PI : 0; P.tip = 0; P.hidden = null; P.cart = null; P.held = null;
      this.w.throatT = y.st === 'hit' ? Math.max(0, 0.3 - y.t) * 3.3 : 0; f.pose = y.st === 'win' ? 'win' : null;
      B.x = b.x; B.z = -0.9; B.y = 0; B.f = b.dir > 0 ? 0 : Math.PI; B.st = { idle: 'free', jab: 'palm', heavy: 'charge', block: 'brace', hit: 'free', ko: 'fall', win: 'win', lose: 'fall' }[b.st]; B.w.throatT = b.st === 'hit' ? Math.max(0, 0.3 - b.t) * 3.3 : 0;
      B.w.fallX = b.dir > 0 ? -1 : 1; B.w.fallZ = 0; B.w.down = b.st === 'ko' && b.t > 0.3 && b.t < 1.0;
    }
    sfHit(a, d, kind) {   // a (the attacker) hits d, if it reaches
      const f = this.sf, dist = Math.abs(a.x - d.x), reach = kind === 'jab' ? 1.75 : 2.15; if (dist > reach || (d.x - a.x) * a.dir < 0) return;
      const dmg = kind === 'jab' ? 6 : 14, kb = kind === 'jab' ? 0.5 : 1.8, blocking = d.st === 'block' && (a.x - d.x) * d.dir > 0; a.done = true;
      if (blocking) { d.hp -= dmg * 0.12; d.vx = a.dir * kb * 2.2; this.fx.dust && this.fx.dust(d.x, 1.0, -0.9, 2, 0.1, 0.2, 0.1); if (this.g.audio && this.g.audio.thump) this.g.audio.thump(3); return; }
      if (d.inv > 0) return;
      d.hp -= dmg; d.st = 'hit'; d.t = 0; d.stun = kind === 'jab' ? 0.28 : 0.5; d.vx = a.dir * kb * 3.2; d.inv = d.stun + 0.12; d.done = true;
      this.fx.dust && this.fx.dust(d.x, 1.0, -0.9, 5, 0.2, 0.3, 0.2); this.flash = kind === 'jab' ? 0.1 : 0.3; f.shake = kind === 'jab' ? 0.08 : 0.2;
      this.popAt({ x: d.x, z: -0.9, y: 0.3 }, kind === 'jab' ? 'バシッ!' : 'ドーン!', 0.5); if (this.g.audio && this.g.audio.thump) this.g.audio.thump(kind === 'jab' ? 6 : 10);
    }
    sfStep(dt) {
      const f = this.sf, y = f.you, b = f.boss, c = this.ctrl; f.t += dt;
      const face = () => { y.dir = b.x >= y.x ? 1 : -1; b.dir = y.x >= b.x ? 1 : -1; };
      const run = (F, fr, kind) => {   // an attack's timeline: startup, active, recovery
        F.t += dt; const [s0, s1, e] = kind === 'jab' ? [0.09, 0.2, 0.34] : [0.3, 0.42, 0.72];
        if (!F.done && F.t >= s0 && F.t <= s1) this.sfHit(F, fr, kind); if (F.t >= e) { F.st = 'idle'; F.t = 0; F.done = false; } else if (kind === 'heavy' && F.t > s0 && F.t < s1) F.x += F.dir * 5 * dt;   // (the shove lunges)
      };
      if (f.ph === 'intro') { if (f.t > 1.3 && !f.fightShown) { f.fightShown = true; this.sfText('FIGHT!'); } if (f.t > 2.2) { f.ph = 'fight'; f.t = 0; this.sfText(''); } }
      else if (f.ph === 'fight') {
        f.timer -= dt; face();
        for (const F of [y, b]) { F.inv = Math.max(0, F.inv - dt); F.x += F.vx * dt; F.vx *= Math.max(0, 1 - dt * 7); }
        if (y.st === 'hit') { y.t += dt; if (y.t >= y.stun) { y.st = 'idle'; y.t = 0; } }
        else if (y.st === 'jab' || y.st === 'heavy') run(y, b, y.st);
        else {
          const mx = c ? c.mx : 0, blk = !!this.keys.KeyI; y.st = blk ? 'block' : 'idle'; y.t += dt;
          if (!blk && Math.abs(mx) > 0.3) y.x += Math.sign(mx) * (Math.sign(mx) === y.dir ? 3.3 : 2.7) * dt;
          if (c && c.push.pressed) { y.st = 'jab'; y.t = 0; y.done = false; } else if (c && (c.grab.pressed || c.dash.pressed)) { y.st = 'heavy'; y.t = 0; y.done = false; }
        }
        if (b.st === 'hit') { b.t += dt; if (b.t >= b.stun) { b.st = 'idle'; b.t = 0; } }
        else if (b.st === 'jab' || b.st === 'heavy') run(b, y, b.st);
        else {
          const dist = Math.abs(y.x - b.x); b.t += dt; b.ai -= dt; b.blockT = Math.max(0, b.blockT - dt);
          if (b.blockT > 0) b.st = 'block'; else if (b.st === 'block') b.st = 'idle';
          if ((y.st === 'jab' || y.st === 'heavy') && y.t < 0.2 && dist < 2.4 && !b.reacted) { b.reacted = true; if (Math.random() < 0.38) { b.blockT = 0.55; b.st = 'block'; } }
          if (y.st !== 'jab' && y.st !== 'heavy') b.reacted = false;
          if (b.st !== 'block' && b.ai <= 0) { b.ai = 0.22 + Math.random() * 0.38; const r = Math.random();
            if (dist > 2.7) b.mv = 1;
            else if (dist > 1.8) { if (r < 0.4) { b.st = 'heavy'; b.t = 0; b.done = false; } else if (r < 0.7) b.mv = 1; else b.mv = 0; }
            else { if (r < 0.42) { b.st = 'jab'; b.t = 0; b.done = false; } else if (r < 0.6) { b.st = 'heavy'; b.t = 0; b.done = false; } else if (r < 0.8) { b.blockT = 0.6; b.st = 'block'; } else b.mv = -1; } }
          if (b.st === 'idle') b.x += b.dir * b.mv * 2.5 * dt;
        }
        for (const F of [y, b]) F.x = clamp(F.x, 3.3, 11.2);
        const gap = 1.45, d = b.x - y.x; if (Math.abs(d) < gap) { const m = (gap - Math.abs(d)) / 2 * Math.sign(d || 1); y.x -= m; b.x += m; y.x = clamp(y.x, 3.3, 11.2); b.x = clamp(b.x, 3.3, 11.2); }
        if (y.hp <= 0 || b.hp <= 0 || f.timer <= 0) {
          const youWin = b.hp <= 0 ? true : y.hp <= 0 ? false : y.hp >= b.hp; f.wins[youWin ? 0 : 1]++; f.last = youWin;
          (youWin ? b : y).st = 'ko'; (youWin ? b : y).t = 0; (youWin ? y : b).st = 'win'; (youWin ? y : b).t = 0; f.ph = 'ko'; f.t = 0;
          this.sfText(f.timer <= 0 && y.hp > 0 && b.hp > 0 ? 'TIME UP' : 'K.O.'); this.flash = 0.5; f.shake = 0.35; if (this.g.audio) { this.g.audio.thump && this.g.audio.thump(14); this.g.audio.roar && this.g.audio.roar(); }
        }
      } else if (f.ph === 'ko') {
        for (const F of [y, b]) { F.t += dt; F.x += F.vx * dt; F.vx *= Math.max(0, 1 - dt * 6); }
        if (f.t > 2.6) {
          const done = f.wins[0] >= 2 || f.wins[1] >= 2;
          if (!done) { f.round++; this.sfReset(); } else { f.ph = 'end'; f.t = 0; this.sfText(f.wins[0] >= 2 ? 'YOU WIN' : 'YOU LOSE'); }
        }
      } else if (f.ph === 'end') {
        for (const F of [y, b]) F.t += dt;
        if (f.t > 3.0) { f.ph = 'gone'; this.sfEnd(f.wins[0] >= 2); }
      }
      if (this.sf) { this.sfApply(); this.sfHud(); const mid = clamp((y.x + b.x) / 2, 5.6, 8.9); this.camFocus = { x: mid, z: -0.9, y: 1.1, dist: 10.5, h: 0.27 }; }
    }
    sfEnd(won) {
      const bn = S.Banners, B = this.boss, P = this.P;
      const back = () => { this.hud.classList.remove('sf'); this.sfHide(false); this.sf = null; this.camD = 15; this.camH = 0.64; this.camFocus = null; this.el('.st-sf').innerHTML = ''; P.x = 5.6; P.z = 0.6; P.f = 0; P.st = 'free'; P.dur = 0; B.st = 'free'; B.x = 8.4; B.z = 0.6; B.f = Math.PI; B.w.throatT = 0; this.w.throatT = 0; this.camT.set(7, 0, 0);
        if (won) this.say([
          { who: '親方', jp: '…ぐっ。やるじゃないか。', en: '...Gh. Not bad at all.', t: 2.6 },
          { who: '親方', jp: 'いや、待て待て。相撲のルールでやろう!', en: 'Nah, nah, hold on. Let\'s play by SUMO rules!', t: 3.2 },
        ], () => this.g.startBossBout(this));
        else this.say([{ who: '親方', jp: 'まだまだだな。もう一度!', en: 'Not yet. Once more!', t: 2.4 }], () => this.sfStart()); };
      if (bn && !bn.busy) bn.flood({ hold: 0.12, speed: 1.4, onCovered: back }); else back();
    }
    // ---- bonuses: kept until you blow them. Never seen / nobody knocked out / nothing broken (that the story didn't need) / nothing thrown
    bonusLose(k) {
      const B = this.bonus || (this.bonus = { seen: true, ko: true, broke: true, smash: true, hit: true }); if (!B[k]) return; B[k] = false;
      const e = this.el('.st-bonus i[data-k="' + k + '"]'); if (e) { e.classList.add('pop'); setTimeout(() => { e.classList.remove('pop'); e.classList.add('off'); }, 450); }
    }
    bonusBar() {
      const B = this.bonus || (this.bonus = { seen: true, ko: true, broke: true, smash: true, hit: true }), e = this.el('.st-bonus'); if (!e || e.childNodes.length) return;
      e.innerHTML = [['seen', 'UNSEEN'], ['ko', 'NO ONE HURT'], ['broke', 'NOTHING BROKEN'], ['smash', 'NOTHING SMASHED'], ['hit', 'FLAWLESS']].map(([k, t]) => '<i data-k="' + k + '"' + (B[k] ? '' : ' class="off"') + '>' + t + '</i>').join('');
    }
    bonusHTML() {
      const B = this.bonus || { seen: true, ko: true, broke: true, smash: true, hit: true }, all = B.seen && B.ko && B.broke && B.smash && B.hit;
      const row = (ok, jp, t, d) => '<div style="display:flex;gap:10px;align-items:baseline;justify-content:center;opacity:' + (ok ? 1 : 0.45) + '"><b style="font:400 20px \'Yuji Syuku\',serif;color:' + (ok ? '#d8262e' : '#8a8178') + '">' + jp + '</b><span style="font:700 18px \'Barlow Condensed\',sans-serif;letter-spacing:0.06em;' + (ok ? '' : 'text-decoration:line-through') + '">' + (ok ? '✓ ' : '') + t + '</span><span style="font:500 15px \'Barlow Condensed\',sans-serif;opacity:0.7">' + d + '</span></div>';
      return '<div style="margin:10px 0 14px;display:flex;flex-direction:column;gap:4px">' + row(B.seen, '忍', 'GHOST', 'never spotted') + row(B.ko, '和', 'PACIFIST', 'nobody knocked out') + row(B.broke, '静', 'LIGHT TOUCH', 'nothing broken by charging') + row(B.smash, '丁寧', 'GENTLE', 'nothing smashed on the floor') + row(B.hit, '無傷', 'FLAWLESS', 'never got hit') +
        (all ? '<div style="font:400 26px \'Dela Gothic One\',sans-serif;color:#d8262e;margin-top:6px">完璧 · PERFECT</div>' : '') + '</div>';
    }
    // ---- subtitles: who's speaking, the Japanese as they say it, the English underneath
    say(lines, done) {
      const e = this.el('.st-sub'); let t = 0;
      lines.forEach((L) => { this.later(t, () => { if (!this.scene) return; e.innerHTML = '<span class="jp">' + (L.who ? '<span class="who">' + L.who + '</span>' : '') + L.jp + '</span><span class="en">' + L.en + '</span>'; e.style.display = 'block'; }); t += L.t || 2.6; });
      this.later(t, () => { e.style.display = 'none'; if (done) done(); });
      return t;
    }
    // ---- the phone call: he's in the stall; outside, one of the staff takes a call from the boss
    phoneCall(D) {
      const P = this.P, n = this.npcs.find((m) => m.room === 'toilet' && !m.ko) || this.npcs[0], a = n.a, ST = LY.stalls[LY.stall_use];
      n.hold = 14; n.path = null; a.vx = a.vz = 0; n.phone = true; a.f = Math.PI / 2 + 0.5;   // (turned towards us, so we see the phone at the ear)
      this.popAt(a, '♪ プルルル…', 1.4);
      this.say([
        { jp: '♪ プルルル… プルルル…', en: '*ring ring... ring ring...*', t: 2.0 },
        { who: '店員', jp: '…はい、もしもし。', en: '...Hello?', t: 2.0 },
        { who: '店員', jp: 'え、親方ですか?', en: 'Oh, boss? It\'s you?', t: 2.2 },
        { who: '店員', jp: '風呂で…まわしを拾った!?', en: 'You found a MAWASHI... in the bath!?', t: 3.4 },
      ], () => {
        n.phone = false; n.hold = 0.5; if (this.phoneM) this.phoneM.visible = false; this.camFocus = null;
        P.inStall = false; if (D) D.rotation.y = -1.4; P.st = 'free';
        this.stage = 'bossgo'; this.cp = CP.toilet; this.spBack.visible = false;
        this.think('MY MAWASHI!! It\'s in the BATH... and someone\'s GOT it!', 3);
        this.spOut.visible = true; this.objective('Your MAWASHI is in the BATH! Back to the bath steps, where you woke up');
      });
      P.dur = 99;   // (stays put in the stall, listening)
    }
    // scratching his head: elbow up and out, the hand on the top of his head, rubbing back and forth
    scratchPose(n, T) {
      const B = n.v.body; if (!B || !B.bones || !B.bones.RightArm || !B.bones.Head) return;
      const V = THREE.Vector3, Q = THREE.Quaternion, f = n.a.f, fw = new V(Math.cos(f), 0, Math.sin(f)), rt = new V(-Math.sin(f), 0, Math.cos(f));
      const aim = (b, c, dir) => { b.updateMatrixWorld(true); const bp = new V().setFromMatrixPosition(b.matrixWorld), cp = new V().setFromMatrixPosition(c.matrixWorld);
        const q = new Q().setFromUnitVectors(cp.sub(bp).normalize(), dir.normalize()), wq = b.getWorldQuaternion(new Q()); b.quaternion.copy(b.parent.getWorldQuaternion(new Q()).invert().multiply(q.multiply(wq))); b.updateMatrixWorld(true); };
      const bu = B.bones.RightArm, bl = B.bones.RightForeArm, bh = B.bones.RightHand, hd = B.bones.Head;
      aim(bu, bl, new V(0, 0.55, 0).add(rt.clone().multiplyScalar(0.8)).add(fw.clone().multiplyScalar(0.1)));   // elbow up and out to the side
      hd.updateMatrixWorld(true); bl.updateMatrixWorld(true);
      const top = new V().setFromMatrixPosition(hd.matrixWorld).add(new V(0, 0.16, 0)).add(fw.clone().multiplyScalar(0.04 * Math.sin(T * 14))).add(rt.clone().multiplyScalar(0.05)), el = new V().setFromMatrixPosition(bl.matrixWorld);
      aim(bl, bh, top.sub(el));
      hd.rotation.z += 0.18;   // (head tipped, puzzled)
    }
    // the phone to the ear: the right arm folds up so the hand's at the side of the head
    phonePose(n) {
      const B = n.v.body; if (!B || !B.bones || !B.bones.RightArm || !B.bones.Head) return;
      const V = THREE.Vector3, Q = THREE.Quaternion, f = n.a.f, fw = new V(Math.cos(f), 0, Math.sin(f)), rt = new V(-Math.sin(f), 0, Math.cos(f));
      const aim = (b, c, dir) => { b.updateMatrixWorld(true); const bp = new V().setFromMatrixPosition(b.matrixWorld), cp = new V().setFromMatrixPosition(c.matrixWorld);
        const q = new Q().setFromUnitVectors(cp.sub(bp).normalize(), dir.normalize()), wq = b.getWorldQuaternion(new Q()); b.quaternion.copy(b.parent.getWorldQuaternion(new Q()).invert().multiply(q.multiply(wq))); b.updateMatrixWorld(true); };
      const bu = B.bones.RightArm, bl = B.bones.RightForeArm, bh = B.bones.RightHand, hd = B.bones.Head;
      aim(bu, bl, new V(0, -0.55, 0).add(rt.clone().multiplyScalar(0.55)).add(fw.clone().multiplyScalar(0.25)));   // elbow out and down
      hd.updateMatrixWorld(true); bl.updateMatrixWorld(true);
      const ear = new V().setFromMatrixPosition(hd.matrixWorld).add(rt.clone().multiplyScalar(0.11)), el = new V().setFromMatrixPosition(bl.matrixWorld);
      aim(bl, bh, ear.sub(el));
      if (!this.phoneM) { const g = new THREE.Group(), m = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.24, 0.02), S.Flat.mat(0x3a3644)); m.userData.flatDone = true; g.add(m);
        const sc = new THREE.Mesh(new THREE.PlaneGeometry(0.1, 0.2), new THREE.MeshBasicMaterial({ color: 0x9fd0ef })); sc.position.z = 0.011; sc.userData.flatDone = true; g.add(sc); this.G.add(g); this.phoneM = g; }
      const pm = this.phoneM; pm.visible = true; bh.updateMatrixWorld(true); pm.position.setFromMatrixPosition(bh.matrixWorld); pm.rotation.set(0, Math.PI / 2 - f, 0.3);
    }
    // ---- the boss rises out of the bath
    bossStep(dt) {
      const B = this.boss, P = this.P; if (!B) return;
      if (this.stage === 'bossgo' && Math.hypot(P.x - 1, P.z + 0.9) < 2.2 && !B.rise && !B.done) {   // back at the bath steps, where he woke up: the water stirs
        B.rise = { t: 0 }; B.on = true; B.x = 1.8; B.z = -4.6; B.y = -2.7; B.hold = false; this.spOut.visible = false;
        B.f = Math.atan2(P.z - B.z, P.x - B.x); P.st = 'busy'; P.t = 0; P.dur = 99; P.vx = P.vz = 0;
        P.f = Math.atan2(B.z - P.z, B.x - P.x); this.objective('...');   // (the camera eases in on the two of them)
        this.think('...hm? The water\'s... bubbling?', 1.6);
      }
      if (!B.rise) return;
      const R = B.rise; if (!R) return; R.t += dt; const t = R.t;
      if (t < 1.6) { if ((R.bub = (R.bub || 0) - dt) <= 0) { R.bub = 0.12; this.fx.water && this.fx.water(B.x + (Math.random() - 0.5) * 1.2, B.z + (Math.random() - 0.5) * 1.2, 0.8, POOL.water); } }
      else if (t < 3.0) { if (!R.splash) { R.splash = true; this.fx.water && (this.fx.water(B.x, B.z, 7, POOL.water), this.fx.water(B.x + 0.6, B.z - 0.3, 5, POOL.water)); if (this.g.audio && this.g.audio.whoosh) this.g.audio.whoosh(0.8); this.flash = 0.2; }
        const k = Math.min(1, (t - 1.6) / 0.9); B.y = -2.7 + (2.7 - 0.12) * (1 - Math.pow(1 - k, 3)); }   // (up to his belly: the water streams off him)
      if (t > 2.4 && !B.hold && B.sink === undefined) { B.hold = true; B.holdT = 0; }
      if (B.sink !== undefined) { B.sink += dt; B.hold = false; B.y -= dt * 1.6; if (B.sink > 0.4 && !R.gone) { R.gone = true; this.fx.water && this.fx.water(B.x, B.z, 4, POOL.water); } if (B.y < -2.8) { B.on = false; B.rise = null; B.sink = undefined; B.done = true; } }
      if (t > 3.0 && !R.talk) { R.talk = true;
        this.say([
          { who: '親方', jp: '探しものは…これか?', en: 'Looking for... THIS?', t: 3.0 },
          { who: '親方', jp: 'わしの風呂で、ずいぶん好き勝手してくれたな。', en: 'You\'ve been running riot all over MY bathhouse.', t: 3.4 },
          { who: '親方', jp: '欲しけりゃ…力ずくで取ってみい!', en: 'Want it back? ...Then come and TAKE it!', t: 3.2 },
        ], () => { this.think('He\'s got MY MAWASHI... and he\'s a YOKOZUNA?!', 2.2); try { localStorage.setItem('wmm_boss', '1'); } catch (e) {} this.later(1.4, () => this.bossAsk(0)); });
      }
    }
    bossDraw(dt, T) {
      const B = this.boss; if (!B) return; const bv = B.v;
      if (S.SoftSumo && S.SoftSumo.loaded && !bv.soft) { S.SoftSumo.attach(bv, { noBlob: true }); for (const m of bv.soft.mats) if (/hair/i.test(m.name || '')) m.color.set(0xc9c6c0); }
      if (bv.soft && !this.shrineDone && this.kit && this.bossOn) this.makeShrine(T);   // (only with the boss story, until it's signed off)
      if (!B.on) { bv.root.visible = false; if (this.mawM) this.mawM.visible = false; return; }
      const w = B.w; w.x = B.x; w.z = B.z; w.y = 0; w.f = B.f; w.fx = Math.cos(B.f); w.fz = Math.sin(B.f); w.vx = w.vz = 0; w.spd = 0;
      if (w.st !== B.st) { w.st = B.st; w.t = 0; } else w.t += dt;
      w.carry = B.hold ? { overhead: true } : null; w.relaxed = true; w.hand = 1;
      bv.update(w, Math.max(dt, 1e-4), T); bv.root.position.y += B.y; bv.root.visible = true;
      // our mawashi, held up over his head in both hands (it glints)
      if (B.hold) { if (!this.mawM) this.mawM = this.makeMawashi(B.belt); const a = this._ha || (this._ha = new THREE.Vector3()), b = this._hb || (this._hb = new THREE.Vector3());
        bv.handWorld(1, a); bv.handWorld(-1, b); this.mawDrape(this.mawM, b, a, B.f, T); this.mawM.visible = true;
        B.holdT = (B.holdT || 0) + dt; if ((B.glint = (B.glint || 0) - dt) <= 0) { B.glint = 0.35; this.popAt({ x: (a.x + b.x) / 2 + (Math.random() - 0.5) * 0.9, z: (a.z + b.z) / 2, y: a.y + 0.1 + Math.random() * 0.5 }, '✦', 0.6); } }
      else if (this.mawM) this.mawM.visible = false;
    }
    // a mawashi: a long, wide band of heavy cloth. Held up by both hands it sags between them, the loose end hanging down
    makeMawashi(col) {
      const N = 34, pos = new Float32Array(N * 2 * 3), idx = [];
      for (let k = 0; k < N - 1; k++) { if (k === 21) continue; const a = k * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }   // (two strips: the sag, and the end hanging)
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setIndex(idx);
      const m = new THREE.Mesh(g, S.Flat.mat(col === undefined ? 0x2c3d93 : col, { side: THREE.DoubleSide })); m.userData.flatDone = true; m.castShadow = true; m.frustumCulled = false; m.N = N;
      this.G.add(m); return m;
    }
    mawDrape(m, L, R, f, T) {
      const N = m.N, pos = m.geometry.attributes.position, fw = new THREE.Vector3(Math.cos(f), 0, Math.sin(f)), side = new THREE.Vector3().subVectors(R, L).setY(0).normalize(), up = new THREE.Vector3(0, 1, 0);
      const put = (k, p, wd, wv) => { pos.setXYZ(k * 2, p.x + wv.x * wd, p.y + wv.y * wd, p.z + wv.z * wd); pos.setXYZ(k * 2 + 1, p.x - wv.x * wd, p.y - wv.y * wd, p.z - wv.z * wd); };
      const p = new THREE.Vector3();
      for (let k = 0; k < 22; k++) { const t = k / 21; p.lerpVectors(L, R, t); p.y += 0.2 - Math.sin(t * Math.PI) * 0.06; p.addScaledVector(fw, 0.04);   // the sag between his hands
        put(k, p, 0.17, up.clone().addScaledVector(fw, -0.15).normalize()); }
      for (let k = 22; k < N; k++) { const t = (k - 22) / (N - 23), sw = Math.sin(T * 2.2 + t * 2) * 0.06 * t;   // the loose end, hanging off his right hand
        p.copy(R).addScaledVector(fw, -0.12 - 0.08 * t).addScaledVector(side, 0.12 + 0.1 * t + sw); p.y += 0.1 - t * 0.9; put(k, p, 0.15, side); }
      pos.needsUpdate = true; m.geometry.computeVertexNormals(); m.geometry.computeBoundingSphere();
    }
    // ---- the shrine to him: framed photos (the locker room; on the counter behind reception) and his bronze statue upstairs
    makeShrine(T) {
      this.shrineDone = true; const B = this.boss, bv = B.v, r = this.R.r;
      // the photo: him in his prime (black topknot), rendered once into a texture
      const rt = new THREE.WebGLRenderTarget(256, 320); const hair = bv.soft.mats.find((m) => /hair/i.test(m.name || '')), hc = hair && hair.color.getHex();
      if (hair) hair.color.set(0x241f2a);
      const w = B.w, X = 300, Z = 300; Object.assign(w, { x: X, z: Z, f: Math.PI / 2, fx: 0, fz: 1, st: 'win', t: 0.7, carry: null }); bv.victory = 'flex';
      for (let i = 0; i < 8; i++) bv.update(w, 1 / 30, T);
      bv.root.visible = true; bv.root.position.y = 0;
      const cam = new THREE.PerspectiveCamera(26, 256 / 320, 0.5, 40); cam.position.set(X, 1.25 * bv.s, Z + 7.2); cam.lookAt(X, 1.1 * bv.s, Z); cam.updateMatrixWorld();
      const bg = this.scene.background; this.scene.background = new THREE.Color(0xe6d6b8);
      r.setRenderTarget(rt); r.render(this.scene, cam); r.setRenderTarget(null); this.scene.background = bg;
      bv.root.visible = false; if (hair) hair.color.setHex(hc); bv.victory = 'tegatana';
      const plateTex = () => { const c = document.createElement('canvas'); c.width = 256; c.height = 64; const x = c.getContext('2d');
        x.fillStyle = '#d3ab7a'; x.fillRect(0, 0, 256, 64); x.fillStyle = '#3b2a1e'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.font = '400 36px "Yuji Syuku", "Dela Gothic One", serif'; x.fillText('横綱 湯乃富士', 128, 34);
        const t = new THREE.CanvasTexture(c); if (document.fonts && document.fonts.load) document.fonts.load('400 36px "Yuji Syuku"', '横綱湯乃富士').then(() => { x.fillStyle = '#d3ab7a'; x.fillRect(0, 0, 256, 64); x.fillStyle = '#3b2a1e'; x.fillText('横綱 湯乃富士', 128, 34); t.needsUpdate = true; }, () => 0); return t; };
      const photo = (wd, ht) => { const g = new THREE.Group();
        const fr = new THREE.Mesh(new THREE.BoxGeometry(wd + 0.1, ht + 0.1, 0.04), S.Flat.mat(0x6e4c38)); fr.castShadow = true; g.add(fr);
        const pic = new THREE.Mesh(new THREE.PlaneGeometry(wd, ht), new THREE.MeshBasicMaterial({ map: rt.texture })); pic.position.z = 0.022; pic.userData.flatDone = true; g.add(pic);
        const pl = new THREE.Mesh(new THREE.PlaneGeometry(wd * 0.8, wd * 0.2), new THREE.MeshBasicMaterial({ map: plateTex() })); pl.position.set(0, -ht / 2 - 0.02, 0.025); pl.userData.flatDone = true; g.add(pl);
        fr.userData.flatDone = true; this.G.add(g); return g; };
      // 1: the changing room, on the far wall by the staff door (facing into the room)
      const p1 = photo(0.76, 0.92); p1.position.set(3.2, 0.6, -46.76);
      // 2: on the reception desk, propped up facing the door, leaning back a little
      const p2 = photo(0.6, 0.75); p2.position.set(6.6, UP + 1.5, -82.75); p2.rotation.x = -0.14;   // (standing on the front desk, facing whoever walks in)
      // 3: the statue, upstairs in the lounge: bronze, on a stone plinth, flexing
      const sv = new S.WrestlerView(this.scene, B.w.a, this.fx, S.DEF_EQ); sv.viewer = 2; sv.match = null;
      if (S.SoftSumo.attach(sv, { noBlob: true })) { const bz = S.Flat.mat(0xc39a62); sv.soft.M.traverse((q) => { if (q.isMesh) q.material = Array.isArray(q.material) ? q.material.map(() => bz) : bz; }); }
      const fr = this.breakables.find((q) => q.s.k === 'fridge' && q.s.f);   // the milk fridge makes way for him
      if (fr) { fr.done = true; fr.o.visible = false; if (fr.w) this.walls.splice(this.walls.indexOf(fr.w), 1); }
      const SX = 11.35, SZ = -64.8;
      const sw = Object.assign({}, B.w, { x: SX, z: SZ, f: 2.3, fx: Math.cos(2.3), fz: Math.sin(2.3), st: 'win', t: 0.7, carry: null }); sv.victory = 'crossed';   // (arms folded: the proud old champion)
      for (let i = 0; i < 10; i++) sv.update(sw, 1 / 30, T);
      sv.root.position.y += UP + 0.5; sv.root.scale.multiplyScalar(1.12); this.statue = sv;
      const pl = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.5, 1.3), S.Flat.mat(0xc4beb4)); pl.position.set(SX, UP + 0.25, SZ); pl.castShadow = true; pl.userData.flatDone = true; this.G.add(pl);
      const pq = new THREE.Mesh(new THREE.PlaneGeometry(0.7, 0.18), new THREE.MeshBasicMaterial({ map: plateTex() })); pq.position.set(SX - 0.58, UP + 0.27, SZ); pq.rotation.y = -Math.PI / 2; pq.userData.flatDone = true; this.G.add(pq);
      this.walls.push({ x0: SX - 0.6, x1: 12, z0: SZ - 0.7, z1: SZ + 0.7, tall: true }); this.buildNav();
    }
    // ---- the drinks machine: no coins on him, but a good thump drops a can; the third wrecks it
    hitVend() {
      const V = this.vend, P = this.P; if (!V || V.broke) return; V.hits++; V.shake = 0.45; this.flash = 0.15;
      const fx = V.x0 - 0.25, nz = () => V.z + (Math.random() - 0.5) * 0.4;
      if (this.g.audio && this.g.audio.thump) this.g.audio.thump(7); this.noise(V.x0 - 0.5, V.z, 11, '?!');
      if (V.hits < 3) { this.makeCan(fx, 0.35, nz(), -1.6 - Math.random() * 0.8, (Math.random() - 0.5) * 1.2);
        this.think(V.hits === 1 ? '*THUNK* ...oh! A free one!' : '*KA-CHUNK* Another! One more thump...', 2); return; }
      V.broke = true; this.bonusLose('broke'); if (this.spVend) this.spVend.visible = false; this.think('*KRRRASH!!* ...oops.', 2); this.noise(V.x0 - 0.5, V.z, 16, '?!'); if (this.g.audio && this.g.audio.thump) this.g.audio.thump(10);
      // it pitches forward onto its face a little, the front glass bursts, and out comes everything
      if (V.o) { const piv = new THREE.Group(); piv.position.set(V.x0, 0, V.z); this.scene.add(piv); piv.attach(V.o); V.piv = piv; V.tilt = 0; }
      if (S.Flat) for (let k = 0; k < 8; k++) { const sh = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.02, 0.12), S.Flat.mat(k % 3 ? 0xc4dde8 : 0xf2ede4)); sh.userData.flatDone = true; this.G.add(sh);
        const a = Math.PI + (Math.random() - 0.5) * 2.2, r = 0.6 + Math.random() * 1.4, tx = V.x0 + Math.cos(a) * r, tz = V.z + Math.sin(a) * r;
        this.flying.push({ m: sh, sx: V.x0, sy: 1.3, sz: V.z + (Math.random() - 0.5) * 0.8, tx, ty: 0.012, tz, h: 0.4, t: 0, dur: 0.4 + Math.random() * 0.3, r0: [0, 0, 0], r1: [Math.random() * 6, Math.random() * 6, 0] }); }
      for (let k = 0; k < 10; k++) { const a = Math.PI + (k / 9 - 0.5) * 2.4, sp = 1.8 + Math.random() * 2.2;
        const c = this.makeCan(V.x0 - 0.2, 0.3 + Math.random() * 0.9, V.z + (Math.random() - 0.5) * 0.8, Math.cos(a) * sp, Math.sin(a) * sp);
        if (k === 4 && c) { c.state = 'jet'; c.jetT = 3.4; c.jetA = a; c.soda = false; } }   // one's split: it hisses and rockets about, spraying
    }
    makeCan(x, y, z, vx, vz) {
      const ci = (this.canN = (this.canN || 0) + 1) % 3, o = this.cloneP && this.cloneP('ITEM_CAN' + ci); if (!o) return null;
      const m = new THREE.Group(); m.add(o); m.position.set(x, y, z); m.scale.setScalar(1.7); this.G.add(m);   // (sumo-sized: big enough to read)
      const b = { m, kind: 'can', col: [0x5a8fd0, 0xef9a4c, 0x84b5ad][ci], x, z, y: 0, state: 'roll', x0: x, z0: z, base: 0, soda: true, vx, vz, vy: 0.5, roll: 0, yaw: Math.atan2(vz, vx) + Math.PI / 2 };
      this.buckets.push(b); return b;
    }
    canStep(dt) {
      const V = this.vend;
      if (V) { if (V.shake > 0) { V.shake -= dt; if (V.o && !V.piv) V.o.position.x = Math.sin(V.shake * 70) * 0.03 * V.shake / 0.45; }
        if (V.piv && V.tilt < 0.2) { V.tilt = Math.min(0.2, V.tilt + dt * 1.6); V.piv.rotation.z = V.tilt; } }
      const qY = this._qY || (this._qY = new THREE.Quaternion()), qL = this._qL || (this._qL = new THREE.Quaternion()), qR = this._qR || (this._qR = new THREE.Quaternion()), Y = new THREE.Vector3(0, 1, 0), Z = new THREE.Vector3(0, 0, 1);
      for (const b of this.buckets) if (b.kind === 'can' && (b.state === 'roll' || b.state === 'jet')) {
        const p = b.m.position;
        if (b.state === 'jet') {   // the split can: hissing, spinning, shooting about the floor, spraying as it goes
          b.jetT -= dt; b.jetA += (Math.sin(this.t * 7 + b.x0) * 4 + (Math.random() - 0.5) * 6) * dt; const sp = 4.2 * Math.min(1, b.jetT);
          b.vx = Math.cos(b.jetA) * sp; b.vz = Math.sin(b.jetA) * sp; b.yaw += dt * 22;
          if ((b.sprayT = (b.sprayT || 0) - dt) <= 0) { b.sprayT = 0.09; if (this.fx.water) this.fx.water(p.x, p.z, 0.7, 0.15); }
          if ((b.dripT = (b.dripT || 0) - dt) <= 0) { b.dripT = 1.1; this.spill(p.x, p.z, 0, 'soda'); }
          if (b.jetT <= 0) { b.state = 'roll'; b.vx *= 0.3; b.vz *= 0.3; }
        }
        b.vy -= 9 * dt; p.y = Math.max(0.1, p.y + b.vy * dt); if (p.y <= 0.1) { b.vy = Math.abs(b.vy) > 1 ? -b.vy * 0.3 : 0; }
        const ox = p.x, oz = p.z, q = { x: p.x + b.vx * dt, z: p.z + b.vz * dt }; this.collide(q, 0.1);
        const ex = q.x - (p.x + b.vx * dt), ez = q.z - (p.z + b.vz * dt), el = Math.hypot(ex, ez);
        if (el > 1e-4) { const nx = ex / el, nz = ez / el, d = b.vx * nx + b.vz * nz; if (d < 0) { b.vx -= 1.6 * d * nx; b.vz -= 1.6 * d * nz; if (b.state === 'jet') b.jetA = Math.atan2(b.vz, b.vx); } }
        p.x = q.x; p.z = q.z; if (b.state !== 'jet') { const f = Math.max(0, 1 - dt * 1.1); b.vx *= f; b.vz *= f; }
        const spd = Math.hypot(b.vx, b.vz); if (b.state !== 'jet' && spd > 0.2) b.yaw = Math.atan2(b.vz, b.vx) + Math.PI / 2;
        b.roll += Math.hypot(p.x - ox, p.z - oz) / 0.1;
        // lying on its side, rolling about its own axis (across the way it's going)
        qY.setFromAxisAngle(Y, -b.yaw); qL.setFromAxisAngle(Z, Math.PI / 2); qR.setFromAxisAngle(Y, b.roll); b.m.quaternion.copy(qY).multiply(qL).multiply(qR);
        b.m.children[0].position.y = -0.085;
        if (b.state === 'roll' && spd < 0.15 && p.y <= 0.101) { b.state = 'floor'; b.vx = b.vz = 0; b.x = p.x; b.z = p.z; }
      }
    }
    drink() {
      const P = this.P, b = P.held; if (!b) return;
      if (!b.soda) { this.think('Empty.', 1); return; }
      P.held = null; b.state = 'gone'; b.m.visible = false; P.st = 'busy'; P.t = 0; P.dur = 1.1; this.w.hand = 1;
      this.hits = Math.max(0, (this.hits || 0) - 1); P.stam = 1; P.tired = false;
      this.think((this.hits ? '*glug glug glug* Ahhh... that\'s better. ♥' : '*glug glug glug* AHHH. Good as new! ♥'), 1.6);
      this.later(1.7, () => { this.think(['*BUUUUURP*', '*BWAAARP!*', '*urrrp*... pardon.'][(this.t * 3 | 0) % 3], 1.6); this.popAt({ x: P.x, z: P.z, y: P.y + 0.6 }, 'げっぷ', 1.2);
        if (!SAFE[roomAt(P.x, P.z)]) this.noise(P.x, P.z, 6, '?'); if (this.g.audio && this.g.audio.thump) this.g.audio.thump(3); });   // (loud enough to turn heads)
    }
    // a big bare footprint (x forward, the big toe on the inside): a sole, wide at the ball, and five toes
    footGeo(side) {
      const K = this._feet || (this._feet = {}); if (K[side]) return K[side];
      const sole = new THREE.Shape(), N = 16;
      for (let k = 0; k <= N; k++) { const a = k / N * Math.PI * 2, x = Math.cos(a) * 0.15 - 0.03, t = (x + 0.18) / 0.3, w = 0.05 + 0.035 * Math.min(1, Math.max(0, t)) + 0.012 * side * Math.sin(a) * t, y = Math.sin(a) * w + side * 0.008 * t;
        k ? sole.lineTo(x, y) : sole.moveTo(x, y); }
      const toes = [[0.165, 0.052, 0.03], [0.178, 0.018, 0.022], [0.172, -0.012, 0.02], [0.16, -0.038, 0.018], [0.142, -0.06, 0.016]].map(([x, y, r]) => { const t = new THREE.Shape(); t.absarc(x, y * side, r, 0, Math.PI * 2, false); return t; });
      return (K[side] = new THREE.ShapeGeometry([sole, ...toes], 3));
    }
    // ---- wet feet: out of a puddle he leaves a trail of big footprints for a few steps (staff who spot it follow it)
    printStep(dt) {
      const P = this.P; if (!this.prints) { this.prints = []; this.trailN = 0; }
      for (let k = this.prints.length - 1; k >= 0; k--) { const f = this.prints[k]; f.t += dt; if (f.t > 30) { this.G.remove(f.m); this.prints.splice(k, 1); } else if (f.t > 24) f.m.material.opacity = f.o * (30 - f.t) / 6; }
      if (P.hidden || P.boxHide || P.sub || P.st === 'busy' && !this.wetF) return;
      const onP = !P.hidden && this.puddles.find((q) => Math.abs((q.y !== undefined ? q.y : (q.f ? UP : 0)) - P.y) < 0.6 && ((P.x - q.x) / q.rx) ** 2 + ((P.z - q.z) / q.rz) ** 2 < 1.1);
      if (onP) { if (!this.wetF || this.wetF.n < 5 || this.wetF.from !== onP) this.wetF = { n: 5, trail: ++this.trailN, i: 0, acc: 0, side: 1, soda: !!onP.soda, from: onP }; this.wetF.lx = P.x; this.wetF.lz = P.z; return; }
      const W = this.wetF; if (!W || W.n <= 0) return;
      W.acc += Math.hypot(P.x - W.lx, P.z - W.lz); W.lx = P.x; W.lz = P.z; if (W.acc < (P.tip > 0.5 ? 0.45 : 0.62)) return; W.acc = 0;
      const sx = -Math.sin(P.f) * 0.3 * W.side, sz = Math.cos(P.f) * 0.3 * W.side, x = P.x + sx, z = P.z + sz, o = 0.25 + 0.5 * W.n / 5;
      const m = new THREE.Mesh(this.footGeo(W.side), new THREE.MeshBasicMaterial({ color: W.soda ? 0xd9a250 : 0x9cc6e8, transparent: true, opacity: o, depthWrite: false }));
      m.rotation.set(-Math.PI / 2, 0, -P.f); m.scale.setScalar(P.tip > 0.5 ? 1.7 : 2.0); /* (his feet are huge) */ m.position.set(x, floorY(x, z) + 0.014, z); m.userData.flatDone = true; m.renderOrder = 1; this.G.add(m);
      this.prints.push({ x, z, y: P.y, t: 0, trail: W.trail, i: W.i++, m, o }); W.n--; W.side = -W.side;
    }
    // out cold (a slap, or bowled over by a charge before they'd made him out): ten seconds, or till a colleague wakes them
    knockOut(n, fx, fz, sfx, pow) {
      this.bonusLose('ko');
      const a = n.a; if (n.raid && n.mode === 'raid') n.raid = false;
      if (n.pushing) { const c = this.carts.find((cc) => cc.ret && cc.ret.n === n); if (c) c.ret.n = null; n.pushing = false; }
      a.st = 'down'; a.t = 0; a.dur = 10; a.slipFall = false; a.fallX = fx; a.fallZ = fz; a.vx = fx * (pow || 2.2); a.vz = fz * (pow || 2.2); n.ko = true; n.alarm = 0; n.path = null; n.hold = 0;
      this.popAt(a, sfx, 1.0); this.later(0.6, () => { if (n.ko) this.popAt(n.a, '@_@', 1.6); });
      if (this.g.audio) { this.g.audio.thump && this.g.audio.thump(7); this.g.audio.whoosh && this.g.audio.whoosh(0.3); }
      if (!this.saidKO) { this.saidKO = true; this.think('Sorry! ...quick, before someone finds them.', 2.2); }
      this.noise(a.x, a.z, 9, '!?');
    }
    oniDraw() { if (!this.oni) return; this.oni.pieces.forEach((o, k) => { o.visible = k < this.oni.n; }); const e = this.el && this.hud && this.el('.st-oni'); if (e) e.textContent = 'ONIGIRI ' + this.oni.eaten + ' / ' + LY.onigiri.need; }
    chefMakes() {   // the chef is at his counter: a few onigiri, one by one
      if (this.stage !== 'onigiri') return;
      for (let k = 0; k < 3; k++) this.later(0.7 + k * 0.8, () => { if (this.stage === 'onigiri' && this.oni.n < 4) { this.oni.n++; this.oniDraw(); } });
    }
    ratStep(dt) {
      const O = LY.onigiri, tx = O.x + 0.2, tz = O.z - 0.75;
      for (const r of this.rats) {
        if (r.st === 'home') { r.m.visible = false; if (this.stage === 'onigiri' && this.oni.n > 0 && (r.t -= dt) <= 0) { r.st = 'run'; r.x = r.hx; r.z = r.hz; r.wi = 0; } continue; }
        // out of the hole, along the back wall behind the prep island and up to the counter (and the same way home)
        const RP = (LY.ratpath || []).concat([[tx, tz]]);
        r.m.visible = true; let gx = tx, gz = tz, sp = 1.05;
        if (r.st === 'run') { const w = RP[Math.min(r.wi, RP.length - 1)]; gx = w[0]; gz = w[1]; if (r.wi < RP.length - 1 && Math.hypot(gx - r.x, gz - r.z) < 0.25) { r.wi++; continue; } }
        if (r.st === 'fly') { r.t -= dt; r.x += r.vx * dt; r.z += r.vz * dt; r.vx *= 0.92; r.vz *= 0.92; this.collide(r, 0.15); r.m.rotation.x += dt * 14; if (r.t <= 0) { r.st = 'flee'; r.m.rotation.x = 0; let bi = 0, bd = 1e9; [[r.hx, r.hz]].concat(LY.ratpath || []).forEach((w, k) => { const d = Math.hypot(w[0] - r.x, w[1] - r.z); if (d < bd) { bd = d; bi = k; } }); r.wi = bi; } r.m.position.set(r.x, 0.1 + Math.max(0, r.t) * 0.6, r.z); continue; }
        if (r.st === 'flee') { const back = [[r.hx, r.hz]].concat(LY.ratpath || []); if (r.wi > back.length - 1) r.wi = back.length - 1; const w = back[r.wi]; gx = w[0]; gz = w[1]; sp = 1.5; if (r.wi > 0 && Math.hypot(gx - r.x, gz - r.z) < 0.25) { r.wi--; continue; } }
        const dx = gx - r.x, dz = gz - r.z, d = Math.hypot(dx, dz);
        if (d < 0.25) {
          if (r.st === 'run') { if (this.oni.n > 0) { this.oni.n--; r.carry = true; this.oniDraw(); this.popAt({ x: r.x, z: r.z, y: 0.6 }, 'ちゅう', 0.8); } r.st = 'flee'; r.wi = (LY.ratpath || []).length; }
          else { r.st = 'home'; r.carry = false; r.t = 4 + Math.random() * 4; }
          continue;
        }
        r.x += dx / d * sp * dt; r.z += dz / d * sp * dt; r.m.position.set(r.x, 0, r.z); r.m.rotation.set(0, -Math.atan2(dz, dx), 0);
        r.m.position.y = Math.abs(Math.sin(this.t * 20 + r.hx)) * 0.03;
      }
    }
    frontDoor() {   // the front doors are stuck: rattling them is loud
      if (this.doorPound) return;
      const P = this.P, En = LY.entrance; this.doorPound = { t: 0 };
      P.st = 'busy'; P.t = 0; P.dur = 1.9; P.vx = P.vz = 0; P.f = -Math.PI / 2;   // pounding on the doors (palm strikes)
      for (let k = 0; k < 4; k++) this.later(0.15 + k * 0.42, () => { if (!this.doorPound) return; if (this.g.audio && this.g.audio.thump) this.g.audio.thump(5); this.flash = 0.15; this.noise((En.x0 + En.x1) / 2, En.z + 0.6, 14, '?!'); });
      this.think('The door\'s STUCK?! *RATTLE RATTLE*', 2.4);
      this.later(2.0, () => {
        if (!this.doorPound || this.stage !== 'exit') { this.doorPound = null; return; }   // caught at it: the doors are still to try
        this.doorPound = null; this.stage = 'kitchen'; this.spExit.visible = false;
        this.think('...that was loud. The back way out, then: through the KITCHEN, downstairs.', 3.2); this.objective('Leave by the back door: the KITCHEN (downstairs, off the back corridor)'); this.spKitchen.visible = true;
      });
    }
    hungry() {
      this.stage = 'onigiri'; this.spKitchen.visible = false; this.spOni.visible = true; this.el('.st-oni').style.display = 'block'; this.oniDraw();
      this.think('*GRRRUMBLE*... my stomach. I can\'t run on empty... those ONIGIRI!', 3.2);
      this.objective('Eat 10 ONIGIRI from the counter. Wait for the chef to make them, and beat the rats to them (J slap them away)');
    }
    stall(second) {   // into the stall: the door shuts behind him
      const P = this.P, ST = LY.stalls[LY.stall_use], D = this.stallDoors && this.stallDoors[LY.stall_use];
      this.noGuard = true; P.x = ST.x + 0.2; P.z = ST.z; P.f = 0; P.vx = P.vz = 0; P.st = 'busy'; P.t = 0; P.dur = second ? 3.2 : 4.6; P.inStall = true; this.spStall.visible = false;
      if (D) D.rotation.y = 0;
      if (!second) {
        this.think('Nnnnnnngh...!!', 2.0); this.flash = 0.25;
        this.later(2.4, () => { this.think('*FLUSHHH*', 1.2); if (this.g.audio && this.g.audio.whoosh) this.g.audio.whoosh(0.6); this.stinky = true; });
        this.later(3.8, () => { this.think('...there\'s no PAPER?!', 2.4); });
        this.later(5.6, () => { if (this.stage === 'paper') this.think('...and now I STINK. They\'ll smell me coming, tiptoe or not.', 2.8); });
        this.later(4.6, () => { P.inStall = false; if (D) D.rotation.y = -1.4; this.stage = 'paper'; this.spTP.visible = true; this.objective('Get TOILET PAPER from the STORAGE room (upstairs, behind the front desk)'); });
      } else {
        this.think('*rustle rustle*... ahh. Much better.', 2.2); this.stinky = false;   // (wiped: no more stink, no more flies)
        this.later(1.8, () => { this.think('*FLUSHHH*', 1.0); if (this.g.audio && this.g.audio.whoosh) this.g.audio.whoosh(0.6); });
        if (this.bossOn) this.later(2.6, () => this.phoneCall(D)); else this.later(3.2, () => { P.inStall = false; if (D) D.rotation.y = -1.4; this.escapeStage(); });
      }
    }
    escapeStage() {
      this.stage = 'escape'; this.spBack.visible = true; this.cp = CP.toilet;
      for (const t of this.traps) t.m.visible = true;
      for (const n of this.npcs) if (n.room === 'kitchen') { n.range *= 1.25; n.speed *= 1.4; n.sway = 0.9; n.onigiri = false; }
      this.think('Now OUT. The kitchen\'s back door... the chefs will be furious about those onigiri.', 3.4);
      this.objective('Escape by the KITCHEN\'s back door. The chefs are angry... and watch out for MOUSETRAPS');
    }
    hitLocker() {
      if (this.t - (this.lockHitAt || -9) < 0.5) return; this.lockHitAt = this.t;   // (one charge, one hit)
      this.lockerHits = (this.lockerHits || 0) + 1; const k = this.lockerHits, D = this.lkDoors || [];
      if (k >= 3) { this.smashLocker(); return; }
      if (D[0]) { D[0].position.z -= k === 1 ? 0.05 : 0.09; D[0].rotation.set(-0.12 * k, 0.04 * k, 0.05 * k); if (k === 2) D[0].scale.y = 0.93; }
      if (D[1]) D[1].rotation.set(0, -0.06 * k, 0.03 * k); if (D[2]) D[2].rotation.set(0.02 * k, 0, -0.035 * k);
      if (k === 2) { if (D[3]) D[3].rotation.y = 0.18; if (D[4]) D[4].position.z -= 0.03; }
      this.fx.dust && this.fx.dust(this.locker.x, 1.0, this.locker.z, 6, 0.3, 0.4, 0.3); this.flash = 0.35;
      if (this.g.audio && this.g.audio.thump) this.g.audio.thump(7);
      this.noise(this.locker.x, this.locker.z, 14, '?!');
      this.think(k === 1 ? 'Hmm... just a dent. Let me try that again.' : 'The hinge is coming loose... one more!', 2.2);
      this.objective('CHARGE your locker again (' + (3 - k) + ' more). Hide when they come to look');
    }
    smashLocker() {
      this.stage = 'storage'; this.spLocker.visible = false;
      if (this.holes) this.holes.visible = true;
      // the five doors fly off (his first: EMPTY behind it); tiny clothes burst out of the other four
      (this.lkDoors || []).forEach((d, k) => { const sd = k % 2 ? -1 : 1;
        this.flying.push({ m: d, sx: d.position.x, sy: d.position.y, sz: d.position.z, tx: d.position.x + sd * (0.5 + k * 0.25), ty: 0.03, tz: d.position.z + 1.0 + k * 0.25, h: 0.6, t: 0, dur: 0.45 + 0.1 * k, r0: [0, 0, 0], r1: [-Math.PI / 2, sd * 0.8, sd * 0.3] }); });
      if (this.proto && this.proto.CLOTH_SHIRT) for (let k = 0; k < 8; k++) {
        const c = this.proto[k % 2 ? 'CLOTH_SHORTS' : 'CLOTH_SHIRT'].clone(); c.visible = true; this.G.add(c);
        const src = this.lkDoors[1 + (k % 4)] || this.lkDoors[0], sx = src ? src.position.x : this.locker.x, sy = src ? src.position.y : 1;
        this.flying.push({ m: c, sx, sy, sz: LY.locker.face + 0.2, tx: sx + (k % 2 ? 0.5 : -0.5) * (0.5 + (k % 3) * 0.4), ty: 0.01, tz: LY.locker.face + 0.8 + (k % 4) * 0.35, h: 0.7 + (k % 3) * 0.2, t: 0, dur: 0.5 + k * 0.06, r0: [0, 0, 0], r1: [0, k * 1.3, 0] });
      }
      this.fx.dust && this.fx.dust(this.locker.x, 0.8, this.locker.z, 10, 0.4, 0.6, 0.4); this.flash = 0.6;
      this.noise(this.locker.x, this.locker.z, 26, '!?');
      if (this.g.audio) { this.g.audio.thump && this.g.audio.thump(9); this.later(0.15, () => this.g.audio.thump && this.g.audio.thump(5)); }
      this.think('...EMPTY?! Someone took my clothes!', 2.2);
      this.stage = 'towel'; this.objective('They heard that! Get away from the lockers and HIDE');
      this.later(2.3, () => { if (this.stage === 'towel') this.think('And everyone else\'s clothes are TINY. Nothing here fits me...', 2.6); });
      this.later(5.0, () => { if (this.stage === 'towel') { this.think('A towel, at least! The LAUNDRY room, at the end of the back corridor.', 3.4); this.objective('Get a TOWEL from the LAUNDRY room (through the staff door, along the back corridor)'); this.spTowel.visible = true; } });
      this.cp = CP.lockN;
    }
    // the raid: two of the changing-room staff come through to the bath and look over the water. Under it (I) when they
    // look and they see nothing; but he can only hold his breath for five seconds or so
    raidStep(dt) {
      const R = this.raid; if (!R || this.stage !== 'bathhide') return; R.t += dt;
      if (R.phase === 'wait' && R.t >= R.wait) {
        const P = this.P, cand = this.npcs.filter((n) => n.room === 'lock' && !n.ko && n.a.st === 'free' && n.a.y < 1).sort((a, b) => Math.hypot(a.a.x - this.locker.x, a.a.z - this.locker.z) - Math.hypot(b.a.x - this.locker.x, b.a.z - this.locker.z)).slice(0, 2);
        const spots = [[POOL.x0 + 2.4, POOL.z1 - 0.9], [POOL.x1 - 2.6, POOL.z1 - 0.9]];
        cand.forEach((n, k) => { n.raid = true; n.looked = false; this.goTo(n, spots[k][0], POOL.z0 - 0.75); n.mode = 'raid'; n.alarm = 0; });
        R.who = cand; R.phase = 'come'; R.t = 0;
        this.later(0.1, () => { if (this.stage === 'bathhide' && roomAt(P.x, P.z) === 'bath') this.think('Footsteps... they\'re coming! Wait till they look, then under! (hold I)', 2.6); });
      }
      if (R.phase === 'come' && R.who && R.who.every((n) => !n.raid || n.ko)) {   // both have looked and gone: in the clear
        R.phase = 'done'; this.raid = null; this.stage = 'towel';
        this.think('...phew. They\'ve gone.', 1.6);
        this.later(1.8, () => { if (this.stage === 'towel') this.think('And everyone else\'s clothes are TINY. Nothing here fits me...', 2.6); });
        this.later(4.6, () => { if (this.stage === 'towel') { this.think('A towel, at least! The LAUNDRY room, at the end of the back corridor.', 3.4); this.objective('Get a TOWEL from the LAUNDRY room (through the staff door, along the back corridor)'); this.spTowel.visible = true; } });
      }
    }
    smashCrack() {
      this.crackDone = true; this.spCrack.visible = false;
      this.walls.splice(this.walls.indexOf(this.crackW), 1); this.buildNav();
      if (this.crackM) this.crackM.visible = false; if (this.rubble) this.rubble.visible = true;
      const M = S.Flat.mat(0xd3a96e), C = LY.crack;   // a few cartons go tumbling up the stairs
      for (let k = 0; k < 7; k++) { const sz = 0.3 + (k % 3) * 0.12, ch = new THREE.Mesh(new THREE.BoxGeometry(sz, sz * 0.8, sz), M); ch.castShadow = true; ch.userData.flatDone = true; this.G.add(ch);
        const x = C.x0 + 0.8 + (k * 0.67) % 3.2, y = 0.3 + (k % 3) * 0.35, tz = C.z0 - 0.8 - (k % 4) * 0.9;
        this.flying.push({ m: ch, sx: x, sy: y, sz: C.z, tx: x + ((k % 3) - 1) * 0.7, ty: floorY(x, tz) + sz * 0.4, tz, h: 0.5 + (k % 3) * 0.3, t: 0, dur: 0.4 + (k % 4) * 0.08, r0: [0, 0, 0], r1: [k, k * 0.7, k * 1.3] }); }
      this.fx.dust && this.fx.dust(C.x, 0.8, C.z, 14, 0.6, 0.8, 0.6); this.flash = 0.7;
      if (this.g.audio && this.g.audio.thump) this.g.audio.thump(9);
      this.noise(C.x, C.z1 + 0.8, 14, '?!');
      this.think('Special delivery! ...up the stairs we go.', 2.2);
    }
    // the box he wears: built here (the same size and card as the storage-room box) so its two flaps can fold shut over him
    makeBox() {
      const g = new THREE.Group(), C = S.Flat.mat(0xd3a96e), Cd = S.Flat.mat(0xb98c52), Bd = S.Flat.mat(0xe6cfa4), W = 1.6, H = 0.8, D = 1.4, t = 0.04;
      const bx = (w, h, d, x, y, z, m) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); o.position.set(x, y, z); o.castShadow = true; o.userData.flatDone = true; g.add(o); return o; };
      bx(W, H, t, 0, H / 2, -D / 2 + t / 2, C); bx(W, H, t, 0, H / 2, D / 2 - t / 2, C); bx(t, H, D, -W / 2 + t / 2, H / 2, 0, Cd); bx(t, H, D, W / 2 - t / 2, H / 2, 0, Cd); bx(W, t, D, 0, t / 2, 0, Cd);
      bx(0.32, H - 0.07, 0.01, 0, H / 2, D / 2 + 0.005, Bd);   // the shipping label
      g.flaps = [1, -1].map((sd) => { const p = new THREE.Group(); p.position.set(0, H, sd * D / 2); g.add(p); const f = new THREE.Mesh(new THREE.BoxGeometry(W - 0.03, 0.025, D / 2), C); f.position.set(0, 0.013, -sd * D / 4); f.castShadow = true; f.userData.flatDone = true; p.add(f); p.sd = sd; return p; });
      g.setOpen = (k) => { for (const p of g.flaps) p.rotation.x = p.sd * (Math.PI - 0.55) * k; };
      g.setOpen(1); return g;
    }
    wearBox() {
      if (!this.proto || !this.proto.BOX) return;
      const b = this.makeBox(); b.visible = true; b.scale.setScalar(0.95); b.position.set(0, -0.62 * this.view.s, 0.02 * this.view.s); this.view.body.add(b); this.boxWorn = b;
    }
    putOnBox() {
      this.wearing = true; this.pantsBox.visible = false; this.spBox.visible = false; this.spExit.visible = true; this.wearBox();
      this.stage = 'exit'; this.cp = CP.store;
      this.think('Perfect fit. Now, out the FRONT DOOR... without anyone seeing a walking box. (Hold I to squat inside it)', 3.6);
      this.objective('Out through the FRONT DOOR (the entrance, past the shoe lockers). Unseen: hold I to squat in the box');
      if (this.g.audio && this.g.audio.swell) this.g.audio.swell(0.4, 1.0);
    }
    caught(n) {
      this.catcher = n; this.doorPound = null;
      this.spotted++; this.freeze = 1.6; this.P.vx = this.P.vz = 0;
      this.popAt(n.a, this.wearing ? ['箱が…動いてる!?', 'おい!その箱!', '歩く箱!?'][this.spotted % 3] : ['キャーッ!', '変態!', 'おい!そこのお前!', '目が…目がぁ!'][this.spotted % 4], 1.5, true);
      if (this.g.audio && this.g.audio.whoosh) this.g.audio.whoosh(0.4);
      this.flash = 1;
    }
    // the stink: wavy green lines rising off him, three flies round his head
    stinkStep(T, v) {
      if (!this.stinky) { if (this.stinkG) this.stinkG.visible = false; return; }
      if (!this.stinkG) {
        const g = this.stinkG = new THREE.Group(); this.G.add(g); g.lines = []; g.flies = [];
        for (let i = 0; i < 3; i++) { const pts = []; for (let k = 0; k <= 14; k++) { const y = k / 14 * 0.55; pts.push(new THREE.Vector3(Math.sin(y * 13 + i) * 0.06, y, 0)); }
          const l = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 24, 0.018, 5), new THREE.MeshBasicMaterial({ color: 0x8fa04a, transparent: true, opacity: 0.8, depthWrite: false })); l.userData.flatDone = true; g.add(l); g.lines.push(l); }
        const fm = new THREE.MeshBasicMaterial({ color: 0x23202a });
        for (let i = 0; i < 3; i++) { const f = new THREE.Mesh(new THREE.SphereGeometry(0.035, 6, 4), fm); f.userData.flatDone = true; g.add(f); g.flies.push(f); }
      }
      const g = this.stinkG, P = this.P, s = v.s; g.visible = v.root.visible || !!P.hidden || !!this.boxDown;
      g.position.set(P.x, P.y, P.z);
      g.lines.forEach((l, i) => { const h = (T * 0.55 + i / 3) % 1, a = i * 2.1 + 0.4; l.position.set(Math.cos(a) * 0.42 * s, (1.3 + h * 0.9) * s, Math.sin(a) * 0.42 * s); l.rotation.y = -a; l.material.opacity = Math.sin(h * Math.PI) * 0.85; });
      g.flies.forEach((f, i) => { f.position.set(Math.cos(T * 7 + i * 2.1) * 0.5 * s, (2.05 + Math.sin(T * 11 + i) * 0.12) * s, Math.sin(T * 6 + i * 2.1) * 0.5 * s); });
    }
    // his tattoo, across his BACK. He asked for 無敵, "INVINCIBLE". The parlour gave him 半額豆腐: "HALF-PRICE TOFU".
    // Painted into his skin itself (the shader reads the rest-pose body position, so it moves with every fold and step)
    tattooStep(v) {
      if (this.tatDone || !v.soft || !v.soft.mats) return;
      const skin = v.soft.mats.find((m) => /skin/i.test(m.name || '')); if (!skin) return;
      this.tatDone = true;
      const c = document.createElement('canvas'); c.width = 256; c.height = 256; const tex = new THREE.CanvasTexture(c); tex.generateMipmaps = false; tex.minFilter = THREE.LinearFilter;
      const draw = () => { const x = c.getContext('2d'); x.clearRect(0, 0, 256, 256); x.fillStyle = '#000'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.font = '400 112px "Yuji Syuku", "Dela Gothic One", serif'; x.fillText('半額', 128, 66); x.fillText('豆腐', 128, 192); tex.needsUpdate = true; };   // (brush lettering, as a tattooist writes it)
      draw(); if (document.fonts && document.fonts.load) document.fonts.load('400 112px "Yuji Syuku"', '半額豆腐').then(draw, () => 0); if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
      const T = S.Stealth.tat || { x: 0, y: 1.3, w: 0.6, h: 0.6 };   // (rest-pose metres: his upper back)
      const prev = skin.onBeforeCompile;
      skin.onBeforeCompile = (sh, r) => {
        if (prev) prev.call(skin, sh, r);
        sh.uniforms.tatMap = { value: tex };
        sh.vertexShader = 'varying vec3 vTat;\nvarying vec3 vTatN;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n vTat = position; vTatN = normal;');
        const ink = `{ vec2 tu = vec2((vTat.x - ${T.x.toFixed(3)}) / ${T.w.toFixed(3)} + 0.5, (vTat.y - ${T.y.toFixed(3)}) / ${T.h.toFixed(3)} + 0.5);
          if (vTatN.z < -0.15 && tu.x > 0.0 && tu.x < 1.0 && tu.y > 0.0 && tu.y < 1.0) { float a = texture2D(tatMap, vec2(1.0 - tu.x, tu.y)).a; diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.16, 0.2, 0.38), a * 0.88); } }`;
        let f = 'uniform sampler2D tatMap;\nvarying vec3 vTat;\nvarying vec3 vTatN;\n' + sh.fragmentShader;
        f = f.includes('#include <map_fragment>') ? f.replace('#include <map_fragment>', '#include <map_fragment>\n' + ink) : f.replace('vec4 diffuseColor = vec4( diffuse, opacity );', 'vec4 diffuseColor = vec4( diffuse, opacity );\n' + ink);
        sh.fragmentShader = f; this.tatOk = f.includes('tatMap, vec2');
      };
      const ck = skin.customProgramCacheKey ? skin.customProgramCacheKey.bind(skin) : () => '';
      skin.customProgramCacheKey = () => ck() + '|tattoo'; skin.needsUpdate = true;
    }
    // out of the towel cart: somebody's shorts draped over his shoulder. Three steps and they slide off onto the floor
    // borrowed towel-cart trunks, draped over his right shoulder like a towel: one leg down his front, the waistband down
    // his back, the cloth curving over the top of the shoulder. Three steps and they slide off and settle flat on the floor
    shoulderShorts() {
      this.dropShorts(true);
      if (!this.shortsTex) { const c = document.createElement('canvas'); c.width = 128; c.height = 192; const x = c.getContext('2d');
        x.fillStyle = '#86aede'; x.beginPath(); x.moveTo(8, 0); x.lineTo(120, 0); x.lineTo(126, 186); x.lineTo(72, 190); x.lineTo(64, 104); x.lineTo(56, 190); x.lineTo(2, 186); x.closePath(); x.fill();   // the trunks, legs at the bottom
        x.fillStyle = '#f4f1ea'; x.fillRect(8, 0, 112, 18);   // the white waistband
        x.strokeStyle = 'rgba(40,60,110,0.25)'; x.lineWidth = 3; x.beginPath(); x.moveTo(64, 20); x.lineTo(64, 100); x.stroke();
        this.shortsTex = new THREE.CanvasTexture(c); }
      const geo = new THREE.PlaneGeometry(0.4, 0.6, 6, 30), mat = S.Flat.mat(0xffffff, { map: this.shortsTex, side: THREE.DoubleSide }); mat.alphaTest = 0.5; mat.transparent = false;
      const m = new THREE.Mesh(geo, mat); m.castShadow = true; m.userData.flatDone = true; m.frustumCulled = false;
      const g = new THREE.Group(); g.add(m); this.G.add(g);
      const base = Float32Array.from(geo.attributes.position.array);   // (u across, v along the trunks: +0.3 waistband .. -0.3 leg ends)
      this.shorts = { g, m, base, d: 0, on: true, k: 0, seed: Math.random() * 6 };
      this.shortsShape(this.shorts, 0, 0);
      if (!this.saidShorts) { this.saidShorts = true; this.think('...someone\'s shorts came with me.', 1.8); }
    }
    // the cloth's shape: k 0 = over the shoulder (bent round a 0.11 m roll, the two halves hanging down front and back), k 1 = lying crumpled flat
    shortsShape(s, k, T) {
      const pos = s.m.geometry.attributes.position, B = s.base, r = 0.11, s0 = 0.04, arc = Math.PI * r / 2;
      for (let i = 0; i < pos.count; i++) { const u = B[i * 3], v = B[i * 3 + 1], sv = v - s0;
        let fx, fy; const th = clamp(sv / r, -Math.PI / 2, Math.PI / 2);
        fx = Math.sin(th) * r; fy = Math.cos(th) * r - r;                                       // over the top of the shoulder
        if (Math.abs(sv) > arc) { const hang = Math.abs(sv) - arc, sg = Math.sign(sv); fx = sg * (r + hang * 0.18) ; fy = -r - hang; }   // hanging down, flaring a little away from him
        fx += Math.sin(T * 3 + v * 9 + s.seed) * 0.008 * Math.min(1, Math.abs(sv) * 4);   // (a little sway as he walks)
        // on the floor: laid out flat, a few soft rucks
        const gx = v * 0.95 + Math.sin(u * 13 + s.seed) * 0.02, gy = 0.006 + Math.max(0, Math.sin(v * 17 + u * 6 + s.seed)) * 0.025, gz = u * 1.05;
        pos.setXYZ(i, fx + (gx - fx) * k, fy + (gy - fy) * k, u + (gz - u) * k); }
      pos.needsUpdate = true; s.m.geometry.computeVertexNormals();
    }
    dropShorts(now) {
      const s = this.shorts; if (!s) return;
      if (now) { this.G.remove(s.g); this.shorts = null; return; }
      if (!s.on) return; const P = this.P; s.on = false; s.vy = 0.6; s.vx = -Math.cos(P.f) * 0.9; s.vz = -Math.sin(P.f) * 0.9; s.life = 12; s.spin = (Math.random() - 0.5) * 3;
    }
    shortsStep(dt) {
      const s = this.shorts; if (!s) return; const P = this.P, v = this.view, g = s.g;
      if (s.on) {
        s.d += Math.hypot(P.vx, P.vz) * dt;
        // on his right shoulder (the soft sumo's own shoulder joint), the fold along the line of the shoulder
        const A = v.arms && v.arms.find((q) => q.sd < 0), w = this._shw || (this._shw = new THREE.Vector3());
        if (A && A.sh && v.body) { w.copy(A.sh); v.body.localToWorld(w); } else w.set(P.x, P.y + 1.5 * v.s, P.z);
        g.position.set(w.x, w.y + 0.17 * v.s, w.z); g.rotation.set(0, -P.f, 0); g.scale.setScalar(1.4 * v.s);
        g.visible = v.root.visible; this.shortsShape(s, 0, this.t);
        if (s.d > 1.5) this.dropShorts();   // about three steps
        return;
      }
      if (s.vy !== null) {   // sliding off: it falls, turning, and spreads out as it lands
        g.position.x += s.vx * dt; g.position.z += s.vz * dt; g.position.y += s.vy * dt; s.vy -= 9.8 * dt; g.rotation.y += s.spin * dt;
        s.k = Math.min(1, s.k + dt * 2.2); this.shortsShape(s, s.k * 0.7, this.t);
        const fy = floorY(g.position.x, g.position.z) + 0.01;
        if (g.position.y <= fy) { g.position.y = fy; s.vy = null; s.k = 1; this.shortsShape(s, 1, 0); if (this.fx.dust) this.fx.dust(g.position.x, fy + 0.05, g.position.z, 3, 0.2, 0.3, 0.2); }
      }
      if ((s.life -= dt) <= 0) this.dropShorts(true);
    }
    respawn() {
      const P = this.P; this.dropShorts(true); this.noGuard = true; P.x = this.cp.x; P.z = this.cp.z; P.f = this.cp.f; P.y = floorY(P.x, P.z); P.vx = P.vz = 0; P.st = 'free';
      if (P.held) { const b = P.held; P.held = null; b.state = 'floor'; b.m.position.set(b.x0, b.base, b.z0); b.m.rotation.set(0, 0, 0); }
      // the staff are where they were: nobody resets. Whoever caught him looks round for a moment
      for (const n of this.npcs) { n.alarm = 0; n.pullOut = false; if (n.mode === 'chase' || (n === this.catcher && this.hits >= 3)) { const r = n.route[n.i]; n.a.x = r[0]; n.a.z = r[1]; n.a.y = floorY(r[0], r[1]); n.mode = 'route'; n.wait = r[2] || 1; n.path = null; n.a.vx = n.a.vz = 0; continue; }   /* (back at their posts: no spawn-camping) */ if (n === this.catcher) { n.mode = 'search'; n.wait = 3.0; n.path = null; } if (n.a.st === 'act') n.a.st = 'free'; }
      this.hits = 0; this.shove = null; this.hitCd = 0;
      if (P.cart) { P.cart.off = false; this.cartBox(P.cart); P.cart = null; }
      if (P.hidden) { P.hidden.off = false; this.cartBox(P.hidden); P.hidden = null; this.view.root.visible = true; }
      if (this.stage === 'bathhide') {   // (the usual checkpoint, by the wash area door) the two go back to their posts, then come looking again
        P.stam = 1; P.tired = false;
        for (const n of this.npcs) if (n.raid) { n.raid = false; n.looked = false; n.mode = 'return'; this.goTo(n, n.route[n.i][0], n.route[n.i][1]); }
        this.raid = { t: 0, phase: 'wait', wait: 6, k: 0 };
      }
      this.grace = 3.0;
      this.think(this.wearing ? ['Back in the storage room... try again.', 'Out of sight, then move.', 'Tiptoe (I) past them... but not for long.'][this.spotted % 3]
        : ['...ow. Woke up back here. Sneakier this time.', 'Wait for them to look away.', 'Stay behind cover, then move.', 'Tiptoe (I) past them... but not for long.'][this.spotted % 4], 2.2);
    }
    win() {
      this.over = 'win'; this.spExit.visible = false; this.P.vx = this.P.vz = 0;
      this.think('Freedom. Nobody will ever know.', 3);
      if (this.g.audio && this.g.audio.swell) this.g.audio.swell(0.6, 1.4);
      setTimeout(() => { if (!this.scene) return; const e = this.el('.st-over'); e.innerHTML = '<h2 data-jp="脱出">ESCAPED (WELL FED)</h2><p>Time ' + fmtT(this.t) + ' · Spotted ' + this.spotted + ' time' + (this.spotted === 1 ? '' : 's') + '</p>' + this.bonusHTML() + '<button data-c="retry">PLAY AGAIN</button><button data-c="quit">QUIT TO TITLE</button><p class="k">Enter / J play again · Esc quit</p>'; e.classList.add('on'); this.overI = 0; this.markMenu('.st-over', 0); }, 1800);
    }

    // ============================================================== drawing
    draw(dt) {
      const P = this.P, T = this.t, w = this.w, v = this.view;
      if (S.SoftSumo && S.SoftSumo.loaded && !v.soft) S.SoftSumo.attach(v, { noBlob: true });
      if (v.soft && !v.pantsOff && !this.gotMawashi) { v.pantsOff = true; for (const m of v.soft.mats) if (/mawashi/i.test(m.name || '')) m.visible = false; }
      if (v.soft && v.pantsOff && this.gotMawashi) { v.pantsOff = false; for (const m of v.soft.mats) if (/mawashi/i.test(m.name || '')) m.visible = true; }   // (won it back)
      w.x = P.x; w.z = P.z; w.y = 0; w.f = P.f; w.fx = Math.cos(P.f); w.fz = Math.sin(P.f); w.vx = P.vx; w.vz = P.vz; w.spd = Math.hypot(P.vx, P.vz);
      if (this.eatAnim) {   // a vacuum, like Kirby (the gacha inhale): each one spirals in, faster and faster, and vanishes into his mouth
        const E = this.eatAnim; E.t += dt; const hy = P.y + 1.72 * v.s, fx = Math.cos(P.f), fz = Math.sin(P.f), mx = P.x + fx * 0.32 * v.s, mz = P.z + fz * 0.32 * v.s;
        for (const q of E.pieces) { if (!q.m) continue; const k = Math.max(0, Math.min(1, (E.t - q.d) / 0.42)), e = k * k * k, sw = Math.sin(k * Math.PI) * 0.25;
          q.m.position.set(q.sx + (mx - q.sx) * e - fz * sw, q.sy + (hy - q.sy) * e + sw * 0.4, q.sz + (mz - q.sz) * e + fx * sw); q.m.rotation.y += dt * 18; q.m.rotation.x += dt * 9; q.m.scale.setScalar(1.3 * (1 - 0.7 * e)); q.m.visible = k < 1; }
        if (E.t > E.dur) { for (const q of E.pieces) if (q.m) this.G.remove(q.m); this.eatAnim = null; }
      }
      const nst = this.sf && this.sf.pose ? this.sf.pose : this.eatAnim ? 'inhale' : P.st === 'charge' ? 'charge' : P.st === 'wind' ? 'brace' : P.st === 'slip' ? 'fall' : P.st === 'busy' ? 'palm' : P.st === 'wear' ? 'brace' : 'free';
      if (w.st !== nst) { w.st = nst; w.t = 0; } else w.t = P.t;
      if (nst === 'fall') { w.fallX = Math.cos(P.fall); w.fallZ = Math.sin(P.fall); w.down = P.t > 0.3 && P.t < 1.0; } else w.down = false;
      w.hand = 1; const ballW = (this.ballK || 0) > 0.5; w.hunch = Math.max(0.55 * P.tip, ballW ? 1 : 0); w.tiptoe = ballW ? 0 : P.tip; w.crouchT = ballW ? 1 : 0; w.relaxed = true; w.fxs = this.asleep ? { sleep: 1 } : {}; w.carry = P.held ? { small: P.held.kind === 'oke' } : P.cart ? { cart: true } : null;
      if (this.freeze) w.fxs.dizzy = 1;
      v.update(w, Math.max(dt, 1e-4), T);
      if (this.asleep && v.soft) for (const m of v.soft.mats) m.emissive.setRGB(0, 0, 0);   // (asleep: the pose, not the versus sleep-skill's blue tint)
      v.root.position.y += P.y + 0.04 * v.s * P.tip; v.root.visible = !P.hidden;
      const ball = P.boxHide || (!!this.keys.KeyI && P.tip > 0.5 && Math.hypot(P.vx, P.vz) < 0.3 && P.st === 'free' && !P.sub && !P.held && !P.cart);   // I, standing still: curled up in a ball
      this.ballK = (this.ballK || 0) + ((ball ? 1 : 0) - (this.ballK || 0)) * Math.min(1, dt * 10);
      if (this.ballK > 0.01) { const k = this.ballK; v.root.position.y -= (P.boxHide ? 0.8 : 0.06) * v.s * k; v.root.scale.set(v.s * (1 - 0.1 * k), v.s * (1 - 0.32 * k), v.s * (1 - 0.1 * k)); } else v.root.scale.setScalar(v.s);
      // ducking in the box: the same box stays where it stood on the floor and he sinks down into it (no second box)
      const duck = !!P.boxHide && (this.ballK || 0) > 0.05, bw = this.boxWorn;
      if (this.squatBox) this.squatBox.visible = false;
      if (bw) {
        if (duck && !this.boxDown) { this.boxDown = true; this.scene.attach(bw);   // let go of it where it is: it stays standing on the floor, its own size, level
          const e = new THREE.Euler().setFromQuaternion(bw.quaternion, 'YXZ'); bw.rotation.set(0, e.y, 0); bw.scale.setScalar(0.95 * v.s); bw.position.y = P.y; }
        else if (!duck && this.boxDown) { this.boxDown = false; v.body.attach(bw); bw.position.set(0, -0.62 * v.s, 0.02 * v.s); bw.rotation.set(0, 0, 0); bw.scale.setScalar(0.95); }
        if (this.boxDown) { bw.position.x = P.x; bw.position.z = P.z;
          if (this.boxYaw !== undefined && this.npcs.some((n) => n.pushing2)) { const q = Math.PI / 2, want = -this.boxYaw, d = ((want - bw.rotation.y) % q + q * 1.5) % q - q / 2; bw.rotation.y += d * Math.min(1, dt * 2.5); } }   // (shoved square-on: the box swings round flat to them)
        if (bw.setOpen) bw.setOpen(this.boxDown ? Math.max(0, 1 - (this.ballK || 0) * 1.3) : 1);   // the flaps fold shut over him
        if (this.boxDown && (this.ballK || 0) > 0.8) v.root.visible = false;   // (lid shut: just a box)
      }
      v.root.rotation.z = 0;   // (no rocking on tiptoe)
      v.root.updateMatrixWorld(true);   // the floor he stands on (the poses think he's on the ground)
      this.shortsStep(dt); this.tattooStep(v); this.stinkStep(T, v);
      if (P.held && P.held.state === 'held') {
        const b = P.held, ha = this._ha || (this._ha = new THREE.Vector3()), hb = this._hb || (this._hb = new THREE.Vector3()), H = { stool: 0.34, oke: 0.26, bucket: 0.42, can: 0.29 }[b.kind] || 0.4;
        if (b.kind === 'oke' || b.kind === 'can') { v.handWorld(1, ha); b.m.position.set(ha.x, ha.y - H * 0.75, ha.z); }   // by its rim, in one fist
        else { v.handWorld(1, ha); v.handWorld(-1, hb); ha.add(hb).multiplyScalar(0.5); b.m.position.set(ha.x, ha.y - H * 0.5, ha.z); }   // gripped by its sides
        b.m.rotation.set(0, -P.f, 0);
      }
      this.kdt = Math.min(0.05, dt); this.drawN = (this.drawN || 0) + 1;
      this.bossDraw(dt, T); this.bonusBar(); this.mapDraw(T);
      for (const n of this.npcs) { n.a.push = !!n.pushing2; n.v.update(n.a, Math.max(dt, 1e-4), T); if (n.busy) this.knead(n, T); else { n.pushK = (n.pushK || 0) + ((n.pushing2 ? 1 : 0) - (n.pushK || 0)) * Math.min(1, dt * 10); if (n.pushK > 0.01) this.knead(n, T, true, n.pushK); if (n.pushing2) this.sweat(n, dt); } if (n.phone) this.phonePose(n); if (n.scratch) this.scratchPose(n, T); this.drawCone(n); }
      this.sweatStep(dt);
      // censored: a jittering pixel block on his hips, on the line from his hips to the camera (hidden while he's in the water)
      const m = this.mosaic; m.s.visible = !this.wearing && P.y > -0.25 && this.outOfBath && !P.hidden && !this.gotMawashi;
      if (m.s.visible) {
        m.t -= dt;
        if (m.t <= 0) { m.t = 0.1; const g = m.cv.getContext('2d'), sk = ['#e9b894', '#d9a07c', '#f0c8a8', '#c98a6a', '#e0ac88'];
          g.clearRect(0, 0, 8, 5); for (let y = 0; y < 5; y++) for (let x = 0; x < 8; x++) { if ((x === 0 || x === 7) && Math.random() < 0.6) continue; g.fillStyle = sk[(Math.random() * sk.length) | 0]; g.fillRect(x, y, 1, 1); }
          m.s.material.map.needsUpdate = true; }
        const s = v.s, hip = (this._hip || (this._hip = new THREE.Vector3())).set(0, CENSOR.y * s, 0);
        v.body.updateWorldMatrix(true, false); v.body.localToWorld(hip); const to = this.cam.position.clone().sub(hip).normalize();
        const pop = m.pop > 0 ? (m.pop -= dt, 1 + Math.sin(Math.max(0, m.pop) / 0.5 * Math.PI) * 0.6) : 1;
        m.s.position.copy(hip).addScaledVector(to, 0.95 * s); m.s.scale.set(CENSOR.w * s * pop, CENSOR.h * s * pop, 1);
      }
      for (const sp of this.marks) if (sp.visible) { const u = sp.userData, k = (T * 0.9) % 1;
        u.ar.position.y = 2.3 + Math.abs(Math.sin(T * 3.2)) * 0.22; u.ring.scale.setScalar(0.8 + 0.35 * k); u.ring.material.opacity = 0.85 * (1 - k * k); }
      if (this.water) this.water.position.y = Math.sin(T * 1.3) * 0.01;
      for (const b of this.buckets) if (b.wet && b.state === 'floor') { b.m.position.y = b.ty + Math.sin(T * 1.6 + b.x) * 0.03; b.m.rotation.z = 0.2 + Math.sin(T * 1.1 + b.z) * 0.08; }
      this.fx.update(dt); this.fx.updateWater && this.fx.updateWater(dt);
      // camera: high, behind, following (as in the campaign), up the stairs with him; closer for the ending
      const CF = this.camFocus; this.camT.lerp(CF ? new THREE.Vector3(CF.x, CF.y || 0, CF.z) : new THREE.Vector3(this.over ? P.x + 2.2 : clamp(P.x * 0.8, -18, 18), Math.max(0, P.y), P.z - (this.over ? 0.6 : 2.6)), 1 - Math.exp(-dt * (CF ? 2.5 : 4)));
      this.camD = (this.camD || 15) + ((CF && CF.dist ? CF.dist : this.over ? 9 : 15) - (this.camD || 15)) * Math.min(1, dt * 2); const dist = this.camD, sh = this.flash ? this.flash * 0.25 : 0; this.flash = Math.max(0, (this.flash || 0) - dt * 2);
      this.camH = (this.camH || 0.64) + ((CF && CF.h ? CF.h : 0.64) - (this.camH || 0.64)) * Math.min(1, dt * 2); const ch = this.camH, cz = Math.sqrt(Math.max(0.05, 1 - ch * ch));
      this.cam.position.set(this.camT.x + (Math.random() - 0.5) * sh, this.camT.y + dist * ch, this.camT.z + dist * cz * (CF && CF.flip ? -1 : 1));   // (a cutscene can look from the far side)
      this.cam.lookAt(this.camT.x, this.camT.y + 0.6, this.camT.z); this.cam.updateMatrixWorld();
      this.flat.lights.aim(this.camT.x, this.camT.z - 3);
      if ((this.cvN = (this.cvN || 0) + 1) % 30 === 1) S.Flat.convert(this.scene, { pastel: 0.6 });
      this.R.r.shadowMap.enabled = true;
      this.R.r.render(this.scene, this.cam);
      this.drawHud(dt);
    }
    drawCone(n) {
      const a = n.a, N = 22, P = this.P, hide = (SAFE[roomAt(P.x, P.z)] && !n.raid) || n.busy || Math.abs(a.y - P.y) > 1.6 || a.st !== 'free';
      n.cone.visible = !hide; if (hide) return;
      const range = this.range(n), pos = new Float32Array((N + 2) * 3), y = a.y + 0.03; pos[0] = a.x; pos[1] = y; pos[2] = a.z;
      for (let i = 0; i <= N; i++) { const t = a.f - n.half + (2 * n.half) * i / N, L = this.reach(a.x, a.z, t, range); pos[(i + 1) * 3] = a.x + Math.cos(t) * L; pos[(i + 1) * 3 + 1] = y; pos[(i + 1) * 3 + 2] = a.z + Math.sin(t) * L; }
      const idx = []; for (let i = 1; i <= N; i++) idx.push(0, i + 1, i);
      const g = n.cone.geometry; g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setIndex(idx); g.computeBoundingSphere();
      const k = clamp(n.alarm, 0, 1); n.cone.material.color.setRGB(1, 0.81 - 0.5 * k, 0.23 - 0.1 * k); n.cone.material.opacity = 0.36 + 0.24 * k;
    }

    // ============================================================== HUD
    buildHud() {
      const h = this.hud = document.createElement('div'); h.id = 'stealthHud';
      h.innerHTML = '<style>#stealthHud{position:fixed;inset:0;pointer-events:none;z-index:6;font-family:"Barlow Condensed",sans-serif;color:#3a3440}' +
        '#stealthHud .st-obj{position:absolute;left:24px;top:20px;background:rgba(255,250,240,.9);padding:8px 14px;border-radius:10px;font-weight:700;font-size:20px;letter-spacing:.02em;max-width:60vw}' +
        '#stealthHud .st-ko{position:fixed;inset:0;z-index:5;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(30,24,36,.28);color:#fffaf0;text-shadow:0 4px 0 rgba(40,30,50,.35);opacity:0;pointer-events:none;transition:opacity .3s}#stealthHud .st-ko.on{opacity:1}#stealthHud .st-ko b{font:400 64px "Dela Gothic One",sans-serif;letter-spacing:2px}#stealthHud .st-ko i{font-style:normal;font-size:24px;opacity:.8;margin-top:6px}#stealthHud .st-obj.chase b{color:#cf3a3a}' +
        '#stealthHud .st-bonus{position:absolute;left:24px;top:64px;display:flex;gap:6px;pointer-events:none}#stealthHud .st-bonus i{font:700 13px "Barlow Condensed",sans-serif;font-style:normal;letter-spacing:0.06em;padding:3px 8px 2px;border-radius:999px;background:rgba(255,250,240,0.9);color:#2e7d4c;transition:all .3s}#stealthHud .st-bonus i.off{color:#a49c94;background:rgba(255,250,240,0.55);text-decoration:line-through}#stealthHud .st-bonus i.pop{transform:scale(1.25);color:#d8262e}#stealthHud .st-hp{top:96px!important}' +
        '#stealthHud .st-map{position:absolute;left:20px;bottom:20px;width:150px;height:150px;border-radius:50%;box-shadow:0 0 0 4px rgba(255,250,240,0.9),0 4px 12px rgba(40,30,40,0.25);pointer-events:none}' +
        '#stealthHud.sf .st-bonus,#stealthHud.sf .st-map,#stealthHud.sf .st-obj,#stealthHud.sf .st-hp,#stealthHud.sf .st-think,#stealthHud.sf .st-help,#stealthHud.sf .st-safe,#stealthHud.sf .st-stam{display:none!important}' +
        '#stealthHud .st-sf{position:absolute;left:0;right:0;top:0;bottom:0;pointer-events:none;display:none;font-family:"Barlow Condensed",sans-serif}#stealthHud.sf .st-sf{display:block}' +
        '#stealthHud .st-sf .bars{position:absolute;left:3%;right:3%;top:18px;display:flex;align-items:flex-start;gap:14px}' +
        '#stealthHud .st-sf .bar{flex:1;height:30px;background:#2a2430;border:4px solid #f4efe6;border-radius:6px;position:relative;overflow:hidden}' +
        '#stealthHud .st-sf .bar i{position:absolute;top:0;bottom:0;background:#f2cf4a}#stealthHud .st-sf .bar b{position:absolute;top:0;bottom:0;background:#d8262e}' +
        '#stealthHud .st-sf .bar.l i,#stealthHud .st-sf .bar.l b{right:0}#stealthHud .st-sf .bar.r i,#stealthHud .st-sf .bar.r b{left:0}' +
        '#stealthHud .st-sf .tm{width:84px;height:62px;margin-top:-6px;background:#2a2430;border:4px solid #f4efe6;border-radius:10px;color:#f2cf4a;font:800 44px "Barlow Condensed",sans-serif;text-align:center;line-height:60px;font-style:italic}' +
        '#stealthHud .st-sf .nm{position:absolute;top:60px;font:800 26px "Barlow Condensed",sans-serif;font-style:italic;letter-spacing:0.08em;color:#fffaf0;background:rgba(42,36,48,0.85);padding:1px 12px 0}#stealthHud .st-sf .nm.l{left:3%}#stealthHud .st-sf .nm.r{right:3%}' +
        '#stealthHud .st-sf .pips{position:absolute;top:96px;font:700 24px "Barlow Condensed",sans-serif;color:#d8262e;letter-spacing:6px}#stealthHud .st-sf .pips.l{left:3%}#stealthHud .st-sf .pips.r{right:3%}' +
        '#stealthHud .st-sf .big{position:absolute;left:0;right:0;top:34%;text-align:center;font:800 118px "Barlow Condensed",sans-serif;font-style:italic;letter-spacing:0.06em;color:#d8262e;text-shadow:none;opacity:0}#stealthHud .st-sf .big.on{opacity:1;animation:sfpop .35s ease-out}@keyframes sfpop{0%{transform:scale(1.9)}100%{transform:scale(1)}}' +
        '#stealthHud .st-sf .keys{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);text-align:center;font:700 22px "Barlow Condensed",sans-serif;color:#fffaf0;background:rgba(42,36,48,0.82);padding:6px 18px 4px;border-radius:8px;white-space:nowrap}' +
        '#stealthHud .st-choice{position:absolute;left:50%;top:52%;transform:translateX(-50%);display:none;text-align:center;background:rgba(42,36,48,0.92);padding:18px 34px 20px;border-radius:14px;color:#fffaf0}#stealthHud .st-choice.on{display:block}' +
        '#stealthHud .st-choice h3{margin:0 0 4px;font:400 26px "Dela Gothic One",sans-serif}#stealthHud .st-choice p{margin:0 0 12px;font:600 19px "Barlow Condensed",sans-serif;opacity:0.85}' +
        '#stealthHud .st-choice button{display:block;width:100%;background:none;border:0;color:rgba(244,239,230,.55);font:700 30px "Barlow Condensed",sans-serif;padding:4px 0;cursor:pointer}#stealthHud .st-choice button.sel{color:#f4efe6;border-left:5px solid #d8262e;padding-left:16px}' +
        '#stealthHud .st-sub{position:absolute;left:50%;bottom:96px;transform:translateX(-50%);width:max-content;max-width:94vw;text-align:center;pointer-events:none;display:none}#stealthHud .st-sub .jp{display:inline-block;font:400 24px "Dela Gothic One",sans-serif;color:#fffaf0;background:rgba(34,30,40,0.72);padding:6px 14px 4px;border-radius:10px;letter-spacing:0.04em}#stealthHud .st-sub .en{display:block;margin-top:6px;font:700 19px "Barlow Condensed",sans-serif;color:#fffaf0;text-shadow:0 2px 0 rgba(0,0,0,0.55)}#stealthHud .st-sub .who{color:#f2cf4a;margin-right:8px}' +
        '#stealthHud .st-hp{position:absolute;left:24px;top:76px;font-size:28px;letter-spacing:4px;color:#cf3a3a;text-shadow:0 2px 0 #fffaf0;display:none}#stealthHud .st-hp.chase{animation:hpPulse .5s ease-in-out infinite alternate}@keyframes hpPulse{to{transform:scale(1.12)}}' +
        '#stealthHud .st-obj b{color:#cf5a4a}#stealthHud .st-safe{position:absolute;right:24px;top:20px;background:#a8dcc6;color:#2f4b4a;padding:6px 12px;border-radius:10px;font-weight:800;font-size:18px;display:none}' +
        '#stealthHud .st-think{position:absolute;left:0;top:0;width:max-content;transform:translate(-50%,-100%);background:#fffaf0;border-radius:18px;padding:8px 16px;font-weight:700;font-size:20px;max-width:360px;text-align:center;box-shadow:0 3px 0 rgba(60,50,70,.15);opacity:0;transition:opacity .2s}' +
        '#stealthHud .st-think.on{opacity:1}#stealthHud .st-think:after{content:"";position:absolute;left:50%;bottom:-12px;width:14px;height:14px;border-radius:50%;background:#fffaf0;transform:translateX(-50%)}' +
        '#stealthHud .st-pop{position:absolute;transform:translate(-50%,-100%);font:400 26px "Dela Gothic One",sans-serif;color:#cf3a3a;white-space:nowrap}' +
        '#stealthHud .st-q{position:absolute;transform:translate(-50%,-100%);font:400 24px "Dela Gothic One",sans-serif;color:#e2a13a}' +
        '#stealthHud .st-stam{position:absolute;width:64px;height:9px;border-radius:6px;background:rgba(255,250,240,.85);transform:translate(-50%,-100%);display:none;padding:2px}#stealthHud .st-stam i{display:block;height:100%;border-radius:4px;background:#84b5ad}#stealthHud .st-stam.tired i{background:#e59d86}' +
        '#stealthHud .st-zzz{position:absolute;display:none;transform:translate(-50%,-100%);font:400 30px "Dela Gothic One",sans-serif;color:#6f8fc8}#stealthHud .st-zzz i{font-style:normal;position:absolute;opacity:0;animation:stz 2.4s linear infinite}' +
        '#stealthHud .st-zzz i:nth-child(2){animation-delay:.8s;font-size:24px}#stealthHud .st-zzz i:nth-child(3){animation-delay:1.6s;font-size:36px}' +
        '@keyframes stz{0%{opacity:0;transform:translate(0,0)}15%{opacity:1}100%{opacity:0;transform:translate(40px,-90px)}}' +
        '#stealthHud .st-wake{position:absolute;left:50%;bottom:16%;transform:translateX(-50%);display:none;font:400 26px "Dela Gothic One",sans-serif;color:#2f2a38;background:rgba(255,250,240,.85);padding:8px 22px;border-radius:14px;animation:stw 1.6s ease-in-out infinite}' +
        '@keyframes stw{0%,100%{opacity:.55}50%{opacity:1}}' +
        '#stealthHud .st-oni{position:absolute;right:24px;top:64px;background:#fffaf0;color:#3a3440;padding:6px 14px;border-radius:12px;font:400 24px "Dela Gothic One",sans-serif;display:none}' +
        '#stealthHud .st-help{position:absolute;left:190px;right:24px;bottom:18px;font-size:16px;opacity:.8;background:rgba(255,250,240,.75);padding:4px 10px;border-radius:8px}' +
        '#stealthHud .st-jump{position:absolute;left:0;top:0;bottom:0;width:min(620px,92vw);display:none;pointer-events:auto;background:linear-gradient(90deg,rgba(30,24,36,.95),rgba(30,24,36,.7) 85%,transparent);padding:44px 50px;color:#f4efe6;overflow:auto;z-index:50}#stealthHud .st-jump.on{display:block}#stealthHud .st-jump h2{margin:0 0 10px;font:800 44px "Barlow Condensed",sans-serif}#stealthHud .st-jump button{display:block;background:none;border:0;color:rgba(244,239,230,.55);font:700 24px "Barlow Condensed",sans-serif;padding:3px 0;cursor:pointer;text-align:left}#stealthHud .st-jump button.sel{color:#f4efe6;padding-left:18px;border-left:5px solid #d8262e}#stealthHud .st-jump .k{font:500 16px "Barlow Condensed",sans-serif;opacity:.6}'
        + '#stealthHud .st-pause,#stealthHud .st-over{position:absolute;left:0;top:0;bottom:0;width:min(520px,92vw);display:none;pointer-events:auto;background:linear-gradient(90deg,rgba(30,24,36,.92),rgba(30,24,36,.6) 80%,transparent);padding:80px 60px;color:#f4efe6}' +
        '#stealthHud .st-over{left:auto;right:0;text-align:right;background:linear-gradient(270deg,rgba(30,24,36,.92),rgba(30,24,36,.6) 80%,transparent)}#stealthHud .st-over button{margin-left:auto}' +
        '#stealthHud .on{display:block}#stealthHud h2{font:400 56px "Dela Gothic One",sans-serif;margin:0 0 20px}#stealthHud h2:before{content:attr(data-jp);display:block;font-size:15px;letter-spacing:.5em;color:#d8262e;margin-bottom:8px}' +
        '#stealthHud .st-pause button,#stealthHud .st-over button{display:block;background:none;border:0;color:rgba(244,239,230,.55);font:700 30px "Barlow Condensed",sans-serif;padding:6px 0;cursor:pointer}' +
        '#stealthHud .st-pause button.sel{color:#f4efe6;padding-left:22px;border-left:5px solid #d8262e}#stealthHud .st-over button.sel{color:#f4efe6;padding-right:22px;border-right:5px solid #d8262e}#stealthHud .k{font-size:15px;opacity:.6}</style>' +
        '<canvas class="st-map" width="180" height="180"></canvas><div class="st-sf"></div><div class="st-choice"></div><div class="st-sub"></div><div class="st-bonus"></div><div class="st-obj"></div><div class="st-oni"></div><div class="st-zzz"><i>z</i><i>z</i><i>Z</i></div><div class="st-wake">PRESS ANY KEY</div><div class="st-stam"><i></i></div><div class="st-hp"></div><div class="st-ko"></div><div class="st-safe">SAFE: everyone\'s naked here</div><div class="st-think"></div><div class="st-pops"></div><div class="st-help">WASD move (they hear you close by) · hold I tiptoe (silent, tiring) · I by a cart or toilet stall: hide (hold I + a direction: climb out that side, silently) · I in the bath: duck under · J punch (knocks them out) · J at a wall: knock, a noise to lure them · hold L + direction charge (loud · take a run-up to smash things) · K use / pick up / throw / push a cart · hold K smash what you hold · Esc pause</div>' +
        '<div class="st-pause"><h2 data-jp="一時停止">PAUSED</h2><button data-c="resume">RESUME</button><button data-c="cp">RESTART AT CHECKPOINT</button><button data-c="jump">JUMP TO A GOAL (testing)</button><button data-c="retry">RESTART LEVEL</button><button data-c="quit">QUIT TO TITLE</button><p class="k">W / S choose · Enter or J select</p></div><div class="st-jump"><h2 data-jp="跳">JUMP TO</h2><button data-j="locker">1 · Find your locker</button><button data-j="key">2 · Check the wash bucket for the key</button><button data-j="smash">3 · Smash the locker (charge)</button><button data-j="towel">4 · Get a towel (laundry)</button><button data-j="storage">5 · Upstairs: smash the box heap</button><button data-j="box">6 · Put on the box (storage)</button><button data-j="exit">7 · Out the front door (in the box)</button><button data-j="kitchen">8 · The back way: the kitchen</button><button data-j="onigiri">9 · Eat the onigiri</button><button data-j="toilet">10 · The toilet</button><button data-j="paper">11 · Fetch toilet paper</button><button data-j="toilet2">12 · Wipe (back to the stall)</button><button data-j="bossgo">13 · The boss rises (the phone call is done)</button><button data-j="fight">14 · Boss: Street Fighter bout</button><button data-j="sumo">15 · Boss: sumo bout</button><button data-j="escape">16 · Escape (the kitchen back door)</button><p class="k">W / S choose · Enter or J go · Esc back</p></div><div class="st-over"></div>';
      document.body.appendChild(h);
      h.addEventListener('click', (e) => { const b = e.target.closest('[data-c]'); if (b) this.command(b.dataset.c); });
      this.pops = [];
    }
    el(q) { return this.hud.querySelector(q); }
    objective(t) { const h = 'GOAL: <b>' + t + '</b>'; if (this.chaseObj) this.chaseObj = h; else this.el('.st-obj').innerHTML = h; }   // (mid-chase: shown once he's lost them)
    think(t, dur) {
      const e = this.el('.st-think');
      // quick exclamations (*CRASH*, slips...) never churn the bubble: they don't replace one that has only just appeared
      if ((dur || 2.5) <= 1.6 && this.thinkT > 0 && (this.t - (this.thinkAt || -9)) < 1.2) return;
      if (e.textContent === t && this.thinkT > 0) { this.thinkT = Math.max(this.thinkT, dur || 2.5); return; }
      this.thinkT = dur || 2.5; this.thinkAt = this.t; e.textContent = t; e.classList.add('on');
    }
    popAt(a, txt, dur, big) {
      // (a fresh shout on someone already shouting replaces it; never a stack of overlapping bubbles over one head)
      for (let i = this.pops.length - 1; i >= 0; i--) { const o = this.pops[i]; if (o.a === a || (o.a && a && Math.hypot((o.a.x || 0) - (a.x || 0), (o.a.z || 0) - (a.z || 0)) < 0.6)) { o.d.remove(); this.pops.splice(i, 1); } }
      if (this.pops.length >= 4) { const o = this.pops.shift(); o.d.remove(); }
      const d = document.createElement('div'); d.className = 'st-pop'; d.textContent = txt; if (!big) d.style.fontSize = '22px'; this.el('.st-pops').appendChild(d); this.pops.push({ d, a, t: dur || 1.4 }); }
    clearPops() { for (const o of this.pops) o.d.remove(); this.pops.length = 0; }
    project(x, y, z) { const v = new THREE.Vector3(x, y, z).project(this.cam); return { x: (v.x * 0.5 + 0.5) * innerWidth, y: (-v.y * 0.5 + 0.5) * innerHeight }; }
    drawHud(dt) {
      const P = this.P, s = this.view.s;
      if (this.asleep) { const q = this.project(P.x + 0.4, P.y + 2.2 * s, P.z), z = this.el('.st-zzz'); z.style.left = q.x + 'px'; z.style.top = q.y + 'px'; }
      const sb = this.el('.st-stam');
      if (P.stam < 0.999 && !this.over) { const q = this.project(P.x, P.y + 2.55 * s, P.z); sb.style.display = 'block'; sb.style.left = q.x + 'px'; sb.style.top = q.y + 'px'; sb.firstChild.style.width = (P.stam * 100) + '%'; sb.classList.toggle('tired', P.tired); }
      else sb.style.display = 'none';
      this.chaseGoal(); const hp = this.el('.st-hp'), ch = this.chasing(), hits = this.hits || 0;   // three hits and he's out: ♥♥♥
      hp.style.display = (ch || hits) && !this.over ? 'block' : 'none'; hp.textContent = '♥'.repeat(3 - Math.min(3, hits)) + '♡'.repeat(Math.min(3, hits)); hp.classList.toggle('chase', ch);
      const sf = this.el('.st-safe'), hunt = this.stage === 'bathhide';
      sf.style.display = SAFE[roomAt(P.x, P.z)] && !this.over ? 'block' : 'none';
      if (sf._hunt !== hunt) { sf._hunt = hunt; sf.textContent = hunt ? 'NOT SAFE: they\'re looking for whoever did that' : 'SAFE: everyone\'s naked here'; sf.style.background = hunt ? '#f2c4b6' : ''; sf.style.color = hunt ? '#7a2e22' : ''; }
      if (this.thinkT > 0) { this.thinkT -= dt; const p = this.project(P.x, P.y + 2.9 * s, P.z), e = this.el('.st-think');
        const tp = this.thinkPos || (this.thinkPos = { x: p.x, y: p.y }), k = Math.min(1, dt * 14); tp.x += (p.x - tp.x) * k; tp.y += (p.y - tp.y) * k;
        e.style.left = Math.round(tp.x) + 'px'; e.style.top = Math.round(tp.y) + 'px'; if (this.thinkT <= 0) e.classList.remove('on'); }
      else this.thinkPos = null;
      this.pops = this.pops.filter((q) => { q.t -= dt; const p = this.project(q.a.x, (q.a.y || 0) + 2.6 + (1.4 - q.t) * 0.3, q.a.z); q.d.style.left = p.x + 'px'; q.d.style.top = p.y + 'px'; if (q.t <= 0) { q.d.remove(); return false; } return true; });
      if (!this.qs) this.qs = this.npcs.map(() => { const d = document.createElement('div'); d.className = 'st-q'; this.el('.st-pops').appendChild(d); return d; });
      this.npcs.forEach((n, i) => { const d = this.qs[i]; if (n.alarm > 0.08 && !this.freeze) { const p = this.project(n.a.x, n.a.y + 2.4, n.a.z); d.style.left = p.x + 'px'; d.style.top = p.y + 'px'; d.textContent = n.alarm > 0.6 ? '?!' : '?'; d.style.display = ''; d.style.transform = 'translate(-50%,-100%) scale(' + (0.8 + n.alarm * 0.6) + ')'; } else d.style.display = 'none'; });
    }
    markMenu(q, i) { this.el(q).querySelectorAll('button').forEach((b, k) => b.classList.toggle('sel', k === i)); }
    setPause(on) { this.paused = on; this.el('.st-pause').classList.toggle('on', on); if (on) { this.pauseI = 0; this.markMenu('.st-pause', 0); } }
    command(c) {
      if (c === 'resume') this.setPause(false);
      else if (c === 'jump') { this.jumpOn = true; this.jumpI = 0; this.el('.st-jump').classList.add('on'); this.markMenu('.st-jump', 0); }
      else if (c === 'cp') { this.setPause(false); if (this.P.stallHide !== undefined) this.stallOut(); this.respawn(); this.grace = 2.5; }
      else if (c === 'retry') { const g = this.g; this.stop(); g.camp = new S.Stealth(g); g.camp.start(); }
      else if (c === 'quit') this.g.endCampaign();
    }
    onKey(e) {
      if (this.jumpOn) {
        if (e.repeat) return true; const bs = this.el('.st-jump').querySelectorAll('button');
        if (e.code === 'ArrowUp' || e.code === 'KeyW') this.jumpI = (this.jumpI - 1 + bs.length) % bs.length;
        else if (e.code === 'ArrowDown' || e.code === 'KeyS') this.jumpI = (this.jumpI + 1) % bs.length;
        else if (e.code === 'Enter' || e.code === 'NumpadEnter' || e.code === 'KeyJ') { const k = bs[this.jumpI].dataset.j; this.jumpOn = false; this.el('.st-jump').classList.remove('on'); this.setPause(false); this.jumpTo(k); return true; }
        else if (e.code === 'Escape') { this.jumpOn = false; this.el('.st-jump').classList.remove('on'); return true; }
        this.markMenu('.st-jump', this.jumpI); bs[this.jumpI].scrollIntoView({ block: 'nearest' }); return true;
      }
      if (this.choiceCb) {   // the boss's question
        if (e.repeat) return true; const bs = this.el('.st-choice').querySelectorAll('button');
        if (e.code === 'ArrowUp' || e.code === 'KeyW' || e.code === 'ArrowDown' || e.code === 'KeyS') { this.choiceI = (this.choiceI + 1) % bs.length; bs.forEach((b, k) => b.classList.toggle('sel', k === this.choiceI)); }
        else if (e.code === 'Enter' || e.code === 'NumpadEnter' || e.code === 'KeyJ' || e.code === 'Space') { const cb = this.choiceCb, i = this.choiceI; this.choiceCb = null; this.el('.st-choice').classList.remove('on'); this.keys = {}; cb(i); }
        return true;
      }
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
  // the bathhouse kit, fetched once (in the background soon after start-up, so the test level opens at once)
  let bathP = null;
  S.loadBathKit = () => bathP || (bathP = new Promise((res) => new THREE.GLTFLoader().load('assets/models/bathhouse_kit.glb' + (LY.v ? '?v=' + LY.v : ''), (gl) => res(S.Flat.kit(gl.scene)), undefined, () => { bathP = null; res(null); })));
  addEventListener('load', () => setTimeout(() => { if (window.KUMITE_STYLE === 'anime' && S.preloadKits) S.preloadKits(); S.loadBathKit(); }, 2000));
})();
