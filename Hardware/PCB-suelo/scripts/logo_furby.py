#!/usr/bin/env python3
"""Huella de KiCad con el logo «Furby» en pixel art para la serigrafía de la FurbyBoard.

Lee la matriz de píxeles versionada en serigrafia/logo-furby-pixelart.txt
(X = tinta, . = sin tinta, o = sin tinta y, con --cobre, cobre visto) y escribe:

- kicad/Furby.pretty/Logo_Furby_PixelArt.kicad_mod: cada tramo horizontal de
  píxeles con tinta es un polígono relleno en F.SilkS. La huella se coloca en
  la cara inferior (KiCad la pasa a B.SilkS y la espeja, así que se lee bien
  mirando la placa desde abajo). Lleva un courtyard que marca la zona sin
  pads ni vías.
- render/logo-furby.png: vista previa a escala, como se verá desde abajo.

Con --cobre, los píxeles «o» (las pupilas) son pads SMD sin red ni pasta: el
cobre queda visto con el acabado de la placa (HASL plateado o ENIG dorado).

Mínimos de JLCPCB para serigrafía: trazo de 0,153 mm y separación de 0,15 mm.
Con píxeles de 0,40 mm, el detalle más fino (un píxel o un hueco de un
píxel) los cumple de sobra.

Uso (desde Hardware/PCB-suelo):
    python -I scripts/logo_furby.py [--pixel 0.40] [--cobre]
Requiere: matplotlib (ver scripts/requirements.txt).
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

DIR = Path(__file__).resolve().parent.parent
MATRIZ = DIR / "serigrafia" / "logo-furby-pixelart.txt"
HUELLA = DIR / "kicad" / "Furby.pretty" / "Logo_Furby_PixelArt.kicad_mod"
VISTA_PREVIA = DIR / "render" / "logo-furby.png"

PIXEL_MM = 0.40
SERIGRAFIA_MIN_MM = 0.153       # trazo y separación mínimos de JLCPCB
MARGEN_COURTYARD_MM = 0.5


def leer_matriz(ruta):
    filas = [linea.rstrip("\n") for linea in ruta.read_text(encoding="utf-8").splitlines()
             if linea.strip() and not linea.startswith(";")]
    ancho = len(filas[0])
    if any(len(f) != ancho for f in filas):
        raise SystemExit(f"{ruta}: todas las filas tienen que medir {ancho} caracteres")
    if set("".join(filas)) - set("X.o"):
        raise SystemExit(f"{ruta}: solo se admiten X, . y o")
    if any(f != f[::-1] for f in filas):
        raise SystemExit(f"{ruta}: el dibujo tiene que ser simétrico")
    return filas


def tramos(filas, simbolo):
    """Tramos horizontales (fila, columna inicial, columna final exclusiva) de un símbolo."""
    for r, fila in enumerate(filas):
        c = 0
        while c < len(fila):
            if fila[c] == simbolo:
                inicio = c
                while c < len(fila) and fila[c] == simbolo:
                    c += 1
                yield r, inicio, c
            else:
                c += 1


def mm(valor):
    return f"{valor:.4f}".rstrip("0").rstrip(".")


def huella(filas, pixel, cobre):
    alto, ancho = len(filas), len(filas[0])
    x0, y0 = -ancho * pixel / 2, -alto * pixel / 2

    def caja(r, c0, c1):
        xa, xb = x0 + c0 * pixel, x0 + c1 * pixel
        ya, yb = y0 + r * pixel, y0 + (r + 1) * pixel
        return xa, ya, xb, yb

    lineas = [
        '(footprint "Logo_Furby_PixelArt"',
        "\t(version 20260206)",
        '\t(generator "logo_furby")',
        '\t(layer "F.Cu")',
        f'\t(descr "Logo Furby en pixel art de 1 bit, {ancho} x {alto} px de {mm(pixel)} mm '
        f'({mm(ancho * pixel)} x {mm(alto * pixel)} mm). Generado por scripts/logo_furby.py; no editar a mano")',
        '\t(tags "logo serigrafia furby")',
        '\t(property "Reference" "LOGO**" (at 0 0 0) (layer "F.SilkS") (hide yes) '
        "(effects (font (size 1 1) (thickness 0.15))))",
        '\t(property "Value" "Logo_Furby_PixelArt" (at 0 0 0) (layer "F.Fab") (hide yes) '
        "(effects (font (size 1 1) (thickness 0.15))))",
        "\t(attr board_only exclude_from_pos_files exclude_from_bom)",
    ]
    for r, c0, c1 in tramos(filas, "X"):
        xa, ya, xb, yb = caja(r, c0, c1)
        lineas.append(f"\t(fp_poly (pts (xy {mm(xa)} {mm(ya)}) (xy {mm(xb)} {mm(ya)}) (xy {mm(xb)} {mm(yb)}) "
                      f"(xy {mm(xa)} {mm(yb)})) (stroke (width 0) (type solid)) (fill yes) (layer \"F.SilkS\"))")
    if cobre:
        for n, (r, c0, c1) in enumerate(tramos(filas, "o"), start=1):
            xa, ya, xb, yb = caja(r, c0, c1)
            lineas.append(f'\t(pad "" smd rect (at {mm((xa + xb) / 2)} {mm((ya + yb) / 2)}) '
                          f'(size {mm(xb - xa)} {mm(yb - ya)}) (layers "F.Cu" "F.Mask"))')
    m = MARGEN_COURTYARD_MM
    xa, ya, xb, yb = x0 - m, y0 - m, -x0 + m, -y0 + m
    for capa in ("F.CrtYd", "F.Fab"):
        lineas.append(f"\t(fp_rect (start {mm(xa)} {mm(ya)}) (end {mm(xb)} {mm(yb)}) "
                      f"(stroke (width 0.05) (type solid)) (fill no) (layer \"{capa}\"))")
    lineas.append(f'\t(fp_text user "sin pads ni vías bajo el logo" (at 0 {mm(yb + 0.6)} 0) (layer "F.Fab") '
                  "(effects (font (size 0.5 0.5) (thickness 0.08))))")
    lineas.append(")")
    return "\n".join(lineas) + "\n"


def vista_previa(filas, pixel, cobre):
    alto, ancho = len(filas), len(filas[0])
    fig, ax = plt.subplots(figsize=(5, 5 * alto / ancho + 0.6), dpi=150)
    ax.set_facecolor("#1d6b3f")
    for r, fila in enumerate(filas):
        for c, ch in enumerate(fila):
            x, y = c * pixel, (alto - 1 - r) * pixel
            if ch == "X":
                ax.add_patch(Rectangle((x, y), pixel, pixel, fc="#f4f4f4", ec="none"))
            elif ch == "o" and cobre:
                ax.add_patch(Rectangle((x, y), pixel, pixel, fc="#d4ac0d", ec="none"))
    ax.set_xlim(-pixel, (ancho + 1) * pixel)
    ax.set_ylim(-pixel, (alto + 1) * pixel)
    ax.set_aspect("equal")
    ax.set_xlabel("mm")
    ax.set_title(f"Logo Furby · {ancho} × {alto} px de {mm(pixel)} mm = "
                 f"{mm(ancho * pixel)} × {mm(alto * pixel)} mm".replace(".", ","), fontsize=9)
    fig.tight_layout()
    VISTA_PREVIA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(VISTA_PREVIA)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pixel", type=float, default=PIXEL_MM, help="lado del píxel en mm (0,40)")
    parser.add_argument("--cobre", action="store_true", help="pupilas en cobre visto (pads sin red)")
    args = parser.parse_args()
    if args.pixel < SERIGRAFIA_MIN_MM:
        raise SystemExit(f"El píxel de {args.pixel} mm baja del mínimo de JLCPCB ({SERIGRAFIA_MIN_MM} mm)")
    filas = leer_matriz(MATRIZ)
    HUELLA.write_text(huella(filas, args.pixel, args.cobre), encoding="utf-8")
    vista_previa(filas, args.pixel, args.cobre)
    print(f"Escritos {HUELLA.relative_to(DIR)} y {VISTA_PREVIA.relative_to(DIR)}: "
          f"{len(filas[0])} × {len(filas)} px, {len(filas[0]) * args.pixel:.2f} × {len(filas) * args.pixel:.2f} mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
