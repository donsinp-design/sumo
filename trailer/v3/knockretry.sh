#!/bin/bash
cd "$(dirname "$0")"
L="'st'+F.take.st+' '+P.st+' H'+(P.hidden?1:0)+' '+c.npcs.map((n,i)=>((n.mode!=='route'&&n.mode!=='return')?i+n.mode+' ':'')).join('')"
for k in 1 2 3 4; do bash ../ens.sh; LOG="$L" SS=2 N=300 DIR=../frames7/ node run3.js knock2 > ../logf7_knock2.log 2>&1; grep -q chase ../frames7/knock2.log || { grep -q "goto\|search" ../frames7/knock2.log && break; }; done; echo "knock2 retry $k" >> ../ssq.log
