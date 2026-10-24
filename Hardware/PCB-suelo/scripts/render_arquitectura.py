#!/usr/bin/env python3
"""Renders de la propuesta de arquitectura de la FurbyBoard v1.0 (ver ARQUITECTURA.md).

Dibuja dos figuras:

- render/planta-arquitectura.png: colocación por bloques sobre el contorno real
  de la PCB (geometria.json). La batería va en una bandeja elevada; debajo,
  parte del ESP32-S3-WROOM-1 y los bloques bajos que no calientan. Fuera de la
  batería van la antena del módulo, los bloques de potencia, el conector de la
  cámara, los pads de los cables del Furby, el header de expansión, los puntos
  de test, los LED y los botones.
- render/bloques.png: diagrama de bloques eléctrico.

Antes de dibujar comprueba la colocación:

- todo lo de la cara superior queda dentro de la PCB, fuera de la exclusión del
  mecanismo, de las cabezas de los tornillos y del USB-C, y sin solapes;
- en la zona sin cobre de la antena solo está el módulo;
- la batería queda dentro de la pared interior, lejos del agujero del
  mecanismo y de la antena, y solo tapa lo marcado como «bajo la bandeja»;
- los puntos de test, el header, los botones y los LED quedan fuera de la
  batería, accesibles con ella montada.

Si algo falla, sale con código 1 y no escribe nada.

Es una propuesta de arquitectura: los bloques son envolventes aproximadas de
cada circuito con sus pasivos, no huellas. El layout real es de la fase 2.

Uso (desde Hardware/PCB-suelo):
    python -I scripts/render_arquitectura.py
Requiere: numpy, matplotlib, shapely (ver scripts/requirements.txt).
"""

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon as ParchePoligono  # noqa: E402
from shapely import affinity  # noqa: E402
from shapely.geometry import Point, Polygon, box  # noqa: E402

DIR = Path(__file__).resolve().parent.parent
GEOMETRIA = DIR / "geometria.json"
RENDER_PLANTA = DIR / "render" / "planta-arquitectura.png"
RENDER_BLOQUES = DIR / "render" / "bloques.png"

HOLGURA_PARED_MM = 0.5          # la pared interior está a 0,5 del borde de la PCB
CABEZA_TORNILLO_D_MM = 5.0      # zona libre alrededor de cada taladro (cabeza M2 Ø4 + margen)
MARGEN_BORDE_MM = 0.3           # bloque a borde de PCB
MARGEN_EXCLUSION_MM = 0.5       # bloque a la exclusión Ø15,3 del mecanismo
MARGEN_BATERIA_AGUJERO_MM = 1.5  # batería al agujero Ø11,3 del mecanismo, como mínimo
MARGEN_BATERIA_ANTENA_MM = 4.0   # batería a la antena del módulo, en planta, como mínimo

BATERIA = {"centro": (-84.5, -91.8), "ancho": 33.0, "largo": 50.0, "giro": -4.0}
BATERIA_Z = (10.1, 17.7)        # cara inferior y superior sobre la bandeja

# ESP32-S3-WROOM-1: 18 × 25,5 × 3,1. La antena (≈ 6,5 del extremo) mira al borde delantero.
MODULO = {"x": (-82.0, -64.0), "y": (-81.0, -55.5), "antena_largo": 6.5}
ANTENA_SIN_COBRE = {"x": (-85.0, -61.0), "y": (-63.5, -50.0)}

