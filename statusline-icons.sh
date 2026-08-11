#!/bin/bash
# Shows model-icon candidates in the real statusline segment so they can be
# compared as rendered rather than as codepoint names. Every glyph here was
# verified present in JetBrainsMonoNerdFontMono-Regular.ttf by reading the
# font's cmap table, so a tofu box means a font fallback problem, not a typo.
#
#   ./statusline-icons.sh          compare candidates
#   ./statusline-icons.sh --check  report cell width of each glyph

unset LC_ALL
export LC_CTYPE=UTF-8

R=$'\033[0m'
BG_MANGO=$'\033[48;2;255;180;84m'
BG_BUTTER=$'\033[48;2;255;240;165m'
BG_DEEP=$'\033[48;2;10;61;31m'
FG_MANGO=$'\033[38;2;255;180;84m'
FG_BUTTER=$'\033[38;2;255;240;165m'
FG_DEEP=$'\033[38;2;10;61;31m'
FG_INK=$'\033[38;2;24;40;24m'
FG_TEAL=$'\033[38;2;53;224;208m'
FG_SLATE=$'\033[38;2;120;140;120m'
BOLD=$'\033[1m'

CAP_L=$'\xee\x82\xb6'
SEP=$'\xee\x82\xb0'
CAP_R=$'\xee\x82\xb4'
ICON_DIR=$'\xef\x81\xbb'
ICON_BRANCH=$'\xee\x82\xa0'

# name, codepoint label, glyph
names=(
  "nf-md-robot          (live)"
  "nf-md-robot_outline"
  "nf-md-robot_happy"
  "nf-oct-hubot"
  "nf-cod-hubot"
  "nf-md-brain"
  "nf-md-chip"
  "nf-fa-microchip"
  "nf-oct-cpu"
  "nf-md-sparkles"
  "nf-md-creation"
  "nf-fa-bolt           (old)"
)
codes=(U+F06A9 U+F167E U+F1719 U+F498 U+EB07 U+F09DA U+F061A U+F2DB U+F4BC U+F1545 U+F0674 U+F0E7)
glyphs=(
  $'\xf3\xb0\x9a\xa9' $'\xf3\xb1\x99\xbe' $'\xf3\xb1\x9c\x99'
  $'\xef\x92\x98'     $'\xee\xac\x87'     $'\xf3\xb0\xa7\x9a'
  $'\xf3\xb0\x98\x9a' $'\xef\x8b\x9b'     $'\xef\x92\xbc'
  $'\xf3\xb1\x95\x85' $'\xf3\xb0\x99\xb4' $'\xef\x83\xa7'
)
escs=(
  '\xf3\xb0\x9a\xa9' '\xf3\xb1\x99\xbe' '\xf3\xb1\x9c\x99'
  '\xef\x92\x98'     '\xee\xac\x87'     '\xf3\xb0\xa7\x9a'
  '\xf3\xb0\x98\x9a' '\xef\x8b\x9b'     '\xef\x92\xbc'
  '\xf3\xb1\x95\x85' '\xf3\xb0\x99\xb4' '\xef\x83\xa7'
)

if [ "${1:-}" = --check ]; then
    # A glyph that advances two cells would push the line one column wider than
    # the statusline predicts, so confirm each is single-width before adopting.
    printf '%sCell width probe%s  (column marker should land at 4 for every row)\n\n' "$BOLD" "$R"
    printf '    0123456789\n'
    for i in "${!glyphs[@]}"; do
        printf '    abc%s' "${glyphs[$i]}"
        printf '\033[6n' >/dev/tty
        read -rsd R -t 0.3 pos </dev/tty
        col="${pos##*;}"
        printf '  col=%-4s %s\n' "$col" "${names[$i]}"
    done
    echo
    exit 0
fi

printf '%sModel icon candidates%s   the mango segment is what changes\n\n' "$BOLD" "$R"
for i in "${!glyphs[@]}"; do
    printf '  %s%-28s%s %s%-8s%s ' "$FG_SLATE" "${names[$i]}" "$R" "$FG_SLATE" "${codes[$i]}" "$R"
    printf '%s%s%s' "$FG_MANGO" "$CAP_L" "$R"
    printf '%s%s %s Opus 5 %s' "$BG_MANGO" "$FG_INK" "${glyphs[$i]}" "$R"
    printf '%s%s%s%s' "$FG_MANGO" "$BG_BUTTER" "$SEP" "$R"
    printf '%s%s %s ~/dev %s' "$BG_BUTTER" "$FG_INK" "$ICON_DIR" "$R"
    printf '%s%s%s%s' "$FG_BUTTER" "$BG_DEEP" "$SEP" "$R"
    printf '%s%s %s main %s' "$BG_DEEP" "$FG_TEAL" "$ICON_BRANCH" "$R"
    printf '%s%s%s\n' "$FG_DEEP" "$CAP_R" "$R"
done

printf '\n%sTo switch%s, set this line in ~/.claude/statusline.sh:\n' "$BOLD" "$R"
printf '  %sICON_MODEL=$'"'"'<escape>'"'"'%s\n\n' "$FG_SLATE" "$R"
for i in "${!glyphs[@]}"; do
    printf '  %-28s %s\n' "${names[$i]}" "\$'${escs[$i]}'"
done
echo
