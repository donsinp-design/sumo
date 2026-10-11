#!/bin/bash
# gss.sh "skill:frames:pattern" ... : supersampled gacha captures into frames8, retried until the log matches
cd "$(dirname "$0")"
for j in "$@"; do IFS=: read s n pat <<< "$j"; for k in 1 2 3 4; do bash ../ens.sh; SS=2 OUT=${GOUT:-../frames8/} node gcap2.js $s $n > ../log_g8_$s.log 2>&1; grep -qE "$pat" ${GOUT:-../frames8/}g5_$s.log && break; done; echo "$s try $k" >> ../gss.log; done
