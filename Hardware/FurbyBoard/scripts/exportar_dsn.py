#!/usr/bin/env python3
"""Exporta scripts/rutado.dsn (Specctra) para autorrutar la FurbyBoard con Freerouting.

Se ejecuta con el Python de KiCad, después de gen_pcb.py --sin-rutado:
    $KICAD_PY scripts/exportar_dsn.py

Va en un proceso aparte porque el DSN solo lleva las clases de red del .kicad_pro
cuando el PCB se carga del disco en un proceso limpio. Lleva bloqueadas las pistas
de rutas_fijas.py, In1 (GND) e In2 (VSYS) como planos y las áreas sin cobre.

Freerouting (fuera del repositorio):
    java -jar freerouting.jar -de scripts/rutado.dsn -do scripts/rutado.ses -mp 100
y luego gen_pcb.py sin --sin-rutado importa scripts/rutado.ses.
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P  # noqa: E402

if __name__ == "__main__":
    dsn = os.path.join(P.ROOT, "scripts", "rutado.dsn")
    ok = pcbnew.ExportSpecctraDSN(pcbnew.LoadBoard(P.PCB), dsn)
    print("DSN exportado:" if ok else "ERROR al exportar el DSN:", os.path.relpath(dsn, P.ROOT))
    sys.exit(0 if ok else 1)
