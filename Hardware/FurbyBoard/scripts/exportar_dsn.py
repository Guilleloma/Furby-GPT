#!/usr/bin/env python3
"""Exporta scripts/rutado.dsn (Specctra) para autorrutar la FurbyBoard con Freerouting.

Se ejecuta con el Python de KiCad, después de gen_pcb.py --sin-rutado:
    $KICAD_PY scripts/exportar_dsn.py

Va en un proceso aparte porque el DSN solo lleva las clases de red del .kicad_pro
cuando el PCB se carga del disco en un proceso limpio. Lleva bloqueadas las pistas
de rutas_fijas.py, In1 (GND) e In2 (VSYS) como planos, las áreas sin cobre y una
franja prohibida junto al borde (no se guarda en el PCB).

Freerouting (fuera del repositorio):
    java -jar freerouting.jar -de scripts/rutado.dsn -do scripts/rutado.ses -mp 100
y luego gen_pcb.py sin --sin-rutado importa scripts/rutado.ses.
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P  # noqa: E402

# Freerouting no conoce el margen a borde de KiCad (0,3) y usa el margen general (0,15):
# se le da una franja prohibida de este ancho a lo largo de todo el contorno.
FRANJA_BORDE = P.RULE_EDGE_CLEARANCE + 0.02


def franja_borde(board):
    """Áreas sin pistas ni vías pegadas al contorno (y al agujero del mecanismo), solo para el DSN.

    Cada tramo del contorno se engorda FRANJA_BORDE a cada lado: rectángulos convexos, que
    Freerouting lee bien (un anillo de una pieza, con su corte, no lo carga)."""
    borde = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(borde, True)
    w = pcbnew.FromMM(FRANJA_BORDE)
    cadenas = [borde.Outline(0)] + [borde.Hole(0, k) for k in range(borde.HoleCount(0))]
    for cadena in cadenas:
        n = cadena.PointCount()
        for k in range(n):
            a, b = cadena.CPoint(k), cadena.CPoint((k + 1) % n)
            dx, dy = b.x - a.x, b.y - a.y
            largo = math.hypot(dx, dy)
            if largo < 1:
                continue
            ux, uy = dx / largo * w, dy / largo * w
            nx, ny = -uy, ux
            esquinas = [(a.x - ux + nx, a.y - uy + ny), (b.x + ux + nx, b.y + uy + ny),
                        (b.x + ux - nx, b.y + uy - ny), (a.x - ux - nx, a.y - uy - ny)]
            z = pcbnew.ZONE(board)
            capas = pcbnew.LSET()
            capas.AddLayer(pcbnew.F_Cu)
            capas.AddLayer(pcbnew.B_Cu)
            z.SetLayerSet(capas)
            z.SetIsRuleArea(True)
            z.SetDoNotAllowTracks(True)
            z.SetDoNotAllowVias(True)
            z.SetDoNotAllowPads(False)
            z.SetDoNotAllowZoneFills(False)
            z.SetDoNotAllowFootprints(False)
            ol = z.Outline()
            ol.NewOutline()
            for x, y in esquinas:
                ol.Append(int(x), int(y))
            board.Add(z)


if __name__ == "__main__":
    dsn = os.path.join(P.ROOT, "scripts", "rutado.dsn")
    board = pcbnew.LoadBoard(P.PCB)
    # El relleno de VSYS de In2 (capa de señal) iría al DSN como plano y taparía la capa:
    # fuera para el autorrutado; los rellenos de F.Cu/B.Cu tampoco existen aún.
    for z in list(board.Zones()):
        if not z.GetIsRuleArea() and z.GetLayer() != pcbnew.In1_Cu:
            board.Remove(z)
    franja_borde(board)
    ok = pcbnew.ExportSpecctraDSN(board, dsn)
    print("DSN exportado:" if ok else "ERROR al exportar el DSN:", os.path.relpath(dsn, P.ROOT))
    sys.exit(0 if ok else 1)
