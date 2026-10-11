#!/bin/bash
cd "$(dirname "$0")"
for k in 1 2 3; do LOG="'st'+F.take.st+' '+P.st+' brk'+c.breakables.filter(B=>B.done).length+' '+c.npcs.map((n,i)=>n.ko?i+'KO ':'').join('')" N=150 DIR=../frames4/ node run3.js chargelock > ../logf4_chargelock.log 2>&1; grep -q KO ../frames4/chargelock.log && break; done
