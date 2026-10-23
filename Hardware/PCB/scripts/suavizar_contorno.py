#!/usr/bin/env python3
"""Suaviza el contorno de la PCB del FurbyGPT y genera DXF, proyecto KiCad y render.

El contorno de entrada (FurbyPCB.dxf) es un polígono de segmentos rectos. Cada
vértice convexo se sustituye por un arco tangente a sus dos segmentos (fillet),
así que el borde nuevo es continuo en tangente (G1), queda siempre por dentro
del original y se puede fabricar con líneas y arcos nativos (DXF, KiCad, Gerber).

El radio de cada arco sale de la desviación máxima permitida respecto al vértice
original (--desviacion) y de la longitud de los segmentos vecinos.

Uso (desde Hardware/PCB):
    python -I scripts/suavizar_contorno.py
    python -I scripts/suavizar_contorno.py --desviacion 0.3
Requiere: ezdxf, numpy, matplotlib (ver scripts/requirements.txt).
"""

import argparse
import json
import math
import uuid
from pathlib import Path

import ezdxf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PCB_DIR = Path(__file__).resolve().parent.parent
DXF_ENTRADA = PCB_DIR / "FurbyPCB.dxf"
DXF_SALIDA = PCB_DIR / "FurbyPCB-suave.dxf"
KICAD_DIR = PCB_DIR / "kicad"
RENDER_PNG = PCB_DIR / "render" / "comparacion.png"

PROYECTO = "FurbyGPT"
LIB_FOOTPRINTS = "Furby"
FOOTPRINT_TALADRO = "MountingHole_2.3mm_M2"

DESVIACION_MAX_MM = 0.5
TALADRO_M2_MM = 2.3
RECORTE_GRANDE_MM = 11.3
# Un taladro de montaje se distingue del recorte grande por su diámetro.
UMBRAL_TALADRO_MM = 4.0
# Segmentos más cortos que esto con un vértice cóncavo se tratan como un
# escalón de dibujo y se eliminan alargando los segmentos vecinos.
ESCALON_MAX_MM = 0.5
# Segmentos más cortos que esto entre dos vértices convexos se absorben en un
# solo arco (si cabe por dentro); evita arcos pequeños encadenados.
FUSION_MAX_MM = 2.0
# Esquina inferior izquierda del contorno dentro de la hoja de KiCad.
ORIGEN_KICAD_MM = (100.0, 160.0)
UUID_BASE = uuid.UUID("6f1b3c2e-1d0a-4c8e-9a51-f0b9e7a2c001")
TOL = 1e-6


# ---------------------------------------------------------------- lectura DXF

def leer_dxf(ruta):
    doc = ezdxf.readfile(ruta)
    segmentos, circulos = [], []
    for entidad in doc.modelspace():
        if entidad.dxftype() == "LINE":
            ini, fin = entidad.dxf.start, entidad.dxf.end
            segmentos.append(((ini.x, ini.y), (fin.x, fin.y)))
        elif entidad.dxftype() == "CIRCLE":
            centro = entidad.dxf.center
            circulos.append(((centro.x, centro.y), 2 * entidad.dxf.radius))
    return encadenar(segmentos), circulos


def encadenar(segmentos):
    """Ordena los segmentos sueltos en un polígono cerrado (lista de vértices)."""
    clave = lambda p: (round(p[0], 5), round(p[1], 5))  # noqa: E731
    pendientes = [s for s in segmentos if math.dist(*s) > TOL]
    ini, fin = pendientes.pop(0)
    vertices = [ini, fin]
    while pendientes:
        ultimo = clave(vertices[-1])
        for i, (a, b) in enumerate(pendientes):
            if clave(a) == ultimo:
                vertices.append(b)
                break
            if clave(b) == ultimo:
                vertices.append(a)
                break
        else:
            raise ValueError(f"Contorno abierto: no hay segmento que continúe en {ultimo}")
        pendientes.pop(i)
    if clave(vertices[-1]) != clave(vertices[0]):
        raise ValueError("El contorno no cierra")
    return np.array(vertices[:-1], dtype=float)


# ------------------------------------------------------------- geometría base

