#!/usr/bin/env python3
"""Comprueba lo que el DRC de KiCad no ve de la colocación de la FurbyBoard.

Se ejecuta con el Python de KiCad, después de gen_pcb.py:
    $KICAD_PY scripts/comprobar_colocacion.py

1. TP, puentes, LED, botones y pads de cables, fuera de la batería (accesibles con ella montada).
2. Calzos de espuma de la batería sin componentes debajo.
3. Bajo la batería, solo piezas de altura conocida y por debajo del hueco de los calzos.
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as LAY  # noqa: E402
import params as P  # noqa: E402

HUECO_BAJO_BATERIA = 4.1        # calzos de espuma de 4,1 (ARQUITECTURA.md, sección 12)
MARGEN_ALTURA = 0.5
MARGEN_ACCESO = 0.3             # el pad del TP queda al menos a esto del borde de la batería

# Altura máxima de cada encapsulado según su datasheet (mm). El módulo es el apoyo
# delantero de la batería (con espuma de 1,0) y por eso puede asomar debajo.
ALTURAS = {
    "C_0603_1608Metric": 0.95, "R_0603_1608Metric": 0.55, "C_0805_2012Metric": 1.45,
    "R_0805_2012Metric": 0.65, "SOT-23": 1.25, "SOT-23-5": 1.45, "SOT-23-6": 1.45,
    "TSSOP-24_4.4x7.8mm_P0.65mm": 1.2, "TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm": 0.8,
    "Texas_DLA_VSON-10_2x3mm_P0.5mm": 1.0, "L_Changjiang_FHD4020S": 2.1,
    "MountingHole_2.3mm_M2": 1.6, "Logo_Furby_PixelArt": 0.0,
    "TestPoint_Pad_D1.5mm": 0.0, "SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm": 0.0,
    "Pads_1x07_P2.54mm": 0.0, "Pads_2x04_P2.54mm": 0.0,   # pads de cable sin montar
}
APOYOS = {"U4"}
ACCESIBLES = ("TP", "JP", "D", "SW")
PADS_CABLE = ("J2", "J3", "J4", "J5", "J7", "J8", "J9", "J10", "J11")


def stl(p):
    return pcbnew.ToMM(p.x) - P.STL_OX, P.STL_OY - pcbnew.ToMM(p.y)


def bateria():
    b = LAY.BATERIA
    cx, cy = b["centro"]
    g = math.radians(b["giro"])

    def distancia_dentro(x, y):
        """Positiva dentro de la batería: distancia al borde más cercano."""
        dx, dy = x - cx, y - cy
        u = dx * math.cos(g) + dy * math.sin(g)
        v = -dx * math.sin(g) + dy * math.cos(g)
        return min(b["ancho"] / 2 - abs(u), b["largo"] / 2 - abs(v))
    return distancia_dentro


def caja(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    x0, y1 = stl(bb.GetOrigin())
    x1, y0 = stl(bb.GetEnd())
    return x0, y0, x1, y1


def muestras(x0, y0, x1, y1, n=6):
    return [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * j / n) for i in range(n + 1) for j in range(n + 1)]


def main():
    board = pcbnew.LoadBoard(P.PCB)
    dentro = bateria()
    fallos = []
    bajo = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        nombre = str(fp.GetFPID().GetLibItemName())
        # Los TP de la cara inferior se miden con la placa fuera de la base: la batería (arriba)
        # no los tapa. Solo se exige fuera de la batería lo que va en la cara superior.
        if ref.startswith(ACCESIBLES) and ref.rstrip("0123456789") in ACCESIBLES and fp.GetLayer() == pcbnew.F_Cu:
            for pad in fp.Pads():
                x, y = stl(pad.GetPosition())
                r = max(pcbnew.ToMM(pad.GetSize(pcbnew.F_Cu).x), pcbnew.ToMM(pad.GetSize(pcbnew.F_Cu).y)) / 2
                if dentro(x, y) > -(r + MARGEN_ACCESO):
                    fallos.append("%s pad %s bajo la batería o a menos de %.1f de su borde" % (ref, pad.GetNumber(), MARGEN_ACCESO))
        if ref in PADS_CABLE:
            for pad in fp.Pads():
                if dentro(*stl(pad.GetPosition())) > 0:
                    fallos.append("%s pad %s (cable) bajo la batería" % (ref, pad.GetNumber()))
        x0, y0, x1, y1 = caja(fp)
        for cx, cy, calzo in LAY.CALZOS:
            px, py = min(max(cx, x0), x1), min(max(cy, y0), y1)
            if math.dist((px, py), (cx, cy)) < LAY.CALZO_D / 2 and nombre != "Logo_Furby_PixelArt":
                fallos.append("%s invade el calzo %s" % (ref, calzo))
        if any(dentro(x, y) > 0 for x, y in muestras(x0, y0, x1, y1)) and ref not in APOYOS:
            if ref in PADS_CABLE:
                continue
            h = ALTURAS.get(nombre)
            if h is None:
                fallos.append("%s (%s) bajo la batería sin altura conocida" % (ref, nombre))
            elif h > HUECO_BAJO_BATERIA - MARGEN_ALTURA:
                fallos.append("%s (%s, %.2f mm) no cabe bajo la batería" % (ref, nombre, h))
            else:
                bajo.append((h, ref))
    for cx, cy, calzo in LAY.CALZOS:
        if dentro(cx, cy) < LAY.CALZO_D / 2:
            fallos.append("El calzo %s no queda entero bajo la batería" % calzo)
    # Franja del flex de la cámara (de J6 a la pared): ninguna otra pieza debajo del flex.
    fl = LAY.FLEX_SIN_PIEZAS
    for fp in board.GetFootprints():
        if fp.GetReference() == "J6" or fp.GetLayer() != pcbnew.F_Cu:
            continue
        x0, y0, x1, y1 = caja(fp)
        if x0 < fl["x"][1] and x1 > fl["x"][0] and y0 < fl["y"][1] and y1 > fl["y"][0]:
            fallos.append("%s bajo el flex de la cámara" % fp.GetReference())
    bajo.sort(reverse=True)
    print("Bajo la batería: %d piezas, la más alta %s con %.2f mm (hueco %.1f)"
          % (len(bajo), bajo[0][1], bajo[0][0], HUECO_BAJO_BATERIA))
    for f in fallos:
        print("FALLO ", f)
    if not fallos:
        print("OK     TP, puentes, LED y botones accesibles; calzos libres; alturas bajo la batería")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
