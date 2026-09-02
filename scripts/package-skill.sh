#!/usr/bin/env bash
# Fabrique le ZIP à déposer dans Customize > Skills sur claude.ai (repli pour les
# plans Free, qui n'ont pas droit aux plugins).
# Le ZIP doit contenir le DOSSIER du skill à sa racine, pas SKILL.md directement.
set -euo pipefail

PLUGIN="${1:-feve-relecture}"
SKILL="${2:-relecture}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/plugins/$PLUGIN/skills/$SKILL"
OUT="$ROOT/dist/$PLUGIN-skill.zip"

[ -f "$SRC/SKILL.md" ] || { echo "Skill introuvable : $SRC/SKILL.md" >&2; exit 1; }

rm -rf "$ROOT/dist/.pack" && mkdir -p "$ROOT/dist/.pack"
cp -R "$SRC" "$ROOT/dist/.pack/$SKILL"
find "$ROOT/dist/.pack" \( -name __pycache__ -o -name '.DS_Store' \) -exec rm -rf {} +

rm -f "$OUT"
(cd "$ROOT/dist/.pack" && zip -qr "$OUT" "$SKILL")
rm -rf "$ROOT/dist/.pack"

echo "$OUT"
unzip -l "$OUT" | sed -n '3,12p'
