#!/bin/bash
cd "$(dirname "$0")"
while kill -0 10792 2>/dev/null; do sleep 5; done
export DIR=../frames2/
LOG="'st'+F.take.st+' '+P.st+' brk'+c.breakables.filter(B=>B.done).length+' pud'+c.puddles.length+' '+c.npcs.map((n,i)=>n.ko?i+'KO ':n.a.st==='down'?i+'down ':n.shock>0?i+'SHOCK ':'').join('')" N=215 node run3.js chaseslip > ../logf2_chaseslip.log 2>&1
LOG="'st'+F.take.st+' '+P.st+' brk'+c.breakables.filter(B=>B.done).length+' '+c.npcs.map((n,i)=>n.ko?i+'KO ':n.a.st==='down'?i+'down ':'').join('')" N=150 node run3.js chargelock > ../logf2_chargelock.log 2>&1
LOG="P.x.toFixed(1)" N=150 node run3.js boxsneak > ../logf2_boxsneak.log 2>&1
