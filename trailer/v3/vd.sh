#!/bin/bash
cd "$(dirname "$0")"
while pgrep -f "run3.js cartko" >/dev/null; do sleep 5; done
LOG="'st'+F.take.st+' hits'+c.vend.hits+' broke'+c.vend.broke" N=170 DIR=../frames3/ node run3.js vend > ../logf_vd.log 2>&1
