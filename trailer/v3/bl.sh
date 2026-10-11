#!/bin/bash
cd "$(dirname "$0")"
for s in "$@"; do node bosslive.js bl$s $s ${PAI:-easy} > ../log_bl$s.log 2>&1; done
