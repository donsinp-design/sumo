# Render the option-1 segment as separate light passes (multilayer EXR) for a flat-look composite.
import bpy,sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[-3]); cam=sys.argv[-2]; out=sys.argv[-1]
s=bpy.context.scene; s.camera=bpy.data.objects[cam]
vl=s.view_layers[0]
for p in ('use_pass_diffuse_direct','use_pass_diffuse_indirect','use_pass_diffuse_color','use_pass_glossy_direct','use_pass_glossy_indirect','use_pass_glossy_color','use_pass_transmission_direct','use_pass_transmission_indirect','use_pass_transmission_color','use_pass_emit','use_pass_environment','use_pass_ambient_occlusion','use_pass_normal'):
    setattr(vl,p,True)
s.render.film_transparent=False
# lighter, warmer street greys and softer darks (KKBC roads read pale, wires read grey-violet, not black)
REC={2:'b3aba2',3:'bdb5ab',4:'a0978e',0:'4d4756',1:'524b5a',8:'cbbfb1',9:'b3a698'}
im=bpy.data.images['KKBC_Palette']; px=list(im.pixels); W=im.size[0]
def lin(h): return [ (v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4) for v in (int(h[i:i+2],16)/255 for i in (0,2,4))]
for i,h in REC.items():
    c=lin(h) if im.colorspace_settings.name!='sRGB' else [int(h[k:k+2],16)/255 for k in (0,2,4)]
    for y in range((i//8)*4,(i//8)*4+4):
        for x in range((i%8)*4,(i%8)*4+4):
            px[(y*W+x)*4:(y*W+x)*4+3]=c
im.pixels=px; im.update()
# soften the sumo: iron out skinning lumps and muscle-like bumps so he reads as a few big simple shapes
so=bpy.data.objects['Sumo']
import bmesh
bm=bmesh.new(); bm.from_mesh(so.data); n0=len(bm.verts); bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=0.0005); print('welded',n0,'->',len(bm.verts)); bm.to_mesh(so.data); bm.free()
so.data.shade_smooth()
cs=so.modifiers.new('soften','CORRECTIVE_SMOOTH'); cs.iterations=30; cs.factor=1.0; cs.rest_source='ORCO'; cs.smooth_type='LENGTH_WEIGHTED'
sm=so.modifiers.new('round','SMOOTH'); sm.factor=0.5; sm.iterations=6
print('palette cs',im.colorspace_settings.name)
s.cycles.samples=96
sun=bpy.data.objects['LGT_Sun'].data; import math; sun.angle=math.radians(5); s.cycles.use_denoising=True
s.view_settings.view_transform='Standard'; s.view_settings.look='None'; s.view_settings.exposure=0
s.render.image_settings.file_format='OPEN_EXR_MULTILAYER'; s.render.image_settings.color_depth='32'
s.render.filepath=out; bpy.ops.render.render(write_still=True)
