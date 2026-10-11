#!/bin/bash
# queue.sh JOBFILE LANES : runs each line of JOBFILE (a shell command) with up to LANES at once; a line is skipped if its marker file exists
cd "$(dirname "$0")"
jobs_file=$1; lanes=${2:-3}
while IFS= read -r line; do
  [ -z "$line" ] && continue
  mk=$(echo "$line" | cut -d'#' -f2 | tr -d ' ')
  cmd=$(echo "$line" | cut -d'#' -f1)
  [ -n "$mk" ] && [ -f "../done/$mk" ] && continue
  while [ "$(jobs -rp | wc -l)" -ge "$lanes" ]; do sleep 3; done
  ( eval "$cmd" && [ -n "$mk" ] && touch "../done/$mk" ) &
done < "$jobs_file"
wait
