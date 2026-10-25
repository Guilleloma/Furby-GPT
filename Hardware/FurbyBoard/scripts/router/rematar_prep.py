#!/usr/bin/env python3
"""Prepara el remate: quita lo que está mal del rutado y saca la lista de lo pendiente.

Se ejecuta con el Python de KiCad:
    $KICAD_PY scripts/router/rematar_prep.py <pendientes.json>

1. Cuello del par USB en J1: el tramo de B6 a su vía pasa a 45° + vertical (era el
   único fuera de 0/45/90°). La vía no se mueve y el par acoplado no cambia.
2. Quita las pistas de In2 a menos de 0,3 mm del borde y los dos tramos de cada
   ángulo agudo.
3. Quita las puntas colgando (repite el DRC hasta que no quede ninguna).
4. Escribe, con el DRC de KiCad, cada conexión pendiente: red y geometría de los dos
   elementos (pad, pista, vía o zona) que hay que unir.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import params as P  # noqa: E402

KICAD_CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
CAPAS = {pcbnew.F_Cu: "F", pcbnew.In2_Cu: "I", pcbnew.B_Cu: "B"}


def mm(v):
    return round(pcbnew.ToMM(v), 4)


def drc(pcb):
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "drc.json")
        subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "json", "--schematic-parity", "--severity-all",
                        "-o", out, pcb], check=True, capture_output=True)
        return json.load(open(out, encoding="utf-8"))


def item(board, uuid):
    it = board.ResolveItem(pcbnew.KIID(uuid))
    return it.Cast() if it is not None else None


def cuello_usb(board):
    """B6 -> vía: el tramo oblicuo (-72,75; -120,45)->(-72,60; -119,75) pasa a 45° + vertical.

    Solo actúa si encuentra el tramo viejo (es idempotente). La vía no se mueve, así que
    el tramo acoplado del par en B.Cu queda igual.
    """
    def k(x, y):
        return pcbnew.VECTOR2I(pcbnew.FromMM(x + P.STL_OX), pcbnew.FromMM(P.STL_OY - y))
    a, via, codo = k(-72.75, -120.45), k(-72.60, -119.75), k(-72.60, -120.30)
    for t in list(board.GetTracks()):
        if t.GetNetname() != "USB_DP" or t.GetClass() != "PCB_TRACK":
            continue
        if {(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)} == {(a.x, a.y), (via.x, via.y)}:
            t.SetStart(a)
            t.SetEnd(codo)
            n = pcbnew.PCB_TRACK(board)
            n.SetStart(codo)
            n.SetEnd(via)
            n.SetWidth(t.GetWidth())
            n.SetLayer(t.GetLayer())
            n.SetNet(t.GetNet())
            n.SetLocked(True)
            board.Add(n)
            return 1
    return 0


def agudos(board):
    """Pares de tramos de la misma red y capa que forman un ángulo de menos de 90°."""
    from collections import defaultdict
    porpunto = defaultdict(list)
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.IsLocked():
            continue
        s, e = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
        porpunto[(t.GetLayer(), t.GetNetCode(), s)].append((t, s, e))
        porpunto[(t.GetLayer(), t.GetNetCode(), e)].append((t, e, s))
    malos = set()
    for lista in porpunto.values():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                t1, c, a = lista[i]
                t2, _, b = lista[j]
                v1 = (a[0] - c[0], a[1] - c[1])
                v2 = (b[0] - c[0], b[1] - c[1])
                n1, n2 = math.hypot(*v1), math.hypot(*v2)
                if n1 and n2 and (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2) > math.cos(math.radians(89.5)):
                    malos.add(t1.m_Uuid.AsString())
                    malos.add(t2.m_Uuid.AsString())
    return malos


def geometria(it):
    clase = it.GetClass()
    if clase == "PAD":
        ps = pcbnew.SHAPE_POLY_SET()
        capa = pcbnew.F_Cu if it.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        it.TransformShapeToPolygon(ps, capa, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
        o = ps.Outline(0)
        capas = [c for l, c in CAPAS.items() if it.IsOnLayer(l)]
        if it.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            capas = ["F", "I", "B"]
        return {"tipo": "pad", "capas": capas, "poly": [(mm(o.CPoint(k).x), mm(o.CPoint(k).y))
                                                         for k in range(o.PointCount())],
                "pos": [mm(it.GetPosition().x), mm(it.GetPosition().y)], "ref": it.GetParentFootprint().GetReference(),
                "num": it.GetNumber()}
    if clase == "PCB_VIA":
        return {"tipo": "via", "capas": ["F", "I", "B"], "pos": [mm(it.GetPosition().x), mm(it.GetPosition().y)],
                "r": mm(it.GetWidth(pcbnew.F_Cu)) / 2}
    if clase == "PCB_TRACK":
        return {"tipo": "pista", "capas": [CAPAS.get(it.GetLayer(), "?")], "a": [mm(it.GetStart().x), mm(it.GetStart().y)],
                "b": [mm(it.GetEnd().x), mm(it.GetEnd().y)], "w": mm(it.GetWidth())}
    return {"tipo": "zona"}


def main():
    salida = sys.argv[1]
    board = pcbnew.LoadBoard(P.PCB)
    print("Cuello del USB:", cuello_usb(board), "cambios")
    pcbnew.SaveBoard(P.PCB, board)
    datos = drc(P.PCB)
    borrar = set()
    for v in datos["violations"]:
        if v["type"] == "copper_edge_clearance":
            for i in v["items"]:
                if "In2.Cu" in i["description"] and ("Pista" in i["description"] or "Vía" in i["description"]):
                    borrar.add(i["uuid"])
    board = pcbnew.LoadBoard(P.PCB)
    borrar |= agudos(board)
    for u in borrar:
        it = item(board, u)
        if it is not None and not it.IsLocked():
            board.Delete(it)
    print("Quitadas por borde de In2 o ángulo agudo:", len(borrar))
    pcbnew.SaveBoard(P.PCB, board)
    for vuelta in range(8):
        datos = drc(P.PCB)
        puntas = [i["uuid"] for v in datos["violations"] if v["type"] in ("track_dangling", "via_dangling")
                  for i in v["items"]]
        if not puntas:
            break
        board = pcbnew.LoadBoard(P.PCB)
        n = 0
        for u in puntas:
            it = item(board, u)
            if it is not None and not it.IsLocked():
                board.Delete(it)
                n += 1
        pcbnew.SaveBoard(P.PCB, board)
        print("vuelta %d: %d puntas quitadas" % (vuelta, n))
        if n == 0:
            break
    datos = drc(P.PCB)
    board = pcbnew.LoadBoard(P.PCB)
    pend = []
    for u in datos["unconnected_items"]:
        a, b = [item(board, i["uuid"]) for i in u["items"]]
        if a is None or b is None:
            continue
        pend.append({"red": a.GetNetname(), "a": geometria(a), "b": geometria(b)})
    json.dump(pend, open(salida, "w"))
    print("Conexiones pendientes:", len(pend))


if __name__ == "__main__":
    main()
