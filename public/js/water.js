// Water that reads as water: clear, with light moving through it. Two materials share one set of tricks:
//  - caustics: the bright web of focused sunlight that dances on the bottom of shallow water
//  - glints: tiny sun sparkles on the surface that come and go
//  - depth: turquoise in the shallows, deep teal further out (pond), or barely any tint at all (puddle)
// Both animate on their own (time comes from the clock as each mesh renders), so nothing has to drive them.
(() => {
  const S = window.S || (window.S = {});
  const uTime = { value: 0 };
  const tick = () => { uTime.value = performance.now() / 1000; };

  const COMMON = `
    uniform float uTime;
    float h21(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
    float vnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
    // the classic tileable caustic: a few warped sine fields whose sharp peaks make the light web
    float caustic(vec2 uv, float t) {
      vec2 p = mod(uv * 6.28318, 6.28318) - 250.0, i = p; float c = 1.0, inten = 0.005;
      for (int n = 0; n < 4; n++) {
        float tt = t * (1.0 - (3.5 / float(n + 1)));
        i = p + vec2(cos(tt - i.x) + sin(tt + i.y), sin(tt - i.y) + cos(tt + i.x));
        c += 1.0 / length(vec2(p.x / (sin(i.x + tt) / inten), p.y / (cos(i.y + tt) / inten)));
      }
      c /= 4.0; c = 1.17 - pow(c, 1.4); return clamp(pow(abs(c), 8.0), 0.0, 1.0);
    }
    // sun sparkles: a sparse grid of points that each flash briefly at their own time
    float glints(vec2 p, float t) {
      vec2 g = floor(p), f = fract(p) - 0.5; float r = h21(g);
      float on = step(0.55, r) * smoothstep(0.8, 1.0, sin(t * (1.5 + r * 2.0) + r * 40.0));
      vec2 o = (vec2(h21(g + 7.1), h21(g + 3.3)) - 0.5) * 0.6;
      return on * smoothstep(0.13, 0.0, length(f - o));
    }`;
  const VS = `varying vec3 vW; varying vec2 vUv; varying vec3 vV;
    void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vUv = uv; vV = cameraPosition - w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;

  // a pond or sea: opaque, deep teal far out, turquoise in the shallows round `shore` (a disc of radius uShoreR)
  function pond(o) {
    o = o || {};
    const m = new THREE.ShaderMaterial({
      uniforms: { uTime, uShoreR: { value: o.shoreR || 0 }, uShallow: { value: new THREE.Color(o.shallow || 0x5fd0c4) }, uDeep: { value: new THREE.Color(o.deep || 0x1f7f97) },
        uSky: { value: new THREE.Color(o.sky || 0xcfe8f2) }, uScale: { value: o.scale || 0.16 } },
      vertexShader: VS,
      fragmentShader: COMMON + `
        uniform float uShoreR, uScale; uniform vec3 uShallow, uDeep, uSky; varying vec3 vW; varying vec3 vV;
        void main() {
          vec2 p = vW.xz; float r = length(p);
          float depth = clamp((r - uShoreR) / 14.0, 0.0, 1.0) * 0.75 + vnoise(p * 0.08) * 0.35;  // patches of sand and weed under the water
          vec3 col = mix(uShallow, uDeep, smoothstep(0.1, 1.0, depth));
          vec2 drift = vec2(uTime * 0.02, -uTime * 0.015);
          float c = caustic(p * uScale + drift, uTime * 0.45);
          c = max(c, caustic(p * uScale * 1.7 - drift * 1.3, uTime * 0.38) * 0.6);
          col += vec3(0.85, 1.0, 0.95) * c * mix(0.42, 0.12, depth);
          // long soft swell bands and a little sky in the surface at glancing angles
          float swell = sin(dot(p, vec2(0.35, 0.22)) + uTime * 0.9 + vnoise(p * 0.2) * 3.0);
          col += uSky * 0.05 * smoothstep(0.6, 1.0, swell);
          float fres = pow(1.0 - clamp(normalize(vV).y, 0.0, 1.0), 3.0);
          col = mix(col, uSky, fres * 0.45);
          col += vec3(1.0) * glints(p * 1.1 + vec2(uTime * 0.05, 0.0), uTime) * 1.2;
          gl_FragColor = vec4(col, 1.0);
        }`,
    });
    return m;
  }

  // a puddle on the floor: almost clear. The shape comes from `mask` (white = water), the floor shows through,
  // with caustic shimmer, a wet darker rim and glints. `strength` scales the effects for dark or bright floors.
  function puddle(mask, o) {
    o = o || {};
    return new THREE.ShaderMaterial({
      uniforms: { uTime, uMask: { value: mask }, uStr: { value: o.strength || 1 }, uSky: { value: new THREE.Color(o.sky || 0xdfeeff) } },
      vertexShader: VS, transparent: true, depthWrite: false,
      blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
      fragmentShader: COMMON + `
        uniform sampler2D uMask; uniform float uStr; uniform vec3 uSky; varying vec3 vW; varying vec2 vUv;
        void main() {
          float a = texture2D(uMask, vUv).a;
          if (a < 0.01) discard;
          vec2 p = vW.xz;
          float inner = smoothstep(0.35, 0.9, a), rim = smoothstep(0.08, 0.35, a) * (1.0 - smoothstep(0.45, 0.85, a));
          float c = caustic(p * 0.45 + vec2(uTime * 0.03), uTime * 0.6);
          float g = glints(p * 5.0, uTime * 1.3);
          float sheen = smoothstep(0.55, 1.0, sin(p.x * 0.9 - p.y * 0.6 + uTime * 0.7 + vnoise(p * 1.3) * 2.5)) * inner;
          float al = 0.0;
          al += 0.26 * smoothstep(0.08, 0.6, a);                                   // the wet darkening
          vec3 add = uSky * (0.16 * rim + 0.3 * sheen) + vec3(0.95, 1.0, 1.0) * (c * 0.2 * inner + g * 1.2 * inner);
          // premultiplied blend: alpha darkens the floor (wet), rgb adds the light (reflections, caustics, glints)
          gl_FragColor = vec4(add * uStr, al);
        }`,
    });
  }

  // attach to a mesh so its water material animates whenever it is drawn
  function animate(mesh) { const prev = mesh.onBeforeRender; mesh.onBeforeRender = function () { tick(); if (prev) prev.apply(this, arguments); }; return mesh; }

  S.Water = { pond, puddle, animate, uTime };
})();
