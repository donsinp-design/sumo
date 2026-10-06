# "CLOCK" stage, fully modelled: two sumos fight on the face of a giant clock lying on its back on a dark surface.
# Built entirely by script (Blender 4.2, run headless).
#   python tools/blender/stage_clock.py [out_dir] [chars_dir] [samples=32] [pct=100] [noren] [nochars]
# Writes <out_dir>/clock.glb (the clock only: Z up, metres, origin at the dial centre, dial surface at Z=0, 12 o'clock
# towards +Y, i.e. away from the game camera) and renders <out_dir>/ex_game.png from the game camera ('wide' of
# stage_render.py) with the game's characters (sumo2_stance.glb, sumo2_red.glb, gyoji.glb from chars_dir) in masks.
# The dial: cream enamel (one painted 1024 colour texture + clear coat), printed serif numerals, a railroad minute track
# whose inner line is the fighting circle (RING_R); blued-steel hour/minute hands, a red second hand and a brass boss,
# all lying flat (<= 3 cm); a polished, bevelled brass bezel and case. The dark surface it lies on is render-only.
import bpy, bmesh, math, sys, os, re
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-sumo/f8028735-3c86-5a27-b070-5e521ee72586/scratchpad'
ARGS = [a for a in sys.argv[sys.argv.index('--') + 1 if '--' in sys.argv else 1:]
        if '=' not in a and a not in ('noren', 'nochars') and not a.endswith('.py')]
OUT = ARGS[0] if ARGS else os.path.join(SP, 'clock')
CHARS = ARGS[1] if len(ARGS) > 1 else os.path.join(SP, 'stage')
os.makedirs(OUT, exist_ok=True)
OPT = dict(a.split('=', 1) for a in sys.argv if '=' in a and not a.startswith('-'))
SAMPLES = int(OPT.get('samples', 32)); PCT = int(OPT.get('pct', 100))
NOREN = 'noren' in sys.argv; NOCHARS = 'nochars' in sys.argv

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
TAU = 2 * math.pi


def ring_r():
    try:
        txt = open(os.path.join(HERE, '..', '..', 'public', 'js', 'config.js')).read()
        return float(re.search(r'S\.RING_R\s*=\s*([\d.]+)', txt).group(1))
    except Exception:
        return 4.6


R = ring_r()           # fighting circle = inner line of the minute track
RD = R + 0.7           # dial radius (bezel starts here)
FLOOR = -1.2           # the surface the clock lies on


# ================================================================ helpers
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


STAGE = []
def obj(name, me, mats=(), stage=True, loc=None, rot=None):
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    for m in mats: me.materials.append(m)
    if loc is not None: o.location = loc
    if rot is not None: o.rotation_euler = rot
    if stage: STAGE.append(o)
    return o
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == 'MESH' else 0


def planar_uv(me, S, cx=0.0, cy=0.0):
    uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for l in me.loops:
        co = me.vertices[l.vertex_index].co; uv.data[l.index].uv = ((co.x - cx) / (2 * S) + 0.5, (co.y - cy) / (2 * S) + 0.5)


def lathe(name, prof, mats, segs=128, mi=None, uvS=None, smooth=40, stage=True):
    """Profile [(r, z)] traversed top-inside -> outside -> down (normals face out); r == 0 is a pole."""
    bm = bmesh.new(); rings = []
    for (r, z) in prof:
        if r < 1e-6: rings.append([bm.verts.new((0, 0, z))]); continue
        rings.append([bm.verts.new((r * math.cos(TAU * i / segs), r * math.sin(TAU * i / segs), z)) for i in range(segs)])
    for k, (A, B) in enumerate(zip(rings[:-1], rings[1:])):
        for i in range(segs):
            j = (i + 1) % segs
            if len(A) == 1: f = bm.faces.new((A[0], B[i], B[j]))
            elif len(B) == 1: f = bm.faces.new((A[i], B[0], A[j]))
            else: f = bm.faces.new((A[i], B[i], B[j], A[j]))
            if mi: f.material_index = mi[k]
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth: me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(smooth))
    planar_uv(me, uvS or max(r for r, _ in prof))
    return obj(name, me, mats, stage=stage)


