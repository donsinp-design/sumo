'use strict';
// Cel-shaded renderer: toon shader + inverted-hull outlines, procedural wrestlers,
// dohyo, crowd, referee, dust / impact effects, camera.
(function () {
  const R = S.RING_R;
  const clamp = S.clamp;
  const LIGHT_W = new THREE.Vector3(-0.5, 0.85, 0.42).normalize();
  const RIM_W = new THREE.Vector3(0.6, 0.35, -0.75).normalize();
  const LIGHT_ANIME = new THREE.Vector3(-0.85, 0.5, 0.35).normalize(); // anime fighters light from the side: a clear lit half and shadow half
  const SH = { uLight: { value: new THREE.Vector3() }, uRimDir: { value: new THREE.Vector3() }, uAnime: { value: 0 }, uOL: { value: 1 } }; // uAnime: the anime look (KUMITEGAME / ART STYLE)

  // ------------------------------------------------------------------ shaders
  const TOON_VS = `
    varying vec3 vN; varying vec3 vV; varying vec3 vIC; varying vec2 vUv;
    void main(){
      vec4 p = vec4(position,1.0); vec3 n = normal;
      vIC = vec3(1.0); vUv = uv;
      #ifdef USE_INSTANCING
      p = instanceMatrix * p; n = mat3(instanceMatrix) * n;
      #endif
      #ifdef USE_INSTANCING_COLOR
      vIC = instanceColor;
      #endif
      vec4 mv = modelViewMatrix * p;
      vN = normalize(normalMatrix * n); vV = -mv.xyz;
      gl_Position = projectionMatrix * mv;
    }`;
  const TOON_FS = `
    uniform vec3 uColor; uniform vec3 uShade; uniform vec3 uRim; uniform vec3 uLight; uniform vec3 uRimDir;
    uniform float uRimAmt; uniform float uSpec; uniform float uFlash; uniform vec3 uFlashCol;
    uniform sampler2D uMap; uniform float uHasMap; uniform float uAlpha; uniform float uAnime;
    varying vec3 vN; varying vec3 vV; varying vec3 vIC; varying vec2 vUv;
    void main(){
      vec3 n = normalize(vN); vec3 v = normalize(vV);
      vec3 tx = uHasMap > 0.5 ? texture2D(uMap, vUv).rgb : vec3(1.0);
      vec3 base = uColor * vIC * tx, sh = uShade * vIC * tx;
      // anime: brighter lit side, cool violet shadow, a razor-sharp terminator
      sh *= mix(vec3(1.0), vec3(0.8, 0.76, 1.1), uAnime);
      float d = dot(n, uLight);
      float lit = smoothstep(0.0, mix(0.04, 0.012, uAnime), d);
      float deep = smoothstep(-0.5, -0.46, d);
      vec3 col = mix(sh * mix(0.78, 0.66, uAnime), sh, deep);
      col = mix(col, base, lit);
      float fres = 1.0 - max(dot(n, v), 0.0);
      float rim = smoothstep(mix(0.58, 0.6, uAnime), mix(0.62, 0.615, uAnime), fres) * smoothstep(-0.15, 0.2, dot(n, uRimDir));
      col = mix(col, uRim, min(1.0, rim * uRimAmt * mix(1.0, 1.5, uAnime)));
      vec3 h = normalize(uLight + v);
      col += uSpec * smoothstep(0.955, 0.965, dot(n, h));
      col = mix(col, uFlashCol, uFlash);
      gl_FragColor = vec4(col, uAlpha);
    }`;
  const OL_VS = `
    uniform float uThick; uniform float uOL;
    void main(){
      vec4 p = vec4(position,1.0); vec3 n = normal;
      #ifdef USE_INSTANCING
      p = instanceMatrix * p; n = mat3(instanceMatrix) * n;
      #endif
      vec4 mv = modelViewMatrix * p;
      vec3 nv = normalize(normalMatrix * n);
      mv.xyz += nv * uThick * uOL * (0.5 + 0.035 * -mv.z);
      gl_Position = projectionMatrix * mv;
    }`;
  const OL_FS = `uniform vec3 uColor; uniform float uAlpha; void main(){ gl_FragColor = vec4(uColor, uAlpha); }`;

  function toon(color, o) {
    o = o || {};
    const c = new THREE.Color(color);
    const shade = o.shade !== undefined ? new THREE.Color(o.shade) : c.clone().multiply(new THREE.Color(0.5, 0.42, 0.62));
    return new THREE.ShaderMaterial({
      uniforms: {
        uColor: { value: c }, uShade: { value: shade }, uRim: { value: new THREE.Color(o.rim || 0xfff0d8) },
        uRimAmt: { value: o.rimAmt !== undefined ? o.rimAmt : 0.55 }, uSpec: { value: o.spec || 0 },
        uFlash: { value: 0 }, uFlashCol: { value: new THREE.Color(0xffffff) },
        uMap: { value: o.map || null }, uHasMap: { value: o.map ? 1 : 0 }, uAlpha: { value: 1 },
        uLight: SH.uLight, uRimDir: SH.uRimDir, uAnime: SH.uAnime,
      },
      vertexShader: TOON_VS, fragmentShader: TOON_FS,
    });
  }
  const olCache = {};
  function outlineMat(th, color) {
    const key = th + ':' + (color || 0);
    if (!olCache[key]) {
      olCache[key] = new THREE.ShaderMaterial({
        uniforms: { uThick: { value: th }, uOL: SH.uOL, uColor: { value: new THREE.Color(color || 0x1c0f15) }, uAlpha: { value: 1 } },
        vertexShader: OL_VS, fragmentShader: OL_FS, side: THREE.BackSide,
      });
    }
    return olCache[key];
  }
  function mesh(geo, mat, th, olColor) {
    const m = new THREE.Mesh(geo, mat);
    if (th === undefined) th = 0.022;
    if (th > 0) m.add(new THREE.Mesh(geo, outlineMat(th, olColor)));
    return m;
  }
  S.toon = toon; S.R3 = { mesh: (...a) => mesh(...a), canvasTex: (...a) => canvasTex(...a), GEO: null, SH, OL_FS };

  const GEO = {
    sphere: new THREE.SphereGeometry(1, 28, 18),
    sphereLo: new THREE.SphereGeometry(1, 14, 10),
    box: new THREE.BoxGeometry(1, 1, 1),
  };

  // pattern textures for cosmetics: solid / stripe / dots / sun / check / bolt / wave / scales / grid / tiger
  const patCache = {};
  function patDraw(g, W, H, pat, c1, c2) {
    g.fillStyle = c1; g.fillRect(0, 0, W, H); g.fillStyle = c2; g.strokeStyle = c2;
    switch (pat) {
      case 'stripe': for (let x = 0; x < W; x += 32) g.fillRect(x, 0, 10, H); break;
      case 'dots': for (let y = 8; y < H; y += 24) for (let x = (y / 24 % 2) * 12 + 8; x < W; x += 24) { g.beginPath(); g.arc(x, y, 5, 0, 7); g.fill(); } break;
      case 'sun': g.beginPath(); g.arc(W / 2, H / 2, H * 0.32, 0, 7); g.fill(); break;
      case 'check': for (let y = 0; y < H; y += 16) for (let x = ((y / 16) % 2) * 16; x < W; x += 32) g.fillRect(x, y, 16, 16); break;
      case 'bolt': g.lineWidth = 6; g.beginPath(); for (let x = 0; x <= W; x += 24) g.lineTo(x, (x / 24) % 2 ? H * 0.25 : H * 0.75); g.stroke(); break;
      case 'wave': g.lineWidth = 4; for (let y = 10; y < H + 20; y += 22) for (let x = 0; x < W + 30; x += 30) { g.beginPath(); g.arc(x, y, 13, Math.PI, 0); g.stroke(); } break;
      case 'scales': g.lineWidth = 3; for (let y = 0; y < H + 20; y += 14) for (let x = ((y / 14) % 2) * 12; x < W + 24; x += 24) { g.beginPath(); g.arc(x, y, 12, 0, Math.PI); g.stroke(); } break;
      case 'grid': g.lineWidth = 2; for (let x = 0; x < W; x += 20) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); } for (let y = 0; y < H; y += 20) { g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); } break;
      case 'tiger': g.lineWidth = 9; for (let x = 0; x < W; x += 36) { g.beginPath(); g.moveTo(x, 0); g.quadraticCurveTo(x + 18, H / 2, x + 4, H); g.stroke(); } break;
    }
  }
  S.patDraw = patDraw;
  function patTex(pat, c1, c2) {
    const k = pat + c1 + c2;
    if (!patCache[k]) { patCache[k] = canvasTex(256, 64, (g, W, H) => patDraw(g, W, H, pat, c1, c2)); patCache[k].wrapS = patCache[k].wrapT = THREE.RepeatWrapping; }
    return patCache[k];
  }
  function canvasTex(w, h, draw) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    draw(c.getContext('2d'), w, h);
    const t = new THREE.CanvasTexture(c);
    t.anisotropy = 4;
    return t;
  }

  // ------------------------------------------------------------------ IK utils
  const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _c = new THREE.Vector3(), _Y = new THREE.Vector3(0, 1, 0);
  function ik(root, tip, l1, l2, pole, mid) { // tip is modified to the reachable point
    const d = _a.copy(tip).sub(root);
    let L = d.length();
    L = clamp(L, 0.05, l1 + l2 - 0.002);
    d.normalize();
    tip.copy(root).addScaledVector(d, L);
    const a = (l1 * l1 - l2 * l2 + L * L) / (2 * L);
    const h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
    const pp = _b.copy(pole).addScaledVector(d, -pole.dot(d));
    if (pp.lengthSq() < 1e-6) pp.set(0, 0, 1);
    pp.normalize();
    mid.copy(root).addScaledVector(d, a).addScaledVector(pp, h);
  }
  function seg(m, p, q) {
    m.position.copy(p).add(q).multiplyScalar(0.5);
    _c.copy(q).sub(p).normalize();
    m.quaternion.setFromUnitVectors(_Y, _c);
  }
  const lerpA = (a, b, k) => [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
  const mir = (a) => [-a[0], a[1], a[2]];

  // ------------------------------------------------------------------ Wrestler
  class WrestlerView {
    constructor(scene, arch, fx, loadout) {
      const s = this.s = arch.scale;
      this.arch = arch; this.fx = fx; this.scene = scene; this.lo = loadout || S.DEF_EQ;
      this.root = new THREE.Group(); scene.add(this.root);
      this.body = new THREE.Group(); this.body.rotation.order = 'YXZ'; this.root.add(this.body);
      const skin = this.skin = toon(arch.skin, { shade: arch.skinShade, rimAmt: 0.6 });
      const belt = this.belt = toon(arch.belt, { shade: arch.beltShade, spec: 0.22, rimAmt: 0.45 });
      const hair = toon(0x2a1e2c, { shade: 0x0e0a14, spec: 0.18, rim: 0x8fa6e8, rimAmt: 0.5 });
      const ink = toon(0x1a1014, { shade: 0x0b0608, rimAmt: 0 });
      const armM = toon(arch.skin, { shade: arch.skinShade, rimAmt: 0.9, rim: 0xfff6e0 });
      this.mats = [skin, belt, hair, armM];
      const SG = GEO.sphere, th = 0.026;
      const add = (parent, geo, mat, pos, scl, t) => {
        const m = mesh(geo, mat, t === undefined ? th : t);
        m.position.set(pos[0], pos[1], pos[2]); if (scl) m.scale.set(scl[0], scl[1], scl[2]);
        parent.add(m); return m;
      };
      // torso
      add(this.body, SG, skin, [0, 0.16 * s, 0.07 * s], [0.66 * s, 0.6 * s, 0.62 * s]);
      add(this.body, SG, skin, [0, 0.6 * s, -0.02 * s], [0.6 * s, 0.44 * s, 0.5 * s]);
      add(this.body, SG, skin, [0.2 * s, 0.62 * s, 0.24 * s], [0.25 * s, 0.2 * s, 0.2 * s]);
      add(this.body, SG, skin, [-0.2 * s, 0.62 * s, 0.24 * s], [0.25 * s, 0.2 * s, 0.2 * s]);
      for (const sd of [-1, 1]) add(this.body, SG, skin, [sd * 0.5 * s, 0.68 * s, 0], [0.23 * s, 0.21 * s, 0.23 * s]);
      // head
      this.head = new THREE.Group(); this.head.position.set(0, 0.95 * s, 0.1 * s); this.body.add(this.head);
      add(this.head, SG, skin, [0, 0.1 * s, 0], [0.24 * s, 0.26 * s, 0.25 * s]);
      // hair: a cut that hugs the scalp (hairline above the brow, low at the nape, sideburns), and the
      // oicho-mage on top: the ginkgo-leaf topknot, tied with a white cord and folded forward over the crown
      const cap = add(this.head, new THREE.SphereGeometry(1, 30, 18, 0, Math.PI * 2, 0, Math.PI * 0.6), hair, [0, 0.105 * s, -0.008 * s], [0.258 * s, 0.272 * s, 0.262 * s], 0.02);
      cap.rotation.x = -0.55;
      for (const sd of [-1, 1]) add(this.head, SG, hair, [sd * 0.232 * s, 0.07 * s, 0.05 * s], [0.026 * s, 0.075 * s, 0.05 * s], 0.008); // sideburns
      const stem = add(this.head, new THREE.CylinderGeometry(0.036 * s, 0.044 * s, 0.11 * s, 12), hair, [0, 0.31 * s, -0.12 * s], null, 0.012); stem.rotation.x = 0.55;
      const tie = add(this.head, new THREE.TorusGeometry(0.045 * s, 0.012 * s, 6, 14), toon(0xf6f2ea, { shade: 0xa8a0a8 }), [0, 0.3 * s, -0.125 * s], null, 0.006); tie.rotation.x = Math.PI / 2 + 0.55;
      const leaf = add(this.head, SG, hair, [0, 0.37 * s, 0.015 * s], [0.17 * s, 0.038 * s, 0.11 * s], 0.016); leaf.rotation.x = 0.22;
      add(this.head, SG, hair, [0, 0.35 * s, -0.07 * s], [0.06 * s, 0.045 * s, 0.07 * s], 0.012); // the fold where it turns forward
      for (const sd of [-1, 1]) {
        this.eyes = this.eyes || []; this.eyes.push(add(this.head, SG, ink, [sd * 0.085 * s, 0.1 * s, 0.225 * s], [0.03 * s, 0.024 * s, 0.02 * s], 0));
        const br = add(this.head, GEO.box, ink, [sd * 0.09 * s, 0.155 * s, 0.215 * s], [0.085 * s, 0.022 * s, 0.03 * s], 0);
        br.rotation.z = sd * 0.32;
      }
      add(this.head, GEO.box, ink, [0, 0.0, 0.235 * s], [0.07 * s, 0.012 * s, 0.02 * s], 0);
      // mawashi: thick silk wound round several times (proud folds with creases between), the front panel,
      // a folded knot at the back, and the sagari: a fringe of stiff cords tucked under the front
      add(this.body, new THREE.CylinderGeometry(0.66 * s, 0.6 * s, 0.34 * s, 48, 1), belt, [0, -0.04 * s, 0.035 * s], [1.0, 1.0, 0.95]);
      for (const [y, r] of [[0.115, 0.668], [0.005, 0.657], [-0.105, 0.638]]) {
        const ring = add(this.body, new THREE.TorusGeometry(r * s, 0.034 * s, 8, 48), belt, [0, (y - 0.04) * s, 0.035 * s], [1.0, 0.95, 1.0], 0.012); ring.rotation.x = Math.PI / 2;
      }
      // folded cloth: rounded slabs, not boxes
      const cloth = (w, h, d) => { const r = Math.min(w, h) * 0.28, sh = new THREE.Shape(); sh.moveTo(-w / 2 + r, -h / 2); sh.lineTo(w / 2 - r, -h / 2); sh.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r); sh.lineTo(w / 2, h / 2 - r); sh.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2); sh.lineTo(-w / 2 + r, h / 2); sh.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r); sh.lineTo(-w / 2, -h / 2 + r); sh.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
        const g = new THREE.ExtrudeGeometry(sh, { depth: d * 0.5, bevelEnabled: true, bevelThickness: d * 0.25, bevelSize: d * 0.22, bevelSegments: 3, curveSegments: 5 }); g.translate(0, 0, -d * 0.25); g.computeVertexNormals(); return g; };
      add(this.body, cloth(0.34 * s, 0.3 * s, 0.1 * s), belt, [0, -0.2 * s, 0.52 * s]).rotation.x = -0.28;          // front panel
      add(this.body, cloth(0.28 * s, 0.9 * s, 0.14 * s), belt, [0, -0.28 * s, 0.05 * s]).rotation.x = Math.PI / 2;  // between the legs
      add(this.body, cloth(0.24 * s, 0.44 * s, 0.12 * s), belt, [0, -0.04 * s, -0.66 * s]);                           // the knot: upright fold
      add(this.body, cloth(0.42 * s, 0.12 * s, 0.13 * s), belt, [0, 0.03 * s, -0.69 * s]);                            //   crossed by the wrap
      add(this.body, cloth(0.2 * s, 0.14 * s, 0.1 * s), belt, [0, 0.2 * s, -0.62 * s]).rotation.x = 0.35;             //   its folded top
      add(this.body, cloth(0.16 * s, 0.36 * s, 0.09 * s), belt, [0, -0.25 * s, -0.52 * s]).rotation.x = 0.35;         //   the tail down to the legs
      this.sagari = new THREE.Group(); this.sagari.position.set(0, -0.05 * s, 0.6 * s); this.body.add(this.sagari);
      const sg = new THREE.CylinderGeometry(0.012 * s, 0.009 * s, 1, 5); sg.translate(0, -0.5, 0);
      const tip = new THREE.ConeGeometry(0.014 * s, 0.03 * s, 5); tip.rotateX(Math.PI); tip.translate(0, -0.015 * s, 0);
      for (let k = 0; k < 17; k++) {
        const a = (k / 16 - 0.5) * 1.7, L = (k % 2 ? 0.3 : 0.35) * s;
        const st = mesh(sg, belt, 0.008); st.scale.set(1, L, 1);
        st.position.set(Math.sin(a) * 0.57 * s, 0, (Math.cos(a) - 1) * 0.57 * s + 0.02 * s); st.rotation.set(-0.06, 0, -Math.sin(a) * 0.08);
        const tp = mesh(tip, belt, 0); tp.position.y = -1; tp.scale.set(1, 1 / L, 1); st.add(tp);
        this.sagari.add(st);
      }
      const rope = mesh(new THREE.TorusGeometry(0.57 * s, 0.014 * s, 5, 24, 1.8), belt, 0.006); rope.rotation.set(Math.PI / 2, 0, Math.PI / 2 - 0.9); rope.position.set(0, 0, -0.55 * s); this.sagari.add(rope);
      // limbs
      const capA = new THREE.CapsuleGeometry(0.185 * s, 0.28 * s, 4, 14);
      const capF = new THREE.CapsuleGeometry(0.165 * s, 0.26 * s, 4, 14);
      const capT = new THREE.CapsuleGeometry(0.22 * s, 0.3 * s, 4, 12);
      const capC = new THREE.CapsuleGeometry(0.16 * s, 0.3 * s, 4, 12);
      this.arms = [-1, 1].map((sd) => ({
        sd, sh: new THREE.Vector3(sd * 0.56 * s, 0.68 * s, 0),
        up: add(this.body, capA, armM, [0, 0, 0], null, 0.034), lo: add(this.body, capF, armM, [0, 0, 0], null, 0.034),
        hand: add(this.body, SG, armM, [0, 0, 0], [0.17 * s, 0.15 * s, 0.17 * s], 0.032),
        cur: new THREE.Vector3(sd * 0.4 * s, 0.42 * s, 0.6 * s),
        l1: 0.36 * s, l2: 0.36 * s,
      }));
      this.legs = [-1, 1].map((sd) => {
        const foot = add(this.root, SG, skin, [0, 0, 0], [0.13 * s, 0.075 * s, 0.22 * s]);
        return {
          sd, thigh: add(this.root, capT, skin, [0, 0, 0]), calf: add(this.root, capC, skin, [0, 0, 0]), foot,
          l1: 0.4 * s, l2: 0.4 * s,
          // world foot state
          x: 0, z: 0, sx: 0, sz: 0, ex: 0, ez: 0, k: 1, dur: 0.15, y: 0,
        };
      });
      // blob shadow
      const shTex = canvasTex(128, 128, (g, w, h) => {
        const gr = g.createRadialGradient(64, 64, 10, 64, 64, 62);
        gr.addColorStop(0, 'rgba(25,8,18,0.55)'); gr.addColorStop(0.7, 'rgba(25,8,18,0.35)'); gr.addColorStop(1, 'rgba(25,8,18,0)');
        g.fillStyle = gr; g.fillRect(0, 0, w, h);
      });
      // anime look: a hard-edged cel shadow instead of a soft blob
      this.shTexSoft = shTex;
      this.shTexHard = canvasTex(128, 128, (g) => { g.fillStyle = 'rgba(40,14,52,0.62)'; g.beginPath(); g.arc(64, 64, 52, 0, Math.PI * 2); g.fill(); });
      this.shadow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
        new THREE.MeshBasicMaterial({ map: shTex, transparent: true, depthWrite: false }));
      this.shadow.renderOrder = 1;
      scene.add(this.shadow);
      // smoothed pose
      this.ps = { c: 0.5, p: 0.2, r: 0, tw: 0, hp: 0, drop: 0 };
      this.flash = 0; this.lastSquash = 0; this.hook = 0; this.footInit = false;
      this.v1 = new THREE.Vector3(); this.v2 = new THREE.Vector3(); this.v3 = new THREE.Vector3(); this.v4 = new THREE.Vector3();
      this.faceParts = [];
      this.dress(add);
    }
    // ---- cosmetics
    dress(add) {
      const s = this.s, lo = this.lo, SG = GEO.sphere, it = (id) => S.item(id) || {};
      // mawashi variant
      const mw = it(lo.mawashi);
      if (mw.c1) {
        const u = this.belt.uniforms;
        u.uColor.value.set(0xffffff); u.uShade.value.setRGB(0.55, 0.45, 0.66);
        u.uMap.value = patTex(mw.pat, mw.c1, mw.c2); u.uHasMap.value = 1;
      }
      // headband
      const hb = it(lo.headband);
      if (hb.c1) {
        const m = toon(0xffffff, { shade: 0x8a7a9a, map: patTex(hb.pat, hb.c1, hb.c2), rimAmt: 0.4 });
        this.mats.push(m);
        const band = add(this.head, new THREE.TorusGeometry(0.248 * s, 0.035 * s, 8, 36), m, [0, 0.15 * s, -0.005 * s], null, 0.016);
        band.rotation.x = Math.PI / 2 + 0.12; band.scale.set(1, 1.03, 1);
        for (const sd of [-1, 1]) { const tl = add(this.head, GEO.box, m, [sd * 0.05 * s, 0.07 * s, -0.27 * s], [0.06 * s, 0.2 * s, 0.015 * s], 0.012); tl.rotation.z = sd * 0.35; tl.rotation.x = -0.4; }
      }
      // mask
      const mk = it(lo.mask);
      if (mk.kind) {
        const range = { menpo: [0.52, 0.28], visor: [0.38, 0.14] }[mk.kind] || [0.24, 0.52];
        const geo = new THREE.SphereGeometry(0.272 * s, 28, 16, 0, Math.PI, range[0] * Math.PI, range[1] * Math.PI);
        const tex = canvasTex(256, 128, (g, W, H) => this.paintMask(g, W, H, mk.kind));
        const m = toon(0xffffff, { shade: mk.kind === 'visor' ? 0x9090b0 : 0xa08890, map: tex, spec: mk.kind === 'visor' ? 0.6 : 0.15, rimAmt: 0.5 });
        if (mk.kind === 'visor') m.uniforms.uRim.value.set(0x46f2ff);
        this.mats.push(m);
        const mm = add(this.head, geo, m, [0, 0.1 * s, 0.005 * s], [0.95, 1.0, 1.0], 0.02);
        if (mk.kind !== 'menpo' && mk.kind !== 'visor') for (const e of this.eyes) e.visible = false;
        const red = toon(0xc8231d, { shade: 0x6e1018 }), ivory = toon(0xf1e6cf, { shade: 0xa89a86 });
        if (mk.kind === 'tengu') { const n = add(this.head, new THREE.ConeGeometry(0.045 * s, 0.3 * s, 10), red, [0, 0.08 * s, 0.38 * s], null, 0.014); n.rotation.x = Math.PI / 2 - 0.25; }
        if (mk.kind === 'hannya' || mk.kind === 'oni') for (const sd of [-1, 1]) { const h = add(this.head, new THREE.ConeGeometry(0.035 * s, 0.2 * s, 8), mk.kind === 'oni' ? ivory : ivory, [sd * 0.13 * s, 0.33 * s, 0.1 * s], null, 0.014); h.rotation.z = -sd * 0.45; h.rotation.x = 0.3; }
        if (mk.kind === 'kitsune') for (const sd of [-1, 1]) { const e = add(this.head, new THREE.ConeGeometry(0.06 * s, 0.16 * s, 4), ivory, [sd * 0.15 * s, 0.34 * s, 0.05 * s], null, 0.014); e.rotation.z = -sd * 0.3; }
        void mm;
      }
      // headwear
      const hw = it(lo.headwear);
      if (hw.kind) {
        const gold = toon(0xf0c35a, { shade: 0x9a6a2a, spec: 0.5 });
        if (hw.kind === 'kasa') {
          const m = toon(0xffffff, { shade: 0x9a8070, map: patTex('stripe', '#d8b878', '#b89458') });
          add(this.head, new THREE.CylinderGeometry(0.05 * s, 0.62 * s, 0.24 * s, 28), m, [0, 0.42 * s, -0.02 * s], null, 0.02);
        } else if (hw.kind === 'horns') {
          const red = toon(0xc8231d, { shade: 0x6e1018, spec: 0.3 });
          for (const sd of [-1, 1]) { const h = add(this.head, new THREE.ConeGeometry(0.05 * s, 0.3 * s, 10), red, [sd * 0.15 * s, 0.38 * s, 0.03 * s], null, 0.016); h.rotation.z = -sd * 0.55; }
        } else if (hw.kind === 'kabuto') {
          const c = add(this.head, new THREE.TorusGeometry(0.17 * s, 0.025 * s, 6, 24, Math.PI), gold, [0, 0.33 * s, 0.2 * s], null, 0.014);
          c.rotation.z = 0; c.rotation.x = -0.25;
          add(this.head, GEO.sphere, gold, [0, 0.27 * s, 0.24 * s], [0.05 * s, 0.05 * s, 0.03 * s], 0.012);
        } else if (hw.kind === 'crown') {
          add(this.head, new THREE.CylinderGeometry(0.17 * s, 0.15 * s, 0.09 * s, 18, 1, true), gold, [0, 0.36 * s, -0.02 * s], null, 0.014);
          for (let k = 0; k < 6; k++) { const a = k / 6 * Math.PI * 2; add(this.head, new THREE.ConeGeometry(0.025 * s, 0.09 * s, 6), gold, [Math.cos(a) * 0.16 * s, 0.44 * s, Math.sin(a) * 0.16 * s - 0.02 * s], null, 0.01); }
        } else if (hw.kind === 'halo') {
          this.halo = new THREE.Mesh(new THREE.TorusGeometry(0.22 * s, 0.022 * s, 6, 40), new THREE.MeshBasicMaterial({ color: 0x46f2ff, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false }));
          this.halo.rotation.x = Math.PI / 2; this.halo.position.set(0, 0.62 * s, 0); this.head.add(this.halo);
        }
      }
      // ceremonial jacket (comes off at the first face-off)
      const jk = it(lo.jacket);
      if (jk.c1) {
        const m = toon(0xffffff, { shade: 0x8a7a9a, map: patTex(jk.pat, jk.c1, jk.c2), rimAmt: 0.55, spec: 0.15 });
        this.mats.push(m);
        const g = this.jacket = new THREE.Group(); this.body.add(g);
        const coat = mesh(new THREE.CylinderGeometry(0.67 * s, 0.82 * s, 0.95 * s, 28, 1, true), m, 0.022); coat.position.set(0, 0.3 * s, 0.0); g.add(coat);
        m.side = THREE.DoubleSide;
        const col = mesh(new THREE.TorusGeometry(0.42 * s, 0.07 * s, 8, 24), toon(jk.c2, { shade: 0x554455 }), 0.016); col.rotation.x = Math.PI / 2; col.position.set(0, 0.76 * s, 0); g.add(col);
        for (const sd of [-1, 1]) { const sl = mesh(new THREE.CylinderGeometry(0.2 * s, 0.3 * s, 0.5 * s, 14, 1, true), m, 0.02); sl.position.set(sd * 0.72 * s, 0.5 * s, 0); sl.rotation.z = sd * 0.5; g.add(sl); }
        this.jacketOn = true;
      }
      this.victory = (it(lo.victory).pose) || 'tegatana';
    }
    paintMask(g, W, H, kind) {
      const C = W / 2;
      const eye = (x, y, col, w2, h2, rot) => { g.save(); g.translate(x, y); g.rotate(rot || 0); g.fillStyle = col; g.beginPath(); g.ellipse(0, 0, w2, h2, 0, 0, 7); g.fill(); g.restore(); };
      if (kind === 'oni') {
        g.fillStyle = '#c8231d'; g.fillRect(0, 0, W, H);
        g.fillStyle = '#1a0a0a'; g.beginPath(); g.moveTo(C - 70, 34); g.lineTo(C - 18, 50); g.lineTo(C - 70, 46); g.fill(); g.beginPath(); g.moveTo(C + 70, 34); g.lineTo(C + 18, 50); g.lineTo(C + 70, 46); g.fill();
        eye(C - 40, 60, '#ffd23a', 14, 8, 0.25); eye(C + 40, 60, '#ffd23a', 14, 8, -0.25);
        g.fillStyle = '#1a0a0a'; g.fillRect(C - 34, 92, 68, 16); g.fillStyle = '#fff'; for (const x of [C - 30, C + 22]) { g.beginPath(); g.moveTo(x, 92); g.lineTo(x + 8, 92); g.lineTo(x + 4, 112); g.fill(); }
      } else if (kind === 'kitsune') {
        g.fillStyle = '#f6f2ea'; g.fillRect(0, 0, W, H);
        g.fillStyle = '#d0201a'; for (const sd of [-1, 1]) { g.beginPath(); g.moveTo(C + sd * 18, 52); g.quadraticCurveTo(C + sd * 50, 30, C + sd * 74, 58); g.quadraticCurveTo(C + sd * 50, 50, C + sd * 18, 60); g.fill(); }
        eye(C - 40, 60, '#1a1010', 12, 3, 0.2); eye(C + 40, 60, '#1a1010', 12, 3, -0.2);
        g.fillStyle = '#d0201a'; g.fillRect(C - 3, 20, 6, 22); eye(C, 92, '#1a1010', 7, 5);
      } else if (kind === 'tengu') {
        g.fillStyle = '#b81f1a'; g.fillRect(0, 0, W, H);
        g.fillStyle = '#f6f2ea'; g.fillRect(C - 66, 34, 50, 10); g.fillRect(C + 16, 34, 50, 10);
        eye(C - 40, 58, '#f0c35a', 11, 8); eye(C + 40, 58, '#f0c35a', 11, 8);
        g.fillStyle = '#f6f2ea'; g.beginPath(); g.ellipse(C, 112, 50, 16, 0, Math.PI, 0); g.fill();
      } else if (kind === 'hannya') {
        g.fillStyle = '#efe4c8'; g.fillRect(0, 0, W, H);
        eye(C - 38, 56, '#2a1a10', 15, 9, 0.35); eye(C + 38, 56, '#2a1a10', 15, 9, -0.35); eye(C - 38, 56, '#e9c234', 5, 5); eye(C + 38, 56, '#e9c234', 5, 5);
        g.fillStyle = '#9c1c1c'; g.beginPath(); g.ellipse(C, 100, 46, 20, 0, 0, 7); g.fill();
        g.fillStyle = '#fff'; g.fillRect(C - 36, 92, 72, 7); g.fillStyle = '#efe4c8'; for (const sd of [-1, 1]) { g.beginPath(); g.moveTo(C + sd * 30, 99); g.lineTo(C + sd * 22, 99); g.lineTo(C + sd * 26, 118); g.fill(); }
      } else if (kind === 'visor') {
        g.fillStyle = '#0b0f1e'; g.fillRect(0, 0, W, H);
        const gr = g.createLinearGradient(0, 0, W, 0); gr.addColorStop(0, '#46f2ff'); gr.addColorStop(0.5, '#ff3a6a'); gr.addColorStop(1, '#46f2ff');
        g.fillStyle = gr; g.fillRect(0, H * 0.42, W, H * 0.14);
      } else if (kind === 'menpo') {
        g.fillStyle = '#2a2428'; g.fillRect(0, 0, W, H);
        g.fillStyle = '#c8231d'; g.fillRect(0, 0, W, 10);
        g.strokeStyle = '#d6a53a'; g.lineWidth = 4; for (let x = C - 50; x <= C + 50; x += 14) { g.beginPath(); g.moveTo(x, 50); g.lineTo(x, 100); g.stroke(); }
      }
    }
    resetJacket() {
      if (!this.jacket) return;
      if (this.jacket.parent !== this.body) { this.scene.remove(this.jacket); this.body.add(this.jacket); }
      this.jacket.position.set(0, 0, 0); this.jacket.rotation.set(0, 0, 0); this.jacket.visible = true;
      this.jacketOn = true; this.jacketFly = null;
    }
    updateJacket(w, m, dt) {
      const J = this.jacket; if (!J) return;
      if (this.jacketOn) {
        const derobe = !m || m.round !== 1 || m.phase !== 'shikiri' || m.phaseT > 0.8;
        if (derobe) {
          this.jacketOn = false;
          if (!m || m.round !== 1 || m.phase !== 'shikiri' || m.phaseT > 1.6) { J.visible = false; return; }
          this.body.updateMatrixWorld(true); this.scene.attach(J);
          this.jacketFly = { t: 0, vx: -w.fx * 2.4 + (Math.random() - 0.5), vy: 4.2, vz: -w.fz * 2.4 + (Math.random() - 0.5), sp: (Math.random() - 0.5) * 8 };
          if (this.onDerobe) this.onDerobe(w);
        }
      } else if (this.jacketFly) {
        const F = this.jacketFly; F.t += dt;
        F.vy -= 9 * dt; J.position.x += F.vx * dt; J.position.y = Math.max(-0.4, J.position.y + F.vy * dt); J.position.z += F.vz * dt;
        J.rotation.y += F.sp * dt; J.rotation.x += F.sp * 0.4 * dt;
        if (F.t > 1.6) { J.visible = false; this.jacketFly = null; }
      }
    }

    // a wrestler turned into something else: a rolling ball or a tiny chicken
    morph(w, dt, show) {
      const sc = this.scene;
      // CYCLONE: a whirlwind funnel and wind rings spinning round the wrestler
      if (w.fxs.cyclone > 0 && show) {
        if (!this.cycM) this.cycM = S.R3.cyclone(); if (!this.cycM.parent) sc.add(this.cycM);
        const s = (w.szCur || 1) * w.a.scale, k = Math.min(1, w.fxs.cyclone / 0.5, (5 - w.fxs.cyclone) / 0.3);
        S.R3.cycloneUpdate(this.cycM, w.x, w.z, s, k, dt);
        if (this.fx && Math.random() < dt * 30) { const a = Math.random() * 6.3; this.fx.dust(w.x + Math.cos(a) * 0.9 * s, 0.05, w.z + Math.sin(a) * 0.9 * s, 1, 0.25, 0.5, 0.35, -Math.sin(a) * 4, Math.cos(a) * 4); }
      } else if (this.cycM) this.cycM.visible = false;
      if (w.fxs.ball > 0 && show) {
        if (!this.ballM) {
          const g = new THREE.Group();
          // a daruma doll: red body, white face, fierce brows, gold trim
          const red = toon(0xd42a22, { shade: 0x7a1010, spec: 0.5 }), wht = toon(0xf6eddc, { shade: 0xb8a890 }), blk = toon(0x141414), gold = toon(0xf0c35a, { shade: 0x9a6a2a, spec: 0.6 });
          const b = mesh(new THREE.SphereGeometry(0.62, 22, 16), red, 0.03); b.scale.set(1, 1.08, 1); g.add(b);
          const face = mesh(new THREE.SphereGeometry(0.42, 18, 12, 0, Math.PI * 2, 0, Math.PI / 2), wht, 0.0); face.rotation.z = -Math.PI / 2; face.scale.set(1, 0.42, 1); face.position.set(0.44, 0.1, 0); g.add(face);
          for (const sd of [-1, 1]) {
            const eye = mesh(GEO.sphere, blk, 0); eye.scale.setScalar(0.07); eye.position.set(0.6, 0.16, sd * 0.15); g.add(eye);
            const brow = mesh(GEO.box, blk, 0); brow.scale.set(0.04, 0.05, 0.2); brow.position.set(0.6, 0.32, sd * 0.15); brow.rotation.x = sd * 0.35; g.add(brow);
          }
          const trim = mesh(new THREE.TorusGeometry(0.47, 0.035, 6, 24), gold, 0); trim.rotation.y = Math.PI / 2; trim.position.x = 0.36; trim.scale.set(1, 1, 1); g.add(trim);
          this.ballSpin = new THREE.Group(); this.ballSpin.add(g); sc.add(this.ballSpin); this.ballM = g;
        }
        const s = (w.szCur || 1) * w.a.scale;
        this.ballSpin.visible = true; this.ballSpin.position.set(w.x, 0.62 * s, w.z); this.ballSpin.scale.setScalar(s);
        this.ballSpin.rotation.set(0, -w.f, 0); this.ballM.rotation.set(0, 0, -(w.ballRoll || 0));
      } else if (this.ballSpin) this.ballSpin.visible = false;
      if (w.fxs.chicken > 0 && show) {
        if (!this.chick) {
          const g = new THREE.Group(), wht = toon(0xf6f2ea, { shade: 0xb9b0a0 }), red = toon(0xe2322b, { shade: 0x8a1a14 }), yel = toon(0xf0b030, { shade: 0x9a6a10 });
          const body = mesh(GEO.sphere, wht, 0.02); body.scale.set(0.34, 0.3, 0.26); body.position.y = 0.42; g.add(body);
          const head = mesh(GEO.sphere, wht, 0.02); head.scale.setScalar(0.17); head.position.set(0.24, 0.72, 0); g.add(head);
          const comb = mesh(GEO.sphere, red, 0.01); comb.scale.set(0.1, 0.08, 0.04); comb.position.set(0.24, 0.88, 0); g.add(comb);
          const beak = mesh(new THREE.ConeGeometry(0.05, 0.12, 6), yel, 0.01); beak.rotation.z = -Math.PI / 2; beak.position.set(0.42, 0.72, 0); g.add(beak);
          const tail = mesh(GEO.sphere, wht, 0.02); tail.scale.set(0.12, 0.18, 0.16); tail.position.set(-0.32, 0.55, 0); g.add(tail);
          this.chLegs = [-1, 1].map((sd) => { const l = mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.28, 5), yel, 0.008); l.position.set(0, 0.14, sd * 0.1); g.add(l); return l; });
          sc.add(g); this.chick = g;
        }
        const k = Math.hypot(w.vx, w.vz), T = performance.now() / 1000;
        this.chick.visible = true; this.chick.position.set(w.x, Math.abs(Math.sin(T * 26)) * 0.06 * Math.min(1, k), w.z);
        this.chick.rotation.set(0, -w.f, Math.sin(T * 30) * 0.1);
        this.chLegs.forEach((l, i) => { l.rotation.z = Math.sin(T * 30 + i * Math.PI) * 0.7 * Math.min(1, k); });
      } else if (this.chick) this.chick.visible = false;
      // CENSORED: a jittering block mosaic where the wrestler should be
      if (w.fxs.blur > 0 && show && this.viewer !== w.idx) {
        if (!this.mosaic) {
          const cv = document.createElement('canvas'); cv.width = 6; cv.height = 9;
          const tex = new THREE.CanvasTexture(cv); tex.magFilter = THREE.NearestFilter; tex.minFilter = THREE.NearestFilter;
          this.mosaic = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true })); this.mosaic.renderOrder = 5;
          this.mosaicCv = cv; this.mosaicT = 0; sc.add(this.mosaic);
        }
        this.mosaicT -= dt;
        if (this.mosaicT <= 0) {
          this.mosaicT = 0.12;
          const g = this.mosaicCv.getContext('2d'), skin = ['#e9b894', '#d9a07c', '#f0c8a8', '#c98a6a'], belt = this.arch.accent || '#4060c0';
          g.clearRect(0, 0, 6, 9);
          for (let y = 0; y < 9; y++) for (let x = 0; x < 6; x++) {
            const edge = (x === 0 || x === 5) && Math.random() < 0.5;
            if (edge) continue;
            g.fillStyle = y >= 4 && y <= 5 && Math.random() < 0.7 ? belt : y < 2 && Math.random() < 0.5 ? '#2a1a14' : skin[(Math.random() * 4) | 0];
            g.fillRect(x, y, 1, 1);
          }
          this.mosaic.material.map.needsUpdate = true;
        }
        const s = w.a.scale * (w.szCur || 1);
        this.mosaic.visible = true; this.mosaic.position.set(w.x, 1.15 * s + (w.y || 0), w.z); this.mosaic.scale.set(1.5 * s, 2.25 * s, 1);
      } else if (this.mosaic) this.mosaic.visible = false;
      // TRIPLETS: the real one wears an armband only its owner can see
      const trip = this.match && this.match.objs.some((o) => o.type === 'clones' && o.owner === w);
      if (trip && this.viewer === w.idx) {
        if (!this.armband) { this.armband = mesh(new THREE.TorusGeometry(0.21 * w.a.scale, 0.05, 8, 18), toon(0x46f2ff, { shade: 0x1a8a9a }), 0.01); this.armband.rotation.x = Math.PI / 2; this.arms[1].up.add(this.armband); }
        this.armband.visible = true;
      } else if (this.armband) this.armband.visible = false;
    }
    dispose(scene) {
      for (const x of [this.ballSpin, this.chick, this.bigFan, this.flopShadow, this.mosaic]) if (x && x.parent) x.parent.remove(x);
      if (this.stars) for (const sp of this.stars) if (sp.parent) sp.parent.remove(sp);
      if (this.jacket && this.jacket.parent === scene) scene.remove(this.jacket);
      scene.remove(this.root); scene.remove(this.shadow);
    }

    targetPose(w, T) {
      const t = w.t;
      let c = 0.42, p = 0.18, r = 0, tw = 0, hp = 0, rate = 14, drop = 0;
      const G = [0.52, 0.62, 0.7];
      this.stompLift = 0; this.hyT = 0; this.turnAway = 0;
      let Rh = G, Lh = mir(G);
      this.hook = 0;
      if (w.fxs && w.fxs.cyclone > 0) { const A = [1.02, 0.95, 0.0]; return { c: 0.32, p: -0.05, r: 0, tw: 0, hp: -0.05, Rh: A, Lh: mir(A), rate: 22, drop: 0 }; } // CYCLONE: arms straight out
      switch (w.st) {
        case 'ready': {
          // standing ready, hands on knees; hold L to drop into the full crouch, fists on the clay
          c = 0.65; p = 0.32; Rh = [0.48, 0.02, 0.42]; Lh = mir(Rh); hp = -0.05;
          const pt = w.preT;
          const mph = this.match ? this.match.phaseT : 9;
          if (this.match && this.match.phase === 'shikiri' && mph < 0.8 && !w.pre) { // rei: bow to each other first
            const k = Math.sin(Math.min(1, mph / 0.8) * Math.PI);
            c = 0.12; p = 0.7 * k; hp = 0.2 * k; Rh = [0.62, 0.02, 0.22]; Lh = mir(Rh); rate = 10;
            return { c, p, r, tw, hp, Rh, Lh, rate, drop };
          }
          const xp = w.pre && w.pre.indexOf('x_') === 0 && pt < (S.PRE_DUR[w.pre] || 0) ? w.pre.slice(2) : null;
          if (xp) {
            rate = 24; hp = 0; c = 0.25; p = 0;
            if (xp === 'flex') { Rh = [0.78, 0.95, -0.02]; Lh = mir(Rh); p = -0.12; this.ps.squash = 0; }
            else if (xp === 'point') { Rh = [0.22, 0.85, 1.3]; Lh = [-0.55, 0.05, 0.25]; tw = -0.25; }
            else if (xp === 'drum') { const k = Math.sin(T * 30) > 0; Rh = k ? [0.3, 0.2, 0.68] : [0.45, 0.45, 0.4]; Lh = mir(k ? [0.45, 0.45, 0.4] : [0.3, 0.2, 0.68]); rate = 60; }
            else if (xp === 'hype') { const k = Math.abs(Math.sin(T * 9)); Rh = [0.7, 1.1 + 0.3 * k, 0.1]; Lh = mir(Rh); p = -0.1; }
            else if (xp === 'bow') { p = 0.75 * Math.min(1, pt / 0.3); Rh = [0.5, 0.0, 0.2]; Lh = mir(Rh); }
            else if (xp === 'neck') { this.hyT = Math.sin(pt * 14) * 0.6; Rh = [0.55, 0.05, 0.1]; Lh = mir(Rh); }
            else if (xp === 'cry') { Rh = [0.95, 0.3, 0.35]; Lh = mir(Rh); p = -0.3; hp = -0.45; r = Math.sin(T * 40) * 0.03; c = 0.55; }
            else if (xp === 'shimmy') { tw = Math.sin(pt * 16) * 0.5; r = Math.sin(pt * 8) * 0.18; Rh = [0.6, 0.85, 0.4]; Lh = mir(Rh); }
          } else if (w.pre === 'salt' && pt < 0.9) {
            c = 0.2; p = pt < 0.35 ? 0.2 : -0.12; hp = pt < 0.35 ? 0.1 : -0.2; rate = 26; Lh = [-0.6, 0.1, 0.3];
            Rh = pt < 0.35 ? [0.5, 0.0, -0.15] : pt < 0.6 ? [0.3, 1.15, 0.85] : [0.45, 0.85, 0.6]; tw = pt < 0.35 ? 0.3 : -0.2;
          } else if (w.pre === 'spread' && pt < 0.8) {
            c = 1.0; p = 0.1; hp = 0; rate = 22;
            Rh = pt < 0.2 ? [0.05, 0.5, 0.55] : [1.05, 0.55, 0.05]; Lh = mir(Rh);
          } else if (w.pre === 'faceSlap' && pt < 0.35) {
            c = 0.35; p = 0.05; rate = 45; Rh = pt < 0.1 ? [0.6, 1.0, 0.3] : [0.2, 1.05, 0.28]; Lh = mir(Rh); hp = pt > 0.1 && pt < 0.2 ? 0.2 : 0;
          } else if (w.pre === 'beltSlap' && pt < 0.35) {
            c = 0.5; p = 0.25; rate = 45; Rh = pt < 0.1 ? [0.62, 0.55, 0.6] : [0.25, 0.0, 0.64]; Lh = mir(Rh);
          } else if (w.crouchT > 0) { const k = Math.min(1, w.crouchT / 0.25); c = 0.65 + 0.4 * k; p = 0.32 + 0.3 * k; Rh = [0.3, 0.02 - 0.55 * k, 0.42 + 0.2 * k]; Lh = mir(Rh); hp = -0.25 * k; rate = 22; }
          else if (w.pre === 'clap' && pt < 0.32) {
            c = 0.55; p = 0.12; hp = 0; rate = 40;
            Rh = pt < 0.1 ? [0.62, 0.7, 0.5] : [0.04, 0.7, 0.62]; Lh = mir(Rh);
          } else if (w.pre === 'stomp' && pt < 0.8) {
            const up = pt < 0.5 ? Math.sin(pt / 0.5 * Math.PI / 2) : Math.max(0, 1 - (pt - 0.5) / 0.08);
            this.stompLift = up; c = 0.35 + 0.4 * (1 - up); p = 0.2; r = -0.32 * up; hp = 0; rate = 30;
            Rh = [0.5, 0.05, 0.4]; Lh = [-0.75, 0.55 + 0.3 * up, 0.3];
          } else if (w.power > 0.05) {
            p = 0.62 + Math.sin(T * 47) * 0.025 * w.power; r = Math.sin(T * 39) * 0.02 * w.power; c = 1;
          }
          break;
        }
        case 'free':
          if (w.contact && w.fwdIn > 0.4) { p = 0.5; c = 0.62; Rh = [0.32, 0.5, 0.88]; Lh = mir(Rh); }
          else if (!w.contact) {
            // walking: the guard drops and the arms hang by the belly, swinging against the legs
            const sp = w.spd !== undefined ? w.spd : Math.hypot(w.vx || 0, w.vz || 0);
            const dtp = Math.min(0.1, Math.max(0, T - (this.gaitT || T))); this.gaitT = T;
            this.gaitW = (this.gaitW || 0) + ((w.relaxed ? 1 : Math.min(1, Math.max(0, (sp - 0.4) / 1.2))) - (this.gaitW || 0)) * Math.min(1, dtp * 6);
            this.gaitPh = (this.gaitPh || 0) + dtp * (4 + sp * 1.6);
            const k = this.gaitW;
            if (k > 0.01) {
              const sw = Math.sin(this.gaitPh) * (0.12 + 0.06 * Math.min(1, sp / 4)) * Math.min(1, sp / 0.8);
              const hang = (s) => [0.66, 0.04 + Math.abs(s) * 0.25, 0.1 + s];
              Rh = lerpA(G, hang(sw), k); Lh = mir(lerpA(G, hang(-sw), k));
              c = 0.42 - 0.12 * k; p = 0.18 - 0.06 * k; tw = 0.06 * Math.sin(this.gaitPh) * k;
            }
          }
          break;
        case 'brace': c = 0.88; p = 0.32; Rh = [0.45, 0.32, 0.58]; Lh = mir(Rh); break;
        case 'palm': {
          const e = t < 0.05 ? t / 0.05 : t < 0.11 ? 1 : Math.max(0, 1 - (t - 0.11) / 0.09);
          const act = [0.14, 0.62, 1.25], idle = [0.45, 0.5, 0.32];
          if (w.hand === 1) { Rh = lerpA(G, act, e); Lh = mir(idle); tw = -0.32 * e; }
          else { Lh = mir(lerpA(G, act, e)); Rh = idle; tw = 0.32 * e; }
          p = 0.25 + 0.18 * e; c = 0.5; rate = 45; break;
        }
        case 'wind': c = 0.62 + 0.1 * w.windPow; p = -0.1 - 0.08 * w.windPow; Rh = [0.33, 0.62, 0.15]; Lh = mir(Rh); tw = 0.04 * Math.sin(T * 40) * w.windPow; break;
        case 'heavy': {
          const e = t < 0.05 ? 0 : t < 0.17 ? 1 : Math.max(0, 1 - (t - 0.17) / 0.25);
          Rh = lerpA([0.33, 0.62, 0.15], [0.24, 0.62, 1.3], e); Lh = mir(Rh); p = -0.1 + 0.65 * e; c = 0.6; rate = 45;
          if (w.thrHand > 0 || w.throat) { Rh = [0.1, 1.05, 1.4]; Lh = [-0.5, 0.45, 0.3]; tw = -0.25; } // one hand up at their throat
          break;
        }
        case 'charge': if (w.torpedo) { c = 0.1; p = 1.45; Rh = [0.25, 0.95, 1.05]; Lh = mir(Rh); hp = -0.5; rate = 30; break; }
          c = 0.62; p = 0.68; Rh = [0.36, 0.4, 0.78]; Lh = mir(Rh); hp = -0.3; break;
        case 'overrun': c = 0.4; p = 0.85 + 0.12 * Math.sin(T * 25); Rh = [0.78, 0.82, 0.3]; Lh = mir(Rh); rate = 20; break;
        case 'slap':
          rate = 45; Lh = [-0.45, 0.5, 0.4]; tw = -0.25;
          if (t < 0.08) { Rh = [0.3, 0.98, 0.55]; p = -0.15; } else if (t < 0.26) { Rh = [0.12, 0.0, 0.98]; p = 0.4; } else { Rh = G; p = 0.2; }
          c = 0.45; break;
        case 'grab': Rh = [0.56, 0.35, 1.02]; Lh = mir(Rh); p = 0.45; c = 0.56; rate = 30; break;
        case 'dash': {
          c = 0.5; const lf = w.ddx * w.fx + w.ddz * w.fz, ls = w.ddx * w.fz - w.ddz * w.fx;
          p = 0.15 + lf * 0.3; r = -ls * 0.4; Rh = [0.5, 0.45, 0.45]; Lh = mir(Rh); break;
        }
        case 'recover': c = 0.35; p = 0.02; Rh = [0.55, 0.3, 0.38]; Lh = mir(Rh); break;
        case 'stun': c = 0.3; p = -0.22 + 0.06 * Math.sin(T * 30); Rh = [0.68, 0.42, 0.18]; Lh = mir(Rh); break;
        case 'teeter': { // heels on the straw, arms windmilling
          const L = Math.max(0, Math.min(1, w.lean || 0));
          c = 0.25; rate = 28; p = -0.15 - 0.35 * L;
          Rh = [0.85, 0.9 + 0.35 * Math.sin(T * 26), 0.1]; Lh = [-0.85, 0.9 + 0.35 * Math.sin(T * 26 + 3), 0.1]; break;
        }
        case 'stumble': {
          c = 0.3; rate = 20;
          Rh = [0.8, 0.75 + 0.28 * Math.sin(T * 18), 0.15]; Lh = [-0.8, 0.75 + 0.28 * Math.sin(T * 18 + 2), 0.15]; break;
        }
        case 'clinch': {
          const cl = w.clinch;
          if (!cl) break;
          const inside = cl.type[w.idx] === 'inside';
          Rh = inside ? [0.3, 0.05, 0.9] : [0.52, 0.32, 0.84]; Lh = mir(Rh);
          c = 0.62; p = 0.45;
          const tw0 = cl.tow[w.idx];
          if (tw0 > 0.3) { p = 0.62; c = 0.7; } else if (tw0 < -0.3) p = 0.15;
          if (cl.rear === w) { Rh = [0.36, 0.3, 0.86]; Lh = mir(Rh); p = 0.5; }
          if (cl.rear && cl.rear !== w) { Rh = [0.75, 0.6, 0.1]; Lh = mir(Rh); p = 0.2; rate = 20; }
          if (cl.lift) {
            if (cl.lift.w === w) { p = -0.32; c = 0.42; Rh = [0.3, -0.06, 0.72]; Lh = mir(Rh); }
            else { p = 0.38; c = 0.05; Rh = [0.42, 0.65, 0.72]; Lh = mir(Rh); }
          }
          if (cl.swing) {
            const om = cl.swing.om || 0;
            if (cl.swing.w === w) { tw = S.clamp(-om * 0.18, -0.9, 0.9); p = 0.35; c = 0.55; Rh = [0.55, 0.45, 0.75]; Lh = [-0.3, 0.15, 0.9]; rate = 25; }
            else { Rh = [0.8, 0.75, 0.2]; Lh = [-0.8, 0.75, 0.2]; p = 0.4; rate = 25; }
          }
          const Tq = cl.tech;
          if (Tq && Tq.w === w) {
            const k = clamp(Tq.t / Tq.dur, 0, 1);
            if (Tq.kind === 'throw') { tw = -Tq.side * 1.0 * Math.sin(k * Math.PI); p = 0.55; Rh = [0.6, 0.5, 0.7]; Lh = [-0.3, 0.1, 0.9]; }
            if (Tq.kind === 'utchari') { p = -0.75 * Math.sin(Math.min(1, k * 1.5) * Math.PI * 0.5); c = 0.25; }
            if (Tq.kind === 'pull') { p = -0.3; Rh = [0.35, 0.55, 0.95]; Lh = mir(Rh); }
            if (Tq.kind === 'trip') { this.hook = Math.sin(k * Math.PI); p = 0.5; }
            rate = 25;
          }
          break;
        }
        case 'sslap': { rate = 45; tw = -0.4; p = 0.3; c = 0.45; Rh = t < 0.1 ? [0.75, 1.05, 0.4] : [-0.15, 0.75, 1.0]; Lh = [-0.45, 0.45, 0.4]; break; }
        case 'hyaku': {
          rate = 70; c = 0.5; p = 0.3;
          const act = [0.12, 0.6 + Math.random() * 0.15, 1.25], idle = [0.45, 0.5, 0.45];
          if (w.hand) { Rh = act; Lh = mir(idle); } else { Lh = mir(act); Rh = idle; }
          tw = (w.hand ? -1 : 1) * 0.25; break;
        }
        case 'gale': { rate = 14; c = 0.4; const sw = Math.sin(t * 14); p = 0.05 + 0.12 * sw; Rh = [0.18, 1.1 + 0.3 * sw, 0.45 + 0.2 * sw]; Lh = mir(Rh); break; }
        case 'rewinding': { rate = 30; const sw = Math.sin(t * 40); p = -0.15; Rh = [0.5, 0.35 + 0.25 * sw, -0.2]; Lh = [-0.5, 0.35 - 0.25 * sw, -0.2]; tw = 0.15 * sw; break; } // jerky backwards scramble
        case 'bigstomp': { // the big leg lift, then the stamp
          const up = Math.sin(Math.min(1, t / 0.45) * Math.PI / 2);
          this.stompLift = up; c = 0.35 + 0.3 * (1 - up); p = 0.2; r = -0.36 * up; rate = 30;
          Rh = [0.5, 0.05, 0.4]; Lh = [-0.75, 0.55 + 0.35 * up, 0.3]; break;
        }
        case 'inhale': { rate = 14; c = 0.35; p = -0.3; hp = 0.25; Rh = [0.85, 0.75, 0.55]; Lh = mir(Rh); break; }
        case 'spit': { rate = 10; c = 0.25; p = t > w.dur - 0.12 ? 0.55 : -0.1; Rh = [0.7, 0.55, 0.2]; Lh = mir(Rh); break; }
        case 'air': {
          const k = Math.max(0, (t - 1.2) / 0.4);
          c = 0.1; p = 0.3 + 1.1 * Math.min(1, k); Rh = [1.0, 0.7, 0.1]; Lh = mir(Rh); rate = 12; break;
        }
        case 'fall': {
          const k = Math.min(1, Math.pow(t / 0.22, 2)); // gravity: slow to tip, then slammed flat
          const ff = w.fallX * w.fx + w.fallZ * w.fz, fs = w.fallX * w.fz - w.fallZ * w.fx;
          p = ff * 1.38 * k; r = -fs * 1.38 * k; c = 0.3 + 0.5 * k; drop = k;
          // arms fling out as they tip, then lie tucked along the body so the four limbs don't read as four legs
          Rh = k < 1 ? [0.8, 0.2, 0.7] : [0.62, -0.25, 0.12]; Lh = mir(Rh); rate = k < 1 ? 20 : 8; break;
        }
        case 'win': {
          c = 0.05; p = -0.06; Rh = [0.68, 0.05, 0.2]; Lh = mir(Rh);
          if (t > 1.15) { // finish with a bow to the opponent
            const k = Math.min(1, (t - 1.15) / 0.3);
            p = 0.72 * k; hp = 0.25 * k; c = 0.12; Rh = [0.6, 0.0, 0.25]; Lh = mir(Rh); this.turnAway = 0; rate = 10;
            break;
          }
          const vp = this.victory;
          if (vp !== 'tegatana' && t > 0.2) {
            const k = Math.min(1, (t - 0.2) / 0.2);
            if (vp === 'fist') { Rh = lerpA(Rh, [0.3, 1.5, 0.15], k); }
            else if (vp === 'bow') { p = 0.75 * k; }
            else if (vp === 'flex') { Rh = lerpA(Rh, [0.78, 0.95, -0.02], k); Lh = mir(Rh); p = -0.15; }
            else if (vp === 'shiko') { const ph = (t - 0.35) % 1.4; this.stompLift = ph < 0.6 ? Math.sin(ph / 0.6 * Math.PI / 2) : Math.max(0, 1 - (ph - 0.6) / 0.08); c = 0.4 + 0.4 * (1 - this.stompLift); r = -0.3 * this.stompLift; Rh = [0.5, 0.05, 0.4]; Lh = [-0.75, 0.6, 0.3]; }
            else if (vp === 'crossed') { Rh = lerpA(Rh, [-0.18, 0.62, 0.48], k); Lh = lerpA(Lh, [0.18, 0.55, 0.44], k); hp = -0.1; }
            else if (vp === 'cool') { this.turnAway = k; }
            break;
          }
          if (t > 0.2 && t < 1.05) { // tegatana: the winner's knife-hand salute
            const k = (t - 0.2) / 0.85;
            Rh = [0.35 - 0.7 * Math.sin(k * Math.PI) * (k > 0.5 ? -1 : 1) * 0.5, 0.45, 0.85];
          }
          break;
        }
        case 'lose': c = 0.15; p = 0.28 + (t > 0.8 ? 0.4 * Math.min(1, (t - 0.8) / 0.4) : 0); hp = 0.35; Rh = [0.64, 0.05, 0.25]; Lh = mir(Rh); break;
      }
      if (w.uprightT > 0 && w.st !== 'fall') { p -= 0.35 * Math.min(1, w.uprightT / 0.3); hp += 0.3; }
      if (w.throatT > 0 && w.st !== 'fall') { const k = Math.min(1, w.throatT / 0.25); p -= 0.45 * k; hp -= 0.9 * k; Rh = [0.8, 0.55, 0.05]; Lh = mir(Rh); } // head snapped back, arms flung out
      if (w.fxs && w.fxs.grabbed > 0) { Rh = [0.8, 0.8 + 0.2 * Math.sin(T * 20), 0.2]; Lh = [-0.8, 0.8 + 0.2 * Math.sin(T * 20 + 2), 0.2]; rate = 20; }
      if (w.fxs && w.fxs.dizzy > 0) { r += Math.sin(T * 5) * 0.2; hp += Math.sin(T * 3) * 0.2; }
      if (w.fxs && w.fxs.sleep > 0) { hp = 0.6 + Math.sin(T * 1.6) * 0.08; p += 0.12 + Math.sin(T * 1.6) * 0.05; Rh = [0.55, 0.15, 0.05]; Lh = mir(Rh); rate = 6; } // dozing, head down
      // balance shows in the body
      const tf = w.tx * w.fx + w.tz * w.fz, ts = w.tx * w.fz - w.tz * w.fx;
      if (w.st !== 'fall') {
        p += clamp(tf, -1, 1) * 0.55; r += -clamp(ts, -1, 1) * 0.55;
        const wob = Math.max(0, 0.55 - w.bal);
        p += Math.sin(T * 17 + w.idx) * wob * 0.35; r += Math.sin(T * 13 + 1) * wob * 0.3;
        if (wob > 0.2 && (w.st === 'free' || w.st === 'recover')) { Rh = [0.75, 0.7, 0.2]; Lh = mir(Rh); }
      }
      return { c, p, r, tw, hp, Rh, Lh, rate, drop };
    }

    update(w, dt, T) {
      const s = this.s, root = this.root, ps = this.ps;
      root.position.set(w.x, w.y + (w.torpedo ? 0.35 : 0), w.z);
      root.scale.setScalar((w.szCur || 1) * (w.gulpI >= 0 ? 1.22 + Math.sin(T * 9) * 0.03 : w.st === 'inhale' ? 1.06 : 1));
      const frozen = w.fxs && w.fxs.frozen > 0;
      if (frozen) dt = 1e-5; // ice: hold the pose
      const tp = this.targetPose(w, T);
      if (w.hunch > 0) { tp.p += w.hunch * 0.3; tp.c += w.hunch * 0.16; tp.hp += w.hunch * 0.22; } // campaign: badly hurt, he hunches over
      root.rotation.y = Math.PI / 2 - w.f + (this.turnAway || 0) * Math.PI;
      this.head.rotation.y = this.hyT || 0;
      if (this.halo) this.halo.rotation.z += dt * 2;
      this.updateJacket(w, this.match, dt);
      // status tints
      const f = w.fxs || {}, pulse = 0.5 + 0.5 * Math.sin(T * 12);
      let tint = null, tAmt = 0;
      if (w.st === 'rewinding') { tint = 0x7ad7ff; tAmt = 0.25 + 0.25 * (Math.sin(performance.now() / 30) > 0 ? 1 : 0); } // tape-flicker
      else if (w.boomT > 0) { tint = 0xff3a1a; tAmt = 0.2 + 0.4 * (Math.sin(performance.now() / (40 + w.boomT * 90)) * 0.5 + 0.5); } // lit fuse: faster as it burns down
      else if (f.frozen > 0) { tint = 0x9fe6ff; tAmt = 0.55; }
      else if (f.burning > 0) { tint = Math.sin(performance.now() / 40) > 0 ? 0xff7a1a : 0xffc040; tAmt = 0.45; } // on fire
      else if (f.zapped > 0) { tint = Math.sin(performance.now() / 25) > 0 ? 0xbff4ff : 0x2a3a6a; tAmt = 0.55; } // frazzled
      else if (f.possessed > 0) { tint = 0x7a2bb0; tAmt = 0.35 + 0.15 * pulse; }
      else if (f.poison > 0) { tint = 0x6ac23a; tAmt = 0.3 + 0.15 * pulse; }
      else if (f.haste > 0) { tint = 0xfff08a; tAmt = 0.15 + 0.1 * pulse; }
      else if (f.sleep > 0) { tint = 0x6a74c8; tAmt = 0.18 + 0.08 * pulse; }
      else if (f.invuln > 0) { tint = 0xffd23a; tAmt = 0.25 + 0.25 * pulse; }
      else if (f.absorb > 0) { tint = 0x9aa4b8; tAmt = 0.3 + 0.15 * pulse; }
      else if (f.slow > 0) { tint = 0x8a6cff; tAmt = 0.22; }
      else if (f.giant > 0) { tint = 0xff6a3a; tAmt = 0.12 * pulse; }
      else if (w.charges > 0) { tint = 0xff3a2a; tAmt = 0.12 * w.charges * pulse; }
      else if (w.bruise > 0) { tint = 0x7a1e34; tAmt = 0.34 * w.bruise; } // campaign: hurt shows on the skin, purple-red bruising
      // vanish: the owner sees a ghost of themselves, the opponent sees nothing at all
      const alpha = f.invis > 0 ? (this.viewer === w.idx || this.viewer === -1 ? 0.3 : 0) : 1;
      const morph = w.fxs.ball > 0 || w.fxs.chicken > 0;
      const censored = w.fxs.blur > 0 && this.viewer !== w.idx;
      this.root.visible = alpha > 0 && !w.swallowed && !morph && !w.inShop && !censored;
      this.morph(w, dt, alpha > 0 && !w.swallowed && !w.inShop);
      this.shadow.visible = this.root.visible && alpha > 0.1;
      if (alpha !== this.alpha) {
        this.alpha = alpha;
        this.root.traverse((o) => {
          if (!o.material || !o.material.uniforms || !o.material.uniforms.uAlpha) return;
          if (o.material.uniforms.uThick) { o.visible = alpha === 1; return; }
          o.material.uniforms.uAlpha.value = alpha; o.material.transparent = alpha < 1; o.material.depthWrite = alpha === 1;
        });
        this.shadow.visible = alpha > 0.1;
      }
      const k1 = 1 - Math.exp(-dt * tp.rate), k2 = 1 - Math.exp(-dt * 9);
      ps.c += (tp.c - ps.c) * k2; ps.p += (tp.p - ps.p) * k1; ps.r += (tp.r - ps.r) * k1;
      ps.tw += (tp.tw - ps.tw) * k1; ps.hp += (tp.hp - ps.hp) * k2; ps.drop += (tp.drop - ps.drop) * k1;
      // hit flash
      if (w.squash > this.lastSquash + 0.15) this.flash = 1;
      this.lastSquash = w.squash;
      this.flash = Math.max(0, this.flash - dt * 9);
      for (const m of this.mats) {
        if (tint && this.flash < 0.2) { m.uniforms.uFlashCol.value.set(tint); m.uniforms.uFlash.value = tAmt; }
        else { m.uniforms.uFlashCol.value.set(0xffffff); m.uniforms.uFlash.value = this.flash * 0.75; }
      }

      const bk = w.breath || 0, bph = (this.bph = (this.bph || 0) + dt * (2.4 + bk * 5.5)); // campaign: out of breath = big, fast breaths
      const breathe = Math.sin(bph + w.idx * 2) * (0.012 + bk * 0.03) * s;
      const H = s * (0.84 - 0.3 * ps.c) + breathe - ps.drop * 0.42 * s;
      this.body.position.set(0, H, -ps.drop * 0.1 * s);
      this.body.rotation.set(ps.p, ps.tw, ps.r);
      const q = w.squash;
      const heave = bk * Math.max(0, Math.sin(bph)) * 0.045;
      this.body.scale.set(1 + 0.08 * q + heave, 1 - 0.12 * q, 1 + 0.08 * q + heave * 1.4);
      if (w.sweat > 0 && this.fx && Math.random() < dt * 9 * w.sweat) { const a = Math.random() * 6.28; this.fx.salt(w.x + Math.cos(a) * 0.3 * s, 1.9 * s, w.z + Math.sin(a) * 0.3 * s, Math.cos(a) * 1.2, Math.sin(a) * 1.2); } // sweat flicking off
      this.head.rotation.x = ps.hp;
      // sagari swing
      const lvf = w.vx * w.fx + w.vz * w.fz;
      this.sagari.rotation.x = clamp(-lvf * 0.1, -0.6, 0.6) - ps.p * 0.6 + Math.sin(T * 7) * 0.04;

      // arms (body space); NO ARMS hides them
      const armless = !!(w.fxs && w.fxs.noarms > 0);
      for (const A of this.arms) { A.up.visible = A.lo.visible = A.hand.visible = !armless; }
      const kh = 1 - Math.exp(-dt * tp.rate);
      for (const A of this.arms) {
        const tg = A.sd > 0 ? tp.Rh : tp.Lh;
        this.v1.set(tg[0] * s, tg[1] * s, tg[2] * s);
        A.cur.lerp(this.v1, kh);
        const tip = this.v2.copy(A.cur);
        const pole = this.v3.set(A.sd, -0.6, -0.45);
        ik(A.sh, tip, A.l1, A.l2, pole, this.v4);
        seg(A.up, A.sh, this.v4); seg(A.lo, this.v4, tip);
        A.hand.position.copy(tip);
      }

      // feet (world) -> legs (root space)
      this.updateFeet(w, dt, T);
      this.body.updateMatrix();
      root.updateMatrixWorld(true);
      for (const Lg of this.legs) {
        const hip = this.v1.set(Lg.sd * 0.3 * s, -0.1 * s, 0).applyMatrix4(this.body.matrix);
        let foot;
        const downed = w.st === 'fall' || w.down;
        if (downed) { // lying on the clay: legs straight out along the body, fully reached so no knee pokes up
          const hb = this.v2.set(Lg.sd * 0.3 * s, -0.1 * s, 0), len = (Lg.l1 + Lg.l2) * 0.995;
          foot = hb.add(this.v3.set(Lg.sd * 0.06, -1, 0.05).normalize().multiplyScalar(len)).applyMatrix4(this.body.matrix);
        } else if (w.lifted || w.y > 0.12) {
          foot = this.v2.set(Lg.sd * 0.34 * s, hip.y - 0.74 * s, 0.05 * s + Math.sin(T * 14 + Lg.sd) * 0.12 * s);
        } else {
          foot = this.v2.set(Lg.x, Lg.y + 0.07 * s, Lg.z);
          root.worldToLocal(foot);
        }
        if (this.hook > 0 && Lg.sd > 0) foot.lerp(this.v3.set(0.1 * s, 0.25 * s, 0.75 * s), this.hook);
        if (this.stompLift > 0 && Lg.sd < 0) foot.lerp(this.v3.set(-0.85 * s, 0.25 * s + 0.75 * s * this.stompLift, 0.12 * s), Math.min(1, this.stompLift * 1.5));
        const pole = this.v3.set(Lg.sd * 0.75, 0.1, 1);
        if (downed) pole.set(Lg.sd * 0.3, 0, 1).transformDirection(this.body.matrix); // knees bend the way the body faces, not the old standing way
        if (w.st === 'air' || w.torpedo) foot.set(Lg.sd * 0.45 * s, hip.y - 0.6 * s, -0.5 * s);
        ik(hip, foot, Lg.l1, Lg.l2, pole, this.v4);
        seg(Lg.thigh, hip, this.v4); seg(Lg.calf, this.v4, foot);
        Lg.foot.position.set(foot.x, Math.max(foot.y - 0.02 * s, 0.05 * s + (w.y > 0.12 ? -1 : 0)), foot.z + 0.08 * s);
        Lg.foot.rotation.y = Lg.sd * 0.4;
      }
      // shadow
      const sc = 1.9 * s * (1 - Math.min(0.5, w.y));
      this.shadow.material.map = SH.uAnime.value > 0.5 ? this.shTexHard : this.shTexSoft;
      this.shadow.position.set(w.x + 0.12, 0.015, w.z + 0.05);
      this.shadow.scale.set(sc, 1, sc * (1 + ps.drop * 0.6));
      this.shadow.rotation.y = Math.PI / 2 - w.f;
    }

    updateFeet(w, dt, T) {
      const s = this.s;
      const fx = w.fx, fz = w.fz, rx = fz, rz = -fx;
      const sp = w.spd;
      const wide = 0.4 * s * (1 + 0.3 * this.ps.c);
      const back = (w.vx * fx + w.vz * fz) < -0.6;
      const sliding = (w.slideT > 0 && back) || (w.st === 'brace' && sp > 0.5) || w.st === 'stun' ||
        (w.clinch && !w.clinch.tech && !w.lifted && back);
      let slideAmt = 0;
      if (w.st === 'fall' || w.down) { // no stepping while down; plant fresh when they are back up
        for (const Lg of this.legs) { Lg.k = 1; Lg.y = 0; }
        this.footInit = false; this.slideAmt = 0; return;
      }
      for (let i = 0; i < 2; i++) {
        const Lg = this.legs[i], sd = Lg.sd;
        const fwdOff = (w.st === 'charge' || w.st === 'heavy' ? 0.12 : 0.04) * (i === 0 ? 1 : -1) * s;
        const ix = w.x + rx * sd * wide + fx * fwdOff + w.vx * 0.1;
        const iz = w.z + rz * sd * wide + fz * fwdOff + w.vz * 0.1;
        if (!this.footInit) { Lg.x = Lg.ex = ix; Lg.z = Lg.ez = iz; Lg.k = 1; }
        if (w.lifted || w.y > 0.12) { Lg.x = ix; Lg.z = iz; Lg.k = 1; continue; }
        if (Lg.k < 1) {
          Lg.k = Math.min(1, Lg.k + dt / Lg.dur);
          const e = Lg.k;
          Lg.x = Lg.sx + (Lg.ex - Lg.sx) * e; Lg.z = Lg.sz + (Lg.ez - Lg.sz) * e;
          Lg.y = Math.sin(Math.PI * e) * 0.13 * s;
          if (Lg.k >= 1) {
            Lg.y = 0;
            this.fx.footprint(Lg.x, Lg.z, w.f, sd, s);
            if (sp > 3 && !this.fx.noMarks) this.fx.dust(Lg.x, 0.05, Lg.z, 2, 0.15, 0.6, 0.35, -w.vx * 0.1, -w.vz * 0.1);
            if (sp > 0.8) this.fx.sand(Lg.x, Lg.z, sp > 3 ? 7 : 3, -w.vx * 0.25, -w.vz * 0.25, sp > 3 ? 1.2 : 0.7);
          }
          continue;
        }
        const dev = Math.hypot(ix - Lg.x, iz - Lg.z);
        const other = this.legs[1 - i];
        if (sliding && dev < 0.7 * s) {
          const ox = Lg.x, oz = Lg.z;
          Lg.x += w.vx * dt; Lg.z += w.vz * dt;
          const mv = Math.hypot(Lg.x - ox, Lg.z - oz);
          if (mv > 0.004) { this.fx.slide(ox, oz, Lg.x, Lg.z, s); slideAmt += mv / dt; if (Math.random() < 0.5) this.fx.sand(Lg.x, Lg.z, 2, (Lg.x - ox) / dt * 0.4, (Lg.z - oz) / dt * 0.4, 0.6); } // heels ploughing the clay
          continue;
        }
        const thr = (w.st === 'ready' || w.st === 'win' || w.st === 'lose') ? 0.15 * s : 0.26 * s;
        if (dev > thr && other.k >= 1) {
          Lg.sx = Lg.x; Lg.sz = Lg.z;
          Lg.ex = ix + w.vx * 0.08; Lg.ez = iz + w.vz * 0.08;
          Lg.k = 0; Lg.dur = clamp(0.2 - sp * 0.018, 0.085, 0.2);
        }
      }
      this.footInit = true;
      this.slideAmt = slideAmt;
    }
  }

  // ------------------------------------------------------------------ Referee
  class RefView {
    constructor(scene) {
      this.g = new THREE.Group(); scene.add(this.g);
      const robe = toon(0x7a2c8c, { shade: 0x3a1150, spec: 0.15 });
      const gold = toon(0xe5b84c, { shade: 0x9a6a2a, spec: 0.4 });
      const skin = toon(0xefc3a0, { shade: 0xb87a6c });
      const blk = toon(0x1d1820, { shade: 0x0b0a10, spec: 0.4 });
      const m1 = mesh(new THREE.CylinderGeometry(0.24, 0.5, 1.15, 16), robe, 0.022); m1.position.y = 0.58; this.g.add(m1);
      const ob = mesh(new THREE.TorusGeometry(0.31, 0.05, 6, 20), gold, 0.015); ob.rotation.x = Math.PI / 2; ob.position.y = 0.82; this.g.add(ob);
      const sl = mesh(GEO.sphere, robe, 0.022); sl.scale.set(0.42, 0.18, 0.3); sl.position.y = 1.12; this.g.add(sl);
      this.headG = new THREE.Group(); this.headG.position.y = 1.32; this.g.add(this.headG);
      const hd = mesh(GEO.sphere, skin, 0.02); hd.scale.set(0.16, 0.18, 0.16); this.headG.add(hd);
      const hat = mesh(new THREE.CylinderGeometry(0.08, 0.16, 0.42, 12), blk, 0.02); hat.position.set(0, 0.28, -0.04); hat.rotation.x = -0.25; this.headG.add(hat);
      this.arm = new THREE.Group(); this.arm.position.set(0.3, 1.08, 0); this.g.add(this.arm);
      const ua = mesh(new THREE.CapsuleGeometry(0.07, 0.42, 3, 8), robe, 0.02); ua.position.y = -0.25; this.arm.add(ua);
      this.fan = new THREE.Group(); this.fan.position.y = -0.52; this.arm.add(this.fan);
      const disc = mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.035, 22), gold, 0.02); disc.rotation.x = Math.PI / 2; disc.position.y = -0.3; this.fan.add(disc);
      const dot = mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.04, 16), blk, 0); dot.rotation.x = Math.PI / 2; dot.position.set(0, -0.3, 0.005); this.fan.add(dot);
      const hdl = mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.24, 6), blk, 0.012); hdl.position.y = -0.08; this.fan.add(hdl);
      this.x = 0; this.z = -R - 0.6; this.ang = -Math.PI / 2; this.pose = 'idle'; this.poseT = 0; this.pointAt = null;
      const shTex = canvasTex(64, 64, (g) => { const gr = g.createRadialGradient(32, 32, 4, 32, 32, 31); gr.addColorStop(0, 'rgba(25,8,18,0.5)'); gr.addColorStop(1, 'rgba(25,8,18,0)'); g.fillStyle = gr; g.fillRect(0, 0, 64, 64); });
      this.shadow = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 1.2).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: shTex, transparent: true, depthWrite: false }));
      scene.add(this.shadow);
    }
    set(p, at) { this.pose = p; this.poseT = 0; this.pointAt = at || null; }
    update(dt, T, m) {
      this.poseT += dt;
      let tx = 0, tz = -R - 0.55, look = 0;
      if (m) {
        const A = m.w[0], B = m.w[1];
        const mx = (A.x + B.x) / 2, mz = (A.z + B.z) / 2;
        let ax = B.x - A.x, az = B.z - A.z; const al = Math.hypot(ax, az) || 1; ax /= al; az /= al;
        let px = -az, pz = ax; if (pz > 0) { px = -px; pz = -pz; } // stay on the far side
        const a = Math.atan2(mz + pz * 3, mx + px * 3);
        tx = Math.cos(a) * (R + 0.6); tz = Math.sin(a) * (R + 0.6);
        look = Math.atan2(mz - this.z, mx - this.x);
        if (this.pose === 'point' && this.pointAt) look = Math.atan2(this.pointAt.z - this.z, this.pointAt.x - this.x);
      }
      const k = 1 - Math.exp(-dt * 2.2);
      const brk = m && m.objs.find((o) => o.type === 'ref');
      if (brk) {
        // REFEREE BREAK: run straight in between them, arms out, then shove
        this.x += (brk.x - this.x) * Math.min(1, dt * 11); this.z += (brk.z - this.z) * Math.min(1, dt * 11);
        look = Math.atan2(m.w[0].z - this.z, m.w[0].x - this.x);
        if (this.pose !== 'go') this.set('go');
      } else if (Math.hypot(this.x, this.z) < R + 0.55) {
        // walk back out to the edge
        this.x += (tx - this.x) * Math.min(1, dt * 4); this.z += (tz - this.z) * Math.min(1, dt * 4);
      } else {
        // move around the ring along the circle
        let ca = Math.atan2(this.z, this.x); const ta = Math.atan2(tz, tx);
        ca += S.wrap(ta - ca) * k;
        this.x = Math.cos(ca) * (R + 0.6); this.z = Math.sin(ca) * (R + 0.6);
      }
      const bob = Math.abs(Math.sin(T * 5)) * 0.02;
      this.g.position.set(this.x, bob, this.z);
      this.yaw = this.yaw === undefined ? Math.PI / 2 - look : this.yaw + S.wrap(Math.PI / 2 - look - this.yaw) * Math.min(1, dt * 8);
      this.g.rotation.y = this.yaw;
      this.shadow.position.set(this.x + 0.1, 0.015, this.z + 0.05);
      // arm pose
      let ax = 0.25, az = 0;
      if (this.pose === 'ready') { ax = -1.3; az = 0.1; }
      else if (this.pose === 'go') { const e = Math.min(1, this.poseT / 0.15); ax = -1.3 - 1.2 * e; az = 0.2; }
      else if (this.pose === 'point' && this.pointAt) {
        // snap the gunbai up and out toward the winner, and hold it there
        const e = Math.min(1, this.poseT / 0.18);
        ax = -0.6 - 1.45 * e; az = 0;
        this.fan.rotation.y = Math.sin(Math.min(1, this.poseT / 0.4) * Math.PI) * 1.2;
      } else { ax = 0.2 + Math.sin(T * 3) * 0.05; this.fan.rotation.y = 0; }
      this.arm.rotation.x += (ax - this.arm.rotation.x) * Math.min(1, dt * (this.pose === 'point' ? 22 : 12));
      this.arm.rotation.z += (az - this.arm.rotation.z) * Math.min(1, dt * 12);
      this.headG.rotation.x = this.pose === 'point' ? -0.15 : 0.05;
    }
  }

  // ------------------------------------------------------------------ FX
  class FX {
    constructor(scene) {
      const N = this.N = 900;
      const g = new THREE.BufferGeometry();
      this.pos = new Float32Array(N * 3); this.size = new Float32Array(N); this.alpha = new Float32Array(N); this.shade = new Float32Array(N);
      this.vel = new Float32Array(N * 3); this.life = new Float32Array(N); this.max = new Float32Array(N); this.grow = new Float32Array(N); this.base = new Float32Array(N);
      for (let i = 0; i < N; i++) { this.life[i] = 1; this.max[i] = 1; this.pos[i * 3 + 1] = -50; }
      g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
      g.setAttribute('aSize', new THREE.BufferAttribute(this.size, 1));
      g.setAttribute('aAlpha', new THREE.BufferAttribute(this.alpha, 1));
      g.setAttribute('aShade', new THREE.BufferAttribute(this.shade, 1));
      this.pmat = new THREE.ShaderMaterial({
        uniforms: { uScale: { value: 600 }, uLite: { value: new THREE.Color(0xf2dcb8) }, uDark: { value: new THREE.Color(0xb98d66) }, uLine: { value: new THREE.Color(0x5a3828) } },
        vertexShader: `attribute float aSize; attribute float aAlpha; attribute float aShade; uniform float uScale;
          varying float vA; varying float vS;
          void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); gl_PointSize = aAlpha > 0.001 ? aSize * uScale / -mv.z : 0.0; gl_Position = projectionMatrix * mv; vA = aAlpha; vS = aShade; }`,
        fragmentShader: `uniform vec3 uLite; uniform vec3 uDark; uniform vec3 uLine; varying float vA; varying float vS;
          float h(vec2 q){ return fract(sin(dot(q, vec2(12.9898, 78.233))) * 43758.5453); }
          float vn(vec2 q){ vec2 i = floor(q), f = fract(q); f = f*f*(3.0-2.0*f);
            return mix(mix(h(i), h(i+vec2(1,0)), f.x), mix(h(i+vec2(0,1)), h(i+vec2(1,1)), f.x), f.y); }
          void main(){ if (vA <= 0.001) discard; vec2 p = gl_PointCoord * 2.0 - 1.0;
            float n = vn(p * 2.6 + vS * 17.0) * 0.6 + vn(p * 5.3 - vS * 9.0) * 0.4;
            float r = length(p) + (n - 0.5) * 0.35;
            float k = 1.0 - vA;               // life: 0 -> 1
            float edge = 0.95 - k * 0.55;
            if (r > edge) discard;
            if (n < k * 0.9 - 0.05) discard; // erode into wisps
            float lit = step(length(p - vec2(-0.3, -0.34)), 0.68);
            vec3 c = mix(uDark, uLite, lit);
            c = mix(c, uLine, step(edge - 0.1, r) * 0.6);
            gl_FragColor = vec4(c, 1.0); }`,
        transparent: true, depthWrite: false,
      });
      this.points = new THREE.Points(g, this.pmat); this.points.frustumCulled = false; this.points.renderOrder = 3;
      scene.add(this.points);
      this.geo = g; this.next = 0;

      // shock rings
      this.rings = [];
      const rg = new THREE.RingGeometry(0.86, 1, 56).rotateX(-Math.PI / 2);
      for (let i = 0; i < 8; i++) {
        const m = new THREE.Mesh(rg, new THREE.MeshBasicMaterial({ color: 0xfff6e6, transparent: true, depthWrite: false, opacity: 0 }));
        m.renderOrder = 2; m.visible = false; scene.add(m); this.rings.push({ m, t: 1, max: 0.3, size: 1 });
      }
      // hit sparks
      const star = canvasTex(256, 256, (g2) => {
        g2.translate(128, 128);
        const spikes = 9; g2.beginPath();
        for (let i = 0; i < spikes * 2; i++) {
          const a = i / (spikes * 2) * Math.PI * 2, r = i % 2 ? 34 + Math.random() * 10 : 92 + Math.random() * 30;
          g2.lineTo(Math.cos(a) * r, Math.sin(a) * r);
        }
        g2.closePath(); g2.fillStyle = '#fffaf0'; g2.fill(); g2.lineWidth = 9; g2.strokeStyle = '#1c0f15'; g2.stroke();
        g2.beginPath(); g2.arc(0, 0, 22, 0, Math.PI * 2); g2.fillStyle = '#ffe27a'; g2.fill();
      });
      this.sparks = [];
      for (let i = 0; i < 8; i++) {
        const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: star, transparent: true, depthTest: false }));
        sp.visible = false; sp.renderOrder = 10; scene.add(sp); this.sparks.push({ sp, t: 1, max: 0.14, size: 1 });
      }
      // decals: footprints and slide grooves
      const fpTex = canvasTex(64, 128, (g2) => {
        g2.fillStyle = 'rgba(70,38,26,0.9)';
        g2.beginPath(); g2.ellipse(32, 70, 20, 44, 0, 0, Math.PI * 2); g2.fill();
        for (let k = 0; k < 5; k++) { g2.beginPath(); g2.arc(14 + k * 9, 18 + Math.abs(k - 2) * 3, 5, 0, Math.PI * 2); g2.fill(); }
      });
      const slTex = canvasTex(64, 16, (g2) => {
        const gr = g2.createLinearGradient(0, 0, 0, 16);
        gr.addColorStop(0, 'rgba(70,38,26,0)'); gr.addColorStop(0.3, 'rgba(70,38,26,0.8)'); gr.addColorStop(0.5, 'rgba(240,215,180,0.5)'); gr.addColorStop(0.7, 'rgba(70,38,26,0.8)'); gr.addColorStop(1, 'rgba(70,38,26,0)');
        g2.fillStyle = gr; g2.fillRect(0, 0, 64, 16);
      });
      const plane = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
      const decalMat = (map, op) => new THREE.MeshBasicMaterial({ map, transparent: true, depthWrite: false, opacity: op, polygonOffset: true, polygonOffsetFactor: -2 });
      this.fp = new THREE.InstancedMesh(plane, decalMat(fpTex, 0.42), 500);
      this.sl = new THREE.InstancedMesh(plane, decalMat(slTex, 0.32), 1400);
      for (const im of [this.fp, this.sl]) { im.frustumCulled = false; im.renderOrder = 1; scene.add(im); }
      this.fpI = 0; this.slI = 0;
      this.m4 = new THREE.Matrix4(); this.q = new THREE.Quaternion(); this.e = new THREE.Euler(); this.vp = new THREE.Vector3(); this.vs = new THREE.Vector3();
      this.clearDecals();
    }
    salt(x, y, z, dx, dz) {
      if (!this.saltPts) {
        const n = this.saltN = 160, g = new THREE.BufferGeometry();
        this.saltPos = new Float32Array(n * 3); this.saltVel = new Float32Array(n * 3); this.saltLife = new Float32Array(n).fill(9);
        g.setAttribute('position', new THREE.BufferAttribute(this.saltPos, 3));
        this.saltPts = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 0.07, transparent: true, opacity: 0.95, depthWrite: false }));
        this.saltPts.frustumCulled = false; this.saltPts.renderOrder = 4; this.scene.add(this.saltPts); this.saltI = 0;
        for (let i = 0; i < n; i++) this.saltPos[i * 3 + 1] = -50;
      }
      for (let k = 0; k < 70; k++) {
        const i = this.saltI; this.saltI = (this.saltI + 1) % this.saltN;
        this.saltPos[i * 3] = x; this.saltPos[i * 3 + 1] = y; this.saltPos[i * 3 + 2] = z;
        const sp = 2 + Math.random() * 2.5, sx = (Math.random() - 0.5) * 1.6, sz = (Math.random() - 0.5) * 1.6;
        this.saltVel[i * 3] = dx * sp + sx; this.saltVel[i * 3 + 1] = 2.2 + Math.random() * 2; this.saltVel[i * 3 + 2] = dz * sp + sz;
        this.saltLife[i] = 0;
      }
    }
    updateSalt(dt) {
      if (!this.saltPts) return;
      for (let i = 0; i < this.saltN; i++) {
        if (this.saltLife[i] > 3) continue;
        this.saltLife[i] += dt;
        this.saltVel[i * 3 + 1] -= 9 * dt;
        for (let a = 0; a < 3; a++) this.saltPos[i * 3 + a] += this.saltVel[i * 3 + a] * dt;
        if (this.saltPos[i * 3 + 1] < 0.02) { this.saltPos[i * 3 + 1] = 0.02; this.saltVel[i * 3] *= 0.3; this.saltVel[i * 3 + 2] *= 0.3; this.saltVel[i * 3 + 1] = 0; }
        if (this.saltLife[i] > 2.5) this.saltPos[i * 3 + 1] = -50;
      }
      this.saltPts.geometry.attributes.position.needsUpdate = true;
    }
    // sand kicked up off the clay (dohyo only, fx.sandy): grains fly, land, lie there a moment and fade
    sand(x, z, n, dx, dz, up) {
      if (!this.sandy) return;
      if (!this.sPts) {
        const N = this.sN = 400, g = new THREE.BufferGeometry();
        this.sPos = new Float32Array(N * 3).fill(-50); this.sVel = new Float32Array(N * 3); this.sLife = new Float32Array(N).fill(9); this.sCol = new Float32Array(N * 3); this.sI = 0;
        const tones = [[0.93, 0.84, 0.66], [0.5, 0.37, 0.24], [0.98, 0.92, 0.78], [0.42, 0.3, 0.19]];
        for (let i = 0; i < N; i++) { const t = tones[i % 4]; this.sCol.set(t, i * 3); }
        g.setAttribute('position', new THREE.BufferAttribute(this.sPos, 3)); g.setAttribute('color', new THREE.BufferAttribute(this.sCol, 3));
        this.sPts = new THREE.Points(g, new THREE.PointsMaterial({ size: 0.075, vertexColors: true, transparent: true, opacity: 1, depthWrite: true }));
        this.sPts.frustumCulled = false; this.sPts.renderOrder = 3; this.scene.add(this.sPts);
      }
      up = up || 1;
      for (let j = 0; j < n; j++) {
        const i = this.sI; this.sI = (this.sI + 1) % this.sN;
        const a = Math.random() * Math.PI * 2, sp = 0.4 + Math.random() * 1.2;
        this.sPos[i * 3] = x + Math.cos(a) * 0.12; this.sPos[i * 3 + 1] = 0.03; this.sPos[i * 3 + 2] = z + Math.sin(a) * 0.12;
        this.sVel[i * 3] = (dx || 0) * (0.6 + Math.random()) + Math.cos(a) * sp; this.sVel[i * 3 + 1] = (0.8 + Math.random() * 1.8) * up; this.sVel[i * 3 + 2] = (dz || 0) * (0.6 + Math.random()) + Math.sin(a) * sp;
        this.sLife[i] = 0;
      }
    }
    updateSand(dt) {
      if (!this.sPts) return;
      for (let i = 0; i < this.sN; i++) {
        if (this.sLife[i] > 2.5) continue;
        this.sLife[i] += dt;
        if (this.sPos[i * 3 + 1] > 0.015) {
          this.sVel[i * 3 + 1] -= 12 * dt;
          for (let a = 0; a < 3; a++) this.sPos[i * 3 + a] += this.sVel[i * 3 + a] * dt;
          if (this.sPos[i * 3 + 1] <= 0.015) { this.sPos[i * 3 + 1] = 0.015; this.sVel[i * 3] *= 0.25; this.sVel[i * 3 + 2] *= 0.25; } // landed: a short skid
        } else { const k = Math.exp(-dt * 10); this.sVel[i * 3] *= k; this.sVel[i * 3 + 2] *= k; this.sPos[i * 3] += this.sVel[i * 3] * dt; this.sPos[i * 3 + 2] += this.sVel[i * 3 + 2] * dt; }
        if (this.sLife[i] > 2.5) this.sPos[i * 3 + 1] = -50;   // settled into the clay
      }
      this.sPts.geometry.attributes.position.needsUpdate = true;
    }
    // stepping in water: a few droplets kicked up and thin ripples spreading out (k = how hard: 1 a step, 3 a body)
    water(x, z, k) {
      if (!this.wPts) {
        const n = this.wN = 120, g = new THREE.BufferGeometry();
        this.wPos = new Float32Array(n * 3).fill(-50); this.wVel = new Float32Array(n * 3); this.wLife = new Float32Array(n).fill(9); this.wI = 0;
        g.setAttribute('position', new THREE.BufferAttribute(this.wPos, 3));
        this.wPts = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xe6f2ff, size: 0.11, transparent: true, opacity: 0.85, depthWrite: false }));
        this.wPts.frustumCulled = false; this.wPts.renderOrder = 4; this.scene.add(this.wPts);
        const rg = new THREE.RingGeometry(0.84, 1, 40).rotateX(-Math.PI / 2);
        this.ripples = [...Array(10)].map(() => {
          const m = new THREE.Mesh(rg, new THREE.MeshBasicMaterial({ color: 0xe8f2ff, transparent: true, opacity: 0, depthWrite: false }));
          m.renderOrder = 2; m.visible = false; this.scene.add(m); return { m, t: 9, max: 0.8, size: 1 };
        });
      }
      for (let j = 0; j < 4 + k * 5; j++) {
        const i = this.wI; this.wI = (this.wI + 1) % this.wN; const a = Math.random() * Math.PI * 2, sp = (0.6 + Math.random()) * (0.7 + k * 0.4);
        this.wPos[i * 3] = x + Math.cos(a) * 0.08; this.wPos[i * 3 + 1] = 0.04; this.wPos[i * 3 + 2] = z + Math.sin(a) * 0.08;
        this.wVel[i * 3] = Math.cos(a) * sp; this.wVel[i * 3 + 1] = 1.4 + Math.random() * (1 + k); this.wVel[i * 3 + 2] = Math.sin(a) * sp; this.wLife[i] = 0;
      }
      for (let j = 0; j < (k > 1.5 ? 2 : 1); j++) {
        const r = this.ripples.find((o) => o.t >= o.max) || this.ripples[0];
        r.t = -j * 0.15; r.max = 0.7 + k * 0.25; r.size = 0.35 + k * 0.3; r.m.position.set(x, 0.016, z); r.m.visible = true;
      }
    }
    updateWater(dt) {
      if (!this.wPts) return;
      for (let i = 0; i < this.wN; i++) {
        if (this.wLife[i] > 1) continue;
        this.wLife[i] += dt; this.wVel[i * 3 + 1] -= 11 * dt;
        for (let a = 0; a < 3; a++) this.wPos[i * 3 + a] += this.wVel[i * 3 + a] * dt;
        if (this.wPos[i * 3 + 1] < 0.02 || this.wLife[i] > 1) { this.wPos[i * 3 + 1] = -50; this.wLife[i] = 9; }
      }
      this.wPts.geometry.attributes.position.needsUpdate = true;
      for (const r of this.ripples) {
        if (r.t >= r.max) { r.m.visible = false; continue; }
        r.t += dt; const k = Math.max(0, r.t / r.max), sc = r.size * (0.15 + (1 - Math.pow(1 - k, 2)));
        r.m.scale.set(sc, 1, sc * 0.9); r.m.material.opacity = r.t < 0 ? 0 : 0.85 * (1 - k);
      }
    }
    clearDecals() {
      const z = new THREE.Matrix4().makeScale(0, 0, 0);
      for (let i = 0; i < 500; i++) this.fp.setMatrixAt(i, z);
      for (let i = 0; i < 1400; i++) this.sl.setMatrixAt(i, z);
      this.fp.instanceMatrix.needsUpdate = true; this.sl.instanceMatrix.needsUpdate = true;
    }
    footprint(x, z, f, sd, s) {
      if (this.noMarks) return;
      this.e.set(0, Math.PI / 2 - f + sd * 0.4, 0); this.q.setFromEuler(this.e);
      this.m4.compose(this.vp.set(x, 0.012, z + 0.06), this.q, this.vs.set(0.22 * s, 1, 0.36 * s));
      this.fp.setMatrixAt(this.fpI, this.m4); this.fpI = (this.fpI + 1) % 500;
      this.fp.instanceMatrix.needsUpdate = true;
    }
    slide(x0, z0, x1, z1, s) {
      if (this.noMarks) return;
      const len = Math.hypot(x1 - x0, z1 - z0);
      this.e.set(0, -Math.atan2(z1 - z0, x1 - x0), 0); this.q.setFromEuler(this.e);
      this.m4.compose(this.vp.set((x0 + x1) / 2, 0.011, (z0 + z1) / 2), this.q, this.vs.set(len + 0.03, 1, 0.13 * s));
      this.sl.setMatrixAt(this.slI, this.m4); this.slI = (this.slI + 1) % 1400;
      this.sl.instanceMatrix.needsUpdate = true;
    }
    dust(x, y, z, n, spread, up, size, dx, dz) {
      for (let k = 0; k < n; k++) {
        const i = this.next; this.next = (this.next + 1) % this.N;
        const a = Math.random() * Math.PI * 2, r = Math.random() * spread;
        this.pos[i * 3] = x + Math.cos(a) * r; this.pos[i * 3 + 1] = y + Math.random() * 0.1; this.pos[i * 3 + 2] = z + Math.sin(a) * r;
        const sp = (0.6 + Math.random()) * up;
        this.vel[i * 3] = Math.cos(a) * sp * 1.6 + (dx || 0); this.vel[i * 3 + 1] = sp * (0.4 + Math.random() * 0.7); this.vel[i * 3 + 2] = Math.sin(a) * sp * 1.6 + (dz || 0);
        this.life[i] = 0; this.max[i] = 0.45 + Math.random() * 0.5;
        this.base[i] = size * 0.35 * (0.6 + Math.random() * 0.7); this.grow[i] = size * 0.45 * (0.6 + Math.random());
        this.shade[i] = Math.random();
      }
    }
    burst(x, z, power) {
      const p = Math.min(1.6, power / 6);
      this.dust(x, 0.05, z, Math.round(8 + p * 18), 0.25 + p * 0.3, 1.0 + p * 1.4, 0.42 + p * 0.25);
      this.sand(x, z, Math.round(10 + p * 30), 0, 0, 1 + p * 0.5);
    }
    ring(x, z, size, dur) {
      const r = this.rings.find((o) => o.t >= o.max) || this.rings[0];
      r.t = 0; r.max = dur || 0.32; r.size = size; r.m.position.set(x, 0.03, z); r.m.visible = true;
    }
    spark(x, y, z, size) {
      const s = this.sparks.find((o) => o.t >= o.max) || this.sparks[0];
      s.t = 0; s.max = 0.13; s.size = size; s.sp.position.set(x, y, z); s.sp.visible = true; s.sp.material.rotation = Math.random() * 6.28;
    }
    update(dt) {
      for (let i = 0; i < this.N; i++) {
        if (this.life[i] >= this.max[i]) { this.alpha[i] = 0; this.size[i] = 0; this.pos[i * 3 + 1] = -50; continue; }
        this.life[i] += dt;
        const k = this.life[i] / this.max[i];
        const d = Math.exp(-dt * 3.2);
        this.vel[i * 3] *= d; this.vel[i * 3 + 1] = this.vel[i * 3 + 1] * d - dt * 1.2; this.vel[i * 3 + 2] *= d;
        this.pos[i * 3] += this.vel[i * 3] * dt; this.pos[i * 3 + 1] = Math.max(0.02, this.pos[i * 3 + 1] + this.vel[i * 3 + 1] * dt); this.pos[i * 3 + 2] += this.vel[i * 3 + 2] * dt;
        this.size[i] = this.base[i] + this.grow[i] * Math.sqrt(k);
        this.alpha[i] = 1 - k;
      }
      const at = this.geo.attributes;
      at.position.needsUpdate = true; at.aSize.needsUpdate = true; at.aAlpha.needsUpdate = true; at.aShade.needsUpdate = true;
      for (const r of this.rings) {
        if (r.t >= r.max) { r.m.visible = false; continue; }
        r.t += dt; const k = Math.min(1, r.t / r.max);
        const sc = r.size * (0.3 + 1.0 * (1 - Math.pow(1 - k, 3)));
        r.m.scale.set(sc, 1, sc); r.m.material.opacity = 0.9 * (1 - k);
      }
      for (const s of this.sparks) {
        if (s.t >= s.max) { s.sp.visible = false; continue; }
        s.t += dt; const k = s.t / s.max;
        const sc = s.size * (k < 0.3 ? k / 0.3 : 1 - (k - 0.3) * 0.6);
        s.sp.scale.set(sc, sc, 1); s.sp.material.opacity = k < 0.7 ? 1 : 1 - (k - 0.7) / 0.3;
      }
    }
  }


  // ------------------------------------------------------------------ anime post-processing
  // The anime look (KUMITEGAME, or ART STYLE: ANIME): the scene is drawn into a texture, then one pass adds
  // ink lines around every shape and fold (from depth and colour changes, so stages and crowd get them too),
  // an anime grade (richer colour, violet shadows, warm highlights), halftone dots in the shadows, a soft
  // glow on bright things, film grain and a vignette.
  const POST_VS = 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }';
  const BRIGHT_FS = `uniform sampler2D tColor; varying vec2 vUv;
    void main(){ vec3 c = texture2D(tColor, vUv).rgb; float l = dot(c, vec3(0.299, 0.587, 0.114)); float sat = max(c.r, max(c.g, c.b)) - min(c.r, min(c.g, c.b)); gl_FragColor = vec4(c * smoothstep(0.93, 1.0, l + sat * 0.25), 1.0); } // only really bright things (sparks, fire, lights), not pale skin`;
  const BLUR_FS = `uniform sampler2D tColor; uniform vec2 uDir; varying vec2 vUv;
    void main(){
      vec3 c = texture2D(tColor, vUv).rgb * 0.227;
      c += (texture2D(tColor, vUv + uDir * 1.385).rgb + texture2D(tColor, vUv - uDir * 1.385).rgb) * 0.316;
      c += (texture2D(tColor, vUv + uDir * 3.231).rgb + texture2D(tColor, vUv - uDir * 3.231).rgb) * 0.070;
      gl_FragColor = vec4(c, 1.0); }`;
  const COMP_FS = `uniform sampler2D tColor; uniform sampler2D tDepth; uniform sampler2D tBloom;
    uniform vec2 uRes; uniform float uNear; uniform float uFar; uniform float uTime; uniform float uPx; uniform float uCine; uniform vec3 uHaze;
    varying vec2 vUv;
    float D(vec2 uv){ float z = texture2D(tDepth, uv).r; return uNear * uFar / (uFar - z * (uFar - uNear)); }
    vec3 C(vec2 uv){ return texture2D(tColor, uv).rgb; }
    float L(vec3 c){ return dot(c, vec3(0.299, 0.587, 0.114)); }
    void main(){
      vec2 px = uPx / uRes;
      vec3 c = C(vUv);
      // ink: where depth bends (silhouettes, overlaps) or the colour jumps (folds, markings)
      float d0 = D(vUv);
      float dl = D(vUv - vec2(px.x, 0.0)), dr = D(vUv + vec2(px.x, 0.0)), du = D(vUv + vec2(0.0, px.y)), dd = D(vUv - vec2(0.0, px.y));
      float bend = (abs(dl + dr - 2.0 * d0) + abs(du + dd - 2.0 * d0)) / d0;
      float edgeD = smoothstep(0.012, 0.03, bend) * step(d0, uFar * 0.8);
      vec3 cl = C(vUv - vec2(px.x, 0.0)), cr = C(vUv + vec2(px.x, 0.0)), cu = C(vUv + vec2(0.0, px.y)), cd = C(vUv - vec2(0.0, px.y));
      float edgeC = smoothstep(0.45, 0.8, length(cl - cr) + length(cu - cd)) * step(d0, uFar * 0.8);
      float edge = max(edgeD, edgeC * 0.45);
      // CINEMATIC (campaign): contact shadows from the depth buffer, distance haze, a warmer/cooler grade
      if (uCine > 0.5) {
        float ao = 0.0, rad = 0.55 / (d0 * 0.70);
        for (int i = 0; i < 12; i++) {
          float a = float(i) * 2.39996 + mod(floor(gl_FragCoord.x) + floor(gl_FragCoord.y) * 2.0, 4.0) * 0.39; // a tiny 4-step rotation, not noise
          float rr = rad * (0.3 + 0.7 * fract(float(i) * 0.618));
          vec2 o = vec2(cos(a) * uRes.y / uRes.x, sin(a)) * rr;
          float ds = D(vUv + o), diff = d0 - ds;
          ao += smoothstep(0.03, 0.35, diff) * (1.0 - smoothstep(0.9, 2.6, diff));
        }
        ao = clamp(ao / 12.0, 0.0, 1.0);
        c *= 1.0 - ao * 0.62;
        float hz = smoothstep(18.0, 46.0, d0) * 0.55 + (1.0 - step(d0, uFar * 0.8)) * 0.0;
        c = mix(c, uHaze, hz);
      }
      // anime grade
      float l = L(c);
      c = mix(vec3(l), c, 1.15);
      c = mix(c, c * c * (3.0 - 2.0 * c), 0.2);
      c *= mix(vec3(0.93, 0.9, 1.0), vec3(1.0, 0.98, 0.93), smoothstep(0.1, 0.6, l)); // a faint cool shadow, not violet
      if (uCine > 0.5) { c = mix(c, c * mix(vec3(0.82, 0.92, 1.08), vec3(1.08, 0.99, 0.88), smoothstep(0.15, 0.7, l)), 0.7); c = (c - 0.5) * 1.08 + 0.5; } // teal shadows, warm light, a little more contrast
      // halftone dots in the shadows (comic print)
      float cell = 4.5 * max(1.0, uPx);
      vec2 g = mat2(0.7071, -0.7071, 0.7071, 0.7071) * gl_FragCoord.xy;
      float r = length(mod(g, cell) - cell * 0.5) / (cell * 0.5);
      float shade = smoothstep(0.34, 0.1, l);
      c *= 1.0 - step(r, shade * 0.95) * (uCine > 0.5 ? 0.0 : 0.22); // the comic dots belong to versus
      // glow, ink, vignette, grain
      c += texture2D(tBloom, vUv).rgb * (uCine > 0.5 ? 0.12 : 0.35); // the campaign keeps glow for lights, not skin
      c = mix(c, vec3(0.1, 0.045, 0.085), edge * 0.92);
      vec2 vg = vUv - 0.5; c *= 1.0 - dot(vg, vg) * (uCine > 0.5 ? 1.05 : 0.6);
      float n = fract(sin(dot(gl_FragCoord.xy + fract(uTime) * 91.7, vec2(12.9898, 78.233))) * 43758.5453);
      c += (n - 0.5) * (uCine > 0.5 ? 0.018 : 0.035);
      gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0);
    }`;
  class AnimePost {
    constructor(r) {
      this.r = r;
      const ms = r.capabilities.isWebGL2 ? (S.touch && S.touch.on ? 2 : 4) : 0; // phones: lighter anti-aliasing (the ink pass draws the edges anyway)
      this.rt = new THREE.WebGLRenderTarget(4, 4, { samples: ms });
      this.rt.depthTexture = new THREE.DepthTexture(4, 4); this.rt.depthTexture.type = THREE.UnsignedIntType;
      const lin = { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter };
      this.bA = new THREE.WebGLRenderTarget(4, 4, lin); this.bB = new THREE.WebGLRenderTarget(4, 4, lin);
      this.qs = new THREE.Scene(); this.qc = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2)); this.quad.frustumCulled = false; this.qs.add(this.quad);
      const mk = (fs, u) => new THREE.ShaderMaterial({ uniforms: u, vertexShader: POST_VS, fragmentShader: fs, depthTest: false, depthWrite: false });
      this.bright = mk(BRIGHT_FS, { tColor: { value: null } });
      this.blur = mk(BLUR_FS, { tColor: { value: null }, uDir: { value: new THREE.Vector2() } });
      this.comp = mk(COMP_FS, { tColor: { value: null }, tDepth: { value: null }, tBloom: { value: null }, uRes: { value: new THREE.Vector2() }, uNear: { value: 0.1 }, uFar: { value: 200 }, uTime: { value: 0 }, uCine: { value: 0 }, uHaze: { value: new THREE.Color(0x1c1830) }, uPx: { value: 1 } });
    }
    setSize(w, h, pr) {
      const W = Math.max(4, Math.round(w * pr)), H = Math.max(4, Math.round(h * pr));
      this.rt.setSize(W, H); this.bA.setSize(W >> 2, H >> 2); this.bB.setSize(W >> 2, H >> 2);
      this.comp.uniforms.uRes.value.set(W, H);
      this.comp.uniforms.uPx.value = Math.max(1, H / 900); // line width grows with the screen, about 1px at 900p
    }
    pass(mat, target) { this.quad.material = mat; this.r.setRenderTarget(target); this.r.render(this.qs, this.qc); }
    render(scene, cam, t) {
      const r = this.r;
      r.setRenderTarget(this.rt); r.render(scene, cam);
      this.bright.uniforms.tColor.value = this.rt.texture; this.pass(this.bright, this.bA);
      for (let i = 0; i < 2; i++) {
        this.blur.uniforms.tColor.value = this.bA.texture; this.blur.uniforms.uDir.value.set(1 / this.bA.width, 0); this.pass(this.blur, this.bB);
        this.blur.uniforms.tColor.value = this.bB.texture; this.blur.uniforms.uDir.value.set(0, 1 / this.bA.height); this.pass(this.blur, this.bA);
      }
      const u = this.comp.uniforms;
      u.tColor.value = this.rt.texture; u.tDepth.value = this.rt.depthTexture; u.tBloom.value = this.bA.texture;
      u.uNear.value = cam.near; u.uFar.value = cam.far; u.uTime.value = t;
      this.pass(this.comp, null);
    }
  }

  // ------------------------------------------------------------------ CYCLONE whirlwind (versus and campaign)
  let cycTex = null;
  const cyclone = () => {
    if (!cycTex) cycTex = canvasTex(256, 128, (g) => {
      g.clearRect(0, 0, 256, 128); g.lineCap = 'round';
      for (let i = 0; i < 14; i++) { const y = 8 + Math.random() * 112, x = Math.random() * 256, l = 50 + Math.random() * 110; g.strokeStyle = 'rgba(255,255,255,' + (0.35 + Math.random() * 0.6) + ')'; g.lineWidth = 2 + Math.random() * 5; g.beginPath(); g.moveTo(x, y); g.lineTo(x + l, y - l * 0.12); g.stroke(); }
    });
    const grp = new THREE.Group();
    const mat = () => { const t = cycTex.clone(); t.wrapS = THREE.RepeatWrapping; t.needsUpdate = true; return new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, opacity: 0.55, color: 0xdff4ff }); };
    const funnel = new THREE.Mesh(new THREE.CylinderGeometry(1.35, 0.55, 2.4, 28, 1, true), mat()); funnel.position.y = 1.2; grp.add(funnel);
    const inner = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 0.45, 2.0, 24, 1, true), mat()); inner.position.y = 1.0; inner.material.opacity = 0.35; grp.add(inner);
    const rings = [0.25, 0.9, 1.6].map((y, i) => { const r = new THREE.Mesh(new THREE.TorusGeometry(0.9 + i * 0.2, 0.025, 6, 40), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.7, depthWrite: false })); r.rotation.x = Math.PI / 2; r.position.y = y; grp.add(r); return r; });
    grp.userData = { funnel, inner, rings, t: 0 };
    return grp;
  };
  const cycloneUpdate = (grp, x, z, s, k, dt) => {
    const U = grp.userData; U.t += dt;
    grp.visible = k > 0.01; grp.position.set(x, 0, z); grp.scale.set(s * (0.6 + 0.4 * k), s, s * (0.6 + 0.4 * k));
    U.funnel.rotation.y -= dt * 14; U.inner.rotation.y -= dt * 20;
    U.funnel.material.map.offset.x -= dt * 2.5; U.inner.material.map.offset.x -= dt * 3.5;
    U.funnel.material.opacity = 0.55 * k; U.inner.material.opacity = 0.35 * k;
    U.rings.forEach((r, i) => { r.rotation.z += dt * (9 + i * 3); const p = 1 + 0.12 * Math.sin(U.t * 12 + i * 2); r.scale.set(p, p, 1); r.material.opacity = 0.7 * k; });
  };

  S.R3.cyclone = cyclone; S.R3.cycloneUpdate = cycloneUpdate;

  // ------------------------------------------------------------------ Renderer
  class Renderer {
    constructor(el) {
      this.el = el;
      const r = this.r = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
      // resolution: phones start a little under their (very high) native density; perf() then trims or restores it
      this.prMax = Math.min(S.touch && S.touch.on ? 1.5 : 2, window.devicePixelRatio || 1); this.pr = Math.min(1.5, this.prMax); this.prFail = 9; this.ft = 1 / 60; this.ftT = 0; // retina starts at 1.5x: the ink pass keeps edges crisp
      r.setPixelRatio(this.pr);
      el.appendChild(r.domElement);
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0x150c14);
      this.cam = new THREE.PerspectiveCamera(34, 1, 0.1, 200);
      this.fx = new FX(this.scene); this.fx.scene = this.scene; this.fx.sandy = true;
      this.views = [];
      this.ref = new RefView(this.scene);
      this.buildArena();
      this.buildCrowd();
      this.cs = { fx: 0, fz: 0, tight: 0, kick: 0, shake: 0, yaw: 0, orbit: false, focusW: 0, fox: 0, foz: 0 };
      this.time = 0; this.excite = 0;
      this.setAnime(window.KUMITE_STYLE === 'anime');
      this.resize();
      addEventListener('resize', () => this.resize());
    }
    // the anime look: crisper toon shading, bolder outlines, hard shadows and the ink / grade pass
    setAnime(on) {
      this.anime = !!on; SH.uAnime.value = on ? 1 : 0; SH.uOL.value = on ? 1.35 : 1;
      this.applyArena();
      if (on && !this.post) { this.post = new AnimePost(this.r); this.resize(); }
    }
    // classic look: the square dohyo in a hall full of people. Anime look: a round stage in a black void,
    // no audience (you still hear them), no corner props: one spotlight and the two of them.
    applyArena() {
      const classic = this.classicStage !== false, boss = classic && this.anime;
      if (this.dohyoG) this.dohyoG.visible = classic && !boss;
      if (this.bossG) this.bossG.visible = boss;
      if (this.crowdG) this.crowdG.visible = classic && !boss;
      if (this.floorM) this.floorM.visible = classic && !boss;
      if (this.banners) for (const b of this.banners) b.visible = classic && !boss;
      if (this.coneM) this.coneM.visible = classic && !boss; // against pure black the beam reads as a grey slab
      if (classic) this.scene.background.set(boss ? 0x000000 : 0x150c14); // themed stages set their own sky
      const d3 = boss && this.ring3d && this.ring3d.length > 0;          // the modelled dohyo replaces the painted one
      if (this.flat2d) for (const o of this.flat2d) o.visible = !d3 && (o.parent === this.spinG ? classic : true);
      if (this.ring3d) for (const o of this.ring3d) o.visible = d3;
    }
    // adaptive resolution: if frames run slow for a moment, render fewer pixels; if there is plenty of headroom, add them back
    perf(dt) {
      if (!(dt > 0) || dt > 0.25) return; // tab switches and hitches are not the steady frame rate
      this.ft += (dt - this.ft) * 0.05; this.ftT += dt;
      if (this.ftT < 1.2) return;
      let pr = this.pr;
      if (this.ft > 1 / 45) { this.prFail = Math.min(this.prFail, pr); pr = Math.max(0.75, pr - 0.15); }
      else if (this.ft < 1 / 58 && this.ftT > 4 && pr + 0.1 < this.prFail - 0.01) pr = Math.min(this.prMax, pr + 0.1); // never climb back to a level that was too slow (no see-saw)
      else return;
      this.ftT = 0;
      if (Math.abs(pr - this.pr) < 0.01) return;
      this.pr = pr; this.r.setPixelRatio(pr); this.resize();
      if (S.game && S.game.camp && S.game.camp.resize) S.game.camp.resize();
    }
    resize() {
      const w = innerWidth, h = innerHeight;
      this.r.setSize(w, h);
      if (this.post) this.post.setSize(w, h, this.r.getPixelRatio());
      this.cam.aspect = w / h; this.cam.updateProjectionMatrix();
      this.fx.pmat.uniforms.uScale.value = h * this.r.getPixelRatio() / (2 * Math.tan(this.cam.fov * Math.PI / 360));
    }

    paintRing(g, W) {
      const half = this.half, px = W / (half * 2), C = W / 2;
      const P = (u) => C + u * px;
      // clay base
      g.fillStyle = '#b4855a'; g.fillRect(0, 0, W, W);
      // outer sand (janome) band outside the bales
      g.fillStyle = '#d6bd93'; g.beginPath(); g.arc(C, C, (R + 0.95) * px, 0, Math.PI * 2); g.fill();
      g.fillStyle = '#c9a06f'; g.beginPath(); g.arc(C, C, (R + 0.28) * px, 0, Math.PI * 2); g.fill();
      // spotlight pool
      let gr = g.createRadialGradient(C - 0.6 * px, C - 0.8 * px, 0, C, C, (R + 0.3) * px);
      gr.addColorStop(0, 'rgba(255,236,200,0.38)'); gr.addColorStop(0.65, 'rgba(255,220,170,0.12)'); gr.addColorStop(1, 'rgba(90,40,30,0.12)');
      g.fillStyle = gr; g.beginPath(); g.arc(C, C, (R + 0.28) * px, 0, Math.PI * 2); g.fill();
      // grain
      for (let i = 0; i < 9000; i++) {
        const x = Math.random() * W, y = Math.random() * W, l = Math.random();
        g.fillStyle = l < 0.5 ? 'rgba(80,45,30,0.08)' : 'rgba(255,240,215,0.07)';
        g.fillRect(x, y, 1 + Math.random() * 2.5, 1 + Math.random() * 2.5);
      }
      // sweep strokes in the sand
      g.strokeStyle = 'rgba(255,240,215,0.07)'; g.lineWidth = 2;
      for (let i = 0; i < 60; i++) { g.beginPath(); g.arc(C, C, (R + 0.35 + Math.random() * 0.55) * px, Math.random() * 6, Math.random() * 6 + 0.6); g.stroke(); }
      // boundary line just inside the bales: always readable
      g.strokeStyle = 'rgba(255,248,230,0.55)'; g.lineWidth = 0.05 * px;
      g.beginPath(); g.arc(C, C, (R - 0.02) * px, 0, Math.PI * 2); g.stroke();
      // shikiri-sen
      g.fillStyle = '#fbf6ea';
      for (const sx of [-0.62, 0.62]) g.fillRect(P(sx - 0.035), P(-0.45), 0.07 * px, 0.9 * px);
      // edge of platform
      gr = g.createLinearGradient(0, 0, 0, W);
      g.strokeStyle = 'rgba(60,30,25,0.6)'; g.lineWidth = 6; g.strokeRect(3, 3, W - 6, W - 6);
      void gr;
    }

    buildArena() {
      const sc = this.scene;
      const half = this.half = R + 1.55;
      // floor
      const floorTex = canvasTex(512, 512, (g, w) => {
        const gr = g.createRadialGradient(w / 2, w / 2, 20, w / 2, w / 2, w / 2);
        gr.addColorStop(0, '#4a2a24'); gr.addColorStop(0.25, '#2a1719'); gr.addColorStop(1, '#0e080c');
        g.fillStyle = gr; g.fillRect(0, 0, w, w);
      });
      const floor = new THREE.Mesh(new THREE.PlaneGeometry(90, 90).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: floorTex }));
      floor.position.y = -0.62; sc.add(floor); this.floorM = floor;
      // platform (square frustum)
      let pg = new THREE.CylinderGeometry(half * Math.SQRT2, (half + 0.6) * Math.SQRT2, 0.62, 4, 1, true).toNonIndexed();
      pg.computeVertexNormals();
      const plat = new THREE.Mesh(pg, toon(0xae7a51, { shade: 0x6b3d33, rimAmt: 0.2 }));
      // everything that belongs to the classic dohyo lives in one group, so a themed stage can replace it
      this.dohyoG = new THREE.Group(); sc.add(this.dohyoG);
      plat.rotation.y = Math.PI / 4; plat.position.y = -0.31; this.dohyoG.add(plat);
      // top surface
      this.ringTex = canvasTex(2048, 2048, (g, W) => this.paintRing(g, W));
      const top = new THREE.Mesh(new THREE.PlaneGeometry(half * 2, half * 2).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: this.ringTex }));
      top.position.y = 0.0; this.dohyoG.add(top);
      // ROTATING RING: a round turntable cut from the same painted surface, with the straw on it, turns on its own
      this.spinG = new THREE.Group(); sc.add(this.spinG);
      const rc = R + 0.3, disc = new THREE.CircleGeometry(rc, 72).rotateX(-Math.PI / 2), uv = disc.attributes.uv;
      for (let i = 0; i < uv.count; i++) uv.setXY(i, 0.5 + (uv.getX(i) - 0.5) * rc / half, 0.5 + (uv.getY(i) - 0.5) * rc / half);
      const turn = new THREE.Mesh(disc, new THREE.MeshBasicMaterial({ map: this.ringTex })); turn.position.y = 0.004; turn.userData.dohyo = true; this.spinG.add(turn);
      this.flat2d = [turn];
      const seam = new THREE.Mesh(new THREE.RingGeometry(rc - 0.02, rc + 0.03, 96).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x5a3a24 })); seam.position.y = 0.006; this.dohyoG.add(seam);
      // tawara: straw bales ring with the four gaps
      const straw = toon(0xdcc58c, { shade: 0x9a7c52, rimAmt: 0.4 });
      const gap = 0.14, arc = Math.PI / 2 - gap;
      for (let k = 0; k < 4; k++) {
        const g = new THREE.Group(); g.rotation.y = k * Math.PI / 2 + gap / 2;
        const t = mesh(new THREE.TorusGeometry(R + 0.13, 0.13, 8, 48, arc), straw, 0.02);
        t.rotation.x = -Math.PI / 2; t.position.y = 0.03; g.add(t); g.userData.dohyo = true; this.spinG.add(g); this.flat2d.push(g);
        // straw bands
        for (let j = 1; j < 6; j++) {
          const a = j / 6 * arc;
          const b = new THREE.Mesh(new THREE.TorusGeometry(0.135, 0.018, 5, 12), toon(0x8a6a3c, { shade: 0x5a4024, rimAmt: 0 }));
          b.position.set(Math.cos(a) * (R + 0.13), 0.03, -Math.sin(a) * (R + 0.13));
          b.rotation.y = a; g.add(b);
        }
      }
      // outer square bales
      const sideLen = half * 2 - 0.5;
      const cg = new THREE.CapsuleGeometry(0.12, sideLen, 3, 10);
      for (let k = 0; k < 4; k++) {
        const b = mesh(cg, straw, 0.02);
        b.rotation.z = Math.PI / 2;
        const g = new THREE.Group(); g.rotation.y = k * Math.PI / 2; g.add(b);
        b.position.set(0, 0.05, half - 0.22);
        this.dohyoG.add(g);
      }
      // ANIME LOOK: a round raised stage floating in a black void under one spotlight ("final boss" arena).
      // It replaces the square platform (dohyoG); the ring, its straw and the referee stay as they are.
      {
        const rT = R + 1.6, bg = this.bossG = new THREE.Group(); bg.visible = false; sc.add(bg);
        const disc = new THREE.CircleGeometry(rT, 96).rotateX(-Math.PI / 2), uv = disc.attributes.uv;
        for (let i = 0; i < uv.count; i++) uv.setXY(i, 0.5 + (uv.getX(i) - 0.5) * rT / half, 0.5 + (uv.getY(i) - 0.5) * rT / half);
        const topM = new THREE.Mesh(disc, new THREE.MeshBasicMaterial({ map: this.ringTex })); topM.position.y = -0.002; bg.add(topM);
        const side = new THREE.Mesh(new THREE.CylinderGeometry(rT, rT - 0.25, 0.7, 96, 1, true), toon(0x4a2a2e, { shade: 0x120810, rim: 0xffc890, rimAmt: 0.7 }));
        side.position.y = -0.35; bg.add(side);
        const lip = new THREE.Mesh(new THREE.TorusGeometry(rT, 0.05, 6, 96), toon(0xe2c48c, { shade: 0x7a5a3a, rimAmt: 0.6 }));
        lip.rotation.x = Math.PI / 2; lip.position.y = 0.0; bg.add(lip);
        this.flat2d.push(topM, side, lip);
        // the spotlight falls off towards the edge of the stage
        const vig = canvasTex(512, 512, (g, w) => {
          const gr = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
          gr.addColorStop(0, 'rgba(8,3,10,0)'); gr.addColorStop(0.62, 'rgba(8,3,10,0)'); gr.addColorStop(0.9, 'rgba(8,3,10,0.38)'); gr.addColorStop(1, 'rgba(8,3,10,0.6)');
          g.fillStyle = gr; g.fillRect(0, 0, w, w);
        });
        const vm = new THREE.Mesh(new THREE.CircleGeometry(rT + 0.02, 96).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: vig, transparent: true, depthWrite: false }));
        vm.position.y = 0.009; vm.renderOrder = 1; bg.add(vm);
        // the modelled dohyo (tools/blender/dohyo.py -> assets/models/dohyo.glb): a raised clay mound with swept sand,
        // half-buried straw bales, the start lines and loose sand. Once it has loaded it replaces the painted stage
        // and the toon straw in the boss arena. Bales and lines ride the turntable; the clay stays put.
        this.ring3d = [];
        new THREE.GLTFLoader().load('assets/models/dohyo.glb', (gl) => {
          gl.scene.updateMatrixWorld(true);
          for (const [name, parent, th] of [['Mound', bg, 0], ['Sand', bg, 0], ['Tawara', this.spinG, 0.012], ['Shikiri', this.spinG, 0.006]]) {
            const src = gl.scene.getObjectByName(name); if (!src) continue;
            const grp = new THREE.Group();
            src.traverse((o) => {
              if (!o.isMesh) return;
              const sm = o.material, col = sm.color ? sm.color.clone().convertLinearToSRGB() : new THREE.Color(1, 1, 1);
              if (name === 'Mound' || name === 'Sand') col.multiply(new THREE.Color(0.8, 0.82, 0.86)); // calmer clay under the comic grade
              const m = mesh(o.geometry, toon(col.getHex(), { shade: col.clone().multiply(new THREE.Color(0.62, 0.52, 0.5)).getHex(), map: sm.map || undefined, rimAmt: 0.15 }), th);
              if (name === 'Mound') { // the clay shell came out of Blender wound inside out: draw both faces, normals facing up/out
                m.material.side = THREE.DoubleSide;
                const nr = o.geometry.attributes.normal; let sy = 0; for (let i = 0; i < nr.count; i++) sy += nr.getY(i);
                if (sy < 0) { for (let i = 0; i < nr.count; i++) nr.setXYZ(i, -nr.getX(i), -nr.getY(i), -nr.getZ(i)); nr.needsUpdate = true; }
              }
              m.applyMatrix4(o.matrixWorld); grp.add(m);
            });
            parent.add(grp); this.ring3d.push(grp);
          }
          this.applyArena();
        }, undefined, () => {});
      }
      // salt box + water bucket corners
      const wood = toon(0x6d4430, { shade: 0x3c2219 });
      for (const [x, z] of [[half - 0.6, half - 0.6], [-half + 0.6, half - 0.6]]) {
        const b = mesh(GEO.box, wood, 0.02); b.scale.set(0.45, 0.35, 0.45); b.position.set(x, 0.17, z); this.dohyoG.add(b);
        const s = mesh(GEO.sphereLo, toon(0xf6f2ea, { shade: 0xb8b0c8 }), 0.015); s.scale.set(0.18, 0.08, 0.18); s.position.set(x, 0.36, z); this.dohyoG.add(s);
      }
      // floating motes in the light
      const mg = new THREE.BufferGeometry(), mp = new Float32Array(240 * 3);
      for (let i = 0; i < 240; i++) { const a = Math.random() * 6.28, rr = Math.sqrt(Math.random()) * 8; mp[i * 3] = Math.cos(a) * rr; mp[i * 3 + 1] = Math.random() * 5; mp[i * 3 + 2] = Math.sin(a) * rr; }
      mg.setAttribute('position', new THREE.BufferAttribute(mp, 3));
      const dotTex = canvasTex(32, 32, (g) => { const gr = g.createRadialGradient(16, 16, 0, 16, 16, 15); gr.addColorStop(0, 'rgba(255,230,190,1)'); gr.addColorStop(1, 'rgba(255,230,190,0)'); g.fillStyle = gr; g.fillRect(0, 0, 32, 32); });
      this.motes = new THREE.Points(mg, new THREE.PointsMaterial({ size: 0.07, map: dotTex, transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending }));
      sc.add(this.motes);
      // god-ray cone
      const coneTex = canvasTex(4, 256, (g) => { const gr = g.createLinearGradient(0, 0, 0, 256); gr.addColorStop(0, 'rgba(255,225,180,0.0)'); gr.addColorStop(0.5, 'rgba(255,225,180,0.05)'); gr.addColorStop(1, 'rgba(255,225,180,0.11)'); g.fillStyle = gr; g.fillRect(0, 0, 4, 256); });
      const cone = new THREE.Mesh(new THREE.CylinderGeometry(3.5, 8.5, 14, 40, 1, true), new THREE.MeshBasicMaterial({ map: coneTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
      cone.position.y = 6.5; sc.add(cone); this.coneM = cone;
    }

    // ---- the crowd: the original simple spectators, as dark silhouettes lit round the edges (dohyo stage only)
    buildCrowd() {
      const pos = [];
      for (let side = 0; side < 4; side++) {
        for (let row = 0; row < 8; row++) {
          const D = 7.6 + row * 0.85, y = -0.62 + row * 0.42;
          for (let t = -D + 0.5; t < D - 0.3; t += 0.64 + Math.random() * 0.1) {
            const j = (Math.random() - 0.5) * 0.15;
            let x, z;
            if (side === 0) { x = t; z = -D + j; } else if (side === 1) { x = D + j; z = t; } else if (side === 2) { x = -t; z = D + j; } else { x = -D + j; z = -t; }
            pos.push([x, y, z, Math.random() * 6.28, Math.random()]);
          }
        }
      }
      const N = pos.length;
      this.crowdPos = pos;
      const sil = { shade: 0x050305, rim: 0xffb070, rimAmt: 0.9 };
      const bodyMat = toon(0xffffff, sil), headMat = toon(0xffffff, sil);
      this.crowdB = new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.21, 0.3, 3, 8), bodyMat, N);
      this.crowdH = new THREE.InstancedMesh(new THREE.SphereGeometry(0.13, 10, 8), headMat, N);
      const col = new THREE.Color();
      for (let i = 0; i < N; i++) {
        col.setRGB(0.07, 0.05, 0.065).multiplyScalar(0.8 + Math.random() * 0.4); // near-black, with a little variety
        this.crowdB.setColorAt(i, col); this.crowdH.setColorAt(i, col);
      }
      this.crowdB.frustumCulled = this.crowdH.frustumCulled = false;
      this.crowdG = new THREE.Group(); this.crowdG.add(this.crowdB, this.crowdH); this.scene.add(this.crowdG);
      this.m4 = new THREE.Matrix4();
      this.updateCrowd(0, 0, 0, 0);
    }
    crowdReact() { this.crowdBurst = 1.4; }
    updateCrowd(T, ex, dt, raw) {
      if (!this.crowdPos || !this.crowdG.visible) return;
      raw = raw || 0;
      if (raw - (this.lastExcite || 0) > 0.4 && raw > 0.9) this.crowdBurst = 1.6;
      this.lastExcite = raw; this.crowdBurst = Math.max(0, (this.crowdBurst || 0) - (dt || 0));
      const m = this.m4, N = this.crowdPos.length, burst = this.crowdBurst > 0 ? 1 : 0;
      for (let i = 0; i < N; i++) {
        const p = this.crowdPos[i];
        const jump = burst && p[4] < 0.55 ? Math.abs(Math.sin(T * 9 + p[3])) * 0.3 : 0; // on big moments about half of them leap up
        const b = Math.max(0, Math.sin(T * (7 + (i % 5)) + p[3])) * 0.16 * ex + Math.sin(T * 1.3 + p[3]) * 0.01 + jump;
        m.makeTranslation(p[0], p[1] + 0.36 + b, p[2]); this.crowdB.setMatrixAt(i, m);
        m.makeTranslation(p[0], p[1] + 0.78 + b * 1.1, p[2]); this.crowdH.setMatrixAt(i, m);
      }
      this.crowdB.instanceMatrix.needsUpdate = true; this.crowdH.instanceMatrix.needsUpdate = true;
    }

    setWrestlers(archs, loadouts, names) {
      for (const v of this.views) v.dispose(this.scene);
      this.views = archs.map((a, i) => new WrestlerView(this.scene, a, this.fx, loadouts && loadouts[i]));
      // everyone fights masked, like the campaign: two different masks each match (cosmetic in versus)
      if (S.CampSkills) {
        const pool = ['oni', 'tengu', 'kitsune', 'hannya', 'okame'], m0 = pool[(Math.random() * pool.length) | 0];
        const m1 = pool.filter((k) => k !== m0)[(Math.random() * (pool.length - 1)) | 0];
        this.views.forEach((v, i) => { const mk = S.CampSkills.maskMesh(i ? m1 : m0); if (mk && v.head) { mk.scale.setScalar(v.s || 1); v.head.add(mk); v.maskId = i ? m1 : m0; } });
      }
      this.fx.clearDecals();
      this.clearObjs(); this.clearThrown();
      this.buildBanners(loadouts, names || ['', '']);
    }

    // ---- corner banners (nobori) in each wrestler's colours
    buildBanners(loadouts, names) {
      if (this.banners) for (const b of this.banners) this.scene.remove(b);
      this.banners = [];
      for (let i = 0; i < 2; i++) {
        const it = S.item((loadouts && loadouts[i] && loadouts[i].banner) || 'bn_ink') || {};
        const tex = canvasTex(128, 384, (g, W, H) => {
          S.patDraw(g, W, H, it.pat || 'solid', it.c1 || '#170c12', it.c2 || '#e2322b');
          g.fillStyle = 'rgba(0,0,0,0.35)'; g.fillRect(W * 0.2, 20, W * 0.6, H - 40);
          g.fillStyle = '#fff8ec'; g.font = 'bold 34px "Dela Gothic One", sans-serif'; g.textAlign = 'center';
          const nm = (names[i] || '').slice(0, 9);
          for (let k = 0; k < nm.length; k++) g.fillText(nm[k], W / 2, 60 + k * 36);
        });
        const grp = new THREE.Group();
        const pole = mesh(new THREE.CylinderGeometry(0.04, 0.04, 4.2, 8), toon(0x3a2418, { shade: 0x1a0e0a }), 0.015); pole.position.y = 1.5; grp.add(pole);
        const flag = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 2.7), new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide }));
        flag.position.set(i ? -0.48 : 0.48, 2.1, 0); grp.add(flag);
        grp.position.set((i ? 1 : -1) * (this.half + 0.9), -0.6, -(this.half - 0.4));
        grp.userData.flag = flag;
        this.scene.add(grp); this.banners.push(grp);
      }
    }

    // ---- what the crowd throws in when someone wins
    crowdThrow(kind, x, z) {
      this.clearThrown();
      const n = kind === 'petals' || kind === 'confetti' ? 70 : 26;
      const mk = () => {
        let g, m;
        const pal = [0xe2322b, 0x2b3d93, 0x2fa98f, 0xf0c35a, 0x7a3b8c, 0xf2a7c0];
        const col = pal[(Math.random() * pal.length) | 0];
        switch (kind) {
          case 'flowers': g = new THREE.Group(); g.add(mesh(new THREE.SphereGeometry(0.11, 8, 6), toon(0xf06aa0, { shade: 0x9a2a60 }), 0.01)); { const st = mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.35, 5), toon(0x3a8a3a), 0); st.position.y = -0.18; g.add(st); } return g;
          case 'petals': m = new THREE.Mesh(new THREE.PlaneGeometry(0.09, 0.07), new THREE.MeshBasicMaterial({ color: Math.random() < 0.5 ? 0xffc0d6 : 0xffe4ee, side: THREE.DoubleSide })); return m;
          case 'confetti': m = new THREE.Mesh(new THREE.PlaneGeometry(0.08, 0.05), new THREE.MeshBasicMaterial({ color: col, side: THREE.DoubleSide })); return m;
          case 'coins': return mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.025, 14), toon(0xf0c35a, { shade: 0x9a6a2a, spec: 0.7 }), 0.008);
          default: { const c = mesh(GEO.box, toon(col, { shade: new THREE.Color(col).multiplyScalar(0.5).getHex() }), 0.012); c.scale.set(0.5, 0.08, 0.5); return c; }
        }
      };
      this.thrown = [];
      for (let k = 0; k < n; k++) {
        const o = mk();
        const a = Math.random() * Math.PI * 2, R0 = 9 + Math.random() * 3;
        o.position.set(Math.cos(a) * R0, 2 + Math.random() * 2, Math.sin(a) * R0);
        const tx = x + (Math.random() - 0.5) * 6, tz = z + (Math.random() - 0.5) * 6, ft = 0.9 + Math.random() * 0.9;
        const light = kind === 'petals' || kind === 'confetti';
        o.userData = { vx: (tx - o.position.x) / ft, vz: (tz - o.position.z) / ft, vy: (0.1 - o.position.y + 0.5 * 9 * ft * ft) / ft, light, delay: Math.random() * 0.6, sp: (Math.random() - 0.5) * 10 };
        o.visible = false;
        this.scene.add(o); this.thrown.push(o);
      }
    }
    clearThrown() { if (this.thrown) for (const o of this.thrown) this.scene.remove(o); this.thrown = []; }
    updateThrown(dt) {
      for (const o of this.thrown || []) {
        const u = o.userData;
        if (u.delay > 0) { u.delay -= dt; continue; }
        o.visible = true;
        if (o.position.y <= 0.05 && !u.light) continue;
        if (u.light) { u.vx *= Math.exp(-dt * 1.2); u.vz *= Math.exp(-dt * 1.2); u.vy = Math.max(u.vy - 9 * dt, -1.2); }
        else u.vy -= 9 * dt;
        o.position.x += u.vx * dt; o.position.y = Math.max(0.05, o.position.y + u.vy * dt); o.position.z += u.vz * dt;
        if (o.position.y > 0.05) { o.rotation.x += u.sp * dt; o.rotation.z += u.sp * 0.7 * dt; } else { o.rotation.x = u.light ? -Math.PI / 2 : 0; o.rotation.z = 0; }
      }
    }

    // ---- anime fire pieces (made once, shared)
    flameTextures() {
      if (this._flameTex) return this._flameTex;
      const tongue = (g, w, h, lean, sc) => { // a flame tongue rooted at the bottom middle
        const cx = w / 2, b = h * 0.97, t = h * (1 - sc) + h * 0.03, hw = w * 0.42 * sc;
        g.beginPath(); g.moveTo(cx, b);
        g.bezierCurveTo(cx - hw * 1.15, b - h * 0.06, cx - hw * 1.05, b - (b - t) * 0.55, cx - hw * 0.2 + lean * 0.4, b - (b - t) * 0.78);
        g.quadraticCurveTo(cx + lean * 0.6, b - (b - t) * 0.86, cx + lean, t);
        g.quadraticCurveTo(cx + hw * 0.55 + lean * 0.3, b - (b - t) * 0.7, cx + hw * 0.45, b - (b - t) * 0.55);
        g.bezierCurveTo(cx + hw * 1.2, b - (b - t) * 0.35, cx + hw * 1.1, b - h * 0.05, cx, b);
        g.closePath();
      };
      this._flameTex = [-18, 6, 22].map((lean) => canvasTex(128, 256, (g) => {
        g.lineJoin = 'round';
        tongue(g, 128, 256, lean, 1); g.fillStyle = '#d8261a'; g.fill(); g.lineWidth = 7; g.strokeStyle = '#2a0806'; g.stroke(); // ink outline
        tongue(g, 128, 256, lean * 0.8, 0.74); g.fillStyle = '#ff7a1c'; g.fill();
        tongue(g, 128, 256, lean * 0.6, 0.48); g.fillStyle = '#ffd34a'; g.fill();
        tongue(g, 128, 256, lean * 0.4, 0.24); g.fillStyle = '#fff6d2'; g.fill();
      }));
      return this._flameTex;
    }
    scorchTexture() {
      if (this._scorch) return this._scorch;
      this._scorch = canvasTex(256, 256, (g) => {
        const c = 128, gr = g.createRadialGradient(c, c, 10, c, c, 126);
        gr.addColorStop(0, 'rgba(26,8,4,0.85)'); gr.addColorStop(0.7, 'rgba(40,12,4,0.7)'); gr.addColorStop(0.86, 'rgba(255,110,20,0.75)'); gr.addColorStop(1, 'rgba(255,110,20,0)');
        g.fillStyle = gr; g.beginPath(); g.arc(c, c, 126, 0, Math.PI * 2); g.fill();
        g.strokeStyle = 'rgba(255,150,40,0.8)'; g.lineWidth = 2.5; // glowing cracks
        for (let k = 0; k < 11; k++) { let a = k / 11 * Math.PI * 2, r = 20; g.beginPath(); g.moveTo(c + Math.cos(a) * r, c + Math.sin(a) * r); while (r < 104) { r += 12 + Math.random() * 10; a += (Math.random() - 0.5) * 0.5; g.lineTo(c + Math.cos(a) * r, c + Math.sin(a) * r); } g.stroke(); }
      });
      return this._scorch;
    }
    glowTexture() {
      if (this._glow) return this._glow;
      this._glow = canvasTex(128, 128, (g) => { const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,0.9)'); gr.addColorStop(0.5, 'rgba(255,255,255,0.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); });
      return this._glow;
    }
    // ---- gacha skill objects
    clearObjs() { if (this.objMeshes) for (const [, me] of this.objMeshes) { this.scene.remove(me); if (me.userData.views) for (const v of me.userData.views) v.dispose(this.scene); } this.objMeshes = new Map(); }
    cloudTex() {
      if (!this._cloud) this._cloud = canvasTex(128, 128, (g) => {
        g.fillStyle = '#5a5560'; for (const [x, y, r] of [[64, 70, 40], [40, 60, 28], [88, 58, 30], [64, 44, 30]]) { g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); }
        g.fillStyle = '#9a96a2'; for (const [x, y, r] of [[56, 60, 30], [36, 54, 18], [80, 50, 20]]) { g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); }
      });
      return this._cloud;
    }
    makeObj(ob) {
      const sc = this.scene;
      let me;
      if (ob.type === 'smoke') {
        me = new THREE.Group();
        // about half the ring: a solid wall to the opponent, a thin haze to whoever threw it
        const mine = this.viewer === ob.owner.idx || this.viewer === -1;
        for (let k = 0; k < 70; k++) {
          const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.cloudTex(), transparent: true, depthWrite: false, depthTest: mine }));
          const a = Math.random() * 6.28, r = Math.sqrt(Math.random()) * 3.4;
          sp.position.set(Math.cos(a) * r, 0.3 + Math.random() * 2.6, Math.sin(a) * r); sp.userData.s = 2.2 + Math.random() * 1.6; sp.renderOrder = 9;
          me.add(sp);
        }
      } else if (ob.type === 'banana') {
        me = mesh(new THREE.TorusGeometry(0.16, 0.05, 6, 12, Math.PI * 1.2), toon(0xf6d23a, { shade: 0xb08a1a }), 0.014);
        me.rotation.x = -Math.PI / 2;
      } else if (ob.type === 'trap') {
        me = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.5, 4, 1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x1a0e12, transparent: true, opacity: 0.6, depthWrite: false }));
        me.rotation.y = Math.PI / 4; me.renderOrder = 2;
        const hole = new THREE.Mesh(new THREE.CircleGeometry(0.62, 24).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x050205 }));
        hole.position.y = 0.012; hole.visible = false; me.add(hole); me.userData.hole = hole;
      } else if (ob.type === 'proj') {
        const cols = [0x7a3b8c, 0x2b3d93, 0xe2322b]; // floor cushions (zabuton), as real sumo crowds throw
        me = mesh(GEO.box, toon(cols[ob.kind], { shade: 0x3a2a3a }), 0.012);
        me.scale.set(0.4, 0.07, 0.4);
      } else if (ob.type === 'storm') {
        me = new THREE.Group();
        const ring = new THREE.Mesh(new THREE.RingGeometry(0.7, 0.85, 40).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x8ad8ff, transparent: true, opacity: 0.8, depthWrite: false }));
        ring.position.y = 0.03; me.add(ring); me.userData.ring = ring;
        const bolt = new THREE.Group(); me.add(bolt); me.userData.bolt = bolt;
        const mat = new THREE.MeshBasicMaterial({ color: 0xeefaff }), glow = new THREE.MeshBasicMaterial({ color: 0x6ac8ff, transparent: true, opacity: 0.45, depthWrite: false });
        me.userData.boltMats = [mat, glow];
      } else if (ob.type === 'molotov') {
        // anime fire: ink-outlined flame tongues in red / orange / yellow bands, rising embers, a scorched glowing floor
        me = new THREE.Group();
        const FT = this.flameTextures();
        const bottle = new THREE.Group(); me.add(bottle); me.userData.bottle = bottle;
        const glassM = toon(0x2f9a52, { shade: 0x0f4a24, spec: 0.9 });
        const glass = mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.32, 14), glassM, 0.014); bottle.add(glass);
        const shoulder = mesh(new THREE.SphereGeometry(0.12, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), glassM, 0.012); shoulder.position.y = 0.16; bottle.add(shoulder);
        const neck = mesh(new THREE.CylinderGeometry(0.045, 0.05, 0.16, 10), glassM, 0.01); neck.position.y = 0.3; bottle.add(neck);
        const label = mesh(new THREE.CylinderGeometry(0.123, 0.123, 0.12, 14, 1, true), toon(0xf2e6c8, { shade: 0xb0a080 }), 0); bottle.add(label);
        const rag = mesh(new THREE.ConeGeometry(0.07, 0.2, 7), toon(0xe8dcc0, { shade: 0x9a8a6a }), 0.01); rag.position.y = 0.46; rag.rotation.z = 0.3; bottle.add(rag);
        const tf = new THREE.Sprite(new THREE.SpriteMaterial({ map: FT[0], transparent: true, depthWrite: false })); tf.center.set(0.5, 0.05); tf.scale.set(0.32, 0.55, 1); tf.position.y = 0.52; tf.renderOrder = 11; bottle.add(tf); me.userData.torch = tf;
        // the fire patch
        const patch = new THREE.Group(); me.add(patch); me.userData.patch = patch;
        const scorch = new THREE.Mesh(new THREE.CircleGeometry(1.75, 48).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: this.scorchTexture(), transparent: true, depthWrite: false }));
        scorch.position.y = 0.025; patch.add(scorch);
        const glow = new THREE.Mesh(new THREE.CircleGeometry(2.2, 40).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: this.glowTexture(), color: 0xff7a1a, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
        glow.position.y = 0.04; patch.add(glow); me.userData.glow = glow;
        me.userData.flames = [];
        for (let k = 0; k < 22; k++) {
          const a = k * 2.399 + Math.random() * 0.4, r = Math.sqrt((k + 0.5) / 22) * 1.3; // spread evenly over the patch
          const fl = new THREE.Sprite(new THREE.SpriteMaterial({ map: FT[k % FT.length], transparent: true, depthWrite: false }));
          fl.center.set(0.5, 0.04);
          const big = 1 - r / 1.6; fl.userData = { x: Math.cos(a) * r, z: Math.sin(a) * r, w: 0.55 + 0.4 * big + Math.random() * 0.15, h: 1.0 + 1.2 * big + Math.random() * 0.35, ph: Math.random() * 6, v: k % FT.length };
          fl.position.set(fl.userData.x, 0.02, fl.userData.z); fl.renderOrder = 6; patch.add(fl); me.userData.flames.push(fl);
        }
        me.userData.embers = [];
        for (let k = 0; k < 16; k++) {
          const e = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.fx.sparks[0].sp.material.map, color: k % 2 ? 0xffd25a : 0xff8a2a, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
          e.userData = { a: Math.random() * 6.28, r: Math.random() * 1.2, ph: Math.random(), sp: 0.7 + Math.random() * 0.6 }; e.renderOrder = 12; patch.add(e); me.userData.embers.push(e);
        }
      } else if (ob.type === 'konbini') {
        me = new THREE.Group();
        const wall = toon(0xf4f1ea, { shade: 0xb5b0a5 }), glass = toon(0x9fd8f0, { shade: 0x4a8aa8, spec: 0.8 });
        const box = mesh(GEO.box, wall, 0.025); box.scale.set(1.6, 1.4, 1.2); box.position.y = 0.7; me.add(box);
        for (const [c, y] of [[0x2a9a4a, 1.25], [0x2a5ac8, 1.12], [0xe2322b, 0.99]]) { const st = mesh(GEO.box, toon(c), 0); st.scale.set(1.62, 0.1, 1.22); st.position.y = y; me.add(st); }
        const front = mesh(GEO.box, glass, 0.01); front.scale.set(1.2, 0.75, 0.04); front.position.set(0, 0.45, 0.61); me.add(front);
        const roof = mesh(GEO.box, toon(0xd6d2c8, { shade: 0x8a867c }), 0.02); roof.scale.set(1.7, 0.1, 1.3); roof.position.y = 1.45; me.add(roof);
        me.userData.box = me;
      } else if (ob.type === 'bag') {
        me = new THREE.Group();
        const paper = toon(0xb98a55, { shade: 0x6d4a28 });
        const b = mesh(GEO.box, paper, 0.02); b.scale.set(0.5, 0.55, 0.32); b.position.y = 0.28; me.add(b);
        const fold = mesh(GEO.box, toon(0x9a6e40, { shade: 0x5a3c20 }), 0.01); fold.scale.set(0.52, 0.08, 0.34); fold.position.y = 0.58; me.add(fold);
        const tag = mesh(GEO.box, toon(0xe2322b), 0); tag.scale.set(0.2, 0.2, 0.01); tag.position.set(0, 0.3, 0.17); me.add(tag);
        me.userData.b = b;
      } else if (ob.type === 'potato') {
        me = new THREE.Group();
        const b = mesh(new THREE.SphereGeometry(0.26, 16, 12), toon(0x1c1c22, { shade: 0x060608, spec: 0.8 }), 0.02); me.add(b);
        const spark = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.fx.sparks[0].sp.material.map, color: 0xffc040, depthTest: false })); spark.scale.setScalar(0.3); spark.position.y = 0.32; spark.renderOrder = 11; me.add(spark);
        me.userData.body = b;
      } else if (ob.type === 'claw') {
        // an arcade crane claw: chrome hub with a candy band and a blinking lamp, three jointed hooked fingers,
        // a shiny cable, and a pulsing target on the floor so you can see where it will drop
        me = new THREE.Group();
        const chrome = toon(0xdfe5ee, { shade: 0x5d6574, spec: 1 }), band = toon(0xff4fa3, { shade: 0x9a1e5c, spec: 0.6 });
        const cable = mesh(new THREE.CylinderGeometry(0.035, 0.035, 1, 8), toon(0xc8ced8, { shade: 0x4a505c, spec: 1 }), 0); me.add(cable); me.userData.cable = cable;
        const head = new THREE.Group(); head.scale.setScalar(1.7); me.add(head); me.userData.head = head;
        const cap = mesh(new THREE.CylinderGeometry(0.2, 0.3, 0.22, 20), chrome, 0.016); cap.position.y = 0.12; head.add(cap);
        const ring = mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.09, 20), band, 0.014); head.add(ring);
        const base = mesh(new THREE.CylinderGeometry(0.3, 0.16, 0.2, 20), chrome, 0.016); base.position.y = -0.14; head.add(base);
        const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffd23a })); lamp.position.y = 0.27; head.add(lamp); me.userData.lamp = lamp;
        me.userData.prongs = [0, 1, 2].map((k) => {
          const pg = new THREE.Group(); pg.rotation.y = k * 2.094 + 0.5; pg.position.y = -0.2; head.add(pg);
          const knuckle = mesh(new THREE.SphereGeometry(0.075, 12, 8), chrome, 0.012); knuckle.position.set(0.2, -0.02, 0); pg.add(knuckle); // children[0]: sits on the outside
          const upper = mesh(new THREE.BoxGeometry(0.075, 0.5, 0.1), chrome, 0.012); upper.position.set(0.29, -0.25, 0); upper.rotation.z = 0.28; pg.add(upper);
          const joint = mesh(new THREE.SphereGeometry(0.06, 10, 8), band, 0.01); joint.position.set(0.36, -0.49, 0); pg.add(joint);
          const lower = mesh(new THREE.BoxGeometry(0.07, 0.4, 0.09), chrome, 0.012); lower.position.set(0.27, -0.66, 0); lower.rotation.z = -0.62; pg.add(lower);
          const hook = mesh(new THREE.ConeGeometry(0.06, 0.16, 8), chrome, 0.01); hook.position.set(0.15, -0.82, 0); hook.rotation.z = -2.1; pg.add(hook);
          return pg;
        });
        const tgt = new THREE.Group(); me.add(tgt); me.userData.tgt = tgt; tgt.position.y = 0.03;
        const r1 = new THREE.Mesh(new THREE.RingGeometry(1.0, 1.16, 56).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff3b5c, transparent: true, opacity: 0.85, depthWrite: false }));
        const r2 = new THREE.Mesh(new THREE.RingGeometry(0.34, 0.42, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff3b5c, transparent: true, opacity: 0.85, depthWrite: false }));
        tgt.add(r1); tgt.add(r2);
        for (let k = 0; k < 4; k++) { const tick = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.09).rotateX(-Math.PI / 2), r1.material); tick.rotation.y = -k * Math.PI / 2; tick.position.set(Math.cos(k * Math.PI / 2) * 1.36, 0, Math.sin(k * Math.PI / 2) * 1.36); tgt.add(tick); }
        me.userData.tgtMat = r1.material;
      } else if (ob.type === 'doors') {
        me = new THREE.Group();
        const red = toon(0xc2302a, { shade: 0x6a1410 }), dark = new THREE.MeshBasicMaterial({ color: 0x0a0408 });
        me.userData.doors = [0, 1].map(() => {
          const g = new THREE.Group();
          for (const sd of [-1, 1]) { const post = mesh(GEO.box, red, 0.015); post.scale.set(0.16, 2.8, 0.16); post.position.set(sd * 1.05, 1.4, 0); g.add(post); }
          const beam = mesh(GEO.box, red, 0.015); beam.scale.set(2.6, 0.18, 0.2); beam.position.y = 2.85; g.add(beam);
          const hole = new THREE.Mesh(new THREE.PlaneGeometry(1.94, 2.75), dark); hole.position.y = 1.38; g.add(hole);
          const back = hole.clone(); back.rotation.y = Math.PI; g.add(back);
          me.add(g); return g;
        });
      } else if (ob.type === 'pickup') {
        const nm = (S.Skills.BY[ob.id === 'fake' ? ob.fakeOf : ob.id] || { name: '???' }).name;
        const tex = canvasTex(256, 160, (g) => { g.fillStyle = '#f6eddc'; g.fillRect(0, 0, 256, 160); g.strokeStyle = '#d33'; g.lineWidth = 12; g.strokeRect(6, 6, 244, 148); g.fillStyle = '#1a0e14'; g.font = 'bold 30px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; const words = nm.split(' '); words.forEach((wd, i) => g.fillText(wd, 128, 80 + (i - (words.length - 1) / 2) * 34)); });
        me = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.56), new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide }));
      } else if (ob.type === 'train') {
        me = new THREE.Group();
        const lane = new THREE.Group(); me.add(lane); me.userData.lane = lane;
        for (const sd of [-1, 1]) { const st = new THREE.Mesh(new THREE.PlaneGeometry(30, 0.14).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff2a1a, transparent: true, opacity: 0.8, depthWrite: false })); st.position.set(0, 0.03, sd * 1.05); lane.add(st); }
        const fill = new THREE.Mesh(new THREE.PlaneGeometry(30, 2.1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff2a1a, transparent: true, opacity: 0.15, depthWrite: false })); fill.position.y = 0.02; lane.add(fill); me.userData.fill = fill;
        const loco = new THREE.Group(); me.add(loco); me.userData.loco = loco;
        const body = mesh(GEO.box, toon(0x1a1a20, { shade: 0x050508, spec: 0.5 }), 0.03); body.scale.set(7, 2.2, 2.0); body.position.set(-3.5, 1.3, 0); loco.add(body);
        const nose = mesh(GEO.box, toon(0xe2322b, { shade: 0x7a1414 }), 0.03); nose.scale.set(0.6, 2.0, 2.05); nose.position.set(0.15, 1.2, 0); loco.add(nose);
        const lamp = mesh(GEO.sphere, toon(0xfff2a0), 0); lamp.scale.setScalar(0.22); lamp.position.set(0.5, 1.9, 0); loco.add(lamp);
        for (const sd of [-1, 1]) { const stripe = mesh(GEO.box, toon(0xf0c35a), 0); stripe.scale.set(7, 0.18, 0.02); stripe.position.set(-3.5, 1.0, sd * 1.01); loco.add(stripe); }
      } else if (ob.type === 'hole') {
        me = new THREE.Group();
        const core = new THREE.Mesh(new THREE.SphereGeometry(0.22, 16, 12), new THREE.MeshBasicMaterial({ color: 0x050008 })); core.position.y = 0.9; me.add(core);
        me.userData.rings = [0, 1, 2].map((k) => { const r = new THREE.Mesh(new THREE.TorusGeometry(0.4 + k * 0.28, 0.025, 6, 32), new THREE.MeshBasicMaterial({ color: k ? 0x8a3cff : 0xd9a8ff, transparent: true, opacity: 0.8 - k * 0.2, depthWrite: false })); r.position.y = 0.9; r.rotation.x = Math.PI / 2 + 0.3 * k; me.add(r); return r; });
        const disc = new THREE.Mesh(new THREE.CircleGeometry(1.3, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x1a0030, transparent: true, opacity: 0.45, depthWrite: false })); disc.position.y = 0.02; me.add(disc);
      } else if (ob.type === 'fish') {
        me = new THREE.Group();
        const blue = toon(0x2f5585, { shade: 0x18294a, spec: 0.6 }), silver = toon(0xd0d8e0, { shade: 0x7a8694, spec: 0.6 }), yel = toon(0xf0c030, { shade: 0x9a7010 });
        const body = mesh(new THREE.SphereGeometry(1, 20, 14), blue, 0.02); body.scale.set(0.78, 0.27, 0.24); me.add(body);
        const belly = mesh(new THREE.SphereGeometry(1, 18, 10), silver, 0.0); belly.scale.set(0.7, 0.17, 0.22); belly.position.y = -0.08; me.add(belly);
        // forked tail on a narrow stalk
        const tailG = new THREE.Group(); tailG.position.x = -0.74; me.add(tailG);
        const stalk = mesh(new THREE.CylinderGeometry(0.05, 0.09, 0.22, 8), blue, 0.012); stalk.rotation.z = Math.PI / 2; tailG.add(stalk);
        for (const sd of [-1, 1]) { const lobe = mesh(new THREE.ConeGeometry(0.1, 0.42, 4), blue, 0.012); lobe.scale.z = 0.25; lobe.position.set(-0.22, sd * 0.17, 0); lobe.rotation.z = Math.PI / 2 + sd * 0.75; tailG.add(lobe); }
        // dorsal fins on top, a fin underneath, little yellow finlets, side fins
        const dorsal = mesh(new THREE.ConeGeometry(0.11, 0.3, 4), blue, 0.012); dorsal.scale.z = 0.2; dorsal.position.set(0.05, 0.3, 0); dorsal.rotation.z = 0.5; me.add(dorsal);
        const dorsal2 = mesh(new THREE.ConeGeometry(0.06, 0.2, 4), blue, 0.01); dorsal2.scale.z = 0.2; dorsal2.position.set(-0.32, 0.22, 0); dorsal2.rotation.z = 0.6; me.add(dorsal2);
        const anal = mesh(new THREE.ConeGeometry(0.06, 0.2, 4), silver, 0.01); anal.scale.z = 0.2; anal.position.set(-0.32, -0.22, 0); anal.rotation.z = Math.PI - 0.6; me.add(anal);
        for (let k = 0; k < 4; k++) for (const sy of [-1, 1]) { const fl = mesh(new THREE.ConeGeometry(0.03, 0.08, 3), yel, 0); fl.position.set(-0.42 - k * 0.07, sy * (0.17 - k * 0.025), 0); if (sy < 0) fl.rotation.z = Math.PI; me.add(fl); }
        me.userData.pecs = [-1, 1].map((sd) => { const pf = mesh(new THREE.ConeGeometry(0.06, 0.26, 4), blue, 0.01); pf.scale.x = 0.25; pf.position.set(0.28, -0.02, sd * 0.22); pf.rotation.set(sd * 1.2, 0, Math.PI / 2 + 0.6); me.add(pf); return pf; });
        // big eyes on both sides
        for (const sd of [-1, 1]) {
          const w = mesh(GEO.sphere, toon(0xffffff, { shade: 0xc8c8c8 }), 0.006); w.scale.set(0.07, 0.07, 0.03); w.position.set(0.55, 0.06, sd * 0.19); me.add(w);
          const pu = mesh(GEO.sphere, toon(0x111111), 0); pu.scale.set(0.035, 0.04, 0.02); pu.position.set(0.57, 0.06, sd * 0.215); me.add(pu);
        }
        const mouth = mesh(GEO.box, toon(0x151a28), 0); mouth.scale.set(0.1, 0.012, 0.18); mouth.position.set(0.72, -0.04, 0); me.add(mouth);
        me.userData.tail = tailG;
      } else if (ob.type === 'bomb') {
        me = new THREE.Group();
        const b = mesh(new THREE.SphereGeometry(0.34, 18, 14), toon(0x1c1c22, { shade: 0x060608, spec: 0.8 }), 0.02); b.position.y = 0.34; me.add(b);
        const cap = mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.1, 10), toon(0x6d6d74), 0.01); cap.position.y = 0.7; me.add(cap);
        const spark = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.fx.sparks[0].sp.material.map, color: 0xffc040, depthTest: false })); spark.scale.setScalar(0.35); spark.position.y = 0.85; spark.renderOrder = 11; me.add(spark);
        me.userData.body = b; me.userData.spark = spark;
      } else if (ob.type === 'wave') {
        me = new THREE.Mesh(new THREE.RingGeometry(0.85, 1, 48).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xf6eddc, transparent: true, opacity: 0.8, depthWrite: false, side: THREE.DoubleSide }));
        me.position.y = 0.05; me.renderOrder = 3;
      } else if (ob.type === 'third') {
        me = new THREE.Group();
        me.userData.views = [new WrestlerView(this.scene, S.ARCH[ob.arch], this.fx, S.profile.randomLoadout())];
      } else if (ob.type === 'clones') {
        // two more of the same wrestler, built from the same look
        const v = this.views[ob.owner.idx];
        me = new THREE.Group();
        me.userData.views = ob.c.map(() => new WrestlerView(this.scene, v.arch, this.fx, v.lo));
      } else if (ob.type === 'beartrap') {
        me = new THREE.Group();
        const iron = toon(0x55585e, { shade: 0x23252a, spec: 0.6 });
        const base = mesh(new THREE.CylinderGeometry(0.12, 0.14, 0.05, 12), iron, 0.01); base.position.y = 0.03; me.add(base);
        me.userData.jaws = [-1, 1].map((sd) => {
          const j = new THREE.Group(); j.position.set(0, 0.05, 0); me.add(j);
          const arc = mesh(new THREE.TorusGeometry(0.3, 0.03, 6, 14, Math.PI), iron, 0.01); arc.rotation.x = -Math.PI / 2; arc.rotation.z = sd > 0 ? 0 : Math.PI; j.add(arc);
          for (let k = 0; k < 6; k++) { const a = (k + 0.5) / 6 * Math.PI * (sd > 0 ? 1 : -1); const t = mesh(new THREE.ConeGeometry(0.035, 0.12, 4), toon(0xd8dade, { shade: 0x777b83 }), 0.006); t.position.set(Math.cos(a) * 0.29, 0.05, -Math.sin(a) * 0.29); j.add(t); }
          j.userData.sd = sd; return j;
        });
      } else if (ob.type === 'dart') {
        me = new THREE.Group();
        const shaft = mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.4, 6), toon(0xd9d2c4, { shade: 0x8a8070 }), 0.008); shaft.rotation.z = Math.PI / 2; me.add(shaft);
        const tuft = mesh(new THREE.ConeGeometry(0.07, 0.14, 8), toon(0xe2322b, { shade: 0x7a1414 }), 0.008); tuft.rotation.z = Math.PI / 2; tuft.position.x = -0.22; me.add(tuft);
      } else if (ob.type === 'fan') {
        me = new THREE.Group();
        const body = mesh(new THREE.CapsuleGeometry(0.25, 0.5, 4, 8), toon(0x2b3d93, { shade: 0x151a4c }), 0.02); body.position.y = 0.5; me.add(body);
        const head = mesh(GEO.sphere, toon(0xefc3a0, { shade: 0xb87a6c }), 0.02); head.scale.setScalar(0.16); head.position.y = 1.05; me.add(head);
        // two short arms: the fan runs in and bear-hugs them from behind
        me.userData.arms = [0, 1].map(() => { const a = mesh(new THREE.CapsuleGeometry(0.09, 1, 4, 8), toon(0xefc3a0, { shade: 0xb87a6c }), 0.02); me.add(a); return a; });
      } else return null;
      sc.add(me);
      return me;
    }
    updateObjs(game, dt) {
      const m = game.match; if (!this.objMeshes) this.objMeshes = new Map();
      const live = new Set(m ? m.objs : []);
      for (const [ob, me] of this.objMeshes) if (!live.has(ob)) { this.scene.remove(me); if (me.userData.views) for (const v of me.userData.views) v.dispose(this.scene); this.objMeshes.delete(ob); }
      if (!m) return;
      const viewer = this.viewer;
      for (const ob of m.objs) {
        let me = this.objMeshes.get(ob);
        if (!me) { me = this.makeObj(ob); if (!me) continue; this.objMeshes.set(ob, me); }
        if (ob.type === 'smoke') {
          me.position.set(ob.x, 0, ob.z);
          const fade = Math.min(1, ob.t / 0.3) * Math.min(1, (ob.dur - ob.t) / 0.6);
          const mine = viewer === ob.owner.idx || viewer === -1;
          for (const sp of me.children) {
            sp.material.opacity = fade * (mine ? 0.22 : 1);
            const k = sp.userData.s * (0.8 + 0.2 * Math.sin(this.time * 1.5 + sp.position.x));
            sp.scale.set(k, k, 1); sp.material.rotation += dt * 0.2;
          }
        } else if (ob.type === 'banana') { me.position.set(ob.x, 0.05, ob.z); }
        else if (ob.type === 'trap') {
          me.position.set(ob.x, 0.015, ob.z);
          const mine = viewer === ob.owner.idx;
          me.material.opacity = ob.sprung ? 0 : mine ? (ob.armed ? 0.55 : 0.25) : 0;
          me.userData.hole.visible = !!ob.sprung;
        } else if (ob.type === 'proj') {
          me.position.set(ob.x, ob.y, ob.z);
          if (ob.live) { me.rotation.x += dt * 9; me.rotation.z += dt * 6; } else { me.rotation.set(0, me.rotation.y, 0); }
        } else if (ob.type === 'storm') {
          const warn = ob.strikeAt >= 0;
          me.userData.ring.visible = warn; me.userData.ring.position.set(ob.x, 0.03, ob.z);
          if (warn) { const k = 1 - Math.max(0, ob.strikeAt - ob.t) / 0.75; me.userData.ring.scale.setScalar(1.4 - 0.5 * k); me.userData.ring.material.opacity = 0.4 + 0.5 * (Math.sin(this.time * 30) > 0 ? 1 : 0); }
          const bolt = me.userData.bolt;
          if (ob.flash > 0 && ob.bx !== undefined) {
            if (bolt.userData.at !== ob.n) { // a fresh jagged bolt for each strike
              bolt.userData.at = ob.n; while (bolt.children.length) bolt.remove(bolt.children[0]);
              let px = ob.bx, py = 14, pz = ob.bz;
              for (let i = 0; i < 9; i++) {
                const ny = Math.max(0, py - 1.6), nx = i === 8 ? ob.bx : ob.bx + (Math.random() - 0.5) * 1.2, nz = i === 8 ? ob.bz : ob.bz + (Math.random() - 0.5) * 1.2;
                const a = new THREE.Vector3(px, py, pz), b = new THREE.Vector3(nx, ny, nz), len = a.distanceTo(b);
                for (const [mat, th] of [[me.userData.boltMats[1], 0.28], [me.userData.boltMats[0], 0.09]]) {
                  const sgm = new THREE.Mesh(new THREE.CylinderGeometry(th, th, len, 5), mat); sgm.position.copy(a).lerp(b, 0.5); sgm.lookAt(b); sgm.rotateX(Math.PI / 2); bolt.add(sgm);
                }
                px = nx; py = ny; pz = nz;
              }
            }
            bolt.visible = Math.random() > 0.15; me.userData.boltMats[1].opacity = 0.45 * ob.flash;
          } else bolt.visible = false;
        } else if (ob.type === 'molotov') {
          const U = me.userData, FT = this.flameTextures();
          U.bottle.visible = !ob.landed; U.patch.visible = ob.landed;
          if (!ob.landed) {
            U.bottle.position.set(ob.x, ob.y + 0.2, ob.z); U.bottle.rotation.z += dt * 14; U.bottle.rotation.x += dt * 5;
            U.torch.material.map = FT[Math.floor(this.time * 14) % FT.length]; U.torch.scale.set(0.32, 0.5 + 0.15 * Math.sin(this.time * 30), 1);
            if (Math.random() < 0.7) this.fx.spark(ob.x, ob.y + 0.5, ob.z, 0.5);
          } else {
            const life = Math.min(1, ob.t / 0.18) * Math.min(1, (ob.dur - ob.t) / 0.6);
            U.patch.position.set(ob.x, 0, ob.z);
            U.glow.material.opacity = (0.55 + 0.25 * Math.sin(this.time * 11)) * life;
            for (const fl of U.flames) {
              const d = fl.userData, k = 0.78 + 0.32 * Math.abs(Math.sin(this.time * 8.5 + d.ph)) + 0.1 * Math.sin(this.time * 23 + d.ph * 3);
              fl.scale.set(d.w * life * (0.9 + 0.1 * Math.sin(this.time * 13 + d.ph)), d.h * k * life + 0.01, 1);
              fl.material.rotation = Math.sin(this.time * 5 + d.ph) * 0.14; // flames lean and sway
              if (Math.random() < 0.08) { d.v = (d.v + 1) % FT.length; fl.material.map = FT[d.v]; }
            }
            for (const e of U.embers) {
              const d = e.userData, f = (this.time * 0.6 * d.sp + d.ph) % 1;
              e.position.set(Math.cos(d.a + f * 2) * (d.r + f * 0.3), 0.3 + f * 2.4, Math.sin(d.a + f * 2) * (d.r + f * 0.3));
              e.scale.setScalar(0.12 * (1 - f) * life + 0.001); e.material.opacity = (1 - f) * life;
            }
            if (Math.random() < 0.25) this.fx.dust(ob.x + (Math.random() - 0.5) * 2, 1.4, ob.z + (Math.random() - 0.5) * 2, 1, 0.05, 0.9, 0.35); // smoke
          }
        } else if (ob.type === 'konbini') {
          const sh = ob.shake * 0.08;
          me.position.set(ob.x + (Math.random() - 0.5) * sh, 0, ob.z + (Math.random() - 0.5) * sh);
          me.rotation.y = -Math.atan2(-ob.z, -ob.x) + Math.PI / 2; // shop front faces the middle
          const g = Math.min(1, ob.t / 0.25) * Math.min(1, (ob.dur - ob.t) / 0.3); me.scale.setScalar(Math.max(0.01, g));
        } else if (ob.type === 'bag') {
          me.position.set(ob.x, Math.max(0, 6 - ob.t * 14), ob.z); me.rotation.y = this.time * 0.5;
          if (ob.t > 0.45 && Math.random() < 0.3) this.fx.dust(ob.x, 0.7, ob.z, 1, 0.05, 0.6, 0.15);
        } else if (ob.type === 'potato') {
          const H = m.w[ob.holder], s = H.a.scale * (H.szCur || 1);
          me.position.set(H.x, (2.45 * s) + (H.y || 0), H.z);
          const left = ob.dur - ob.t, fl = Math.sin(this.time * (6 + (6 - left) * 5)) > 0;
          const u = me.userData.body.material.uniforms; if (u) { u.uFlash.value = fl ? 0.6 : 0; u.uFlashCol.value.set(0xff2a1a); }
          me.visible = !H.swallowed;
        } else if (ob.type === 'claw') {
          me.position.set(ob.x, 0, ob.z);
          const U = me.userData, top = 9, hy = ob.h + 1.75;
          U.head.position.y = hy; U.head.rotation.y += dt * (ob.mode === 'hunt' ? 1.2 : 0.3);
          U.cable.position.y = (top + hy) / 2; U.cable.scale.y = top - hy;
          const open = ob.mode === 'hunt' || ob.mode === 'drop' || ob.mode === 'release' ? 0.55 : -0.05;
          for (const p of U.prongs) p.rotation.z += ((p.children[0].position.x > 0 ? -open : open) - p.rotation.z) * Math.min(1, dt * 10);
          const hunting = ob.mode === 'hunt' || ob.mode === 'drop';
          U.lamp.material.color.setHex(Math.sin(this.time * (hunting ? 14 : 5)) > 0 ? 0xffd23a : 0xff4fa3);
          U.tgt.visible = ob.mode !== 'carry' && ob.mode !== 'release';
          U.tgtMat.color.setHex(ob.mode === 'drop' ? 0xffd23a : 0xff3b5c);
          const pul = 1 + 0.08 * Math.sin(this.time * 9); U.tgt.scale.set(pul, 1, pul); U.tgt.rotation.y = this.time * 0.8;
        } else if (ob.type === 'doors') {
          const D = [[Math.cos(ob.a) * (R - 0.9), Math.sin(ob.a) * (R - 0.9)], [-Math.cos(ob.a) * (R - 0.9), -Math.sin(ob.a) * (R - 0.9)]];
          const g = Math.min(1, ob.t / 0.3) * Math.min(1, (ob.dur - ob.t) / 0.3);
          me.userData.doors.forEach((d, k) => { d.position.set(D[k][0], 0, D[k][1]); d.rotation.y = Math.atan2(D[k][0], D[k][1]); /* doorway faces the middle, so you walk straight in */ d.scale.set(1, Math.max(0.01, g), 1); });
        } else if (ob.type === 'pickup') {
          me.position.set(ob.x, 0.7 + Math.sin(this.time * 3) * 0.1, ob.z); me.rotation.y = this.time * 2.5;
        } else if (ob.type === 'train') {
          me.rotation.y = -ob.a; const px = -Math.sin(ob.a), pz = Math.cos(ob.a); me.position.set(px * ob.off, 0, pz * ob.off);
          me.userData.lane.visible = ob.t < ob.warn + 0.4 && Math.sin(this.time * 18) > -0.3;
          me.userData.loco.visible = ob.t >= ob.warn; me.userData.loco.position.x = ob.front || -14;
        } else if (ob.type === 'spin') {
          // nothing to draw: the ring itself turns
        } else if (ob.type === 'hole') {
          me.position.set(ob.x, 0, ob.z);
          const g = Math.min(1, ob.t / 0.2) * Math.min(1, (ob.dur - ob.t) / 0.25);
          me.scale.setScalar(Math.max(0.01, g));
          me.userData.rings.forEach((r, k) => { r.rotation.z += dt * (6 - k * 1.5); });
          if (Math.random() < 0.5) { const a = Math.random() * 6.28, d = 1.2 + Math.random(); this.fx.dust(ob.x + Math.cos(a) * d, 0.1, ob.z + Math.sin(a) * d, 1, 0.05, 0.1, 0.25, -Math.cos(a) * 3, -Math.sin(a) * 3); }
        } else if (ob.type === 'fish') {
          const hop = Math.max(0, Math.sin(Math.min(1, ob.hopT / 0.45) * Math.PI)) * 0.5;
          me.position.set(ob.x, 0.45 + hop, ob.z); me.scale.setScalar(1.8); // a properly giant tuna
          me.rotation.set(Math.sin(this.time * 14) * 0.6, -Math.atan2(ob.vz, ob.vx), Math.sin(this.time * 9) * 0.4);
          me.userData.tail.rotation.y = Math.sin(this.time * 30) * 0.6;
          me.userData.pecs.forEach((p, i) => { p.rotation.y = Math.sin(this.time * 24 + i * Math.PI) * 0.5; });
        } else if (ob.type === 'bomb') {
          me.position.set(ob.x, 0, ob.z);
          const left = ob.dur - ob.t, fl = Math.sin(this.time * (8 + (5 - left) * 6)) > 0.2;
          me.userData.body.material.uniforms && (me.userData.body.material.uniforms.uFlash.value = fl ? 0.55 : 0, me.userData.body.material.uniforms.uFlashCol.value.set(0xff2a1a));
          me.userData.spark.scale.setScalar(0.25 + Math.random() * 0.2);
          me.scale.setScalar(1 + ob.hits * 0.12);
        } else if (ob.type === 'wave') {
          me.position.set(ob.x, 0.05, ob.z); me.scale.set(ob.r, 1, ob.r);
          me.material.opacity = 0.85 * (1 - ob.t / ob.dur);
          if (Math.random() < 0.7) { const a = Math.random() * 6.28; this.fx.dust(ob.x + Math.cos(a) * ob.r, 0.05, ob.z + Math.sin(a) * ob.r, 1, 0.05, 0.4, 0.3, Math.cos(a) * 2, Math.sin(a) * 2); }
        } else if (ob.type === 'third') {
          const v = me.userData.views[0], base = m.w[0];
          const p = Object.assign(Object.create(Object.getPrototypeOf(base)), base);
          Object.assign(p, { a: S.ARCH[ob.arch], x: ob.x, z: ob.z, vx: ob.vx, vz: ob.vz, f: ob.f, st: ob.st === 'stun' ? 'stun' : ob.st, t: 0.25 - Math.max(0, ob.stT), dur: 0.25, hand: ob.hand, clinch: null, swallowed: false, lifted: false, down: false, fxs: {}, y: 0, szCur: 1, squash: 0, gulpI: -1, inShop: false, idx: 2, tx: 0, tz: 0, bal: 1, power: 0, pre: null, crouchT: 0 });
          v.viewer = this.viewer; v.match = m; v.update(p, Math.max(dt, 1e-4), this.animT);
        } else if (ob.type === 'clones') {
          const own = ob.owner;
          ob.c.forEach((c, k) => {
            const v = me.userData.views[k];
            if (!c.alive) { v.root.visible = false; v.shadow.visible = false; return; }
            const p = Object.assign(Object.create(Object.getPrototypeOf(own)), own);
            p.x = c.x; p.z = c.z; p.vx = c.vx || 0; p.vz = c.vz || 0; p.f = Math.atan2(own.opp.z - c.z, own.opp.x - c.x); p.clinch = null; p.swallowed = false; p.st = 'free'; p.lifted = false; p.down = false; p.fxs = {};
            v.viewer = this.viewer; v.match = m; v.update(p, Math.max(dt, 1e-4), this.animT);
            if (v.armband) v.armband.visible = false;
          });
        } else if (ob.type === 'beartrap') {
          me.position.set(ob.x, 0, ob.z);
          // jaws lie open flat, then slam shut upright
          const shut = ob.sprung ? Math.min(1, (ob.t - (ob.dur - 3.3)) / 0.08) : 0;
          for (const j of me.userData.jaws) j.rotation.x = -j.userData.sd * shut * 1.35;
        } else if (ob.type === 'dart') {
          me.position.set(ob.x, 1.25, ob.z); me.rotation.y = -Math.atan2(ob.vz, ob.vx);
        } else if (ob.type === 'fan') {
          // the fan runs in from the crowd, grabs them from behind, then runs back out
          const T = ob.target, dx = ob.ax - T.x, dz = ob.az - T.z, dl = Math.hypot(dx, dz) || 1, ux = dx / dl, uz = dz / dl;
          const hx = T.x + ux * (T.r * 0.75 + 0.2), hz = T.z + uz * (T.r * 0.75 + 0.2);
          const k = Math.min(1, ob.t / 0.28), out = Math.max(0, (ob.t - (ob.dur - 0.35)) / 0.35);
          const e = k * k * (3 - 2 * k) * (1 - out * out);
          const px = ob.ax + (hx - ob.ax) * e, pz = ob.az + (hz - ob.az) * e;
          const running = k < 1 || out > 0;
          me.position.set(px, running ? Math.abs(Math.sin(ob.t * 22)) * 0.08 : 0, pz); me.scale.setScalar(1.35);
          me.rotation.y = Math.atan2(T.x - px, T.z - pz);
          me.rotation.x = running ? 0.15 : -0.12; // leaning in to run, leaning back to pull
          const [aL, aR] = me.userData.arms;
          const reach = Math.min(0.75, Math.hypot(T.x - px, T.z - pz));
          for (const [arm, sd] of [[aL, -1], [aR, 1]]) {
            const sh = new THREE.Vector3(sd * 0.24, 0.85, 0.05);
            // arms wrap round their belly, hands meeting in front
            const hand = running && k < 1 ? new THREE.Vector3(sd * 0.3, 0.75, 0.35) : new THREE.Vector3(sd * 0.12, 0.8, reach / 1.35 + 0.2);
            arm.scale.set(1, sh.distanceTo(hand) / 1.1, 1);
            seg(arm, sh, hand);
          }
          me.visible = true;
        }
      }
      // giant fan: a huge paper fan waved over the head, with gusts streaming off it
      for (const w of m.w) {
        const v = this.views[w.idx]; if (!v) continue;
        if (w.st === 'gale') {
          if (!v.bigFan) {
            // built with the handle end at the origin, so the group sits in the wrestler's hands
            const g = new THREE.Group(), top = new THREE.Group(); top.position.y = 0.85; g.add(top);
            const leaf = mesh(new THREE.CircleGeometry(1.15, 24, 0, Math.PI), toon(0xe2322b, { shade: 0x8a1a14 }), 0.02);
            leaf.material.side = THREE.DoubleSide; top.add(leaf);
            const ring = mesh(new THREE.CircleGeometry(0.62, 18, 0, Math.PI), toon(0xf6eddc, { shade: 0xb8a890 }), 0.0); ring.position.z = 0.01; ring.material.side = THREE.DoubleSide; top.add(ring);
            const sun = mesh(new THREE.CircleGeometry(0.28, 16, 0, Math.PI), toon(0xe2322b, { shade: 0x8a1a14 }), 0.0); sun.position.z = 0.02; sun.material.side = THREE.DoubleSide; top.add(sun);
            const stick = mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.9, 6), toon(0x6d4430, { shade: 0x3a2418 }), 0.01); stick.position.y = 0.45; g.add(stick);
            this.scene.add(g); v.bigFan = g;
          }
          const fx = Math.cos(w.f), fz = Math.sin(w.f), sw = Math.sin(w.t * 14), sc = w.a.scale * (w.szCur || 1);
          v.bigFan.visible = true;
          v.bigFan.position.set(w.x + fx * 0.5 * sc, 1.45 * sc, w.z + fz * 0.5 * sc);
          // fanned up and down from the hands: the face points at them, swinging from overhead down to waist height
          // face it half toward them and half toward the camera, so it reads from above
          const cx = this.cam.position.x - w.x, cz = this.cam.position.z - w.z, cl = Math.hypot(cx, cz) || 1;
          const ax = fx + cx / cl * 0.9, az = fz + cz / cl * 0.9;
          v.bigFan.rotation.set(0, 0, 0); v.bigFan.rotateY(Math.atan2(ax, az)); v.bigFan.rotateX(-0.25 + sw * 0.55); // from up over the head, chopping down toward them
          v.bigFan.scale.setScalar(sc * Math.min(1, w.t / 0.15));
          if (w.t > 0.15 && Math.random() < 0.8) {
            const d = 1 + Math.random() * 4.5, sp = (Math.random() - 0.5) * 0.7 * d;
            this.fx.dust(w.x + fx * d - fz * sp, 0.1 + Math.random() * 0.8, w.z + fz * d + fx * sp, 1, 0.1, 0.2, 0.7, fx * 7, fz * 7);
          }
        } else if (v.bigFan) v.bigFan.visible = false;
      }
      // rotating ring: turn the dohyo with the spin, and leave it where it stops
      const spn = m.objs.find((o) => o.type === 'spin');
      if (spn) { this.spinNow = spn.a; this.spinG.rotation.y = -((this.spinBase || 0) + spn.a); }
      else if (this.spinNow) { this.spinBase = (this.spinBase || 0) + this.spinNow; this.spinNow = 0; }
      // bumper ring: the straw glows while it's bouncy
      const bump = m.w.some((w) => w.fxs.bumper > 0);
      if (bump && !this.bumperM) { this.bumperM = new THREE.Mesh(new THREE.TorusGeometry(R, 0.09, 8, 72), new THREE.MeshBasicMaterial({ color: 0xf0c35a, transparent: true, opacity: 0.7, depthWrite: false })); this.bumperM.rotation.x = Math.PI / 2; this.bumperM.position.y = 0.16; this.scene.add(this.bumperM); }
      if (this.bumperM) { this.bumperM.visible = bump; this.bumperM.material.opacity = 0.45 + 0.3 * Math.sin(this.time * 8); }
      // belly-flop target shadow
      for (const w of m.w) {
        const v = this.views[w.idx]; if (!v) continue;
        if (w.st === 'air') {
          if (!v.flopShadow) {
            v.flopShadow = new THREE.Mesh(new THREE.CircleGeometry(1.0, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x1a0610, transparent: true, opacity: 0.5, depthWrite: false }));
            v.flopShadow.renderOrder = 2; this.scene.add(v.flopShadow);
          }
          v.flopShadow.visible = true;
          v.flopShadow.position.set(w.st === 'air' && w.t > 0.45 ? w.ax2 : w.x, 0.02, w.st === 'air' && w.t > 0.45 ? w.az2 : w.z);
          const k = Math.min(1, w.t / 1.5); v.flopShadow.scale.setScalar(0.4 + 1.0 * k); v.flopShadow.material.opacity = 0.25 + 0.4 * k;
        } else if (v.flopShadow) v.flopShadow.visible = false;
        // dizzy stars
        if (w.fxs.dizzy > 0) {
          if (!v.stars) { v.stars = []; for (let k = 0; k < 3; k++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.fx.sparks[0].sp.material.map, color: 0xffe14a, depthTest: false })); sp.scale.setScalar(0.25); sp.renderOrder = 11; this.scene.add(sp); v.stars.push(sp); } }
          v.stars.forEach((sp, k) => { const a = this.time * 5 + k * 2.1; sp.visible = true; sp.position.set(w.x + Math.cos(a) * 0.35, 2.35 * w.a.scale * (w.szCur || 1), w.z + Math.sin(a) * 0.35); });
        } else if (v.stars) v.stars.forEach((sp) => { sp.visible = false; });
      }
    }



    setMarker(x, z) {
      if (!this.marker) {
        this.marker = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.6, 48).rotateX(-Math.PI / 2),
          new THREE.MeshBasicMaterial({ color: 0xf0c35a, transparent: true, opacity: 0.8, depthWrite: false }));
        this.marker.renderOrder = 2; this.scene.add(this.marker);
      }
      this.marker.visible = x !== null && x !== undefined;
      if (this.marker.visible) this.marker.position.set(x, 0.03, z);
    }
    kick(amount) { this.cs.kick = Math.max(this.cs.kick, amount); }
    shake(amount) { this.cs.shake = Math.max(this.cs.shake, amount); }
    focus(x, z, w) { this.cs.fox = x; this.cs.foz = z; this.cs.focusW = w; }

    update(game, dt, rdt) {
      this.time += rdt;
      this.animT = (this.animT || 0) + dt;
      const T = this.time, m = game.match;
      this.viewer = game.viewerIdx === undefined ? 0 : game.viewerIdx;
      for (const v of this.views) { v.viewer = this.viewer; v.match = m; }
      if (m) for (let i = 0; i < this.views.length; i++) {
        const w = m.w[i];
        this.views[i].update(w, Math.max(dt, 1e-4), this.animT);
        // gathering power at the face-off: dust swirls at the feet
        if (m.phase === 'shikiri' && w.power > 0.2 && dt > 0 && Math.random() < w.power * 0.5) {
          const a = Math.random() * 6.28;
          this.fx.dust(w.x + Math.cos(a) * 0.7, 0.05, w.z + Math.sin(a) * 0.7, 1, 0.05, 0.4 + w.power * 0.6, 0.25, -Math.sin(a) * 1.5, Math.cos(a) * 1.5);
        }
      }
      if (this.marker && this.marker.visible) { const k = 1 + 0.12 * Math.sin(this.time * 6); this.marker.scale.set(k, 1, k); }
      this.ref.update(rdt, T, m);
      this.fx.update(dt); this.fx.updateSalt(dt); this.fx.updateWater(dt); this.fx.updateSand(dt);
      this.updateObjs(game, dt); this.updateThrown(dt);
      if (this.banners) for (const b of this.banners) b.userData.flag.rotation.y = Math.sin(this.time * 1.3 + b.position.x) * 0.12;
      this.excite += ((game.excite || 0) - this.excite) * Math.min(1, rdt * 3);
      this.updateCrowd(T, 0.25 + this.excite, rdt, game.excite || 0);
      if (this.stageTick) this.stageTick(T, rdt, m);
      this.motes.rotation.y += rdt * 0.02;
      this.updateCamera(rdt, game);
      SH.uLight.value.copy(this.anime ? LIGHT_ANIME : LIGHT_W).transformDirection(this.cam.matrixWorldInverse);
      SH.uRimDir.value.copy(RIM_W).transformDirection(this.cam.matrixWorldInverse);
    }

    updateCamera(dt, game) {
      const cs = this.cs, m = game.match, cam = this.cam;
      let fx = 0, fz = 0, tight = 0;
      if (m && game.mode !== 'title') {
        const A = m.w[0], B = m.w[1];
        fx = (A.x + B.x) / 2 * 0.3; fz = (A.z + B.z) / 2 * 0.3;
        if (m.clinch) tight = 0.07;
        if (m.deadT > 0) tight = 0.12;
      }
      if (cs.focusW > 0) { fx += (cs.fox - fx) * cs.focusW * 0.6; fz += (cs.foz - fz) * cs.focusW * 0.6; tight += 0.2 * cs.focusW; }
      const k = 1 - Math.exp(-dt * 3);
      cs.fx += (fx - cs.fx) * k; cs.fz += (fz - cs.fz) * k; cs.tight += (tight - cs.tight) * (1 - Math.exp(-dt * 4));
      cs.kick *= Math.exp(-dt * 7); cs.shake *= Math.exp(-dt * 6);
      const fovV = cam.fov * Math.PI / 180;
      const ext = 6.0;
      const dV = ext / Math.tan(fovV / 2) * 1.02, dH = ext / (Math.tan(fovV / 2) * cam.aspect) * 1.3;
      let dist = Math.max(dV, dH) * (1 - cs.tight - cs.kick);
      let pitch = 0.8, yaw = 0;
      if (game.mode === 'title') { cs.yaw += dt * 0.07; yaw = Math.sin(cs.yaw) * 0.5; pitch = 0.72; dist *= 0.88; }
      const T = this.time;
      const sh = cs.shake;
      const sx = (Math.sin(T * 31) + Math.sin(T * 17.3)) * 0.5 * sh, sy = (Math.sin(T * 27.1) + Math.sin(T * 13.7)) * 0.5 * sh;
      cam.position.set(cs.fx + Math.sin(yaw) * Math.cos(pitch) * dist + sx * 0.3, Math.sin(pitch) * dist + sy * 0.3, cs.fz + Math.cos(yaw) * Math.cos(pitch) * dist);
      cam.lookAt(cs.fx + sx * 0.08, 0.2 + sy * 0.08, cs.fz - 0.15);
      if (this.camOverride) { const o = this.camOverride; cam.position.set(o.p[0], o.p[1], o.p[2]); cam.lookAt(o.l[0], o.l[1], o.l[2]); }
      cam.updateMatrixWorld();
    }

    project(x, y, z) {
      const v = new THREE.Vector3(x, y, z).project(this.cam);
      return { x: (v.x * 0.5 + 0.5) * innerWidth, y: (-v.y * 0.5 + 0.5) * innerHeight };
    }

    render() { if (this.anime && this.post) this.post.render(this.scene, this.cam, this.time); else this.r.render(this.scene, this.cam); }
  }

  S.Renderer = Renderer;
  S.R3.GEO = GEO;
  // shared with the campaign (campaign.js): the wrestler model, effects, and the toon light for any camera
  S.WrestlerView = WrestlerView; S.FX = FX;
  S.R3.setLight = (cam, anime) => {
    SH.uLight.value.copy(anime ? LIGHT_ANIME : LIGHT_W).transformDirection(cam.matrixWorldInverse);
    SH.uRimDir.value.copy(RIM_W).transformDirection(cam.matrixWorldInverse);
  };
  // STAGES: swap the classic dohyo for a themed stage (built in stages.js). The fight area is the same everywhere.
  Renderer.prototype.setStage = function (id) {
    const classic = !id || id === 'dohyo' || !S.STAGE_BUILD[id];
    // the arena, its crowd, the corner banners and the light cone belong to the dohyo only
    this.dohyoG.visible = classic;
    for (const c of this.spinG.children) if (c.userData.dohyo) c.visible = classic;
    this.classicStage = classic;
    if (this.fx) this.fx.sandy = classic; // sand kicks up off the clay ring only
    if (this.floorM) this.floorM.visible = classic;
    if (this.coneM) this.coneM.visible = classic;
    if (this.motes) this.motes.visible = classic;
    if (this.banners) for (const b of this.banners) b.visible = classic;
    this.applyArena();
    this.fx.noMarks = !classic; // sand footprints, slide marks and step dust belong to the dohyo only
    if (this.fx.noMarks) this.fx.clearDecals();
    if (this.stageId === id) return;
    this.stageId = id;
    if (this.stageG) { this.scene.remove(this.stageG); this.stageG = null; }
    if (this.stageSpin) { this.spinG.remove(this.stageSpin); this.stageSpin = null; }
    this.stageTick = null;
    if (classic) return;
    this.stageG = new THREE.Group(); this.scene.add(this.stageG);
    this.stageSpin = new THREE.Group(); this.spinG.add(this.stageSpin);
    this.stageTick = S.STAGE_BUILD[id](this, this.stageG, this.stageSpin) || null;
  };

})();
