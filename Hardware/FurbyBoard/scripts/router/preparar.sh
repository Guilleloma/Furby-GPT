#!/usr/bin/env bash
# Prepara el PCB para el autorrutado: colocación, TP, vías térmicas y lo crítico
# pre-rutado y fijado; deja el DSN en scripts/rutado.dsn.
#   scripts/router/preparar.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KP="${KICAD_PY:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}"
PY="${ROUTER_PY:-python3}"     # con numpy y matplotlib
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$ROOT"
"$KP" scripts/gen_pcb.py --sin-rutado
"$KP" scripts/router/extraer.py "$TMP/geo.json"
"$PY" scripts/router/rutar.py "$TMP/geo.json" "$TMP/tp.json" --solo-tp
"$KP" scripts/router/aplicar.py "$TMP/tp.json" --fijar
"$KP" scripts/router/vias_termicas.py
"$KP" scripts/router/extraer.py "$TMP/geo2.json"
python3 -c "import json; d=json.load(open('scripts/router/prerrutado.json')); json.dump(d['orden'], open('$TMP/orden.json','w')); json.dump(d['anchos'], open('$TMP/anchos.json','w'))"
"$PY" scripts/router/rutar.py "$TMP/geo2.json" "$TMP/pre.json" --orden "$TMP/orden.json" --anchos "$TMP/anchos.json" --vueltas 1 --sin-tp
"$KP" scripts/router/aplicar.py "$TMP/pre.json" --fijar
"$KP" scripts/exportar_dsn.py