def flat_poly(name, outline, z0, z1, mat, bev=0.0, loc=(0, 0, 0), rot_z=0.0, stage=True):
    """Extrude a 2D outline [(x, y)] (CCW) from z0 to z1; optional chamfer round the top edge."""
    bm = bmesh.new()
    B = [bm.verts.new((x, y, z0)) for x, y in outline]; T = [bm.verts.new((x, y, z1)) for x, y in outline]
    bm.faces.new(T); bm.faces.new(B[::-1])
    for i in range(len(B)):
        j = (i + 1) % len(B); bm.faces.new((B[i], B[j], T[j], T[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = obj(name, me, [mat], stage=stage, loc=loc, rot=(0, 0, rot_z))
    if bev > 0:
        b = o.modifiers.new('bev', 'BEVEL'); b.width = bev; b.segments = 2; b.limit_method = 'ANGLE'
        b.angle_limit = math.radians(30)
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg); o.modifiers.clear(); o.data = me2
    o.data.shade_smooth(); o.data.set_sharp_from_angle(angle=math.radians(35))
    planar_uv(o.data, 1.0)
    return o


def text_mesh(name, body, size, mat, loc, font=None, stage=True, spacing=1.0):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.extrude = 0.0
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = 4; cu.space_character = spacing
    if font: cu.font = font
    tmp = bpy.data.objects.new(name + '_t', cu); scn.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg); bpy.data.objects.remove(tmp)
    me.materials.clear()
    # optical centring: put the bounding-box centre on loc
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for v in me.vertices: v.co.x -= cx; v.co.y -= cy; v.co.z = 0
    planar_uv(me, 1.0)
    return obj(name, me, [mat], stage=stage, loc=loc)


def image(name, arr, data=False):
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2: arr = np.repeat(arr[..., None], 3, 2)
    h, w = arr.shape[:2]; rgba = np.ones((h, w, 4), np.float32); rgba[..., :3] = np.clip(arr[..., :3], 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=False)
    if data: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.file_format = 'PNG'; im.pack(); return im


BSDF = {}
def mat(name, col=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, tcol=None, emit=None, estr=0.0, coat=0.0, coat_r=0.05, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']; BSDF[name] = bs
    bs.inputs['Base Color'].default_value = (*col, 1); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal; bs.inputs['Specular IOR Level'].default_value = spec
    if coat: bs.inputs['Coat Weight'].default_value = coat; bs.inputs['Coat Roughness'].default_value = coat_r
    if tcol:
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = tcol; nt.links.new(n.outputs['Color'], bs.inputs['Base Color'])
    if emit: bs.inputs['Emission Color'].default_value = (*emit, 1); bs.inputs['Emission Strength'].default_value = estr
    return m


# ================================================================ dial texture: cream enamel
N = 1024
rng = np.random.default_rng(7)
def blur_noise(n, k):
    a = rng.standard_normal((n, n)).astype(np.float32)
    f = np.fft.fftfreq(n); fx, fy = np.meshgrid(f, f)
    a = np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-(fx ** 2 + fy ** 2) * (k ** 2))))
    return a / (a.std() + 1e-6)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
u = (xx + 0.5) / N * 2 - 1; v = (yy + 0.5) / N * 2 - 1      # image row 0 = v -1 (Blender images are bottom-up)
rr = np.sqrt(u * u + v * v)
base = np.array(lin('f2ecdc'), np.float32)
cloud = blur_noise(N, 60) * 0.5 + blur_noise(N, 14) * 0.25
dial = base[None, None, :] * (1 + 0.018 * cloud[..., None])
dial *= (1 - 0.05 * np.clip((rr - 0.80) / 0.2, 0, 1) ** 2)[..., None]                 # faint ageing at the rim
dial[..., 2] *= (1 - 0.03 * np.clip(rr - 0.5, 0, 1))                                  # slightly warmer to the edge
speck = rng.random((N, N)) > 0.9993
dial[speck] *= 0.82
TDIAL = image('DialEnamel', dial)

