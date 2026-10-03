'use strict';
// Touch controls for phones and tablets: a movement circle on the left, PUSH / GRAB / DEFEND (+ SKILL) on the right.
// They feed S.touch, which the keyboard source merges in, so every mode works with touch.
(function () {
  const isTouch = window.matchMedia && (matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window);
  S.touch = { mx: 0, mz: 0, push: false, grab: false, dash: false, skill: false, on: !!isTouch };
  if (!isTouch) return;
  document.documentElement.classList.add('touch');

  // never drag, scroll or zoom the page
  const stop = (e) => {
    const t = e.target;
    if (t && t.tagName === 'INPUT') return;
    // menus may scroll (move list, locker); the game screen never drags
    if (t && t.closest && !document.body.classList.contains('playing') && t.closest('#screen')) return;
    e.preventDefault();
  };
  document.addEventListener('touchmove', stop, { passive: false });
  document.addEventListener('gesturestart', stop, { passive: false });
  document.addEventListener('dblclick', stop, { passive: false });
  document.addEventListener('contextmenu', (e) => e.preventDefault());
  document.addEventListener('selectstart', (e) => { if (!(e.target && e.target.tagName === 'INPUT')) e.preventDefault(); });
  // holding a finger on the game or the controls must never zoom, magnify or select
  document.addEventListener('touchstart', (e) => {
    const t = e.target;
    if (t && t.closest && (t.closest('#tpad') || t.closest('#gl') || document.body.classList.contains('playing') && !t.closest('#screen'))) e.preventDefault();
  }, { passive: false });

  // first tap: go fullscreen and lock to landscape where the browser allows it
  const goFull = () => {
    const el = document.documentElement;
    const req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (req && !document.fullscreenElement) {
      Promise.resolve(req.call(el)).then(() => { if (screen.orientation && screen.orientation.lock) screen.orientation.lock('landscape').catch(() => {}); }).catch(() => {});
    }
  };
  // every tap tries again, so leaving full screen by accident is fixed by the next tap
  document.addEventListener('pointerdown', () => { if (!standalone) goFull(); });
  const standalone = matchMedia('(display-mode: fullscreen), (display-mode: standalone)').matches || navigator.standalone || S.APP !== 'web'; // the apps are always full screen
  const canFull = !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen);
  const iOS = /iP(hone|od|ad)/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (!standalone && (iOS || !canFull)) {
    const tip = document.createElement('div'); tip.id = 'tfull'; tip.className = 'on';
    tip.innerHTML = 'For full screen: tap <b>Share</b> then <b>Add to Home Screen</b>, and open Kumite from there';
    tip.addEventListener('click', () => tip.classList.remove('on'));
    document.body.appendChild(tip);
  }

  const pad = document.createElement('div');
  pad.id = 'tpad';
  pad.innerHTML = '<div id="tstick"><div id="tknob"></div></div>' +
    '<div id="tbtns"><button data-b="skill" id="tskill">SKILL</button><button data-b="grab">GRAB</button><button data-b="dash">DEFEND</button><button data-b="push">PUSH</button></div>' +
    '<button id="tpause" aria-label="Pause">II</button>';
  document.body.appendChild(pad);
  const rot = document.createElement('div');
  rot.id = 'trotate'; rot.innerHTML = '<div>↻</div>Turn your phone sideways to play';
  document.body.appendChild(rot);

  // movement circle
  const stick = pad.querySelector('#tstick'), knob = pad.querySelector('#tknob');
  let sid = null;
  const moveTo = (e) => {
    const r = stick.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2, R = r.width / 2;
    let dx = (e.clientX - cx) / R, dy = (e.clientY - cy) / R;
    const l = Math.hypot(dx, dy); if (l > 1) { dx /= l; dy /= l; }
    knob.style.transform = 'translate(' + dx * R * 0.6 + 'px,' + dy * R * 0.6 + 'px)';
    const dead = Math.hypot(dx, dy) < 0.22;
    S.touch.mx = dead ? 0 : dx; S.touch.mz = dead ? 0 : dy;
  };
  stick.addEventListener('pointerdown', (e) => { sid = e.pointerId; stick.setPointerCapture(sid); moveTo(e); });
  stick.addEventListener('pointermove', (e) => { if (e.pointerId === sid) moveTo(e); });
  const release = (e) => { if (e.pointerId !== sid) return; sid = null; S.touch.mx = S.touch.mz = 0; knob.style.transform = ''; };
  stick.addEventListener('pointerup', release); stick.addEventListener('pointercancel', release);

  // action buttons (several fingers at once are fine)
  for (const b of pad.querySelectorAll('#tbtns button')) {
    const k = b.dataset.b;
    const on = (e) => { e.preventDefault(); b.setPointerCapture(e.pointerId); S.touch[k] = true; b.classList.add('down'); };
    const off = () => { S.touch[k] = false; b.classList.remove('down'); };
    b.addEventListener('pointerdown', on); b.addEventListener('pointerup', off); b.addEventListener('pointercancel', off);
  }
  pad.querySelector('#tpause').addEventListener('pointerdown', (e) => {
    e.preventDefault(); dispatchEvent(new KeyboardEvent('keydown', { code: 'Escape' }));
  });

  // the game tells us when a bout is on screen, and whether a skill is held
  S.touchState = (playing, hasSkill) => {
    document.body.classList.toggle('playing', !!playing);
    document.body.classList.toggle('menus', !playing);
    document.body.classList.toggle('hasskill', !!hasSkill);
    if (!playing) { S.touch.push = S.touch.grab = S.touch.dash = S.touch.skill = false; }
  };
})();
