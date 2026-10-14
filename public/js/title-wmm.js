'use strict';
// WHERE'S MY MAWASHI: the kumitegame fork's front end.
//   boot     straight onto the menu
//   title    white, the menu on the left; on the right the sumo from behind on a clay mound, a trophy held up over his head
//   PLAY     the screen goes white, the bathhouse fades in: the sumo asleep in the bath
//            (zzz); any key wakes him and the level starts (see Stealth intro)
// The original Kumite build is untouched (this only runs when window.KUMITE_FORK === 'kumitegame').
(function () {
  if (window.KUMITE_FORK !== 'kumitegame') return;
  document.body.classList.add('wmm');
  const W = S.WMM = { busy: false };
  let scene = null, cam = null, sun = null, t = 0;
  const stars = [];

  function setup(R) {
    scene = new THREE.Scene(); scene.background = new THREE.Color(0xffffff);
    cam = new THREE.PerspectiveCamera(36, innerWidth / innerHeight, 0.1, 200);
    cam.position.set(0, 0.6, 14); cam.lookAt(0, 0, 0);
    sun = S.Flat.lights(scene, { r: 8 }); if (sun && sun.aim) sun.aim(0, 0);
    addEventListener('resize', () => { cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix(); });
    cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix();
  }
  // the food: the same flat look as the bathhouse props (onigiri, dango, fish cake)
  const M = (c) => { const m = S.Flat.mat(c); return m; };
  function done(g) { g.traverse((o) => { if (o.isMesh) o.userData.flatDone = true; }); return g; }
  const FOOD = [
    function onigiri() {
      const g = new THREE.Group(), sh = new THREE.Shape(), r = 0.5;
      for (let k = 0; k <= 36; k++) { const a = k / 36 * Math.PI * 2 + Math.PI / 2; const rr = r * (1 + 0.16 * Math.cos(3 * (a - Math.PI / 2))); const x = Math.cos(a) * rr, y = Math.sin(a) * rr * 0.95; k ? sh.lineTo(x, y) : sh.moveTo(x, y); }
      const geo = new THREE.ExtrudeGeometry(sh, { depth: 0.22, bevelEnabled: true, bevelSize: 0.08, bevelThickness: 0.1, bevelSegments: 4, curveSegments: 24 }); geo.center();
      g.add(new THREE.Mesh(geo, M(0xf7f4ec)));
      const nori = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.4, 0.46), M(0x26332c)); nori.position.y = -0.3; g.add(nori);
      return done(g);
    },
    function dango() {
      const g = new THREE.Group();
      const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.5, 8), M(0xcfa86e)); stick.position.y = -0.1; g.add(stick);
      [0xf2a7b9, 0xf8f3e6, 0x9fca86].forEach((c, k) => { const b = new THREE.Mesh(new THREE.SphereGeometry(0.21, 18, 14), M(c)); b.position.y = 0.4 - k * 0.38; g.add(b); });
      return done(g);
    },
    function naruto() {
      const g = new THREE.Group();
      const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.36, 0.14, 12).rotateX(Math.PI / 2), M(0xf8f4ec)); g.add(disc);
      for (const z of [0.072, -0.072]) { const sw = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.04, 6, 24, Math.PI * 1.6), M(0xef7f9e)); sw.position.z = z; g.add(sw); const dot = new THREE.Mesh(new THREE.CircleGeometry(0.05, 12), M(0xef7f9e)); dot.position.z = z * 1.02; if (z < 0) dot.rotation.y = Math.PI; g.add(dot); }
      return done(g);
    },
  ];
  // rain: pieces drop from above the frame, tumble and fall out the bottom
  function spawn(y) {
    const make = FOOD[(Math.random() * FOOD.length) | 0], g = make();
    const half = Math.tan(cam.fov * Math.PI / 360) * 14 * cam.aspect;
    const z = -4 + Math.random() * 7;
    const sc = 1.15 + Math.random() * 0.6; g.scale.setScalar(sc);
    g.position.set(-half * 0.3 + Math.random() * (half * 1.3 + 1), y, z); g.rotation.set(Math.random() * 6, Math.random() * 6, Math.random() * 6);
    scene.add(g);
    stars.push({ m: g, vy: -(1.6 + Math.random() * 1.6), sx: (Math.random() - 0.5) * 2.4, sy: (Math.random() - 0.5) * 2.4, sz: (Math.random() - 0.5) * 2.4 });
  }
  let spawnT = 0;
  function step(dt) {
    t += dt;
    if (!ready) { ready = true; for (let k = 0; k < 40; k++) spawn(-6 + Math.random() * 14); }
    spawnT -= dt; while (spawnT <= 0) { spawnT += 0.09 + Math.random() * 0.08; spawn(8.5); }
    for (let i = stars.length - 1; i >= 0; i--) {
      const s = stars[i]; s.vy = Math.max(s.vy - dt * 1.2, -4.2);
      s.m.position.y += s.vy * dt; s.m.rotation.x += s.sx * dt; s.m.rotation.y += s.sy * dt; s.m.rotation.z += s.sz * dt;
      if (s.m.position.y < -8.5) { scene.remove(s.m); stars.splice(i, 1); }
    }
  }
  let ready = false;
  let fadeEl = null;
  function fade(to, sec) {
    if (!fadeEl) { fadeEl = document.createElement('div'); fadeEl.style.cssText = 'position:fixed;inset:0;background:#fff;z-index:45;pointer-events:none;opacity:0'; document.body.appendChild(fadeEl); }
    fadeEl.style.transition = 'opacity ' + sec + 's ease'; requestAnimationFrame(() => { fadeEl.style.opacity = to; });
  }

  // ---- the champion: the sumo from behind on a clay mound, a gold trophy held up over his head (in place of the food rain)
  let champ = null;
  function trophy() {
    const g = new THREE.Group(), gold = M(0xf2c14e), dark = M(0xb98a2c), base = M(0x3a2a22);
    const prof = [[0, 0], [0.22, 0], [0.22, 0.07], [0.1, 0.1], [0.06, 0.2], [0.05, 0.32], [0.12, 0.38], [0.28, 0.5], [0.34, 0.68], [0.36, 0.86], [0.33, 0.88]].map(([x, y]) => new THREE.Vector2(x, y));
    const cup = new THREE.Mesh(new THREE.LatheGeometry(prof, 24), gold); g.add(cup);
    for (const sd of [-1, 1]) { const h = new THREE.Mesh(new THREE.TorusGeometry(0.13, 0.03, 8, 16, Math.PI * 1.2), dark); h.position.set(sd * 0.36, 0.66, 0); h.rotation.z = sd > 0 ? -Math.PI * 0.6 : Math.PI * 1.6; g.add(h); }
    const b = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.12, 0.4), base); b.position.y = -0.06; g.add(b);
    return done(g);
  }
  function makeChamp(R) {
    if (!S.SoftSumo || !S.SoftSumo.loaded || !S.Match || !S.WrestlerView) return null;
    const A = [S.ARCH[0], S.ARCH[1]], m = new S.Match(A), w = m.w[0];
    m.phase = 'shikiri'; m.phaseT = 9; w.x = 0; w.z = 0; w.f = -Math.PI / 2 + 0.6; w.pre = 'trophy';   // (his back to us: the booty, the trophy up over his head) w.preT = 0;
    const v = new S.WrestlerView(scene, A[0], R.fx, S.DEF_EQ); S.SoftSumo.attach(v, { noBlob: true, booty: 3.5 });
    if (v.shadow) v.shadow.visible = false;
    const clay = M(0xd9b07c), straw = M(0xdcc58c);
    const mound = new THREE.Mesh(new THREE.CylinderGeometry(3.0, 3.7, 0.7, 48), clay); mound.position.y = -0.35;
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.15, 0.11, 8, 64), straw); ring.rotation.x = Math.PI / 2; ring.position.y = 0.03;
    const tr = trophy(); tr.scale.setScalar(1.65);
    const G = new THREE.Group(); G.add(done(mound), done(ring)); scene.add(G); scene.add(tr);
    return { m, w, v, tr, h1: new THREE.Vector3(), h2: new THREE.Vector3() };
  }
  W.frame = function (dt, R) {
    if (!scene) setup(R);
    dt = Math.min(dt, 0.05); t += dt;
    if (!champ) {
      champ = makeChamp(R);
      if (champ) { cam.fov = 50; cam.position.set(-1.3, 0.5, 5.4); cam.lookAt(-1.3, 1.75, 0); cam.updateProjectionMatrix(); }   // (low, looking up past the booty at the trophy)
      else { step(dt); R.r.render(scene, cam); return; }   // (the model is still loading: the food rain for a moment)
    }
    if (stars.length) { for (const s of stars) scene.remove(s.m); stars.length = 0; }
    const c = champ; c.w.preT = 0.2; c.v.match = c.m; c.v.viewer = 0; c.v.update(c.w, dt, t);
    c.v.handWorld(1, c.h1); c.v.handWorld(-1, c.h2); c.tr.position.copy(c.h1).add(c.h2).multiplyScalar(0.5); c.tr.position.y += 0.12 + Math.max(0, Math.sin(t * 3.2)) * 0.06;   // (a gentle lift of the cup)
    c.tr.rotation.y = Math.sin(t * 0.8) * 0.25;
    R.r.render(scene, cam);
  };
  // PLAY: a white-out, then the bathhouse fades in (the sumo asleep in the bath)
  W.play = function (cb) {
    if (W.busy) return; W.busy = true;
    fade(1, 0.45); setTimeout(() => { cb(); setTimeout(() => fade(0, 1.0), 120); W.busy = false; }, 500);
  };
  // boot: straight onto the menu (no logo screen); the white cover only hides the page while the game is loading
  // the banners sweep in over the white cover; once they've covered the screen the menu is put up beneath them, and they slide away
  W.splash = function (done) {
    const bc = document.getElementById('wmmBoot') || document.getElementById('bootcover');
    let went = false; const go = () => { if (went) return; went = true; done && done(); if (bc) bc.remove(); };
    if (S.Banners && S.Banners.flood && S.Banners.whenReady) S.Banners.whenReady(() => S.Banners.flood({ hold: 0.12, speed: 1.3, onCovered: go }), 3000);
    else go();
    setTimeout(go, 6000);   // (never stuck on the white cover)
  };
})();
