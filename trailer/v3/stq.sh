#!/bin/bash
cd "$(dirname "$0")"
L="'st'+F.take.st+' '+P.st+' P'+P.x.toFixed(1)+','+P.z.toFixed(1)+' held'+(P.held?P.held.kind:'-')+' '+c.npcs.map((n,i)=>(n.ko?i+'KO ':'')+((n.mode!=='route'&&n.mode!=='return')?i+n.mode+' ':'')).join('')"
for tk in wake3 cartko vend3; do bash ../ens.sh; LOG="$L" DIR=../frames6/ node run3.js $tk > ../logf6_$tk.log 2>&1; echo "$tk $(tail -1 ../logf6_$tk.log)" >> ../stq.log; done
