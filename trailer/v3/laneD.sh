#!/bin/bash
cd "$(dirname "$0")"; bash ../ens.sh
SS=2 OUT=../frames10/ ./botq.sh sb1:21:dodge,wait,lift sb5:19:dodge,lift,parry sb4:24:dodge,spin,parry; echo laneD done
