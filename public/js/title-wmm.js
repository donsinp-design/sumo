'use strict';
// WHERE'S MY MAWASHI: the kumitegame fork's front end.
//   boot     the logo on white: fades in, holds 3 s, fades out
//   title    white, the menu on the left; a ninja stands where the sumo will be sleeping in the bath, throwing
//            shuriken and swinging his sword (the staff models and mocap, in the game's flat look)
//   PLAY     the ninja throws a smoke bomb, the screen goes white, the bathhouse fades in: the sumo asleep in the bath
//            (zzz); any key wakes him and the level starts (see Stealth intro)
// The original Kumite build is untouched (this only runs when window.KUMITE_FORK === 'kumitegame').
(function () {
  if (window.KUMITE_FORK !== 'kumitegame') return;
  document.body.classList.add('wmm');
  const W = S.WMM = { busy: false };
  const SPOT = { x: 1.2, z: -6.2 };                 // where the sumo wakes up in the bath (Stealth.P at the start)
  let scene = null, cam = null, sun = null, ninja = null, a = null, swordHand = null, swordBack = null, t = 0;
  const stars = [], puffs = [];
  let seq = [], seqI = 0, smoke = null;

  function setup(R) {
    scene = new THREE.Scene(); scene.background = new THREE.Color(0xffffff);
    cam = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 200);
    // the stealth level's opening camera: the ninja stands on screen exactly where the sumo will lie
    const cx = SPOT.x * 0.8, cz = SPOT.z - 2.6;
    cam.position.set(cx, 9.6, cz + 11.55); cam.lookAt(cx, 0.6, cz);
    sun = S.Flat.lights(scene, { r: 8 }); sun.aim(SPOT.x, SPOT.z);
    // pure white: the floor only catches his shadow (a soft lilac, as in the game)
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(80, 80).rotateX(-Math.PI / 2), new THREE.ShadowMaterial({ color: 0x8a86b8, opacity: 0.28 })); floor.receiveShadow = true; floor.userData.flatDone = true; scene.add(floor);
    addEventListener('resize', () => { cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix(); });
    cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix();
  }
  // a katana, authored along +Y (the grip axis Body.attach expects)
  function katana() {
    const g = new THREE.Group(), M = (c) => S.Flat.mat(c);
    const blade = new THREE.Mesh(new THREE.BoxGeometry(0.032, 0.86, 0.008), M(0xe6ecf2)); blade.position.y = 0.58; g.add(blade);
    const edge = new THREE.Mesh(new THREE.BoxGeometry(0.01, 0.86, 0.01), M(0xb6c0c8)); edge.position.set(0.016, 0.58, 0); g.add(edge);
    const tip = new THREE.Mesh(new THREE.ConeGeometry(0.018, 0.06, 4), M(0xe6ecf2)); tip.position.y = 1.04; tip.scale.z = 0.3; g.add(tip);
    const guard = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.014, 14), M(0x2a2024)); guard.position.y = 0.14; g.add(guard);
    const grip = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.02, 0.24, 8), M(0x3a2a44)); grip.position.y = 0.01; g.add(grip);
    g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.userData.flatDone = true; } });
    return g;
  }
  function shuriken() {
    const sh = new THREE.Shape(); for (let k = 0; k < 8; k++) { const ang = k / 8 * Math.PI * 2, r = k % 2 ? 0.035 : 0.13; const x = Math.cos(ang) * r, y = Math.sin(ang) * r; if (k) sh.lineTo(x, y); else sh.moveTo(x, y); }
    const m = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 0.012, bevelEnabled: false }).rotateX(Math.PI / 2), S.Flat.mat(0x8f9ba8)); m.castShadow = true; m.userData.flatDone = true;
    return m;
  }
  function makeNinja() {
    a = { kind: 'ninja', x: SPOT.x, z: SPOT.z, y: 0, f: Math.PI / 2, vx: 0, vz: 0, st: 'free', t: 0, dur: 1, atk: null, hp: 1, maxHp: 1, dead: false, engage: true };
    ninja = new S.WorkerView(scene, 'ninja', false, 0);
    const B = ninja.body;
    swordHand = katana(); swordBack = katana();
    if (B && B.attach) B.attach(swordHand, 'R');
    if (B && B.bones && B.bones.Chest) { const k = 1 / B.root.scale.y; swordBack.scale.setScalar(k); swordBack.position.set(0.05 * k, 0.05 * k, -0.17 * k); swordBack.rotation.set(0, 0, 2.4); B.bones.Chest.add(swordBack); }
    // the routine: two shuriken, a sword cut, a shuriken, a sword cut... on the spot, forever
    seq = [['bottle', 0.22, 0.5], ['bottle', 0.16, 0.5], ['sweep', 0.3, 0.6], ['bottle', 0.16, 0.5], ['sweep', 0.24, 0.6]];
    seqI = 0; a.st = 'free'; a.t = 0; a.dur = 0.8;
  }
  function throwStar() {
    const B = ninja.body, p = new THREE.Vector3(); if (!B || !B.handPos || !B.handPos('R', p)) p.set(a.x, 1.4, a.z);
    for (let k = 0; k < 2; k++) {
      const m = shuriken(); m.position.copy(p); scene.add(m);
      const ang = a.f + (k - 0.5) * 0.25 + (Math.random() - 0.5) * 0.2;
      stars.push({ m, vx: Math.cos(ang) * 13, vz: Math.sin(ang) * 13, vy: 0.6 + Math.random() * 0.6, life: 1.2 });
    }
  }
  function step(dt) {
    t += dt; a.t += dt;
    const wantSword = a.atk === 'sweep' && a.st !== 'free';
    if (swordHand) swordHand.visible = wantSword; if (swordBack) swordBack.visible = !wantSword;
    if (smoke) { smokeStep(dt); }
    else if (a.st === 'free' && a.t >= a.dur) { const s = seq[seqI++ % seq.length]; a.atk = s[0]; a.st = 'wind'; a.t = 0; a.dur = s[1]; a.actDur = s[2]; a.thrown = false; }
    else if (a.st === 'wind' && a.t >= a.dur) { a.st = 'act'; a.t = 0; a.dur = a.actDur; }
    else if (a.st === 'act') { if (a.atk === 'bottle' && !a.thrown && a.t > 0.08) { a.thrown = true; throwStar(); } if (a.t >= a.dur) { a.st = 'recover'; a.t = 0; a.dur = 0.35; } }
    else if (a.st === 'recover' && a.t >= a.dur) { a.st = 'free'; a.t = 0; a.dur = 0.35 + Math.random() * 0.4; }
    for (let i = stars.length - 1; i >= 0; i--) { const s = stars[i]; s.life -= dt; s.m.position.x += s.vx * dt; s.m.position.z += s.vz * dt; s.m.position.y += s.vy * dt; s.m.rotation.y += dt * 22; if (s.life <= 0) { scene.remove(s.m); stars.splice(i, 1); } }
  }
  // PLAY: a smoke bomb at his feet, white-out, then the level
  function smokeStep(dt) {
    smoke.t += dt;
    if (!smoke.thrown && smoke.t > 0.25) {
      smoke.thrown = true;
      const M = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.96 }), M2 = new THREE.MeshBasicMaterial({ color: 0xe9e8f2, transparent: true, opacity: 0.96 });
      for (let k = 0; k < 70; k++) {
        const m = new THREE.Mesh(new THREE.SphereGeometry(0.4, 16, 12), k % 3 ? M : M2); m.userData.flatDone = true;
        const ang = Math.random() * Math.PI * 2, r = Math.random() * 0.7;
        m.position.set(a.x + Math.cos(ang) * r, 0.2 + Math.random() * 0.6, a.z + Math.sin(ang) * r); m.scale.setScalar(0.2); scene.add(m);
        puffs.push({ m, vx: Math.cos(ang) * (1 + Math.random() * 2.5), vz: Math.sin(ang) * (1 + Math.random() * 2.5), vy: 0.6 + Math.random() * 1.6, g: 1.4 + Math.random() * 1.6 });
      }
      if (S.game && S.game.audio && S.game.audio.whoosh) S.game.audio.whoosh(0.5);
    }
    if (smoke.thrown && smoke.t > 0.55 && ninja && ninja.root.visible) ninja.root.visible = false;   // gone in the smoke
    for (const p of puffs) { p.m.position.x += p.vx * dt; p.m.position.z += p.vz * dt; p.m.position.y += p.vy * dt; p.vx *= 0.94; p.vz *= 0.94; p.vy *= 0.96; p.m.scale.multiplyScalar(1 + dt * p.g); }
    if (!smoke.white && smoke.t > 0.75) { smoke.white = true; fade(1, 0.35); }
    if (!smoke.done && smoke.t > 1.2) { smoke.done = true; const cb = smoke.cb; cb && cb(); setTimeout(() => fade(0, 1.0), 120); setTimeout(reset, 400); }
  }
  function reset() {   // ready for the next time the title shows
    for (const p of puffs) scene.remove(p.m); puffs.length = 0;
    smoke = null; W.busy = false; if (ninja) ninja.root.visible = true; if (a) { a.st = 'free'; a.t = 0; a.dur = 0.6; a.atk = null; }
  }
  let fadeEl = null;
  function fade(to, sec) {
    if (!fadeEl) { fadeEl = document.createElement('div'); fadeEl.style.cssText = 'position:fixed;inset:0;background:#fff;z-index:45;pointer-events:none;opacity:0'; document.body.appendChild(fadeEl); }
    fadeEl.style.transition = 'opacity ' + sec + 's ease'; requestAnimationFrame(() => { fadeEl.style.opacity = to; });
  }

  W.frame = function (dt, R) {
    if (!scene) setup(R);
    if (!ninja && S.Chars && S.Chars.ready && S.WorkerView && S.Anim && S.Anim.ready) makeNinja();
    if (ninja) { step(dt); ninja.update(a, Math.max(dt, 1e-4), t); }
    if ((W.cvN = (W.cvN || 0) + 1) % 30 === 1) S.Flat.convert(scene, { pastel: 0.6 });
    R.r.shadowMap.enabled = true; R.r.shadowMap.type = THREE.PCFSoftShadowMap;
    R.r.render(scene, cam);
  };
  W.play = function (cb) {
    if (W.busy) return; W.busy = true;
    if (!ninja) { fade(1, 0.3); setTimeout(() => { cb(); setTimeout(() => fade(0, 1.0), 120); W.busy = false; }, 350); return; }
    smoke = { t: 0, cb }; a.atk = 'bottle'; a.st = 'act'; a.t = 0; a.dur = 0.5;
  };
  // boot: the logo on white, fade in, three seconds, fade out
  W.splash = function (done) {
    const bc = document.getElementById('bootcover'); if (bc) bc.remove();
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
