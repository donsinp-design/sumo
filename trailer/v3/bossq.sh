#!/bin/bash
cd "$(dirname "$0")"
for j in "bx13 13 normal 320" "bx27 27 normal 300" "bx17 17 normal 420" "bxR49 49 bossRematch 620" "bx28 28 normal 190" "bx1 1 normal 510"; do set -- $j; bash ../ens.sh; node boutrec.js $1 $2 $3 $4 > ../log_$1.log 2>&1; echo "$1 $(tail -1 ../log_$1.log)" >> ../bossq.log; done
