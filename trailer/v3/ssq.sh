#!/bin/bash
cd "$(dirname "$0")"
L="'st'+F.take.st+' '+P.st+' P'+P.x.toFixed(1)+','+P.z.toFixed(1)+' H'+(P.hidden?1:0)+(P.boxHide?'B':'')+' held'+(P.held?P.held.kind:'-')+' '+c.npcs.map((n,i)=>(n.ko?i+'KO ':'')+(n.shock>0?i+'SHOCK ':'')+((n.mode!=='route'&&n.mode!=='return')?i+n.mode+' ':'')).join('')"
for j in "$@"; do set -- $(echo $j | tr ':' ' '); bash ../ens.sh; LOG="$L" SS=2 N=$2 DIR=../frames7/ node run3.js $1 > ../logf7_$1.log 2>&1; echo "$1 $(tail -1 ../logf7_$1.log)" >> ../ssq.log; done
