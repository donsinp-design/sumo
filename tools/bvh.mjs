// BVH -> world joint positions per frame (CMU cgspeed release)
import fs from 'fs';
import * as THREE from 'three';
export function parse(file) {
  const txt = fs.readFileSync(file, 'utf8'), tok = txt.split(/\s+/).filter(Boolean);
  let i = 0; const joints = [];
  function node(parent) {
    const kind = tok[i++]; const name = kind === 'End' ? (tok[i++], parent.name + '_end') : tok[i++];
    const j = { name, parent, offset: null, channels: [], children: [] }; joints.push(j);
    i++; // {
    while (tok[i] !== '}') {
      const t = tok[i++];
      if (t === 'OFFSET') { j.offset = [+tok[i++], +tok[i++], +tok[i++]]; }
      else if (t === 'CHANNELS') { const n = +tok[i++]; for (let k = 0; k < n; k++) j.channels.push(tok[i++]); }
      else if (t === 'JOINT' || t === 'End') { i--; j.children.push(node(j)); }
    }
    i++; return j;
  }
  i = tok.indexOf('ROOT'); const root = node(null);
  i = tok.indexOf('MOTION') + 1; i++; const nF = +tok[i++]; i += 2; const dt = +tok[i++];
  const nC = joints.reduce((s, j) => s + j.channels.length, 0), frames = [];
  for (let f = 0; f < nF; f++) { const row = new Float32Array(nC); for (let c = 0; c < nC; c++) row[c] = +tok[i++]; frames.push(row); }
  return { root, joints, frames, dt };
}
export function positions(B, f) {
  const row = B.frames[f]; let c = 0; const out = {}; const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Vector3();
  const D2R = Math.PI / 180;
  function walk(j, parentM) {
    const pos = new THREE.Vector3(...j.offset); const rot = new THREE.Matrix4();
    for (const ch of j.channels) {
      const v = row[c++];
      if (ch === 'Xposition') pos.x += v; else if (ch === 'Yposition') pos.y += v; else if (ch === 'Zposition') pos.z += v;
      else { const r = new THREE.Matrix4(); if (ch === 'Xrotation') r.makeRotationX(v * D2R); else if (ch === 'Yrotation') r.makeRotationY(v * D2R); else r.makeRotationZ(v * D2R); rot.multiply(r); }
    }
    const M = new THREE.Matrix4().copy(parentM).multiply(new THREE.Matrix4().makeTranslation(pos.x, pos.y, pos.z)).multiply(rot);
    out[j.name] = new THREE.Vector3().setFromMatrixPosition(M);
    for (const ch of j.children) walk(ch, M);
  }
  walk(B.root, new THREE.Matrix4());
  return out;
}
