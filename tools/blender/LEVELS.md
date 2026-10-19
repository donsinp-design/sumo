# Making a level

Every level past the bathhouse is ONE Python script, `tools/blender/lv_<id>.py`, built with the shared toolbox
`tools/blender/levelkit.py`. The script makes the art AND the floor plan together, so the game's colliders always sit
exactly on the art. `tools/blender/lv_shibuya.py` is the worked example: read it first and copy its patterns.

```
blender -b -P tools/blender/lv_<id>.py        # -> public/assets/models/lv_<id>.glb + public/js/levels/<id>.js
node tools/level-test.js <id> <outdir> --map  # an overhead plan of the whole level (check the layout)
node tools/level-test.js <id> <outdir> --run 20 x z yaw x z yaw ...       # top-down shots where P1 stands
node tools/level-test.js <id> <outdir> --fpv x z yaw ...                  # third-person shots (yaw -1.57 = facing -z)
node tools/level-test.js <id> <outdir> --mode hide --run 60               # hide & seek, the computer plays P2
```
(A static server must be running at the repo root on port 8896: `python3 -m http.server 8896`.)
The level's script tag (`<script src="js/levels/<id>.js">`) is already in `public/index.html`.

## The game, in short
"Big Booty Sumo": a naked sumo with a huge booty has lost his mawashi. Third-person / top-down stealth comedy. He walks,
runs (SHIFT, loud), BELLY SLIDES (L: flat on his belly; long on wet or icy floors, short on dry ones, speeds up downhill),
pushes (J tap), BOOTY SLAMS (J hold), uses things (K), hides (I) in carts and fixed hiding places (his booty pokes out of
the hiding place, which is the joke). Staff patrol, see in a cone, chase, grab and hold; the other player pushes them off.
Party modes on every level: CO-OP HEIST (find your mawashi, get out the exit), HIDE & SEEK, PANTS TAG.

