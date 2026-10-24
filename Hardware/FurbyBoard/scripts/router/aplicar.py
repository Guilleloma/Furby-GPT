#!/usr/bin/env python3
"""Añade al PCB las pistas y vías que calcula rutar.py y rellena los planos.

Se ejecuta con el Python de KiCad:
    $KICAD_PY scripts/router/aplicar.py <rutas.json> [<rutas2.json> ...]
"""
import json
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import params as P  # noqa: E402

CAPAS = {"F": pcbnew.F_Cu, "I": pcbnew.In2_Cu, "B": pcbnew.B_Cu}


def mm(v):
    return pcbnew.FromMM(v)


def punto(p):
    return pcbnew.VECTOR2I(mm(p[0]), mm(p[1]))


def main():
    board = pcbnew.LoadBoard(P.PCB)
    redes = {}
    n_p = n_v = 0
    for ruta in sys.argv[1:]:
        datos = json.load(open(ruta))
        for t in datos["pistas"]:
            red = redes.setdefault(t["red"], board.FindNet(t["red"]))
            s = pcbnew.PCB_TRACK(board)
            s.SetStart(punto(t["a"]))
            s.SetEnd(punto(t["b"]))
            s.SetWidth(mm(t["w"]))
            s.SetLayer(CAPAS[t["capa"]])
            s.SetNet(red)
            board.Add(s)
            n_p += 1
        for v in datos["vias"]:
            red = redes.setdefault(v["red"], board.FindNet(v["red"]))
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(punto(v["pos"]))
            via.SetWidth(mm(P.RULE_VIA_DIAM))
            via.SetDrill(mm(P.RULE_VIA_DRILL))
            via.SetNet(red)
            board.Add(via)
            n_v += 1
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(P.PCB, board)
    print("Aplicadas %d pistas y %d vías; planos rellenos" % (n_p, n_v))


if __name__ == "__main__":
    main()
