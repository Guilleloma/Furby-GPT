#!/usr/bin/env python3
"""Huella de KiCad con el logo de GuilleMaker para la serigrafía inferior de la FurbyBoard.

Fuente versionada: serigrafia/logo-guillemaker.png (gris, recortado y sin metadatos). Se
crea una vez con --importar <png> a partir del logo original (negro sobre blanco o sobre
transparente).

Proceso, al ancho pedido:
1. Escala a 0,01 mm por píxel y umbral al 50 %.
2. Mínimos de JLCPCB (trazo y hueco de 0,15 mm): se mide qué parte de la tinta y de los huecos
   queda por debajo (una apertura con un disco de 0,15 mm) y se informa. Engrosar o abrir a la
   fuerza dejaba bordes con dientes; el ancho se elige para que lo fino sean solo puntas.
   Se quitan las motas y los agujeros de menos de 0,15 × 0,15 mm.
3. Contornos (contourpy) simplificados con Ramer-Douglas-Peucker (5 µm). Los agujeros de cada
   polígono (la «a», la «e», el interior del círculo…) se unen a su contorno exterior con un
   corte de ancho cero, porque fp_poly es un solo contorno.

Escribe lib/FurbyBoard.pretty/Logo_GuilleMaker.kicad_mod: polígonos rellenos en F.SilkS (la
huella va en la cara inferior y KiCad la espeja, así que se lee mirando la placa desde abajo)
y un courtyard con la silueta (círculo del símbolo y caja del texto), que gen_pcb.py usa para
buscarle sitio sin vías, pads, rótulos ni otros courtyards.

Uso (desde Hardware/FurbyBoard):
    python3 -I scripts/logo_guillemaker.py [--ancho 11.0] [--importar <png>]
Requiere: numpy, Pillow y matplotlib (trae contourpy).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from contourpy import FillType, contour_generator
from PIL import Image, ImageFilter

DIR = Path(__file__).resolve().parent.parent
FUENTE = DIR / "serigrafia" / "logo-guillemaker.png"
HUELLA = DIR / "lib" / "FurbyBoard.pretty" / "Logo_GuilleMaker.kicad_mod"

ANCHO_MM = 11.0              # lo que cabe en la cara inferior sin vías dentro de la silueta (gen_pcb.py)
RES_MM = 0.01                # rejilla de trabajo
SERIGRAFIA_MIN_MM = 0.15     # trazo y hueco mínimos de JLCPCB (fabricante-jlcpcb.md)
SIMPLIFICA_MM = 0.005
MARGEN_SILUETA_MM = 0.0      # courtyard = silueta de la tinta; los márgenes los pone serigrafia.py
MARGEN_IMPORTAR_PX = 4


# ---------------------------------------------------------------- imagen


def importar(origen):
    """Copia limpia del logo: gris sobre blanco, recortada a la tinta y sin metadatos."""
    im = Image.open(origen).convert("RGBA")
    fondo = Image.new("RGBA", im.size, "white")
    fondo.alpha_composite(im)
    gris = fondo.convert("L")
    filas, cols = np.nonzero(np.asarray(gris) < 128)
    m = MARGEN_IMPORTAR_PX
    caja = (max(cols.min() - m, 0), max(filas.min() - m, 0),
            min(cols.max() + 1 + m, gris.width), min(filas.max() + 1 + m, gris.height))
    recorte = gris.crop(caja)
    limpia = Image.frombytes("L", recorte.size, recorte.tobytes())   # imagen nueva: sin info ni EXIF
    FUENTE.parent.mkdir(parents=True, exist_ok=True)
    limpia.save(FUENTE, optimize=True)
    print(f"Escrito {FUENTE.relative_to(DIR)}: {limpia.width} × {limpia.height} px")


def tinta_a_escala(ancho_mm):
    """Máscara de tinta a RES_MM por píxel, con un borde vacío para la morfología."""
    gris = Image.open(FUENTE).convert("L")
    filas, cols = np.nonzero(np.asarray(gris) < 128)
    gris = gris.crop((cols.min(), filas.min(), cols.max() + 1, filas.max() + 1))
    f = ancho_mm / RES_MM / gris.width
    gris = gris.resize((round(gris.width * f), round(gris.height * f)), Image.BICUBIC)
    borde = 40
    tinta = np.zeros((gris.height + 2 * borde, gris.width + 2 * borde), bool)
    tinta[borde:-borde, borde:-borde] = np.asarray(gris) < 128
    return tinta


def disco(diametro_px):
    r = (diametro_px - 1) / 2
    n = int(r)
    return [(i, j) for i in range(-n, n + 1) for j in range(-n, n + 1) if i * i + j * j <= r * r + 0.25]


def erosiona(m, diametro_px):
    out = m.copy()
    for i, j in disco(diametro_px):
        out &= np.roll(m, (i, j), (0, 1))
    return out


def dilata(m, diametro_px):
    out = m.copy()
    for i, j in disco(diametro_px):
        out |= np.roll(m, (i, j), (0, 1))
    return out


def estrechos(m, diametro_px):
    """Partes de m más estrechas que el disco (lo que se lleva una apertura)."""
    return m & ~dilata(erosiona(m, diametro_px), diametro_px)


def cerca(m, diametro_px):
    return dilata(m, diametro_px) & ~m


def mide_minimos(tinta):
    """Fracción de la tinta más estrecha que el mínimo y de los huecos junto a la tinta más estrechos."""
    d = int(round(SERIGRAFIA_MIN_MM / RES_MM)) | 1
    junto = cerca(tinta, d)
    return estrechos(tinta, d).sum() / tinta.sum(), (estrechos(~tinta, d) & junto).sum() / junto.sum()


# ---------------------------------------------------------------- contornos


def rdp(puntos, tol):
    """Ramer-Douglas-Peucker iterativo sobre una polilínea abierta (array N × 2)."""
    guarda = np.zeros(len(puntos), bool)
    guarda[0] = guarda[-1] = True
    pila = [(0, len(puntos) - 1)]
    while pila:
        a, b = pila.pop()
        if b - a < 2:
            continue
        p, q = puntos[a], puntos[b]
        seg = puntos[a + 1:b] - p
        d = q - p
        n = np.hypot(*d)
        dist = np.abs(seg[:, 0] * d[1] - seg[:, 1] * d[0]) / n if n else np.hypot(seg[:, 0], seg[:, 1])
        k = int(np.argmax(dist))
        if dist[k] > tol:
            guarda[a + 1 + k] = True
            pila += [(a, a + 1 + k), (a + 1 + k, b)]
    return puntos[guarda]


def area(anillo):
    x, y = anillo[:, 0], anillo[:, 1]
    return abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2


def anillo_simple(puntos, tol):
    """Contorno cerrado simplificado (sin repetir el primer punto)."""
    if np.allclose(puntos[0], puntos[-1]):
        puntos = puntos[:-1]
    k = int(np.argmax(np.hypot(*(puntos - puntos[0]).T)))   # dos mitades: RDP no admite lazos cerrados
    a = rdp(np.vstack([puntos[:k + 1]]), tol)
    b = rdp(np.vstack([puntos[k:], puntos[:1]]), tol)
    return np.vstack([a, b[1:-1]])


def se_cortan(p, q, a, b):
    """¿Corta el segmento p-q a alguno de los segmentos a[i]-b[i]? (sin contar extremos comunes)"""
    def lado(o, u, v):
        return (u[..., 0] - o[..., 0]) * (v[..., 1] - o[..., 1]) - (u[..., 1] - o[..., 1]) * (v[..., 0] - o[..., 0])
    d1, d2 = lado(a, b, p), lado(a, b, q)
    d3, d4 = lado(p, q, a), lado(p, q, b)
    return bool(np.any((d1 * d2 < 0) & (d3 * d4 < 0)))


def aristas(*anillos):
    a = np.vstack([r for r in anillos])
    b = np.vstack([np.roll(r, -1, 0) for r in anillos])
    return a, b


def une_agujeros(exterior, agujeros):
    """Une cada agujero al contorno con un corte de ancho cero, sin cruzar ninguna arista."""
    contorno = exterior
    pendientes = sorted(agujeros, key=lambda h: h[:, 0].min())
    while pendientes:
        h = pendientes.pop(0)
        j = int(np.argmin(h[:, 0]))
        orden = np.argsort(np.hypot(*(contorno - h[j]).T))
        a, b = aristas(contorno, h, *pendientes)
        for i in orden:
            if not se_cortan(h[j], contorno[i], a, b):
                break
        else:
            raise SystemExit("No se encuentra un corte limpio para un agujero del logo")
        contorno = np.vstack([contorno[:i + 1], h[j:], h[:j + 1], contorno[i:]])
    return contorno


def poligonos(tinta):
    """Contornos de la tinta en mm, centrados en la caja de la tinta, con los agujeros unidos."""
    suave = np.asarray(Image.fromarray((tinta * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)))
    filas, cols = np.nonzero(tinta)
    cy, cx = (filas.min() + filas.max() + 1) / 2, (cols.min() + cols.max() + 1) / 2
    gen = contour_generator(z=suave.astype(float) / 255, fill_type=FillType.OuterOffset)
    puntos, offsets = gen.filled(0.5, 2.0)
    tol = SIMPLIFICA_MM / RES_MM
    salida = []
    for pts, off in zip(puntos, offsets):
        anillos = [anillo_simple(pts[off[k]:off[k + 1]], tol) for k in range(len(off) - 1)]
        minima = (SERIGRAFIA_MIN_MM / RES_MM) ** 2
        if len(anillos[0]) < 3 or area(anillos[0]) < minima:
            continue    # mota
        anillos = anillos[:1] + [r for r in anillos[1:] if len(r) >= 3 and area(r) >= minima]
        poli = une_agujeros(anillos[0], anillos[1:])
        salida.append((poli - (cx, cy)) * RES_MM)
    return salida


def silueta(tinta):
    """Círculo del símbolo y caja del texto, en mm desde el centro de la tinta.

    El texto empieza tras el mayor tramo de filas sin tinta."""
    filas, cols = np.nonzero(tinta)
    cy, cx = (filas.min() + filas.max() + 1) / 2, (cols.min() + cols.max() + 1) / 2
    con_tinta = np.nonzero(tinta.any(1))[0]
    salto = int(np.argmax(np.diff(con_tinta)))
    simbolo, texto = tinta[:con_tinta[salto] + 1], tinta[con_tinta[salto + 1]:]
    fs, cs = np.nonzero(simbolo)
    ft, ct = np.nonzero(texto)
    ft = ft + con_tinta[salto + 1]
    m = MARGEN_SILUETA_MM
    circulo = (((cs.min() + cs.max() + 1) / 2 - cx) * RES_MM, ((fs.min() + fs.max() + 1) / 2 - cy) * RES_MM,
               max(cs.max() + 1 - cs.min(), fs.max() + 1 - fs.min()) / 2 * RES_MM + m)
    caja = ((ct.min() - cx) * RES_MM - m, (ft.min() - cy) * RES_MM - m,
            (ct.max() + 1 - cx) * RES_MM + m, (ft.max() + 1 - cy) * RES_MM + m)
    return circulo, caja, (ft.max() + 1 - ft.min()) * RES_MM


# ---------------------------------------------------------------- huella


def mm(valor):
    return f"{valor:.4f}".rstrip("0").rstrip(".")


def huella(polis, circulo, caja, ancho, alto):
    lineas = [
        '(footprint "Logo_GuilleMaker"',
        "\t(version 20260206)",
        '\t(generator "logo_guillemaker")',
        '\t(layer "F.Cu")',
        f'\t(descr "Logo @GuilleMaker, {mm(ancho)} x {mm(alto)} mm. Generado por scripts/logo_guillemaker.py '
        f'desde serigrafia/logo-guillemaker.png; no editar a mano")',
        '\t(tags "logo serigrafia guillemaker")',
        '\t(property "Reference" "LOGO**" (at 0 0 0) (layer "F.SilkS") (hide yes) '
        "(effects (font (size 1 1) (thickness 0.15))))",
        '\t(property "Value" "Logo_GuilleMaker" (at 0 0 0) (layer "F.Fab") (hide yes) '
        "(effects (font (size 1 1) (thickness 0.15))))",
        "\t(attr board_only exclude_from_pos_files exclude_from_bom)",
    ]
    for p in polis:
        pts = " ".join(f"(xy {mm(x)} {mm(y)})" for x, y in p)
        lineas.append(f'\t(fp_poly (pts {pts}) (stroke (width 0) (type solid)) (fill yes) (layer "F.SilkS"))')
    cx, cy, r = circulo
    for capa in ("F.CrtYd", "F.Fab"):
        lineas.append(f"\t(fp_circle (center {mm(cx)} {mm(cy)}) (end {mm(cx + r)} {mm(cy)}) "
                      f'(stroke (width 0.05) (type solid)) (fill no) (layer "{capa}"))')
        lineas.append(f"\t(fp_rect (start {mm(caja[0])} {mm(caja[1])}) (end {mm(caja[2])} {mm(caja[3])}) "
                      f'(stroke (width 0.05) (type solid)) (fill no) (layer "{capa}"))')
    lineas.append(")")
    return "\n".join(lineas) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ancho", type=float, default=ANCHO_MM, help="ancho del logo en mm (11,0)")
    parser.add_argument("--importar", type=Path, help="crea serigrafia/logo-guillemaker.png desde este PNG")
    args = parser.parse_args()
    if args.importar:
        importar(args.importar)
    tinta = tinta_a_escala(args.ancho)
    fino, hueco = mide_minimos(tinta)
    polis = poligonos(tinta)
    circulo, caja, alto_texto = silueta(tinta)
    filas, cols = np.nonzero(tinta)
    ancho, alto = (cols.max() + 1 - cols.min()) * RES_MM, (filas.max() + 1 - filas.min()) * RES_MM
    HUELLA.write_text(huella(polis, circulo, caja, ancho, alto), encoding="utf-8")
    print(f"Escrito {HUELLA.relative_to(DIR)}: {ancho:.2f} × {alto:.2f} mm, {len(polis)} polígonos, "
          f"{sum(len(p) for p in polis)} vértices; texto de {alto_texto:.2f} mm de alto")
    print(f"Por debajo de {SERIGRAFIA_MIN_MM} mm (puntas y esquinas incluidas): {100 * fino:.1f} % de la tinta, "
          f"{100 * hueco:.1f} % del fondo junto a la tinta")
    return 0


if __name__ == "__main__":
    sys.exit(main())
