#!/usr/bin/env python3
"""Vías térmicas bajo los pads expuestos (al plano de GND de In1), fijas.

Se ejecuta con el Python de KiCad, antes de exportar el DSN:
    $KICAD_PY scripts/router/vias_termicas.py

Rejilla de vías de 0,6/0,3 dentro de cada pad expuesto, como piden las hojas de
datos (BQ24073 y MAX98357A: vías al plano bajo el pad; DRV8231A: pad térmico a GND;
WROOM-1: pad de GND central). Son vías bajo pad expuesto, no en pads de soldadura de
pines; JLCPCB las tapa por la cara inferior.
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import params as P  # noqa: E402

# referencia -> (número de pad expuesto, filas, columnas, paso en mm)
PADS_EXPUESTOS = {
    "U2": ("17", 2, 2, 0.9),     # VQFN-16, pad 1,6 × 1,6
    "U7": ("17", 1, 1, 0.0),     # TQFN-16, pad 1,23 × 1,23
    "U6": ("9", 2, 1, 0.8),      # WSON-8, pad 0,9 × 1,6
    "U4": ("41", 3, 3, 1.2),     # WROOM-1, pad de GND 3,7 × 3,7
}


def main():
    board = pcbnew.LoadBoard(P.PCB)
    gnd = board.FindNet("GND")
    n = 0
    for ref, (num, filas, cols, paso) in PADS_EXPUESTOS.items():
        fp = board.FindFootprintByReference(ref)
        pad = [p for p in fp.Pads() if p.GetNumber() == num and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD][0]
        c = pad.GetPosition()
        # el pad puede ser más largo en una dirección: las filas siguen su lado mayor
        tam = pad.GetBoundingBox()
        vertical = tam.GetHeight() >= tam.GetWidth()
        for i in range(filas):
            for j in range(cols):
                di = (i - (filas - 1) / 2) * paso
                dj = (j - (cols - 1) / 2) * paso
                dx, dy = (dj, di) if vertical else (di, dj)
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(c.x + pcbnew.FromMM(dx), c.y + pcbnew.FromMM(dy)))
                v.SetWidth(pcbnew.FromMM(P.RULE_VIA_DIAM))
                v.SetDrill(pcbnew.FromMM(P.RULE_VIA_DRILL))
                v.SetNet(gnd)
                v.SetLocked(True)
                board.Add(v)
                n += 1
    pcbnew.SaveBoard(P.PCB, board)
    print("Vías térmicas:", n)


if __name__ == "__main__":
    main()
