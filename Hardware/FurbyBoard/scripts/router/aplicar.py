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


def rellenos_exteriores(board):
    """Relleno de GND en F.Cu y B.Cu, ya con el rutado puesto."""
    import gen_pcb as G
    c = G.GEO["resultado"]["caja"]
    todo = G.caja(c[0] - 1, c[2] + 1, c[1] - 1, c[3] + 1)
    gnd = board.FindNet("GND")
    for capa in (pcbnew.F_Cu, pcbnew.B_Cu):
        if not any(z.GetLayer() == capa and not z.GetIsRuleArea() for z in board.Zones()):
            G.poly_zone(board, [capa], todo, net=gnd)


def rotular_tps(board):
    """Nombre de cada TP en la serigrafía inferior, junto a su pad."""
    import gen_pcb as G
    import serigrafia as SG
    abajo = G.colocador(board, "B")
    sin_sitio = []
    for ref, txt in SG.TP_ABAJO.items():
        fp = board.FindFootprintByReference(ref)
        if fp.GetLayer() != pcbnew.B_Cu:
            continue
        xy = abajo.coloca(ref, G.caja_pads(fp, silk=pcbnew.B_SilkS), G.rotulo(board, "B", txt), "RLUD")
        if xy:
            G.rotulo(board, "B", txt, xy)
        else:
            sin_sitio.append(ref)
    if sin_sitio:
        print("TP sin rótulo (identificados en el TEST-PLAN):", ", ".join(sin_sitio))


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
        for ref, pos in datos.get("tps", {}).items():
            # El TP pasa a la cara inferior, centrado en su vía
            fp = board.FindFootprintByReference(ref)
            if fp.GetLayer() != pcbnew.B_Cu:
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetPosition(punto(pos))
    rotular_tps(board)
    rellenos_exteriores(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(P.PCB, board)
    print("Aplicadas %d pistas y %d vías; planos rellenos" % (n_p, n_v))


if __name__ == "__main__":
    main()
