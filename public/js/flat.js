'use strict';
// FLAT LOOK (the campaign's Little-Kitty-Big-City style): every surface keeps its own flat colour, the sun only
// decides lit or in shadow (with a soft edge and a hint of form), shadows are a pale lilac tint, nothing is black.
// One master material (MeshLambert with a patched light model) for everything, a soft sun with soft shadows.
(function () {
  const U = {
    uLit: { value: new THREE.Color(1.0, 0.985, 0.955) },     // sunlit: the colour as painted, a touch warm
    uShade: { value: new THREE.Color(0.80, 0.81, 0.95) },    // shadow: lilac-blue tint, never dark
    uSunI: { value: 1.0 }, uLo: { value: 0.06 }, uHi: { value: 0.34 }, uForm: { value: 0.14 }, uLift: { value: 0.03 },
  };
  function patch(m) {
    m.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, U);
      sh.fragmentShader = 'uniform vec3 uLit; uniform vec3 uShade; uniform float uSunI, uLo, uHi, uForm, uLift;\n' + sh.fragmentShader
        .replace('#include <lights_lambert_pars_fragment>', `#include <lights_lambert_pars_fragment>
float flatSun = 0.0;
void RE_Direct_Flat( const in IncidentLight directLight, const in GeometricContext geometry, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
  flatSun += saturate( dot( geometry.normal, directLight.direction ) ) * max( directLight.color.r, max( directLight.color.g, directLight.color.b ) );
}
#undef RE_Direct
#define RE_Direct RE_Direct_Flat`)
        .replace('#include <output_fragment>', `{
  float s = flatSun / uSunI;
  float L = mix( smoothstep( uLo, uHi, s ), clamp( s, 0.0, 1.0 ), uForm );
  outgoingLight = diffuseColor.rgb * mix( uShade, uLit, L ) + totalEmissiveRadiance;
  outgoingLight = uLift + ( 0.99 - uLift ) * outgoingLight;
}
#include <output_fragment>`);
    };
    m.customProgramCacheKey = () => 'flat1';
    m.userData.flat = true;
    return m;
  }
  // the master material: a flat colour, or a palette / texture map
  function mat(color, o) {
    o = o || {};
    const m = new THREE.MeshLambertMaterial({ color: color === undefined ? 0xffffff : color, map: o.map || null, vertexColors: !!o.vertexColors,
      side: o.side || THREE.FrontSide, transparent: !!o.transparent, opacity: o.opacity === undefined ? 1 : o.opacity });
    if (o.transparent) m.depthWrite = o.depthWrite !== undefined ? o.depthWrite : false;
    return patch(m);
  }
  // old toon colours -> the soft pastel range: lighter, a little less saturated (no near-blacks)
  const hsl = {};
  function pastel(c, k) {
    k = k === undefined ? 1 : k;
    c.getHSL(hsl);
    const l = hsl.l + (Math.max(hsl.l, 0.5 + 0.42 * hsl.l) - hsl.l) * k, s = hsl.s * (1 - 0.22 * k);
    return c.setHSL(hsl.h, s, Math.min(0.93, l));
  }
  // convert a built scene graph: toon shader materials become the master material, outline hulls go, all cast shadows
  const cache = new Map();
  function convertMat(m, o) {
    if (!m || m.userData.flat) return m;
    if (cache.has(m)) return cache.get(m);
    let out = m;
    if (m.uniforms && m.uniforms.uThick) out = null;                                            // ink outline: gone
    else if (m.uniforms && m.uniforms.uColor) {                                                  // the toon shader
      const map = m.uniforms.uHasMap && m.uniforms.uHasMap.value ? m.uniforms.uMap.value : null;
      out = mat(map ? 0xffffff : pastel(m.uniforms.uColor.value.clone(), o.pastel), { map, side: m.side, transparent: m.transparent, opacity: m.uniforms.uAlpha ? m.uniforms.uAlpha.value : 1 });
      out.userData.toon = m;                                                                     // keep hit-flash uniforms reachable
    } else if (m.isMeshStandardMaterial || m.isMeshPhongMaterial || m.isMeshLambertMaterial || m.isMeshToonMaterial) {
      out = mat(m.map ? 0xffffff : pastel(m.color.clone(), o.pastel), { map: m.map, side: m.side, transparent: m.transparent, opacity: m.opacity, vertexColors: m.vertexColors });
      if (m.map) out.color.copy(m.color);
    }
    if (out && m.clippingPlanes) out.clippingPlanes = m.clippingPlanes;
    cache.set(m, out);
    return out;
  }
  function convert(root, o) {
    o = o || {};
    root.traverse((q) => {
      if (!q.isMesh || q.userData.flatDone) return;
      q.userData.flatDone = true;
      const ms = Array.isArray(q.material) ? q.material : [q.material];
      const nm = ms.map((m) => convertMat(m, o));
      if (nm.some((m) => m === null)) { q.visible = false; return; }
      q.material = Array.isArray(q.material) ? nm : nm[0];
      if (nm.some((m) => m.userData && m.userData.flat)) { q.castShadow = !o.noCast; q.receiveShadow = true; }
    });
  }
  // the sun: soft, warm, from the back-left and high (short shadows that read under things), following the action
  function lights(scene, o) {
    o = o || {};
    const sun = new THREE.DirectionalLight(0xffffff, 1.0);
    sun.castShadow = true; sun.shadow.mapSize.set(o.map || 2048, o.map || 2048);
    const R = o.r || 20; Object.assign(sun.shadow.camera, { left: -R, right: R, top: R, bottom: -R, near: 1, far: 90 });
    sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.035; sun.shadow.radius = 4;
    scene.add(sun, sun.target);
    const off = new THREE.Vector3(-7, 17, 9);   // from behind the camera: the sumo's back (what you see most) is lit, shadows fall away up the street
    return { sun, aim(x, z) { sun.position.set(x + off.x, off.y, z + off.z); sun.target.position.set(x, 0, z); sun.target.updateMatrixWorld(); } };
  }
  // a model built from the Blender kit (palette texture or flat colours, glTF linear factors): the master material
  function kit(root) {
    const done = new Map();
    const conv = (m) => {
      if (done.has(m)) return done.get(m);
      let f;
      // both sides: Blender draws faces either way round, and a few kit pieces export facing down (the pizza's tablecloth)
      if (m.map) { m.map.encoding = THREE.LinearEncoding; m.map.needsUpdate = true; f = mat(0xffffff, { map: m.map, side: THREE.DoubleSide }); }
      else f = mat(m.color.clone().convertLinearToSRGB(), { side: THREE.DoubleSide, transparent: m.transparent, opacity: m.opacity });   // (water: see-through over the pond floor)
      done.set(m, f); return f;
    };
    root.traverse((o) => { if (!o.isMesh) return; o.material = Array.isArray(o.material) ? o.material.map(conv) : conv(o.material); o.castShadow = o.receiveShadow = true; o.userData.flatDone = true; });
    return root;
  }
  S.Flat = { U, patch, mat, pastel, convert, convertMat, lights, kit };
})();
