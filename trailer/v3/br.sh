#!/bin/bash
cd "$(dirname "$0")"
for s in "$@"; do node boutrec.js br$s $s ${PAI:-normal} 600 > ../log_br$s.log 2>&1; done