# Bloques de la cara superior: (nombre, x0, x1, y0, y1, color, texto, bajo la bandeja)
BLOQUES = [
    ("botones", -62.5, -53.5, -73.0, -64.5, "#566573", "BOOT · RESET\nLED PWR, PROG, RUN\nTP EN, IO0, GND", False),
    ("fpc", -63.5, -48.0, -79.5, -74.0, "#117a65", "FPC cámara 24p 0,5", False),
    ("ldo_cam", -62.0, -54.0, -86.0, -80.5, "#117a65", "LDO cámara\n2,8 V · 1,2/1,5 V", False),
    ("elevador", -52.0, -41.5, -94.5, -84.0, "#c0392b", "Elevador 6 V\nTPS61089\nL 1 µH", False),
    ("puente_h", -52.0, -46.0, -102.5, -96.0, "#8e44ad", "DRV8231A\nTP IPROPI", False),
    ("carga", -66.5, -56.5, -114.5, -104.5, "#e07b39", "BQ24073 + PTC\nLED CHG, PG\nTP CHG, PGOOD", False),
    ("3v3", -55.5, -47.5, -112.5, -104.5, "#e07b39", "3,3 V\nTPS63802\nL 0,47 µH", False),
    ("jst", -56.0, -48.0, -119.5, -113.3, "#9e6b3d", "JST-PH\nbatería", False),
    ("esd", -67.5, -63.5, -118.5, -115.3, "#7f8c8d", "ESD\nTP D±", False),
    ("expansor", -96.0, -83.0, -110.0, -90.0, "#1e8449",
     "Expansor TCA9535\n+ acondicionamiento\n(pull-ups, RC,\nSchmitt, VBAT)", True),
    ("amp", -80.0, -72.0, -113.0, -106.0, "#2471a3", "MAX98357A", True),
]

# Pads pasantes de 2,54: (nombre, x0, y0, columnas, filas, color, texto, lado del texto)
PASO = 2.54
PAD_D = 1.7
PADS = [
    ("micro", -60.0, -60.5, 3, 2, "#1e8449", "Micro I2S ×6", "derecha"),
    ("frente_izq", -92.5, -61.5, 3, 2, "#1e8449", "IR: emisor ×2,\nreceptor ×3, GND", "izquierda"),
    ("izquierda", -102.2, -71.0, 1, 5, "#1e8449", "Inclinación ×3\nlengua ×2", "izquierda"),
    ("header", -105.0, -84.0, 1, 10, "#b7950b", "J_EXP 1×10 (sin montar):\nGND, 3V3, VSYS, VBUS,\nSDA, SCL, EXP P07, P17,\nU0TX, U0RX", "izquierda"),
    ("derecha", -46.6, -72.3, 2, 5, "#1e8449", "Leva ×2, encoder ×4,\nbarriga ×2, espalda ×2", "derecha"),
    ("motor", -43.6, -97.0, 1, 2, "#8e44ad", "Motor", "derecha"),
    ("lobulo", -82.8, -120.0, 2, 2, "#2471a3", "", "izquierda"),
]

# Puntos de test SMD de Ø1,5 fuera de los bloques: (nombre, x, y)
TP_D = 1.5
PUNTOS_TEST = [
    ("VBUS", -45.5, -103.5), ("VBAT", -43.0, -103.5), ("VSYS", -45.5, -105.5),
    ("3V3", -43.0, -105.5), ("6V", -45.5, -107.5), ("GND", -43.0, -107.5),
    ("I2S DOUT", -83.3, -125.0), ("GND", -81.0, -125.0),
]

# Apoyos de la bandeja de la batería: dos atornillados (H1 y H3, M2 largo) y dos apoyados
APOYOS = [(-97.0, -68.5, "H1"), (-86.8, -122.4, "H3"), (-70.5, -100.0, "A1"), (-99.0, -103.0, "A2")]
APOYO_D = 4.0

SERIGRAFIA = ("FurbyBoard v1.0", (-73.0, -54.0))


def leer_geometria():
    return json.loads(GEOMETRIA.read_text(encoding="utf-8"))


def puntos_arco(p, paso=0.2):
    c = np.array(p["centro"])
    r = p["radio"]
    a0 = math.atan2(p["inicio"][1] - c[1], p["inicio"][0] - c[0])
    am = math.atan2(p["medio"][1] - c[1], p["medio"][0] - c[0])
    a1 = math.atan2(p["fin"][1] - c[1], p["fin"][0] - c[0])
    barrido = (a1 - a0) % (2 * math.pi)
    if (am - a0) % (2 * math.pi) > barrido:
        barrido -= 2 * math.pi
    n = max(4, int(abs(barrido) * r / paso))
    return [(c[0] + r * math.cos(a0 + barrido * i / n), c[1] + r * math.sin(a0 + barrido * i / n))
            for i in range(n + 1)]


def poligono_pcb(geo):
    puntos = []
    for p in geo["contorno"]:
        tramo = [tuple(p["inicio"]), tuple(p["fin"])] if p["tipo"] == "linea" else puntos_arco(p)
        if puntos and math.dist(puntos[-1], tramo[0]) < 1e-3:
            tramo = tramo[1:]
        puntos += tramo
    return Polygon(puntos).buffer(0)


