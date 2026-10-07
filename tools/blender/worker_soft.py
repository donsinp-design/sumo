# Fish-market workers, soft variant: three enemy bodies in the same soft toy style as sumo_soft.py / sumo_game.py
# (Little Kitty, Big City-like humans: big round head, chunky fused volumes, mitten hands, flat matte colours).
#   python tools/blender/worker_soft.py OUT_DIR [PREVIEW_DIR] [only=m,f,o] [render=1] [samples=32] [res=700]
# Writes OUT_DIR/worker_m.glb (stocky man, hachimaki), worker_f.glb (woman, bob + bun, bandana) and worker_o.glb
# (older heavy man, bald, towel round the neck). With render=1 it re-imports the GLBs and renders, into PREVIEW_DIR,
# front/back 3/4 views of each at rest, a posed check of each (arms forward, knees bent 40 degrees, posed through
# the bones) and a row of the three.
#
# Contract (public/js/chars.js, class Body): one skinned mesh on one armature with VRoid humanoid bone names
# (J_Bip_C_Hips root ... J_Bip_?_Foot, 19 bones), A-pose rest, hips bone head at 1.018 m, soles at 0, facing glTF -Z
# with the J_Bip_L_* bones on the character's own left, which (like the VRoid samples the game ships) is glTF -X.
# Materials by name: Tops / Bottoms / Shoes (near-white, recoloured in game), Skin, Hair, Apron, Band, Eyes.
#
# Recipe: every clothing / skin region is its own handful of overlapping primitives fused by a voxel remesh,
# Taubin-smoothed (round without shrinking) and decimated; the regions interpenetrate, so cloth edges read as clean
# cuts. Weights: bone heat on one fused whole-body proxy, smoothed and tidied (trunk bands, rigid head, mitts on the
# hand bones), then copied onto every part by distance-weighted nearest proxy vertices; boots ride shin/foot rigidly,
# the apron rides the trunk and only half the thighs.
# Built in Blender's frame facing -Y with the left side on +X (as sumo_soft.py), then turned 180 degrees about Z
# before export, so the glTF faces -Z.
import bpy, math, sys, os
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ARGS = [a for a in sys.argv[sys.argv.index('--') + 1:]] if '--' in sys.argv else [a for a in sys.argv[1:] if not a.endswith('.py')]
OPT = dict(a.split('=', 1) for a in ARGS if '=' in a)
POS = [a for a in ARGS if '=' not in a]
OUT = POS[0] if POS else '/tmp/workers'
PREV = POS[1] if len(POS) > 1 else OUT
os.makedirs(OUT, exist_ok=True); os.makedirs(PREV, exist_ok=True)
ONLY = OPT.get('only', 'm,f,o').split(',')
RENDER = OPT.get('render', '1') != '0'
SAMPLES, RES = int(OPT.get('samples', 32)), int(OPT.get('res', 700))
S2 = (-1, 1)
HIPS_Z = 1.018

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def sstep(a, b, v):
    t = min(max((v - a) / (b - a), 0.0), 1.0); return t * t * (3 - 2 * t)

# ---------------------------------------------------------------- the three workers
VAR = {
    'm': dict(head=(0.19, 0.18, 0.20), hc=1.60, sh_z=1.37, sh_x=0.26, tw=0.30, td=0.21, belly=0.0, hip_x=0.14,
              thigh=0.15, arm=0.08, apron='3f6f8f', band='f4f2ee', hair='crop', hat='hachimaki'),
    'f': dict(head=(0.176, 0.168, 0.186), hc=1.53, sh_z=1.315, sh_x=0.22, tw=0.255, td=0.185, belly=0.0, hip_x=0.13,
              thigh=0.14, arm=0.07, apron='f2a23a', band='c8402f', hair='bob', hat='bandana'),
    'o': dict(head=(0.19, 0.18, 0.192), hc=1.575, sh_z=1.355, sh_x=0.275, tw=0.34, td=0.25, belly=0.07, hip_x=0.15,
              thigh=0.16, arm=0.086, apron='35553c', band='f4f2ee', hair='bald', hat='towel'),
}
BONE_NAMES = ['J_Bip_C_Hips', 'J_Bip_C_Spine', 'J_Bip_C_Chest', 'J_Bip_C_Neck', 'J_Bip_C_Head',
              'J_Bip_L_Shoulder', 'J_Bip_L_UpperArm', 'J_Bip_L_LowerArm', 'J_Bip_L_Hand',
              'J_Bip_R_Shoulder', 'J_Bip_R_UpperArm', 'J_Bip_R_LowerArm', 'J_Bip_R_Hand',
              'J_Bip_L_UpperLeg', 'J_Bip_L_LowerLeg', 'J_Bip_L_Foot', 'J_Bip_R_UpperLeg', 'J_Bip_R_LowerLeg', 'J_Bip_R_Foot']
def SD(s): return 'L' if s > 0 else 'R'