# ================================================================ materials
ENAMEL = mat('Enamel', lin('f2ecdc'), 0.32, tcol=TDIAL, coat=1.0, coat_r=0.035)
INK = mat('Ink', (0.012, 0.012, 0.014), 0.42)
INKRED = mat('InkRed', lin('9e1b16'), 0.42)
BRASS = mat('Brass', (0.80, 0.55, 0.22), 0.16, metal=1.0)
BRASS_SAT = mat('BrassSatin', (0.78, 0.53, 0.21), 0.3, metal=1.0)
BLUED = mat('BluedSteel', (0.05, 0.09, 0.26), 0.2, metal=1.0, coat=0.6, coat_r=0.06)
REDHAND = mat('RedLacquer', lin('b3201a'), 0.3, coat=1.0, coat_r=0.05)

# ================================================================ dial
dial_o = lathe('Dial', [(0, 0), (1.5, 0), (3.0, 0), (4.2, 0), (RD + 0.02, 0)], [ENAMEL], segs=128, uvS=RD + 0.02)
if dial_o.data.polygons[0].normal.z < 0:
    dial_o.data.flip_normals()

# printed minute track (railroad): inner line = fighting circle
ZI = 0.0015
def annulus(bm, r0, r1, segs=192):
    a0 = [bm.verts.new((r0 * math.cos(TAU * i / segs), r0 * math.sin(TAU * i / segs), 0)) for i in range(segs)]
    a1 = [bm.verts.new((r1 * math.cos(TAU * i / segs), r1 * math.sin(TAU * i / segs), 0)) for i in range(segs)]
    for i in range(segs):
        j = (i + 1) % segs; bm.faces.new((a0[i], a1[i], a1[j], a0[j]))
def bar(bm, ang, r0, r1, w):
    s, c = math.sin(ang), math.cos(ang); px, py = c, -s       # radial dir (s, c); perpendicular (c, -s)
    pts = [(s * r0 - px * w / 2, c * r0 - py * w / 2), (s * r0 + px * w / 2, c * r0 + py * w / 2),
           (s * r1 + px * w / 2, c * r1 + py * w / 2), (s * r1 - px * w / 2, c * r1 - py * w / 2)]
    vs = [bm.verts.new((x, y, 0)) for x, y in pts]; f = bm.faces.new(vs)
    if f.normal.z < 0: f.normal_flip()
bm = bmesh.new()
RO = R + 0.42                                   # outer line of the minute track
annulus(bm, R - 0.03, R + 0.03, 256)            # the fighting circle: the boldest printed line on the dial
annulus(bm, RO - 0.012, RO + 0.012, 256)
annulus(bm, R - 0.13, R - 0.115, 256)           # a hair line just inside (classic double line)
for k in range(60):
    a = TAU * k / 60
    if k % 5 == 0: bar(bm, a, R + 0.03, RO + 0.012, 0.11)
    else: bar(bm, a, R + 0.03, RO - 0.012, 0.03)
for f in bm.faces:
    if f.normal.z < 0: f.normal_flip()
me = bpy.data.meshes.new('MinuteTrack'); bm.to_mesh(me); bm.free(); planar_uv(me, RD)
obj('MinuteTrack', me, [INK], loc=(0, 0, ZI))

# small five-minute figures outside the track
FONT = None
for fp in ('/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'):
    if os.path.exists(fp): FONT = bpy.data.fonts.load(fp); break
for k in range(1, 13):
    a = TAU * k / 12; rn = R - 0.78
    text_mesh('Num%d' % k, str(k), 0.98, INK, (rn * math.sin(a), rn * math.cos(a), ZI), font=FONT)
for k in range(12):
    a = TAU * k / 12; rf = RO + 0.17
    o = text_mesh('Min%d' % k, '%02d' % (k * 5) if k else '60', 0.17, INK, (rf * math.sin(a), rf * math.cos(a), ZI), font=FONT)
    o.rotation_euler = (0, 0, -a)
