'use strict';
// CHARACTERS: real skinned bodies for the market workers (Kenney "animated characters", CC0), painted with
// worker outfits, toon-shaded with ink outlines. They are driven by the procedural rig in campaign.js
// (keyframed moves and the ragdoll): each frame the rig's bone directions are copied onto the skeleton.
(function () {
  const C = S.Chars = { ready: false };
  const SH = () => S.R3.SH;
  const VS = `
    #include <common>
    #include <skinning_pars_vertex>
    varying vec3 vN; varying vec3 vV; varying vec3 vIC; varying vec2 vUv;
    void main(){
      #include <beginnormal_vertex>
      #include <skinbase_vertex>
      #include <skinnormal_vertex>
      #include <begin_vertex>
      #include <skinning_vertex>
      vIC = vec3(1.0); vUv = uv;
      vec4 mv = modelViewMatrix * vec4(transformed, 1.0);
      vN = normalize(normalMatrix * objectNormal); vV = -mv.xyz;
      gl_Position = projectionMatrix * mv;
    }`;
  const OLVS = `
    #include <common>
    #include <skinning_pars_vertex>
    uniform float uThick; uniform float uOL;
    void main(){
      #include <beginnormal_vertex>
      #include <skinbase_vertex>
      #include <skinnormal_vertex>
      #include <begin_vertex>
      #include <skinning_vertex>
      vec4 mv = modelViewMatrix * vec4(transformed, 1.0);
      vec3 nv = normalize(normalMatrix * objectNormal);
      mv.xyz += nv * uThick * uOL * (0.5 + 0.035 * -mv.z);
      gl_Position = projectionMatrix * mv;
    }`;
  function skinToon(map) {
    const m = S.toon(0xffffff, { map, shade: 0x9a86a6, rimAmt: 0.55, rim: 0xfff0d8 });
    m.vertexShader = VS; return m;
  }
  let olMat = null;
  const outline = () => olMat || (olMat = new THREE.ShaderMaterial({
    uniforms: { uThick: { value: 0.022 }, uOL: SH().uOL, uColor: { value: new THREE.Color(0x1c0f15) }, uAlpha: { value: 1 } },
    vertexShader: OLVS, fragmentShader: S.R3.OL_FS, side: THREE.BackSide,
  }));

  C.load = function () {
    if (C.loading) return C.loading;
    C.loading = new Promise((res) => {
      if (!THREE.GLTFLoader) { res(); return; }
      new THREE.GLTFLoader().load('assets/models/worker.glb', (g) => {
        C.gltf = g; C.heads = []; let n = 0;
        const done = () => { if (++n === 5) { C.ready = true; res(); } };
        for (let i = 0; i < 5; i++) { const im = new Image(); im.onload = done; im.onerror = done; im.src = 'assets/models/head' + i + '.png'; C.heads.push(im); }
      }, undefined, () => res());
    });
    return C.loading;
  };

  // ---------------------------------------------------------------- outfits, painted onto the model's texture layout
  const css = (c) => '#' + new THREE.Color(c).getHexString();
  const shadeC = (c, k) => { const o = new THREE.Color(c); o.multiplyScalar(k); return '#' + o.getHexString(); };
  const texCache = {};
  function outfit(kind, K, head, fat) {
    const key = kind + head + (fat ? 'f' : '');
    if (texCache[key]) return texCache[key];
    const cv = document.createElement('canvas'); cv.width = cv.height = 1024; const c = cv.getContext('2d');
    const skin = ['#e9b894', '#d9a47e', '#f0c4a0', '#c98e68', '#e2ae88'][head], shirt = css(K.shirt), apron = css(K.apron), band = css(K.band);
    const pants = kind === 'commander' ? '#1a1a22' : ['#2a2e44', '#33302a', '#24303a'][head % 3], boots = head % 2 ? '#f2f2ec' : '#1e2230';
    c.fillStyle = skin; c.fillRect(0, 0, 1024, 1024);
    // head: one of five faces / haircuts, then the headband (hachimaki) round the forehead
    if (C.heads[head] && C.heads[head].complete) c.drawImage(C.heads[head], 0, 0);
    if (!K.cap) { c.fillStyle = band; c.fillRect(0, 148, 640, 26); c.fillStyle = 'rgba(0,0,0,0.25)'; c.fillRect(0, 170, 640, 4); c.fillStyle = band; c.fillRect(0, 140, 60, 50); c.fillRect(580, 140, 60, 50); }
    else { c.fillStyle = '#2a5a9a'; c.fillRect(0, 0, 640, 165); c.fillStyle = '#1a3a6a'; c.fillRect(0, 155, 640, 14); }
    if (K.glasses) { c.strokeStyle = '#141018'; c.lineWidth = 7; for (const x of [292, 352]) { c.beginPath(); c.arc(x, 226, 22, 0, 7); c.stroke(); } c.beginPath(); c.moveTo(314, 224); c.lineTo(330, 224); c.stroke(); }
    // angry brows over the eyes
    c.fillStyle = '#1a1014'; c.save(); c.translate(292, 196); c.rotate(0.25); c.fillRect(-22, -5, 44, 9); c.restore(); c.save(); c.translate(352, 196); c.rotate(-0.25); c.fillRect(-22, -5, 44, 9); c.restore();
    // shirt (torso block), neck opening
    c.fillStyle = shirt; c.fillRect(150, 486, 340, 538);
    c.fillStyle = shadeC(K.shirt, 0.8); for (let y = 500; y < 1024; y += 40) c.fillRect(150, y, 340, 3); // fabric folds
    c.fillStyle = skin; c.beginPath(); c.ellipse(320, 742, 40, 34, 0, 0, 7); c.fill();
    if (K.coat) { c.fillStyle = '#f6eddc'; c.fillRect(300, 770, 40, 254); c.fillStyle = '#f2c14e'; c.font = '60px "Dela Gothic One", sans-serif'; c.textAlign = 'center'; c.fillText('祭', 320, 640); }
    // apron: the front of the torso runs from the neck (y 742) down to the waist (y 1024); the back is above it
    if (!K.coat) {
      c.fillStyle = apron; c.fillRect(222, 812, 196, 212); c.fillRect(256, 776, 128, 44);
      c.strokeStyle = 'rgba(0,0,0,0.3)'; c.lineWidth = 4; c.strokeRect(224, 814, 192, 210);
      c.fillStyle = 'rgba(255,255,255,0.16)'; c.fillRect(232, 822, 14, 190);
      c.strokeStyle = apron; c.lineWidth = 16; c.beginPath(); c.moveTo(262, 780); c.lineTo(290, 742); c.moveTo(378, 780); c.lineTo(350, 742);
      c.moveTo(290, 742); c.lineTo(410, 500); c.moveTo(350, 742); c.lineTo(230, 500); c.stroke();
      c.fillStyle = apron; c.fillRect(150, 486, 340, 18);
    }
    // sleeves: rolled up to the elbow (forearms bare), a rolled cuff
    const sleeve = K.coat ? 120 : 52;
    c.fillStyle = shirt; c.fillRect(160 - sleeve, 640, sleeve, 200); c.fillRect(480, 640, sleeve, 200);
    c.fillStyle = shadeC(K.shirt, 0.7); c.fillRect(160 - sleeve - 8, 640, 12, 200); c.fillRect(480 + sleeve - 4, 640, 12, 200);
    // trousers and rubber boots
    c.fillStyle = pants; c.fillRect(624, 760, 400, 264);
    c.fillStyle = 'rgba(0,0,0,0.25)'; for (let x = 640; x < 1024; x += 64) c.fillRect(x, 760, 3, 200);
    c.fillStyle = boots; c.fillRect(624, 930, 400, 94); c.fillRect(630, 0, 196, 530); c.fillRect(826, 0, 198, 130);
    c.fillStyle = 'rgba(0,0,0,0.3)'; c.fillRect(624, 930, 400, 6);
    
    const t = new THREE.CanvasTexture(cv); t.flipY = false; t.anisotropy = 4;
    return (texCache[key] = t);
  }

  // ---------------------------------------------------------------- one character instance
  // pairs: skeleton bone <- procedural joints. The rig's sd=-1 side is the model's Right side (x<0).
  const DRIVE = {
    Hips: { frame: ['pelvis', 'neck', 'hipL', 'hipR'] }, Chest: { frame: ['pelvis', 'neck', 'shL', 'shR'] }, Head: { frame: ['neck', 'head', 'shL', 'shR'] },
    RightArm: { aim: ['shL', 'elL'] }, RightForeArm: { aim: ['elL', 'haL'] }, LeftArm: { aim: ['shR', 'elR'] }, LeftForeArm: { aim: ['elR', 'haR'] },
    RightUpLeg: { aim: ['hipL', 'knL'] }, RightLeg: { aim: ['knL', 'ftL'] }, LeftUpLeg: { aim: ['hipR', 'knR'] }, LeftLeg: { aim: ['knR', 'ftR'] },
  };
  const CHILD = { RightArm: 'RightForeArm', RightForeArm: 'RightHand', LeftArm: 'LeftForeArm', LeftForeArm: 'LeftHand', RightUpLeg: 'RightLeg', RightLeg: 'RightFoot', LeftUpLeg: 'LeftLeg', LeftLeg: 'LeftFoot' };
  const v1 = new THREE.Vector3(), v2 = new THREE.Vector3(), v3 = new THREE.Vector3(), q1 = new THREE.Quaternion(), m1 = new THREE.Matrix4(), mInv = new THREE.Matrix4();

  class Body {
    constructor(scene, kind, K, fat, head) {
      this.scene = scene;
      const src = C.gltf.scene, root = THREE.SkeletonUtils.clone(src);
      this.wrap = new THREE.Group(); this.wrap.add(root); scene.add(this.wrap);
      const sc = 0.9 / 0.8; this.sc = sc; root.scale.set(sc * (fat ? 1.32 : 1), sc, sc * (fat ? 1.25 : 1));
      let sk = null; root.traverse((o) => { if (o.isSkinnedMesh) sk = o; });
      this.mesh = sk; sk.frustumCulled = false;
      sk.material = skinToon(outfit(kind, K, head, fat)); this.mat = sk.material;
      const ol = new THREE.SkinnedMesh(sk.geometry, outline()); ol.frustumCulled = false; ol.bind(sk.skeleton, sk.bindMatrix); sk.parent.add(ol);
      // bones and their rest pose in model space (relative to `root`)
      this.bones = {}; for (const b of sk.skeleton.bones) this.bones[b.name] = b;
      root.updateMatrixWorld(true);
      mInv.copy(root.matrixWorld).invert();
      this.rest = {};
      const modelQ = (o) => { o.matrixWorld.decompose(v1, q1, v2); const rq = new THREE.Quaternion(); root.matrixWorld.decompose(v3, rq, v2); return rq.invert().multiply(q1.clone()); };
      const modelP = (o) => o.getWorldPosition(new THREE.Vector3()).applyMatrix4(mInv);
      this.order = sk.skeleton.bones.slice().sort((a, b) => depth(a) - depth(b));
      for (const b of this.order) {
        const r = this.rest[b.name] = { q: modelQ(b), p: modelP(b), lq: b.quaternion.clone(), pq: b.parent ? modelQ(b.parent) : new THREE.Quaternion() };
        if (CHILD[b.name]) r.dir = modelP(this.bones[CHILD[b.name]]).sub(r.p).normalize();
      }
      const hp = this.bones.Hips.parent; hp.updateMatrixWorld(true);
      this.hipsParentInv = new THREE.Matrix4().copy(hp.matrixWorld).invert().multiply(root.matrixWorld); // model -> hips-parent local
      this.parentRestQ = modelQ(hp);
      if (this.bones.Head) this.bones.Head.scale.setScalar(0.62); // adult proportions, not a big-headed toy
      for (const n of ['LeftHand', 'RightHand']) if (this.bones[n]) this.bones[n].scale.setScalar(0.62);
      this.root = root; this.Q = {};
      function depth(o) { let d = 0; while (o.parent) { d++; o = o.parent; } return d; }
    }
    // copy the rig: J = { name: world position } of the procedural joints, rootObj = the rig's root group
    drive(J, rootObj, visible) {
      this.wrap.visible = visible;
      if (!visible) return;
      this.wrap.position.copy(rootObj.position); this.wrap.quaternion.copy(rootObj.quaternion);
      this.wrap.updateMatrixWorld(true);
      mInv.copy(this.root.matrixWorld).invert();
      const P = {}; for (const k in J) P[k] = J[k].clone().applyMatrix4(mInv); // into model space
      const Q = this.Q;
      for (const b of this.order) {
        const r = this.rest[b.name], d = DRIVE[b.name];
        const pq = b.parent && Q[b.parent.name] ? Q[b.parent.name] : r.pq;
        let q;
        if (d && d.aim) { v1.subVectors(P[d.aim[1]], P[d.aim[0]]).normalize(); q = new THREE.Quaternion().setFromUnitVectors(r.dir, v1).multiply(r.q); }
        else if (d && d.frame) {
          const Y = v1.subVectors(P[d.frame[1]], P[d.frame[0]]).normalize(), X = v2.subVectors(P[d.frame[3]], P[d.frame[2]]), Z = v3.crossVectors(X, Y).normalize(); X.crossVectors(Y, Z).normalize();
          q = new THREE.Quaternion().setFromRotationMatrix(m1.makeBasis(X, Y, Z)).multiply(r.q);
        } else q = pq.clone().multiply(r.lq);
        Q[b.name] = q;
        b.quaternion.copy(pq.clone().invert().multiply(q));
      }
      // pelvis position
      this.bones.Hips.position.copy(P.pelvis).applyMatrix4(this.hipsParentInv);
    }
    flash(col, amt) { this.mat.uniforms.uFlashCol.value.set(col); this.mat.uniforms.uFlash.value = amt; }
    dispose() { this.scene.remove(this.wrap); }
  }
  C.Body = Body;
})();
// load early so the market's workers are ready by the time the campaign starts
if (document.readyState === 'complete') S.Chars.load(); else window.addEventListener('load', () => S.Chars.load());
