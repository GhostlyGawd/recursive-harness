#!/usr/bin/env bash
# statusline-command.sh — renders the fleet HUD (context % + 5h/7d rate-limit usage) from the
# statusline JSON on stdin. Portable: hardcodes no paths. provenance: session 56295237, 2026-06-13.
input=$(cat)

# --- Context window ---
ctx_used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
ctx_total=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0')
ctx_size=$(echo "$input"  | jq -r '.context_window.context_window_size // 0')

# --- Rate limits ---
five_h=$(echo "$input"  | jq -r '.rate_limits.five_hour.used_percentage  // empty')
seven_d=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage  // empty')

parts=()

# Context: "Ctx 42% (84k/200k)" — require numeric inputs so the awk math can't error
if [ -n "$ctx_used" ] && [[ "$ctx_size" =~ ^[0-9]+$ ]] && [ "$ctx_size" -gt 0 ] && [[ "$ctx_total" =~ ^[0-9]+$ ]]; then
  ctx_k=$(awk "BEGIN { printf \"%.0f\", $ctx_total / 1000 }")
  ctx_size_k=$(awk "BEGIN { printf \"%.0f\", $ctx_size / 1000 }")
  parts+=("$(printf '\033[36mCtx\033[0m \033[1m%.0f%%\033[0m (%sk/%sk)' "$ctx_used" "$ctx_k" "$ctx_size_k")")
fi

# Rate limits: "5h 12% | 7d 34%"
rate_parts=()
[ -n "$five_h"  ] && rate_parts+=("$(printf '5h \033[1m%.0f%%\033[0m' "$five_h")")
[ -n "$seven_d" ] && rate_parts+=("$(printf '7d \033[1m%.0f%%\033[0m' "$seven_d")")

if [ ${#rate_parts[@]} -gt 0 ]; then
  rate_str="${rate_parts[0]}"
  for r in "${rate_parts[@]:1}"; do rate_str="$rate_str | $r"; done
  parts+=("$(printf '\033[33mLimits\033[0m %s' "$rate_str")")
fi

# Render — separator "  ·  " between sections
if [ ${#parts[@]} -gt 0 ]; then
  out="${parts[0]}"
  for p in "${parts[@]:1}"; do out="$out  ·  $p"; done
  printf '%b\n' "$out"
fi