text_mesh('Brand', 'SUMO', 0.42, INK, (0, -2.15, ZI), font=FONT, spacing=1.25)
text_mesh('Brand2', 'TOKYO', 0.17, INK, (0, -2.52, ZI), font=FONT, spacing=1.5)
text_mesh('Quartz', 'QUARTZ', 0.17, INKRED, (0, -2.98, ZI), font=FONT, spacing=1.5)


# ================================================================ hands (lying flat, <= 3 cm)
def mirror(prof):
    right = [(hw, y) for y, hw in prof]
    left = [(-hw, y) for y, hw in reversed(prof) if hw > 1e-6]
    return right + left if right[0][0] > 1e-6 else right + left
def hand_outline(prof):
    pts = mirror(prof); out = []
    for p in pts:
        if not out or (abs(out[-1][0] - p[0]) > 1e-6 or abs(out[-1][1] - p[1]) > 1e-6): out.append(p)
    # CCW
    area = sum(out[i][0] * out[(i + 1) % len(out)][1] - out[(i + 1) % len(out)][0] * out[i][1] for i in range(len(out)))
    return out if area > 0 else out[::-1]

H, M, S = 10, 9, 36                       # 10:09:36, the classic display time
ang_h = TAU * ((H % 12) + M / 60) / 12; ang_m = TAU * (M + S / 60) / 60; ang_s = TAU * S / 60
# hour hand: short tail, slim shaft, spade, sharp tip
hp = [(-0.55, 0.0), (-0.54, 0.07), (-0.2, 0.1), (0.0, 0.14), (0.35, 0.1), (1.75, 0.065)] + \
     [(1.75 + 0.75 * t, 0.065 + 0.16 * math.sin(math.pi * t * 0.85)) for t in (0.15, 0.3, 0.45, 0.6, 0.75)] + \
     [(2.55, 0.12), (2.75, 0.06), (2.95, 0.0)]
flat_poly('HourHand', hand_outline(hp), 0.004, 0.011, BLUED, bev=0.006, rot_z=-ang_h)
# minute hand: long lance
mp = [(-0.75, 0.0), (-0.74, 0.06), (-0.3, 0.085), (0.0, 0.12), (0.4, 0.085), (3.3, 0.06), (3.9, 0.075), (4.25, 0.03), (4.42, 0.0)]
flat_poly('MinuteHand', hand_outline(mp), 0.012, 0.019, BLUED, bev=0.006, rot_z=-ang_m)
# second hand: red needle + counterweight ring
sp = [(-1.35, 0.0), (-1.34, 0.03), (0.0, 0.035), (4.0, 0.02), (4.78, 0.0)]
flat_poly('SecondHand', hand_outline(sp), 0.02, 0.024, REDHAND, rot_z=-ang_s)
cw = lathe('SecondWeight', [(0.0, 0.026), (0.13, 0.026), (0.15, 0.022), (0.15, 0.019)], [REDHAND], segs=48, uvS=1.0)
cw.location = (-1.05 * math.sin(ang_s), -1.05 * math.cos(ang_s), 0)
lathe('Boss', [(0, 0.03), (0.06, 0.0298), (0.11, 0.028), (0.15, 0.026), (0.2, 0.024), (0.23, 0.02), (0.24, 0.016),
               (0.24, 0.0)], [BRASS], segs=64, uvS=1.0)

