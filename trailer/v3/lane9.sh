#!/bin/bash
cd "$(dirname "$0")"
./les.sh final "m3_spin|SPIN|215" "m3_slapdown|SLAP DOWN|215" &
./les.sh final "m3_catch|CATCH|215" "m3_trip|LEG TRIP|200" &
(node gcap2.js train 220 > ../log_g3_train.log 2>&1; node gcap2.js bumper 210 > ../log_g3_bumper.log 2>&1) &
(node gcap2.js triplets 190 > ../log_g3_triplets.log 2>&1; node gcap2.js chicken 190 > ../log_g3_chicken.log 2>&1)
wait
