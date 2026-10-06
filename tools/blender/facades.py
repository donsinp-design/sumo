# Modular 3D building facades for the fish-market street (Blender 4.2, run headless by script).
#   python tools/blender/facades.py [out_dir] [shot=street shot=front shot=hall shot=row | noprev]
# Writes <out_dir>/facades.glb with one top-level object per module, plus preview renders.
#   shop_0..shop_5  two-storey shopfronts, 4.0 m wide (X -2..2), wall top 3.4 m (roof edge to 3.6)
#   hall_0..hall_2  market hall wall, 5.0 m wide, 4.6 m tall
#   bay_0, bay_1    loading bay with a roller door, 4.0 m wide, 4.4 m tall
# Blender Z up, metres. The wall plane is Y=0 and the front faces -Y; the origin is the bottom centre of the
# wall line. Ground-floor openings recess into the building (to Y=+0.62 at most) and are closed at the back, so
# a backing block behind a module must start at least 0.65 m behind the wall plane or the openings look shut.
# The look is carried by base colour (flat colours plus small painted textures, packed in the GLB) so a flat
# toon shader reads it; real depth (recesses, sills, signs, AC units, eaves) gives the silhouette and shadows.
# "Glass" in shop windows is drawn as a few glare strips over an open pane so displays stay visible to a shader
# without transparency.
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector, Matrix

ARGS = sys.argv[1:]
OUT = next((a for a in ARGS if '=' not in a and a not in ('noprev', 'debug') and not a.endswith('.py')),
           '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad/facades')
DEBUG = 'debug' in ARGS
SHOTS = [a[5:] for a in ARGS if a.startswith('shot=')] or ['street', 'front', 'hall', 'row']
if 'noprev' in ARGS or DEBUG: SHOTS = []
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
C = bpy.context
FONT = None
for f in ('/usr/share/fonts/truetype/fonts-japanese-gothic.ttf', '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'):
    if os.path.exists(f): FONT = bpy.data.fonts.load(f); break     # no CJK font: signs get raised blank panels instead

# ================================================================ colour, painted textures, materials
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def hexc(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])

def pnoise(n, cx, cy, rng):  # tileable value noise: cx cells across, cy cells up
    g = rng.random((cy, cx))
    def ax(c):
        t = np.arange(n) / n * c; i0 = np.floor(t).astype(int); f = t - i0; return i0 % c, (i0 + 1) % c, f * f * (3 - 2 * f)
    y0, y1, fy = ax(cy); x0, x1, fx = ax(cx); fx = fx[None, :]; fy = fy[:, None]
    a, b, c_, d = g[np.ix_(y0, x0)], g[np.ix_(y0, x1)], g[np.ix_(y1, x0)], g[np.ix_(y1, x1)]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c_ * (1 - fx) + d * fx) * fy
def fbm(n, rng, base=4, octs=4, sx=1, sy=1):
    s, w, tw = 0, 1.0, 0
    for o in range(octs):
        c = base * 2 ** o; s = s + w * pnoise(n, max(1, int(c * sx)), max(1, int(c * sy)), rng); tw += w; w *= 0.5
    return s / tw

def image(name, arr):  # arr: rows (bottom first) x cols x 3, sRGB 0..1 -> packed image
    h, w, _ = arr.shape
    im = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = np.clip(arr, 0, 1)
    im.pixels.foreach_set(px.ravel()); im.file_format = 'PNG'; im.pack(); return im

N = 256
def t_plaster(h, seed=1, n=N):
    rng = np.random.default_rng(seed); c = hexc(h)
    k = 0.93 + 0.12 * fbm(n, rng, 3, 4) - 0.04 * (fbm(n, rng, 20, 2) > 0.6)
    return c * k[..., None]
def t_wood(h, planks=4, seed=2, vertical=False, contrast=0.13, n=N):
    rng = np.random.default_rng(seed); c = hexc(h)
    grain = 0.6 * pnoise(n, 3, 40, rng) + 0.4 * pnoise(n, 7, 110, rng)
    p = n // planks; r = np.arange(n)
    tint = rng.uniform(-0.07, 0.07, planks)[np.minimum(r // p, planks - 1)][:, None]
    k = 0.92 + contrast * (grain - 0.5) * 2 + tint
    k = np.where(((r % p) < 2)[:, None], 0.6, k)
    a = c * k[..., None]
    return a.transpose(1, 0, 2) if vertical else a
def t_tiles(cols, grout, nt=8, seed=3, jit=0.05, n=N):
    rng = np.random.default_rng(seed); cs = np.array([hexc(c) for c in cols]); p = n // nt; ii = np.arange(n) // p
    idx = rng.integers(0, len(cs), (nt, nt)); tint = 1 + rng.uniform(-jit, jit, (nt, nt))
    a = cs[idx[np.ix_(ii, ii)]] * tint[np.ix_(ii, ii)][..., None]
    f = (np.arange(n) % p) / p
    a = a * (0.95 + 0.08 * f)[:, None, None]                          # a soft glaze: lighter towards the top of each tile
    g = (f < 0.07) | (f > 0.95)
    a[g[:, None] | g[None, :]] = hexc(grout)
    return a
def t_metal(h, seed=4, n=N):
    rng = np.random.default_rng(seed); c = hexc(h)
    k = 0.94 + 0.08 * pnoise(n, 40, 2, rng) + 0.06 * fbm(n, rng, 3, 3) - 0.03
    return c * k[..., None]
def t_hazard(n=N):
    u = np.arange(n) / n; s = (((u[None, :] + u[:, None]) * 3) % 1) < 0.5
    k = 0.95 + 0.08 * fbm(n, np.random.default_rng(5), 6, 3)
    return np.where(s[..., None], hexc('f0bf2e'), hexc('2a2622')) * k[..., None]
def t_glass(n=N):
    u = np.arange(n) / n; d = ((u[None, :] * 1 + u[:, None] * 1)) % 1
    a = np.repeat((hexc('3f5871') * (0.8 + 0.35 * u)[:, None])[:, None, :], n, axis=1)               # the sky reflected brighter towards the top
    band = ((d > 0.12) & (d < 0.24)) | ((d > 0.3) & (d < 0.34))
    a[band] = a[band] * 0.4 + hexc('b8d2e6') * 0.6
    return a
def t_weave(h, n=128):
    c = hexc(h); cell = 16; i = np.arange(n); ci = i // cell; f = (i % cell) / cell
    alt = (ci[:, None] + ci[None, :]) % 2
    k = np.where(alt == 0, 0.8 + 0.3 * np.sin(np.pi * f)[:, None], 0.8 + 0.3 * np.sin(np.pi * f)[None, :])
    return c * k[..., None]
def t_ice(n=N):
    rng = np.random.default_rng(6); f = fbm(n, rng, 10, 3)
    return np.where((f > 0.55)[..., None], hexc('f6fbfc'), hexc('cfe6ee') * (0.95 + 0.1 * f)[..., None])
def t_ribs(h, nr=10, n=N):  # paper lantern: bulging ribs, darker creases
    c = hexc(h); f = (np.arange(n) * nr / n) % 1
    k = 0.72 + 0.38 * np.sin(np.pi * f) ** 0.5
    return np.repeat((c * k[:, None])[:, None, :], n, axis=1)
def t_stripes(a, b, ns=4, n=N):
    u = (np.arange(n) * ns / n) % 1
    return np.repeat(np.where((u < 0.5)[:, None], hexc(a), hexc(b))[None, :, :], n, axis=0) * 1.0
def t_cloth(h, seed=7, n=N):
    rng = np.random.default_rng(seed); c = hexc(h)
    k = 0.94 + 0.08 * pnoise(n, 60, 3, rng) + 0.06 * fbm(n, rng, 2, 3)
    return c * k[..., None]
def t_concrete(h, seed=8, n=N):
    rng = np.random.default_rng(seed); c = hexc(h)
    k = 0.9 + 0.16 * fbm(n, rng, 4, 5) - 0.05 * (fbm(n, rng, 30, 2) > 0.62)
    return c * k[..., None]

UVS = {}   # material name -> metres per texture repeat (box-projected UVs)
MATS = {}
def mat(name, h, rough=0.7, metal=0.0, tex=None, scale=1.0, emit=0.0):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(h), 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if tex is not None:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = image('tx_' + name, tex); nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
        if emit: nt.links.new(t.outputs['Color'], b.inputs['Emission Color'])
        UVS[name] = scale
    elif emit: b.inputs['Emission Color'].default_value = (*srgb(h), 1)
    if emit: b.inputs['Emission Strength'].default_value = emit
    MATS[name] = m; return m

# ---- the shared palette
TRIM = mat('trim_wood', '4b3529', 0.6, tex=t_wood('4b3529', 2, 11, vertical=True), scale=1.2)
STONE = mat('stone', 'a59f95', 0.85, tex=t_concrete('a59f95', 12), scale=1.5)
CAP = mat('coping', '5d5753', 0.45, 0.3, tex=t_metal('5d5753', 13), scale=2)
CONC = mat('concrete', 'b4aea2', 0.9, tex=t_concrete('b4aea2', 14), scale=2)
GLASS = mat('glass', '3f5871', 0.08, tex=t_glass(), scale=1.1)
GLARE = mat('glare', 'b4d2e4', 0.05)
ALU = mat('aluminium', 'c7cbc9', 0.35, 0.4)
DARK = mat('dark', '2b2a2e', 0.5)
STEEL = mat('steel_grey', '70767c', 0.45, 0.5)
WHITE = mat('white', 'f2efe8', 0.5)
INK = mat('ink', '1f1c20', 0.5)
BULB = mat('bulb', 'fff1c8', 0.4, emit=6.0)
POT = mat('terracotta', 'b8664a', 0.8)
LEAF = [mat('leaf_a', '5c9a48', 0.7), mat('leaf_b', '4a863e', 0.7), mat('leaf_c', '73ad55', 0.7)]
SILL = mat('sill', 'ddd6c8', 0.7)
HAZ = mat('hazard', 'f0bf2e', 0.6, tex=t_hazard(), scale=0.75)
INT_WARM = mat('interior_warm', 'f4d9a2', 0.8, tex=t_plaster('f4d9a2', 21), scale=2, emit=0.5)       # lit interiors
INT_TILE = mat('interior_tile', 'e9f0ea', 0.4, tex=t_tiles(['eef3ee', 'e2ebe5'], 'b9c4c0', 8, 22), scale=1, emit=0.35)
INT_SIDE = mat('interior_side', 'c9a874', 0.8)
INT_DARK = mat('interior_ceiling', '4a3a30', 0.8)

# ================================================================ geometry helpers: every part goes into PARTS, joined per module
PARTS = []
def _fin(o, m, bev=0.0, seg=2, smooth=False):
    o.data.materials.append(m)
    if bev:
        b = o.modifiers.new('b', 'BEVEL'); b.width = bev; b.segments = seg; b.limit_method = 'ANGLE'
    if bev or smooth:
        for p in o.data.polygons: p.use_smooth = True
        o.modifiers.new('w', 'WEIGHTED_NORMAL').keep_sharp = True
    PARTS.append(o); return o
def box(x0, x1, y0, y1, z0, z1, m, bev=0.012, seg=2, rot=None):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = C.object; o.scale = (x1 - x0, y1 - y0, z1 - z0)
    if rot: o.rotation_euler = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    t = min(x1 - x0, y1 - y0, z1 - z0)
    return _fin(o, m, min(bev, 0.45 * t) if bev and t >= 0.03 else 0, seg if t >= 0.1 else 1)   # small parts: one bevel segment
def cyl(x, y, z, r, h, m, axis='Z', verts=12, r2=None, bev=0.0, seg=1, rot=None):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=(x, y, z))
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=(x, y, z))
    o = C.object
    o.rotation_euler = rot or {'Z': (0, 0, 0), 'X': (0, math.pi / 2, 0), 'Y': (math.pi / 2, 0, 0)}[axis]
    bpy.ops.object.transform_apply(rotation=True)
    return _fin(o, m, bev, seg, smooth=True)
