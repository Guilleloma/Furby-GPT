#!/usr/bin/env python3
"""Ensancha las pistas de potencia autorrutadas donde caben, y rellena los planos.

Se ejecuta con el Python de KiCad, después de gen_pcb.py (que importa el rutado):
    $KICAD_PY scripts/ensanchar_potencia.py

El autorrutado traza la potencia a 0,4 (lo que entra en los pads de 0,5 de paso).
Aquí cada tramo de una red de potencia o de motor prueba 0,8, 0,6 y 0,5 mm, y se
queda con el más ancho que no da ninguna infracción en el DRC de KiCad. Las
pistas bloqueadas (rutas_fijas.py) no se tocan.
"""
import json
import os
import subprocess
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pro  # noqa: E402
import params as P  # noqa: E402

KICAD_CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
ANCHOS = [P.TRACK_POWER_MAX, 0.6, 0.5, P.TRACK_POWER]
REDES = set(gen_pro.POWER_NETS + gen_pro.MOTOR_NETS) - {"VSYS"}


def drc_uuids(pcb):
    """UUID de los elementos que aparecen en alguna infracción (sin contar lo no rutado)."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "drc.json")
        subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "json", "--severity-error", "--severity-warning",
                        "--refill-zones", "-o", out, pcb], check=True, capture_output=True)
        data = json.load(open(out, encoding="utf-8"))
    malos = set()
    for v in data.get("violations", []):
        for item in v.get("items", []):
            malos.add(item.get("uuid"))
    return malos, len(data.get("violations", []))


def rellenar(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def main():
    board = pcbnew.LoadBoard(P.PCB)
    tramos = [t for t in board.GetTracks()
              if t.GetClass() == "PCB_TRACK" and not t.IsLocked() and t.GetNetname() in REDES]
    nivel = {t.m_Uuid.AsString(): 0 for t in tramos}
    original = {t.m_Uuid.AsString(): t.GetWidth() for t in tramos}
    for vuelta in range(len(ANCHOS) + 1):
        for t in tramos:
            u = t.m_Uuid.AsString()
            t.SetWidth(max(original[u], pcbnew.FromMM(ANCHOS[nivel[u]])))
        pcbnew.SaveBoard(P.PCB, board)
        malos, n = drc_uuids(P.PCB)
        cambios = 0
        for t in tramos:
            u = t.m_Uuid.AsString()
            if u in malos and nivel[u] < len(ANCHOS) - 1:
                nivel[u] += 1
                cambios += 1
        print("vuelta %d: %d infracciones, %d tramos bajan de ancho" % (vuelta, n, cambios))
        if not cambios:
            break
    reparto = {}
    for t in tramos:
        reparto[ANCHOS[nivel[t.m_Uuid.AsString()]]] = reparto.get(ANCHOS[nivel[t.m_Uuid.AsString()]], 0) + 1
    print("Tramos de potencia por ancho:", ", ".join("%.1f mm: %d" % kv for kv in sorted(reparto.items(), reverse=True)))
    rellenar(board)
    pcbnew.SaveBoard(P.PCB, board)


if __name__ == "__main__":
    main()
