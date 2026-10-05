'use strict';
// ANIM: motion-captured clips for the market workers. Real people, recorded: the CMU Graphics Lab Motion
// Capture Database (mocap.cs.cmu.edu; free to use, including in commercial products), BVH release by
// B. Hahne. tools converted the takes offline into the campaign's 15-joint rig (the same points the ragdoll
// simulates), in place and facing +z, with loop points found automatically for the cycles.
//
//   S.Anim.load()                 fetch and unpack clips.json
//   S.Anim.sample(name, t, out)   fill out[15] (THREE.Vector3, rig space, metres) at time t (s); loops wrap
//   S.Anim.clip(name)             { n, dur, loop, speed (m/s travelled by a looping walk), peak (s of the hit) }
(function () {
  const A = S.Anim = { ready: false, clips: {}, joints: null };
  A.load = function () {
    if (A.loading) return A.loading;
    A.loading = fetch('assets/anim/clips.json').then((r) => r.json()).then((j) => {
      A.fps = j.fps; A.joints = j.joints; const J = j.joints.length;
      for (const name in j.clips) {
        const c = j.clips[name], bin = atob(c.data), b = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) b[i] = bin.charCodeAt(i);
        const i16 = new Int16Array(b.buffer), f = new Float32Array(i16.length);
        for (let i = 0; i < i16.length; i++) f[i] = i16[i] / 1000;
        A.clips[name] = { n: c.n, dur: c.n / j.fps, loop: c.loop, speed: c.speed, peak: c.peak, f, J };
      }
      A.ready = true;
    }).catch(() => {});
    return A.loading;
  };
  A.clip = (name) => A.clips[name];
  // sample with linear interpolation between frames
  A.sample = function (name, t, out) {
    const c = A.clips[name]; if (!c) return false;
    let x = t * A.fps; const n = c.n;
    if (c.loop) { x = ((x % n) + n) % n; } else x = Math.max(0, Math.min(n - 1.001, x));
    const i0 = Math.floor(x), i1 = c.loop ? (i0 + 1) % n : Math.min(n - 1, i0 + 1), w = x - i0, J = c.J, f = c.f;
    for (let j = 0; j < J; j++) {
      const a = (i0 * J + j) * 3, b = (i1 * J + j) * 3;
      out[j].set(f[a] + (f[b] - f[a]) * w, f[a + 1] + (f[b + 1] - f[a + 1]) * w, f[a + 2] + (f[b + 2] - f[a + 2]) * w);
    }
    return true;
  };
  if (document.readyState === 'complete') A.load(); else window.addEventListener('load', () => A.load());
})();
