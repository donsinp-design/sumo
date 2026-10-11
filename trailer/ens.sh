#!/bin/bash
# make sure the local game server is up (serves the repo root on :8896)
curl -s -o /dev/null -m 2 http://127.0.0.1:8896/dist-kumitegame/index.html && exit 0
cd "$(dirname "$0")/.." && (nohup python3 -m http.server 8896 >/dev/null 2>&1 &)
for i in $(seq 1 20); do sleep 0.5; curl -s -o /dev/null -m 2 http://127.0.0.1:8896/dist-kumitegame/index.html && exit 0; done; exit 1
