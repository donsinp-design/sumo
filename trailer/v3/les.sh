#!/bin/bash
# les.sh mode "name|TITLE|N" ...
cd "$(dirname "$0")"; mode=$1; shift
for a in "$@"; do IFS='|' read n t c <<< "$a"; node lescap.js "$n" "$t" "$c" $mode > ../log_$n.log 2>&1; done
