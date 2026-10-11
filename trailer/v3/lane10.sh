#!/bin/bash
cd "$(dirname "$0")"
export DIR=../frames4/
r(){ LOG="'st'+F.take.st+' '+P.st+' '+c.npcs.map((n,i)=>n.ko?i+'KO ':n.a.st==='down'?i+(n.a.slipFall?'SLIP ':'down '):n.shock>0?i+'SHOCK ':'').join('')+(c.vend?' hits'+c.vend.hits:'')" N=$2 node run3.js $1 > ../logf4_$1.log 2>&1; }
case $1 in
 a) r wake 210; r boxsneak 150; r shovesurp 170;;
 b) r cartko 170; r chasemaw 215;;
 c) r vend 170; r chargelock 150;;
esac
