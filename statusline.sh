#!/bin/bash
# Claude Code statusline — Nerd Font powerline segments on the Grass remix palette
# Segments: model (mango) > cwd (butter) > git branch (deep green)
# Then, on plain background: rate-limit quota, then the context meter.
# Both meters recolor green > mango > coral as they fill.
#
# Quota reads .rate_limits from stdin, so there is no token, network, or cache.
# Each limit shows its percentage and when it resets, in local wall-clock time.
# ▲N means N points spent ahead of even pacing for that window; it appears only
# when overspending, so a quiet line means nothing needs attention. An earlier
# version drew small bars here, but at 5 cells the fill edge and the pace mark
# collided into noise and the empty cells stranded each number from its bar.
#
# This runs on every render, so it forks as little as possible: colors are
# precomputed strings, and all arithmetic folds into the single jq pass or
# plain shell integer math.

# ${#var} counts bytes under LC_ALL=C, which would corrupt the width estimates
# below (▰ is 3 bytes). Force a UTF-8 ctype so it counts characters instead.
unset LC_ALL
export LC_CTYPE=UTF-8

eval "$(jq -r '
. as $i
| (($i.context_window.current_usage // {}) | (.input_tokens//0)+(.cache_creation_input_tokens//0)+(.cache_read_input_tokens//0)+(.output_tokens//0)) as $t
| (if $t <= 0 then "" elif $t >= 1000 then " (\((($t/1000)|round))k)" else " (\($t))" end) as $tok
| @sh "model=\($i.model.display_name // "Claude") dir=\($i.workspace.current_dir // $i.cwd // ".") p=\((($i.context_window.used_percentage // 0)|round)) tokens=\($tok) h5_pct=\((($i.rate_limits.five_hour.used_percentage // -1)|round)) h5_reset=\($i.rate_limits.five_hour.resets_at // 0) d7_pct=\((($i.rate_limits.seven_day.used_percentage // -1)|round)) d7_reset=\($i.rate_limits.seven_day.resets_at // 0)"
')"

R=$'\033[0m'
FG_MANGO=$'\033[38;2;255;180;84m'   BG_MANGO=$'\033[48;2;255;180;84m'
FG_BUTTER=$'\033[38;2;255;240;165m' BG_BUTTER=$'\033[48;2;255;240;165m'
FG_DEEP=$'\033[38;2;10;61;31m'      BG_DEEP=$'\033[48;2;10;61;31m'
FG_INK=$'\033[38;2;24;40;24m'
FG_TEAL=$'\033[38;2;53;224;208m'
FG_CORAL=$'\033[38;2;255;92;138m'
FG_GREEN=$'\033[38;2;124;227;139m'
FG_SLATE=$'\033[38;2;120;140;120m'
FG_DIM=$'\033[38;2;92;108;92m'

# Written as byte escapes, not literal characters. These live in the Unicode
# private use area, and whatever edited this file previously silently dropped
# them, leaving empty strings and a powerline with no dividers. Escapes keep the
# source pure ASCII so that cannot happen again.
CAP_L=$'\xee\x82\xb6'   # U+E0B6 left half circle
SEP=$'\xee\x82\xb0'     # U+E0B0 right-pointing divider
CAP_R=$'\xee\x82\xb4'   # U+E0B4 right half circle

# Robot rather than a bolt, which reads as fast mode. Alternatives, all verified
# present in JetBrainsMonoNerdFontMono: run statusline-icons.sh to compare.
#   $'\xf3\xb1\x99\xbe' U+F167E robot outline   $'\xef\x92\x98' U+F498  hubot
#   $'\xf3\xb1\x9c\x99' U+F1719 robot happy     $'\xf3\xb0\xa7\x9a' U+F09DA brain
ICON_MODEL=$'\xf3\xb0\x9a\xa9'   # U+F06A9 nf-md-robot
ICON_DIR=$'\xef\x81\xbb'      # U+F07B folder
ICON_BRANCH=$'\xee\x82\xa0'   # U+E0A0 git branch

now=$(date +%s)

sev() {  # percent -> SEV, the same green/mango/coral ramp both meters share
    if   [ "$1" -lt 50 ]; then SEV=$FG_GREEN
    elif [ "$1" -lt 80 ]; then SEV=$FG_MANGO
    else                       SEV=$FG_CORAL
    fi
}

# Reset stamp as local wall-clock, into RS. The 5h window always lands inside
# today so a bare time reads straight off your clock; 7d names its weekday.
# One date call emits every field this needs.
fmt_reset() {  # epoch, near|far
    local ap mm hm wd wdm suf
    set -- $(date -r "$1" '+%p %M %-I:%M %a%-I %a%-I:%M') "$2"
    ap=$1 mm=$2 hm=$3 wd=$4 wdm=$5
    suf=a; [ "$ap" = PM ] && suf=p
    if   [ "$6" = near ]; then RS="↻$hm$suf"
    elif [ "$mm" = 00 ];  then RS="↻$wd$suf"
    else                       RS="↻$wdm$suf"
    fi
}

# One limit as "<label> <pct>% [▲over] [↻reset]" into QI_OUT, with its display
# width in QI_W. Tiers: 2 = with stamp, 1 = flag only, 0 = percentage only.
quota_item() {  # label, pct, reset, window_seconds, near|far, tier
    local label=$1 pct=$2 reset=$3 win=$4 kind=$5 tier=$6 pace over
    sev "$pct"
    QI_OUT="$FG_SLATE$label $SEV$pct%"
    QI_W=$(( ${#label} + 1 + ${#pct} + 1 ))
    if [ "$tier" -ge 1 ] && [ "$reset" -gt "$now" ] && [ "$win" -gt 0 ]; then
        pace=$(( (now - (reset - win)) * 100 / win ))
        over=$(( pct - pace ))
        # Gated so the flag stays a signal. Early in a window almost any usage
        # is technically "ahead of pace" (three hours into seven days, pace is
        # 2%), which would leave ▲ permanently lit and therefore meaningless.
        # Require enough of the window elapsed to extrapolate from, and enough
        # of a gap to be worth acting on.
        if [ "$pace" -ge 15 ] && [ "$over" -ge 5 ]; then
            QI_OUT+="$FG_CORAL ▲$over"
            QI_W=$(( QI_W + 2 + ${#over} ))
        fi
    fi
    if [ "$tier" -ge 2 ] && [ "$reset" -gt 0 ]; then
        fmt_reset "$reset" "$kind"
        QI_OUT+="$FG_DIM $RS"
        QI_W=$(( QI_W + 1 + ${#RS} ))
    fi
}

# ── powerline assembly; the plain twin embeds the real cap/separator/icon ────
# values rather than stand-ins, so width math holds whether or not they are set

pre_out="$FG_MANGO$CAP_L$R"
pre_plain="$CAP_L"
pre_out+="$BG_MANGO$FG_INK $ICON_MODEL $model $R"
pre_plain+=" $ICON_MODEL $model "
pre_out+="$FG_MANGO$BG_BUTTER$SEP$R"
pre_plain+="$SEP"

disp="$dir"
[ "${dir#"$HOME"}" != "$dir" ] && disp="~${dir#"$HOME"}"
if [ ${#disp} -gt 38 ]; then
    parent="${dir%/*}"
    disp="…/${parent##*/}/${dir##*/}"
fi
pre_out+="$BG_BUTTER$FG_INK $ICON_DIR $disp $R"
pre_plain+=" $ICON_DIR $disp "

# Git state read from the real cwd, not the abbreviated display path
branch=$(git -C "$dir" symbolic-ref --short HEAD 2>/dev/null || git -C "$dir" rev-parse --short HEAD 2>/dev/null)

tail_fg=$FG_BUTTER
if [ -n "$branch" ]; then
    pre_out+="$FG_BUTTER$BG_DEEP$SEP$R"
    pre_plain+="$SEP"
    pre_out+="$BG_DEEP$FG_TEAL $ICON_BRANCH $branch $R"
    pre_plain+=" $ICON_BRANCH $branch "
    tail_fg=$FG_DEEP
fi
pre_out+="$tail_fg$CAP_R$R"
pre_plain+="$CAP_R"

# Context meter, sized first so quota knows how much room is left
[ "$p" -lt 0 ] && p=0
[ "$p" -gt 100 ] && p=100
sev "$p"
filled=$(( (p + 10) / 20 ))
meter=""
for i in 1 2 3 4 5; do
    if [ "$i" -le "$filled" ]; then meter+="▰"; else meter+="▱"; fi
done
ctx_out="   ${SEV}$meter ${p}%${tokens}$R"
ctx_plain="   $meter ${p}%${tokens}"

# ── quota, at the richest tier that fits ────────────────────────────────────

cols=${COLUMNS:-$(tput cols 2>/dev/null || echo 120)}
quota_out=""
if [ "$h5_pct" -ge 0 ] || [ "$d7_pct" -ge 0 ]; then
    avail=$(( cols - ${#pre_plain} - ${#ctx_plain} ))
    for tier in 2 1 0; do
        cand_out=""
        cand_w=0
        if [ "$h5_pct" -ge 0 ]; then
            quota_item 5h "$h5_pct" "$h5_reset" 18000 near "$tier"
            cand_out+="  $QI_OUT"
            cand_w=$(( cand_w + 2 + QI_W ))
        fi
        if [ "$d7_pct" -ge 0 ]; then
            quota_item 7d "$d7_pct" "$d7_reset" 604800 far "$tier"
            cand_out+="   $QI_OUT"
            cand_w=$(( cand_w + 3 + QI_W ))
        fi
        if [ "$cand_w" -le "$avail" ]; then
            quota_out="$cand_out$R"
            break
        fi
    done
fi

printf '%s\n' "$pre_out$quota_out$ctx_out"