def area_con_signo(poligono):
    x, y = poligono[:, 0], poligono[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def cruz(a, b):
    return a[0] * b[1] - a[1] * b[0]


def unitario(v):
    return v / np.linalg.norm(v)


def punto_en_poligono(punto, poligono):
    x, y = punto
    dentro = False
    n = len(poligono)
    for i in range(n):
        x1, y1 = poligono[i]
        x2, y2 = poligono[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            dentro = not dentro
    return dentro


def distancia_a_poligono(puntos, poligono):
    """Distancia mínima de cada punto al borde del polígono (vectorizado)."""
    a = poligono
    b = np.roll(poligono, -1, axis=0)
    ab = b - a
    ap = puntos[:, None, :] - a[None, :, :]
    t = np.clip(np.sum(ap * ab, axis=2) / np.sum(ab * ab, axis=1), 0, 1)
    proyeccion = a[None, :, :] + t[:, :, None] * ab[None, :, :]
    return np.min(np.linalg.norm(puntos[:, None, :] - proyeccion, axis=2), axis=1)


def interseccion_rectas(p1, d1, p2, d2):
    t = cruz(p2 - p1, d2) / cruz(d1, d2)
    return p1 + t * d1


def giros_poligono(poligono):
    n = len(poligono)
    return np.array([cruz(poligono[i] - poligono[i - 1], poligono[(i + 1) % n] - poligono[i])
                     for i in range(n)])


def limpiar_poligono(poligono):
    """Pone el polígono en sentido antihorario, quita vértices colineales y
    elimina escalones cóncavos diminutos (p. ej. el de 0,137 mm de la esquina
    superior derecha) prolongando los segmentos vecinos hasta que se cortan."""
    if area_con_signo(poligono) < 0:
        poligono = poligono[::-1]
    cambios = []
    while True:
        n = len(poligono)
        giros = giros_poligono(poligono)
        colineal = next((i for i in range(n) if abs(giros[i]) < TOL), None)
        if colineal is not None:
            poligono = np.delete(poligono, colineal, axis=0)
            continue
        escalon = None
        for i in range(n):
            j = (i + 1) % n
            corto = np.linalg.norm(poligono[j] - poligono[i]) < ESCALON_MAX_MM
            if corto and (giros[i] < 0 or giros[j] < 0):
                escalon = i
                break
        if escalon is None:
            return poligono, cambios
        i, j = escalon, (escalon + 1) % n
        anterior, siguiente = poligono[i - 1], poligono[(j + 1) % n]
        nuevo = interseccion_rectas(anterior, poligono[i] - anterior,
                                    siguiente, poligono[j] - siguiente)
        if not punto_en_poligono(nuevo, poligono) and \
                distancia_a_poligono(nuevo[None], poligono)[0] > TOL:
            raise ValueError(f"Quitar el escalón en {poligono[i]} sacaría el borde hacia fuera")
        cambios.append((poligono[i].copy(), poligono[j].copy(), nuevo))
        poligono = np.delete(poligono, j, axis=0)
        poligono[i if j > i else i - 1] = nuevo


def fusionar_segmentos_cortos(poligono, original, longitud_max):
    """Sustituye cada segmento corto entre dos vértices convexos por un vértice
    virtual, el cruce de los segmentos vecinos, para que un único arco cubra
    los dos giros. Ese vértice queda fuera del original: su distancia al borde
    original (holgura) se suma a la desviación que se le permite al arco."""
    holgura = np.zeros(len(poligono))
    while True:
        n = len(poligono)
        giros = giros_poligono(poligono)
        candidatos = [i for i in range(n)
                      if np.linalg.norm(poligono[(i + 1) % n] - poligono[i]) < longitud_max
                      and giros[i] > 0 and giros[(i + 1) % n] > 0
                      and holgura[i] == 0 and holgura[(i + 1) % n] == 0]
        if not candidatos:
            return poligono, holgura
        i = candidatos[0]
        j = (i + 1) % n
        anterior, siguiente = poligono[i - 1], poligono[(j + 1) % n]
        virtual = interseccion_rectas(anterior, poligono[i] - anterior,
                                      siguiente, poligono[j] - siguiente)
        poligono = poligono.copy()
        poligono[i] = virtual
        holgura[i] = distancia_a_poligono(virtual[None], original)[0]
        poligono = np.delete(poligono, j, axis=0)
        holgura = np.delete(holgura, j)


# -------------------------------------------------------------------- fillets

def calcular_fillets(poligono, presupuesto):
    """Devuelve, por vértice, la longitud de tangente t, el radio y la desviación.

    En un vértice con giro phi, un arco de radio R tiene tangente
    t = R * tan(phi / 2) y se separa del vértice d = t * tan(phi / 4).
    Los radios crecen a la vez (llenado progresivo): cada arco se congela
    cuando llega a su desviación máxima (presupuesto[i]) o cuando él y su
    vecino ya ocupan todo el segmento que comparten. Así el radio más pequeño
    del contorno es el mayor posible y no quedan arcos diminutos que parezcan
    picos junto a arcos enormes.
    """
    n = len(poligono)
    entrada = [unitario(poligono[i] - poligono[i - 1]) for i in range(n)]
    salida = [unitario(poligono[(i + 1) % n] - poligono[i]) for i in range(n)]
    giro = np.array([math.atan2(cruz(entrada[i], salida[i]), np.dot(entrada[i], salida[i]))
                     for i in range(n)])
    longitud = np.array([np.linalg.norm(poligono[(i + 1) % n] - poligono[i]) for i in range(n)])

    convexo = giro > TOL
    pendiente = np.where(convexo, np.tan(np.abs(giro) / 2), 0.0)  # t por mm de radio
    t_max = np.where(convexo, presupuesto / np.tan(np.abs(giro) / 4), 0.0)
    t = np.zeros(n)
    activo = convexo.copy()
    radio = 0.0
    while activo.any():
        limites = []  # (radio al que salta la restricción, vértices que congela)
        for i in np.flatnonzero(activo):
            limites.append((t_max[i] / pendiente[i], [i]))
        for i in range(n):
            j = (i + 1) % n
            if activo[i] and activo[j]:
                limites.append((longitud[i] / (pendiente[i] + pendiente[j]), [i, j]))
            elif activo[i]:
                limites.append(((longitud[i] - t[j]) / pendiente[i], [i]))
            elif activo[j]:
                limites.append(((longitud[i] - t[i]) / pendiente[j], [j]))
        radio, congelados = min(limites, key=lambda limite: limite[0])
        t[activo] = radio * pendiente[activo]
        activo[congelados] = False

    radio = np.where(convexo, t / np.maximum(pendiente, TOL), 0.0)
    desviacion = t * np.tan(np.abs(giro) / 4)
    return {"t": t, "radio": radio, "desviacion": desviacion, "giro": giro,
            "entrada": entrada, "salida": salida, "longitud": longitud}


def construir_contorno(poligono, fillets):
    """Lista de primitivas cerrada: ('linea', p0, p1) y ('arco', p0, medio, p1, centro, r)."""
    n = len(poligono)
    arcos = []
    for i in range(n):
        v, t, r = poligono[i], fillets["t"][i], fillets["radio"][i]
        if t < TOL:
            arcos.append((v, None, v, None, 0.0))
            continue
        u_in, u_out = fillets["entrada"][i], fillets["salida"][i]
        tangente_in = v - u_in * t
        tangente_out = v + u_out * t
        normal_in = np.array([-u_in[1], u_in[0]])  # interior a la izquierda (antihorario)
        centro = tangente_in + normal_in * r
        medio = centro + unitario(v - centro) * r
        arcos.append((tangente_in, medio, tangente_out, centro, r))

    primitivas = []
    for i in range(n):
        ini, medio, fin, centro, r = arcos[i]
        if centro is not None:
            primitivas.append(("arco", ini, medio, fin, centro, r))
        siguiente = arcos[(i + 1) % n][0]
        if np.linalg.norm(siguiente - fin) > TOL:
            primitivas.append(("linea", fin, siguiente))
    return primitivas


def angulo(centro, punto):
    return math.atan2(punto[1] - centro[1], punto[0] - centro[0])


def barrido_arco(primitiva):
    """Ángulo inicial y barrido antihorario (rad) de un arco."""
    _, ini, _, fin, centro, _ = primitiva
    a0 = angulo(centro, ini)
    barrido = (angulo(centro, fin) - a0) % (2 * math.pi)
    return a0, barrido


def muestrear(primitivas, paso=0.02):
    puntos = []
    for p in primitivas:
        if p[0] == "linea":
            n = max(2, int(np.linalg.norm(p[2] - p[1]) / paso))
            s = np.linspace(0, 1, n, endpoint=False)[:, None]
            puntos.append(p[1] + s * (p[2] - p[1]))
        else:
            a0, barrido = barrido_arco(p)
            n = max(4, int(barrido * p[5] / paso))
            a = a0 + np.linspace(0, barrido, n, endpoint=False)
            puntos.append(p[4] + p[5] * np.column_stack([np.cos(a), np.sin(a)]))
    return np.vstack(puntos)


def distancia_a_contorno(punto, primitivas):
    """Distancia exacta de un punto al contorno de líneas y arcos."""
    mejor = math.inf
    for p in primitivas:
        if p[0] == "linea":
            a, b = p[1], p[2]
            t = np.clip(np.dot(punto - a, b - a) / np.dot(b - a, b - a), 0, 1)
            mejor = min(mejor, np.linalg.norm(punto - (a + t * (b - a))))
        else:
            a0, barrido = barrido_arco(p)
            relativo = (angulo(p[4], punto) - a0) % (2 * math.pi)
            if relativo <= barrido:
                mejor = min(mejor, abs(np.linalg.norm(punto - p[4]) - p[5]))
            else:
                mejor = min(mejor, np.linalg.norm(punto - p[1]), np.linalg.norm(punto - p[3]))
    return mejor


def puntos_fuera(original, primitivas):
    return [p for p in muestrear(primitivas)
            if not punto_en_poligono(p, original)
            and distancia_a_poligono(p[None], original)[0] > 1e-6]


def suavizar(original, poligono, desviacion_max, holgura=None):
    """Aplica los fillets y, si algún vértice del original (p. ej. el de un
    escalón eliminado) queda a más de desviacion_max del borde nuevo, recorta
    el presupuesto del vértice limpio más cercano y repite."""
    if holgura is None:
        holgura = np.zeros(len(poligono))
    presupuesto = desviacion_max + holgura
    for _ in range(50):
        fillets = calcular_fillets(poligono, presupuesto)
        primitivas = construir_contorno(poligono, fillets)
        if puntos_fuera(original, primitivas):
            raise ValueError("El contorno suavizado sale del original")
        excesos = [(distancia_a_contorno(v, primitivas) - desviacion_max, v) for v in original]
        excesos = [(e, v) for e, v in excesos if e > 1e-4]
        if not excesos:
            return fillets, primitivas
        for exceso, v in excesos:
            cercano = int(np.argmin(np.linalg.norm(poligono - v, axis=1)))
            presupuesto[cercano] -= exceso * 1.05
    raise ValueError("No se consigue respetar la desviación máxima")


# ---------------------------------------------------------------- validación

def validar(original, primitivas, taladros):
    for actual, siguiente in zip(primitivas, primitivas[1:] + primitivas[:1]):
        fin = actual[2] if actual[0] == "linea" else actual[3]
        if np.linalg.norm(fin - siguiente[1]) > 1e-9:
            raise ValueError(f"Hueco en el contorno en {fin}")

    muestras = muestrear(primitivas)
    fuera = puntos_fuera(original, primitivas)
    if fuera:
        raise ValueError(f"{len(fuera)} puntos del contorno nuevo salen del original")

    # Sin autointersecciones: el giro acumulado de un contorno simple es 360°.
    tangentes = np.diff(np.vstack([muestras, muestras[:1]]), axis=0)
    siguientes = np.roll(tangentes, -1, axis=0)
    giros = np.arctan2(tangentes[:, 0] * siguientes[:, 1] - tangentes[:, 1] * siguientes[:, 0],
                       np.sum(tangentes * siguientes, axis=1))
    giro_total = math.degrees(np.sum(giros))
    if abs(giro_total - 360) > 0.01 or np.any(giros < -1e-6):
        raise ValueError(f"Contorno no simple o no convexo (giro total {giro_total:.3f}°)")

    # Hausdorff contra el polígono original (muestreado) en los dos sentidos.
    lado = np.vstack([original, muestrear([("linea", original[i], original[(i + 1) % len(original)])
                                          for i in range(len(original))], paso=0.05)])
    hacia_nuevo = max(distancia_a_contorno(p, primitivas) for p in lado)
    hacia_original = float(np.max(distancia_a_poligono(muestras[::5], original)))

    holguras = []
    for centro, diametro in taladros:
        borde = distancia_a_contorno(np.array(centro), primitivas)
        holguras.append((centro, diametro, borde, borde - diametro / 2))
    return {"desviacion_max": hacia_nuevo, "desviacion_inversa": hacia_original,
            "giro_total": giro_total, "holguras": holguras}


# -------------------------------------------------------------------- salidas

def normalizar_taladros(circulos, diametro_taladro, diametro_recorte):
    """Mantiene los centros exactos y normaliza los diámetros."""
    taladros = []
    for centro, diametro in circulos:
        nuevo = diametro_taladro if diametro < UMBRAL_TALADRO_MM else diametro_recorte
        taladros.append((centro, nuevo, diametro))
    return taladros


def escribir_dxf(ruta, primitivas, taladros):
    doc = ezdxf.new("R2010", setup=False, units=ezdxf.units.MM)
    doc.header["$MEASUREMENT"] = 1
    doc.layers.add("Contorno", color=3)
    doc.layers.add("Taladros", color=1)
    msp = doc.modelspace()
    for p in primitivas:
        if p[0] == "linea":
            msp.add_line(tuple(p[1]), tuple(p[2]), dxfattribs={"layer": "Contorno"})
        else:
            a0, barrido = barrido_arco(p)
            msp.add_arc(tuple(p[4]), p[5], math.degrees(a0), math.degrees(a0 + barrido),
                        dxfattribs={"layer": "Contorno"})
    for centro, diametro, _ in taladros:
        msp.add_circle(centro, diametro / 2, dxfattribs={"layer": "Taladros"})
    doc.saveas(ruta)


def uuid_estable(nombre):
    return str(uuid.uuid5(UUID_BASE, nombre))


def a_kicad(punto):
    """De coordenadas DXF (Y hacia arriba) a KiCad (Y hacia abajo)."""
    x0, y0 = ORIGEN_KICAD_MM
    return f"{x0 + punto[0]:.6f} {y0 - punto[1]:.6f}"


def footprint_taladro(diametro, cabecera):
    """Taladro M2 sin cobre: NPTH, marca de la cabeza del tornillo y courtyard."""
    radio_cabeza = 2.2   # cabeza M2 ISO 7045 (dk = 4,0 mm) con margen
    radio_courtyard = 2.45
    return f"""{cabecera}
\t(descr "Taladro de montaje {diametro} mm para M2, sin cobre (NPTH)")
\t(tags "mountinghole M2 NPTH")
\t(attr exclude_from_pos_files exclude_from_bom)
\t(fp_circle (center 0 0) (end {radio_cabeza} 0) (stroke (width 0.15) (type solid)) (fill no) (layer "Cmts.User"))
\t(fp_circle (center 0 0) (end {radio_courtyard} 0) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))
\t(fp_text user "${{REFERENCE}}" (at 0 0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
\t(pad "" np_thru_hole circle (at 0 0) (size {diametro} {diametro}) (drill {diametro}) (layers "*.Cu" "*.Mask"))
)
"""


def escribir_kicad(directorio, primitivas, taladros, forzar=False):
    """Crea el proyecto KiCad. No pisa la placa ni el esquema si ya existen
    (pueden tener componentes) salvo con forzar=True."""
    directorio.mkdir(parents=True, exist_ok=True)
    biblioteca = directorio / f"{LIB_FOOTPRINTS}.pretty"
    biblioteca.mkdir(exist_ok=True)
    diametro_m2 = next(d for _, d, _ in taladros if d < UMBRAL_TALADRO_MM)
    (biblioteca / f"{FOOTPRINT_TALADRO}.kicad_mod").write_text(footprint_taladro(
        diametro_m2,
        f'(footprint "{FOOTPRINT_TALADRO}"\n\t(version 20260206)\n\t(generator "suavizar_contorno")\n'
        f'\t(layer "F.Cu")'))
    tabla = directorio / "fp-lib-table"
    if not tabla.exists():
        tabla.write_text(
            f'(fp_lib_table\n\t(version 7)\n\t(lib (name "{LIB_FOOTPRINTS}") (type "KiCad") '
            f'(uri "${{KIPRJMOD}}/{LIB_FOOTPRINTS}.pretty") (options "") (descr "Footprints del FurbyGPT"))\n)\n')

    placa = directorio / f"{PROYECTO}.kicad_pcb"
    if placa.exists() and not forzar:
        print(f"{placa.name} ya existe: no se toca (usa --forzar-kicad para regenerarlo, "
              "o importa FurbyPCB-suave.dxf en Edge.Cuts)")
        return

    trazo = '(stroke (width 0.1) (type solid)) (layer "Edge.Cuts")'
    elementos = []
    for k, p in enumerate(primitivas):
        if p[0] == "linea":
            elementos.append(f'\t(gr_line (start {a_kicad(p[1])}) (end {a_kicad(p[2])}) '
                             f'{trazo} (uuid "{uuid_estable(f"borde-{k}")}"))')
        else:
            elementos.append(f'\t(gr_arc (start {a_kicad(p[1])}) (mid {a_kicad(p[2])}) '
                             f'(end {a_kicad(p[3])}) {trazo} (uuid "{uuid_estable(f"borde-{k}")}"))')

    numero = 0
    for centro, diametro, _ in taladros:
        if diametro >= UMBRAL_TALADRO_MM:
            borde = (centro[0] + diametro / 2, centro[1])
            elementos.append(f'\t(gr_circle (center {a_kicad(centro)}) (end {a_kicad(borde)}) '
                             f'{trazo} (fill no) (uuid "{uuid_estable("recorte")}"))')
            continue
        numero += 1
        cabecera = (f'\t(footprint "{LIB_FOOTPRINTS}:{FOOTPRINT_TALADRO}"\n\t(layer "F.Cu")\n'
                    f'\t(uuid "{uuid_estable(f"H{numero}")}")\n\t(at {a_kicad(centro)})\n'
                    f'\t(property "Reference" "H{numero}" (at 0 -3.15 0) (layer "F.SilkS") (hide yes) '
                    f'(effects (font (size 1 1) (thickness 0.15))))\n'
                    f'\t(property "Value" "M2" (at 0 3.15 0) (layer "F.Fab") '
                    f'(effects (font (size 1 1) (thickness 0.15))))')
        huella = footprint_taladro(diametro, cabecera).replace(
            "(attr exclude_from_pos_files exclude_from_bom)",
            "(attr board_only exclude_from_pos_files exclude_from_bom)")
        elementos.append(huella.rstrip())

    x0, y0 = ORIGEN_KICAD_MM
    pcb = f"""(kicad_pcb
\t(version 20260206)
\t(generator "suavizar_contorno")
\t(general (thickness 1.6))
\t(paper "A4")
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(2 "B.Cu" signal)
\t\t(5 "F.SilkS" user "F.Silkscreen")
\t\t(7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user)
\t\t(3 "B.Mask" user)
\t\t(13 "F.Paste" user)
\t\t(15 "B.Paste" user)
\t\t(17 "Dwgs.User" user "User.Drawings")
\t\t(19 "Cmts.User" user "User.Comments")
\t\t(25 "Edge.Cuts" user)
\t\t(27 "Margin" user)
\t\t(31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard")
\t\t(35 "F.Fab" user)
\t\t(33 "B.Fab" user)
\t)
\t(setup
\t\t(pad_to_mask_clearance 0)
\t\t(aux_axis_origin {x0} {y0})
\t\t(grid_origin {x0} {y0})
\t)
\t(net 0 "")
{chr(10).join(elementos)}
)
"""
    placa.write_text(pcb)
    esquema = directorio / f"{PROYECTO}.kicad_sch"
    if not esquema.exists():
        esquema.write_text(
            f'(kicad_sch\n\t(version 20231120)\n\t(generator "eeschema")\n'
            f'\t(uuid "{uuid_estable("esquema")}")\n\t(paper "A4")\n\t(lib_symbols)\n'
            f'\t(sheet_instances (path "/" (page "1")))\n)\n')
    proyecto = directorio / f"{PROYECTO}.kicad_pro"
    if not proyecto.exists():  # KiCad completa y reescribe este fichero al abrirlo
        proyecto.write_text(json.dumps({"meta": {"filename": proyecto.name, "version": 3}},
                                       indent=2) + "\n")


def mm(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",")


def acotar(ax, p0, p1, desplazamiento, texto, vertical=False):
    ax.annotate("", xy=p0, xytext=p1, arrowprops=dict(arrowstyle="<->", lw=0.8, color="#333"))
    medio = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    ax.text(medio[0] + (desplazamiento if vertical else 0), medio[1] + (0 if vertical else desplazamiento),
            texto, ha="center", va="center", fontsize=9, rotation=90 if vertical else 0,
            bbox=dict(fc="white", ec="none", pad=1))


def dibujar_contorno(ax, original, muestras, taladros, desviacion):
    cerrado = np.vstack([original, original[:1]])
    ax.plot(cerrado[:, 0], cerrado[:, 1], color="#9a9a9a", lw=1.4, label="Original (polígono)")
    ax.plot(*np.vstack([muestras, muestras[:1]]).T, color="#0b7bd6", lw=1.6,
            label=f"Suavizado (desviación máx. {mm(desviacion)} mm)")
    for centro, nuevo, viejo in taladros:
        ax.add_patch(plt.Circle(centro, viejo / 2, fill=False, ec="#9a9a9a", lw=1.0, ls="--"))
        ax.add_patch(plt.Circle(centro, nuevo / 2, fill=False, ec="#d6420b", lw=1.4))
        ax.plot(*centro, "+", color="#d6420b", ms=5, mew=0.8)


def escribir_render(ruta, original, primitivas, taladros, resultado, fillets_info):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    muestras = muestrear(primitivas, paso=0.01)
    fig = plt.figure(figsize=(14, 8.2), dpi=160)
    ax = fig.add_axes([0.03, 0.06, 0.6, 0.86])
    dibujar_contorno(ax, original, muestras, taladros, resultado["desviacion_max"])

    xmin, ymin = original.min(axis=0)
    xmax, ymax = original.max(axis=0)
    ancho_nuevo, alto_nuevo = np.ptp(muestras, axis=0)
    acotar(ax, (xmin, ymin - 4), (xmax, ymin - 4), -1.8,
           f"{mm(xmax - xmin)} mm (suavizado {mm(ancho_nuevo)})")
    acotar(ax, (xmin - 4, ymin), (xmin - 4, ymax), -1.8,
           f"{mm(ymax - ymin)} mm (suavizado {mm(alto_nuevo)})", vertical=True)
    for (cx, cy), nuevo, viejo in taladros:
        etiqueta = f"Ø{mm(nuevo, 1)} M2" if nuevo < UMBRAL_TALADRO_MM else f"Ø{mm(nuevo, 1)}"
        etiqueta += f"\n({mm(cx)}; {mm(cy)})"
        dy = -2.6 if nuevo < UMBRAL_TALADRO_MM else -nuevo / 2 - 2.2
        ax.text(cx, cy + dy, etiqueta, ha="center", va="top", fontsize=7.5, color="#a8330a")
    ax.set_aspect("equal")
    ax.set_xlim(xmin - 8, xmax + 3)
    ax.set_ylim(ymin - 8, ymax + 3)
    ax.grid(True, lw=0.3, color="#e4e4e4")
    ax.set_xlabel("mm")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.06), ncol=2, fontsize=9, frameon=False)
    fig.suptitle("FurbyGPT · contorno de PCB original frente a suavizado", x=0.03, y=0.985,
                 ha="left", fontsize=13, fontweight="bold")

    # Detalles: esquina superior izquierda del borde recto y la esquina con más
    # giro del resto del contorno.
    poligono = fillets_info["poligono"]
    superior = poligono[:, 1] > ymax - 1
    esquina_recta = int(np.argmin(np.where(superior, poligono[:, 0], np.inf)))
    esquina_giro = int(np.argmax(np.where(superior, 0, np.abs(fillets_info["giro"]))))
    for k, indice in enumerate((esquina_recta, esquina_giro)):
        vertice = poligono[indice]
        zoom = fig.add_axes([0.665 + k * 0.165, 0.5, 0.15, 0.38])
        dibujar_contorno(zoom, original, muestras, taladros, resultado["desviacion_max"])
        zoom.set_aspect("equal")
        zoom.set_xlim(vertice[0] - 3.5, vertice[0] + 3.5)
        zoom.set_ylim(vertice[1] - 3.5, vertice[1] + 3.5)
        zoom.grid(True, lw=0.3, color="#e4e4e4")
        zoom.tick_params(labelsize=7)
        zoom.set_title(f"({mm(vertice[0])}; {mm(vertice[1])})\n"
                       f"R {mm(fillets_info['radio'][indice], 1)} mm, "
                       f"desv. {mm(fillets_info['desviacion'][indice])} mm", fontsize=8)

    lineas = [f"Desviación máxima hacia dentro: {mm(resultado['desviacion_max'], 3)} mm",
              "Ningún punto del borde nuevo sale del original",
              f"Radio de los arcos: {mm(fillets_info['radio_min'], 1)} a {mm(fillets_info['radio_max'], 0)} mm",
              "", "Distancia borde de taladro a borde de placa:"]
    for (cx, cy), diametro, _, holgura in resultado["holguras"]:
        lineas.append(f"  Ø{mm(diametro, 1)} en ({mm(cx)}; {mm(cy)}): {mm(holgura)} mm")
    fig.text(0.67, 0.40, "\n".join(lineas), va="top", fontsize=9, family="monospace")
    fig.savefig(ruta)
    plt.close(fig)


