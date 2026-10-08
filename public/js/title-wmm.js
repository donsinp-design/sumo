'use strict';
// WHERE'S MY MAWASHI: the kumitegame fork's front end.
//   boot     the logo on white: fades in, holds 3 s, fades out
//   title    white, the menu on the left; food rains down behind it (onigiri, nigiri, dango..., in the game's flat look)
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
  // the food: the same flat look as the bathhouse props (onigiri, nigiri, dango, fish cake, tempura, manju)
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
    function nigiri() {
      const g = new THREE.Group();
      const rice = new THREE.Mesh(new THREE.CapsuleGeometry(0.2, 0.42, 6, 14).rotateZ(Math.PI / 2), M(0xf7f4ec)); rice.scale.set(1, 0.9, 1.1); g.add(rice);
      const fish = new THREE.Mesh(new THREE.CapsuleGeometry(0.22, 0.5, 6, 14).rotateZ(Math.PI / 2), M(0xf4895f)); fish.scale.set(1.05, 0.42, 1.15); fish.position.y = 0.2; g.add(fish);
      for (let k = -1; k <= 1; k++) { const st = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.03, 0.5), M(0xffd2bd)); st.position.set(k * 0.2, 0.29, 0); st.rotation.y = 0.4; g.add(st); }
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
    function tempura() {
      const g = new THREE.Group();
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.17, 0.7, 6, 12), M(0xe9b24e)); body.rotation.z = 0.2; g.add(body);
      const tail = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.26, 3), M(0xe2553c)); tail.position.set(0.1, -0.6, 0); tail.rotation.z = Math.PI + 0.2; tail.scale.z = 0.4; g.add(tail);
      return done(g);
    },
    function manju() {
      const g = new THREE.Group();
      const bun = new THREE.Mesh(new THREE.SphereGeometry(0.34, 20, 14), M(0xf3e6cf)); bun.scale.y = 0.72; g.add(bun);
      const mark = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), M(0xc0503e)); mark.position.y = 0.24; mark.scale.y = 0.4; g.add(mark);
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

  W.frame = function (dt, R) {
    if (!scene) setup(R);
    step(Math.min(dt, 0.05));
    R.r.render(scene, cam);
  };
  // PLAY: a white-out, then the bathhouse fades in (the sumo asleep in the bath)
  W.play = function (cb) {
    if (W.busy) return; W.busy = true;
    fade(1, 0.45); setTimeout(() => { cb(); setTimeout(() => fade(0, 1.0), 120); W.busy = false; }, 500);
  };
  // boot: the logo on white, fade in, three seconds, fade out
  W.splash = function (done) {
    const bc = document.getElementById('wmmBoot') || document.getElementById('bootcover'); if (bc) setTimeout(() => bc.remove(), 50);
    const d = document.createElement('div'); d.id = 'wmmSplash';
    d.style.cssText = 'position:fixed;inset:0;background:#fff;z-index:46;display:flex;align-items:center;justify-content:center;transition:opacity .5s ease';
    const img = new Image(); img.src = 'assets/wmm_logo.webp'; img.alt = "Where's my Mawashi";
    img.style.cssText = 'width:min(900px,78vw);height:auto;opacity:0;transition:opacity .8s ease';
    d.appendChild(img); document.body.appendChild(d);
    const go = () => {
      requestAnimationFrame(() => { img.style.opacity = 1; });
      setTimeout(() => { img.style.opacity = 0; }, 800 + 3000);
      setTimeout(() => { done && done(); d.style.opacity = 0; setTimeout(() => d.remove(), 520); }, 800 + 3000 + 800);
    };
    if (img.decode) img.decode().then(go, go); else img.onload = go;
  };
})();
