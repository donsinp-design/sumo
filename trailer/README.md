# Trailer / showcase capture tooling (Big Boy Sumo)

Records real gameplay frame by frame with Playwright at the game's own camera, then cuts with ffmpeg.
Meant to be run by Claude Code on a machine with a GPU (much faster than the cloud container's software renderer).

Setup (once): `npm i playwright && npx playwright install chromium`, ffmpeg and python3 + Pillow installed.
Build the game first: `node tools/build-fork.js` (writes dist-kumitegame). `trailer/ens.sh` serves the repo on :8896.
On a machine without a GPU set `SWGL=1` (swiftshader) and use `SS=2` (2x supersample) against edge flicker.

- `v3/run3.js TAKE [preview]` stealth takes from `v3/takes.js` (env: LOG=js-expr per frame, N=frames, DIR=out dir, SS=2)
  Showcase v5 takes: wake4 (intro, N=1500), knock2 (300), shove2 (160), follow9 (420), cartrun (200), cartko (200), vend3 (330)
- `v3/gcap2.js SKILL N` gacha shot in a boss bout (env OUT=dir, SS); `v3/gss.sh "skill:frames:logRegex" ...` retries until the log matches
- `v3/botrec.js NAME SEED PLAN` real boss bout, player bot answering with planned moves (dodge,wait,parry,catch,tech,lift,spin,trip,slam,save)
- `v3/facecap.js NAME SEED` finale: salt, clap, boss stomp, both charge (CONTACT frame in the log)
- `cut.py OUT "dir:start:count[:fadeIn:fadeOut:color]" ... card=PNG:0:frames` concatenates at 30 fps
- `strobe.py` / `mcflick.py` flicker finders; `cards/` logo + COMING SOON + title overlay (bbs2@2x.png, white, no border)
- Music: `music/modena.ogg` = The Modena Chamber Orchestra, Vivaldi Summer RV 315 III Presto (Musopen, public domain). Big hit at 8.0 s.