# ---------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--entrada", type=Path, default=DXF_ENTRADA)
    parser.add_argument("--desviacion", type=float, default=DESVIACION_MAX_MM,
                        help="desviación máxima hacia dentro en cada vértice, mm (0,5)")
    parser.add_argument("--fusion", type=float, default=FUSION_MAX_MM,
                        help="longitud máxima de segmento que se absorbe en un solo arco, mm (0 = no)")
    parser.add_argument("--forzar-kicad", action="store_true",
                        help="regenera FurbyGPT.kicad_pcb aunque exista (borra lo que tenga)")
    parser.add_argument("--taladro", type=float, default=TALADRO_M2_MM, help="Ø taladros M2, mm")
    parser.add_argument("--recorte", type=float, default=RECORTE_GRANDE_MM, help="Ø agujero grande, mm")
    args = parser.parse_args()

    original, circulos = leer_dxf(args.entrada)
    poligono, escalones = limpiar_poligono(original)
    fusionado, holgura = fusionar_segmentos_cortos(poligono, original, args.fusion)
    try:
        fillets, primitivas = suavizar(original, fusionado, args.desviacion, holgura)
        poligono = fusionado
    except ValueError as error:
        print(f"Sin fusionar segmentos cortos: {error}")
        fillets, primitivas = suavizar(original, poligono, args.desviacion)
    taladros = normalizar_taladros(circulos, args.taladro, args.recorte)
    resultado = validar(original, primitivas, [(c, d) for c, d, _ in taladros])

    radios = fillets["radio"][fillets["radio"] > 0]
    fillets["poligono"] = poligono
    fillets["radio_min"], fillets["radio_max"] = radios.min(), radios.max()

    escribir_dxf(DXF_SALIDA, primitivas, taladros)
    escribir_kicad(KICAD_DIR, primitivas, taladros, args.forzar_kicad)
    escribir_render(RENDER_PNG, original, primitivas, taladros, resultado, fillets)

    print(f"Vértices originales: {len(original)}; tras limpiar y fusionar: {len(poligono)}")
    for viejo_i, viejo_j, nuevo in escalones:
        print(f"  Escalón eliminado {np.round(viejo_i, 4)}-{np.round(viejo_j, 4)} -> {np.round(nuevo, 4)}")
    print("Vértice (x; y)            giro°   tangente  radio    desviación")
    for i, v in enumerate(poligono):
        print(f"  ({v[0]:8.4f}; {v[1]:8.4f})  {math.degrees(fillets['giro'][i]):6.1f}  "
              f"{fillets['t'][i]:7.3f}  {fillets['radio'][i]:8.3f}  {fillets['desviacion'][i]:.4f}")
    rectas = [p for p in primitivas if p[0] == "linea"]
    print(f"Primitivas: {len(primitivas) - len(rectas)} arcos, {len(rectas)} rectas")
    for p in rectas:
        print(f"  recta {np.round(p[1], 3)} -> {np.round(p[2], 3)}  L={np.linalg.norm(p[2] - p[1]):.3f}")
    print(f"Desviación máxima original->nuevo: {resultado['desviacion_max']:.4f} mm")
    print(f"Desviación máxima nuevo->original: {resultado['desviacion_inversa']:.4f} mm")
    print(f"Giro total: {resultado['giro_total']:.4f}°")
    for centro, diametro, al_centro, holgura in resultado["holguras"]:
        print(f"  Ø{diametro} en {np.round(centro, 4)}: centro-borde {al_centro:.3f} mm, "
              f"borde-borde {holgura:.3f} mm")
    nuevo = muestrear(primitivas, paso=0.01)
    print(f"Caja nueva: {np.ptp(nuevo[:, 0]):.3f} x {np.ptp(nuevo[:, 1]):.3f} mm")


if __name__ == "__main__":
    main()