def build(key):
    P = VAR[key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene

    def mat(name, hexcol):
        m = bpy.data.materials.new(name); m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*srgb(hexcol), 1)
        b.inputs['Roughness'].default_value = 0.9; b.inputs['Metallic'].default_value = 0.0
        b.inputs['Specular IOR Level'].default_value = 0.25
        return m
    M = dict(Tops=mat('Tops', 'e8e8e8'), Bottoms=mat('Bottoms', 'd8d8d8'), Shoes=mat('Shoes', 'dcdcdc'),
             Skin=mat('Skin', 'f0c4a2'), Hair=mat('Hair', '3a3040'), Apron=mat('Apron', P['apron']),
             Band=mat('Band', P['band']), Eyes=mat('Eyes', '2a2630'))

    # ------------------------------------------------------------ skeleton landmarks (build frame: front -Y, L on +X)
    hc, sh_z, sh_x = P['hc'], P['sh_z'], P['sh_x']
    rx, ry, rz = P['head']
    HC = Vector((0, 0, hc))
    A = math.radians(45)
    J = {s: Vector((s * sh_x, 0.0, sh_z)) for s in S2}
    D1 = {s: Vector((s * math.cos(A), 0.0, -math.sin(A))) for s in S2}
    E = {s: J[s] + D1[s] * 0.29 for s in S2}
    W = {s: E[s] + D1[s] * 0.27 for s in S2}
    hx = P['hip_x']
    HIP = {s: Vector((s * hx, 0.0, 0.975)) for s in S2}
    KNEE = {s: Vector((s * (hx + 0.005), -0.01, 0.525)) for s in S2}
    ANK = {s: Vector((s * (hx + 0.005), 0.01, 0.085)) for s in S2}
    TOE = {s: Vector((s * (hx + 0.01), -0.17, 0.03)) for s in S2}
    Z_NK = sh_z + 0.03                       # neck bone head
    Z_HD = hc - 0.14                         # head bone head (jaw line)

    # ------------------------------------------------------------ primitive specs and the fuse pipeline
    def E_(c, r, rot=None): return ('e', Vector(c), r, rot)
    def EAX(c, axes, r):
        a, b = Vector(axes[0]).normalized(), Vector(axes[1]).normalized()
        return ('e', Vector(c), r, Matrix((a, b, a.cross(b))).transposed())
    def L_(a, b, ra, rb, caps=True): return ('l', Vector(a), Vector(b), ra, rb, caps)
    def make(specs):
        objs = []
        for sp in specs:
            if sp[0] == 'e':
                bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=tuple(sp[1])); o = bpy.context.object
                o.scale = sp[2]
                if sp[3] is not None: o.rotation_euler = sp[3].to_euler()
                objs.append(o)
            else:
                a, b, ra, rb, caps = sp[1:]; d = b - a
                bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=ra, radius2=rb, depth=d.length, location=tuple((a + b) / 2))
                o = bpy.context.object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); objs.append(o)
                if caps:
                    for c, r in ((a, ra), (b, rb)): objs += make([E_(c, (r, r, r))])
        return objs
    def join(objs, name):
        for o in scn.objects: o.select_set(o in objs)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.object; o.name = name
        bpy.ops.object.transform_apply(location=True, scale=True, rotation=True)
        return o
    def taubin(o, it, lam=0.5, mu=-0.53):
        me = o.data; n = len(me.vertices)
        co = np.empty(n * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        e = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get('vertices', e); e = e.reshape(-1, 2)
        deg = np.maximum(np.bincount(e.ravel(), minlength=n), 1).astype(float)[:, None]
        def lap(Q):
            S = np.zeros_like(Q); np.add.at(S, e[:, 0], Q[e[:, 1]]); np.add.at(S, e[:, 1], Q[e[:, 0]]); return S / deg - Q
        for _ in range(it):
            co += lam * lap(co); co += mu * lap(co)
        me.vertices.foreach_set('co', co.ravel()); me.update()
    def ntris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)
    def finish(o, m_):
        o.data.materials.clear(); o.data.materials.append(m_)
        for p in o.data.polygons: p.use_smooth = True
        if not o.data.uv_layers: o.data.uv_layers.new(name='UVMap')
        return o
    def remesh_smooth(o, voxel, smooth_it):
        r = o.modifiers.new('rm', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = voxel
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='rm')
        taubin(o, smooth_it)
    def decimate(o, tris):
        for _ in range(4):
            n = ntris(o)
            if n <= tris * 1.03: break
            d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = tris / n; d.use_symmetry = True; d.symmetry_axis = 'X'
            bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='dec')
    def fuse(name, specs, m_, voxel, tris, smooth_it=20, floor=False, extra=()):
        o = join(make(specs) + list(extra), name)
        remesh_smooth(o, voxel, smooth_it)
        if floor:
            co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
            co[:, 2] = np.maximum(co[:, 2], 0.0); o.data.vertices.foreach_set('co', co.ravel()); o.data.update()
        decimate(o, tris)
        return finish(o, m_)
    def bvh_of(objs):
        return [BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get()) for o in objs]
    def cast(bvhs, o, d, dist):
        best = None
        for b in bvhs:
            loc, nor, _, dd = b.ray_cast(Vector(o), Vector(d).normalized(), dist)
            if loc is not None and (best is None or dd < best[2]): best = (loc, nor, dd)
        return best
    def radial(bvhs, c, d, R=1.2):
        d = Vector(d).normalized(); h = cast(bvhs, c + d * R, -d, R)
        return max((h[0] - c).dot(d), 0.0) if h else 0.0
    def chain(pts, r):
        out = []
        for a, b in zip(pts[:-1], pts[1:]): out.append(L_(a, b, r, r, caps=False))
        for p in pts: out.append(E_(p, (r, r, r)))
        return out

    # ------------------------------------------------------------ body volumes, by region
    tw, td, belly = P['tw'], P['td'], P['belly']
    def arm_frame(s):
        xh = D1[s]; nin = Vector((-s, 0, 0)); nin = (nin - xh * xh.dot(nin)).normalized()   # palm toward the thigh
        yh = xh.cross(nin).normalized()
        if yh.y > 0: yh = -yh                                                               # thumb forward
        return xh, yh, nin
    ar = P['arm']
    def skin_specs(full=True):
        sp = [E_(HC, (rx, ry, rz)),
              E_((0, -0.035, hc - 0.075), (rx * 0.87, ry * 0.78, rz * 0.58)),                   # full cheeks / jaw
              E_((0, -ry + 0.012, hc - 0.03), (0.032, 0.03, 0.03)),                              # a small round nose
              L_((0, 0.0, sh_z - 0.06), (0, 0.0, hc - 0.08), 0.085, 0.085, caps=False)]          # short neck
        for s in S2:
            sp.append(E_((s * (rx - 0.005), 0.012, hc - 0.015), (0.032, 0.042, 0.052)))          # ear nubs
            sp += [L_(J[s] + D1[s] * (0.06 if full else 0.0), E[s], ar, ar * 0.9), L_(E[s], W[s], ar * 0.9, ar * 0.8)]
            xh, yh, nin = arm_frame(s); H0 = W[s] + xh * 0.015
            sp += [L_(W[s] - xh * 0.02, H0 + xh * 0.04, ar * 0.82, ar * 0.85, caps=False),
                   EAX(H0 + xh * 0.07, (xh, yh, nin), (0.08, 0.072, 0.048)),                     # palm paddle
                   EAX(H0 + xh * 0.125, (xh, yh, nin), (0.06, 0.07, 0.044)),                     # finger block
                   L_(H0 + xh * 0.03 + yh * 0.045 + nin * 0.005, H0 + xh * 0.085 + yh * 0.095 + nin * 0.02, 0.032, 0.03)]
        return sp
    def tops_specs(sleeves=True):
        sp = [E_((0, 0.0, 1.20), (tw, td, 0.27)),
              E_((0, 0.01, sh_z - 0.05), (tw + 0.005, td - 0.015, 0.12)),
              E_((0, 0.005, 1.0), (tw - 0.02, td - 0.005, 0.12))]
        if belly > 0: sp.append(E_((0, -0.06, 1.08), (tw - 0.02, td + 0.02, 0.24)))
        for s in S2:
            sp.append(E_(J[s] + Vector((-s * 0.02, 0, 0)), (0.105, 0.105, 0.1)))
            if sleeves: sp.append(L_(J[s], J[s] + D1[s] * 0.17, ar + 0.035, ar + 0.03, caps=False))
            sp.append(L_((s * 0.05, 0.01, sh_z), J[s], 0.11, 0.1, caps=False))                      # shoulder line
        return sp
    def bottoms_specs():
        sp = [E_((0, 0.01, 0.94), (tw - 0.035, td - 0.01, 0.15))]
        for s in S2:
            sp += [L_(HIP[s] + Vector((0, 0.0, -0.01)), KNEE[s], P['thigh'], P['thigh'] * 0.82),
                   L_(KNEE[s], ANK[s] + Vector((0, 0, 0.26)), P['thigh'] * 0.8, P['thigh'] * 0.72)]
        return sp
    def boot_specs():
        sp = []
        for s in S2:
            x = s * (hx + 0.005); br = 0.13 if key != 'f' else 0.12
            sp += [L_((x, 0.012, 0.05), (x, 0.0, 0.455), br, br + 0.006, caps=False),
                   E_((x, 0.0, 0.452), (br + 0.016, br + 0.016, 0.034)),                         # turned rim
                   E_((x, -0.075, 0.068), (br - 0.005, 0.185, 0.078)),                             # toe
                   E_((x, 0.04, 0.065), (br - 0.008, 0.10, 0.075))]                               # heel
        return sp

    # helper solid (no arms) for draping the apron, straps and towel
    drape = join(make(tops_specs(False) + bottoms_specs() + [s_ for s_ in skin_specs() if s_[0] == 'l' and s_[1].x == 0]), 'Drape')
    DR = bvh_of([drape])

    parts = {}
    parts['Skin'] = fuse('Skin', skin_specs(), M['Skin'], 0.009, 1650 if key != 'f' else 1550, 22)
    parts['Tops'] = fuse('Tops', tops_specs(), M['Tops'], 0.011, 950, 22)
    parts['Bottoms'] = fuse('Bottoms', bottoms_specs(), M['Bottoms'], 0.011, 650, 22)
    parts['Shoes'] = fuse('Shoes', boot_specs(), M['Shoes'], 0.009, 620, 14, floor=True)
    HEAD = bvh_of([parts['Skin']])

    # ------------------------------------------------------------ rubber apron: bib + skirt hanging straight from the belly
    z_top, z_w, z_bot = sh_z - 0.11, 1.02 - (0.03 if key == 'f' else 0), 0.40
    NZ, NU = 34, 31
    zs = np.linspace(z_bot, z_top, NZ)
    def half(z): return 1.18 + (0.60 - 1.18) * sstep(z_w - 0.02, z_w + 0.14, z)
    R = np.zeros((NZ, NU)); TH = np.zeros((NZ, NU))
    for i, z in enumerate(zs):
        for k in range(NU):
            u = -1 + 2 * k / (NU - 1); th = u * half(z); TH[i, k] = th
            R[i, k] = radial(DR, Vector((0, 0, z)), (math.sin(th), -math.cos(th), 0))
    for i in range(NZ - 2, -1, -1):                                     # below the belly the rubber hangs straight
        if zs[i] < z_w + 0.06: R[i] = np.maximum(R[i], R[i + 1])
    for i, z in enumerate(zs):
        r = R[i]
        for _ in range(2): r = np.maximum(r, np.maximum(np.roll(r, 1), np.roll(r, -1)))
        for _ in range(6): r = np.concatenate([[r[0]], (r[:-2] + 2 * r[1:-1] + r[2:]) / 4, [r[-1]]])
        R[i] = r + 0.024 + 0.05 * max(0.0, z_w - z) ** 1.3
    for _ in range(6): R[1:-1] = (R[:-2] + 2 * R[1:-1] + R[2:]) / 4
    verts = [(R[i, k] * math.sin(TH[i, k]), -R[i, k] * math.cos(TH[i, k]), zs[i]) for i in range(NZ) for k in range(NU)]
    faces = [(i * NU + k, i * NU + k + 1, (i + 1) * NU + k + 1, (i + 1) * NU + k) for i in range(NZ - 1) for k in range(NU - 1)]
    me = bpy.data.meshes.new('ApronSheet'); me.from_pydata(verts, [], faces); me.update()
    sheet = bpy.data.objects.new('ApronSheet', me); scn.collection.objects.link(sheet)
    so = sheet.modifiers.new('so', 'SOLIDIFY'); so.thickness = 0.026; so.offset = 0.0
    bpy.context.view_layer.objects.active = sheet; bpy.ops.object.modifier_apply(modifier='so')
    ap_specs = []
    # waist ties round the back, with a small bow
    tie = []
    for j in range(17):
        th = half(z_w) + (2 * math.pi - 2 * half(z_w)) * j / 16
        d = Vector((math.sin(th), -math.cos(th), 0)); tie.append(d * (radial(DR, Vector((0, 0, z_w)), d) + 0.012) + Vector((0, 0, z_w)))
    ap_specs += chain(tie, 0.016)
    yb = tie[8].y
    for s in S2:
        ap_specs += [EAX((s * 0.045, yb + 0.012, z_w + 0.01), ((s, 0, 0.3), (0, 1, 0)), (0.05, 0.022, 0.03)),
                     L_((s * 0.01, yb + 0.015, z_w), (s * 0.06, yb + 0.03, z_w - 0.14), 0.016, 0.014)]
    ap_specs.append(E_((0, yb + 0.018, z_w), (0.024, 0.02, 0.024)))
    if P['hat'] != 'towel':                                              # neck strap from the bib corners round the nape
        neck = []
        corner = {s: Vector((R[-1, 0 if s < 0 else -1] * math.sin(TH[-1, 0 if s < 0 else -1]),
                             -R[-1, 0 if s < 0 else -1] * math.cos(TH[-1, 0 if s < 0 else -1]), z_top - 0.01)) for s in S2}
        def on_top(x, y):                                               # resting on the shoulders / neck, seen from above
            h = cast(DR, Vector((x, y, sh_z + 0.4)), (0, 0, -1), 1.0)
            return Vector((x, y, (h[0].z if h else sh_z) + 0.013))
        for s in (-1, 1):
            seq = [corner[s]]
            a0 = math.radians(30); p0 = on_top(s * 0.14 * math.sin(a0), -0.13 * math.cos(a0))
            mid = (corner[s] + p0) / 2; d = Vector((mid.x, mid.y, 0)).normalized()
            seq.append(Vector((0, 0, mid.z)) + d * (radial(DR, Vector((0, 0, mid.z)), d) + 0.013))
            for f in np.linspace(0, 1, 7):
                ang = s * (a0 + f * (math.pi - a0))
                seq.append(on_top(0.14 * math.sin(ang), -0.13 * math.cos(ang)))
            neck += seq if s < 0 else seq[::-1][1:]
        ap_specs += chain(neck, 0.015)
    parts['Apron'] = fuse('Apron', ap_specs, M['Apron'], 0.007, 600, 24, extra=[sheet])

    # ------------------------------------------------------------ hair, headwear, face
    def shell(name, m_, bvhs, center, pole, inside, thick, NA=36, NE=9, bmax_lim=2.7):
        """a smooth cap over a surface: every direction within `inside` (a star-shaped region round the pole)"""
        pole = Vector(pole).normalized(); pu = Vector((1, 0, 0)); pv = pole.cross(pu).normalized(); pu = pv.cross(pole).normalized()
        def pdir(beta, a): return (pole * math.cos(beta) + (pu * math.cos(a) + pv * math.sin(a)) * math.sin(beta)).normalized()
        B0 = 0.06; bm = []
        for kk in range(NA):
            a = 2 * math.pi * kk / NA; b_ = B0
            while b_ < bmax_lim and inside(pdir(b_ + 0.01, a)): b_ += 0.01
            bm.append(b_)
        bm = np.array(bm)
        for _ in range(3): bm = (np.roll(bm, 1) + 2 * bm + np.roll(bm, -1)) / 4
        verts, faces = [], []
        for kk in range(NA):
            a = 2 * math.pi * kk / NA
            for j in range(NE + 1):
                beta = B0 + (bm[kk] - B0) * (j / NE) ** 0.85
                dr = pdir(beta, a); h = cast(bvhs, center + dr * 0.6, -dr, 0.6)
                l, n_ = (h[0], h[1]) if h else (center + dr * 0.2, dr)
                ed = min(1.0, (NE - j) / 2.5); ed = ed * ed * (3 - 2 * ed)
                verts.append(tuple(l + n_ * (0.002 + thick * ed)))
        for kk in range(NA):
            k2 = (kk + 1) % NA
            for j in range(NE):
                faces.append((kk * (NE + 1) + j, k2 * (NE + 1) + j, k2 * (NE + 1) + j + 1, kk * (NE + 1) + j + 1))
        cap = [kk * (NE + 1) for kk in range(NA)]
        faces.append(tuple(cap))
        me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.validate(); me.update()
        o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
        bpy.context.view_layer.objects.active = o
        for oo in scn.objects: oo.select_set(oo == o)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(); bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        return finish(o, m_)
    def el_phi(d):
        return math.asin(max(-1, min(1, d.z))), math.atan2(d.x, -d.y)          # phi 0 = front
    extra_hair = []
    if P['hair'] == 'crop':
        pts = [(0.0, 0.40), (0.8, 0.33), (1.25, 0.18), (1.55, 0.16), (1.9, 0.08), (2.4, -0.30), (math.pi, -0.48)]
        def inside(d):
            el, ph = el_phi(d); return el > float(np.interp(abs(ph), [p[0] for p in pts], [p[1] for p in pts]))
        parts['Hair'] = shell('Hair', M['Hair'], HEAD, HC, (0, 0.25, 1), inside, 0.02)
    elif P['hair'] == 'bob':
        hs = [E_((0, 0.02, hc + 0.012), (rx + 0.03, ry + 0.035, rz + 0.025)),
              E_((0, 0.035, hc - 0.075), (rx + 0.035, ry + 0.012, 0.13)),
              E_((0, ry + 0.07, hc - 0.03), (0.075, 0.07, 0.072))]                            # bun at the back
        ho = join(make(hs), 'Hair'); remesh_smooth(ho, 0.01, 4)
        cut = join(make([E_((0, -0.13, hc - 0.115), (rx - 0.025, 0.23, 0.17)),
                         E_((0, 0.02, hc - 0.32), (rx + 0.1, ry + 0.02, 0.1))]), 'Cut')
        remesh_smooth(cut, 0.01, 2)
        b = ho.modifiers.new('cut', 'BOOLEAN'); b.operation = 'DIFFERENCE'; b.object = cut; b.solver = 'EXACT'
        bpy.context.view_layer.objects.active = ho; bpy.ops.object.modifier_apply(modifier='cut')
        bpy.data.objects.remove(cut)
        remesh_smooth(ho, 0.009, 16); decimate(ho, 650); parts['Hair'] = finish(ho, M['Hair'])
    else:   # bald: a short horseshoe of hair round the back and sides
        def inside(d):
            el, ph = el_phi(d); return abs(ph) > 1.45 and -0.42 < el < 0.12 + 0.12 * (abs(ph) - 1.45)
        # star-shaped round a pole pointing back and down
        parts['Hair'] = shell('Hair', M['Hair'], HEAD, HC, (0, 1, -0.15), inside, 0.016, NA=40, NE=8)
    HAIRB = bvh_of([parts['Skin'], parts['Hair']])

    band_specs = []
    if P['hat'] == 'hachimaki':
        ring = []
        for j in range(24):
            a = 2 * math.pi * j / 24; z = hc + 0.06 + 0.035 * math.cos(a)
            d = Vector((math.sin(a), -math.cos(a), 0)); ring.append(Vector((0, 0, z)) + d * (radial(HAIRB, Vector((0, 0, z)), d) + 0.006))
        band_specs += chain(ring + [ring[0]], 0.026)
        kb = ring[12] + Vector((0, 0.025, 0))
        band_specs += [E_(kb, (0.04, 0.03, 0.034)),
                       L_(kb, kb + Vector((0.05, 0.045, -0.11)), 0.022, 0.018), L_(kb, kb + Vector((-0.035, 0.05, -0.13)), 0.022, 0.018)]
        parts['Band'] = fuse('Band', band_specs, M['Band'], 0.008, 420, 8)
    elif P['hat'] == 'bandana':
        def inside(d): return d.z > 0.30 - 0.32 * d.y
        cap = shell('BandCap', M['Band'], bvh_of([parts['Hair']]), HC, (0, 0.2, 1), inside, 0.016, NA=34, NE=8)
        h = cast(bvh_of([parts['Hair']]), HC + Vector((0, 0.6, 0.06)), (0, -1, 0), 0.6)
        kb = (h[0] if h else HC + Vector((0, ry + 0.04, 0.06))) + Vector((0, 0.02, -0.0))
        tails = make([E_(kb, (0.034, 0.026, 0.03)), L_(kb, kb + Vector((0.04, 0.04, -0.12)), 0.02, 0.014),
                      L_(kb, kb + Vector((-0.03, 0.045, -0.105)), 0.02, 0.014)])
        knot = join(tails, 'BandKnot'); remesh_smooth(knot, 0.007, 8); finish(knot, M['Band'])
        parts['Band'] = join([cap, knot], 'Band')
    else:   # towel round the neck: a fat soft loop on the shoulders, both ends hanging over the bib
        APB = bvh_of([drape, parts['Apron']])
        loop = []
        for j in range(24):
            a = 2 * math.pi * j / 24
            xy = Vector((0.205 * math.sin(a), -0.175 * math.cos(a) + 0.01, 0))
            h = cast(DR, Vector((xy.x, xy.y, sh_z + 0.4)), (0, 0, -1), 1.0)
            loop.append(Vector((xy.x, xy.y, (h[0].z if h else sh_z) + 0.035)))
        band_specs += chain(loop + [loop[0]], 0.05)
        for s in S2:
            seq = []
            for f in np.linspace(0, 1, 5):
                z = sh_z + 0.0 - f * 0.27; x = s * (0.13 + 0.02 * f)
                h = cast(APB, Vector((x, -0.8, z)), (0, 1, 0), 0.8)
                seq.append(Vector((x, (h[0].y if h else -0.25) - 0.03, z)))
            band_specs += chain([loop[1 if s > 0 else 23]] + seq, 0.042)
        parts['Band'] = fuse('Band', band_specs, M['Band'], 0.009, 700, 12)

    # face: two small dark dot eyes and small brows
    face = []
    for s in S2:
        h = cast(HEAD, Vector((s * 0.068, -0.8, hc - 0.005)), (0, 1, 0), 0.8)
        l = h[0]
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, location=tuple(l + Vector((0, 0.004, 0))))
        o = bpy.context.object; o.scale = (0.016, 0.008, 0.021); face.append(o)
    eyes = join(face, 'Eyes'); finish(eyes, M['Eyes']); parts['Eyes'] = eyes
    brows = []
    for s in S2:
        a_ = cast(HEAD, Vector((s * 0.045, -0.8, hc + 0.048)), (0, 1, 0), 0.8)[0]
        b_ = cast(HEAD, Vector((s * 0.092, -0.8, hc + 0.042 + (0.0 if key != 'o' else -0.006))), (0, 1, 0), 0.8)[0]
        brows.append(L_(a_ + Vector((0, -0.004, 0)), b_ + Vector((0, -0.002, 0)), 0.009 if key != 'o' else 0.012, 0.008 if key != 'o' else 0.011))
    parts['Brows'] = fuse('Brows', brows, M['Hair'], 0.004, 140, 6)
    bpy.data.objects.remove(drape)

    # ------------------------------------------------------------ armature (A-pose), VRoid names
    rig_data = bpy.data.armatures.new('Armature'); rig = bpy.data.objects.new('Armature', rig_data); scn.collection.objects.link(rig)
    for o in scn.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = rig; rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    FWD, UP = Vector((0, -1, 0)), Vector((0, 0, 1))
    PARENT = {}
    def bone(name, head, tail, parent=None, roll_to=FWD):
        b = rig_data.edit_bones.new(name); b.head = Vector(head); b.tail = Vector(tail); b.use_connect = False
        if parent: b.parent = rig_data.edit_bones[parent]
        b.align_roll(roll_to); PARENT[name] = parent
    bone('J_Bip_C_Hips', (0, 0, HIPS_Z), (0, 0, 1.12))
    bone('J_Bip_C_Spine', (0, 0, 1.12), (0, 0, 1.22), 'J_Bip_C_Hips')
    bone('J_Bip_C_Chest', (0, 0, 1.22), (0, 0, Z_NK), 'J_Bip_C_Spine')
    bone('J_Bip_C_Neck', (0, 0, Z_NK), (0, 0, Z_HD), 'J_Bip_C_Chest')
    bone('J_Bip_C_Head', (0, 0, Z_HD), (0, 0, hc + rz), 'J_Bip_C_Neck')
    for s in S2:
        n = SD(s)
        bone('J_Bip_%s_Shoulder' % n, (s * 0.05, 0, sh_z), J[s], 'J_Bip_C_Chest')
        bone('J_Bip_%s_UpperArm' % n, J[s], E[s], 'J_Bip_%s_Shoulder' % n)
        bone('J_Bip_%s_LowerArm' % n, E[s], W[s], 'J_Bip_%s_UpperArm' % n)
        bone('J_Bip_%s_Hand' % n, W[s], W[s] + D1[s] * 0.15, 'J_Bip_%s_LowerArm' % n)
        bone('J_Bip_%s_UpperLeg' % n, HIP[s], KNEE[s], 'J_Bip_C_Hips')
        bone('J_Bip_%s_LowerLeg' % n, KNEE[s], ANK[s], 'J_Bip_%s_UpperLeg' % n)
        bone('J_Bip_%s_Foot' % n, ANK[s], TOE[s], 'J_Bip_%s_LowerLeg' % n, UP)
    bpy.ops.object.mode_set(mode='OBJECT')

    # ------------------------------------------------------------ weights: bone heat on a fused whole-body proxy
    proxy = fuse('Proxy', skin_specs() + tops_specs() + bottoms_specs() + boot_specs(), M['Skin'], 0.016, 7000, 10)
    for o in scn.objects: o.select_set(o in (proxy, rig))
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    pv = proxy.data.vertices; VG = proxy.vertex_groups
    def unweighted(o): return [v.index for v in o.data.vertices if sum(g.weight for g in v.groups) < 1e-3]
    uw = unweighted(proxy); print(key, 'bone heat: unweighted', len(uw), 'of', len(pv))
    if len(uw) > 0.05 * len(pv):
        proxy.parent = None; proxy.modifiers.clear(); proxy.vertex_groups.clear()
        for b in rig_data.bones: b.envelope_distance = 0.2; b.head_radius = b.tail_radius = 0.1
        for o in scn.objects: o.select_set(o in (proxy, rig))
        bpy.context.view_layer.objects.active = rig; bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
        uw = unweighted(proxy); print(key, 'fell back to envelopes')
    if uw:
        kd = KDTree(len(pv)); uws = set(uw)
        for v in pv:
            if v.index not in uws: kd.insert(v.co, v.index)
        kd.balance()
        for i in uw:
            _, j, _ = kd.find(pv[i].co)
            for g in pv[j].groups: VG[g.group].add([i], g.weight, 'REPLACE')
    def wget(v): return {VG[g.group].name: g.weight for g in v.groups if g.weight > 0}
    def wset(v, w):
        for g in list(v.groups): VG[g.group].remove([v.index])
        t = sum(w.values()) or 1.0
        for n, x in w.items():
            if x / t > 1e-4: VG[n].add([v.index], x / t, 'REPLACE')
    def wsmooth(f, rep):
        bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = proxy; proxy.select_set(True)
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=f, repeat=rep)
        bpy.ops.object.mode_set(mode='OBJECT'); bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    wsmooth(0.5, 6)
    TRUNK = ('J_Bip_C_Hips', 'J_Bip_C_Spine', 'J_Bip_C_Chest')
    def is_arm(n): return n.endswith(('Shoulder', 'UpperArm', 'LowerArm', 'Hand'))
    def is_leg(n): return n.endswith(('UpperLeg', 'LowerLeg', 'Foot'))
    def head_rule(v, w):
        c = v.co
        if c.z < sh_z - 0.03 or abs(c.x) > sh_x - 0.06 or (c.x * c.x / (rx + 0.04) ** 2 + c.y * c.y / (ry + 0.05) ** 2) > 1: return w
        wh = sstep(Z_NK - 0.01, Z_NK + 0.07, c.z); wn = (1 - wh) * sstep(sh_z - 0.03, Z_NK, c.z)
        out = {'J_Bip_C_Head': wh, 'J_Bip_C_Neck': wn}
        if 1 - wh - wn > 1e-4: out['J_Bip_C_Chest'] = 1 - wh - wn
        return out
    def hand_rule(v, w):
        c = v.co
        for s in S2:
            if c.x * s < sh_x: continue
            rel = c - W[s]; t = rel.dot(D1[s])
            if t < -0.12 or (rel - D1[s] * t).length > 0.16: continue
            wh = sstep(-0.06, 0.03, t); n = SD(s)
            return {'J_Bip_%s_Hand' % n: wh, 'J_Bip_%s_LowerArm' % n: 1 - wh}
        return w
    for v in pv:
        w = wget(v); c = v.co
        # legs have no say above the seat; the arms none near the midline (their share goes to the trunk)
        kl = sstep(1.03, 0.86, c.z); ka = sstep(sh_x - 0.13, sh_x - 0.02, abs(c.x))
        moved = 0.0
        for n in list(w):
            if is_leg(n) and kl < 1: moved += w[n] * (1 - kl); w[n] *= kl
            if is_arm(n) and ka < 1 and c.z > 0.9: moved += w[n] * (1 - ka); w[n] *= ka
        if moved: w['J_Bip_C_Chest' if c.z > 1.15 else 'J_Bip_C_Hips'] = w.get('J_Bip_C_Chest' if c.z > 1.15 else 'J_Bip_C_Hips', 0) + moved
        # the trunk bends as one soft volume: hips / spine / chest share by height over wide bands
        tot = sum(w.get(n, 0.0) for n in TRUNK)
        if tot > 1e-4:
            wh = 1 - sstep(0.98, 1.17, c.z); wc = sstep(1.15, 1.34, c.z); ws = max(0.0, 1 - wh - wc)
            for n, x in zip(TRUNK, (wh, ws, wc)): w[n] = x * tot
        wset(v, head_rule(v, w))
    wsmooth(0.6, 6)
    for v in pv: wset(v, hand_rule(v, head_rule(v, wget(v))))
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = proxy; proxy.select_set(True)
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0.02)
    bpy.ops.object.mode_set(mode='OBJECT'); bpy.ops.object.vertex_group_normalize_all(lock_active=False)

    PCO = [v.co.copy() for v in pv]; PW = [wget(v) for v in pv]
    KD = KDTree(len(PCO))
    for i, c in enumerate(PCO): KD.insert(c, i)
    KD.balance()
    def skin_w(p, k=6):
        acc = {}
        for c, i, d in KD.find_n(p, k):
            ww = 1 / (d + 0.004) ** 2
            for g, x in PW[i].items(): acc[g] = acc.get(g, 0) + x * ww
        t = sum(acc.values()) or 1
        return {g: x / t for g, x in acc.items() if x / t > 0.01}
    def apron_w(p):                      # trunk above; below the seat the rubber follows the thighs (never shins / feet)
        w = skin_w(p); out = {}
        for n, x in w.items():
            if is_arm(n): n = 'J_Bip_C_Hips' if p.z < 1.1 else 'J_Bip_C_Chest'
            elif n.endswith(('LowerLeg', 'Foot')): n = n[:8] + 'UpperLeg'
            out[n] = out.get(n, 0) + x
        return out
    def towel_w(p):
        w = skin_w(p); out = {}
        for n, x in w.items():
            if is_arm(n) or n == 'J_Bip_C_Head': n = 'J_Bip_C_Chest'
            out[n] = out.get(n, 0) + x
        return out
    def boot_w(p):
        s = 1 if p.x > 0 else -1; n = SD(s)
        wf = sstep(ANK[s].z + 0.08, ANK[s].z - 0.01, p.z) * sstep(ANK[s].y + 0.0, ANK[s].y - 0.08, p.y)
        return {'J_Bip_%s_Foot' % n: wf, 'J_Bip_%s_LowerLeg' % n: 1 - wf}
    RULE = {'Skin': lambda p: hand_rule(type('V', (), {'co': p})(), head_rule(type('V', (), {'co': p})(), skin_w(p))),
            'Tops': skin_w, 'Bottoms': skin_w, 'Shoes': boot_w, 'Apron': apron_w,
            'Hair': lambda p: {'J_Bip_C_Head': 1.0}, 'Eyes': lambda p: {'J_Bip_C_Head': 1.0}, 'Brows': lambda p: {'J_Bip_C_Head': 1.0},
            'Band': towel_w if P['hat'] == 'towel' else (lambda p: {'J_Bip_C_Head': 1.0})}
    for nm, o in parts.items():
        o.vertex_groups.clear()
        for b in BONE_NAMES: o.vertex_groups.new(name=b)
        for v in o.data.vertices:
            w = RULE[nm](v.co); t = sum(w.values()) or 1
            for g, x in w.items():
                if x / t > 1e-4: o.vertex_groups[g].add([v.index], x / t, 'REPLACE')
    bpy.data.objects.remove(proxy)

    # ------------------------------------------------------------ one skinned mesh, turned to face glTF -Z
    objs = list(parts.values())
    print(key, 'parts', {n: (ntris(o), round(min(v.co.z for v in o.data.vertices), 3)) for n, o in parts.items()})
    hero = join(objs, 'Worker'); hero.data.name = 'Worker_' + key
    hero.data.validate(verbose=False)
    for o in scn.objects: o.select_set(o == hero)
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    if hasattr(hero.data, 'set_sharp_from_angle'): hero.data.set_sharp_from_angle(angle=math.radians(180))
    for p in hero.data.polygons: p.use_smooth = True
    ROT = Matrix.Rotation(math.pi, 4, 'Z')
    hero.data.transform(ROT); hero.data.update()
    for o in scn.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = rig; rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for b in rig_data.edit_bones:
        h, t = ROT @ b.head, ROT @ b.tail; b.head = h; b.tail = t
        b.align_roll(Vector((0, 0, 1)) if b.name.endswith('Foot') else Vector((0, 1, 0)))
    bpy.ops.object.mode_set(mode='OBJECT')
    hero.parent = rig
    am = hero.modifiers.new('Armature', 'ARMATURE'); am.object = rig
    tris = ntris(hero); uw = unweighted(hero)
    mats = [m_.name for m_ in hero.data.materials]
    print('WORKER', key, 'TRIANGLES', tris, 'verts', len(hero.data.vertices), 'unweighted', len(uw), 'materials', mats)
    out = os.path.join(OUT, 'worker_%s.glb' % key)
    for o in scn.objects: o.select_set(o in (hero, rig))
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_skins=True, export_animations=False,
                              export_apply=False, export_rest_position_armature=True, export_yup=True,
                              export_texcoords=True, export_normals=True)
    print('exported', out)
    return tris


