#!/bin/bash
cd "$(dirname "$0")"
for k in 1 2 3 4; do LOG="'st'+F.take.st+' '+P.st+' held'+(P.held?P.held.kind:'-')+' '+c.npcs.map((n,i)=>n.ko?i+'KO ':'').join('')" N=300 DIR=../frames5/ node run3.js vend2 > ../logf5_vend2.log 2>&1; grep -q KO ../frames5/vend2.log && break; done