def rect_bateria():
    b = box(-BATERIA["ancho"] / 2, -BATERIA["largo"] / 2, BATERIA["ancho"] / 2, BATERIA["largo"] / 2)
    b = affinity.rotate(b, BATERIA["giro"], origin=(0, 0))
    return affinity.translate(b, *BATERIA["centro"])


def rect_modulo():
    return box(MODULO["x"][0], MODULO["y"][0], MODULO["x"][1], MODULO["y"][1])


def rect_antena():
    return box(MODULO["x"][0], MODULO["y"][1] - MODULO["antena_largo"], MODULO["x"][1], MODULO["y"][1])


def rect_sin_cobre():
    return box(ANTENA_SIN_COBRE["x"][0], ANTENA_SIN_COBRE["y"][0], ANTENA_SIN_COBRE["x"][1], ANTENA_SIN_COBRE["y"][1])


def rects_pads():
    rects = {}
    for nombre, x0, y0, cols, filas, *_ in PADS:
        r = PAD_D / 2
        rects[nombre] = box(x0 - r, y0 - (filas - 1) * PASO - r, x0 + (cols - 1) * PASO + r, y0 + r)
    return rects


def circulos_tp():
    return {f"TP {n} ({x}; {y})": Point(x, y).buffer(TP_D / 2) for n, x, y in PUNTOS_TEST}


def coma(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",")


def comprobar(geo, pcb):
    """Devuelve la lista de fallos de colocación (vacía si todo cabe)."""
    fallos = []
    dentro = pcb.buffer(-MARGEN_BORDE_MM)
    mec = geo["mecanismo"]
    exclusion = Point(mec["centro"]).buffer(mec["exclusion_diametro"] / 2 + MARGEN_EXCLUSION_MM)
    agujero = Point(mec["centro"]).buffer(mec["diametro"] / 2)
    tornillos = [Point(t).buffer(CABEZA_TORNILLO_D_MM / 2) for t in geo["taladros"]]
    usb = geo["usb"]
    zona_usb = box(usb["x_paredes"][0] - 1.0, usb["y_borde"] - 1.0, usb["x_paredes"][1] + 1.0, usb["y_fondo"] + 1.0)
    sin_cobre = rect_sin_cobre()

    bajo_bandeja = {n for n, *_, b in BLOQUES if b}
    cara_superior = {"modulo": rect_modulo()}
    cara_superior.update({n: box(x0, y0, x1, y1) for n, x0, x1, y0, y1, *_ in BLOQUES})
    cara_superior.update(rects_pads())
    cara_superior.update(circulos_tp())
    for nombre, forma in cara_superior.items():
        if not dentro.contains(forma):
            fallos.append(f"{nombre}: se sale de la PCB (margen {MARGEN_BORDE_MM})")
        if forma.intersects(exclusion):
            fallos.append(f"{nombre}: pisa la exclusión del mecanismo")
        if forma.intersects(zona_usb):
            fallos.append(f"{nombre}: pisa el USB-C")
        if nombre != "modulo" and forma.intersects(sin_cobre):
            fallos.append(f"{nombre}: pisa la zona sin cobre de la antena")
        for t, forma_t in zip(("H1", "H2", "H3", "H4"), tornillos):
            if forma.intersects(forma_t):
                fallos.append(f"{nombre}: pisa la cabeza del tornillo {t}")
    nombres = list(cara_superior)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            if cara_superior[a].intersects(cara_superior[b]):
                fallos.append(f"{a} y {b} se solapan")

    bateria = rect_bateria()
    pared = pcb.buffer(HOLGURA_PARED_MM, join_style=2)
    if not pared.contains(bateria):
        fallos.append("batería: se sale de la pared interior")
    if bateria.distance(agujero) < MARGEN_BATERIA_AGUJERO_MM:
        fallos.append(f"batería: a {bateria.distance(agujero):.2f} del agujero del mecanismo")
    if bateria.intersects(zona_usb):
        fallos.append("batería: pisa el USB-C")
    if bateria.distance(rect_antena()) < MARGEN_BATERIA_ANTENA_MM:
        fallos.append(f"batería: a {bateria.distance(rect_antena()):.2f} de la antena")
    for nombre, forma in cara_superior.items():
        if nombre in bajo_bandeja or nombre == "modulo":
            continue
        if bateria.intersects(forma):
            fallos.append(f"batería: tapa {nombre}, que tiene que quedar accesible o fuera de la bandeja")
    return fallos


