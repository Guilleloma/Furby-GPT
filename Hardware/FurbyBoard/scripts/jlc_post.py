#!/usr/bin/env python3
"""Convierte la BOM y el fichero de posiciones de kicad-cli al formato de JLCPCB.

    python3 jlc_post.py <bom_raw.csv> <pos_raw.csv> <dir_salida>

Escribe bom-jlcpcb.csv (una línea por valor, huella y LCSC) y cpl-jlcpcb.csv.
Fuera quedan los pads de cable, TP, puentes, taladros y logo (sin LCSC ni
posición) y los DNP.

JLCPCB coloca cada pieza con la huella EasyEDA de su número LCSC, no con la de
KiCad. GIRO y ORIGEN salen de comparar, pad a pad, cada huella de KiCad 10 con
la EasyEDA de su LCSC (API de easyeda.com, consultada el 2026-10-24; las dos
con la y hacia abajo):

- GIRO: grados CCW vistos desde arriba que se suman a la rotación de KiCad.
  · SOT-23 (C20917) y SOT-23-5 «BR» (C53099, C7836): pin 1 al otro lado → 180.
  · SOT-23-5 «BL» (C236672), SOT-23-6 «BL» (C2687116), TSSOP-24 (C130204),
    WSON-8 DSG (C5139865), TQFN-16 (C910544) y PowerPAK 1212-8 (C553966, con los
    pines 1-4 y el pad de drenador): EasyEDA los dibuja girados → 270.
  · LED (C2286, C2297): EasyEDA numera el cátodo como pad 2, pero está a la
    izquierda, igual que el pad 1 (K) de KiCad → 0. Comparar por número de pad
    daría 180 y montaría los LED al revés.
  · Resistencias, condensadores, fusible, bobinas, pulsadores, VQFN del
    BQ24073 y del TPS61089, VSON del TPS63802, FPC y USB-C → 0.
- ORIGEN: dónde cae el origen de la huella EasyEDA en coordenadas locales de la
  huella de KiCad (mm, y hacia abajo). El CPL da la posición de ese origen.
  · USB-C HRO M-13C (C2848620): la huella de KiCad tiene el origen en la boca;
    el de EasyEDA está 4,70 mm hacia dentro de la placa.
  · ESP32-S3-WROOM-1 (C2913202): el de EasyEDA está 3,627 mm hacia los pines,
    lejos de la antena (y local +3,627).

Antes de pagar, revisar en el visor de JLCPCB el pin 1 de U1–U11, Q1–Q3 y la
polaridad de D1–D5: allí se puede girar cada pieza si algo no cuadra.
"""
import csv
import math
import os
import sys
from collections import OrderedDict

GIRO = {
    "C20917": 180, "C53099": 180, "C7836": 180,
    "C236672": 270, "C2687116": 270, "C130204": 270, "C5139865": 270, "C910544": 270, "C553966": 270,
    "C2286": 0, "C2297": 0,
}
ORIGEN = {
    "C2848620": (0.0, -4.700),
    "C2913202": (0.0, 3.627),
}


def read_bom(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_pos(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["Ref"]: r for r in csv.DictReader(f)}


def short_fp(fp):
    return fp.split(":", 1)[-1]


def posicion(p, lcsc):
    """Centro de la huella EasyEDA en el sistema del fichero de posiciones (y hacia arriba)."""
    x, y, rot = float(p["PosX"]), float(p["PosY"]), math.radians(float(p["Rot"]))
    dx, dy = ORIGEN.get(lcsc, (0.0, 0.0))
    dy = -dy    # local de KiCad (y hacia abajo) -> y hacia arriba
    return (x + dx * math.cos(rot) - dy * math.sin(rot), y + dx * math.sin(rot) + dy * math.cos(rot))


def build(rows, pos):
    keep = [r for r in rows if r["LCSC"].strip() and not r["DNP"].strip() and r["Ref"] in pos]
    groups = OrderedDict()
    for r in keep:
        key = (r["Value"], short_fp(r["Footprint"]), r["LCSC"].strip())
        groups.setdefault(key, []).append(r["Ref"])
    bom = [["Comment", "Designator", "Footprint", "LCSC Part #"]]
    for (val, fp, lcsc), refs in groups.items():
        bom.append([val, ",".join(refs), fp, lcsc])
    cpl = [["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]]
    for r in keep:
        p, lcsc = pos[r["Ref"]], r["LCSC"].strip()
        x, y = posicion(p, lcsc)
        rot = (float(p["Rot"]) + GIRO.get(lcsc, 0)) % 360.0
        layer = "Top" if p["Side"].lower().startswith("top") else "Bottom"
        cpl.append([r["Ref"], "%.3fmm" % x, "%.3fmm" % y, layer, "%.1f" % rot])
    return bom, cpl, keep


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def main():
    bom_raw, pos_raw, out = sys.argv[1:4]
    bom, cpl, keep = build(read_bom(bom_raw), read_pos(pos_raw))
    sin_posicion = [r["Ref"] for r in read_bom(bom_raw) if r["LCSC"].strip() and r["Ref"] not in read_pos(pos_raw)]
    if sin_posicion:
        raise SystemExit("Piezas con LCSC sin posición en el PCB: " + ", ".join(sin_posicion))
    write(os.path.join(out, "bom-jlcpcb.csv"), bom)
    write(os.path.join(out, "cpl-jlcpcb.csv"), cpl)
    ext = sorted({r["LCSC"].strip() for r in keep if r.get("JLC_Class", "").strip() == "ext"})
    print("BOM: %d líneas, %d piezas; %d referencias «extended»" % (len(bom) - 1, len(cpl) - 1, len(ext)))


if __name__ == "__main__":
    main()
