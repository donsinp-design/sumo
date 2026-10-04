/* Kumite — verlet ragdoll. Drives any joint hierarchy (our procedural fighters, or a
   rigged skeleton) from a 15-point physics body: throws, knockdowns, deaths and dangling
   when grabbed. The body is simulated in world space; each bone is then turned so it
   points where its physics segment points. */
(function () {
  'use strict';
  const S = window.S;
  const G = 18; // same gravity as the game's thrown bodies
  const NAMES = ['pelvis', 'neck', 'head', 'shL', 'elL', 'haL', 'shR', 'elR', 'haR', 'hipL', 'knL', 'ftL', 'hipR', 'knR', 'ftR'];
  const RAD = { pelvis: 0.2, neck: 0.16, head: 0.22, shL: 0.12, shR: 0.12, elL: 0.08, elR: 0.08, haL: 0.08, haR: 0.08, hipL: 0.12, hipR: 0.12, knL: 0.09, knR: 0.09, ftL: 0.08, ftR: 0.08 };
  const MASS = { pelvis: 3, neck: 2.5, head: 1.2, shL: 1.5, shR: 1.5, hipL: 1.5, hipR: 1.5, elL: 0.6, elR: 0.6, haL: 0.4, haR: 0.4, knL: 0.9, knR: 0.9, ftL: 0.6, ftR: 0.6 };
  const V = () => new THREE.Vector3();
  const tv = V(), tv2 = V(), tq = new THREE.Quaternion(), tq2 = new THREE.Quaternion(), tm = new THREE.Matrix4(), tm2 = new THREE.Matrix4();

  class Ragdoll {
    /* joints: { name: Object3D } giving each point's position (see NAMES)
       bones: list (parent before child) of { obj, aim: [from, to] } or { obj, frame: [down, up, left, right] } */
    constructor(joints, bones) {
      this.joints = joints; this.bones = bones; this.on = false;
      this.p = NAMES.map((n) => ({ n, x: V(), o: V(), r: RAD[n], w: 1 / MASS[n], pin: null }));
      this.ix = {}; NAMES.forEach((n, i) => (this.ix[n] = i));
      this.cons = []; this.built = false;
    }
    P(n) { return this.p[this.ix[n]]; }
    _build() {
      const c = (a, b, k, min) => { const A = this.P(a), B = this.P(b); this.cons.push({ A, B, L: A.x.distanceTo(B.x), k: k || 1, min }); };
      // torso: a braced box so it stays rigid
      const torso = ['pelvis', 'neck', 'shL', 'shR', 'hipL', 'hipR'];
      for (let i = 0; i < torso.length; i++) for (let j = i + 1; j < torso.length; j++) c(torso[i], torso[j], 1);
      c('head', 'neck', 1); c('head', 'shL', 0.6); c('head', 'shR', 0.6); c('head', 'pelvis', 0.3);
      for (const s of ['L', 'R']) {
        c('sh' + s, 'el' + s, 1); c('el' + s, 'ha' + s, 1); c('sh' + s, 'ha' + s, 1, true); // min: elbow can't fold flat
        c('hip' + s, 'kn' + s, 1); c('kn' + s, 'ft' + s, 1); c('hip' + s, 'ft' + s, 1, true);
        c('pelvis', 'kn' + s, 0.15, true); // thighs can't fold into the belly
      }
      for (const C of this.cons) if (C.min) C.L *= C.A.n.startsWith('sh') ? 0.45 : 0.55;
      this.built = true;
    }
    // read the current animated pose and start simulating from it
    start(vel, opt) {
      opt = opt || {};
      for (const b of this.bones) b.obj.updateMatrixWorld(true);
      for (const q of this.p) { this.joints[q.n].getWorldPosition(q.x); q.pin = null; }
      if (!this.built) this._build();
      else for (const C of this.cons) { const L = C.A.x.distanceTo(C.B.x); C.L = C.min ? L * (C.A.n.startsWith('sh') ? 0.45 : 0.55) : L; }
      // rest orientation of each bone against its segment
      for (const b of this.bones) {
        b.obj.getWorldQuaternion(b.q0 = b.q0 || new THREE.Quaternion());
        if (b.aim) { b.d0 = (b.d0 || V()).subVectors(this.P(b.aim[1]).x, this.P(b.aim[0]).x).normalize(); }
        else { b.m0 = this._basis(b.frame, b.m0 || new THREE.Matrix4()); }
      }
      for (const q of this.p) q.o.copy(q.x);
      this.kick(vel, opt);
      this.on = true; this.age = 0; this.rest = 0;
    }
    // add velocity: v for the whole body, push for the upper body (topples it), spin around the travel direction
    kick(vel, opt) {
      opt = opt || {};
      const dt = 1 / 120, v = vel || V(), spin = opt.spin || 0, push = opt.push, pel = this.P('pelvis').x;
      for (const q of this.p) {
        if (opt.legs && !/kn|ft/.test(q.n)) continue;
        tv.copy(v);
        if (push) { const h = Math.max(0, q.x.y - 0.5); tv.addScaledVector(push, h * 1.2); }
        if (spin) { const h = q.x.y - pel.y; tv.x += opt.ax * h * spin; tv.z += opt.az * h * spin; tv.y -= Math.abs(spin) * 0.15 * h; }
        q.o.addScaledVector(tv, -dt);
      }
    }
    stop() { this.on = false; }
    _basis(f, m) {
      const d = this.P(f[0]).x, u = this.P(f[1]).x, l = this.P(f[2]).x, r = this.P(f[3]).x;
      const Y = tv.subVectors(u, d).normalize(), X = tv2.subVectors(r, l), Z = V();
      Z.crossVectors(X, Y).normalize(); X.crossVectors(Y, Z).normalize();
      return m.makeBasis(X, Y, Z);
    }
    // world-space simulation. collide(p) can push a point out of walls.
    step(dt, collide, anchor) {
      if (!this.on) return;
      this.age += dt;
      const n = Math.max(1, Math.ceil(dt * 120)), h = dt / n;
      for (let s = 0; s < n; s++) {
        for (const q of this.p) {
          if (q.pin) { q.o.copy(q.x); q.x.lerp(q.pin, 0.5); continue; }
          const onGround = q.x.y <= q.r + 0.002;
          const fr = onGround ? 0.82 : 0.995; // ground friction: bodies slide a little then stop
          const vx = (q.x.x - q.o.x) * fr, vy = (q.x.y - q.o.y) * 0.995, vz = (q.x.z - q.o.z) * fr;
          q.o.copy(q.x);
          q.x.x += vx; q.x.y += vy - G * h * h; q.x.z += vz;
        }
        for (let it = 0; it < 6; it++) {
          for (const C of this.cons) {
            const A = C.A, B = C.B; tv.subVectors(B.x, A.x); const d = tv.length() || 1e-6;
            if (C.min && d >= C.L) continue;
            const wa = A.pin ? 0 : A.w, wb = B.pin ? 0 : B.w, ws = wa + wb; if (!ws) continue;
            const diff = ((d - C.L) / d) * C.k;
            A.x.addScaledVector(tv, (diff * wa) / ws); B.x.addScaledVector(tv, (-diff * wb) / ws);
          }
          this._knees();
          for (const q of this.p) {
            if (q.x.y < q.r) { q.x.y = q.r; }
            if (collide) collide(q.x, q.r);
          }
        }
        // stay with the gameplay body (it handles walls, gates and knockback)
        if (anchor) {
          const pel = this.P('pelvis').x, dx = anchor.x - pel.x, dz = anchor.z - pel.z, d = Math.hypot(dx, dz), lim = 0.55;
          if (d > lim) { const k = (d - lim) / d; for (const q of this.p) { q.x.x += dx * k; q.x.z += dz * k; q.o.x += dx * k; q.o.z += dz * k; } }
        }
      }
    }
    // knees only bend forwards: a hinge check against the hips' facing
    _knees() {
      const hl = this.P('hipL').x, hr = this.P('hipR').x, pel = this.P('pelvis').x, nk = this.P('neck').x;
      const X = tv.subVectors(hr, hl), Y = tv2.subVectors(nk, pel), Fw = V().crossVectors(X, Y).normalize();
      for (const s of ['L', 'R']) {
        const hp = this.P('hip' + s).x, kn = this.P('kn' + s), ft = this.P('ft' + s).x;
        const mid = V().addVectors(hp, ft).multiplyScalar(0.5), off = V().subVectors(kn.x, mid).dot(Fw);
        if (off < 0.02) kn.x.addScaledVector(Fw, (0.02 - off) * 0.5);
      }
    }
    // pin points (for being held): { name: Vector3 } or null
    pin(map) { for (const q of this.p) q.pin = map && map[q.n] ? map[q.n] : null; }
    // turn the bones to match the simulated body
    apply(hips, root) {
      if (!this.on) return;
      root.updateMatrixWorld(true);
      // hips sit on the pelvis point
      tv.copy(this.P('pelvis').x); hips.parent.worldToLocal(tv); hips.position.copy(tv);
      for (const b of this.bones) {
        let R;
        if (b.aim) { tv.subVectors(this.P(b.aim[1]).x, this.P(b.aim[0]).x).normalize(); R = tq.setFromUnitVectors(b.d0, tv); }
        else { this._basis(b.frame, tm); tm2.copy(b.m0).transpose(); tm.multiply(tm2); R = tq.setFromRotationMatrix(tm); }
        tq2.copy(R).multiply(b.q0); // desired world rotation
        b.obj.parent.getWorldQuaternion(tq); tq.invert();
        b.obj.quaternion.copy(tq.multiply(tq2));
        b.obj.updateMatrixWorld(true);
      }
    }
    // which way the chest faces once settled: +1 face up, -1 face down
    facing() {
      const hl = this.P('hipL').x, hr = this.P('hipR').x, pel = this.P('pelvis').x, nk = this.P('neck').x;
      const X = V().subVectors(hr, hl), Y = V().subVectors(nk, pel); return V().crossVectors(X, Y).y >= 0 ? 1 : -1;
    }
    speed() { let s = 0; for (const q of this.p) s = Math.max(s, q.x.distanceTo(q.o)); return s * 120; }
  }
  S.Ragdoll = Ragdoll;
})();
