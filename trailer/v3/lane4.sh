#!/bin/bash
cd "$(dirname "$0")"
while pgrep -f "run3.js chasemaw" >/dev/null; do sleep 5; done
./gall.sh ball chicken invis