def medidas(geo, pcb):
    mec = geo["mecanismo"]
    bateria = rect_bateria()
    pared = pcb.buffer(HOLGURA_PARED_MM, join_style=2)
    return {
        "bateria_pared": pared.exterior.distance(bateria),
        "bateria_agujero": bateria.distance(Point(mec["centro"]).buffer(mec["diametro"] / 2)),
        "antena_bateria": rect_antena().distance(bateria),
        "modulo_fuera_bateria": rect_modulo().difference(bateria).area / rect_modulo().area,
    }


def rect_a_parche(forma, **kw):
    return ParchePoligono(np.array(forma.exterior.coords), closed=True, **kw)


def dibujar_pads(ax):
    for nombre, x0, y0, cols, filas, color, texto, lado in PADS:
        for c in range(cols):
            for f in range(filas):
                centro = (x0 + c * PASO, y0 - f * PASO)
                es_pin1 = nombre == "header" and c == 0 and f == 0
                ax.add_patch(Circle(centro, PAD_D / 2, fc="#d4ac0d", ec=color, lw=0.8,
                                    hatch="////" if es_pin1 else None))
                ax.add_patch(Circle(centro, 0.5, fc="white", ec="none"))
        xm = x0 + (cols - 1) * PASO / 2
        ym = y0 - (filas - 1) * PASO / 2
        if lado == "derecha":
            ax.text(x0 + (cols - 1) * PASO + 1.6, ym, texto, ha="left", va="center", fontsize=6.3, color=color)
        else:
            ax.text(x0 - 1.6, ym, texto, ha="right", va="center", fontsize=6.3, color=color)
        del xm


