#!/bin/bash
# record the campaign-gacha takes into v5c, four at a time
cd "$(dirname "$0")"
LOGX="(c.gs?c.gs.id:'-')+' d'+c.npcs.filter(n=>n.a.st==='down'||n.pit>0||n.eaten).length+' '+P.st+(c.gm&&c.gm.used?' used':'')+(c.rew?' rew':'')"
run(){ DIR=../v5c/ LOG="$LOGX" node run3.js "$1" > ../v5c/"$1".run.txt 2>&1; }
for set in "ghands gbomb gstomp gdaruma" "ggiant gphantom gtorpedo"; do
  for t in $set; do run $t & done; wait
done
echo ALLDONE
