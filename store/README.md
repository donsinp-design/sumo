# Kumite: store page kit

Images in this folder:
- `cover-630x500.png`: itch.io cover image
- `capsule-460x215.png`: small banner (Steam "header capsule" size, also handy for Game Jolt / Newgrounds icons)
- `banner-1920x1080.png`: wide banner / page background
- `screenshot-1` … `screenshot-6`: gameplay, 1280×720, one per stage

## Short description (one line)

Sumo, but chaotic. Shove, grab, throw and trip your rival out of the ring on a pizza, a DJ turntable or a flat earth.

## Description

**Kumite** is a fast, physical sumo fighting game. Two wrestlers, one ring: push them out, or put anything but the soles of their feet on the floor.

- **Real sumo moves:** open-hand slaps, charges, grips, belt throws, leg trips, lifts, edge saves and the wooden-clapper face-off.
- **Easy to pick up, deep to master:** a full tutorial with timing cues teaches every move and its counter.
- **A CPU that learns:** it remembers your habits, fakes its charges and punishes spam.
- **Play together:** local versus on one keyboard or two controllers (PS5 and Xbox pads work), phones as controllers by scanning a QR code, or online with Quick Match (skill-based) and private rooms.
- **Gacha mode:** each round both wrestlers draw a random one-shot skill: a molotov, a claw machine, a chicken transformation and many more.
- **14 stages:** the classic dohyo, a sushi train, a birthday cake, a pizza, a DJ vinyl, a flat earth and more.

Controls: keyboard (W A S D + J K L), any game controller, touch, or your phone.

## Tags

Fighting, Sports, Local Multiplayer, Online Multiplayer, Physics, Funny, Party, Sumo, Japan, Casual

## Where to upload

| Store | What to upload | Notes |
|---|---|---|
| **itch.io** | Everything (the "itch.io release" workflow does it) | Kind of project: HTML. Embed: "Click to launch in fullscreen" off, viewport 1280×720, check "Mobile friendly" (landscape) and "Fullscreen button". Free or pay-what-you-want with a minimum. |
| **Newgrounds** | `Kumite-web.zip` | Upload as HTML5 game, 1280×720. |
| **Game Jolt** | `Kumite-web.zip` (browser) + the desktop zips | Browser build: HTML, 1280×720. |
| **CrazyGames** | `Kumite-web.zip` | Free to submit at developer.crazygames.com. They review it, and revenue is from ads (shared with you). |
| **Poki** | Apply at developers.poki.com | Invite-based; they integrate their own ad SDK. |
| **Google Play** | `Kumite.aab` from "Android build" | One-time $25 developer account. Needs the signing secrets (see the workflow). |
| **App Store** | "iOS release" workflow → TestFlight | Apple Developer Program. |
| **Steam** | Desktop zips | Steamworks, $100 per game. |

`Kumite-web.zip` and the desktop zips are attached to every "Desktop builds" run (Actions tab → Desktop builds → latest run → Artifacts).
