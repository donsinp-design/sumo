#!/bin/bash
cd "$(dirname "$0")"
for k in 1 2 3 4 5; do bash ../ens.sh; node gcap2.js bomb 200 > ../log_g5_bomb.log 2>&1; grep -A4 " boom " ../frames5/g5_bomb.log | grep -q "W0\|fall 1" && break; done; echo "bomb2 try $k" >> ../retry.log
