#!/bin/bash
cd "$(dirname "$0")"
node gcap2.js torpedo 100 > ../log_g3_torpedo.log 2>&1
node gcap2.js potato 230 > ../log_g3_potato.log 2>&1