# ================================================================ bezel & case (polished bevelled brass, no glass)
bez = [(RD - 0.005, -0.03), (RD - 0.005, 0.05), (RD + 0.02, 0.075), (RD + 0.09, 0.09),        # inner lip / flange
       (RD + 0.11, 0.16), (RD + 0.14, 0.19),                                                   # step up to the bevel
       (RD + 0.22, 0.27), (RD + 0.33, 0.36),                                                   # the flat inner bevel
       (RD + 0.40, 0.405), (RD + 0.47, 0.43), (RD + 0.55, 0.435), (RD + 0.63, 0.42),          # rounded crown
       (RD + 0.71, 0.38), (RD + 0.78, 0.31), (RD + 0.84, 0.21), (RD + 0.88, 0.09),            # outer shoulder
       (RD + 0.89, 0.0), (RD + 0.87, -0.06), (RD + 0.84, -0.09),                               # a small groove
       (RD + 0.86, -0.13), (RD + 0.9, -0.2), (RD + 0.92, FLOOR + 0.12), (RD + 0.9, FLOOR + 0.04),
       (RD + 0.86, FLOOR + 0.005), (RD + 0.5, FLOOR + 0.005)]
mi = [1] * 6 + [0] * (len(bez) - 7)
mi[16:] = [1] * (len(bez) - 1 - 16)                     # satin on the lip and the case side, polish on the bevel
lathe('Bezel', bez, [BRASS, BRASS_SAT], segs=192, mi=mi, smooth=28, uvS=RD + 1.0)

# ================================================================ export the stage
total = sum(tris(o) for o in STAGE)
print('TOTAL triangles:', total, ' objects:', len(STAGE))
print('heaviest', sorted(((tris(o), o.name) for o in STAGE), reverse=True)[:8])
bpy.ops.object.select_all(action='DESELECT')
for o in STAGE: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'clock.glb'), export_format='GLB', use_selection=True,
                          export_apply=True, export_image_format='JPEG', export_jpeg_quality=92)
print('exported', os.path.join(OUT, 'clock.glb'), os.path.getsize(os.path.join(OUT, 'clock.glb')) // 1024, 'KB')
if NOREN: sys.exit(0)


# ================================================================ render-only: surface, anisotropy, lights
def aniso(mname, amount, rot=0.0):
    bs = BSDF[mname]; nt = bs.id_data
    t = nt.nodes.new('ShaderNodeTangent'); t.direction_type = 'RADIAL'; t.axis = 'Z'
    nt.links.new(t.outputs['Tangent'], bs.inputs['Tangent'])
    bs.inputs['Anisotropic'].default_value = amount; bs.inputs['Anisotropic Rotation'].default_value = rot
aniso('Brass', 0.35, 0.25); aniso('BrassSatin', 0.7, 0.25)

# the dark soft surface: charcoal felt (procedural, render-only)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40)
me = bpy.data.meshes.new('Surface'); bm.to_mesh(me); bm.free()
fm = mat('Felt', (0.02, 0.019, 0.018), 0.85, spec=0.3)
nt = fm.node_tree; bs = BSDF['Felt']
nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.35; nz.inputs['Detail'].default_value = 4
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.013; mr.inputs['To Max'].default_value = 0.026
nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
cr = nt.nodes.new('ShaderNodeCombineColor')
for ch, k in (('Red', 1.0), ('Green', 0.95), ('Blue', 0.9)):
    mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = k
    nt.links.new(mr.outputs['Result'], mm.inputs[0]); nt.links.new(mm.outputs[0], cr.inputs[ch])
nt.links.new(cr.outputs['Color'], bs.inputs['Base Color'])
fz = nt.nodes.new('ShaderNodeTexNoise'); fz.inputs['Scale'].default_value = 90; fz.inputs['Detail'].default_value = 2
bmp = nt.nodes.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.25
nt.links.new(fz.outputs['Fac'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], bs.inputs['Normal'])
bs.inputs['Sheen Weight'].default_value = 0.5; bs.inputs['Sheen Tint'].default_value = (0.5, 0.5, 0.55, 1)
obj('Surface', me, [fm], stage=False, loc=(0, 4, FLOOR))

world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.004, 0.0042, 0.005, 1)


def light(name, kind, loc, look, energy, color, size=None, spot=None, blend=0.5, soft=0.5, glossy=True):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); scn.collection.objects.link(L)
    L.location = loc; L.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    L.data.energy = energy; L.data.color = color
    if kind == 'AREA': L.data.shape = 'RECTANGLE'; L.data.size, L.data.size_y = size
    if kind == 'SPOT': L.data.spot_size = math.radians(spot); L.data.spot_blend = blend
    if kind in ('SPOT', 'POINT'): L.data.shadow_soft_size = soft
    L.visible_glossy = glossy
    return L


