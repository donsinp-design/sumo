'use strict';
// CHARACTERS: anime bodies for the market workers. The models are the VRoid Project's sample avatars
// (AvatarSample A/B/C; their VRoid Hub licence allows commercial use, modification, redistribution and
// violent content, no credit needed), slimmed to web-size GLBs: 512px textures, three face expressions.
// They are toon-shaded with ink outlines, recoloured per enemy role, and driven by the procedural rig in
// campaign.js (keyframed moves and the ragdoll): each frame the rig's bone directions are copied onto
// the skeleton.
(function () {
  const C = S.Chars = { ready: false, models: [] };
  const SH = () => S.R3.SH;
  const FILES = ['assets/models/vroid_c.glb', 'assets/models/vroid_a.glb', 'assets/models/vroid_b.glb']; // c: man, a/b: women
  const VS = `
    #include <common>
    #include <morphtarget_pars_vertex>
    #include <skinning_pars_vertex>
    varying vec3 vN; varying vec3 vV; varying vec3 vIC; varying vec2 vUv;
    void main(){
      #include <beginnormal_vertex>
      #include <morphnormal_vertex>
      #include <skinbase_vertex>
      #include <skinnormal_vertex>
      #include <begin_vertex>
      #include <morphtarget_vertex>
      #include <skinning_vertex>
      vIC = vec3(1.0); vUv = uv;
      vec4 mv = modelViewMatrix * vec4(transformed, 1.0);
      vN = normalize(normalMatrix * objectNormal); vV = -mv.xyz;
      gl_Position = projectionMatrix * mv;
    }`;
  const OLVS = `
    #include <common>
    #include <morphtarget_pars_vertex>
    #include <skinning_pars_vertex>
    uniform float uThick; uniform float uOL;
    void main(){
      #include <beginnormal_vertex>
      #include <morphnormal_vertex>
      #include <skinbase_vertex>
      #include <skinnormal_vertex>
      #include <begin_vertex>
      #include <morphtarget_vertex>
      #include <skinning_vertex>
      vec4 mv = modelViewMatrix * vec4(transformed, 1.0);
      vec3 nv = normalize(normalMatrix * objectNormal);
      mv.xyz += nv * uThick * uOL * (0.5 + 0.035 * -mv.z);
      gl_Position = projectionMatrix * mv;
    }`;
  // toon material for a skinned part: texture alpha cut-out (hair tips, lashes) or blended (eye highlights)
  function skinToon(map, mode, flat) {
    const m = S.toon(0xffffff, { map, shade: flat ? 0xf2f0ee : 0xd6d0cc, rimAmt: flat ? 0 : 0.5, rim: 0xfff0d8 });
    m.vertexShader = VS; m.uniforms.uColor.value.setScalar(flat ? 1.05 : 1.22); // VRoid textures are painted for soft shading: lift them
    m.fragmentShader = m.fragmentShader
      .replace('vec3 tx = uHasMap > 0.5 ? texture2D(uMap, vUv).rgb : vec3(1.0);', 'vec4 t4 = uHasMap > 0.5 ? texture2D(uMap, vUv) : vec4(1.0); if (t4.a < ' + (mode === 'BLEND' ? '0.02' : '0.5') + ') discard; vec3 tx = t4.rgb;')
      .replace('sh *= mix(vec3(1.0), vec3(0.8, 0.76, 1.1), uAnime);', '') // no violet shadow on people: they read as purple at night
      .replace('vec3 col = mix(sh * mix(0.78, 0.66, uAnime), sh, deep);', 'vec3 col = mix(sh * 0.9, sh, deep);')
      .replace('gl_FragColor = vec4(col, uAlpha);', 'gl_FragColor = vec4(col, uAlpha * ' + (mode === 'BLEND' ? 't4.a' : '1.0') + ');');
    if (mode === 'BLEND') { m.transparent = true; m.depthWrite = false; }
    m.side = THREE.DoubleSide;
    return m;
  }
  let olMat = null;
  const outline = () => olMat || (olMat = new THREE.ShaderMaterial({
    uniforms: { uThick: { value: 0.016 }, uOL: SH().uOL, uColor: { value: new THREE.Color(0x1c0f15) }, uAlpha: { value: 1 } },
    vertexShader: OLVS, fragmentShader: S.R3.OL_FS, side: THREE.BackSide,
  }));

  C.load = function () {
    if (C.loading) return C.loading;
    C.loading = new Promise((res) => {
      if (!THREE.GLTFLoader) { res(); return; }
      let n = 0;
      FILES.forEach((f, i) => new THREE.GLTFLoader().load(f, (g) => { C.models[i] = g; if (++n === FILES.length) { C.ready = C.models.every(Boolean); res(); } }, undefined, () => { if (++n === FILES.length) { C.ready = C.models.every(Boolean); res(); } }));
    });
    return C.loading;
  };

  // ---------------------------------------------------------------- outfits: recolour the clothes per enemy role
  const texCache = {};
  function recolour(tex, col, key, keepHi) {
    if (texCache[key]) return texCache[key];
    const im = tex.image, w = Math.min(512, im.width), h = Math.min(512, im.height);
    const cv = document.createElement('canvas'); cv.width = w; cv.height = h; const c = cv.getContext('2d');
    c.drawImage(im, 0, 0, w, h);
    const d = c.getImageData(0, 0, w, h), p = d.data, tc = new THREE.Color(col);
    for (let i = 0; i < p.length; i += 4) {
      const l = (0.3 * p[i] + 0.59 * p[i + 1] + 0.11 * p[i + 2]) / 255, k = Math.min(1.3, 0.62 + l * 0.75);
      const hi = keepHi && l > 0.85 ? (l - 0.85) / 0.15 : 0; // keep bright trims and stitching light
      p[i] = Math.min(255, (tc.r * k * (1 - hi) + l * hi) * 255); p[i + 1] = Math.min(255, (tc.g * k * (1 - hi) + l * hi) * 255); p[i + 2] = Math.min(255, (tc.b * k * (1 - hi) + l * hi) * 255);
    }
    c.putImageData(d, 0, 0);
    const t = new THREE.CanvasTexture(cv); t.flipY = tex.flipY; t.wrapS = tex.wrapS; t.wrapT = tex.wrapT; t.encoding = THREE.LinearEncoding; t.anisotropy = 4;
    return (texCache[key] = t);
  }

  // ---------------------------------------------------------------- one character instance
  // canonical joints <- VRM humanoid bones. The rig's sd=-1 side is the model's Right side.
  const NAMES = { Hips: 'J_Bip_C_Hips', Chest: 'J_Bip_C_Chest', Head: 'J_Bip_C_Head',
    RightArm: 'J_Bip_R_UpperArm', RightForeArm: 'J_Bip_R_LowerArm', RightHand: 'J_Bip_R_Hand', LeftArm: 'J_Bip_L_UpperArm', LeftForeArm: 'J_Bip_L_LowerArm', LeftHand: 'J_Bip_L_Hand',
    RightUpLeg: 'J_Bip_R_UpperLeg', RightLeg: 'J_Bip_R_LowerLeg', RightFoot: 'J_Bip_R_Foot', LeftUpLeg: 'J_Bip_L_UpperLeg', LeftLeg: 'J_Bip_L_LowerLeg', LeftFoot: 'J_Bip_L_Foot' };
  const DRIVE = {
    Hips: { frame: ['pelvis', 'neck', 'hipL', 'hipR'] }, Chest: { frame: ['pelvis', 'neck', 'shL', 'shR'] }, Head: { frame: ['neck', 'head', 'shL', 'shR'] },
    RightArm: { aim: ['shL', 'elL'] }, RightForeArm: { aim: ['elL', 'haL'] }, LeftArm: { aim: ['shR', 'elR'] }, LeftForeArm: { aim: ['elR', 'haR'] },
    RightUpLeg: { aim: ['hipL', 'knL'] }, RightLeg: { aim: ['knL', 'ftL'] }, LeftUpLeg: { aim: ['hipR', 'knR'] }, LeftLeg: { aim: ['knR', 'ftR'] },
  };
  const CHILD = { RightArm: 'RightForeArm', RightForeArm: 'RightHand', LeftArm: 'LeftForeArm', LeftForeArm: 'LeftHand', RightUpLeg: 'RightLeg', RightLeg: 'RightFoot', LeftUpLeg: 'LeftLeg', LeftLeg: 'LeftFoot' };
  const v1 = new THREE.Vector3(), v2 = new THREE.Vector3(), v3 = new THREE.Vector3(), q1 = new THREE.Quaternion(), m1 = new THREE.Matrix4(), mInv = new THREE.Matrix4();
  const HIPS = 1.018, BASE = 0.9 / HIPS, BIG = 1.32; // the rig's hips sit at 0.9; the characters are drawn a third larger so they read at the game camera

  class Body {
    constructor(scene, kind, K, fat, pick) {
      this.scene = scene;
      const female = kind !== 'grappler' && kind !== 'commander' && (pick === 2 || pick === 4), mi = female ? (pick === 2 ? 1 : 2) : 0; // mostly men, some women
      const src = C.models[mi].scene, root = THREE.SkeletonUtils.clone(src);
      this.wrap = new THREE.Group(); scene.add(this.wrap);
      this.inner = new THREE.Group(); this.inner.rotation.y = Math.PI; this.wrap.add(this.inner); // VRM 0.x faces -z
      this.inner.add(root);
      root.scale.set(BASE * BIG * (fat ? 1.3 : 1), BASE * BIG, BASE * BIG * (fat ? 1.22 : 1));
      this.meshes = []; this.mats = []; this.face = null;
      const shirt = K.shirt, pants = kind === 'commander' ? 0x1a1a22 : 0x2a2e44;
      root.traverse((o) => {
        if (!o.isSkinnedMesh) return;
        o.frustumCulled = false;
        const om = o.material, name = om.name || '', mode = om.transparent ? 'BLEND' : om.alphaTest > 0 ? 'MASK' : 'OPAQUE';
        let map = om.map;
        if (map) { map.encoding = THREE.LinearEncoding; map.needsUpdate = true; } // the toon shader works on raw texture colours, like every other map in the game
        if (map && /Tops/.test(name)) map = recolour(map, kind === 'commander' ? 0xc8231d : shirt, 'tops' + mi + kind, true);
        if (map && /Bottoms/.test(name)) map = recolour(map, pants, 'bot' + mi + kind, false);
        if (map && /Shoes/.test(name)) map = recolour(map, pick % 2 ? 0xf2f2ec : 0x22262e, 'shoe' + mi + (pick % 2), false);
        const faceBit = /FACE|EYE/.test(name) && !/SKIN/.test(name);
        const m = skinToon(map, mode, faceBit);
        o.material = m; this.mats.push(m); this.meshes.push(o);
        if (o.morphTargetInfluences && o.morphTargetInfluences.length && !this.face) this.face = o;
        if (!faceBit && mode !== 'BLEND') { const ol = new THREE.SkinnedMesh(o.geometry, outline()); ol.frustumCulled = false; ol.morphTargetInfluences = o.morphTargetInfluences; ol.morphTargetDictionary = o.morphTargetDictionary; ol.bind(o.skeleton, o.bindMatrix); o.parent.add(ol); }
      });
      // bones and their rest pose in model space (relative to `root`)
      this.bones = {}; root.traverse((o) => { if (o.isBone) for (const k in NAMES) if (NAMES[k] === o.name) this.bones[k] = o; });
      this.wrap.updateMatrixWorld(true); // the whole chain, including the 180° turn, before reading the rest pose
      const rootQ = new THREE.Quaternion(); root.matrixWorld.decompose(v3, rootQ, v2); const rootQi = rootQ.clone().invert();
      mInv.copy(root.matrixWorld).invert();
      const modelQ = (o) => { o.matrixWorld.decompose(v1, q1, v2); return rootQi.clone().multiply(q1); };
      const modelP = (o) => o.getWorldPosition(new THREE.Vector3()).applyMatrix4(mInv);
      const depth = (o) => { let d = 0; while (o.parent) { d++; o = o.parent; } return d; };
      this.order = Object.keys(this.bones).map((k) => this.bones[k]).sort((a, b) => depth(a) - depth(b));
      this.rest = {};
      for (const k of Object.keys(this.bones)) {
        const b = this.bones[k], r = this.rest[k] = { q: modelQ(b), p: modelP(b), lq: b.quaternion.clone(), pq: modelQ(b.parent) };
        if (CHILD[k]) r.dir = modelP(this.bones[CHILD[k]]).sub(r.p).normalize();
        b.userData.canon = k;
      }
      // driven bones must also carry their undriven parents (spine, neck, shoulders) as they were at rest
      this.restLocal = new Map(); root.traverse((o) => { if (o.isBone) this.restLocal.set(o, o.quaternion.clone()); });
      const hp = this.bones.Hips.parent; hp.updateMatrixWorld(true);
      this.hipsParentInv = new THREE.Matrix4().copy(hp.matrixWorld).invert().multiply(root.matrixWorld);
      this.yawFix = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI); // the rig's standing frame, seen from the model
      // a headband (hachimaki) on the role's colour, knotted at the back
      if (false && K.band !== undefined && !K.cap && this.bones.Head) { // (off: VRoid hair volumes swallow it)
        const bm = S.toon(K.band, { shade: new THREE.Color(K.band).multiplyScalar(0.5), rimAmt: 0.4 });
        const band = S.R3.mesh(new THREE.TorusGeometry(0.105, 0.017, 6, 28), bm, 0.008); band.rotation.x = Math.PI / 2 + 0.25; band.position.set(0, 0.07, 0.008); band.scale.set(1.08, 1.18, 1);
        this.bones.Head.add(band);
        const knot = S.R3.mesh(new THREE.SphereGeometry(0.022, 8, 6), bm, 0.006); knot.position.set(0, 0.085, 0.125); this.bones.Head.add(knot);
      }
      // relaxed hands: fingers half curled toward the palm, thumb tucked (VRoid ships them flat, straight from the T-pose)
      root.traverse((o) => {
        const m = o.isBone && /J_Bip_([LR])_(Index|Middle|Ring|Little|Thumb)(\d)/.exec(o.name); if (!m) return;
        const sg = m[1] === 'L' ? 1 : -1, j = +m[3];
        if (m[2] === 'Thumb') { o.rotation.y += sg * -0.35 * (j === 1 ? 1 : 0.5); o.rotation.z += sg * 0.2; }
        else o.rotation.z += sg * [0.75, 0.95, 0.7][j - 1] * (m[2] === 'Index' ? 0.8 : 1);
      });
      this.root = root; this.Q = new Map(); this.expr = -1;
    }
    // copy the rig: J = { name: world position } of the procedural joints, rigRoot = the rig's root group
    drive(J, rigRoot, visible, grounded) {
      this.wrap.visible = visible;
      if (!visible) return;
      this.wrap.position.copy(rigRoot.position); this.wrap.quaternion.copy(rigRoot.quaternion);
      this.wrap.updateMatrixWorld(true);
      // rig positions into model space, at the rig's own scale (the BIG factor then enlarges the result)
      m1.copy(this.root.matrixWorld); mInv.copy(m1).invert();
      const P = {}; for (const k in J) { P[k] = J[k].clone().sub(this.wrap.position).multiplyScalar(BIG).add(this.wrap.position).applyMatrix4(mInv); }
      const Q = this.Q;
      for (const b of this.order) {
        const k = b.userData.canon, r = this.rest[k], d = DRIVE[k];
        // parent's model-space rotation: driven parents from this frame, undriven chains from their rest pose
        let pq = r.pq;
        if (b.parent) { let a = b.parent; const chain = []; while (a && a.isBone && !a.userData.canon) { chain.push(a); a = a.parent; } if (a && a.userData.canon && Q.has(a)) { pq = Q.get(a).clone(); for (let i = chain.length - 1; i >= 0; i--) pq.multiply(this.restLocal.get(chain[i])); } }
        let q;
        if (d && d.aim) { v1.subVectors(P[d.aim[1]], P[d.aim[0]]).normalize(); q = new THREE.Quaternion().setFromUnitVectors(r.dir, v1).multiply(r.q); }
        else if (d && d.frame) {
          const Y = v1.subVectors(P[d.frame[1]], P[d.frame[0]]).normalize(), X = v2.subVectors(P[d.frame[3]], P[d.frame[2]]), Z = v3.crossVectors(X, Y).normalize(); X.crossVectors(Y, Z).normalize();
          q = new THREE.Quaternion().setFromRotationMatrix(m1.makeBasis(X, Y, Z)).multiply(this.yawFix).multiply(r.q);
        } else q = pq.clone().multiply(r.lq);
        Q.set(b, q);
        b.quaternion.copy(pq.clone().invert().multiply(q));
      }
      this.bones.Hips.position.copy(P.pelvis).applyMatrix4(this.hipsParentInv);
      // plant the feet: the lower ankle sits at its rest height (the mocap performers' proportions differ from the model's)
      if (grounded) {
        this.root.updateMatrixWorld(true);
        const yL = this.bones.LeftFoot.getWorldPosition(v1).y, yR = this.bones.RightFoot.getWorldPosition(v2).y, ground = this.wrap.position.y + this.rest.LeftFoot.p.y * this.root.scale.y;
        const want = Math.min(yL, yR) - ground; this.drop = (this.drop || 0) + (want - (this.drop || 0)) * 0.35;
        v3.set(0, -this.drop, 0); const hp = this.bones.Hips.parent; hp.updateMatrixWorld(true);
        const a = this.bones.Hips.getWorldPosition(new THREE.Vector3()).add(v3); hp.worldToLocal(a); this.bones.Hips.position.copy(a);
      } else this.drop = 0;
    }
    // 0 angry (default), 1 surprised (hit), 2 eyes shut (down / out)
    setFace(i) {
      if (!this.face || i === this.expr) return; this.expr = i;
      for (const o of this.meshes) if (o.morphTargetInfluences && o.morphTargetInfluences.length >= 3) { o.morphTargetInfluences.fill(0); o.morphTargetInfluences[i] = 1; }
    }
    flash(col, amt) { for (const m of this.mats) { m.uniforms.uFlashCol.value.set(col); m.uniforms.uFlash.value = amt; } }
    dispose() { this.scene.remove(this.wrap); }
  }
  C.Body = Body; C.BIG = BIG;
})();
// load early so the market's workers are ready by the time the campaign starts
if (document.readyState === 'complete') S.Chars.load(); else window.addEventListener('load', () => S.Chars.load());
