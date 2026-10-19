'use strict';
// LEVELS: the maps past the bathhouse. Each one is a Blender kit (tools/blender/lv_<id>.py -> assets/models/lv_<id>.glb) and its
// floor plan (-> js/levels/<id>.js, S.Levels.<id>), made by the same script so the colliders always match the art. The party modes
// and the level story (story.js) run on any of them; the bathhouse stays the stealth level it always was (stealth.js).
// What a layout holds (game coordinates: x right, z towards the camera, y up), see tools/blender/LEVELS.md:
//   bounds, rooms, floors / ramps (one walkable layer: no floor over another), solids (colliders), blockers (round ones), wet / ice
//   (the belly slide runs on), pool (water to duck under), conveyors (the ski travelator...), carts (push / hide in), hides (fixed
//   places to hide: a crate, a locker, a karaoke booth...), the party spots (start, maw, exit, pants, hider, seeker), movers (things
//   on a path that knock you down: a forklift), traps (a trapdoor: in at one, out at the other), crowd (people walking a loop: stand
//   among them and you're hidden), ring (where the boss's dohyo comes up), story (the level's own run: steps and the boss), style
//   (the ZZZ / Orbitals cel look: hard two-tone light, muted low-key colours, a few warm lights)
(function () {
  const Lv = S.Levels = S.Levels || {};
  S.LEVEL_ORDER = ['bath', 'shibuya', 'fish', 'kabuki', 'stadium', 'ski'];
  S.LEVEL_NAMES = { bath: ['THE BATHHOUSE', '銭湯'], shibuya: ['SHIBUYA', '渋谷'], fish: ['FISH MARKET', '魚市場'], kabuki: ['KABUKI THEATRE', '歌舞伎座'], stadium: ['THE STADIUM', 'スタジアム'], ski: ['SKI LODGE', 'スキー場'] };
  S.levelReady = (id) => id === 'bath' || !!Lv[id];
  const inR = (q, x, z) => x > q.x0 && x < q.x1 && z > q.z0 && z < q.z1;

  // ---------------------------------------------------------------- a layout's floor, rooms and water, for the engine (stealth.js asks these)
  S.LevelRT = function (L) {
    const rt = {
      L, bounds: L.bounds,
      floorY(x, z) {
        for (const r of L.ramps || []) if (inR(r, x, z)) { const t = r.ax === 'x' ? (x - r.x0) / (r.x1 - r.x0) : (z - r.z0) / (r.z1 - r.z0); return r.y0 + (r.y1 - r.y0) * t; }
        for (const f of L.floors || []) if (inR(f, x, z)) return f.y;
        return 0;
      },
      roomAt(x, z) { for (const r of L.rooms || []) if (inR(r, x, z)) return r.id; return 'out'; },
      room(x, z) { for (const r of L.rooms || []) if (inR(r, x, z)) return r; return null; },
      inPool(x, z) { return !!L.pool && inR(L.pool, x, z); },
      wetAt(x, z) { return (L.wet || []).some((q) => inR(q, x, z)) || rt.inPool(x, z); },
      iceAt(x, z) { return (L.ice || []).some((q) => inR(q, x, z)); },
      conveyorAt(x, z) { for (const c of L.conveyors || []) if (inR(c, x, z)) return c; return null; },
      slope(x, z) { const e = 0.3; return [(rt.floorY(x + e, z) - rt.floorY(x - e, z)) / (2 * e), (rt.floorY(x, z + e) - rt.floorY(x, z - e)) / (2 * e)]; },   // (dy/dx, dy/dz: a slide picks up speed downhill)
      safe(x, z) { const r = rt.room(x, z); return !!(r && r.safe); },
    };
    return rt;
  };

  // ---------------------------------------------------------------- the look: the flat shader's light, set per level (and put back after)
  let U0 = null;
  S.levelStyle = (st, scene) => {
    const U = S.Flat && S.Flat.U; if (!U) return;
    if (!U0) U0 = { lit: U.uLit.value.clone(), shade: U.uShade.value.clone(), lo: U.uLo.value, hi: U.uHi.value, form: U.uForm.value, lift: U.uLift.value };
    const s = st || {};
    U.uLit.value.copy(s.lit ? new THREE.Color().fromArray(s.lit) : U0.lit); U.uShade.value.copy(s.shade ? new THREE.Color().fromArray(s.shade) : U0.shade);
    U.uLo.value = s.lo !== undefined ? s.lo : U0.lo; U.uHi.value = s.hi !== undefined ? s.hi : U0.hi; U.uForm.value = s.form !== undefined ? s.form : U0.form; U.uLift.value = s.lift !== undefined ? s.lift : U0.lift;
    if (scene && s.sky) scene.background = new THREE.Color(s.sky);
    if (scene && s.fog) scene.fog = new THREE.Fog(s.fog[0], s.fog[1], s.fog[2]);
  };
  S.levelStyleReset = () => S.levelStyle(null, null);

  // ---------------------------------------------------------------- the kit (once per level; each play clones it)
  const kits = {};
  S.loadLevelKit = (id) => {
    if (kits[id]) return kits[id];
    const L = Lv[id]; if (!L) return Promise.resolve(null);
    return (kits[id] = new Promise((res) => new THREE.GLTFLoader().load('assets/models/lv_' + id + '.glb' + (L.v ? '?v=' + L.v : ''), (gl) => {
      gl.scene.traverse((o) => { if (o.isMesh && (Array.isArray(o.material) ? o.material : [o.material]).some((m) => /NEON/i.test(m.name || ''))) o.userData.neon = true; });   // (before the flat conversion renames them)
      const root = S.Flat.kit(gl.scene);
      // neon, screens, lamps: the M_NEON material is drawn unlit, full bright (the glow of Shibuya at night, the stage lights)
      root.traverse((o) => { if (!o.isMesh || !o.userData.neon) return; const ms = Array.isArray(o.material) ? o.material : [o.material];
        const nm = ms.map((m) => new THREE.MeshBasicMaterial({ map: m.map || null, color: m.map ? 0xffffff : m.color, side: THREE.DoubleSide, transparent: m.transparent, opacity: m.opacity }));
        o.material = nm.length === 1 ? nm[0] : nm; o.castShadow = false; });
      res(root);
    }, undefined, () => { kits[id] = null; res(null); })));
  };
})();
