#!/bin/bash
cd "$(dirname "$0")"
for j in "$@"; do set -- $(echo $j | tr ',' ' '); bash ../ens.sh; node boutrec.js $1 $2 $3 900 > ../log_$1.log 2>&1; echo "$1 $(tail -1 ../log_$1.log)" >> ../bossq2.log; done
