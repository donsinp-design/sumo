# LEVEL KIT: the shared toolbox for every level past the bathhouse (see LEVELS.md). One script per level (lv_<id>.py) builds
# its art AND its floor plan with this, so the game's colliders always sit exactly on the art:
#   blender -b -P tools/blender/lv_<id>.py        -> public/assets/models/lv_<id>.glb + public/js/levels/<id>.js
# The look is "ZZZ / Orbitals": flat matte colour, one hard-edged shadow per surface (the game's cel light does that), a muted
# low-key palette (slate, charcoal, navy-grey, teal, ochre, rust) and a few small warm or neon lights. No outlines, no gloss.
# Coordinates: GAME x right, z towards the camera, y up (GB's g* methods take game coordinates; Blender gets (x, -z, y)).
# Roots in the glb: BASE (everything static, walls cut at waist height so the top-down camera sees in), UPPER (the rest of
# the walls, ceilings, upper storeys: drawn in third person only), and the prototypes the game clones (ITEM_*, MOVER_*).
import bpy, bmesh, math, os, sys, random, json, hashlib
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, '..', '..', 'public')
RNG = random.Random(7)
FONT = next((f for f in ['/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc', '/System/Library/Fonts/Hiragino Sans GB.ttc', '/Library/Fonts/Arial Unicode.ttf',
                         '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'] if os.path.exists(f)), None)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene; ROOT = scn.collection

def T(x, y, z): return Matrix.Translation((x, y, z))
def Rx(d): return Matrix.Rotation(math.radians(d), 4, 'X')
def Ry(d): return Matrix.Rotation(math.radians(d), 4, 'Y')
def Rz(d): return Matrix.Rotation(math.radians(d), 4, 'Z')
def Sc(x, y, z): return Matrix.Diagonal((x, y, z, 1))
I4 = Matrix.Identity(4)
def U(n): return [2 * math.pi * i / n for i in range(n)]
def circle(r, n=16, cx=0.0, cy=0.0): return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in U(n)]

