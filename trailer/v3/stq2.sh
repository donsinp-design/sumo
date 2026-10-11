#!/bin/bash
cd "$(dirname "$0")"
L="'st'+F.take.st+' '+P.st+' P'+P.x.toFixed(1)+','+P.z.toFixed(1)+' '+c.npcs.map((n,i)=>(n.shock>0?i+'SHOCK ':'')+((n.mode!=='route'&&n.mode!=='return')?i+n.mode+' ':'')).join('')"
bash ../ens.sh; LOG="$L" N=160 DIR=../frames6/ node run3.js shove2 > ../logf6_shove2.log 2>&1; echo "shove2 $(tail -1 ../logf6_shove2.log)" >> ../stq.log
bash ../ens.sh; LOG="$L" N=180 DIR=../frames6/ node run3.js cartrun > ../logf6_cartrun.log 2>&1; echo "cartrun $(tail -1 ../logf6_cartrun.log)" >> ../stq.log
