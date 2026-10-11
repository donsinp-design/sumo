#!/bin/bash
cd "$(dirname "$0")"
while pgrep -f stq2.sh >/dev/null; do sleep 20; done
L="'st'+F.take.st+' '+P.st+' H'+(P.hidden?1:0)"
bash ../ens.sh; LOG="$L" N=300 DIR=../frames6/ node run3.js knock2 > ../logf6_knock2.log 2>&1; echo "knock2 $(tail -1 ../logf6_knock2.log)" >> ../stq.log