# =====================================================================================================================
# the palette (8 x 8 swatches on a 32 x 32 texture). Muted, low-key, warm accents; the NEON row is drawn unlit (full bright)
# =====================================================================================================================
PAL = [
    # neutrals: ink to paper
    ('ink', '24222b'), ('charcoal', '34333d'), ('slate_dk', '3c4450'), ('slate', '4c5866'), ('slate_lt', '687684'), ('steel', '8a96a0'), ('concrete', '7c7f82'), ('concrete_lt', 'a19f98'),
    ('asphalt', '3e4148'), ('asphalt_lt', '52565e'), ('paint', 'd9d2bc'), ('offwhite', 'e2dac6'), ('paper', 'efe6cf'), ('cream', 'cdbf9f'), ('khaki', 'a89a78'), ('navy', '2c3550'),
    # warm: wood, ochre, rust
    ('wood_dk', '4e3426'), ('wood', '7a5236'), ('wood_lt', 'a87a4e'), ('tan', 'c49a68'), ('ochre', 'c8953e'), ('mustard', 'd4b04a'), ('rust', '9c4a32'), ('brick', '7e3f33'),
    # accents (muted, painted)
    ('red', 'c13f38'), ('red_dk', '842c2b'), ('orange', 'd8743a'), ('yellow', 'e2bb48'), ('green', '4c8458'), ('green_dk', '2c4f3a'), ('teal', '3a6e6c'), ('teal_lt', '6a9e98'),
    ('blue', '3c68a4'), ('blue_lt', '7aa0c8'), ('purple', '5e4680'), ('pink', 'cf7896'), ('skin', 'e2ab86'), ('skin_dk', 'b9805e'), ('gold', 'c9a24a'), ('black', '18171c'),
    # nature and cold
    ('snow', 'eceff2'), ('snow_sh', 'c6d2de'), ('ice', 'a9cbd8'), ('pine', '2c463a'), ('grass', '4a7440'), ('grass_lt', '62904c'), ('dirt', '7e6046'), ('rock', '6a6660'),
    # glass and water (drawn see-through)
    ('glass', '506e84'), ('glass_lt', '8fb0c2'), ('water', '36708e'), ('water_lt', '6fa6c0'), ('fish', 'a6b2ba'), ('fish_red', 'c05a48'), ('tuna', '8e3436'), ('styro', 'e8e6dc'),
    # NEON / screens / lamps (unlit)
    ('neon_pink', 'ff4f9a'), ('neon_cyan', '4fe6ff'), ('neon_yellow', 'ffd84f'), ('neon_green', '6cff8c'), ('neon_red', 'ff4a46'), ('neon_white', 'fff4dc'), ('screen', '7ab6ff'), ('lamp', 'ffc070'),
]
SW = {n: i for i, (n, h) in enumerate(PAL)}
GLASSY = {'glass', 'glass_lt', 'water', 'water_lt'}
NEON = {'neon_pink', 'neon_cyan', 'neon_yellow', 'neon_green', 'neon_red', 'neon_white', 'screen', 'lamp'}
def swuv(n):
    i = SW[n]; return ((i % 8 + 0.5) / 8, 1 - (i // 8 + 0.5) / 8)
def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
_img = bpy.data.images.new('LV_Palette', 32, 32, alpha=False)
_px = [0.0] * (32 * 32 * 4)
for i, (n, h) in enumerate(PAL):
    c = [int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)]
    for yy in range(32 - (i // 8) * 4 - 4, 32 - (i // 8) * 4):
        for xx in range((i % 8) * 4, (i % 8) * 4 + 4):
            j = (yy * 32 + xx) * 4; _px[j:j + 4] = [c[0], c[1], c[2], 1.0]
_img.pixels = _px; _img.pack()

def _master(name, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; Lk = m.node_tree.links.new
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.9; b.inputs['Metallic'].default_value = 0.0
    tx = N.new('ShaderNodeTexImage'); tx.image = _img; tx.interpolation = 'Closest'; tx.extension = 'EXTEND'
    uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = 'PAL'; Lk(uvn.outputs['UV'], tx.inputs['Vector']); Lk(tx.outputs['Color'], b.inputs['Base Color'])
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND'; m.surface_render_method = 'BLENDED'; m.use_backface_culling = False
    return m
M_KIT = _master('M_KIT'); M_GW = _master('M_GLASS_WATER', 0.8); M_NEON = _master('M_NEON')

# =====================================================================================================================
# the module builder: bmesh primitives painted onto palette swatches (GAME coordinates through the g* methods)
# =====================================================================================================================
class MB:
    def __init__(s):
        s.bm = bmesh.new(); s.uv = s.bm.loops.layers.uv.new('PAL')
    def _begin(s): return set(s.bm.faces), set(s.bm.edges)
    def _end(s, before, col, bev=0.0, seg=2, ang=None, smooth=True):
        fb, eb = before; bm = s.bm
        new_e = [e for e in bm.edges if e not in eb]
        nf_ = [f for f in bm.faces if f not in fb]
        if nf_: bmesh.ops.recalc_face_normals(bm, faces=nf_)
        if bev > 0:
            es = new_e if ang is None else [e for e in new_e if e.is_manifold and e.calc_face_angle(0) > math.radians(ang)]
            if es: bmesh.ops.bevel(bm, geom=es, offset=bev, offset_type='OFFSET', segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)
        u = swuv(col); mi = 2 if col in NEON else 1 if col in GLASSY else 0
        for f in bm.faces:
            if f not in fb:
                f.material_index = mi; f.smooth = False
                for l in f.loops: l[s.uv].uv = u
    def box(s, x0, x1, y0, y1, z0, z1, col, bev=0.0, seg=2, M=None):
        b = s._begin(); r = bmesh.ops.create_cube(s.bm, size=1.0)
        Mx = (M or I4) @ T((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) @ Sc(max(abs(x1 - x0), 1e-4), max(abs(y1 - y0), 1e-4), max(abs(z1 - z0), 1e-4))
        bmesh.ops.transform(s.bm, matrix=Mx, verts=r['verts'])
        s._end(b, col, min(bev, abs(x1 - x0) / 2.05, abs(y1 - y0) / 2.05, abs(z1 - z0) / 2.05) if bev else 0, seg)
    def cyl(s, x, y, z, r, h, col, seg=12, r2=None, bev=0.0, bseg=2, M=None, axis='Z'):
        b = s._begin()
        res = bmesh.ops.create_cone(s.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
        A = {'Z': I4, 'X': Ry(90), 'Y': Rx(-90)}[axis]
        bmesh.ops.transform(s.bm, matrix=(M or I4) @ T(x, y, z) @ A, verts=res['verts'])
        s._end(b, col, bev, bseg, ang=30 if bev else None)
    def ico(s, x, y, z, r, col, sub=2, sq=(1, 1, 1), M=None, jit=0.0):
        b = s._begin(); res = bmesh.ops.create_icosphere(s.bm, subdivisions=sub, radius=r)
        for v in res['verts']:
            if jit: v.co *= 1 + RNG.uniform(-jit, jit)
        bmesh.ops.transform(s.bm, matrix=(M or I4) @ T(x, y, z) @ Sc(*sq), verts=res['verts'])
        s._end(b, col)
    def lathe(s, prof, col, seg=12, M=None, bev=0.0, ang=30):
        b = s._begin(); bm = s.bm; rings = []
        for r, z in prof:
            if r <= 1e-6: rings.append([bm.verts.new((0, 0, z))])
            else: rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
        for a, c in zip(rings, rings[1:]):
            for i in range(seg):
                i1 = (i + 1) % seg
                if len(a) == 1: bm.faces.new((a[0], c[i], c[i1]))
                elif len(c) == 1: bm.faces.new((a[i], a[i1], c[0]))
                else: bm.faces.new((a[i], a[i1], c[i1], c[i]))
        if len(rings[0]) > 1: bm.faces.new(list(reversed(rings[0])))
        if len(rings[-1]) > 1: bm.faces.new(rings[-1])
        bmesh.ops.transform(bm, matrix=(M or I4), verts=[v for rg in rings for v in rg]); s._end(b, col, bev, 2, ang=ang if bev else None)
    def prism(s, pts, z0, z1, col, M=None, bev=0.0, bseg=2):
        b = s._begin(); bm = s.bm
        lo = [bm.verts.new((x, y, z0)) for x, y in pts]; hi = [bm.verts.new((x, y, z1)) for x, y in pts]
        bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
        n = len(pts)
        for i in range(n): bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
        bmesh.ops.transform(bm, matrix=(M or I4), verts=lo + hi); s._end(b, col, bev, bseg, ang=30 if bev else None)

class GB(MB):
    """the builder in GAME coordinates: x right, z towards the camera, y up."""
    def gbox(s, x0, x1, z0, z1, y0, y1, col, bev=0.0, seg=2):
        s.box(min(x0, x1), max(x0, x1), -max(z0, z1), -min(z0, z1), min(y0, y1), max(y0, y1), col, bev, seg)
    def gboxr(s, cx, cz, w, d, y0, y1, ry, col, bev=0.0):
        """a box w (along its x) by d, centred on (cx, cz), turned ry degrees (counter-clockwise seen from above, game x towards -z)."""
        s.box(-w / 2, w / 2, -d / 2, d / 2, y0, y1, col, bev, M=T(cx, -cz, 0) @ Rz(ry))
    def gcyl(s, x, z, y, r, h, col, seg=14, r2=None, bev=0.0, axis='Z'):
        """y is the BOTTOM for an upright cylinder; for axis X / Y (lying along game x / game z) it's the centre."""
        if axis == 'Z': s.cyl(x, -z, y + h / 2, r, h, col, seg=seg, r2=r2, bev=bev)
        else: s.cyl(x, -z, y, r, h, col, seg=seg, r2=r2, bev=bev, axis=axis)
    def gico(s, x, z, y, r, col, sub=2, sq=(1, 1, 1), jit=0.0):
        """sq is (x, z, y) in game axes."""
        s.ico(x, -z, y, r, col, sub=sub, sq=(sq[0], sq[1], sq[2]), jit=jit)
    def gprism(s, pts, y0, y1, col, bev=0.0):
        """an upright prism from a floor outline [(x, z), ...] (any winding)."""
        s.prism([(x, -z) for x, z in pts], y0, y1, col, bev=bev)
    def quad(s, x0, x1, z0, z1, y, col):
        b = s._begin(); bm = s.bm
        vs = [bm.verts.new((x0, -z1, y)), bm.verts.new((x1, -z1, y)), bm.verts.new((x1, -z0, y)), bm.verts.new((x0, -z0, y))]
        bm.faces.new(vs); s._end(b, col)
    def vquad(s, pts, col):
        """a flat face from game points [(x, y, z), ...] (decals, signs, screens: put them 5 mm off the surface)."""
        b = s._begin(); bm = s.bm; bm.faces.new([bm.verts.new((x, -z, y)) for x, y, z in pts]); s._end(b, col)
    def sign(s, x, y, z, w, h, col, face='+z', d=0.006):
        """a flat rectangle centred at (x, y, z) facing one way: '+z' / '-z' / '+x' / '-x' / 'up'."""
        a, b2 = w / 2, h / 2
        if face == '+z': P = [(x - a, y - b2, z + d), (x + a, y - b2, z + d), (x + a, y + b2, z + d), (x - a, y + b2, z + d)]
        elif face == '-z': P = [(x + a, y - b2, z - d), (x - a, y - b2, z - d), (x - a, y + b2, z - d), (x + a, y + b2, z - d)]
        elif face == '+x': P = [(x + d, y - b2, z + a), (x + d, y - b2, z - a), (x + d, y + b2, z - a), (x + d, y + b2, z + a)]
        elif face == '-x': P = [(x - d, y - b2, z - a), (x - d, y - b2, z + a), (x - d, y + b2, z + a), (x - d, y + b2, z - a)]
        else: P = [(x - a, y + d, z + b2), (x + a, y + d, z + b2), (x + a, y + d, z - b2), (x - a, y + d, z - b2)]
        s.vquad(P, col)
    def text(s, body, size, col, x, y, z, depth=0.02, face='+z', align='CENTER'):
        """lettering (Japanese welcome) as a thin solid facing +z / -z / +x / -x / up."""
        if not FONT: return
        cu = bpy.data.curves.new('txt', 'FONT'); cu.body = body; cu.size = size; cu.extrude = depth / 2; cu.align_x = align; cu.align_y = 'CENTER'
        try: cu.font = bpy.data.fonts.load(FONT, check_existing=True)
        except Exception: return
        ob = bpy.data.objects.new('txt', cu); ROOT.objects.link(ob)
        dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
        R = {'+z': Rx(90), '-z': Rz(180) @ Rx(90), '+x': Rz(90) @ Rx(90), '-x': Rz(-90) @ Rx(90), 'up': I4}[face]
        Mx = T(x, -z, y) @ R
        b = s._begin(); vm = {}
        for v in me.vertices: vm[v.index] = s.bm.verts.new(Mx @ v.co)
        for p in me.polygons:
            try: s.bm.faces.new([vm[i] for i in p.vertices])
            except ValueError: pass
        s._end(b, col); bpy.data.meshes.remove(me)
    def ramp(s, x0, x1, z0, z1, ax, y0, y1, col, th=0.2):
        """a sloped slab: y0 at the low-coordinate end of axis ax ('x' or 'z'), y1 at the high end."""
        b = s._begin(); bm = s.bm
        def Y(x, z): t = (x - x0) / (x1 - x0) if ax == 'x' else (z - z0) / (z1 - z0); return y0 + (y1 - y0) * t
        cs = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
        top = [bm.verts.new((x, -z, Y(x, z))) for x, z in cs]; bot = [bm.verts.new((x, -z, Y(x, z) - th)) for x, z in cs]
        bm.faces.new(top); bm.faces.new(list(reversed(bot)))
        for i in range(4): bm.faces.new((bot[i], bot[(i + 1) % 4], top[(i + 1) % 4], top[i]))
        s._end(b, col)
    def finish(s, name):
        me = bpy.data.meshes.new(name); s.bm.normal_update(); s.bm.to_mesh(me); s.bm.free()
        for m in (M_KIT, M_GW, M_NEON): me.materials.append(m)
        return me

# =====================================================================================================================
# a level: its floor plan (for the game) and its art (for the glb), built together
# =====================================================================================================================
CUT = 1.15     # walls are cut here in the top-down view (the bathhouse's height): the rest goes in UPPER

class Level:
    def __init__(s, id, name, jp, blurb=''):
        s.id = id
        s.L = dict(id=id, name=name, jp=jp, blurb=blurb, solids=[], blockers=[], rooms=[], floors=[], ramps=[], wet=[], ice=[], pool=None, conveyors=[],
                   carts=[], hides=[], movers=[], traps=[], crowd=[], start=[[0, 0], [2, 0]], maw=[], exit=None, pants=[0, 0], hider=[0, 0], seeker=[2, 0],
                   staffN=5, staffKinds=None, staffZone=None, ceil=0, style={}, ring=None, story=None, ball=None, goals=[])
        s.base = GB(); s.upper = GB(); s.protos = []; s.extra = []
    # ---- the floor plan
    def bounds(s, x0, x1, z0, z1): s.L['bounds'] = dict(x0=x0, x1=x1, z0=z0, z1=z1)
    def room(s, id, name, x0, x1, z0, z1, **kw): s.L['rooms'].append(dict(id=id, name=name, x0=min(x0, x1), x1=max(x0, x1), z0=min(z0, z1), z1=max(z0, z1), **kw))
    def solid(s, k, x0, x1, z0, z1, h, tall=True, draw=True, col='concrete', bev=0.03, **kw):
        """a collider (tall: it blocks sight too). draw: a plain box in col, or a function f(m, x0, x1, z0, z1, h) that builds it into BASE."""
        q = dict(k=k, x0=min(x0, x1), x1=max(x0, x1), z0=min(z0, z1), z1=max(z0, z1), h=h, tall=tall, **kw); s.L['solids'].append(q)
        if callable(draw): draw(s.base, q['x0'], q['x1'], q['z0'], q['z1'], h)
        elif draw: s.base.gbox(q['x0'], q['x1'], q['z0'], q['z1'], 0, h, col, bev=bev)
        return q
    def wall(s, x0, x1, z0, z1, h=3.2, col='concrete', trim='slate_dk', cap=True, base=None):
        """a full-height wall: collider, the lower part (to CUT, with a coping) in BASE, the rest in UPPER."""
        q = s.solid('wall', x0, x1, z0, z1, h, True, draw=False)
        x0, x1, z0, z1 = q['x0'], q['x1'], q['z0'], q['z1']
        s.base.gbox(x0, x1, z0, z1, 0, CUT, col)
        if cap: s.base.gbox(x0 - 0.02, x1 + 0.02, z0 - 0.02, z1 + 0.02, CUT - 0.02, CUT + 0.05, trim)
        if base: s.base.gbox(x0 - 0.012, x1 + 0.012, z0 - 0.012, z1 + 0.012, 0, 0.12, base)
        if h > CUT: s.upper.gbox(x0, x1, z0, z1, CUT + 0.05, h, col)
        return q
    def blocker(s, x, z, r, **kw): s.L['blockers'].append(dict(x=x, z=z, r=r, **kw))
    def floor(s, x0, x1, z0, z1, y): s.L['floors'].append(dict(x0=min(x0, x1), x1=max(x0, x1), z0=min(z0, z1), z1=max(z0, z1), y=y))
    def slope(s, x0, x1, z0, z1, ax, y0, y1): s.L['ramps'].append(dict(x0=min(x0, x1), x1=max(x0, x1), z0=min(z0, z1), z1=max(z0, z1), ax=ax, y0=y0, y1=y1))
    def wet(s, x0, x1, z0, z1): s.L['wet'].append(dict(x0=min(x0, x1), x1=max(x0, x1), z0=min(z0, z1), z1=max(z0, z1)))
    def ice(s, x0, x1, z0, z1): s.L['ice'].append(dict(x0=min(x0, x1), x1=max(x0, x1), z0=min(z0, z1), z1=max(z0, z1)))
    def conveyor(s, x0, x1, z0, z1, vx, vz): s.L['conveyors'].append(dict(x0=min(x0, x1), x1=max(x0, x1), z0=min(z0, z1), z1=max(z0, z1), vx=vx, vz=vz))
    def cart(s, x, z, r=0.0): s.L['carts'].append(dict(x=x, z=z, r=r))
    def hide(s, k, x, z, out, by=1.0, label=None, f=0.0):
        """a fixed hiding place: he stands at (x, z) inside it, steps out to `out`; his booty pokes out at height by (None: not at all)."""
        s.L['hides'].append(dict(k=k, x=x, z=z, out=list(out), by=by, label=label or k, f=f))
    # ---- the art
    def proto(s, name):
        m = GB(); s.protos.append((name, m)); return m
    def obj(s, name, m, parent='BASE'):
        s.extra.append((name, m, parent))
    def export(s):
        L = s.L; assert 'bounds' in L, 'set the bounds'
        coll = bpy.data.collections.new('LV'); ROOT.children.link(coll)
        def mk(name, m, parent=None):
            me = m.finish('ME_' + name); ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
            if parent: ob.parent = parent
            return ob
        roots = {}
        for r in ('BASE', 'UPPER', 'PROTO'):
            e = bpy.data.objects.new(r, None); coll.objects.link(e); roots[r] = e
        mk('BASE_MAIN', s.base, roots['BASE']); mk('UPPER_MAIN', s.upper, roots['UPPER'])
        for name, m, parent in s.extra: mk(name, m, roots.get(parent, roots['BASE']))
        for name, m in s.protos: mk(name, m, roots['PROTO'])
        glb = os.path.join(PUB, 'assets', 'models', 'lv_%s.glb' % s.id)
        bpy.ops.object.select_all(action='DESELECT')
        for o in coll.objects: o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                                  export_cameras=False, export_lights=False, export_materials='EXPORT', export_image_format='AUTO')
        L['v'] = hashlib.md5(open(glb, 'rb').read()).hexdigest()[:10]
        os.makedirs(os.path.join(PUB, 'js', 'levels'), exist_ok=True)
        js = os.path.join(PUB, 'js', 'levels', '%s.js' % s.id)
        with open(js, 'w') as fh:
            fh.write("'use strict';\n// generated by tools/blender/lv_%s.py (the level's floor plan, made with its art: don't edit by hand)\nS.Levels = S.Levels || {};\nS.Levels.%s = %s;\n" % (s.id, s.id, json.dumps(L, separators=(',', ':'))))
        print('LEVEL', s.id, 'solids', len(L['solids']), 'glb', os.path.getsize(glb) // 1024, 'KB ->', glb, js)