def panel(name, loc, look, size, strength, color):
    """An emissive card only reflections see (softboxes for the brass and the enamel's coat)."""
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    o.location = loc; o.scale = (size[0], size[1], 1)
    o.rotation_euler = (Vector(loc) - Vector(look)).to_track_quat('Z', 'Y').to_euler()
    m = mat(name, (0, 0, 0), 1.0, emit=color, estr=strength, spec=0.0); me.materials.append(m)
    o.visible_camera = o.visible_diffuse = o.visible_shadow = o.visible_transmission = o.visible_volume_scatter = False
    return o


light('Key', 'SPOT', (-4.0, -3.5, 18), (0, 0.6, 0), 15000, (1.0, 0.9, 0.78), spot=62, blend=0.85, soft=3.0)
light('Fill', 'AREA', (6, -16, 9), (0, 0, 0), 900, (0.75, 0.82, 1.0), size=(10, 5), glossy=False)
panel('SoftboxBack', (0, 17, 15), (0, 0, 0), (22, 5), 1.6, (1.0, 0.95, 0.88))
panel('SoftboxLeft', (-16, 2, 11), (0, 0, 0), (4, 18), 1.2, (1.0, 0.93, 0.85))
panel('SoftboxRight', (16, 4, 9), (0, 0, 0), (4, 18), 0.8, (0.85, 0.9, 1.0))
panel('Ceiling', (0, 0, 24), (0, 0, 0), (40, 40), 0.08, (1.0, 0.97, 0.92))
panel('EnamelGloss', (0, 25, 19), (0, 2, 0), (24, 7), 0.45, (1.0, 0.97, 0.92))   # soft sheen on the far dial
panel('FrontLow', (0, -22, 4), (0, 0, 0), (26, 3), 0.9, (1.0, 0.95, 0.9))


# ================================================================ characters (as stage_render.py)
def load(f):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CHARS, f))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    return new, roots


stance = None
RIGS = []
def sumo(f, pos, face, scale=1.65):
    global stance
    new, roots = load(f)
    rig = next((o for o in new if o.type == 'ARMATURE'), None); RIGS.append((rig, roots))
    if rig and rig.animation_data and rig.animation_data.action: stance = rig.animation_data.action
    elif rig and stance: rig.animation_data_create(); rig.animation_data.action = stance
    for r in roots:
        r.location = (pos[0], pos[1], 0); r.scale = (scale,) * 3
        r.rotation_mode = 'XYZ'; r.rotation_euler = (0, 0, math.atan2(face[0] - pos[0], -(face[1] - pos[1])))


def mmat(name, hexc, rough=0.35):
    m = bpy.data.materials.new(name); m.use_nodes = True; bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*lin(hexc), 1); bs.inputs['Roughness'].default_value = rough; return m
