#!/bin/bash
cd "$(dirname "$0")"
while [ "$(pgrep -fc 'node (lescap|run3|gcap)')" -ge 3 ]; do sleep 5; done
for a in "$@"; do IFS='|' read s n <<< "$a"; node gcap2.js $s $n > ../log_g3_$s.log 2>&1; done
