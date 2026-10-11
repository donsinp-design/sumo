#!/bin/bash
cd "$(dirname "$0")"; bash ../ens.sh
L="'i'+F.take.i+' '+(F.take.q&&F.take.q[F.take.i]?F.take.q[F.take.i][0]:'-')+' '+P.st+' P'+P.x.toFixed(1)+','+P.z.toFixed(1)+' '+c.stage"
LOG="$L" SS=2 N=1500 DIR=../frames9/ node run3.js wake4 2>&1 | tail -1
