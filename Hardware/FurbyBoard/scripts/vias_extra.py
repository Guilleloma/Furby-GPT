#!/usr/bin/env python3
"""Vías de más a los planos (GND en In1, VSYS en In2) en los pads que llevan corriente.

Se ejecuta con el Python de KiCad, después de gen_pcb.py y antes de ensanchar_potencia.py:
    $KICAD_PY scripts/vias_extra.py

El autorrutado une cada pad con su plano con una sola vía de 0,3 mm, que aguanta
del orden de 1 A. En los pads de los convertidores, del cargador y del
amplificador (hasta ≈ 2,3 A en la entrada del elevador) se añaden vías junto al
pad, unidas con un tramo corto de 0,5 mm. Se prueban varias posiciones y se
quedan las que pasan el DRC de KiCad.
"""
import json
import os
import subprocess
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P  # noqa: E402

KICAD_CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
PIEZAS = ["L2", "C16", "C17", "C18", "C19", "C20", "C21", "U5", "C12", "L1", "U3", "C6", "C7", "C8",
          "U2", "C1", "C2", "C3", "C4", "U7", "C24", "C25", "U6", "C22", "C9", "C10", "Q1"]
REDES = {"GND", "VSYS"}
POR_PAD = 2          # vías nuevas como máximo por pad
SEPARACION = 0.55    # del borde del pad al centro de la vía


def mm(v):
    return pcbnew.FromMM(v)


def candidatos(pad):
    """Puntos alrededor del pad, a SEPARACION de su borde, en las 8 direcciones."""
    c = pad.GetPosition()
    bb = pad.GetBoundingBox()
    hx, hy = bb.GetWidth() / 2, bb.GetHeight() / 2
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
        yield pcbnew.VECTOR2I(int(c.x + dx * (hx + mm(SEPARACION))), int(c.y + dy * (hy + mm(SEPARACION))))


def drc_malos(pcb):
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "drc.json")
        subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "json", "--severity-error", "--severity-warning",
                        "--refill-zones", "-o", out, pcb], check=True, capture_output=True)
        data = json.load(open(out, encoding="utf-8"))
    return {i.get("uuid") for v in data.get("violations", []) for i in v.get("items", [])}


def poner(board, pad, p):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(p)
    v.SetWidth(mm(P.RULE_VIA_DIAM))
    v.SetDrill(mm(P.RULE_VIA_DRILL))
    v.SetNet(pad.GetNet())
    board.Add(v)
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pad.GetPosition())
    t.SetEnd(p)
    t.SetWidth(mm(0.5))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(pad.GetNet())
    board.Add(t)
    return v, t


def main():
    board = pcbnew.LoadBoard(P.PCB)
    pads = []
    for ref in PIEZAS:
        for pad in board.FindFootprintByReference(ref).Pads():
            if pad.GetNetname() in REDES and pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                pads.append(("%s.%s" % (ref, pad.GetNumber()), pad, list(candidatos(pad))))
    puestas = {k: 0 for k, _, _ in pads}
    # Una candidata por pad en cada vuelta: así dos candidatas del mismo pad no se anulan entre sí
    for vuelta in range(8):
        prueba = []
        for key, pad, cands in pads:
            if puestas[key] < POR_PAD and vuelta < len(cands):
                prueba.append((key,) + poner(board, pad, cands[vuelta]))
        if not prueba:
            break
        pcbnew.SaveBoard(P.PCB, board)
        malos = drc_malos(P.PCB)
        for key, v, t in prueba:
            if v.m_Uuid.AsString() in malos or t.m_Uuid.AsString() in malos:
                board.Remove(v)
                board.Remove(t)
            else:
                puestas[key] += 1
        print("vuelta %d: %d probadas, %d en total" % (vuelta, len(prueba), sum(puestas.values())))
    pcbnew.SaveBoard(P.PCB, board)
    print("Vías añadidas: %d en %d pads" % (sum(puestas.values()), sum(1 for n in puestas.values() if n)))


if __name__ == "__main__":
    main()
