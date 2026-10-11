#!/bin/bash
cd "$(dirname "$0")"
LOG="'st'+F.take.st+' P '+P.x.toFixed(1)+' '+P.st+' pud'+c.puddles.length+' '+c.npcs.map((n,i)=>n.a.st==='down'?i+(n.a.slipFall?'SLIP ':'down '):'').join('')" N=215 DIR=../frames3/ node run3.js chasemaw > ../logf_cm.log 2>&1
