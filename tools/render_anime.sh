#!/usr/bin/env bash
# Render anime-style versions of Mia from the owner-approved photos, free and offline.
#
# Slow on CPU (minutes per image) and the agent turn can be interrupted mid-render, so this
# runs as its own process with a log file rather than inline. Re-run it freely: each render
# is skipped if its output already exists.
set -uo pipefail

PY=/workspace/pausia/tools/.venv-st/bin/python
SCRIPT=/home/hermes/.hermes/skills/creative/ai-character-persona/scripts/make_portrait.py
OUT=/workspace/mia-site/img/anime
REF=/home/hermes/.hermes/mia/references
LOG=$OUT/render.log

export HF_HOME=/home/hermes/.cache/huggingface
mkdir -p "$OUT"

say() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

render() {  # render <name> <strength> <seed> <ref|-> <prompt>
  local name="$1" strength="$2" seed="$3" ref="$4" prompt="$5"
  local file="$OUT/$name.jpg"
  if [ -s "$file" ]; then say "skip $name (already rendered)"; return 0; fi
  say "start $name strength=$strength seed=$seed ref=$(basename "$ref")"
  local args=(--prompt "$prompt" --strength "$strength" --steps 3 --size 512
              --seed "$seed" --out "$file")
  if [ "$ref" != "-" ]; then args+=(--init "$ref"); fi
  if "$PY" "$SCRIPT" "${args[@]}" >>"$LOG" 2>&1; then
    say "done $name $(stat -c%s "$file") bytes"
  else
    say "FAILED $name (see the log above)"
  fi
}

A="anime style illustration, cel shaded, oversized charcoal hoodie, long black wavy hair with wispy bangs, large dark almond eyes, pale skin, plain dark background, moody soft lighting, clean line art, vtuber character design"
B="anime style illustration, cel shaded, black over ear gaming headset, oversized charcoal hoodie, long black wavy hair, wispy bangs, dark almond eyes, pale skin, plain near black background, dim moody lighting, clean line art, vtuber character design"
C="anime style illustration, cel shaded, cream knit cardigan, long black wavy hair, wispy bangs, dark almond eyes, pale skin, soft diffused daylight, plain warm background, clean line art, vtuber character design"

render mia_anime_a 0.60 23 "$REF/img_832e8ca97fcb.jpg" "$A"
render mia_anime_b 0.55 7  "$REF/img_d2663a408c9c.jpg" "$B"
render mia_anime_c 0.55 41 "$REF/img_832e8ca97fcb.jpg" "$C"

say "finished. files:"
ls -la "$OUT"/*.jpg >>"$LOG" 2>&1
say "$(ls "$OUT"/*.jpg 2>/dev/null | wc -l) jpg files in $OUT"
