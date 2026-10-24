#!/usr/bin/env python3
"""Saca del PCB lo que necesita el rutador: pads, pistas fijas, zonas prohibidas y contorno.

Se ejecuta con el Python de KiCad:
    $KICAD_PY scripts/router/extraer.py <salida.json>

Coordenadas de KiCad en mm (y hacia abajo). Los TP no entran: se colocan después
del rutado sobre el cobre de su red (scripts/router/colocar_tp.py).
"""
import json
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import gen_pro  # noqa: E402
import params as P  # noqa: E402

CAPAS = {pcbnew.F_Cu: "F", pcbnew.In2_Cu: "I", pcbnew.B_Cu: "B"}
ERR = pcbnew.FromMM(0.005)


def mm(v):
    return round(pcbnew.ToMM(v), 4)


def poligonos(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        out.append([(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())])
    return out


def ancho_red(nombre):
    if nombre in ("USB_DP", "USB_DN"):
        return P.USB_DIFF_W
    if nombre == "3V3":
        return P.TRACK_3V3
    if nombre in gen_pro.MOTOR_NETS:
        return P.TRACK_MOTOR
    if nombre in gen_pro.POWER_NETS:
        return P.TRACK_POWER
    return P.TRACK_SIGNAL


def main():
    board = pcbnew.LoadBoard(P.PCB)
    pads = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("TP") or ref.startswith("LOGO"):
            continue
        for pad in fp.Pads():
            capas = [c for lay, c in CAPAS.items() if pad.IsOnLayer(lay)]
            tht = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            if tht:
                capas = ["F", "I", "B"]
            if not capas:
                continue
            ps = pcbnew.SHAPE_POLY_SET()
            pad.TransformShapeToPolygon(ps, pcbnew.F_Cu if "F" in capas else pcbnew.B_Cu, 0, ERR,
                                        pcbnew.ERROR_OUTSIDE)
            agujero = None
            if tht:
                d = pad.GetDrillSize()
                agujero = [mm(pad.GetPosition().x), mm(pad.GetPosition().y), mm(max(d.x, d.y)) / 2]
            pads.append({"ref": ref, "num": pad.GetNumber(), "red": pad.GetNetname(), "capas": capas,
                         "pos": [mm(pad.GetPosition().x), mm(pad.GetPosition().y)],
                         "poly": poligonos(ps), "agujero": agujero,
                         "npth": pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH})
    pistas, vias = [], []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            vias.append({"red": t.GetNetname(), "pos": [mm(t.GetPosition().x), mm(t.GetPosition().y)],
                         "d": mm(t.GetWidth(pcbnew.F_Cu)), "fija": t.IsLocked()})
        elif t.GetLayer() in CAPAS:
            pistas.append({"red": t.GetNetname(), "capa": CAPAS[t.GetLayer()], "w": mm(t.GetWidth()),
                           "a": [mm(t.GetStart().x), mm(t.GetStart().y)],
                           "b": [mm(t.GetEnd().x), mm(t.GetEnd().y)], "fija": t.IsLocked()})
    prohibidas = []
    zonas = list(board.Zones())
    for fp in board.GetFootprints():
        zonas += list(fp.Zones())
    for z in zonas:
        if not z.GetIsRuleArea():
            continue
        capas = [c for lay, c in CAPAS.items() if z.GetLayerSet().Contains(lay)]
        prohibidas.append({"capas": capas, "pistas": z.GetDoNotAllowTracks(), "vias": z.GetDoNotAllowVias(),
                           "poly": poligonos(z.Outline())})
    # Sin pistas en F.Cu bajo el cuerpo del módulo (entre sus filas de pads, con 1,2 mm de
    # margen para que sus pistas salgan hacia fuera). In2 y B.Cu quedan bajo el GND de In1.
    u4 = board.FindFootprintByReference("U4")
    xs = [mm(p.GetPosition().x) for p in u4.Pads() if p.GetNumber() in ("1", "14", "27", "40")]
    ys = [mm(p.GetPosition().y) for p in u4.Pads() if p.GetNumber() in ("1", "15", "26", "40")]
    x0, x1, y0, y1 = min(xs) + 1.2, max(xs) - 1.2, min(ys) - 0.5, max(ys) - 1.2
    prohibidas.append({"capas": ["F"], "pistas": True, "vias": False,
                       "poly": [[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]]})
    borde = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(borde, True)
    contorno = poligonos(borde)
    huecos = []
    for i in range(borde.HoleCount(0)):
        h = borde.Hole(0, i)
        huecos.append([(mm(h.CPoint(k).x), mm(h.CPoint(k).y)) for k in range(h.PointCount())])
    redes = sorted({p["red"] for p in pads if p["red"]})
    datos = {"pads": pads, "pistas": pistas, "vias": vias, "prohibidas": prohibidas,
             "contorno": contorno[0], "huecos": huecos,
             "anchos": {r: ancho_red(r) for r in redes},
             "reglas": {"holgura": P.RULE_CLEARANCE, "borde": P.RULE_EDGE_CLEARANCE,
                        "via_d": P.RULE_VIA_DIAM, "via_taladro": P.RULE_VIA_DRILL, "agujero_agujero": 0.25,
                        "agujero_cobre": 0.2}}
    with open(sys.argv[1], "w") as fh:
        json.dump(datos, fh)
    print("Extraído: %d pads, %d pistas, %d vías, %d áreas prohibidas, %d redes"
          % (len(pads), len(pistas), len(vias), len(prohibidas), len(redes)))


if __name__ == "__main__":
    main()
