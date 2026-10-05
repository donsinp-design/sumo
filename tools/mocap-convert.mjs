// CMU BVH -> compact 15-joint rig clips for the campaign (in place, facing +z, looped where needed)
import fs from 'fs';
import * as THREE from 'three';
import { parse, positions } from './bvh.mjs';
// usage: put CMU BVH files (github.com/una-dinosauria/cmu-mocap) in tools/cmu-bvh/, then: node tools/mocap-convert.mjs
const DIR = new URL('./cmu-bvh/', import.meta.url).pathname, FPS = 30;
const NAMES = ['pelvis', 'neck', 'head', 'shL', 'elL', 'haL', 'shR', 'elR', 'haR', 'hipL', 'knL', 'ftL', 'hipR', 'knR', 'ftR'];
// rig L (sd = -1) is the subject's Right side
const MAP = { pelvis: 'Hips', neck: 'Neck', shL: 'RightArm', elL: 'RightForeArm', haL: 'RightHand', shR: 'LeftArm', elR: 'LeftForeArm', haR: 'LeftHand', hipL: 'RightUpLeg', knL: 'RightLeg', ftL: 'RightFoot', hipR: 'LeftUpLeg', knR: 'LeftLeg', ftR: 'LeftFoot' };
const CLIPS = [
  { name: 'idle', file: '137_28', t0: 2, t1: 14, loop: [2.5, 6] },
  { name: 'stance', file: '13_17', t0: 5.5, t1: 8.5, loop: [1.0, 2.6] },
  { name: 'walk', file: '137_29', t0: 1, t1: 9, loop: [1.0, 2.6], move: true },
  { name: 'stalk', file: '17_01', t0: 2, t1: 14, loop: [1.0, 2.6], move: true },
  { name: 'heavy', file: '137_42', t0: 1, t1: 12, loop: [1.0, 3.0], move: true },
  { name: 'run', file: '16_35', t0: 0.05, t1: 1.35, loop: [0.5, 1.2], move: true },
  { name: 'jab', file: '13_17', t0: 1.15, t1: 2.6, peak: 1.9 },
  { name: 'grab', file: '18_03', t0: 0.5, t1: 2.4, peak: 1.3 },
  { name: 'throw', file: '33_01', t0: 1.5, t1: 3.1, peak: 2.4 },
  { name: 'sweep', file: '02_07', t0: 14.9, t1: 16.4, peak: 15.6, mirror: true },
  { name: 'shout', file: '56_03', t0: 0.3, t1: 2.6, peak: 1.4 },
];
const smooth = (arr, w) => arr.map((_, i) => { let s = 0, n = 0; for (let k = Math.max(0, i - w); k <= Math.min(arr.length - 1, i + w); k++) { s += arr[k]; n++; } return s / n; });
const out = {};
const cache = {};
for (const C of CLIPS) {
  const B = cache[C.file] || (cache[C.file] = parse(DIR + C.file + '.bvh'));
  const src = Math.round(1 / B.dt), step = src / FPS;
  const T0 = positions(B, 0), scale = 0.92 / T0.Hips.y; // frame 0 is the T-pose
  const frames = [];
  for (let f = Math.round(C.t0 * src); f < Math.min(B.frames.length, Math.round(C.t1 * src)); f += step) {
    const P = positions(B, Math.round(f)), o = {};
    for (const n of NAMES) {
      let src2 = MAP[n];
      if (C.mirror && src2) src2 = src2.startsWith('Right') ? src2.replace('Right', 'Left') : src2.startsWith('Left') ? src2.replace('Left', 'Right') : src2;
      if (n === 'head') { const h = P.Head, nk = P.Neck1 || P.Neck; o.head = h.clone().add(h.clone().sub(nk).multiplyScalar(0.9)); }
      else o[n] = P[src2].clone();
      if (C.mirror) o[n].x = -o[n].x;
    }
    if (C.mirror) o.head.x = o.head.x; // (already mirrored above via clone of mirrored Head)
    for (const n of NAMES) o[n].multiplyScalar(scale);
    frames.push(o);
  }
  // facing: the hips' forward (x = rig right, the subject's left)
  const yaw = frames.map((o) => { const X = o.hipR.clone().sub(o.hipL); const fw = new THREE.Vector3().crossVectors(X, new THREE.Vector3(0, 1, 0)); return Math.atan2(fw.x, fw.z); });
  // unwrap
  for (let i = 1; i < yaw.length; i++) { while (yaw[i] - yaw[i - 1] > Math.PI) yaw[i] -= 2 * Math.PI; while (yaw[i] - yaw[i - 1] < -Math.PI) yaw[i] += 2 * Math.PI; }
  const W = Math.round(FPS * 0.6);
  const yawS = C.loop ? smooth(yaw, W) : yaw.map(() => yaw[0]);
  const px = frames.map((o) => o.pelvis.x), pz = frames.map((o) => o.pelvis.z);
  const pxS = C.loop ? smooth(px, W) : px.map(() => px[0]), pzS = C.loop ? smooth(pz, W) : pz.map(() => pz[0]);
  // clip travel speed (for matching playback rate to the actor's speed)
  const pxT = smooth(px, 6), pzT = smooth(pz, 6); let speed = 0; // path speed (light smoothing removes the side-to-side sway)
  const rel = frames.map((o, i) => {
    const r = {}, q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -yawS[i]);
    for (const n of NAMES) { const v = o[n].clone(); v.x -= pxS[i]; v.z -= pzS[i]; v.applyQuaternion(q); r[n] = v; }
    if (!C.loop) { const k = Math.min(1, 0.6 / Math.max(0.6, Math.hypot(r.pelvis.x, r.pelvis.z))); } // (lunges keep their travel)
    return r;
  });
  // loop: find the best matching pair of frames inside the allowed cycle length, crossfade the seam
  let seg = rel;
  if (C.loop) {
    const feat = (r) => NAMES.flatMap((n) => { const v = r[n].clone().sub(r.pelvis); return [v.x, v.y, v.z]; });
    const F = rel.map(feat), d = (a, b) => a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0);
    let best = [0, rel.length - 1, 1e9];
    const L1 = Math.round(C.loop[0] * FPS), L2 = Math.round(C.loop[1] * FPS);
    for (let i = 0; i < rel.length - L1; i++) for (let j = i + L1; j < Math.min(rel.length, i + L2); j++) {
      const v = d(F[i], F[j]) + d(F[Math.min(i + 1, rel.length - 1)], F[Math.min(j + 1, rel.length - 1)]);
      if (v < best[2]) best = [i, j, v];
    }
    seg = rel.slice(best[0], best[1]);
    let dd = 0; for (let i = best[0] + 1; i < best[1]; i++) dd += Math.hypot(pxT[i] - pxT[i - 1], pzT[i] - pzT[i - 1]); speed = dd / ((best[1] - best[0]) / FPS);
    const X = Math.min(6, Math.floor(seg.length / 4));
    for (let k = 0; k < X; k++) { const w = (k + 1) / (X + 1), a = seg[seg.length - X + k], b = rel[best[1] + k] || seg[k]; for (const n of NAMES) a[n].lerp(b[n], w); }
    console.log(C.name, 'loop', ((best[1] - best[0]) / FPS).toFixed(2) + 's', 'err', best[2].toFixed(3), 'speed', speed.toFixed(2));
  } else console.log(C.name, (seg.length / FPS).toFixed(2) + 's', 'peak at', (C.peak - C.t0).toFixed(2));
  // pack: int16 millimetres
  const buf = new Int16Array(seg.length * NAMES.length * 3); let k = 0;
  for (const r of seg) for (const n of NAMES) { buf[k++] = Math.round(r[n].x * 1000); buf[k++] = Math.round(r[n].y * 1000); buf[k++] = Math.round(r[n].z * 1000); }
  out[C.name] = { n: seg.length, loop: !!C.loop, speed: C.move ? +speed.toFixed(3) : 0, peak: C.peak ? +(C.peak - C.t0).toFixed(3) : 0, data: Buffer.from(buf.buffer).toString('base64') };
}
fs.writeFileSync(new URL('../public/assets/anim/clips.json', import.meta.url).pathname, JSON.stringify({ fps: FPS, joints: NAMES, src: 'CMU Graphics Lab Motion Capture Database (mocap.cs.cmu.edu), BVH by B. Hahne', clips: out }));
console.log('bytes', fs.statSync(new URL('../public/assets/anim/clips.json', import.meta.url).pathname).size);
