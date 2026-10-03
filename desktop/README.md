# Kumite desktop (Steam build)

The game in `../public`, wrapped in Electron so it runs as a normal Windows / Mac / Linux app.
GitHub builds it automatically (Actions → "Desktop builds") and attaches the zips to the run.

- `steam_appid.txt` holds 480 (Valve's test app, "Spacewar") until Kumite has its own Steam App ID; then put that number in.
- Settings: fullscreen is remembered; F11 or Alt+Enter toggles it.
- Online play and phone controllers use https://looktwicestudio.com/kumite.
