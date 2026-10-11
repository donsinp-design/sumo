#!/bin/bash
cd "$(dirname "$0")"; bash ../ens.sh
L2="'st'+F.take.st+' '+P.st+' held'+(P.held?P.held.kind:'-')"
LOG="$L2" SS=2 N=330 DIR=../frames9/ node run3.js vend3 2>&1 | tail -1
GOUT=../frames10/ ./gss.sh 'cyclone:120:cyclone' 'bumper:115:bump' 'triplets:70:skillUse' 'shock:65:bigStomp' 'rewind:150:rewind 0' 'spin:110:skillUse'; echo laneB done
