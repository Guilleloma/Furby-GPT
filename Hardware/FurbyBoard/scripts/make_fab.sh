#!/usr/bin/env bash
# Ficheros de fabricación de la FurbyBoard para JLCPCB: ERC/DRC, Gerber + taladros
# (zip), BOM y CPL, y renders. No pide nada: el pedido lo hace Guillermo a mano.
#   scripts/make_fab.sh
# El PCB debe estar rutado y con las zonas rellenas (gen_pcb.py --rellenar): el DRC
# se pasa sin --refill-zones, sobre lo que hay guardado, y con paridad esquemático-PCB.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KC="${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}"
SCH="$ROOT/FurbyBoard.kicad_sch"
PCB="$ROOT/FurbyBoard.kicad_pcb"
FAB="$ROOT/fabricacion"
GB="$FAB/gerber"
REN="$ROOT/render"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$FAB" "$GB" "$REN"
rm -f "$GB"/* "$FAB"/gerber-jlcpcb.zip

echo "== ERC / DRC (errores y avisos)"
"$KC" sch erc --severity-all --exit-code-violations -o "$FAB/erc.rpt" "$SCH" >/dev/null
"$KC" pcb drc --schematic-parity --severity-all --exit-code-violations -o "$FAB/drc.rpt" "$PCB" >/dev/null
echo "ERC y DRC sin infracciones"

echo "== Gerber + taladros (origen auxiliar = (0,0) del STL, el mismo que el CPL)"
"$KC" pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --subtract-soldermask --use-drill-file-origin --check-zones -o "$GB/" "$PCB" >/dev/null
"$KC" pcb export drill --format excellon --excellon-units mm --excellon-zeros-format decimal \
    --drill-origin plot --generate-map --map-format gerberx2 -o "$GB/" "$PCB" >/dev/null
(cd "$GB" && zip -q -r "$FAB/gerber-jlcpcb.zip" .)
echo "$(ls "$GB" | wc -l | tr -d ' ') ficheros -> fabricacion/gerber-jlcpcb.zip"

echo "== BOM y CPL (formato JLCPCB)"
"$KC" sch export bom --fields 'Reference,Value,Footprint,LCSC,JLC_Class,${DNP}' \
    --labels 'Ref,Value,Footprint,LCSC,JLC_Class,DNP' -o "$TMP/bom_raw.csv" "$SCH" >/dev/null
"$KC" pcb export pos --format csv --units mm --side both --use-drill-file-origin \
    -o "$TMP/pos_raw.csv" "$PCB" >/dev/null
python3 "$ROOT/scripts/jlc_post.py" "$TMP/bom_raw.csv" "$TMP/pos_raw.csv" "$FAB"

echo "== Renders"
"$KC" pcb render --side top --quality high --width 1400 --height 1500 --floor \
    -o "$REN/furbyboard-arriba.png" "$PCB" >/dev/null
"$KC" pcb render --side bottom --quality high --width 1400 --height 1500 --floor \
    -o "$REN/furbyboard-abajo.png" "$PCB" >/dev/null
"$KC" pcb render --quality high --rotate "-50,0,25" --perspective --width 1600 --height 1200 --floor \
    -o "$REN/furbyboard-iso.png" "$PCB" >/dev/null
"$KC" pcb export step --subst-models --force -o "$REN/furbyboard.step" "$PCB" >/dev/null
"$KC" sch export pdf -o "$FAB/esquematico.pdf" "$SCH" >/dev/null
echo "Hecho."
