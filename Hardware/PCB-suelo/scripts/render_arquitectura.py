#!/usr/bin/env python3
"""Renders de la propuesta de arquitectura electrónica v1 (ver ARQUITECTURA.md).

Dibuja dos figuras:

- render/planta-arquitectura.png: colocación por bloques sobre el contorno real
  de la PCB (geometria.json), con la batería en su bandeja elevada, el
  ESP32-S3 Zero debajo con la antena fuera de la batería, los bloques de
  potencia y audio, los grupos de pads y los apoyos de la bandeja.
- render/bloques.png: diagrama de bloques eléctrico.

Antes de dibujar comprueba la colocación: cada bloque de la cara superior queda
dentro de la PCB, fuera de la exclusión del mecanismo, de las cabezas de los
tornillos, del USB-C y de la zona sin cobre de la antena, y sin solapes entre
bloques. La batería queda dentro de la pared interior y lejos del agujero del
mecanismo. Si algo falla, sale con código 1 y no escribe nada.

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

BATERIA = {"centro": (-84.5, -91.8), "ancho": 33.0, "largo": 50.0, "giro": -4.0}
BATERIA_Z = (11.4, 19.0)        # cara inferior y superior sobre la bandeja

# ESP32-S3 Zero: 18 × 23,5 (PCB de 1,0) y USB-C de 3,6 de alto que sobresale 1,0 por detrás.
# La antena va en el extremo delantero (y mayor), fuera de la huella de la batería.
ZERO = {"x": (-87.0, -69.0), "y": (-80.0, -56.5), "usb_sobresale": 1.0, "antena_largo": 6.0}
ANTENA_SIN_COBRE = {"x": (-89.0, -67.0), "y": (-63.5, -54.5)}

# Bloques de la cara superior: (nombre, x0, x1, y0, y1, color, texto)
BLOQUES = [
    ("carga", -66.5, -55.0, -114.5, -104.5, "#e07b39",
     "Carga y power path\nBQ24073 + LM66100\nPTC, RISET, RILIM"),
    ("jst", -52.5, -44.5, -113.5, -105.5, "#9e6b3d", "JST-PH\nbatería"),
    ("boost", -52.0, -41.5, -94.5, -84.0, "#c0392b", "Elevador 6 V\nTPS61089\nL 1 µH 4×4"),
    ("driver", -52.0, -46.0, -102.5, -96.0, "#8e44ad", "Puente H\nDRV8231A"),
    ("amp", -64.5, -55.5, -82.5, -74.0, "#2471a3", "Amplificador\nMAX98357A"),
]

# Grupos de pads pasantes (paso 2,54): (nombre, x0, y0, columnas, filas, color, texto, lado del texto)
PASO = 2.54
PADS = [
    ("frontales", -65.6, -60.6, 5, 3, "#1e8449",
     "Pads delanteros (15):\nmicro I2S ×6, barriga,\nespalda, lengua, luz ×2\ny GND de reserva", "derecha"),
    ("derecha", -46.2, -74.4, 2, 4, "#1e8449", "Leva, encoder ×4,\nLED IR ×2", "derecha"),
    ("motor", -43.6, -97.0, 1, 2, "#8e44ad", "Motor", "derecha"),
    ("altavoz", -52.6, -76.0, 1, 2, "#2471a3", "Altavoz", "derecha"),
    ("izquierda", -104.8, -92.0, 1, 6, "#1e8449", "Inclinación ×3,\nreceptor IR ×3", "izquierda"),
]
PAD_D = 1.7

# Apoyos de la bandeja de la batería: dos atornillados (H1 y H3, M2 largo) y dos apoyados
APOYOS = [(-97.0, -68.5, "H1"), (-86.8, -122.4, "H3"), (-72.0, -108.0, "A1"), (-99.0, -103.0, "A2")]
APOYO_D = 4.0

# Zona bajo la bandeja para el acondicionamiento de sensores (pasivos de menos de 1 mm)
ACONDICIONAMIENTO = {"x": (-97.0, -74.0), "y": (-110.0, -88.0)}


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


def rect_zero():
    return box(ZERO["x"][0], ZERO["y"][0] - ZERO["usb_sobresale"], ZERO["x"][1], ZERO["y"][1])


def rects_pads():
    rects = {}
    for nombre, x0, y0, cols, filas, *_ in PADS:
        r = PAD_D / 2
        rects[nombre] = box(x0 - r, y0 - (filas - 1) * PASO - r, x0 + (cols - 1) * PASO + r, y0 + r)
    return rects


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
    antena = box(ANTENA_SIN_COBRE["x"][0], ANTENA_SIN_COBRE["y"][0], ANTENA_SIN_COBRE["x"][1], ANTENA_SIN_COBRE["y"][1])

    cara_superior = {"zero": rect_zero()}
    cara_superior.update({n: box(x0, y0, x1, y1) for n, x0, x1, y0, y1, *_ in BLOQUES})
    cara_superior.update(rects_pads())
    for nombre, forma in cara_superior.items():
        if not dentro.contains(forma):
            fallos.append(f"{nombre}: se sale de la PCB (margen {MARGEN_BORDE_MM})")
        if forma.intersects(exclusion):
            fallos.append(f"{nombre}: pisa la exclusión del mecanismo")
        if forma.intersects(zona_usb):
            fallos.append(f"{nombre}: pisa el USB-C")
        if nombre != "zero" and forma.intersects(antena):
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
    for nombre, x0, x1, y0, y1, *_ in BLOQUES:
        if bateria.intersects(box(x0, y0, x1, y1)):
            fallos.append(f"batería: tapa el bloque {nombre} (solo van debajo el Zero y pasivos bajos)")
    antena_zero = box(ZERO["x"][0], ZERO["y"][1] - ZERO["antena_largo"], ZERO["x"][1], ZERO["y"][1])
    if bateria.intersects(antena_zero):
        fallos.append("batería: tapa la antena del Zero")
    return fallos


def medidas(geo, pcb):
    mec = geo["mecanismo"]
    bateria = rect_bateria()
    pared = pcb.buffer(HOLGURA_PARED_MM, join_style=2)
    antena_zero = box(ZERO["x"][0], ZERO["y"][1] - ZERO["antena_largo"], ZERO["x"][1], ZERO["y"][1])
    return {
        "bateria_pared": pared.exterior.distance(bateria),
        "bateria_agujero": bateria.distance(Point(mec["centro"]).buffer(mec["diametro"] / 2)),
        "antena_fuera": antena_zero.distance(bateria),
        "zero_fuera_bateria": rect_zero().difference(bateria).area / rect_zero().area,
    }


def coma(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",")


def rect_a_parche(forma, **kw):
    return ParchePoligono(np.array(forma.exterior.coords), closed=True, **kw)


def render_planta(geo, pcb, m):
    fig = plt.figure(figsize=(16, 10.5), dpi=150)
    ax = fig.add_axes([0.04, 0.06, 0.56, 0.86])
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
        ax.text(x, y + 3.0, nombre, ha="center", fontsize=7, color="#a04000")

    usb = geo["usb"]
    ax.add_patch(rect_a_parche(box(usb["x"] - 4.47, usb["y_boca"], usb["x"] + 4.47, usb["y_boca"] + 6.8),
                               fc="#cccccc", ec="#333", hatch="///", lw=0.8))
    ax.text(usb["x"], usb["y_boca"] - 1.6, "USB-C (C2848622)", ha="center", va="top", fontsize=7.5)

    antena = box(ANTENA_SIN_COBRE["x"][0], ANTENA_SIN_COBRE["y"][0], ANTENA_SIN_COBRE["x"][1], ANTENA_SIN_COBRE["y"][1])
    ax.add_patch(rect_a_parche(antena, fc="#fdfefe", ec="#7f8c8d", ls="--", lw=0.8, hatch=".."))

    zero = rect_zero()
    ax.add_patch(rect_a_parche(zero, fc="#34495e", ec="#17202a", lw=1.0, alpha=0.9))
    antena_zero = box(ZERO["x"][0], ZERO["y"][1] - ZERO["antena_largo"], ZERO["x"][1], ZERO["y"][1])
    ax.add_patch(rect_a_parche(antena_zero, fc="#f4d03f", ec="#17202a", lw=0.8))
    xc = sum(ZERO["x"]) / 2
    ax.text(xc, ZERO["y"][1] - ZERO["antena_largo"] / 2, "antena", ha="center", va="center", fontsize=7)
    ax.text(xc, ZERO["y"][0] + 1.6, "USB-C del módulo", ha="center", va="center", fontsize=6.5, color="white")

    acond = box(ACONDICIONAMIENTO["x"][0], ACONDICIONAMIENTO["y"][0], ACONDICIONAMIENTO["x"][1], ACONDICIONAMIENTO["y"][1])
    ax.add_patch(rect_a_parche(acond, fc="#d5f5e3", ec="#1e8449", ls=":", lw=0.8))
    ax.text(sum(ACONDICIONAMIENTO["x"]) / 2, ACONDICIONAMIENTO["y"][0] + 1.0,
            "Acondicionamiento de sensores\n(pull-ups, RC, Schmitt, divisor VBAT)", ha="center", fontsize=6.5,
            color="#145a32")

    for nombre, x0, x1, y0, y1, color, texto in BLOQUES:
        ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.6",
                                    fc=color, ec="#222", lw=0.8, alpha=0.9))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, texto, ha="center", va="center", fontsize=6.3, color="white")

    for nombre, x0, y0, cols, filas, color, texto, lado in PADS:
        for c in range(cols):
            for f in range(filas):
                ax.add_patch(Circle((x0 + c * PASO, y0 - f * PASO), PAD_D / 2, fc="#d4ac0d", ec=color, lw=0.8))
                ax.add_patch(Circle((x0 + c * PASO, y0 - f * PASO), 0.5, fc="white", ec="none"))
        xm = x0 + (cols - 1) * PASO / 2
        ym = y0 - (filas - 1) * PASO / 2
        if lado == "arriba":
            ax.text(xm, y0 + 2.0, texto, ha="center", va="bottom", fontsize=6.5, color=color)
        elif lado == "derecha":
            ax.text(x0 + (cols - 1) * PASO + 1.6, ym, texto, ha="left", va="center", fontsize=6.5, color=color)
        else:
            ax.text(x0 - 1.6, ym, texto, ha="right", va="center", fontsize=6.5, color=color)

    bateria = rect_bateria()
    ax.add_patch(rect_a_parche(bateria, fc="#5dade2", ec="#1b4f72", lw=1.6, alpha=0.28, hatch="\\\\"))
    ax.add_patch(rect_a_parche(bateria, fc="none", ec="#1b4f72", lw=1.6))
    cx, cy = BATERIA["centro"]
    ax.text(cx - 1, cy - 1, f"BATERÍA LiPo 1S 1400 mAh\n7,6 × 33 × 50, sobre bandeja\n"
            f"z {coma(BATERIA_Z[0], 1)} a {coma(BATERIA_Z[1], 1)}", ha="center", va="center", fontsize=8,
            color="#1b4f72", fontweight="bold", bbox={"fc": "white", "ec": "#1b4f72", "alpha": 0.85})

    for x, y, nombre in APOYOS:
        ax.add_patch(Circle((x, y), APOYO_D / 2, fc="none", ec="#1b4f72", lw=1.4))
        ax.text(x + 2.4, y - 2.2, nombre if nombre.startswith("A") else f"{nombre}\n(bandeja)", fontsize=6,
                color="#1b4f72")

    ax.text(-73.5, -51.0, "DELANTE", ha="center", fontsize=9, fontweight="bold")
    ax.text(-73.5, -134.0, "DETRÁS (lóbulo)", ha="center", fontsize=9, fontweight="bold")
    ax.set_xlim(-114, -33)
    ax.set_ylim(-137, -48)
    ax.set_xlabel("x (mm, STL)")
    ax.set_ylabel("y (mm, STL)")
    ax.grid(alpha=0.25)

    leyenda = (
        "Propuesta de colocación v1 (bloques aproximados, no huellas)\n\n"
        "La batería de 33 × 50 solo cabe en el lado izquierdo, girada −4°:\n"
        f"  a {coma(m['bateria_pared'])} de la pared y a {coma(m['bateria_agujero'])} del agujero del mecanismo.\n"
        "  No caben batería y Zero uno junto al otro, así que la batería va\n"
        "  en una bandeja impresa por encima del Zero.\n\n"
        "ESP32-S3 Zero en la cara superior, con los castellated soldados.\n"
        f"  Antena a {coma(m['antena_fuera'])} por fuera de la huella de la batería;\n"
        f"  {m['zero_fuera_bateria'] * 100:.0f} % del módulo queda fuera de la batería.\n"
        "  Debajo de la antena, en la PCB: sin cobre en ninguna capa.\n\n"
        "Bandeja: atornillada en H1 y H3 (M2 × 10 en vez de M2 × 4)\n"
        "  y apoyada en A1 y A2 (círculos sin componentes ni cobre).\n"
        "  Debajo solo van el Zero (4,6 de alto) y pasivos de < 1 mm.\n\n"
        "Fuera de la batería: carga, elevador, puente H y amplificador,\n"
        "  que son los que se calientan o llevan piezas altas.\n\n"
        "Alturas (z, cara superior de la PCB en 5,505):\n"
        "  Zero con su USB-C: hasta 10,1\n"
        "  Bandeja: suelo de 10,6 a 11,4\n"
        f"  Batería: {coma(BATERIA_Z[0], 1)} a {coma(BATERIA_Z[1], 1)}\n"
        "  JST-PH SMD: hasta 11,0 · bobina 4 × 4 × 2: hasta 7,5\n"
        "  Pared de la base: hasta 22,0 → quedan 3,0 sobre la batería\n"
        "  Por encima: cuerpo del Furby, sin medir (riesgo)\n\n"
        "Amarillo: antena · Punteado gris: sin cobre · Magenta: exclusión Ø15,3"
    )
    fig.text(0.62, 0.92, "FurbyGPT · electrónica v1 · planta\n(coordenadas del STL, vista desde arriba)", fontsize=13,
             fontweight="bold", va="top")
    fig.text(0.62, 0.84, leyenda, fontsize=8.6, va="top", family="monospace")
    RENDER_PLANTA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(RENDER_PLANTA)
    plt.close(fig)


def caja(ax, x, y, w, h, texto, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=color, ec="#222", lw=1.0))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=8.2, color="white")


def flecha(ax, p0, p1, texto="", color="#333", lado=0.12, estilo="-|>"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=estilo, mutation_scale=12, color=color, lw=1.4))
    if texto:
        ax.text((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + lado, texto, ha="center", va="bottom", fontsize=7,
                color=color)


def render_bloques():
    fig, ax = plt.subplots(figsize=(15.5, 8.6), dpi=150)
    ax.set_xlim(0, 15.3)
    ax.set_ylim(0, 8.6)
    ax.axis("off")
    pot, sen, aud, mcu, mot = "#c0392b", "#1e8449", "#2471a3", "#34495e", "#8e44ad"

    caja(ax, 0.3, 6.5, 2.0, 1.0, "USB-C trasero\n(solo carga)\nRd 5,1k en CC", "#7f8c8d")
    caja(ax, 0.3, 4.9, 2.0, 0.8, "PTC 1,5 A", "#7f8c8d")
    caja(ax, 2.9, 4.6, 2.5, 1.4, "BQ24073\ncarga con power path\nICHG 0,49 A\nIIN 0,5 A o 1,34 A", "#e07b39")
    caja(ax, 2.9, 6.6, 2.5, 0.9, "LM66100\ndiodo ideal", "#e07b39")
    caja(ax, 2.9, 2.6, 2.5, 1.2, "LiPo 1S 1400 mAh\ncon protección (PCM)\nJST-PH", "#5dade2")
    caja(ax, 0.3, 2.6, 2.0, 1.2, "TPS61089\nelevador 6 V\nVIN = VSYS", pot)
    caja(ax, 2.9, 0.5, 2.5, 1.3, "DRV8231A\npuente H\nITRIP 1,2 A\nIPROPI a ADC1", mot)
    caja(ax, 0.3, 0.5, 2.0, 1.3, "Motor del Furby\nDC bidireccional\n(6 V)", mot)
    caja(ax, 6.3, 3.9, 2.8, 3.6, "ESP32-S3 Zero\n\nESP32-S3FH4R2\n4 MB flash · 2 MB PSRAM\n\nLDO ME6217 3,3 V\n"
         "(alimenta los 3,3 V\nde toda la placa)\n\nUSB-C propio:\nprogramar y recuperar", mcu)
    caja(ax, 9.9, 6.6, 2.5, 0.9, "Micro I2S MEMS\nICS-43434 (en cable)", aud)
    caja(ax, 9.9, 5.0, 2.5, 1.0, "MAX98357A\nclase D I2S\nVDD = VSYS", aud)
    caja(ax, 12.9, 5.0, 2.2, 1.0, "Altavoz original\n(impedancia\npor medir)", aud)
    caja(ax, 9.9, 2.4, 2.5, 1.9, "Acondicionamiento\npull-up 47k, 1k serie,\n100 nF · Schmitt\n(encoder) · divisor\n"
         "VBAT · transistores\nde los LED IR", sen)
    caja(ax, 12.9, 2.4, 2.2, 1.9, "Sensores del Furby\nleva · encoder\nóptico · barriga\nespalda · lengua\n"
         "inclinación · luz · IR", sen)

    flecha(ax, (1.3, 6.5), (1.3, 5.7), "VBUS", lado=-0.05)
    flecha(ax, (2.3, 5.3), (2.9, 5.3))
    flecha(ax, (4.15, 6.0), (4.15, 6.6), "VSYS", lado=-0.1)
    flecha(ax, (5.4, 7.05), (6.3, 7.05), "5V", lado=0.05)
    flecha(ax, (4.15, 4.6), (4.15, 3.8), "BAT", estilo="<|-|>", lado=-0.1)
    flecha(ax, (3.1, 4.6), (2.0, 3.8), "VSYS", lado=0.05)
    flecha(ax, (2.0, 2.6), (3.1, 1.8), "6 V", lado=0.05)
    flecha(ax, (2.9, 1.15), (2.3, 1.15))
    flecha(ax, (5.4, 5.3), (6.3, 5.3), "PGOOD\nCHG, EN2", color="#e07b39", estilo="<|-|>", lado=0.05)
    flecha(ax, (6.4, 3.9), (5.4, 1.5), "PWM ×2\nEN 6 V", color=mot, lado=0.05)
    flecha(ax, (9.9, 7.05), (9.1, 7.05), "I2S0", color=aud, lado=0.05)
    flecha(ax, (9.1, 5.5), (9.9, 5.5), "I2S1", color=aud, lado=0.05)
    flecha(ax, (12.4, 5.5), (12.9, 5.5), color=aud)
    flecha(ax, (12.9, 3.35), (12.4, 3.35), color=sen)
    flecha(ax, (9.9, 4.1), (9.1, 4.3), "GPIO\nADC1", color=sen, lado=0.05)

    ax.text(0.3, 8.2, "FurbyGPT · diagrama de bloques v1", fontsize=14, fontweight="bold")
    ax.text(0.3, 7.85, "Naranja: carga · Rojo: elevador · Morado: motor · Azul: audio · Verde: sensores · "
            "Gris oscuro: MCU", fontsize=8.5, color="#444")
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
    print(f"Antena del Zero a {m['antena_fuera']:.2f} de la batería; "
          f"{m['zero_fuera_bateria'] * 100:.0f} % del Zero fuera de su huella")
    render_planta(geo, pcb, m)
    render_bloques()
    print(f"Escritos {RENDER_PLANTA.relative_to(DIR)} y {RENDER_BLOQUES.relative_to(DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
