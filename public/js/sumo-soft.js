'use strict';
// THE SOFT SUMO: the rounded, skinned sumo (tools/blender/sumo_soft.py -> sumo_game.py) worn over a WrestlerView.
// The view keeps doing all the animation work (stance, steps, IK arms and legs, falls, poses); each frame its
// joints are copied onto the skeleton: torso and head rotations as they are, every limb bone aimed along the view's
// limb segment. The view's own primitive body is hidden; accessories on its head (masks) ride on the soft head.
(function () {
  let tpl = null, rest = null, clips = [];
  const ready = new Promise((res) => {
    if (!THREE.GLTFLoader) return res(null);
    new THREE.GLTFLoader().load('assets/models/sumo_game.glb', (g) => { tpl = g.scene; clips = g.animations || []; prep(); res(tpl); }, undefined, () => res(null));
  });
  const key = (n) => n.replace(/[^A-Za-z]/g, '').toLowerCase();       // 'upper_arm.L' / 'upper_armL' -> 'upperarml'
  const NAMES = ['hips', 'spine', 'belly', 'chest', 'neck', 'head', 'shoulderl', 'upperarml', 'forearml', 'handl', 'shoulderr', 'upperarmr', 'forearmr', 'handr',
    'thighl', 'shinl', 'footl', 'thighr', 'shinr', 'footr'];
  function bonesOf(root) {
    const B = {};
    root.traverse((o) => { if (o.isBone) B[key(o.name)] = o; });
    return B;
  }
  // rest data, model space: world quaternion, head position, and each bone's rest direction (towards its child)
  function prep() {
    tpl.updateMatrixWorld(true);
    const B = bonesOf(tpl), inv = new THREE.Matrix4().copy(tpl.matrixWorld).invert();
    rest = { q: {}, p: {}, dir: {}, parentQ: null };
    for (const n of NAMES) {
      const b = B[n]; if (!b) continue;
      const m = new THREE.Matrix4().multiplyMatrices(inv, b.matrixWorld), p = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
      m.decompose(p, q, s); rest.q[n] = q; rest.p[n] = p;
    }
    const d = (a, b) => rest.p[b].clone().sub(rest.p[a]).normalize();
    for (const sd of ['l', 'r']) {
      rest.dir['upperarm' + sd] = d('upperarm' + sd, 'forearm' + sd); rest.dir['forearm' + sd] = d('forearm' + sd, 'hand' + sd);
      rest.dir['thigh' + sd] = d('thigh' + sd, 'shin' + sd); rest.dir['shin' + sd] = d('shin' + sd, 'foot' + sd);
    }
    rest.leg = rest.p.thighl.distanceTo(rest.p.shinl) + rest.p.shinl.distanceTo(rest.p.footl);
    const hp = B.hips.parent; hp.updateMatrixWorld(true);
    rest.parentQ = new THREE.Quaternion(); new THREE.Matrix4().multiplyMatrices(inv, hp.matrixWorld).decompose(new THREE.Vector3(), rest.parentQ, new THREE.Vector3());
    // the head's size and centre (vertices mostly bound to the head bone), to fit accessories made for the old head
    let hb = null; tpl.traverse((o) => { if (o.isSkinnedMesh && !hb) hb = o; });
    const hi = hb.skeleton.bones.findIndex((b) => key(b.name) === 'head');
    const pos = hb.geometry.attributes.position, ji = hb.geometry.attributes.skinIndex, wi = hb.geometry.attributes.skinWeight;
    const box = new THREE.Box3(), v = new THREE.Vector3(), GET = ['getX', 'getY', 'getZ', 'getW'];
    for (let i = 0; i < pos.count; i++) {
      for (let c = 0; c < 4; c++) if (ji[GET[c]](i) === hi && wi[GET[c]](i) > 0.9) { box.expandByPoint(v.fromBufferAttribute(pos, i).applyMatrix4(hb.matrixWorld).applyMatrix4(inv)); break; }
    }
    rest.headC = box.getCenter(new THREE.Vector3()); rest.headR = box.getSize(new THREE.Vector3()).x / 2;
    // the approved standing pose (Blender 'stance' clip): its arm bones' local rotations, for standing and walking
    rest.stance = {};
    const st = clips.find((c) => /stance/i.test(c.name));
    if (st) for (const tr of st.tracks) { const m = /^(.*)\.quaternion$/.exec(tr.name); if (m) rest.stance[key(m[1])] = new THREE.Quaternion().fromArray(tr.values, 0); }
  }

  // ------------------------------------------------------------------ attach to a WrestlerView
  function attach(view, o) {
    if (!tpl || view.soft) return false;
    o = o || {};
    const M = THREE.SkeletonUtils.clone(tpl), B = bonesOf(M), s = view.s;
    const k = 0.8 * s / rest.leg;                                  // fit the legs exactly to the view's IK legs
    M.scale.setScalar(k); view.root.add(M);
    const mats = [];
    M.traverse((q) => {
      if (!q.isMesh) return;
      q.frustumCulled = false; q.castShadow = true; q.receiveShadow = false; // no self-shadow blotches on the round body
      const ms = Array.isArray(q.material) ? q.material : [q.material];
      const nm = ms.map((m) => {
        const name = (m.name || '').toLowerCase();
        let col = m.color ? m.color.clone().convertLinearToSRGB() : new THREE.Color(1, 1, 1), map = m.map || null;
        if (map) { map.encoding = THREE.LinearEncoding; map.needsUpdate = true; col = new THREE.Color(1, 1, 1); }
        if (name.startsWith('mawashi') && view.arch.belt !== undefined) col = new THREE.Color(view.arch.belt);
        if (name.startsWith('hair') && view.arch.hair !== undefined) col = new THREE.Color(view.arch.hair);   // (the boss's grey topknot)
        const f = S.Flat.mat(col, { map, side: m.side }); f.name = m.name || '';
        mats.push(f); return f;
      });
      q.material = Array.isArray(q.material) ? nm : nm[0];
    });
    for (const b of view.baseMeshes || []) b.visible = false;      // the primitive body goes
    if (o.noBlob && view.shadow) view.shadow.material.opacity = 0;
    view.head.scale.setScalar(rest.headR * k / (0.25 * s));
    view.soft = { M, B, k, mats, tq: new THREE.Quaternion(), q: new THREE.Quaternion(), wq: {}, bodyQ: new THREE.Quaternion(), headQ: new THREE.Quaternion(),
      v: new THREE.Vector3(), a: new THREE.Vector3(), b: new THREE.Vector3(), c: new THREE.Vector3(), m: new THREE.Matrix4() };
    return true;
  }

  // ------------------------------------------------------------------ per frame, after the view's own update
  function drive(view, w) {
    const S_ = view.soft, B = S_.B, k = S_.k, s = view.s, body = view.body, wq = S_.wq, q = S_.q, tq = S_.tq;
    const bodyQ = S_.bodyQ.copy(body.quaternion);
    // squash and stretch, as the view does it to its body
    S_.M.scale.set(k * body.scale.x, k * body.scale.y, k * body.scale.z);
    const set = (n, worldQ, parentQ) => { const b = B[n]; if (!b) return; wq[n] = worldQ; b.quaternion.copy(parentQ).invert().multiply(worldQ); };
    const keep = (n, parent) => { const pq = wq[parent]; set(n, pq.clone().multiply(new THREE.Quaternion().copy(rest.q[parent]).invert().multiply(rest.q[n])), pq); };
    // hips: placed where the view's hips are, turned with the body
    const hipC = S_.v.set(0, -0.1 * s, 0).applyMatrix4(body.matrix);             // root space, between the view's hip joints
    const off = S_.a.copy(rest.p.hips).sub(rest.p.thighl.clone().add(rest.p.thighr).multiplyScalar(0.5)).multiplyScalar(k).applyQuaternion(bodyQ);
    const hp = hipC.add(off).divideScalar(k);                                     // model space (M has no rotation)
    const hb = B.hips, pInv = rest.parentQ.clone().invert();
    hb.position.copy(hp).applyQuaternion(pInv);                                   // the rig node is the hips' parent
    set('hips', bodyQ.clone().multiply(rest.q.hips), rest.parentQ);
    keep('spine', 'hips'); keep('belly', 'spine'); keep('chest', 'spine'); keep('neck', 'chest');
    // the head turns as the view's head does (nod, look)
    S_.headQ.copy(view.head.quaternion);
    set('head', bodyQ.clone().multiply(S_.headQ).multiply(rest.q.head), wq.neck);
    // limbs: aim each bone along the view's segment (minimal turn from its rest direction keeps the twist natural)
    const aim = (n, parent, from, to) => {
      const d = S_.c.copy(to).sub(from); if (d.lengthSq() < 1e-8) return keep(n, parent);
      d.normalize(); tq.setFromUnitVectors(rest.dir[n], d);
      set(n, tq.clone().multiply(rest.q[n]), wq[parent]);
    };
    for (const A of view.arms) {
      const sd = A.sd > 0 ? 'l' : 'r';
      keep('shoulder' + sd, 'chest');
      if (!A.el) continue;
      const sh = S_.a.copy(A.sh).applyMatrix4(body.matrix), el = S_.v.copy(A.el).applyMatrix4(body.matrix), hd = S_.b.copy(A.hand.position).applyMatrix4(body.matrix);
      aim('upperarm' + sd, 'shoulder' + sd, sh, el);
      aim('forearm' + sd, 'upperarm' + sd, el, hd);
      keep('hand' + sd, 'forearm' + sd);
    }
    // tiptoeing: T-rex hands. Palms turned down, wrists drooping forward
    if (w.tiptoe > 0.05) for (const A of view.arms) {
      const sd = A.sd > 0 ? 'l' : 'r'; if (!A.el || !wq['forearm' + sd] || !wq['hand' + sd]) continue;
      const el = S_.v.copy(A.el).applyMatrix4(body.matrix), hd = S_.b.copy(A.hand.position).applyMatrix4(body.matrix);
      const dir = hd.sub(el).normalize(), side = S_.c.set(0, 1, 0).cross(dir).normalize(), kk = w.tiptoe;
      const tw = (S.SoftSumo.trexTw !== undefined ? S.SoftSumo.trexTw : 0) * (A.sd > 0 ? 1 : -1) * kk, dr = (S.SoftSumo.trexDr !== undefined ? S.SoftSumo.trexDr : 1.4) * kk;
      const qd = new THREE.Quaternion().setFromAxisAngle(side, dr).multiply(new THREE.Quaternion().setFromAxisAngle(dir, tw));
      set('hand' + sd, qd.multiply(wq['hand' + sd]), wq['forearm' + sd]);
    }
    // standing and walking: the arms take the approved stance pose (relaxed, a little forward, palms down) and swing
    // gently against the steps; fighting moves blend back to the view's IK arms
    const now = performance.now() / 1000, dtr = Math.min(0.1, now - (S_.tPrev || now)); S_.tPrev = now;
    S_.wA = (S_.wA === undefined ? view.clipArms || 0 : S_.wA) + ((view.clipArms || 0) - (S_.wA || 0)) * Math.min(1, dtr * 9);
    if (S_.wA > 0.001 && rest.stance.upperarml) {
      const spd = Math.min(1, (w.spd || 0) / 3), amp = 0.42 * spd * (view.gaitW || 0), ax = S_.c.set(1, 0, 0).applyQuaternion(bodyQ);
      const blend = (n, parent, extra) => {
        const L = rest.stance[n]; if (!L) return;
        const clipW = wq[parent].clone().multiply(L); if (extra) clipW.premultiply(extra);
        set(n, wq[n].clone().slerp(clipW, S_.wA), wq[parent]);
      };
      for (const sd of ['l', 'r']) {
        const sw = new THREE.Quaternion().setFromAxisAngle(ax, Math.sin(view.gaitPh || 0) * amp * (sd === 'l' ? 1 : -1));
        // bring the upper arms in against his sides (the stance spreads the elbows: from behind that read as wide shoulders)
        const fw = S_.v.set(0, 0, 1).applyQuaternion(bodyQ); sw.multiply(new THREE.Quaternion().setFromAxisAngle(fw, (sd === 'l' ? -1 : 1) * (S.SoftSumo.adduct !== undefined ? S.SoftSumo.adduct : 0.3)));
        blend('shoulder' + sd, 'chest'); blend('upperarm' + sd, 'shoulder' + sd, sw); blend('forearm' + sd, 'upperarm' + sd); blend('hand' + sd, 'forearm' + sd);
      }
    }
    for (const L of view.legs) {
      const sd = L.sd > 0 ? 'l' : 'r', h = L.hp, kn = L.kn, ft = L.ft;
      if (!h) continue;
      aim('thigh' + sd, 'hips', h, kn);
      aim('shin' + sd, 'thigh' + sd, kn, ft);
      const downed = w.st === 'fall' || w.down;
      if (downed) keep('foot' + sd, 'shin' + sd);
      else set('foot' + sd, q.setFromAxisAngle(S_.v.set(0, 1, 0), L.sd * 0.25).clone().multiply(rest.q['foot' + sd]), wq['shin' + sd]);   // feet flat on the floor, toes out
    }
    // hit flash / status tint, from the view's own material
    const u = view.mats[0] && view.mats[0].uniforms;
    if (u) for (const m of S_.mats) m.emissive.copy(u.uFlashCol.value).multiplyScalar(u.uFlash.value * 0.8);
    // the old head group (masks, headbands) sits on the soft head
    const hc = S_.c.copy(rest.headC).sub(rest.p.head).applyQuaternion(wq.head.clone().multiply(rest.q.head.clone().invert()));
    B.head.updateWorldMatrix(true, false);
    const headW = S_.a.setFromMatrixPosition(B.head.matrixWorld);
    view.root.updateMatrixWorld(true);
    const inv = S_.m.copy(body.matrixWorld).invert();
    const centre = headW.add(hc.multiplyScalar(k).applyQuaternion(view.root.quaternion)).applyMatrix4(inv);   // body space
    view.head.position.copy(centre).sub(S_.v.set(0, 0.17 * s * view.head.scale.y, -0.02 * s).applyQuaternion(view.head.quaternion));   // the topknot lifts the box: masks sit on the face, not the brow
  }
  S.SoftSumo = { ready, attach, drive, get loaded() { return !!tpl; } };
})();
