#!/bin/bash
cd "$(dirname "$0")"
LOG="'st'+F.take.st+' '+P.st+' hid'+!!P.hidden+' held'+!!P.held+' '+c.npcs.map((n,i)=>n.ko?i+'KO ':'').join('')" N=170 DIR=../frames3/ node run3.js cartko > ../logf_ck.log 2>&1
