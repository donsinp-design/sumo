#!/bin/bash
cd "$(dirname "$0")"
for s in "$@"; do node gcap.js $s 7 150 8 > ../log_g2_$s.log 2>&1; done
