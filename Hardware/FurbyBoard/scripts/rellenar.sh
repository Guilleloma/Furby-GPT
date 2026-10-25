#!/usr/bin/env bash
# Rellena las zonas de FurbyBoard.kicad_pcb con las reglas del proyecto y guarda la placa.
#   scripts/rellenar.sh
# Va después de gen_pro.py: gen_pcb.py guarda las zonas sin rellenar porque, al guardar, KiCad
# reescribe el .kicad_pro con sus reglas por defecto (margen a borde 0,5 en vez de 0,3;
# hallazgo E1-1). kicad-cli lee las reglas del .kicad_pro y del .kicad_dru y no los toca.
# Termina con el DRC sin relleno, que comprueba lo que se ha guardado (lo que se fabrica).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KC="${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}"
PCB="$ROOT/FurbyBoard.kicad_pcb"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ls "$ROOT"/~*.lck >/dev/null 2>&1; then
    echo "El proyecto está abierto en KiCad: ciérralo antes de rellenar" >&2
    exit 1
fi
"$KC" pcb drc --refill-zones --save-board --schematic-parity --severity-all --exit-code-violations \
    -o "$TMP/drc-relleno.rpt" "$PCB" >/dev/null
"$KC" pcb drc --schematic-parity --severity-all --exit-code-violations -o "$TMP/drc.rpt" "$PCB" >/dev/null
echo "Zonas rellenas y guardadas; DRC con paridad sin infracciones"