TRIS = {}
for k in ONLY: TRIS[k] = build(k)


# ---------------------------------------------------------------- check: re-import, measure, pose through the bones, render
def check_and_render():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    rigs = {}
    for i, k in enumerate(ONLY):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(OUT, 'worker_%s.glb' % k))
        new = [o for o in bpy.data.objects if o not in before]
        rg = next(o for o in new if o.type == 'ARMATURE'); ms = [o for o in new if o.type == 'MESH' and o.users_collection and o.vertex_groups]   # (not the importer's bone-shape icosphere)
        rigs[k] = (rg, ms, [o for o in new if o.parent is None])
    report = {}
    def mesh_z(ms):
        bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); zs = []
        for o in ms:
            ev = o.evaluated_get(dg); me = ev.to_mesh()
            co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
            co = co @ np.array(o.matrix_world.to_3x3()).T + np.array(o.matrix_world.translation)
            zs.append(co); ev.to_mesh_clear()
        return np.concatenate(zs)
    for k, (rg, ms, roots) in rigs.items():
        bones = [b.name for b in rg.data.bones]
        H = rg.matrix_world @ rg.data.bones['J_Bip_C_Hips'].head_local
        co = mesh_z(ms)
        la = rg.matrix_world @ rg.data.bones['J_Bip_L_UpperArm'].head_local
        fa, ft = rg.matrix_world @ rg.data.bones['J_Bip_L_Foot'].head_local, rg.matrix_world @ rg.data.bones['J_Bip_L_LowerLeg'].head_local
        # Blender +Y = glTF -Z (front); Blender -X = glTF -X
        toe = rg.matrix_world @ rg.data.bones['J_Bip_L_Foot'].tail_local
        report[k] = dict(hips=round(H.z, 4), top=round(float(co[:, 2].max()), 3), bottom=round(float(co[:, 2].min()), 3),
                         nbones=len(bones), allnames=sorted(bones) == sorted(BONE_NAMES),
                         hips_parent=rg.data.bones['J_Bip_C_Hips'].parent, L_upperarm_gltf_x=round(la.x, 3),
                         faces_gltf_minusZ=toe.y > fa.y,
                         arm=round((rg.data.bones['J_Bip_L_UpperArm'].length + rg.data.bones['J_Bip_L_LowerArm'].length), 3),
                         leg=round((rg.data.bones['J_Bip_L_UpperLeg'].length + rg.data.bones['J_Bip_L_LowerLeg'].length), 3),
                         tris=sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in ms))
        print('CHECK', k, report[k])
    if not RENDER: return report
    world = bpy.data.worlds.new('W'); world.use_nodes = True; scn.world = world
    bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*srgb('ece4f6'), 1); bg.inputs['Strength'].default_value = 1.1
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(sun)
    sun.data.energy = 2.4; sun.data.color = srgb('ffe8d0'); sun.data.angle = math.radians(20)
    sun.rotation_euler = (math.radians(40), 0, math.radians(150))
    bpy.ops.mesh.primitive_plane_add(size=40); gnd = bpy.context.object
    gm = bpy.data.materials.new('Floor'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*srgb('f2ece6'), 1); gnd.data.materials.append(gm)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam); scn.camera = cam
    scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = SAMPLES; scn.cycles.use_denoising = True
    scn.view_settings.view_transform = 'Standard'
    def shoot(path, tgt, az, el, dist, lens, rx_, ry_):
        a, e = math.radians(az), math.radians(el)
        cam.location = tgt + Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))) * dist   # az 0 = in front (+Y)
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = lens
        scn.render.resolution_x, scn.render.resolution_y = rx_, ry_
        scn.render.filepath = path; bpy.ops.render.render(write_still=True)
    def show_only(k):
        for kk, (rg, ms, roots) in rigs.items():
            for o in ms + [rg]: o.hide_render = (k is not None and kk != k)
    def set_root(k, x):
        for o in rigs[k][2]: o.location.x = x
    # posing: aim each bone (head -> child head) along a direction, parents first
    def aim(rg, name, child, d):
        bpy.context.view_layer.update()
        pb, pc = rg.pose.bones[name], rg.pose.bones[child]
        v = (pc.head - pb.head).normalized(); Rm = v.rotation_difference(Vector(d).normalized()).to_matrix().to_4x4()
        Mx = pb.matrix.copy(); t = Mx.translation.copy(); M2 = Rm @ Mx; M2.translation = t; pb.matrix = M2
        bpy.context.view_layer.update()
    def pose_check(rg):
        b40 = math.radians(20)
        for n, sx in (('L', -1), ('R', 1)):           # L is on Blender -X
            aim(rg, 'J_Bip_%s_UpperArm' % n, 'J_Bip_%s_LowerArm' % n, (sx * 0.28, 0.95, -0.12))
            aim(rg, 'J_Bip_%s_LowerArm' % n, 'J_Bip_%s_Hand' % n, (-sx * 0.05, 0.9, 0.35))
            aim(rg, 'J_Bip_%s_UpperLeg' % n, 'J_Bip_%s_LowerLeg' % n, (0, math.sin(b40), -math.cos(b40)))
            aim(rg, 'J_Bip_%s_LowerLeg' % n, 'J_Bip_%s_Foot' % n, (0, -math.sin(b40), -math.cos(b40)))
        aim(rg, 'J_Bip_C_Spine', 'J_Bip_C_Chest', (0, 0.12, 1))
    def unpose(rg):
        for pb in rg.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    for k in rigs:
        show_only(k); set_root(k, 0)
        for o in rigs[k][2]: o.location.x = 0
        tgt = Vector((0, 0, 0.9))
        shoot(os.path.join(PREV, 'w%s_front.png' % k), tgt, 35, 45, 3.7, 50, RES, RES)
        shoot(os.path.join(PREV, 'w%s_back.png' % k), tgt, 215, 45, 3.7, 50, RES, RES)
        rg = rigs[k][0]; pose_check(rg)
        hz = mesh_z(rigs[k][1])[:, 2].min()
        for o in rigs[k][2]: o.location.z -= hz
        shoot(os.path.join(PREV, 'w%s_posed.png' % k), tgt, 35, 40, 3.7, 50, RES, RES)
        shoot(os.path.join(PREV, 'w%s_posed_side.png' % k), tgt, 90, 15, 3.7, 50, RES, RES)
        for o in rigs[k][2]: o.location.z = 0
        unpose(rg)
    show_only(None)
    for i, k in enumerate(rigs): set_root(k, (i - (len(rigs) - 1) / 2) * 1.25)
    shoot(os.path.join(PREV, 'row_front.png'), Vector((0, 0, 0.9)), 20, 30, 6.5, 50, int(RES * 1.6), RES)
    shoot(os.path.join(PREV, 'row_back.png'), Vector((0, 0, 0.9)), 200, 45, 6.5, 50, int(RES * 1.6), RES)
    # the same row with game-like recolours of the near-white Tops / Bottoms / Shoes (the game multiplies these)
    TINT = [dict(Tops='5b7fa6', Bottoms='2a2e44', Shoes='22262e'), dict(Tops='e9e2cf', Bottoms='2a2e44', Shoes='f2f2ec'),
            dict(Tops='8a3a32', Bottoms='3a3a40', Shoes='22262e')]
    for i, k in enumerate(rigs):
        for o in rigs[k][1]:
            for m_ in o.data.materials:
                base = m_.name.split('.')[0]
                if base in TINT[i % 3]:
                    c = srgb(TINT[i % 3][base]); b = m_.node_tree.nodes['Principled BSDF'].inputs['Base Color']
                    b.default_value = tuple(x * y for x, y in zip(b.default_value, (*c, 1)))
    shoot(os.path.join(PREV, 'row_tinted.png'), Vector((0, 0, 0.9)), 20, 45, 6.5, 50, int(RES * 1.6), RES)
    return report

print('TRIS', TRIS)
check_and_render()
print('done')
