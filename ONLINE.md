# Playing Kumite online

## 1. Test on your own Mac (free, no account)

In Terminal, inside the `hakkeyoi` folder:

```bash
npm start
```

Open http://localhost:8732 in two browser windows.
Window 1: ONLINE LOBBY → CREATE ROOM. Note the 4-letter code.
Window 2: ONLINE LOBBY → JOIN ROOM → type the code, press Enter.
The host (★) presses Enter to start. Open more windows to watch; winner stays on.

## 2. Play a friend somewhere else (free, temporary link)

Keep the server from step 1 running. Install Cloudflare's tunnel tool once:

```bash
brew install cloudflared
```

Then:

```bash
cloudflared tunnel --url http://localhost:8732
```

It prints a link like `https://something.trycloudflare.com`. Send it to your friend.
The link works until you close that Terminal window.

## 3. Put it online for good (free Cloudflare account)

1. Make a free account at cloudflare.com.
2. In the `hakkeyoi` folder:

```bash
npx wrangler login
```

```bash
npx wrangler deploy
```

It prints your permanent address, like `https://kumite.<your-name>.workers.dev`.
Run `npx wrangler deploy` again whenever the game changes.

Notes
- Online bouts use Pure rules.
- Best in the same browser on both ends (Chrome). A built-in check repairs small differences if they appear.
