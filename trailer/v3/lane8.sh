#!/bin/bash
cd "$(dirname "$0")"
for k in 1 2 3 4; do node lescap.js m3_brace BRACE 130 > ../log_m3_brace.log 2>&1; grep -q braceCounter ../frames3/m3_brace.log && break; done
