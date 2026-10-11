#!/bin/bash
cd "$(dirname "$0")"; bash ../ens.sh
GOUT=../frames10/ ./gss.sh "train:115:trainHit 1" "giant:120:skillUse" "chicken:100:skillUse" "claw:155:clawDrop" "inhale:80:spit" "potato:80:potatoPass" "smoke:110:skillUse" "unplug:110:skillUse"; echo laneC done
