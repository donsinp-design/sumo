#!/bin/bash
cd "$(dirname "$0")"
LOG="'st'+F.take.st+' '+c.npcs.map((n,i)=>(n.shock>0?i+'SHOCK y'+n.a.y.toFixed(2)+' ':'')+(n.mode==='chase'?i+'chase ':'')).join('')" DIR=../frames2/ N=170 node run3.js shovesurp > ../logf_ss.log 2>&1
