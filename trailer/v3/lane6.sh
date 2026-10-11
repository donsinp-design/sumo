#!/bin/bash
cd "$(dirname "$0")"
while [ "$(pgrep -fc 'node (lescap|run3|gcap)')" -ge 4 ]; do sleep 5; done
./les.sh final "m3_slam|SLAM|110" "m3_brace|BRACE|130" "m3_trip|LEG TRIP|130" "m3_throat|THROAT PUSH|90"