def render_planta(geo, pcb, m):
    fig = plt.figure(figsize=(17, 10.5), dpi=150)
    ax = fig.add_axes([0.03, 0.06, 0.58, 0.86])
    ax.set_aspect("equal")
    pared = pcb.buffer(HOLGURA_PARED_MM, join_style=2)
    ax.add_patch(rect_a_parche(pared, facecolor="#bbbbbb", edgecolor="#555", lw=0.8))
    ax.add_patch(rect_a_parche(pcb, facecolor="#7fb69e", edgecolor="#2e6b4f", lw=1.0))

    mec = geo["mecanismo"]
    ax.add_patch(Circle(mec["centro"], mec["exclusion_diametro"] / 2, fill=False, ls="--", ec="#a0309a", lw=1))
    ax.add_patch(Circle(mec["centro"], mec["diametro"] / 2, fc="white", ec="#145a32", lw=1.2))
    ax.text(mec["centro"][0], mec["centro"][1], "Mecanismo\nØ11,3", ha="center", va="center", fontsize=7.5,
            color="#145a32")

    for (x, y), nombre in zip(geo["taladros"], ("H1", "H2", "H3", "H4")):
        ax.add_patch(Circle((x, y), CABEZA_TORNILLO_D_MM / 2, fc="none", ec="#a04000", ls=":", lw=0.8))
        ax.add_patch(Circle((x, y), geo["taladro_diametro"] / 2, fc="white", ec="#a04000", lw=1))
        ax.text(x + 2.8, y + 1.6, nombre, ha="left", fontsize=7, color="#a04000")

    usb = geo["usb"]
    ax.add_patch(rect_a_parche(box(usb["x"] - 4.47, usb["y_boca"], usb["x"] + 4.47, usb["y_boca"] + 6.5),
                               fc="#cccccc", ec="#333", hatch="///", lw=0.8))
    ax.text(usb["x"], usb["y_boca"] - 1.6, "USB-C 16 pines, montaje medio\n(TYPE-C-CB16-16P, mismo eje)",
            ha="center", va="top", fontsize=7)

    ax.add_patch(rect_a_parche(rect_sin_cobre().intersection(pcb), fc="#fdfefe", ec="#7f8c8d", ls="--", lw=0.8,
                               hatch=".."))
    ax.add_patch(rect_a_parche(rect_modulo(), fc="#34495e", ec="#17202a", lw=1.0, alpha=0.9))
    ax.add_patch(rect_a_parche(rect_antena(), fc="#f4d03f", ec="#17202a", lw=0.8))
    xc = sum(MODULO["x"]) / 2
    ax.text(xc, MODULO["y"][1] - MODULO["antena_largo"] / 2, "antena del WROOM-1", ha="center", va="center",
            fontsize=7)
    ax.text(xc, MODULO["y"][0] + 4.5, "ESP32-S3-WROOM-1\nN16R8", ha="center", va="center", fontsize=7,
            color="white")
    texto, (tx, ty) = SERIGRAFIA
    ax.text(tx, ty, texto, ha="center", va="center", fontsize=7.5, color="#17202a", fontweight="bold")

    for nombre, x0, x1, y0, y1, color, texto, bajo in BLOQUES:
        ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.5",
                                    fc=color, ec="#222", lw=0.8, alpha=0.75 if bajo else 0.92,
                                    ls="--" if bajo else "-"))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, texto, ha="center", va="center", fontsize=5.8, color="white")

    dibujar_pads(ax)
    for nombre, x, y in PUNTOS_TEST:
        ax.add_patch(Circle((x, y), TP_D / 2, fc="#f5b7b1", ec="#922b21", lw=0.8))
    ax.text(-41.0, -109.6, "TP: VBUS, VBAT, VSYS,\n3V3, 6V, GND", ha="center", va="top", fontsize=6,
            color="#922b21")
    ax.text(-82.2, -126.4, "Pads: luz ×2, altavoz ×2 · TP I2S DOUT, GND", ha="center", va="top", fontsize=6,
            color="#922b21")

    bateria = rect_bateria()
    ax.add_patch(rect_a_parche(bateria, fc="#5dade2", ec="#1b4f72", lw=1.6, alpha=0.25, hatch="\\\\"))
    ax.add_patch(rect_a_parche(bateria, fc="none", ec="#1b4f72", lw=1.6))
    cx, cy = BATERIA["centro"]
    ax.text(cx - 1, cy + 5, f"BATERÍA LiPo 1S 1400 mAh\n7,6 × 33 × 50, sobre bandeja\n"
            f"z {coma(BATERIA_Z[0], 1)} a {coma(BATERIA_Z[1], 1)}", ha="center", va="center", fontsize=8,
            color="#1b4f72", fontweight="bold", bbox={"fc": "white", "ec": "#1b4f72", "alpha": 0.85})
    for x, y, nombre in APOYOS:
        ax.add_patch(Circle((x, y), APOYO_D / 2, fc="none", ec="#1b4f72", lw=1.4))
        ax.text(x + 2.3, y - 2.6, nombre if nombre.startswith("A") else f"{nombre}\n(bandeja)", fontsize=6,
                color="#1b4f72")

    ax.text(-73.5, -49.5, "DELANTE (cara del Furby)", ha="center", fontsize=9, fontweight="bold")
    ax.text(-73.5, -135.0, "DETRÁS (lóbulo)", ha="center", fontsize=9, fontweight="bold")
    ax.set_xlim(-118, -30)
    ax.set_ylim(-138, -47)
    ax.set_xlabel("x (mm, STL)")
    ax.set_ylabel("y (mm, STL)")
    ax.grid(alpha=0.25)

    leyenda = (
        "Propuesta de colocación (bloques aproximados, no huellas)\n\n"
        "Batería: único sitio donde cabe, lado izquierdo girada −4°,\n"
        f"  a {coma(m['bateria_pared'])} de la pared y a {coma(m['bateria_agujero'])} del agujero del mecanismo.\n"
        "  Va en una bandeja impresa sobre el módulo y los bloques bajos.\n\n"
        "ESP32-S3-WROOM-1 con la antena en el borde delantero:\n"
        f"  antena a {coma(m['antena_bateria'])} de la huella de la batería (en planta),\n"
        "  y la batería 4,6 más arriba. Sin cobre bajo la antena (punteado).\n"
        f"  {m['modulo_fuera_bateria'] * 100:.0f} % del módulo queda fuera de la batería.\n"
        "  La huella admite también el WROOM-1U (antena externa).\n\n"
        "Bajo la bandeja (trazo discontinuo): expansor, acondicionamiento\n"
        "  y amplificador; todo de menos de 1,2 mm y sin calor apreciable.\n\n"
        "Accesibles con la batería montada: TP, header J_EXP, BOOT, RESET,\n"
        "  LED, conector de la cámara y pads de los cables del Furby.\n\n"
        "Alturas (z, cara superior de la PCB en 5,505):\n"
        "  WROOM-1: hasta 8,6 · bandeja: 9,3 a 10,1\n"
        f"  Batería: {coma(BATERIA_Z[0], 1)} a {coma(BATERIA_Z[1], 1)} · pared de la base: 22,0\n"
        "  JST-PH SMD ≈ 11,0 y FPC 2,0: fuera de la bandeja\n\n"
        "Serigrafía: «FurbyBoard v1.0» (1,0 de alto) delante; nombre,\n"
        "  versión, fecha y número de GPIO de cada pad en la cara inferior.\n\n"
        "Amarillo: antena · Rosa: TP · Rayado: pin 1 del header"
    )
    fig.text(0.63, 0.92, "FurbyBoard v1.0 · planta\n(coordenadas del STL, vista desde arriba)", fontsize=13,
             fontweight="bold", va="top")
    fig.text(0.63, 0.84, leyenda, fontsize=8.4, va="top", family="monospace")
    RENDER_PLANTA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(RENDER_PLANTA)
    plt.close(fig)


