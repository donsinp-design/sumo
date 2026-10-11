#!/bin/bash
cd "$(dirname "$0")"
for j in "$@"; do set -- $(echo $j | tr ':' ' '); bash ../ens.sh; node botrec.js $1 $2 $3 700 > ../log_$1.log 2>&1; echo "$1 $(tail -1 ../log_$1.log)" >> ../botq.log; done