def blob(x, y, z, sx, sy, sz, m, seg=12, rings=8, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=(x, y, z)); o = C.object
    o.scale = (sx, sy, sz); o.rotation_euler = rot; bpy.ops.object.transform_apply(scale=True, rotation=True)
    return _fin(o, m, smooth=True)
def mesh_obj(name, me, m, smooth=False):
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o); C.view_layer.objects.active = o
    return _fin(o, m, smooth=smooth)

PROF = {'trap': [(0, 0), (0.35, 0), (0.5, 1), (0.85, 1)], 'sine': [(0, 0), (0.25, 0.5), (0.5, 1), (0.75, 0.5)],
        'round': [(j / 6, math.sin(math.pi * j / 6)) for j in range(6)], 'ribs': [(0, 0), (0.5, 0), (0.62, 1), (0.88, 1)], 'slat': [(0, 0), (0.08, 1), (0.9, 1), (0.98, 0)]}
def ribbed(O, U, V, Nn, ul, vl, pitch, depth, m, prof='trap', solid=0.0, smooth=True, vseg=1):
    """A corrugated / folded sheet: profile repeats along U, runs straight along V, ribs stand out along Nn."""
    O, U, V, Nn = Vector(O), Vector(U), Vector(V), Vector(Nn)
    k = max(1, round(ul / pitch)); p = ul / k; pts = []
    for i in range(k):
        for f, d in PROF[prof]: pts.append((i * p + f * p, d * depth))
    pts.append((ul, PROF[prof][0][1] * depth))
    bm = bmesh.new(); rows = []
    for j in range(vseg + 1):
        v = vl * j / vseg; rows.append([bm.verts.new(O + U * u + V * v + Nn * d) for u, d in pts])
    for j in range(vseg):
        for i in range(len(pts) - 1): bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    bm.normal_update()
    if U.cross(V).dot(Nn) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new('rib'); bm.to_mesh(me); bm.free()
    o = mesh_obj('rib', me, m, smooth)
    if solid:
        s = o.modifiers.new('s', 'SOLIDIFY'); s.thickness = solid; s.offset = 1
        o.modifiers.move(len(o.modifiers) - 1, 0)
    return o
FACE = {'-Y': Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))), '+X': Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0))),
        '-X': Matrix(((0, 0, -1), (-1, 0, 0), (0, 1, 0)))}
def text(s, ctr, w, h, m, depth=0.02, face='-Y'):
    """Extruded CJK text standing `depth` proud of the surface point ctr, fitted inside w x h, back cap removed."""
    if FONT is None:
        x, y, z = ctr; R = FACE[face]; nrm = R @ Vector((0, 0, 1)); right = R @ Vector((1, 0, 0))
        c = Vector(ctr) + nrm * depth / 2; hw = right * w * 0.4
        return box(*sorted((c.x - abs(hw.x) - abs(nrm.x) * depth / 2, c.x + abs(hw.x) + abs(nrm.x) * depth / 2)),
                   *sorted((c.y - abs(hw.y) - abs(nrm.y) * depth / 2, c.y + abs(hw.y) + abs(nrm.y) * depth / 2)), z - h * 0.3, z + h * 0.3, m, 0.004, 1)
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = s; cu.font = FONT; cu.size = 1; cu.extrude = 0.5
    cu.resolution_u = 1; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.space_line = 0.9
    tmp = bpy.data.objects.new('txt', cu); scn.collection.objects.link(tmp)
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(C.evaluated_depsgraph_get())); bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.5], context='FACES')
    xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]
    k = min(w / (max(xs) - min(xs)), h / (max(ys) - min(ys))); cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    R = FACE[face]
    for v in bm.verts:
        v.co = Vector(ctr) + R @ Vector(((v.co.x - cx) * k, (v.co.y - cy) * k, (v.co.z + 0.5) * depth))
    bm.to_mesh(me); bm.free()
    return mesh_obj('txt', me, m)
def wire(pts, m, r=0.012, res=6):
    cu = bpy.data.curves.new('w', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 0; cu.resolution_u = res; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts): bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    tmp = bpy.data.objects.new('w', cu); scn.collection.objects.link(tmp)
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(C.evaluated_depsgraph_get())); bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    return mesh_obj('wire', me, m, smooth=True)