def caja(ax, x, y, w, h, texto, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=color, ec="#222", lw=1.0))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=7.8, color="white")


def flecha(ax, p0, p1, texto="", color="#333", lado=0.12, estilo="-|>"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=estilo, mutation_scale=12, color=color, lw=1.4))
    if texto:
        ax.text((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + lado, texto, ha="center", va="bottom", fontsize=7,
                color=color)


def render_bloques():
    fig, ax = plt.subplots(figsize=(17, 9.4), dpi=150)
    ax.set_xlim(0, 17.0)
    ax.set_ylim(0, 9.4)
    ax.axis("off")
    pot, sen, aud, mcu, mot, cam = "#c0392b", "#1e8449", "#2471a3", "#34495e", "#8e44ad", "#117a65"

    caja(ax, 0.3, 7.2, 2.2, 1.1, "USB-C 16 pines\nRd 5,1k en CC", "#7f8c8d")
    caja(ax, 0.3, 5.6, 2.2, 1.0, "PTC 1,5 A\nUSBLC6 (ESD)", "#7f8c8d")
    caja(ax, 3.1, 5.3, 2.5, 1.5, "BQ24073\ncarga + power path\nICHG 0,49 A\nIIN 0,5 o 1,34 A", "#e07b39")
    caja(ax, 3.1, 3.2, 2.5, 1.2, "LiPo 1S 1400 mAh\ncon PCM · JST-PH", "#5dade2")
    caja(ax, 3.1, 7.2, 2.5, 0.8, "TPS63802\nbuck-boost 3,3 V", "#e07b39")
    caja(ax, 6.3, 4.0, 3.0, 4.3, "ESP32-S3-WROOM-1\nN16R8\n\n16 MB flash\n8 MB PSRAM octal\n\nUSB nativo\nGPIO19/20\n\n"
         "LED PROG en U0TXD", mcu)
    caja(ax, 0.3, 3.2, 2.2, 1.2, "TPS61089\nelevador 6 V", pot)
    caja(ax, 0.3, 1.2, 2.2, 1.4, "DRV8231A\nIN/IN · ITRIP 1,2 A\nIPROPI a ADC1", mot)
    caja(ax, 3.1, 1.2, 2.5, 1.4, "Motor del Furby\nDC bidireccional\nPWM 20 kHz", mot)
    caja(ax, 10.0, 7.3, 2.6, 1.0, "Micro ICS-43434\n(placa con cable)", aud)
    caja(ax, 10.0, 5.8, 2.6, 1.1, "MAX98357A\nVDD = VSYS", aud)
    caja(ax, 13.3, 5.8, 2.4, 1.1, "Altavoz original", aud)
    caja(ax, 10.0, 4.0, 2.6, 1.3, "LDO cámara\n2,8 V (AVDD)\n1,2 o 1,5 V (DVDD)", cam)
    caja(ax, 13.3, 4.0, 3.3, 1.3, "FPC 24p 0,5 · cámara DVP\nOV2640 / OV3660 / OV5640\n(flex hasta la cara)", cam)
    caja(ax, 10.0, 1.2, 2.6, 2.0, "TCA9535\nexpansor I2C\n(bus compartido\ncon el SCCB)\nINT → GPIO21", sen)
    caja(ax, 13.3, 1.2, 3.3, 2.0, "Sensores del Furby, LED,\nEN de carga, elevador,\nampli y cámara\n"
         "(leva, encoder, IR y luz\nvan a GPIO nativos)", sen)

    flecha(ax, (1.4, 7.2), (1.4, 6.6), "VBUS", lado=-0.05)
    flecha(ax, (2.5, 6.05), (3.1, 6.05))
    flecha(ax, (2.5, 8.15), (6.3, 8.15), "D+/D− (GPIO19/20)", color=mcu, lado=0.0)
    flecha(ax, (4.35, 6.8), (4.35, 7.2), "VSYS", lado=-0.12)
    flecha(ax, (5.6, 7.6), (6.3, 7.6), "3V3", lado=0.05)
    flecha(ax, (4.35, 5.3), (4.35, 4.4), "BAT", estilo="<|-|>", lado=-0.1)
    flecha(ax, (3.1, 5.5), (2.4, 4.4), "VSYS", lado=0.05)
    flecha(ax, (1.4, 3.2), (1.4, 2.6), "6 V", lado=-0.05)
    flecha(ax, (2.5, 1.9), (3.1, 1.9))
    ax.plot([6.8, 6.8, 1.4], [4.0, 0.75, 0.75], color=mot, lw=1.4)
    ax.text(4.0, 0.8, "PWM ×2 (GPIO48, GPIO46)", ha="center", va="bottom", fontsize=7, color=mot)
    flecha(ax, (1.4, 0.75), (1.4, 1.2), color=mot)
    flecha(ax, (10.0, 7.8), (9.3, 7.8), "I2S DIN", color=aud, lado=0.05)
    flecha(ax, (9.3, 6.35), (10.0, 6.35), "I2S", color=aud, lado=0.05)
    flecha(ax, (12.6, 6.35), (13.3, 6.35), color=aud)
    ax.plot([9.3, 14.95], [3.65, 3.65], color=cam, lw=1.4)
    ax.text(12.0, 3.68, "DVP: 8 bits, VSYNC, HREF, PCLK, XCLK", ha="center", va="bottom", fontsize=7, color=cam)
    flecha(ax, (14.95, 3.65), (14.95, 4.0), color=cam)
    flecha(ax, (12.6, 4.65), (13.3, 4.65), color=cam)
    ax.plot([8.0, 8.0], [4.0, 2.6], color=sen, lw=1.4)
    flecha(ax, (8.0, 2.6), (10.0, 2.6), "I2C (SIOD 4, SIOC 5)", color=sen, estilo="-|>", lado=0.05)
    flecha(ax, (12.6, 2.25), (13.3, 2.25), color=sen, estilo="<|-|>")

    ax.text(0.3, 9.05, "FurbyBoard v1.0 · diagrama de bloques", fontsize=14, fontweight="bold")
    ax.text(0.3, 8.7, "Naranja: alimentación · Rojo: elevador · Morado: motor · Azul: audio · Verde azulado: "
            "cámara · Verde: E/S · Gris oscuro: MCU", fontsize=8.5, color="#444")
    RENDER_BLOQUES.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(RENDER_BLOQUES, bbox_inches="tight")
    plt.close(fig)


def main():
    geo = leer_geometria()
    pcb = poligono_pcb(geo)
    fallos = comprobar(geo, pcb)
    if fallos:
        for fallo in fallos:
            print("FALLO:", fallo)
        return 1
    m = medidas(geo, pcb)
    print(f"Batería: {m['bateria_pared']:.2f} a la pared y {m['bateria_agujero']:.2f} al agujero del mecanismo")
    print(f"Antena del módulo a {m['antena_bateria']:.2f} de la batería; "
          f"{m['modulo_fuera_bateria'] * 100:.0f} % del módulo fuera de su huella")
    render_planta(geo, pcb, m)
    render_bloques()
    print(f"Escritos {RENDER_PLANTA.relative_to(DIR)} y {RENDER_BLOQUES.relative_to(DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
