#!/bin/bash
# retry.sh SKILL N PATTERN : re-capture until the log matches
cd "$(dirname "$0")"
for k in 1 2 3 4; do bash ../ens.sh; node gcap2.js $1 $2 > ../log_g5_$1.log 2>&1; grep -qE "$3" ../frames5/g5_$1.log && break; done
echo "$1 done try $k" >> ../retry.log
