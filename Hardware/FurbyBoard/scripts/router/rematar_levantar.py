#!/usr/bin/env python3
"""Levanta el cobre ajeno que encierra los pads de las conexiones que el remate no une.

Se ejecuta con el Python de KiCad:
    $KICAD_PY scripts/router/rematar_levantar.py <remate.json> <pendientes.json> [radio_mm]

Para cada conexión fallida, borra las pistas y vías no bloqueadas de otras redes que
pasan a menos de `radio_mm` (1,0 por defecto) de sus pads. Esas redes quedan pendientes y
se vuelven a unir en la siguiente vuelta de `rematar_prep.py` + `rutar.py --remate`.

Con `--caja REF[,REF...] margen_mm` limpia en cambio todo el cobre (también el bloqueado,
salvo el de PROTEGIDAS_CAJA) dentro del rectángulo de esos componentes más el margen, para
volver a rutar desde cero un grupo atascado.
"""
import json
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import params as P  # noqa: E402

# Potencia y lazos de los convertidores: no se levantan, el rutado en rejilla no los rehace
PROTEGIDAS = {"GND", "3V3", "VSYS", "V6", "BAT", "BAT_PAD", "VBUS", "VBUS_IN", "BST_SW", "BST_BOOT", "SW",
              "MOT_OUT1", "MOT_OUT2", "SPK_P", "SPK_N", "USB_DP", "USB_DN"}


def dist_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


PROTEGIDAS_CAJA = {"BST_SW", "USB_DP", "USB_DN"}


def limpiar_caja(refs, margen):
    board = pcbnew.LoadBoard(P.PCB)
    caja = None
    for fp in board.GetFootprints():
        if fp.GetReference() in refs:
            bb = fp.GetBoundingBox(False)
            caja = bb if caja is None else caja.Merge(bb) or caja
    caja.Inflate(pcbnew.FromMM(margen))
    borrar = [t for t in board.GetTracks() if t.GetNetname() not in PROTEGIDAS_CAJA
              and not (t.GetClass() == "PCB_VIA" and t.IsLocked() and t.GetNetname() == "GND")
              and caja.Contains(t.GetStart()) and caja.Contains(t.GetEnd())]
    for t in borrar:
        board.Delete(t)
    pcbnew.SaveBoard(P.PCB, board)
    print("Caja %s: %d tramos quitados" % (",".join(refs), len(borrar)))


def main():
    if sys.argv[1] == "--caja":
        limpiar_caja(sys.argv[2].split(","), float(sys.argv[3]))
        return
    fallidas = json.load(open(sys.argv[1]))["fallidas_det"]
    pend = json.load(open(sys.argv[2]))
    radio = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    centros = []
    for k in fallidas:
        p = pend[k]
        for g in (p["a"], p["b"]):
            if g["tipo"] == "pad":
                centros.append((p["red"], g["pos"]))
    board = pcbnew.LoadBoard(P.PCB)
    mm = pcbnew.ToMM
    borrar = []
    for t in board.GetTracks():
        if t.IsLocked() or t.GetNetname() in PROTEGIDAS:
            continue
        if t.GetClass() == "PCB_VIA":
            a = b = (mm(t.GetPosition().x), mm(t.GetPosition().y))
            r = mm(t.GetWidth(pcbnew.F_Cu)) / 2
        else:
            a = (mm(t.GetStart().x), mm(t.GetStart().y))
            b = (mm(t.GetEnd().x), mm(t.GetEnd().y))
            r = mm(t.GetWidth()) / 2
        for red, c in centros:
            if t.GetNetname() != red and dist_seg(c, a, b) - r < radio:
                borrar.append(t)
                break
    redes = sorted({t.GetNetname() for t in borrar})
    for t in borrar:
        board.Delete(t)
    pcbnew.SaveBoard(P.PCB, board)
    print("Levantados %d tramos de %d redes: %s" % (len(borrar), len(redes), ", ".join(redes)))


if __name__ == "__main__":
    main()
