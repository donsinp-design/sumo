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

## Showcase v5: what to make (owner's notes on v4)
Order, all real gameplay at the default camera, no HUD, cut to music/modena.ogg on the beat:
logo2_sharp (2.2 s) -> food rain (3 s, fade in/out) -> wake4 as ONE take (no jump cut; title overlay bbs2@2x fades in as he wakes)
-> a couple of seconds before knock2 (the knock must not look like it caused anyone's slip) -> knock2 -> shove2 -> follow9 (~7 s)
-> cartrun (double speed) -> cartko (he fights back, slap KO) -> chasemaw -> vend3 (drinks BOTH cans, keep through the burp)
-> gacha singles: ball, banana (red ring), shinkansen, giant, chicken, claw, inhale, potato, torpedo, belly flop, cyclone, bumper,
   triplets, shock stomp, rewind (fires the moment he's pushed out), + smoke bomb / controller disconnected / rotating ring for timing.
   NO molotov.
-> boss: short highlights only (no 30 s of fighting): dodge, catch, parry, tech, lift, edge save, throws (botrec bouts)
-> finale facecap: salt, clap, boss stomp, both charge; cut to COMING SOON on a strong beat just before they hit; music ends/fades there naturally.
Check every frame for flicker/freezes (strobe.py, mcflick.py) before sending.

## Showcase v5: how it was made (Oct 2026, Apple M5, GPU, SS=2)
- `lib.js` waits for the boot splash before a take starts (on a fast machine it landed mid-take: white frames, then food rain).
- The edit is `v5b/cut7.py` (cut6.py was the previous pass) -> `v5b/showcase_v5.mp4` (2:12). Frames: `v5/<take>` and the re-recorded `v5b/<take>`.
- Cuts snap to strong hits in the music (`v5b/onsets.json`). COMING SOON lands on the 2:08.9 hit, the last chord rings, then a short fade.
- Ring scenes (gacha, boss, finale) use the ring crop at 2x. Room scenes are the whole frame.
- Takes added: `knock8` (no puddle by the attendant, so the knock makes nobody slip), `vend4` (drinks both cans, burps).
- `v3/gcap5.js`: gcap2 that can also script the boss (hot potato tag chase, stomp from a distance), shows the CONTROLLER DISCONNECTED pop-up, and takes extra CSS (the rewind date is hidden).
- `v3/facecap5.js`: the finale with salt/clap/stomp moved 2.4 s later, so the boss's cage is off the ring first.
- The title overlay uses `v5b/title1280.png` (white under the transparent pixels, so no dark edges when scaled).
- Fourth pass (v5c): your cloud flicker fixes merged in (not committed), everything re-recorded. Edit: `v5b/cut8.py` -> `v5c/showcase_v5.mp4`.
  New takes: `wake5` (smoothed steering), `shove3` (2 s shove, pop, slap KO), `vend18` (footprints, smashed can, slip).
  `gcap5.js` plays `c_*` give each wrestler one skill (SK2 = the boss's; VIEW=1 shows the boss's view, used for the solid smoke).
  End cards: `v5c/bigger.png` on the 2:08.9 hit, `v5c/soon.png` on the 2:10.6 hit.
- Fifth pass: `v5b/cut9.py` -> `v5c/showcase_v5.mp4`. New takes: `shove4` (2 s counted only while pushing/sweating), `vend20`
  (tiptoes through the puddle; thumps only after the attendant is following the prints), `chargeko` (locker aisle charge,
  two KOs: a charge only flattens staff who haven't spotted him), `c_bumpflop3` (flop throws him into the straw, bumper bounces him back).
- Sixth pass: `v5b/cut10.py`. `wake6` (no walk back after the bucket, grabs it from a spot where no stool is in reach, weave on the stick),
  `chargeko2` (one charge, both down), `cartdive` (game change: diving into the cart you push keeps it rolling and throws laundry out),
  `potato3` (charge and dodge), inhale removed, finale cut on the collision frame.
- Laundry flies out of any cart he climbs into (stealth.js laundryOut; debris now animates even while he hides: flyStep at the top of step).

## Second showcase: Mura Masa - Lotus Eater
- `v5b/cut_lotus.py` -> `v5c/showcase_lotus.mp4` (2:12). Same v5c footage; the music is read from the owner's file
  (`~/Soulseek Downloads/04 Mura Masa - Lotus Eater.mp3`, not copied into the repo). Hits in `v5b/lotus_onsets.json`.
- 96.8 BPM. Intro: logo, food rain, asleep; startle on the 12.85 s beat; the bath-to-locker take fills the first full section;
  room scenes (no box-follow) in the break; gacha from the 80.86 s hit; finale collides on 126.07 (BIGGER IS BETTER); COMING SOON 128.81.
- Beat-locked version: `v5b/cut_lotus2.py` (replaces cut_lotus.py's output). `wake7` = wake6 with `sync` steps (song time, startle at 12.85)
  so charge-out 16.8, bucket 21.8, slip 26.5, charge 32.3, stool 38.6 and the locker rattle 54.7 land on beats; `vend21` thumps once a beat,
  crash on the 79.62 drop. Every clip's main event is placed on a beat and every cut is on a beat; nothing from the Vivaldi cut is left out.