def finish(name, limits):
    """Apply modifiers, join into one object, project UVs (box mapping in metres per material), check the envelope."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in PARTS: o.select_set(True)
    C.view_layer.objects.active = PARTS[0]
    bpy.ops.object.convert(target='MESH')
    if DEBUG:
        agg = {}
        for p in C.selected_objects:
            k = p.data.materials[0].name if p.data.materials else '?'; agg[k] = agg.get(k, 0) + sum(len(q.vertices) - 2 for q in p.data.polygons)
        print('   ', sorted(agg.items(), key=lambda kv: -kv[1])[:12])
    bpy.ops.object.join()
    o = C.object; o.name = name; o.data.name = name
    me = o.data
    for uvl in list(me.uv_layers): me.uv_layers.remove(uvl)
    uv = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        s = UVS.get(o.material_slots[p.material_index].material.name, 1.0); n = p.normal; a = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co.y if a == 0 else co.x) / s * (1 if a != 0 or n.x < 0 else -1), (co.z if a != 2 else co.y) / s)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    (xa, xb), zmax, front_lo, front_hi = limits
    bad = []
    for v in me.vertices:
        c = v.co
        if c.x < xa - 1e-3 or c.x > xb + 1e-3: bad.append(('x', tuple(round(t, 3) for t in c)))
        if c.z > zmax + 1e-3 or c.z < -1e-3: bad.append(('z', tuple(round(t, 3) for t in c)))
        if c.y < -(front_hi if c.z >= 2.9 else front_lo) - 1e-3: bad.append(('y', tuple(round(t, 3) for t in c)))
    print(f'{name}: {tris} tris' + (f'  ENVELOPE {len(bad)} verts e.g. {bad[:3]}' if bad else ''))
    PARTS.clear(); MODULES.append(o); TRIS[name] = tris
    o.hide_render = o.hide_viewport = False
    return o
MODULES, TRIS = [], {}
SHOP_LIM = ((-2, 2), 3.6, 0.3, 0.7)

# ================================================================ shop building blocks
GT, S0, S1, UP0, TOP = 2.02, 2.1, 2.6, 2.62, 3.4      # opening top, sign band, upper wall start, wall top
WZ0, WZ1 = 2.78, 3.22                                 # upper windows

def shell(coping='5d5753'):
    for s in (-1, 1):                                  # edge posts: one dark timber post either side, so every seam reads as a pilaster
        box(s * 1.885, s * 2.0, -0.1, 0.3, 0.0, TOP + 0.02, TRIM, 0.022)
        box(s * 1.87, s * 2.0, -0.13, 0.3, 0.0, 0.22, STONE, 0.02)
    box(-1.885, 1.885, 0.0, 0.25, GT - 0.06, UP0 + 0.02, mat('lintel', '3a2e29', 0.7), 0)      # wall band behind the sign
    box(-1.89, 1.89, -0.24, 0.62, 0.0, 0.05, CONC, 0.01, 1)                                       # threshold slab
    if coping:   # the roof edge: the most visible line from the game camera, so each shop gets its own colour
        box(-2.0, 2.0, -0.11, 0.3, TOP, TOP + 0.1, mat('coping_' + coping, coping, 0.45, 0.25, tex=t_metal(coping, 15), scale=2), 0.025)
        box(-2.0, 2.0, -0.02, 0.3, TOP + 0.1, TOP + 0.16, CAP, 0.015, 1)
        box(-2.0, 2.0, -0.06, 0.3, TOP - 0.05, TOP, DARK, 0)                                       # shadow line under the coping

def interior(back=INT_WARM, depth=0.6, ceil=GT):
    box(-1.885, 1.885, depth, depth + 0.06, 0.0, ceil, back, 0)
    for s in (-1, 1): box(s * 1.8, s * 1.885, 0.25, depth, 0.0, ceil, INT_SIDE, 0)
    box(-1.885, 1.885, 0.0, depth + 0.06, ceil, ceil + 0.06, INT_DARK, 0)

def sign_band(board, frame, ink, label, tw=2.5, th=0.33, tx=0.0):
    box(-1.86, 1.86, -0.1, 0.02, S0 - 0.03, S1 + 0.03, frame, 0.02)
    box(-1.79, 1.79, -0.2, -0.05, S0, S1, board, 0.03)
    if label: text(label, (tx, -0.2, (S0 + S1) / 2), tw, th, ink, 0.022)

def sign_lamps(xs):  # gooseneck lamps over the sign
    for x in xs:
        wire([(x, 0.0, UP0 + 0.1), (x, -0.14, UP0 + 0.14), (x, -0.22, UP0 + 0.05)], DARK, 0.012, 4)
        cyl(x, -0.22, UP0 + 0.02, 0.025, 0.07, DARK, verts=10, r2=0.06)
        blob(x, -0.22, UP0 - 0.02, 0.035, 0.035, 0.02, BULB, 8, 5)

def upper_wall(wins, m, kind='flat', rib=None, x0=-1.885, x1=1.885):
    """The upper storey: a 0.2 m thick wall with window holes (all windows share WZ0..WZ1)."""
    yb = 0.0 if kind == 'flat' else 0.035
    pieces = [(x0, x1, UP0, WZ0), (x0, x1, WZ1, TOP)]
    xs = [x0] + [c for a, b in sorted(wins) for c in (a, b)] + [x1]
    pieces += [(xs[i], xs[i + 1], WZ0, WZ1) for i in range(0, len(xs), 2)]
    for a, b, z0, z1 in pieces:
        if b - a < 1e-3 or z1 - z0 < 1e-3: continue
        box(a, b, yb + (0.006 if kind == 'ribbed' else 0), 0.2, z0, z1, m, 0)
        if kind == 'ribbed':
            ribbed((a, yb, z0), (1, 0, 0), (0, 0, 1), (0, -1, 0), b - a, z1 - z0, 0.14, 0.03, rib or m, 'trap')
    if kind == 'ribbed':   # flashing where the siding starts
        box(x0, x1, -0.05, 0.05, UP0 - 0.02, UP0 + 0.05, CAP, 0.012, 1)

def window(a, b, frame=ALU, sill=SILL, dress='curtain', cur=None, surround=None, glass_y=0.15):
    z0, z1 = WZ0, WZ1; fw = 0.045
    box(a, b, glass_y, glass_y + 0.02, z0, z1, GLASS, 0)
    for (xa, xb, za, zb) in [(a, a + fw, z0, z1), (b - fw, b, z0, z1), (a, b, z0, z0 + fw), (a, b, z1 - fw, z1)]:
        box(xa, xb, glass_y - 0.05, glass_y, za, zb, frame, 0.008, 1)
    mx = (a + b) / 2
    box(mx - 0.02, mx + 0.02, glass_y - 0.07, glass_y - 0.02, z0, z1, frame, 0.006, 1)        # where the two sashes meet
    box(a - 0.07, b + 0.07, -0.09, 0.12, z0 - 0.06, z0 + 0.005, sill, 0.018)
    if surround:
        for (xa, xb, za, zb) in [(a - 0.06, a, z0, z1 + 0.06), (b, b + 0.06, z0, z1 + 0.06), (a - 0.06, b + 0.06, z1, z1 + 0.06)]:
            box(xa, xb, -0.025, 0.03, za, zb, surround, 0.01, 1)
    cy = glass_y - 0.035
    if dress == 'curtain':
        cw = (b - a - 2 * fw) * 0.3
        for xa in (a + fw, b - fw - cw * 0.8):
            ww = cw if xa == a + fw else cw * 0.8
            ribbed((xa, cy, z0 + fw), (1, 0, 0), (0, 0, 1), (0, -1, 0), ww, z1 - z0 - 2 * fw, 0.06, 0.022, cur, 'sine')
    elif dress == 'blind':
        hb = (z1 - z0 - 2 * fw) * 0.55
        ribbed((a + fw, cy, z1 - fw - hb), (0, 0, 1), (1, 0, 0), (0, -1, 0), hb, b - a - 2 * fw, 0.032, 0.012, cur, 'slat', smooth=False)
        box(a + fw, b - fw, cy - 0.02, cy + 0.01, z1 - fw - hb - 0.025, z1 - fw - hb, cur, 0.005, 1)
    elif dress == 'cafe':
        ribbed((a + fw, cy, z0 + fw), (1, 0, 0), (0, 0, 1), (0, -1, 0), b - a - 2 * fw, (z1 - z0) * 0.45, 0.05, 0.016, cur, 'sine')
        box(a + fw, b - fw, cy - 0.015, cy + 0.0, z0 + fw + (z1 - z0) * 0.45, z0 + fw + (z1 - z0) * 0.45 + 0.012, ALU, 0)

def ac_unit(x, z=2.95):
    W2, D, H = 0.36, 0.3, 0.4
    box(x - W2, x + W2, -0.06 - D, -0.05, z, z + H, mat('ac_body', 'ebe7dc', 0.45), 0.035)
    cyl(x - 0.08, -0.06 - D - 0.004, z + H / 2, 0.15, 0.02, DARK, 'Y', 16)
    for dz in (-0.07, 0.0, 0.07): box(x - 0.24, x + 0.08, -0.07 - D - 0.01, -0.06 - D, z + H / 2 + dz - 0.006, z + H / 2 + dz + 0.006, mat('ac_grille', 'b9b6ae', 0.5), 0)
    box(x + 0.15, x + 0.3, -0.065 - D, -0.06 - D + 0.01, z + 0.06, z + H - 0.06, mat('ac_grille', 'b9b6ae', 0.5), 0.005, 1)
    for s in (-1, 1):                                    # wall bracket: arm + strut
        box(x + s * 0.27 - 0.02, x + s * 0.27 + 0.02, -0.07 - D, 0.0, z - 0.04, z, STEEL, 0.005, 1)
        L = math.hypot(D, 0.32); ang = math.atan2(0.32, D)
        box(x + s * 0.27 - 0.015, x + s * 0.27 + 0.015, -L / 2, L / 2, -0.015, 0.015, STEEL, 0, rot=None)
        o = PARTS[-1]; o.data.transform(Matrix.Rotation(-ang, 4, 'X')); o.data.transform(Matrix.Translation((0, -D / 2 - 0.03, z - 0.17)))
    wire([(x + W2, -0.2, z + 0.12), (x + W2 + 0.1, -0.15, z + 0.08), (x + W2 + 0.12, -0.02, z + 0.05)], mat('pipe_cover', 'e6e1d4', 0.5), 0.028, 6)

def drainpipe(x, ztop=TOP - 0.02, y=-0.15):
    PIPE = mat('drainpipe', '8d8a84', 0.5, 0.2)
    cyl(x, y, ztop / 2 + 0.06, 0.04, ztop - 0.12, PIPE, verts=10)
    box(x - 0.055, x + 0.055, y - 0.06, 0.0, ztop - 0.18, ztop, PIPE, 0.02)
    for z in (0.7, 1.6, 2.5): cyl(x, y, z, 0.052, 0.035, STEEL, verts=10)
    box(x - 0.05, x + 0.05, y - 0.12, y + 0.04, 0.0, 0.1, PIPE, 0.02)

def meter_box(x, z):
    box(x - 0.13, x + 0.13, -0.11, 0.0, z, z + 0.32, mat('meter', 'cfccc3', 0.55), 0.02)
    box(x - 0.08, x + 0.08, -0.12, -0.1, z + 0.14, z + 0.27, GLASS, 0.004, 1)
    box(x - 0.06, x + 0.06, -0.125, -0.11, z + 0.03, z + 0.09, DARK, 0)
    cyl(x + 0.07, -0.05, z + 0.32 + (TOP - z - 0.32) / 2, 0.02, TOP - z - 0.32, mat('conduit', 'a7a49c', 0.6), verts=8)

def wires(x, z=TOP - 0.1, n=2):
    W_ = mat('cable', '25242a', 0.5)
    for i in range(n):
        dx = 0.12 * i
        wire([(x + dx, 0.0, z), (x + dx - 0.05, -0.22, z - 0.02), (x + dx - 0.18 - 0.1 * i, -0.42, z - 0.16 - 0.06 * i)], W_, 0.012, 6)
    box(x - 0.05, x + 0.05 + 0.12 * (n - 1), -0.04, 0.0, z - 0.05, z + 0.05, DARK, 0.01, 1)

def potted(x, ysill=-0.02, zsill=WZ0 + 0.005, big=1.0):
    cyl(x, ysill, zsill + 0.07 * big, 0.075 * big, 0.14 * big, POT, verts=12, r2=0.095 * big, bev=0.01)
    for i, (dx, dy, dz, r) in enumerate([(0, 0, 0.2, 0.1), (-0.07, -0.02, 0.16, 0.08), (0.07, 0.01, 0.17, 0.085), (0.02, -0.04, 0.26, 0.07)]):
        blob(x + dx * big, ysill + dy, zsill + dz * big, r * big, r * big, r * 0.85 * big, LEAF[i % 3], 10, 6)

def eave(a, b, z=TOP - 0.08, depth=0.42, m=None):
    m = m or mat('tin_eave', '5e7266', 0.5, 0.2)
    box(a, b, -depth, 0.02, z - 0.025, z + 0.025, m, 0.012, 1, rot=(-0.28, 0, 0))
    for x in (a + 0.1, b - 0.1): box(x - 0.015, x + 0.015, -depth + 0.06, 0.0, z - 0.11, z - 0.07, STEEL, 0, rot=(0.6, 0, 0))

def noren(x0, x1, ztop, zbot, m, panels, chars=(), ink=WHITE, y=-0.06):
    cyl((x0 + x1) / 2, y, ztop, 0.022, x1 - x0 + 0.1, mat('rod', '6b4a32', 0.6), 'X', 10)
    gap = 0.035; pw = (x1 - x0 - gap * (panels - 1)) / panels
    for i in range(panels):
        a = x0 + i * (pw + gap)
        ribbed((a, y + 0.012, zbot), (1, 0, 0), (0, 0, 1), (0, -1, 0), pw, ztop - zbot - 0.02, 0.14, 0.02, m, 'sine')
        if i < len(chars) and chars[i]:
            text(chars[i], (a + pw / 2, y - 0.012, (ztop + zbot) / 2 - 0.02), pw * 0.6, (ztop - zbot) * 0.55, ink, 0.008)

def fish(x, y, z, L, m, rz=0.0):
    c, s = math.cos(rz), math.sin(rz)
    blob(x, y, z, L / 2, L * 0.17, L * 0.075, m, 8, 5, (0, 0, rz))
    tx, ty = x - c * L * 0.55, y - s * L * 0.55
    box(tx - L * 0.07, tx + L * 0.07, ty - L * 0.07, ty + L * 0.07, z - 0.008, z + 0.008, m, 0, rot=(0, 0, rz + math.pi / 4))

# ================================================================ the six shops
def shop_fish():
    PL = mat('plaster_cream', 'efe2c6', 0.85, tex=t_plaster('efe2c6', 31), scale=2)
    shell('3f5a78'); interior(INT_TILE)
    sign_band(mat('sign_white', 'f6f1e6', 0.5), mat('sign_navy', '1f3360', 0.5), mat('ink_navy', '1f3360', 0.45), '鮮魚店', 2.3)
    box(-1.79, -1.79 + 0.36, -0.235, -0.2, S0 + 0.07, S1 - 0.07, mat('sign_red', 'c8342c', 0.5), 0.02)          # red end caps on the board
    box(1.79 - 0.36, 1.79, -0.235, -0.2, S0 + 0.07, S1 - 0.07, mat('sign_red', 'c8342c', 0.5), 0.02)
    sign_lamps((-0.9, 0.9))
    upper_wall([(-1.55, 0.35)], PL)
    window(-1.55, 0.35, dress='curtain', cur=mat('curtain_peach', 'eda78c', 0.85, tex=t_cloth('eda78c', 32), scale=0.5), surround=mat('trim_white', 'f7f2e8', 0.6))
    ac_unit(1.08); wires(1.55, n=2)
    # inside: a stainless back counter, menu placards, hanging enamel lamps
    STEELS = mat('stainless', 'b9c0c4', 0.3, 0.6)
    box(-1.75, 1.75, 0.38, 0.6, 0.0, 0.85, STEELS, 0.015)
    box(-1.6, 1.6, 0.56, 0.6, 1.25, 1.6, mat('menu_wood', '8a5a36', 0.7, tex=t_wood('8a5a36', 3, 33), scale=1), 0.01, 1)
    for i in range(6): box(-1.45 + i * 0.5, -1.15 + i * 0.5, 0.545, 0.56, 1.3, 1.55, WHITE, 0.004, 1); box(-1.38 + i * 0.5, -1.22 + i * 0.5, 0.54, 0.545, 1.33, 1.37, mat('red_ink', 'c8342c', 0.5), 0)
    for x in (-1.0, 1.0):
        cyl(x, 0.3, 1.95, 0.006, 0.16, DARK, verts=6)
        cyl(x, 0.3, 1.82, 0.03, 0.1, mat('enamel', '2f6a52', 0.4), verts=14, r2=0.15)
        blob(x, 0.3, 1.76, 0.05, 0.05, 0.05, BULB, 8, 4)
    # the display: a blue stand, an ice bed, the catch of the day
    box(-1.78, 1.78, -0.28, 0.24, 0.0, 0.66, mat('stand_blue', '2f6d93', 0.55), 0.03)
    box(-1.72, 1.72, -0.3, -0.27, 0.06, 0.6, mat('stand_blue_d', '275c7d', 0.6), 0.01, 1)
    ICE = mat('ice', 'd6ecf3', 0.25, tex=t_ice(), scale=0.6)
    box(-1.72, 1.72, -0.25, 0.2, 0.66, 0.76, ICE, 0.03)
    STY = mat('styrofoam', 'f4f3ee', 0.8)
    for x in (-1.45, 1.45):
        box(x - 0.24, x + 0.24, -0.22, 0.18, 0.76, 0.9, STY, 0.02)
        box(x - 0.2, x + 0.2, -0.18, 0.14, 0.86, 0.9, ICE, 0.01, 1)
    FS = [mat('fish_silver', 'a8b9c6', 0.3, 0.2), mat('fish_red', 'e06d55', 0.4), mat('fish_blue', '587a9c', 0.35, 0.1), mat('fish_gold', 'd8a441', 0.4)]
    for i in range(5): fish(-0.95 + i * 0.23, -0.11, 0.79, 0.34, FS[0 if i % 2 else 2], 0.35)
    for i in range(3): fish(0.35 + i * 0.25, -0.08, 0.8, 0.38, FS[1], -0.25)
    for i in range(4): fish(-1.45 + (i % 2) * 0.12, -0.08 + (i // 2) * 0.13, 0.94, 0.3, FS[3], 0.0)
    for i in range(3): blob(1.38 + (i - 1) * 0.13, -0.06 + (i % 2) * 0.08, 0.94, 0.07, 0.07, 0.045, mat('octopus', 'c84a4a', 0.4), 8, 5)
    TUNA = mat('tuna', 'b62e3c', 0.35)
    for i in range(2): box(-0.6 + i * 0.32, -0.32 + i * 0.32, 0.06, 0.17, 0.76, 0.84, TUNA, 0.02); box(-0.6 + i * 0.32, -0.32 + i * 0.32, 0.06, 0.17, 0.835, 0.845, mat('tuna_fat', 'f0b4b4', 0.4), 0)
    for x in (-1.0, -0.2, 0.62, 1.15):
        cyl(x, -0.21, 0.82, 0.005, 0.14, DARK, verts=4)
        box(x - 0.07, x + 0.07, -0.22, -0.2, 0.86, 0.95, WHITE, 0.004, 1)
        box(x - 0.05, x + 0.05, -0.225, -0.22, 0.9, 0.92, mat('red_ink', 'c8342c', 0.5), 0)
    noren(-1.78, 1.78, GT - 0.03, 1.45, mat('noren_navy', '22345e', 0.85, tex=t_cloth('22345e', 34), scale=0.6), 4, ('', '鮮', '魚', ''))
    return finish('shop_0', SHOP_LIM)

def shop_dried():
    SID = mat('siding_sage', '78a296', 0.55, 0.15, tex=t_metal('78a296', 41), scale=2)
    shell('8c4a30'); interior(mat('interior_wood', 'd6a96c', 0.75, tex=t_wood('d6a96c', 6, 42), scale=1.5, emit=0.4))
    WOODS = mat('sign_wood', '6e4329', 0.6, tex=t_wood('6e4329', 2, 43), scale=2)
    sign_band(WOODS, DARK, mat('ink_cream', 'f6e7c4', 0.5), '乾物', 1.5)
    for x in (-1.3, 1.3): cyl(x, -0.205, (S0 + S1) / 2, 0.13, 0.02, mat('sign_red', 'c8342c', 0.5), 'Y', 16)
    upper_wall([(-1.2, 1.0)], SID, 'ribbed')
    window(-1.2, 1.0, dress='blind', cur=mat('blind', 'ece6d6', 0.6), surround=mat('trim_white', 'f7f2e8', 0.6))
    drainpipe(1.94); meter_box(1.45, 2.75)
    # a perpendicular hanging sign, reads up and down the street
    RED = mat('sign_red', 'c8342c', 0.5)
    box(-1.68, -1.58, -0.66, -0.16, 2.96, 3.56, RED, 0.025)
    for s, f in ((-1, '-X'), (1, '+X')): text('乾\n物', (-1.63 + s * 0.05, -0.41, 3.26), 0.36, 0.5, mat('ink_cream', 'f6e7c4'), 0.012, f)
    for z in (3.0, 3.52): box(-1.64, -1.62, -0.2, 0.0, z - 0.012, z + 0.012, STEEL, 0)
    # inside: shelves of jars and packets
    SH = mat('shelf_wood', '9a6a40', 0.65, tex=t_wood('9a6a40', 2, 44), scale=1)
    PK = [mat('pack_a', 'e8c26a', 0.6), mat('pack_b', 'c8553d', 0.6), mat('pack_c', '5e8a4a', 0.6), mat('pack_d', 'f2ebd8', 0.6), mat('jar', 'c88a3a', 0.25)]
    for k, z in enumerate((0.75, 1.15, 1.55)):
        box(-1.8, 1.8, 0.3, 0.6, z - 0.04, z, SH, 0.01, 1)
        for i in range(7):
            x = -1.5 + i * 0.5 + (k % 2) * 0.1
            if (i + k) % 3 == 0: cyl(x, 0.45, z + 0.11, 0.07, 0.22, PK[4], verts=10)
            else: box(x - 0.1, x + 0.1, 0.36, 0.52, z, z + 0.16 + 0.05 * ((i * 7 + k) % 3), PK[(i + k) % 4], 0.012, 1)
    # out front: a stepped stand of baskets heaped with dried goods, under a short canvas awning
    box(-1.8, 1.8, -0.28, 0.05, 0.0, 0.42, SH, 0.02)
    box(-1.8, 1.8, 0.05, 0.42, 0.0, 0.72, SH, 0.02)
    BAS = mat('basket', 'c49a5c', 0.8, tex=t_weave('c49a5c'), scale=0.22)
    GOODS = ['e98a6a', '7a5238', '3d4a3a', 'd9d2c0', 'e07a2e', 'c8342c', 'e7d3a1', 'd9a77a']
    for row, (y, z) in enumerate(((-0.09, 0.42), (0.24, 0.72))):
        for i in range(4):
            x = -1.35 + i * 0.9 + row * 0.0; g = GOODS[(i + row * 4) % 8]
            cyl(x, y, z + 0.08, 0.17, 0.16, BAS, verts=12, r2=0.2)
            blob(x, y, z + 0.16, 0.18, 0.15, 0.07, mat('goods_' + g, g, 0.8, tex=t_plaster(g, 45 + i), scale=0.3), 12, 6)
            box(x + 0.08, x + 0.2, y - 0.17, y - 0.155, z + 0.2, z + 0.28, WHITE, 0.004, 1)
    AW = mat('awning', 'd9823a', 0.85, tex=t_stripes('d9823a', 'f3e6cc', 6), scale=1.5)
    box(-1.86, 1.86, -0.29, 0.02, GT - 0.12, GT - 0.09, AW, 0.012, 1, rot=(-0.32, 0, 0))
    box(-1.86, 1.86, -0.29, -0.26, GT - 0.3, GT - 0.12, AW, 0.01, 1)
    return finish('shop_1', SHOP_LIM)

def shop_knife():
    TL = mat('tile_brown', 'b58e66', 0.45, tex=t_tiles(['b58e66', 'c9a57b', 'a07a55', 'd4b994'], '7d6a58', 8, 51), scale=1)
    shell('3e5c4c'); interior(mat('interior_dim', 'e3c595', 0.8, emit=0.3))
    GOLD = mat('gold', 'd8b25a', 0.35, 0.6)
    sign_band(mat('lacquer', '1e1c1f', 0.25), mat('sign_gold_frame', '8c6a2e', 0.4, 0.4), GOLD, '刃物', 1.4)
    for x in (-1.2, 1.2): text('研' if x < 0 else '包丁', (x, -0.2, (S0 + S1) / 2), 0.55, 0.2, GOLD, 0.01)
    upper_wall([(-0.95, 0.95)], TL)
    window(-0.95, 0.95, frame=mat('frame_dark', '3b3330', 0.5), dress='cafe', cur=mat('lace', 'f4efe2', 0.8), surround=mat('trim_dark', '4a3a32', 0.6))
    eave(-1.15, 1.15); potted(0.72); potted(-0.7, big=0.8); wires(-1.6, n=1)
    # ground floor: a timber shopfront, display window on the left, a sliding door on the right
    WD = mat('front_wood', 'a4703f', 0.6, tex=t_wood('a4703f', 5, 52, vertical=True), scale=1.2)
    box(-1.86, 0.5, -0.05, 0.15, 0.05, 0.6, WD, 0.02)
    box(-1.86, 0.5, -0.16, 0.12, 0.58, 0.64, WD, 0.015)                                       # display ledge
    for xa, xb in ((-1.86, -1.78), (-0.71, -0.65), (0.42, 0.5), (1.78, 1.86)): box(xa, xb, -0.06, 0.1, 0.6, GT, WD, 0.012, 1)
    box(-1.86, 1.86, -0.06, 0.1, GT - 0.08, GT, WD, 0.012, 1)
    for x0, x1 in ((-1.78, -0.71), (-0.65, 0.42)):                                           # glare strips: reads as glass, keeps the display visible
        for (u, w, zc) in ((0.72, 0.035, 1.72), (0.84, 0.016, 1.68)):                              # two short glints in the top corner
            xa = x0 + (x1 - x0) * u; box(xa, xa + w, -0.004, 0.004, zc - 0.17, zc + 0.17, GLARE, 0)
            o = PARTS[-1]; o.data.transform(Matrix.Translation((-xa - w / 2, 0, -zc))); o.data.transform(Matrix.Rotation(-0.6, 4, 'Y')); o.data.transform(Matrix.Translation((xa + w / 2, 0, zc)))
    VEL = mat('velvet', '6e1f2a', 0.9, tex=t_cloth('6e1f2a', 53), scale=0.5)
    box(-1.78, 0.42, 0.3, 0.4, 0.64, 1.9, VEL, 0.01, 1)
    BL, HD = mat('blade', 'dfe4e7', 0.18, 0.85), mat('handle', '3a2a22', 0.5)
    for i in range(8):
        x = -1.6 + i * 0.27; tall = 0.28 + 0.06 * (i % 3)
        box(x - 0.025, x + 0.025, 0.27, 0.3, 1.2, 1.2 + tall, BL, 0.006, 1)
        box(x - 0.018, x + 0.018, 0.26, 0.3, 1.04, 1.2, HD, 0.006, 1)
    for i in range(3): box(-1.5 + i * 0.7, -1.2 + i * 0.7, -0.1, 0.05, 0.64, 0.72, mat('whetstone', 'd98a4a', 0.8), 0.012, 1)
    for i in range(5):  # a row of small knives laid on the ledge
        x = -1.6 + i * 0.42
        box(x, x + 0.22, -0.08, -0.04, 0.64, 0.655, BL, 0.004, 1); box(x + 0.22, x + 0.32, -0.08, -0.04, 0.64, 0.665, HD, 0.004, 1)
    # sliding door: frame, lattice upper glass, wooden lower panel, a short white noren
    for (xa, xb, y) in ((0.55, 1.2, 0.02), (1.15, 1.8, 0.07)):
        for (a, b, za, zb) in ((xa, xa + 0.06, 0.05, GT - 0.08), (xb - 0.06, xb, 0.05, GT - 0.08), (xa, xb, 0.05, 0.6), (xa, xb, 1.0, 1.05), (xa, xb, GT - 0.14, GT - 0.08)):
            box(a, b, y - 0.025, y + 0.025, za, zb, WD, 0.008, 1)
        for zz in (1.3, 1.6): box(xa, xb, y - 0.01, y + 0.01, zz, zz + 0.025, WD, 0)
        box(xa + 0.06, xb - 0.06, y + 0.012, y + 0.018, 1.05, GT - 0.14, mat('door_glass', '6f8aa0', 0.1), 0)
    noren(0.56, 1.78, GT - 0.1, 1.6, mat('noren_white', 'f1ece0', 0.85, tex=t_cloth('f1ece0', 54), scale=0.6), 2, ('刃', '物'), mat('ink_navy', '1f3360'), y=-0.04)
    return finish('shop_2', SHOP_LIM)

def shop_nori():
    PL = mat('plaster_salmon', 'e4a68c', 0.85, tex=t_plaster('e4a68c', 61), scale=2)
    shell('6b5446'); interior(mat('interior_warm2', 'f1d4a0', 0.8, tex=t_plaster('f1d4a0', 62), scale=2, emit=0.45))
    sign_band(mat('sign_green', '2f5d3a', 0.5), INK, mat('ink_cream', 'f6e7c4'), '海苔', 1.5)
    for x in (-1.3, 1.3): text('◆', (x, -0.2, (S0 + S1) / 2), 0.16, 0.16, mat('gold', 'd8b25a', 0.35, 0.6), 0.01)
    upper_wall([(-1.55, 0.2)], PL)
    window(-1.55, 0.2, dress='curtain', cur=mat('curtain_green', '9cc08e', 0.85, tex=t_cloth('9cc08e', 63), scale=0.5), surround=mat('trim_white', 'f7f2e8'))
    ac_unit(0.95); drainpipe(-1.94); wires(1.55, n=3)
    # the half-raised roller shutter
    SH = mat('shutter', 'b6c0c4', 0.45, 0.35, tex=t_metal('b6c0c4', 64), scale=1.5)
    box(-1.86, 1.86, -0.2, 0.2, GT - 0.18, GT + 0.02, mat('shutter_box', '9aa3a8', 0.45, 0.3), 0.03)
    ribbed((-1.8, -0.05, 1.16), (0, 0, 1), (1, 0, 0), (0, -1, 0), GT - 0.18 - 1.16, 3.6, 0.085, 0.025, SH, 'trap', solid=0.012, smooth=False)
    box(-1.8, 1.8, -0.1, 0.0, 1.08, 1.17, mat('shutter_bar', '6b7378', 0.4, 0.5), 0.02)
    for x in (-0.6, 0.6): box(x - 0.1, x + 0.1, -0.13, -0.1, 1.1, 1.14, DARK, 0.008, 1)
    for s in (-1, 1): box(s * 1.79, s * 1.87, -0.1, 0.02, 0.05, GT - 0.18, mat('shutter_rail', '8a9196', 0.45, 0.4), 0.01, 1)
    # the counter: stacks of nori in paper bands, tea tins, a little scale
    WD = mat('counter_wood', 'b07a48', 0.6, tex=t_wood('b07a48', 3, 65), scale=1)
    box(-1.75, 1.75, -0.26, 0.2, 0.0, 0.78, WD, 0.03)
    box(-1.7, 1.7, -0.28, -0.25, 0.08, 0.7, mat('counter_panel', '8a5a32', 0.6), 0.01, 1)
    NORI, BAND = mat('nori', '263428', 0.4), [mat('band_red', 'c8342c', 0.5), mat('band_gold', 'e2b84a', 0.5), WHITE]
    for i in range(6):
        x = -1.45 + i * 0.5; n = 3 + (i * 5) % 4
        for k in range(n): box(x - 0.17, x + 0.17, -0.2, 0.06, 0.78 + k * 0.04, 0.815 + k * 0.04, NORI, 0.006, 1)
        box(x - 0.04, x + 0.04, -0.206, 0.066, 0.78, 0.78 + n * 0.04 + 0.003, BAND[i % 3], 0)
    for i, c in enumerate(('2f6e4a', 'c8342c', 'd8a441', '2f6e4a', '22345e')):
        cyl(-1.5 + i * 0.75, 0.42, 0.9, 0.09, 0.22, mat('tin_' + c, c, 0.35, 0.3), verts=14, bev=0.01)
        cyl(-1.5 + i * 0.75, 0.42, 1.02, 0.092, 0.03, mat('gold', 'd8a441'), verts=14)
    box(-1.8, 1.8, 0.3, 0.6, 0.0, 0.78, WD, 0.02)
    return finish('shop_3', SHOP_LIM)

def shop_tamago():
    SID = mat('siding_blue', '8fa9bb', 0.55, 0.15, tex=t_metal('8fa9bb', 71), scale=2)
    TLW = mat('tile_teal', '9fcabd', 0.35, tex=t_tiles(['a6d0c3', '96c2b5', 'b2d8cc'], 'e8e4da', 16, 72), scale=1)
    shell('3f7a8a'); interior(INT_TILE)
    sign_band(mat('sign_yellow', 'f2c53d', 0.5), mat('sign_red', 'c8342c', 0.5), mat('ink_brown', '7a2618', 0.45), '玉子焼', 2.2)
    sign_lamps((-1.2, 0.0, 1.2))
    upper_wall([(-1.45, 0.55)], SID, 'ribbed')
    window(-1.45, 0.55, dress='blind', cur=mat('blind', 'ece6d6', 0.6), surround=mat('trim_white', 'f7f2e8'))
    meter_box(-1.7, 2.68)
    RED = mat('sign_red', 'c8342c', 0.5)
    box(1.6, 1.7, -0.66, -0.16, 2.96, 3.56, mat('sign_yellow', 'f2c53d'), 0.025)
    for s, f in ((-1, '-X'), (1, '+X')): text('玉\n子', (1.65 + s * 0.05, -0.41, 3.26), 0.36, 0.5, RED, 0.012, f)
    for z in (3.0, 3.52): box(1.64, 1.66, -0.2, 0.0, z - 0.012, z + 0.012, STEEL, 0)
    ac_unit(1.05)
    # ground floor: tiled wall with a serving window (left) and a doorway (right)
    for (a, b, za, zb) in ((-1.885, 0.25, 0.05, 0.84), (0.25, 0.85, 0.05, GT), (1.8, 1.885, 0.05, GT)):
        box(a, b, 0.0, 0.25, za, zb, TLW, 0)
    box(-1.885, 0.25, 0.0, 0.25, 1.95, GT, TLW, 0)
    box(-1.885, 0.25, -0.03, 0.02, 0.05, 0.2, mat('tile_skirt', '6a8aa0', 0.4), 0.01, 1)
    STEELS = mat('stainless', 'b9c0c4', 0.3, 0.6)
    box(-1.75, 0.25, -0.26, 0.25, 0.82, 0.88, STEELS, 0.015)
    box(-1.885, 0.25, -0.06, 0.02, 1.9, 1.98, mat('sign_red', 'c8342c'), 0.015)                # little red lintel
    PLATE, EGG, EGGT = WHITE, mat('egg', 'f6c945', 0.5), mat('egg_top', 'e2a23a', 0.5)
    for i in range(3):
        x = -1.45 + i * 0.4
        cyl(x, -0.08, 0.89, 0.13, 0.02, PLATE, verts=16)
        box(x - 0.1, x + 0.1, -0.15, -0.01, 0.9, 0.98, EGG, 0.025)
        box(x - 0.09, x + 0.09, -0.14, -0.02, 0.975, 0.99, EGGT, 0.006, 1)
        for k in (-0.05, 0.0, 0.05): box(x + k - 0.004, x + k + 0.004, -0.152, -0.149, 0.91, 0.97, EGGT, 0)
    # a glass case at the right of the counter: frame + glare only
    box(-0.25, 0.2, -0.22, 0.2, 0.88, 0.9, ALU, 0)
    for (a, b) in ((-0.25, -0.23), (0.18, 0.2)): box(a, b, -0.22, 0.2, 0.9, 1.15, ALU, 0)
    box(-0.25, 0.2, -0.22, 0.2, 1.14, 1.16, ALU, 0)
    box(-0.15, -0.11, -0.223, -0.219, 0.95, 1.12, GLARE, 0); box(0.0, 0.015, -0.223, -0.219, 0.95, 1.12, GLARE, 0)
    for i in range(2): box(-0.2 + i * 0.2, -0.05 + i * 0.2, -0.1, 0.1, 0.9, 0.97, EGG, 0.02)
    # inside the serving window: a copper pan on a stove
    box(-1.5, -0.2, 0.32, 0.6, 0.0, 0.95, STEELS, 0.02)
    box(-1.2, -0.85, 0.36, 0.56, 0.95, 0.99, mat('copper', 'b8683a', 0.3, 0.7), 0.01, 1)
    box(-0.85, -0.55, 0.45, 0.47, 0.97, 0.99, mat('handle', '3a2a22'), 0)
    cyl(-1.02, 0.46, 1.0, 0.06, 0.02, EGG, verts=10)
    noren(0.88, 1.78, GT - 0.03, 1.5, mat('noren_red', 'b8322e', 0.85, tex=t_cloth('b8322e', 73), scale=0.6), 2, ('玉', '子'), WHITE, y=-0.05)
    # the red paper lantern on the pier between window and door
    LAN = mat('lantern', 'd8402e', 0.6, tex=t_ribs('d8402e', 10), scale=0.45)
    cyl(0.55, -0.15, 1.92, 0.006, 0.12, DARK, verts=4)
    blob(0.55, -0.15, 1.52, 0.15, 0.14, 0.26, LAN, 16, 12)
    for z in (1.79, 1.25): cyl(0.55, -0.15, z, 0.075, 0.05, INK, verts=14, bev=0.01)
    text('玉', (0.55, -0.292, 1.52), 0.12, 0.15, INK, 0.008)
    return finish('shop_4', SHOP_LIM)

def shop_tea():
    PL = mat('plaster_white', 'f1ebdf', 0.85, tex=t_plaster('f1ebdf', 81), scale=2)
    YS = mat('charred_wood', '3f332c', 0.8, tex=t_wood('3f332c', 6, 82, vertical=True), scale=1.2)
    shell(coping=None); interior(mat('interior_tatami', 'e8d29a', 0.8, emit=0.45))
    CED = mat('cedar', 'c9a273', 0.6, tex=t_wood('c9a273', 2, 83), scale=2)
    sign_band(CED, mat('sign_dark_frame', '2c241f', 0.6), mat('ink_brown', '7a2618'), '', 1)
    cyl(0, -0.205, (S0 + S1) / 2, 0.22, 0.02, mat('tea_green', '3c6b3a', 0.5), 'Y', 24)
    text('茶', (0, -0.215, (S0 + S1) / 2), 0.3, 0.3, mat('ink_cream', 'f6e7c4'), 0.014)
    for x, s in ((-1.05, '宇治'), (1.05, '抹茶')): text(s, (x, -0.2, (S0 + S1) / 2), 0.9, 0.28, mat('ink_dark', '2c241f', 0.5), 0.02)
    # upper storey: charred boards below, white plaster above, a koshi lattice over the window
    for a, b, z0, z1 in ((-1.885, 1.885, UP0, WZ0), (-1.885, -0.9, WZ0, WZ1), (0.9, 1.885, WZ0, WZ1)):
        box(a, b, 0.0, 0.2, z0, z1, YS, 0)
    box(-1.885, 1.885, 0.0, 0.2, WZ1, TOP, PL, 0)
    box(-1.885, 1.885, -0.04, 0.02, WZ1, WZ1 + 0.06, TRIM, 0.01, 1)                        # a timber beam across
    window(-0.9, 0.9, frame=mat('frame_dark', '3b3330'), dress='none', glass_y=0.15)
    box(-0.9, 0.9, 0.05, 0.12, WZ0, WZ1, mat('shoji', 'f6eedc', 0.8, emit=0.3), 0)          # shoji behind the lattice
    LAT = mat('lattice', '6b4a32', 0.6)
    for i in range(22): x = -0.86 + i * 0.08; box(x, x + 0.03, -0.04, 0.0, WZ0, WZ1, LAT, 0)
    for z in (WZ0, WZ1 - 0.03): box(-0.92, 0.92, -0.05, 0.0, z, z + 0.03, LAT, 0.005, 1)
    potted(1.45, -0.04, WZ0 - 0.02, 0.9)
    box(1.25, 1.65, -0.12, 0.02, WZ0 - 0.06, WZ0 - 0.02, SILL, 0.01, 1)
    # a small tiled roof along the top: kawara rows with round end tiles
    KW = mat('kawara', '5d6772', 0.4, 0.2)
    sl = math.atan2(0.2, 0.62); L = math.hypot(0.62, 0.2)
    O = Vector((-1.96, -0.62, 3.31)); V = Vector((0, 0.62, 0.2)).normalized(); Nn = Vector((0, -0.2, 0.62)).normalized()
    box(-2.0, 2.0, -0.6, 0.3, 3.32, 3.37, mat('eave_board', '3a2e29', 0.7), 0.01, 1)
    box(-2.0, 2.0, 0.0, 0.3, TOP - 0.02, 3.56, mat('eave_board', '3a2e29'), 0)
    ribbed(O, (1, 0, 0), V, Nn, 3.92, L + 0.05, 0.196, 0.06, KW, 'round')
    for i in range(20): cyl(-1.862 + i * 0.196, -0.635, 3.39, 0.055, 0.05, KW, 'Y', 8)
    box(-2.0, 2.0, 0.02, 0.3, 3.53, 3.6, KW, 0.02)
    # ground floor: koshi lattice front lit from behind, an open door with a white noren, a red bench, a stone step
    box(-1.86, 0.62, 0.12, 0.15, 0.05, GT, mat('shoji', 'f6eedc'), 0)
    for i in range(36): x = -1.84 + i * 0.068; box(x, x + 0.034, -0.06, 0.0, 0.12, GT - 0.06, LAT, 0)
    for z in (0.05, 0.92, GT - 0.08): box(-1.86, 0.62, -0.08, 0.04, z, z + 0.07, LAT, 0.01, 1)
    box(0.62, 0.72, -0.08, 0.2, 0.05, GT, TRIM, 0.015)
    noren(0.74, 1.8, GT - 0.03, 1.45, mat('noren_white', 'f1ece0'), 2, ('お', '茶'), mat('tea_green', '3c6b3a'), y=-0.05)
    box(0.8, 1.75, -0.28, 0.0, 0.0, 0.12, STONE, 0.03)
    BEN = mat('bench_red', 'b8322e', 0.85, tex=t_cloth('b8322e', 84), scale=0.5)
    box(-1.65, -0.35, -0.29, -0.09, 0.4, 0.45, BEN, 0.02)
    box(-1.62, -0.38, -0.27, -0.11, 0.35, 0.4, LAT, 0.01, 1)
    for x in (-1.58, -0.42):
        for y in (-0.25, -0.13): box(x - 0.025, x + 0.025, y - 0.02, y + 0.02, 0.0, 0.36, LAT, 0.005, 1)
    cyl(-1.1, -0.19, 0.5, 0.06, 0.08, mat('teacup', '6d8a5a', 0.3), verts=12, r2=0.045, bev=0.01)
    cyl(-0.8, -0.19, 0.48, 0.07, 0.03, mat('tray', '5a2a22', 0.4), verts=12)
    potted(0.71, -0.17, 0.0, 1.3)
    return finish('shop_5', SHOP_LIM)

# ================================================================ market hall walls and loading bays
HW = 2.5; HH = 4.6
HALL = mat('hall_metal', 'a3b5bb', 0.5, 0.25, tex=t_metal('93a6ae', 91), scale=2.5)
HSTEEL = mat('hall_steel', '4d6a73', 0.45, 0.4)
KICK = mat('kick_yellow', 'e9b92f', 0.6, tex=t_concrete('e9b92f', 92), scale=1.2)
def hall_base():
    LIM = ((-HW, HW), HH, 0.3, 0.3)
    box(-HW, HW, 0.008, 0.15, 0.0, HH, mat('hall_back', '5d6b72', 0.6), 0)
    ribbed((-HW, 0.0, 0.42), (1, 0, 0), (0, 0, 1), (0, -1, 0), 2 * HW, HH - 0.42 - 0.12, 0.25, 0.026, HALL, 'ribs')
    box(-HW, HW, -0.09, 0.05, 0.0, 0.42, KICK, 0.02)
    box(-HW, HW, -0.1, 0.05, 0.4, 0.45, DARK, 0.01, 1)
    box(-HW, HW, -0.16, 0.05, 2.95, 3.08, HSTEEL, 0.012)                               # girt
    box(-HW, HW, -0.24, 0.15, HH - 0.14, HH, mat('gutter', '40484e', 0.45, 0.3), 0.02)
    for s in (-1, 1): box(s * (HW - 0.06), s * HW, -0.07, 0.03, 0.45, HH - 0.14, mat('flashing', 'c3cbcd', 0.45, 0.3), 0.01, 1)
    # an H-section steel column with a striped impact sleeve
    cx = -1.55
    box(cx - 0.15, cx + 0.15, -0.26, -0.22, 0.0, HH - 0.14, HSTEEL, 0.01, 1)
    box(cx - 0.02, cx + 0.02, -0.22, -0.04, 0.0, HH - 0.14, HSTEEL, 0)
    box(cx - 0.15, cx + 0.15, -0.04, 0.0, 0.0, HH - 0.14, HSTEEL, 0.01, 1)
    box(cx - 0.17, cx + 0.17, -0.3, 0.0, 0.0, 1.1, HAZ, 0.02)
    box(cx - 0.2, cx + 0.2, -0.3, 0.02, 0.0, 0.03, STEEL, 0.008, 1)
    box(cx - 0.17, cx + 0.17, -0.27, -0.22, 2.9, 3.13, HSTEEL, 0.01, 1)                 # cleat where the girt meets it
    return LIM

def wall_lamp(x, z):
    box(x - 0.12, x + 0.12, -0.05, 0.0, z - 0.08, z + 0.08, DARK, 0.01, 1)
    blob(x, -0.11, z, 0.1, 0.07, 0.07, BULB, 12, 8)
    for dz in (-0.04, 0.0, 0.04): box(x - 0.11, x + 0.11, -0.185, -0.17, z + dz - 0.006, z + dz + 0.006, DARK, 0)

def notices(x, z):
    for i, (dx, dz, w, h) in enumerate(((0, 0, 0.3, 0.42), (0.36, 0.06, 0.24, 0.32))):
        box(x + dx, x + dx + w, -0.06, -0.045, z + dz, z + dz + h, WHITE, 0.003, 1)
        box(x + dx + 0.04, x + dx + w - 0.04, -0.062, -0.06, z + dz + h - 0.1, z + dz + h - 0.05, mat('red_ink', 'c8342c'), 0)
        for k in range(3): box(x + dx + 0.04, x + dx + w - 0.06 - 0.03 * k, -0.062, -0.06, z + dz + 0.06 + k * 0.07, z + dz + 0.08 + k * 0.07, mat('grey_ink', '6a6a70', 0.6), 0)

def hall_fire():
    lim = hall_base()
    RED = mat('fire_red', 'c8302a', 0.4)
    box(0.25, 1.15, -0.2, 0.0, 0.85, 1.95, RED, 0.025)
    box(0.31, 1.09, -0.215, -0.19, 0.91, 1.89, mat('fire_red_d', 'b0261f', 0.45), 0.012, 1)
    text('消火栓', (0.7, -0.215, 1.55), 0.6, 0.2, WHITE, 0.01)
    box(0.95, 1.0, -0.24, -0.215, 1.25, 1.45, STEEL, 0.008, 1)
    cyl(0.7, -0.21, 1.15, 0.12, 0.012, WHITE, 'Y', 16)
    cyl(0.7, -0.08, 2.16, 0.08, 0.06, DARK, 'Y', 14)
    blob(0.7, -0.14, 2.16, 0.07, 0.05, 0.07, mat('red_lamp', 'ff4a3a', 0.3, emit=4.0), 12, 8)
    cyl(1.0, -0.08, 3.35, 0.045, 2.22, RED, verts=10)                                    # standpipe up to the roof
    for z in (2.2, 3.4, 4.2): cyl(1.0, -0.08, z, 0.058, 0.04, STEEL, verts=10)
    cyl(1.65, -0.14, 0.27, 0.085, 0.5, RED, verts=14, bev=0.02)                        # extinguisher on the floor
    cyl(1.65, -0.14, 0.56, 0.03, 0.08, DARK, verts=8)
    wire([(1.65, -0.14, 0.58), (1.72, -0.2, 0.5), (1.72, -0.22, 0.3)], INK, 0.012, 4)
    notices(-0.9, 1.3); wall_lamp(0.0, 3.6)
    return finish('hall_0', lim)

def hall_power():
    lim = hall_base()
    GR = mat('panel_grey', 'c3c6bd', 0.5, 0.15)
    box(-0.1, 1.2, -0.22, 0.0, 0.9, 2.35, GR, 0.025)
    for (a, b) in ((-0.05, 0.53), (0.57, 1.15)):
        box(a, b, -0.235, -0.215, 0.96, 2.29, GR, 0.012, 1)
        box(b - 0.08 if a < 0 else a + 0.05, (b - 0.05) if a < 0 else a + 0.08, -0.26, -0.23, 1.5, 1.72, DARK, 0.008, 1)
    cyl(0.25, -0.235, 2.05, 0.1, 0.012, mat('warn_yellow', 'f2c230', 0.5), 'Y', 3)
    text('高圧', (0.85, -0.235, 2.08), 0.4, 0.14, mat('red_ink', 'c8342c'), 0.008)
    CON = mat('conduit_grey', '9ea3a3', 0.5, 0.3)
    for i, x in enumerate((0.05, 0.25, 0.45)):
        cyl(x, -0.08, 2.35 + (HH - 0.14 - 2.35) / 2, 0.03, HH - 0.14 - 2.35, CON, verts=10)
        for z in (2.7, 3.6, 4.2): box(x - 0.045, x + 0.045, -0.12, -0.0, z, z + 0.03, STEEL, 0)
    wire([(0.8, -0.08, 2.35), (0.8, -0.08, 2.75), (1.0, -0.08, 2.86), (2.5, -0.08, 2.86)], CON, 0.03, 8)
    box(1.6, 1.9, -0.13, 0.0, 1.2, 1.55, GR, 0.015)
    cyl(1.75, -0.065, 2.2, 0.025, 1.3, CON, verts=8)
    box(1.7, 1.8, -0.15, -0.13, 1.33, 1.43, DARK, 0.005, 1)
    wall_lamp(-0.6, 3.6); notices(-1.1, 1.25)
    for k in range(3): box(1.95 + k * 0.0, 2.35, -0.28 + 0.0, -0.02, 0.45 + k * 0.28, 0.7 + k * 0.28, mat('crate_blue', '2f6d93', 0.5), 0.02)
    return finish('hall_1', lim)

def hall_bay_sign():
    lim = hall_base()
    box(-0.6, 1.9, -0.12, 0.0, 3.2, 4.3, WHITE, 0.025)
    box(-0.6, -0.05, -0.13, -0.11, 3.24, 4.26, mat('bay_blue', '2a58a8', 0.45), 0.01, 1)
    text('12', (0.95, -0.12, 3.75), 1.4, 0.88, mat('bay_blue', '2a58a8'), 0.03)
    text('番', (-0.33, -0.13, 3.75), 0.36, 0.4, WHITE, 0.012)
    for x in (-0.5, 1.8): cyl(x, -0.125, 4.2, 0.02, 0.01, STEEL, 'Y', 8)
    # a pallet leaning on the wall and a stack of fish crates
    PAL = mat('pallet', 'b48a58', 0.75)
    for i in range(5): box(-1.0 + i * 0.27, -0.85 + i * 0.27, -0.24, -0.16, 0.05, 1.25, PAL, 0.01, 1)
    for z in (0.2, 1.05): box(-1.05, 0.3, -0.16, -0.08, z, z + 0.1, PAL, 0.01, 1)
    STY = mat('styrofoam', 'f4f3ee')
    for k in range(4): box(0.7, 1.4, -0.28, 0.0, 0.0 + k * 0.24, 0.23 + k * 0.24, STY if k % 2 == 0 else mat('crate_blue', '2f6d93'), 0.02)
    wall_lamp(-0.1, 2.6)
    return finish('hall_2', lim)

def bay(idx, label, door_bottom, door_col):
    LIM = ((-2, 2), 4.4, 0.3, 0.3)
    FR = mat('bay_frame', '505a62', 0.45, 0.4)
    box(-2.0, 2.0, 0.05, 0.15, 0.0, 4.4, mat('hall_back', '5d6b72'), 0)
    box(-2.0, 2.0, 0.008, 0.05, 3.66, 4.4, mat('hall_back', '5d6b72'), 0)
    ribbed((-2.0, 0.0, 3.8), (1, 0, 0), (0, 0, 1), (0, -1, 0), 4.0, 0.48, 0.25, 0.026, HALL, 'ribs')
    for s in (-1, 1):
        box(s * 1.76, s * 2.0, -0.2, 0.12, 0.0, 3.62, FR, 0.02)
        box(s * 1.75, s * 2.0, -0.23, 0.12, 0.0, 1.4, HAZ, 0.02)
        box(s * 1.55, s * 1.75, -0.28, 0.0, 0.0, 0.2, HAZ, 0.03)                           # wheel guards
        box(s * 1.79, s * 1.85, -0.26, -0.2, 0.3, 1.0, INK, 0.02)                          # rubber bumper
    box(-2.0, 2.0, -0.23, 0.12, 3.5, 3.66, HAZ, 0.02)
    box(-1.76, 1.76, -0.26, 0.05, 3.66, 4.12, mat('drum_box', '8d979c', 0.45, 0.35), 0.035)
    box(-2.0, 2.0, -0.2, 0.15, 4.26, 4.4, mat('gutter', '40484e'), 0.02)
    box(-0.42, 0.42, -0.28, -0.26, 3.72, 4.08, WHITE, 0.02)
    text('搬入口 ' + label, (0.0, -0.28, 3.9), 0.7, 0.24, INK, 0.02)
    cyl(0.0, -0.075, 2.55, 0.36, 0.03, WHITE, 'Y', 24)                                # a big painted number on the door
    text(label, (0.0, -0.09, 2.55), 0.4, 0.46, mat('bay_blue', '2a58a8', 0.45), 0.02)
    # the door: horizontal slats from the floor (or a raised bottom) to the drum
    DOOR = mat('door_' + door_col, door_col, 0.45, 0.35, tex=t_metal(door_col, 93 + idx), scale=1.5)
    if door_bottom > 0.1:
        box(-1.76, 1.76, 1.0, 1.1, 0.0, 3.5, mat('bay_dark', '23262a', 0.8), 0)        # dark inside the warehouse
        box(-1.76, 1.76, 0.1, 1.1, 0.0, 0.03, CONC, 0)
        PAL = mat('pallet', 'b48a58', 0.75)
        box(-1.0, 0.2, 0.3, 0.9, 0.0, 0.14, PAL, 0.01, 1)
        for k in range(3): box(-0.95, 0.15, 0.35, 0.85, 0.14 + k * 0.24, 0.37 + k * 0.24, mat('styrofoam', 'f4f3ee') if k % 2 else mat('crate_blue', '2f6d93'), 0.02)
        box(0.7, 1.4, 0.4, 0.9, 0.0, 0.8, mat('drum_blue', '2f6d93'), 0.03)
    ribbed((-1.76, -0.04, door_bottom + 0.08), (0, 0, 1), (1, 0, 0), (0, -1, 0), 3.5 - door_bottom - 0.08, 3.52, 0.11, 0.028, DOOR, 'trap', solid=0.012, smooth=False)
    box(-1.76, 1.76, -0.11, 0.0, door_bottom, door_bottom + 0.09, mat('door_bar', '5a6268', 0.4, 0.5), 0.02)
    box(-1.76, 1.76, -0.08, 0.0, max(0.0, door_bottom - 0.02), door_bottom + 0.01, INK, 0.005, 1)
    for x in (-1.2, 1.2): box(x - 0.12, x + 0.12, -0.14, -0.11, door_bottom + 0.02, door_bottom + 0.07, DARK, 0.008, 1)
    # a warning plate on the left post
    box(-1.98, -1.78, -0.24, -0.21, 1.6, 2.0, mat('warn_yellow', 'f2c230'), 0.01, 1)
    text('頭上\n注意', (-1.88, -0.24, 1.8), 0.16, 0.32, INK, 0.006)
    return finish(f'bay_{idx}', LIM)

# ================================================================ build, export
for build in (shop_fish, shop_dried, shop_knife, shop_nori, shop_tamago, shop_tea, hall_fire, hall_power, hall_bay_sign):
    build()
bay(0, '3', 0.0, 'a9b7bf')
bay(1, '4', 1.15, '9fb19a')

for o in scn.objects: o.select_set(o in MODULES)
glb = os.path.join(OUT, 'facades.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True, export_image_format='AUTO')
print('triangles total', sum(TRIS.values()), TRIS)
print('wrote', glb)
if not SHOTS: sys.exit(0)

# ================================================================ previews (Cycles, CPU): warm sun, soft sky
world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*srgb('a9c6e8'), 1); bg.inputs['Strength'].default_value = 1.0
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
sun.data.energy = 4.0; sun.data.color = srgb('fff0d8'); sun.data.angle = math.radians(4)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
scn.render.engine = 'CYCLES'; scn.cycles.samples = 40; scn.cycles.device = 'CPU'; scn.cycles.use_denoising = True
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Punchy'
BYNAME = {o.name: o for o in MODULES}
for o in MODULES: o.hide_render = True
TEMP = []
def place(name, x, y, rz=0.0):
    o = BYNAME[name].copy(); scn.collection.objects.link(o); o.location = (x, y, 0); o.rotation_euler = (0, 0, rz); o.hide_render = False; TEMP.append(o); return o
def ground(sx, sy, h='d9c7a1', name='sand', x=0, y=0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, y, 0)); g = C.object; g.scale = (sx, sy, 1)
    g.data.materials.append(mat('pv_' + name, h, 0.9, tex=t_concrete(h, 99), scale=6)); TEMP.append(g); return g
def roofblock(x0, x1, y0, y1, h):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, h / 2)); b = C.object; b.scale = (x1 - x0, y1 - y0, h)
    b.data.materials.append(mat('pv_roof', '6e625c', 0.8)); TEMP.append(b)
def shoot(name, pos, look, lens=40, res=(960, 600), ortho=None):
    cam.location = pos; cam.rotation_euler = (Vector(look) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO' if ortho else 'PERSP'
    if ortho: cam.data.ortho_scale = ortho
    cam.data.lens = lens; scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True)
def clear():
    for o in TEMP: bpy.data.objects.remove(o)
    TEMP.clear()

if 'street' in SHOTS:
    L = ['shop_0', 'shop_1', 'shop_2', 'shop_3', 'shop_4', 'shop_5']; R = ['shop_3', 'shop_5', 'shop_1', 'shop_4', 'shop_0', 'shop_2']
    for i in range(6):
        y = -8 + i * 4
        place(L[i], -5, y, math.pi / 2); place(R[i], 5, y, -math.pi / 2)
    ground(40, 60); roofblock(-16, -5.68, -10, 14, 3.42); roofblock(5.68, 16, -10, 14, 3.42)
    sun.rotation_euler = (math.radians(36), 0, math.radians(55)); bg.inputs['Strength'].default_value = 1.25
    t = Vector((0, 2.5, 1.0)); d = 15
    shoot('prev_street', t + Vector((0, -d * math.cos(math.radians(50)), d * math.sin(math.radians(50)))), t)
    clear()
if 'front' in SHOTS or 'row' in SHOTS:
    for i in range(6): place(f'shop_{i}', -10 + i * 4, 0)
    ground(40, 20, y=-8); roofblock(-12, 12, 0.66, 6, 3.42)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-25))
    if 'front' in SHOTS: shoot('prev_front', (0, -40, 1.9), (0, 0, 1.9), res=(1500, 300), ortho=24.6)
    if 'row' in SHOTS:
        t = Vector((-6, 0, 1.6)); shoot('prev_row_a', t + Vector((0, -12 * math.cos(math.radians(50)), 12 * math.sin(math.radians(50)))), t, 40, (960, 640))
        t = Vector((6, 0, 1.6)); shoot('prev_row_b', t + Vector((0, -12 * math.cos(math.radians(50)), 12 * math.sin(math.radians(50)))), t, 40, (960, 640))
    clear()
if 'hall' in SHOTS:
    for name, x in (('hall_0', -9), ('hall_1', -4), ('hall_2', 1), ('bay_0', 5.5), ('bay_1', 9.5)): place(name, x, 0)
    ground(40, 20, 'a8a49c', 'hallfloor', y=-8); roofblock(-11.5, 11.5, 0.2, 6, 4.6)
    sun.rotation_euler = (math.radians(45), 0, math.radians(-30))
    t = Vector((0, 0, 1.8)); d = 19
    shoot('prev_hall', t + Vector((-2.0, -d * math.cos(math.radians(45)), d * math.sin(math.radians(45)))), t, 36, (1100, 600))
    clear()