## Coordinates and scale
GAME coordinates: x right, z towards the camera (the default top-down camera looks from +z, high, ~50 degrees down), y
up, metres. The sumo is ~2 m tall and ~1.4 m wide: corridors at least 2.2 m, doors at least 1.8 m. Keep a level within
about 70 x 70 m (bigger is fine if it's worth it, e.g. a pitch). ONE walkable layer: floors at any height, slopes, but
never a floor above another floor (no walkable upper storeys; upstairs is art only, in UPPER).

## The art: "ZZZ / Orbitals" look
Zenless Zone Zero meets the game Orbitals: a 90s TV-anime cel look. Flat matte colour, one hard-edged shadow per surface
(the game's light does that), a muted low-key palette (slate, charcoal, navy-grey, teal, ochre, rust, cream) with a few
small warm lamps and, where it fits, neon. Chunky simple shapes with real detail: the bathhouse has every tap, bottle,
locker number and towel; a level should be AS DETAILED OR MORE. No black outlines, no gloss, no photo textures. Only the
palette swatches in levelkit.py (`PAL`); `neon_*`, `screen` and `lamp` are drawn unlit (they glow), glass/water are
see-through. Lettering: Japanese only (`GB.text`), sparingly. Fill rooms: props, clutter, signage, life.

## The toolbox (levelkit.py)
```
LV = Level(id, 'NAME', '日本語', 'one-line blurb'); L = LV.L
LV.bounds(x0, x1, z0, z1)                  # the playable area (an invisible wall round it)
LV.wall(x0, x1, z0, z1, h, col, trim, base) # a full-height wall: collider; lower 1.15 m in BASE, the rest in UPPER
LV.solid(k, x0, x1, z0, z1, h, tall, draw)  # any collider (furniture...). tall=True blocks sight. draw: a colour-less
                                            # plain box, or a function f(m, x0, x1, z0, z1, h) that builds it
LV.blocker(x, z, r)                          # a round collider (a tree, a pillar, a bin)
LV.room(id, name, x0, x1, z0, z1, safe=False)# named areas (noise and the story use them)
LV.floor(x0, x1, z0, z1, y) / LV.slope(x0, x1, z0, z1, 'x'|'z', y0, y1)    # floor heights (y0 at the low-coordinate end)
LV.wet(...) / LV.ice(...)                    # floors the belly slide runs far on (fish market floors, snow, a stage)
LV.conveyor(x0, x1, z0, z1, vx, vz)          # carries him along (the ski travelator)
LV.cart(x, z, r)                             # a cart he can push and hide in (the kit's ITEM_CART proto)
LV.hide(k, x, z, out, by, label)             # a fixed hiding place: he stands at (x, z) inside it, steps out at `out`;
                                             # by = height his booty pokes out at (None: hidden completely)
LV.base / LV.upper                           # GB builders: BASE (always shown) / UPPER (third person only: ceilings,
                                             # the upper parts of walls, building storeys above, things overhead)
LV.proto('ITEM_CART') / LV.proto('MOVER_<K>') / LV.proto('ITEM_BALL')   # prototypes the game clones (built at the origin)
LV.export()                                  # writes the glb and the layout js (call last)
```
GB methods take GAME coordinates: `gbox(x0,x1,z0,z1,y0,y1,col,bev)`, `gboxr(cx,cz,w,d,y0,y1,ry,col)`, `gcyl(x,z,y,r,h,col)`
(y = bottom; axis 'X'/'Y' lies it down, then y is its centre), `gico(x,z,y,r,col,sq=(sx,sz,sy))`, `gprism(pts,y0,y1,col)`,
`ramp(...)`, `sign(x,y,z,w,h,col,face)` (a flat panel 6 mm off a surface: '+z','-z','+x','-x','up'), `vquad`, `text`.
Top-down view: the camera looks down at ~50 degrees from +z. Walls are cut at 1.15 m (like the bathhouse) so it sees into
rooms; tall furniture (shelves, machines) stays full height in BASE but keep it under ~2.5 m so it doesn't hide too much.

## The layout dict (L): what the game reads
- `start` [[x,z],[x,z]] the two players' start; `maw` 8 mawashi spots (co-op), all reachable, spread over the level;
  `exit` {x, z, name}; `pants` [x,z] (pants tag); `hider` / `seeker` [x,z] (hide & seek starts, a few metres apart);
  `seekerName` (who seeks: 'fishmonger'...), `hideList` (a short list of where to hide, for the title card).
- `staffN` (default 5), `staffZone` {x0,x1,z0,z1} (where staff start; keep them away from the start).
- `pool` {x0,x1,z0,z1, water: y of the surface, floor: y he stands at, spots: [[x,z]...] places to duck under, via: [x,z]
  the way in (the steps)} (optional: water to hide under, like the bath).
- `movers` [{k, path:[[x,z]...], v, r, w, d, stops:[i...], stopT, hit:'RUN OVER!'}]: drives its path (loops), knocks
  over anyone it touches. The kit's `MOVER_<K>` proto is its look (length along +x).
- `traps` [{a:[x,z], b:[x,z], label}]: K at one end pops him out the other (a trapdoor, a manhole, the kabuki suppon lift).
- `crowd` [{path:[[x,z]...], n, v, w}]: people walking a loop (w: the band's width). Two or more round him: he's hidden.
- `ball` [x,z] and `goals` [{x0,x1,z0,z1}]: a ball he can push / slide into; into a goal: GOAL!
- `lights` [{x, z, r, col:'#hex', a}] (optional): soft pools of lamp light on the floor (night levels).
- `style` {sky:'#hex', lit:[r,g,b], shade:[r,g,b], lo, hi, form, lift}: the cel light. lit = sunlit tint, shade = the
  shadow tint (cool, ~0.4-0.6), lo/hi the hard edge (~0.30/0.33), form 0.05. Shibuya (night) is the reference.
- `ring` {x, z}: where the boss's dohyo appears (story).
- `story`: the level's own run (see below).

## The story (L['story'])
The sumo has lost his mawashi here, a chain of 4-7 steps leads to it, a boss sumo has it, a bout, then out:
```
L['story'] = dict(
  start=[x, z, yaw],
  intro=[dict(who='', jp='…', en='...'), ...],          # his opening thoughts (2-3 lines, funny)
  steps=[dict(obj='Objective text shown on screen', at=[x, z], r=1.6, do='goto'|'use'|'slam'|'hide',
              think='his thought when the step starts', say=[lines when done], prop='ITEM_<X>' (optional: a proto shown at `at`
              until done), open=k (optional: index into L['solids'] of a blockage that disappears when done)), ...],
  boss=dict(name='NAME', jp='名前', at=[x, z], belt='#hex', intro=[lines], lost=[lines], won=[lines]),
  exit=[x, z],                                           # after the boss: get out here
)
```
Lines are dict(who='名前' or '', jp='日本語', en='English'). Funny, dry, short (the bathhouse boss: "By the way. That
thing on your back... 'HALF-PRICE TOFU'?" / "...I asked for 'INVINCIBLE'.").

## Rules
- Only touch your own files: `tools/blender/lv_<id>.py` and what it generates (`public/assets/models/lv_<id>.glb`,
  `public/js/levels/<id>.js`). Don't edit levelkit.py, the engine, index.html or other levels: if the engine needs
  something, say so in your report. Don't commit.
- Check with --map and with a dozen third-person and top-down shots in every area; fix what looks wrong (floating
  things, z-fighting faces, gaps in walls, props through walls, unreachable spots). Run `--run 60` in each mode and make
  sure the computer player gets round (no spot it can't reach, nobody stuck).
- In a `draw=lambda m, x0, x1, z0, z1, h: (...)` keep it to expressions. Don't leave `if False else` junk.
