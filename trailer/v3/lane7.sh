#!/bin/bash
cd "$(dirname "$0")"
./les.sh final "m3_dodge|SIDESTEP|130" "m3_lift|LIFT|130" &
./les.sh final "m3_taunt|FACE-OFF|260" "m3_teeter|STAY IN|90"
wait