def mask(kind, centre, fwd, up, k):
    fwd = (fwd - up * fwd.dot(up)).normalized(); right = fwd.cross(up).normalized()
    B = Matrix((right, fwd, up)).transposed().to_4x4(); B.translation = centre
    parts = []
    def put(o, loc, mat_):
        o.data.materials.append(mat_); bpy.ops.object.shade_smooth()
        o.matrix_world = B @ Matrix.Translation(Vector(loc) * k) @ o.matrix_world; parts.append(o)
    def ell(loc, sc, mat_, half=False):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16); o = bpy.context.object
        if half:
            bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.05], context='VERTS'); bm.to_mesh(o.data); bm.free()
            sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.06
        o.scale = Vector(sc) * k; bpy.ops.object.transform_apply(scale=True); put(o, loc, mat_); return o
    def cone_(loc, r, h, rot, mat_):
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r * k, depth=h * k); o = bpy.context.object
        o.rotation_euler = rot; bpy.ops.object.transform_apply(rotation=True); put(o, loc, mat_)
    def strap(mat_):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.25 * k, minor_radius=0.03 * k); o = bpy.context.object
        o.rotation_euler = (0.25, 0, 0); bpy.ops.object.transform_apply(rotation=True); put(o, (0, -0.02, 0.02), mat_)
    if kind == 'oni':
        R_ = mmat('mOni', 'c8231d'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), R_, True)
        for sd in (-1, 1):
            ell((sd * 0.075, 0.245, 0.02), (0.04, 0.02, 0.025), mmat('mGold', 'ffd23a', 0.3))
            cone_((sd * 0.11, 0.08, 0.2), 0.04, 0.18, (0, sd * 0.45, 0), mmat('mHorn', 'f2e6c8', 0.4))
        strap(R_)
    elif kind == 'hannya':
        W_ = mmat('mHannya', 'eae2c8'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), W_, True)
        for sd in (-1, 1):
            ell((sd * 0.075, 0.245, 0.02), (0.04, 0.02, 0.025), mmat('mGold', 'ffd23a', 0.3))
            cone_((sd * 0.11, 0.06, 0.22), 0.04, 0.22, (0, sd * 0.5, 0), mmat('mHornH', 'd8c890', 0.4))
        ell((0, 0.25, -0.12), (0.07, 0.02, 0.018), mmat('mMouth', '7a1414'))
        strap(W_)
    elif kind == 'kitsune':
        W_ = mmat('mKitsune', 'f6f2ea'); ell((0, 0.13, -0.03), (0.2, 0.12, 0.24), W_, True)
        for sd in (-1, 1):
            ell((sd * 0.075, 0.245, 0.03), (0.045, 0.015, 0.012), mmat('mRed', 'd8262e'))
            cone_((sd * 0.1, 0.06, 0.2), 0.055, 0.14, (0, sd * 0.3, 0), W_)
        cone_((0, 0.3, -0.06), 0.06, 0.14, (-math.pi / 2, 0, 0), W_)
        strap(mmat('mRedS', 'd8262e'))
    return parts


def head_frame(rig, roots):
    pb = rig.pose.bones['head']; M = rig.matrix_world @ pb.matrix
    up = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    fwd = (roots[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    return M.translation + up * 0.11 * roots[0].scale[0], fwd, up


if not NOCHARS:
    A, Bp = (-1.0, -0.15), (1.0, 0.15)
    sumo('sumo2_stance.glb', A, Bp)
    sumo('sumo2_red.glb', Bp, A)
    GX, GY = 0.4, 5.0
    _, gr = load('gyoji.glb')
    for r in gr: r.location = (GX, GY, 0); r.scale = (1.5,) * 3; r.rotation_euler = (0, 0, math.pi)
    scn.frame_set(1)
    for (rig, roots), kind in zip(RIGS, ('oni', 'hannya')):
        if rig: c, f, u = head_frame(rig, roots); mask(kind, c + f * 0.03, f, u, roots[0].scale[0] * 0.95)
    gf = (gr[0].matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    mask('kitsune', Vector((GX, GY, 1.52 * 1.5)) + gf * 0.02, gf, Vector((0, 0, 1)), 1.5 * 0.62)


# ================================================================ game camera & render
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
cam.data.sensor_fit = 'VERTICAL'; cam.data.clip_end = 200
el = math.radians(50); dist = 21
cam.location = (0, -dist * math.cos(el), dist * math.sin(el)); cam.data.angle_y = math.radians(34)
cam.rotation_euler = (Vector((0, 0.6, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
scn.cycles.max_bounces = 6; scn.cycles.glossy_bounces = 4; scn.cycles.transparent_max_bounces = 4
scn.cycles.sample_clamp_indirect = 6.0
scn.render.resolution_x, scn.render.resolution_y = 1280, 720; scn.render.resolution_percentage = PCT
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
scn.render.filepath = os.path.join(OUT, 'ex_game.png')
bpy.ops.render.render(write_still=True)
print('wrote', scn.render.filepath)
