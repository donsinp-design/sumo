# Option 2 — flat KKBC look (same map as option 1)

Option-1 segment, re-lit flat: albedo stays flat, the sun only decides lit vs. shadow (soft edge),
shadows are a lilac tint, light AO, lighter warm road greys, grey-violet wires, sumo mesh welded and smoothed.

    python tools/blender/kkbc_flat_render.py art/option1/segment_kkbc.blend CAM_Game_Original out.exr
    python tools/blender/kkbc_flat_comp.py out.exr out.png exp=1.2 shdk=1.1
