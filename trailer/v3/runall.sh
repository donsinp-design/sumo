#!/bin/bash
# usage: runall.sh mode "name seed start n" ...
mode=$1; shift
printf '%s\n' "$@" | xargs -P 3 -I{} sh -c 'set -- {}; node sumocap.js $1 $2 $3 $4 '$mode' > ../log_$1.log 2>&1'
