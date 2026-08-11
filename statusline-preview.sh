#!/bin/bash
# Renders candidate quota layouts with real colors so they can be compared in
# situ. Each candidate is shown across three states, because the layout that
# looks best at 80% usage is often the one that looks broken at 4%.
#   ./statusline-preview.sh

unset LC_ALL
export LC_CTYPE=UTF-8

R=$'\033[0m'
FG_MANGO=$'\033[38;2;255;180;84m'   BG_MANGO=$'\033[48;2;255;180;84m'
FG_BUTTER=$'\033[38;2;255;240;165m' BG_BUTTER=$'\033[48;2;255;240;165m'
FG_DEEP=$'\033[38;2;10;61;31m'      BG_DEEP=$'\033[48;2;10;61;31m'
FG_INK=$'\033[38;2;24;40;24m'       BG_INK=$'\033[48;2;24;40;24m'
BG_TRACK=$'\033[48;2;44;62;44m'
FG_TEAL=$'\033[38;2;53;224;208m'
FG_CORAL=$'\033[38;2;255;92;138m'
FG_GREEN=$'\033[38;2;124;227;139m'
FG_SLATE=$'\033[38;2;120;140;120m'
FG_DIM=$'\033[38;2;92;108;92m'
BOLD=$'\033[1m'

sev() {
    if   [ "$1" -lt 50 ]; then SEV=$FG_GREEN
    elif [ "$1" -lt 80 ]; then SEV=$FG_MANGO
    else                       SEV=$FG_CORAL
    fi
}

# A fixed powerline prefix so each candidate is judged in real context
prefix() {
    printf '%s' "$BG_MANGO$FG_INK Opus 5 (1M context) $R$BG_BUTTER$FG_INK ~/aster-frontend $R$BG_DEEP$FG_TEAL next/isr-revalidate $R"
}
ctx() {  # context meter, unchanged from today
    sev 15
    printf '%s' "   ${SEV}▰▱▱▱▱ 15% (149k)$R"
}

# ── candidate A: numbers and resets only, no bars, no background block ───────
cand_A() {  # h5, d7, pace5, pace7, rs5, rs7
    local o
    sev "$1"; o="  $FG_SLATE""5h $SEV$1%$FG_DIM $5"
    sev "$2"; o+="   $FG_SLATE""7d $SEV$2%$FG_DIM $6$R"
    printf '%s' "$o"
}

# ── candidate B: same, plus an overspend flag shown ONLY when ahead of pace ──
cand_B() {
    local o d
    sev "$1"; o="  $FG_SLATE""5h $SEV$1%"
    d=$(( $1 - $3 )); [ "$d" -ge 1 ] && o+="$FG_CORAL ▲$d"
    o+="$FG_DIM $5"
    sev "$2"; o+="   $FG_SLATE""7d $SEV$2%"
    d=$(( $2 - $4 )); [ "$d" -ge 1 ] && o+="$FG_CORAL ▲$d"
    o+="$FG_DIM $6$R"
    printf '%s' "$o"
}

# ── candidate C: used/elapsed pair, pace as a dim second number ─────────────
cand_C() {
    local o
    sev "$1"; o="  $FG_SLATE""5h $SEV$1$FG_DIM/$3 $5"
    sev "$2"; o+="   $FG_SLATE""7d $SEV$2$FG_DIM/$4 $6$R"
    printf '%s' "$o"
}

# ── candidate D: one wide 12-cell bar, binding limit only, pace legible ─────
cand_D() {
    local pick lim pace stamp cells=12 i out used ahead pc
    if [ "$1" -ge "$2" ]; then pick=5h lim=$1 pace=$3 stamp=$5
    else                       pick=7d lim=$2 pace=$4 stamp=$6
    fi
    sev "$lim"
    used=$(( lim * cells / 100 ))
    pc=$(( pace * cells / 100 ))
    out="  $FG_SLATE$pick $BG_TRACK"
    for ((i=0; i<cells; i++)); do
        if   [ "$i" -lt "$used" ] && [ "$i" -ge "$pc" ]; then out+="${FG_CORAL}█"
        elif [ "$i" -lt "$used" ];                       then out+="${SEV}█"
        elif [ "$i" -eq "$pc" ];                         then out+="${FG_SLATE}▏"
        else                                                  out+=" "
        fi
    done
    out+="$R$SEV $lim%$FG_DIM $stamp$R"
    printf '%s' "$out"
}

# ── candidate E: severity dot per limit, nearest reset only ─────────────────
cand_E() {
    local o
    sev "$1"; o="  ${SEV}●$FG_SLATE 5h $SEV$1%"
    sev "$2"; o+="  ${SEV}●$FG_SLATE 7d $SEV$2%$FG_DIM $5$R"
    printf '%s' "$o"
}

state() {  # label, h5, d7, pace5, pace7, rs5, rs7
    printf '\n%s%s%s\n' "$BOLD" "$1" "$R"
    for c in A B C D E; do
        printf '  %s%s%s ' "$FG_DIM" "$c" "$R"
        prefix
        "cand_$c" "$2" "$3" "$4" "$5" "$6" "$7"
        ctx
        printf '\n'
    done
}

printf '%sQuota layout candidates%s  (same powerline prefix and context meter throughout)\n' "$BOLD" "$R"
printf '%sA%s numbers + resets   %sB%s + overspend flag   %sC%s used/pace pair   %sD%s one wide bar   %sE%s severity dots\n' \
    "$BOLD" "$R" "$BOLD" "$R" "$BOLD" "$R" "$BOLD" "$R" "$BOLD" "$R"

state "Fresh, just after a 5h reset  (this is the state that looked broken)" \
      4 31 8 19 "↻7:20p" "↻Tue11a"
state "Mid week, 5h running hot" \
      67 45 40 52 "↻4:05p" "↻Tue11a"
state "Both near the cap" \
      92 88 70 80 "↻2:55p" "↻Tue11a"

printf '\n%sToday, for comparison:%s\n' "$BOLD" "$R"
printf '    '
prefix
printf '%s' " $BG_INK$FG_SLATE""5h$BG_TRACK${FG_GREEN}▎${FG_SLATE}▏$BG_TRACK   $BG_INK$FG_GREEN 4$FG_SLATE ↻7:20p  $FG_SLATE""7d$BG_TRACK${FG_GREEN}█🮕$BG_TRACK   $BG_INK$FG_GREEN 31$FG_SLATE ↻Tue11a $R$FG_INK$R"
ctx
printf '\n\n'
