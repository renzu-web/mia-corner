#!/usr/bin/env bash
# Cron entry point for the anime renders, so the work survives my session dropping.
#
# The renders are slow on CPU and twice died when the agent session was interrupted, even
# detached. A cron run happens in the scheduler's own process, and the render script skips
# any image already on disk, so this can be ticked repeatedly until the set is complete.
#
# Silent until there is something to say (the watchdog pattern): nothing prints while
# renders are still missing, and a one-line summary prints once they all exist.
set -uo pipefail

OUT=/workspace/mia-site/img/anime
WRAP=/workspace/mia-site/tools/render_anime.sh
LOG=$OUT/render.log

mkdir -p "$OUT"
"$WRAP" >/dev/null 2>&1

want=(mia_anime_a mia_anime_b mia_anime_c)
have=()
for n in "${want[@]}"; do [ -s "$OUT/$n.jpg" ] && have+=("$n"); done

if [ "${#have[@]}" -eq "${#want[@]}" ]; then
  echo "anime stills ready:"
  for n in "${want[@]}"; do
    echo "$OUT/$n.jpg ($(stat -c%s "$OUT/$n.jpg") bytes)"
  done
elif [ "${#have[@]}" -gt 0 ]; then
  echo "anime stills partly done: ${have[*]}"
fi
