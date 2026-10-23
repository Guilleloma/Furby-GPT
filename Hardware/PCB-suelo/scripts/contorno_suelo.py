#!/usr/bin/env python3
"""Contorno de la PCB del FurbyGPT con la forma del suelo interior de la base.

La PCB va dentro de la base del Furby de 1998, apoyada en separadores sobre su
suelo. El contorno sale del suelo interior (polilínea facetada del STL):

1. Se encoge el suelo la holgura (--holgura) con esquinas en inglete, así cada
   lado queda paralelo a su pared.
2. Se simplifica por dentro: cada cuerda que sustituye a varios vértices deja
   todos esos vértices por fuera, así que nunca se acerca a la pared.
3. Cada vértice convexo se cambia por un arco tangente (fillet) que no se
   separa más de --desviacion del vértice; cada vértice cóncavo, por un arco de
   radio igual a la holgura, que es el radio de la fresa de JLCPCB (0,5 mm) y
   mantiene la holgura exacta en las esquinas de los hombros del lóbulo.
4. Se abre la ranura del USB-C de montaje medio en el borde trasero, centrada
   en el lóbulo.
5. Se abre una muesca circular (--muesca-r) alrededor de cada uno de los 4
   agujeros originales del suelo, por donde pasan los tornillos hacia el
   cuerpo, con las esquinas redondeadas.

Todo en coordenadas del STL de la base (mm, vista desde arriba, delante = y
máxima). Salidas: DXF del contorno, geometria.json para generar_kicad.py y los
renders de render/.

Uso (desde Hardware/PCB-suelo):
    python -I scripts/contorno_suelo.py --suelo <ruta a suelo-interior.dxf>
Requiere: ezdxf, numpy, matplotlib, shapely (ver scripts/requirements.txt).
"""

import argparse
import json
import math
from pathlib import Path

import ezdxf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import shapely  # noqa: E402
from matplotlib.patches import Arc, Circle, Polygon as ParchePoligono, Rectangle  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402

DIR = Path(__file__).resolve().parent.parent
DXF_SALIDA = DIR / "contorno-pcb.dxf"
JSON_SALIDA = DIR / "geometria.json"
RENDER_PLANTA = DIR / "render" / "planta.png"
RENDER_LATERAL = DIR / "render" / "lateral-lobulo.png"

CAPA_SUELO = "SueloInterior"
CAPA_PARED = "ParedExterior"
CAPA_AGUJEROS_BASE = "Agujeros"

HOLGURA_MM = 0.5            # PCB a pared, por lado
SIMPLIFICACION_MM = 0.12    # cuerda máxima hacia dentro al quitar facetas
DESVIACION_MM = 0.2         # separación máxima de cada fillet convexo a su vértice
CONCAVO_MIN_GRADOS = 3.0    # quiebros cóncavos menores son ruido de facetas: sin arco

# Supuesto: posición estimada del agujero del mecanismo (sin medir en el Furby).
MECANISMO_XY = (-60.88, -95.32)
MECANISMO_D = 11.3
EXCLUSION_MECANISMO_MM = 2.0   # anillo libre alrededor del agujero

TALADRO_M2_D = 2.3
BORDE_TALADRO_MIN_MM = 2.0     # borde del agujero a borde de PCB
TALADROS_XY = [(-97.0, -68.5), (-50.0, -68.5), (-86.8, -122.4), (-60.2, -122.4)]

# Los 4 agujeros originales del suelo (capa Agujeros) pasan tornillos hacia el
# cuerpo, cuya torreta baja hasta el suelo. Supuesto: torreta de Ø5,0 (de 2 a
# 2,5 veces un tornillo de plástico de unos 2 mm), más 0,5 de holgura por lado.
TORRETA_D = 5.0
MUESCA_HOLGURA_MM = 0.5
MUESCA_R = TORRETA_D / 2 + MUESCA_HOLGURA_MM
MUESCA_REDONDEO_MM = 0.5       # esquinas convexas entre el borde y la muesca

# USB-C de montaje medio HRO TYPE-C-31-M-28A (LCSC C2848622), PCB de 1,6 mm.
# Medidas del dibujo del fabricante (layout recomendado y alzado).
USB_X = -73.5
USB_RANURA_ANCHO = 9.24        # cuerpo de 8,94 + 0,15 por lado
USB_RANURA_FONDO = 6.70        # del borde de la PCB al final de la ranura
USB_ALIVIO_R = 0.5             # alivio en las esquinas del fondo (fresa de 0,5 de radio)
USB_SALIENTE_BOCA = 0.20       # la boca sobresale del borde de la PCB
USB_LARGO = 6.80
USB_ANCHO_CUERPO = 8.94
USB_CARCASA = (8.34 + 0.6, 3.16)   # carcasa metálica por fuera, ancho × alto
USB_CENTRO_SOBRE_CARA_SUP = 0.0    # el eje de la boca queda a ras de la cara superior

# Alturas (z del STL)
SUELO_Z = 1.905
SEPARADOR_MM = 2.0
PCB_GROSOR = 1.6
PARED_GROSOR_LOBULO = 1.70
SOBREMOLDEADO = (12.0, 6.5)    # funda típica de un USB-C macho, ancho × alto
HOLGURA_CORTE = 0.5            # por lado, alrededor de la funda
MARGEN_FUNDA_SUELO = 0.3       # la funda del cable no debe rozar el suelo
TOP_MOUNT_CENTRO = 1.63        # USB-C de superficie (HRO TYPE-C-31-M-17): eje sobre la cara superior

TOL = 1e-9


# ---------------------------------------------------------------- lectura

def leer_polilinea(doc, capa):
    for entidad in doc.modelspace().query("LWPOLYLINE"):
        if entidad.dxf.layer == capa:
            return np.array([(x, y) for x, y, *_ in entidad.get_points()], dtype=float)
    return None


def leer_suelo(ruta, capa):
    doc = ezdxf.readfile(ruta)
    suelo = leer_polilinea(doc, capa)
    if suelo is None:
        raise ValueError(f"No hay LWPOLYLINE en la capa {capa} de {ruta}")
    pared = leer_polilinea(doc, CAPA_PARED)
    agujeros = [((c.dxf.center.x, c.dxf.center.y), 2 * c.dxf.radius)
                for c in doc.modelspace().query("CIRCLE") if c.dxf.layer == CAPA_AGUJEROS_BASE]
    return suelo, pared, agujeros


# ---------------------------------------------------------------- geometría

def cruz(a, b):
    return a[0] * b[1] - a[1] * b[0]


def unitario(v):
    return v / np.linalg.norm(v)


def angulo(v):
    return math.atan2(v[1], v[0])


def area_con_signo(poligono):
    x, y = poligono[:, 0], poligono[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def giros(poligono):
    n = len(poligono)
    resultado = np.zeros(n)
    for i in range(n):
        a = poligono[i] - poligono[i - 1]
        b = poligono[(i + 1) % n] - poligono[i]
        resultado[i] = math.atan2(cruz(a, b), np.dot(a, b))
    return resultado


def quitar_colineales(poligono, tolerancia=1e-6):
    while True:
        g = giros(poligono)
        colineal = np.flatnonzero(np.abs(g) < tolerancia)
        if len(colineal) == 0:
            return poligono
        poligono = np.delete(poligono, colineal[0], axis=0)


def antihorario(poligono):
    return poligono if area_con_signo(poligono) > 0 else poligono[::-1]


def encoger_inglete(suelo, holgura):
    """Suelo encogido con esquinas en inglete. En los vértices cóncavos el
    inglete queda más lejos de la pared que la holgura, nunca más cerca."""
    encogido = Polygon(suelo).buffer(-holgura, join_style="mitre", mitre_limit=20)
    if encogido.geom_type != "Polygon":
        raise ValueError("La holgura parte el suelo en varias piezas")
    puntos = np.array(encogido.exterior.coords[:-1])
    return quitar_colineales(antihorario(puntos))


def simplificar_por_dentro(poligono, tolerancia):
    """Douglas-Peucker que solo acepta cuerdas con todos los vértices que
    sustituyen por fuera (lado de la pared). Los vértices cóncavos quedan
    siempre, porque cualquier cuerda que los salte pasaría por fuera."""
    g = giros(poligono)
    n = len(poligono)
    anclas = [i for i in range(n) if g[i] < -math.radians(CONCAVO_MIN_GRADOS)]
    if len(anclas) < 2:
        anclas = sorted({0, n // 2} | set(anclas))
    conservar = set(anclas)

    def tramo(indices):
        if len(indices) <= 2:
            return
        a, b = poligono[indices[0]], poligono[indices[-1]]
        cuerda = b - a
        largo = np.linalg.norm(cuerda)
        lado = np.array([cruz(cuerda, poligono[k] - a) / largo for k in indices[1:-1]])
        if lado.max() > TOL:            # algún vértice por dentro: la cuerda saldría
            corte = 1 + int(np.argmax(lado))
        elif -lado.min() > tolerancia:   # demasiado lejos hacia dentro
            corte = 1 + int(np.argmin(lado))
        else:
            return
        conservar.add(indices[corte])
        tramo(indices[:corte + 1])
        tramo(indices[corte:])

    for k, inicio in enumerate(anclas):
        fin = anclas[(k + 1) % len(anclas)]
        indices = [(inicio + m) % n for m in range(((fin - inicio) % n or n) + 1)]
        tramo(indices)
    return poligono[sorted(conservar)]


# -------------------------------------------------------------------- fillets

def calcular_fillets(poligono, desviacion, radio_concavo):
    """Longitud de tangente t y radio de cada vértice.

    Convexos: los radios crecen a la vez hasta que cada arco llega a su
    desviación máxima o él y su vecino ocupan todo el segmento común (como en
    Hardware/PCB/scripts/suavizar_contorno.py). Cóncavos: radio fijo.
    """
    n = len(poligono)
    entrada = [unitario(poligono[i] - poligono[i - 1]) for i in range(n)]
    salida = [unitario(poligono[(i + 1) % n] - poligono[i]) for i in range(n)]
    giro = giros(poligono)
    longitud = np.array([np.linalg.norm(poligono[(i + 1) % n] - poligono[i]) for i in range(n)])

    convexo = giro > TOL
    concavo = giro < -math.radians(CONCAVO_MIN_GRADOS)
    pendiente = np.where(convexo, np.tan(np.abs(giro) / 2), 0.0)
    t_max = np.where(convexo, desviacion / np.maximum(np.tan(np.abs(giro) / 4), TOL), 0.0)
    t = np.where(concavo, radio_concavo * np.tan(np.abs(giro) / 2), 0.0)
    for i in range(n):
        if t[i] + t[(i + 1) % n] > longitud[i] + TOL:
            raise ValueError(f"No cabe el arco cóncavo en el segmento {i}")

    activo = convexo.copy()
    while activo.any():
        limites = []
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

    radio = np.zeros(n)
    radio[convexo] = t[convexo] / pendiente[convexo]
    radio[concavo] = radio_concavo
    return {"t": t, "radio": radio, "giro": giro, "entrada": entrada, "salida": salida}


def arco(centro, r, a0, barrido):
    return {"tipo": "arco", "c": np.asarray(centro, float), "r": float(r), "a0": a0, "barrido": barrido}


def linea(p0, p1):
    return {"tipo": "linea", "p0": np.asarray(p0, float), "p1": np.asarray(p1, float)}


def inicio(p):
    if p["tipo"] == "linea":
        return p["p0"]
    return p["c"] + p["r"] * np.array([math.cos(p["a0"]), math.sin(p["a0"])])


def fin(p):
    if p["tipo"] == "linea":
        return p["p1"]
    a = p["a0"] + p["barrido"]
    return p["c"] + p["r"] * np.array([math.cos(a), math.sin(a)])


def medio(p):
    if p["tipo"] == "linea":
        return (p["p0"] + p["p1"]) / 2
    a = p["a0"] + p["barrido"] / 2
    return p["c"] + p["r"] * np.array([math.cos(a), math.sin(a)])


def construir_contorno(poligono, fillets):
    """Primitivas cerradas en sentido antihorario: arcos de fillet y rectas."""
    n = len(poligono)
    tramos = []
    for i in range(n):
        v, t, r = poligono[i], fillets["t"][i], fillets["radio"][i]
        if t < 1e-7:
            tramos.append((v, None, v))
            continue
        u_in, u_out = fillets["entrada"][i], fillets["salida"][i]
        tangente_in, tangente_out = v - u_in * t, v + u_out * t
        normal = np.array([-u_in[1], u_in[0]])          # hacia dentro de la placa
        sentido = 1.0 if fillets["giro"][i] > 0 else -1.0
        centro = tangente_in + sentido * normal * r
        tramos.append((tangente_in, arco(centro, r, angulo(tangente_in - centro), fillets["giro"][i]),
                       tangente_out))

    primitivas = []
    for i in range(n):
        _, fillet, salida = tramos[i]
        if fillet is not None:
            primitivas.append(fillet)
        siguiente = tramos[(i + 1) % n][0]
        if np.linalg.norm(siguiente - salida) > 1e-7:
            primitivas.append(linea(salida, siguiente))
    return primitivas


def muestrear(primitivas, paso=0.02):
    puntos = []
    for p in primitivas:
        if p["tipo"] == "linea":
            n = max(2, int(np.linalg.norm(p["p1"] - p["p0"]) / paso))
            s = np.linspace(0, 1, n, endpoint=False)[:, None]
            puntos.append(p["p0"] + s * (p["p1"] - p["p0"]))
        else:
            n = max(4, int(abs(p["barrido"]) * p["r"] / paso))
            a = p["a0"] + np.linspace(0, p["barrido"], n, endpoint=False)
            puntos.append(p["c"] + p["r"] * np.column_stack([np.cos(a), np.sin(a)]))
    return np.vstack(puntos)


# ------------------------------------------------------- ranura del USB-C

def cortar_vertical(primitivas, x, y_max):
    """Índice de la primitiva que cruza la vertical x por debajo de y_max y el
    punto de corte (el borde trasero, recorrido de izquierda a derecha)."""
    for k, p in enumerate(primitivas):
        a, b = inicio(p), fin(p)
        if not (min(a[0], b[0]) - TOL <= x <= max(a[0], b[0]) + TOL) or max(a[1], b[1]) > y_max:
            continue
        if p["tipo"] == "linea":
            s = (x - a[0]) / (b[0] - a[0])
            return k, a + s * (b - a)
        dy = math.sqrt(p["r"] ** 2 - (x - p["c"][0]) ** 2)
        for y in (p["c"][1] - dy, p["c"][1] + dy):
            relativo = (angulo(np.array([x, y]) - p["c"]) - p["a0"]) * np.sign(p["barrido"])
            if relativo % (2 * math.pi) <= abs(p["barrido"]) + TOL:
                return k, np.array([x, y])
    raise ValueError(f"La vertical x={x} no corta el borde trasero")


def partir(p, punto):
    """Divide una primitiva en el punto dado (que está sobre ella)."""
    if p["tipo"] == "linea":
        return linea(p["p0"], punto), linea(punto, p["p1"])
    a = angulo(punto - p["c"])
    parte = ((a - p["a0"]) * np.sign(p["barrido"])) % (2 * math.pi) * np.sign(p["barrido"])
    return arco(p["c"], p["r"], p["a0"], parte), arco(p["c"], p["r"], a, p["barrido"] - parte)


def abrir_ranura_usb(primitivas, x_centro):
    """Sustituye el borde trasero entre las dos paredes de la ranura por la
    ranura: paredes rectas, alivios semicirculares en las esquinas del fondo y
    fondo recto. Devuelve el contorno nuevo y la referencia del conector."""
    xi, xd = x_centro - USB_RANURA_ANCHO / 2, x_centro + USB_RANURA_ANCHO / 2
    y_limite = min(p[1] for p in muestrear(primitivas)) + 3.0
    ki, punto_i = cortar_vertical(primitivas, xi, y_limite)
    kd, punto_d = cortar_vertical(primitivas, xd, y_limite)
    k_centro, borde = cortar_vertical(primitivas, x_centro, y_limite)
    if not ki <= k_centro <= kd:
        raise ValueError("Orden inesperado de primitivas en el borde trasero")
    y_borde = borde[1]
    y_fondo = y_borde + USB_RANURA_FONDO
    r = USB_ALIVIO_R
    ranura = [
        linea(punto_i, (xi, y_fondo)),
        arco((xi + r, y_fondo), r, math.pi, -math.pi),
        linea((xi + 2 * r, y_fondo), (xd - 2 * r, y_fondo)),
        arco((xd - r, y_fondo), r, math.pi, -math.pi),
        linea((xd, y_fondo), punto_d),
    ]
    antes, _ = partir(primitivas[ki], punto_i)
    _, despues = partir(primitivas[kd], punto_d)
    nuevo = primitivas[:ki] + [antes] + ranura + [despues] + primitivas[kd + 1:]
    nuevo = [p for p in nuevo if longitud_primitiva(p) > 1e-6]
    # y_borde es el borde en el eje del conector (origen de la huella); a los
    # lados de la ranura el borde real queda algo más adentro porque el fondo
    # del lóbulo es curvo.
    referencia = {"x": x_centro, "y_borde": float(y_borde), "y_fondo": float(y_fondo),
                  "y_boca": float(y_borde - USB_SALIENTE_BOCA), "x_paredes": [xi, xd],
                  "y_borde_lados": [float(punto_i[1]), float(punto_d[1])]}
    return nuevo, referencia


def longitud_primitiva(p):
    if p["tipo"] == "linea":
        return float(np.linalg.norm(p["p1"] - p["p0"]))
    return abs(p["barrido"]) * p["r"]


# ------------------------------------------- muescas de los agujeros de la base

def cortes_circulo_recta(centro, radio, p0, direccion):
    """Parámetros s de los puntos p0 + s·direccion (unitaria) a distancia radio."""
    d = p0 - centro
    b = np.dot(d, direccion)
    discriminante = b * b - (np.dot(d, d) - radio * radio)
    if discriminante < 0:
        return []
    raiz = math.sqrt(discriminante)
    return [-b - raiz, -b + raiz]


def cortes_circulos(c0, r0, c1, r1):
    d = math.dist(c0, c1)
    if d < TOL or d > r0 + r1 or d < abs(r0 - r1):
        return []
    a = (r0 * r0 - r1 * r1 + d * d) / (2 * d)
    h = math.sqrt(max(r0 * r0 - a * a, 0.0))
    eje = (c1 - c0) / d
    base = c0 + a * eje
    normal = np.array([-eje[1], eje[0]])
    return [base + h * normal, base - h * normal]


def centros_redondeo(p, centro, radio, redondeo):
    """Centros de un redondeo convexo de radio `redondeo` tangente a la
    primitiva p (por dentro de la placa) y por fuera a la muesca de `radio`.
    Devuelve (centro, punto de tangencia, fracción a lo largo de p) para cada
    solución que cae dentro de p."""
    radio += redondeo
    soluciones = []
    if p["tipo"] == "linea":
        largo = longitud_primitiva(p)
        u = (p["p1"] - p["p0"]) / largo
        dentro = np.array([-u[1], u[0]])                 # antihorario: la placa a la izquierda
        desplazada = p["p0"] + dentro * redondeo
        for s in cortes_circulo_recta(centro, radio, desplazada, u):
            if -TOL <= s <= largo + TOL:
                soluciones.append((desplazada + s * u, p["p0"] + s * u, s / largo))
        return soluciones
    # Arco convexo (barrido > 0): su centro está dentro de la placa, el radio
    # desplazado se encoge; arco cóncavo: crece.
    r_desplazado = p["r"] - redondeo if p["barrido"] > 0 else p["r"] + redondeo
    for f in cortes_circulos(p["c"], r_desplazado, centro, radio):
        a = angulo(f - p["c"])
        relativo = ((a - p["a0"]) * np.sign(p["barrido"])) % (2 * math.pi)
        if relativo <= abs(p["barrido"]) + TOL:
            tangente = p["c"] + p["r"] * np.array([math.cos(a), math.sin(a)])
            soluciones.append((f, tangente, relativo / abs(p["barrido"])))
    return soluciones


def abrir_muesca(primitivas, centro, radio, redondeo):
    """Quita de la placa el círculo de `radio` alrededor de un agujero de la base
    que queda junto al borde. La muesca es un arco cóncavo de ese radio y sus
    dos esquinas con el borde, que serían picos convexos, se redondean con
    arcos de `redondeo` tangentes al borde y a la muesca."""
    centro = np.asarray(centro, float)
    n = len(primitivas)
    # Se gira la lista para que la muesca quede en el centro y no cruce el inicio.
    cercana = min(range(n), key=lambda k: np.linalg.norm(medio(primitivas[k]) - centro))
    giro = (cercana - n // 2) % n
    primitivas = primitivas[giro:] + primitivas[:giro]

    soluciones = []
    for k, p in enumerate(primitivas):
        if abs(k - n // 2) > 8:
            continue
        for f, tangente, fraccion in centros_redondeo(p, centro, radio, redondeo):
            if not any(np.linalg.norm(f - otro[2]) < 1e-6 for otro in soluciones):
                soluciones.append((k, fraccion, f, tangente))
    if len(soluciones) != 2:
        raise ValueError(f"La muesca de R {radio} en {tuple(centro)} no corta el borde en dos puntos "
                         f"({len(soluciones)} soluciones)")
    (k1, _, f1, t1), (k2, _, f2, t2) = sorted(soluciones, key=lambda s: (s[0], s[1]))

    m1 = centro + radio * unitario(f1 - centro)          # tangencias con la muesca
    m2 = centro + radio * unitario(f2 - centro)
    a1, b1 = angulo(t1 - f1), angulo(m1 - f1)
    a2, b2 = angulo(m2 - f2), angulo(t2 - f2)
    redondeo1 = arco(f1, redondeo, a1, (b1 - a1) % (2 * math.pi))
    redondeo2 = arco(f2, redondeo, a2, (b2 - a2) % (2 * math.pi))
    am1, am2 = angulo(m1 - centro), angulo(m2 - centro)
    muesca = arco(centro, radio, am1, -((am1 - am2) % (2 * math.pi)))

    antes, _ = partir(primitivas[k1], t1)
    if k1 == k2:
        _, resto = partir(primitivas[k1], t1)
        _, despues = partir(resto, t2)
    else:
        _, despues = partir(primitivas[k2], t2)
    nuevo = primitivas[:k1] + [antes, redondeo1, muesca, redondeo2, despues] + primitivas[k2 + 1:]
    return [p for p in nuevo if longitud_primitiva(p) > 1e-6]


# ---------------------------------------------------------------- validación

def validar(suelo, primitivas, holgura, taladros, mecanismo, usb, muescas, muesca_r, redondeo):
    for actual, siguiente in zip(primitivas, primitivas[1:] + primitivas[:1]):
        if np.linalg.norm(fin(actual) - inicio(siguiente)) > 1e-7:
            raise ValueError(f"Hueco en el contorno en {fin(actual)}")
    muestras = muestrear(primitivas, paso=0.01)
    placa = Polygon(muestras)
    if not placa.is_valid:
        raise ValueError("El contorno se corta a sí mismo")
    pared = Polygon(suelo)
    if not pared.contains(placa):
        raise ValueError("El contorno sale del suelo")
    distancias = shapely.distance(shapely.points(muestras), pared.exterior)
    if distancias.min() < holgura - 1e-6:
        raise ValueError(f"El contorno se acerca a {distancias.min():.4f} mm de la pared")

    # La holgura máxima solo tiene sentido fuera de la ranura del USB-C y de las muescas.
    xi, xd = usb["x_paredes"]
    fuera_ranura = ~((muestras[:, 0] > xi - 0.01) & (muestras[:, 0] < xd + 0.01)
                     & (muestras[:, 1] > usb["y_borde"] - 0.5))
    for centro in muescas:
        fuera_ranura &= np.linalg.norm(muestras - np.asarray(centro), axis=1) > muesca_r + 2 * redondeo + 0.1
    borde = LineString(np.vstack([muestras, muestras[:1]]))
    resultado = {
        "holgura_min": float(distancias.min()),
        "holgura_max": float(distancias[fuera_ranura].max()),
        "area": placa.area, "perimetro": placa.length,
        "caja": [float(v) for v in placa.bounds],
        "taladros": [], "mecanismo": None, "muescas": [],
    }
    for centro in muescas:
        libre = placa.distance(Point(centro))
        if libre < muesca_r - 1e-5:      # flecha de las cuerdas del muestreo: 4e-6 con R 3
            raise ValueError(f"La PCB queda a {libre:.3f} mm del agujero {centro} (se pide {muesca_r})")
        al_taladro = min(math.dist(t, centro) - muesca_r - TALADRO_M2_D / 2 for t in taladros)
        resultado["muescas"].append({"xy": [float(v) for v in centro], "libre": libre,
                                     "al_taladro": al_taladro})
    for centro in taladros:
        margen = borde.distance(Point(centro)) - TALADRO_M2_D / 2
        if margen < BORDE_TALADRO_MIN_MM - 1e-6 or not placa.contains(Point(centro)):
            raise ValueError(f"Taladro {centro}: {margen:.2f} mm a borde (mínimo {BORDE_TALADRO_MIN_MM})")
        al_mecanismo = math.dist(centro, mecanismo) - MECANISMO_D / 2 - TALADRO_M2_D / 2
        resultado["taladros"].append({"xy": centro, "borde": margen, "mecanismo": al_mecanismo})
    resultado["mecanismo"] = borde.distance(Point(mecanismo)) - MECANISMO_D / 2
    if resultado["mecanismo"] < EXCLUSION_MECANISMO_MM:
        raise ValueError("El agujero del mecanismo queda demasiado cerca del borde")
    return resultado


# -------------------------------------------------------------------- alturas

def alturas():
    """Cotas z (STL) del montaje en el lóbulo con el USB-C de montaje medio."""
    z_pcb_inf = SUELO_Z + SEPARADOR_MM
    z_pcb_sup = z_pcb_inf + PCB_GROSOR
    z_centro = z_pcb_sup + USB_CENTRO_SOBRE_CARA_SUP
    funda_inf = z_centro - SOBREMOLDEADO[1] / 2
    corte_inf = max(SUELO_Z, z_centro - SOBREMOLDEADO[1] / 2 - HOLGURA_CORTE)
    corte_sup = z_centro + SOBREMOLDEADO[1] / 2 + HOLGURA_CORTE
    # Separador mínimo para que la funda del cable libre el suelo con la holgura.
    separador_min = SOBREMOLDEADO[1] / 2 + MARGEN_FUNDA_SUELO - PCB_GROSOR - USB_CENTRO_SOBRE_CARA_SUP
    return {
        "z_pcb_inf": z_pcb_inf, "z_pcb_sup": z_pcb_sup, "z_centro_usb": z_centro,
        "centro_sobre_suelo": z_centro - SUELO_Z,
        "z_centro_top_mount": z_pcb_sup + TOP_MOUNT_CENTRO,
        "carcasa_inf": z_centro - USB_CARCASA[1] / 2, "carcasa_sup": z_centro + USB_CARCASA[1] / 2,
        "funda_inf": funda_inf, "corte_inf": corte_inf, "corte_sup": corte_sup,
        "corte_ancho": SOBREMOLDEADO[0] + 2 * HOLGURA_CORTE,
        "separador_min_funda": separador_min,
    }


# -------------------------------------------------------------------- salidas

def escribir_dxf(ruta, primitivas, taladros, mecanismo, usb, agujeros_base, muesca_r):
    doc = ezdxf.new("R2010", setup=False, units=ezdxf.units.MM)
    doc.header["$MEASUREMENT"] = 1
    for nombre, color in (("Contorno", 3), ("Mecanismo", 1), ("Taladros", 1),
                          ("ExclusionMecanismo", 6), ("UsbC", 5), ("AgujerosBase", 2),
                          ("Muescas", 4)):
        doc.layers.add(nombre, color=color)
    msp = doc.modelspace()
    for p in primitivas:
        if p["tipo"] == "linea":
            msp.add_line(tuple(p["p0"]), tuple(p["p1"]), dxfattribs={"layer": "Contorno"})
        else:
            a0, a1 = p["a0"], p["a0"] + p["barrido"]
            if p["barrido"] < 0:
                a0, a1 = a1, a0
            msp.add_arc(tuple(p["c"]), p["r"], math.degrees(a0), math.degrees(a1),
                        dxfattribs={"layer": "Contorno"})
    msp.add_circle(mecanismo, MECANISMO_D / 2, dxfattribs={"layer": "Mecanismo"})
    msp.add_circle(mecanismo, MECANISMO_D / 2 + EXCLUSION_MECANISMO_MM,
                   dxfattribs={"layer": "ExclusionMecanismo"})
    for centro in taladros:
        msp.add_circle(centro, TALADRO_M2_D / 2, dxfattribs={"layer": "Taladros"})
    for centro, diametro in agujeros_base:
        msp.add_circle(centro, diametro / 2, dxfattribs={"layer": "AgujerosBase"})
        msp.add_circle(centro, muesca_r, dxfattribs={"layer": "Muescas"})
    x, y = usb["x"], usb["y_boca"]
    cuerpo = [(x - USB_ANCHO_CUERPO / 2, y), (x + USB_ANCHO_CUERPO / 2, y),
              (x + USB_ANCHO_CUERPO / 2, y + USB_LARGO), (x - USB_ANCHO_CUERPO / 2, y + USB_LARGO)]
    msp.add_lwpolyline(cuerpo, close=True, dxfattribs={"layer": "UsbC"})
    doc.saveas(ruta)


def a_json(primitivas):
    salida = []
    for p in primitivas:
        if p["tipo"] == "linea":
            salida.append({"tipo": "linea", "inicio": list(p["p0"]), "fin": list(p["p1"])})
        else:
            salida.append({"tipo": "arco", "inicio": list(inicio(p)), "medio": list(medio(p)),
                           "fin": list(fin(p)), "centro": list(p["c"]), "radio": p["r"]})
    return salida


def mm(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",")


def cota(ax, p0, p1, texto, desplazamiento=(0, 0), color="#333", tam=8, rot=0):
    ax.annotate("", xy=p0, xytext=p1, arrowprops=dict(arrowstyle="<->", lw=0.7, color=color,
                                                      shrinkA=0, shrinkB=0))
    centro = ((p0[0] + p1[0]) / 2 + desplazamiento[0], (p0[1] + p1[1]) / 2 + desplazamiento[1])
    ax.text(*centro, texto, ha="center", va="center", fontsize=tam, color=color, rotation=rot,
            bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))


def dibujar_base(ax, suelo, pared):
    if pared is not None:
        ax.add_patch(ParchePoligono(pared, closed=True, fc="#9a9a9a", ec="#555", lw=0.6))
    ax.add_patch(ParchePoligono(suelo, closed=True, fc="#e4eefb", ec="#1f5fbf", lw=0.8))


def render_planta(ruta, suelo, pared, agujeros_base, muestras, taladros, mecanismo, usb,
                  resultado, alt, muesca_r):
    fig = plt.figure(figsize=(15, 10.2), dpi=150)
    ax = fig.add_axes([0.03, 0.05, 0.6, 0.88])
    dibujar_base(ax, suelo, pared)
    ax.add_patch(ParchePoligono(muestras, closed=True, fc="#2e8b57", ec="#0e5a32", lw=1.3, alpha=0.55))
    ax.add_patch(Circle(mecanismo, MECANISMO_D / 2, fc="white", ec="#0e5a32", lw=1.2))
    ax.add_patch(Circle(mecanismo, MECANISMO_D / 2 + EXCLUSION_MECANISMO_MM, fill=False,
                        ec="#b0308f", lw=0.9, ls="--"))
    ax.text(mecanismo[0], mecanismo[1], f"Mecanismo\nØ{mm(MECANISMO_D, 1)}\n(supuesto)",
            ha="center", va="center", fontsize=7.5, color="#0e5a32")
    ax.text(mecanismo[0], mecanismo[1] - MECANISMO_D / 2 - EXCLUSION_MECANISMO_MM - 1.2,
            f"exclusión Ø{mm(MECANISMO_D + 2 * EXCLUSION_MECANISMO_MM, 1)}", ha="center", va="top",
            fontsize=7, color="#b0308f")
    for centro, diametro in agujeros_base:
        ax.add_patch(Circle(centro, diametro / 2, fc="white", ec="#c0392b", lw=0.9))
        ax.add_patch(Circle(centro, TORRETA_D / 2, fill=False, ec="#c0392b", lw=0.7, ls=":"))
        dx = 4.2 if centro[0] < -73.5 else -4.2
        ax.text(centro[0] + dx, centro[1], f"muesca R {mm(muesca_r, 1)}", ha="left" if dx > 0 else "right",
                va="center", fontsize=7, color="#c0392b")
    for k, t in enumerate(resultado["taladros"], start=1):
        cx, cy = t["xy"]
        ax.add_patch(Circle((cx, cy), TALADRO_M2_D / 2, fc="white", ec="#a8330a", lw=1.2))
        ax.add_patch(Circle((cx, cy), 2.5, fill=False, ec="#a8330a", lw=0.6, ls="--"))
        dy = 3.4 if cy < -100 else -3.4
        ax.text(cx, cy + dy, f"H{k} ({mm(cx)}; {mm(cy)})\nborde {mm(t['borde'])}",
                ha="center", va="bottom" if dy > 0 else "top", fontsize=7, color="#a8330a")

    x, yb = usb["x"], usb["y_boca"]
    ax.add_patch(Rectangle((x - USB_ANCHO_CUERPO / 2, yb), USB_ANCHO_CUERPO, USB_LARGO,
                           fc="#c9c9c9", ec="#222", lw=0.9, hatch="////"))
    ax.text(x, yb + USB_LARGO + 0.8, "USB-C (C2848622)", ha="center", va="bottom", fontsize=7.5)
    corte = alt["corte_ancho"]
    y_pared_ext = usb["y_pared_int"] - PARED_GROSOR_LOBULO
    ax.add_patch(Rectangle((x - corte / 2, y_pared_ext), corte, PARED_GROSOR_LOBULO, fc="#f5b041",
                           ec="#b9770e", lw=0.8))
    ax.text(x, y_pared_ext - 0.8, f"corte en la pared: {mm(corte, 1)} de ancho", ha="center", va="top",
            fontsize=7.5, color="#b9770e")

    xmin, ymin, xmax, ymax = resultado["caja"]
    cota(ax, (xmin, ymax + 3.5), (xmax, ymax + 3.5), f"PCB {mm(xmax - xmin)}", (0, 0.9))
    cota(ax, (xmax + 4.5, ymin), (xmax + 4.5, ymax), f"PCB {mm(ymax - ymin)}", (0.9, 0), rot=90)
    ax.text(-73.5, -56, "DELANTE", ha="center", fontsize=10, fontweight="bold")
    ax.text(-73.5, -112, "DETRÁS (lóbulo)", ha="center", fontsize=9, fontweight="bold")
    ax.set_aspect("equal")
    ax.set_xlim(-114, -31)
    ax.set_ylim(-136, -44)
    ax.grid(True, lw=0.3, color="#ddd")
    ax.set_xlabel("x (mm, STL)")
    ax.set_ylabel("y (mm, STL)")
    fig.suptitle("FurbyGPT · PCB con la forma del suelo de la base (vista desde arriba, coordenadas del STL)",
                 x=0.03, y=0.985, ha="left", fontsize=13, fontweight="bold")

    zoom = fig.add_axes([0.66, 0.53, 0.32, 0.38])
    dibujar_base(zoom, suelo, pared)
    zoom.add_patch(ParchePoligono(muestras, closed=True, fc="#2e8b57", ec="#0e5a32", lw=1.0, alpha=0.55))
    zoom.add_patch(Rectangle((x - USB_ANCHO_CUERPO / 2, yb), USB_ANCHO_CUERPO, USB_LARGO,
                             fc="#c9c9c9", ec="#222", lw=0.8, hatch="////", alpha=0.8))
    zoom.add_patch(Rectangle((x - corte / 2, y_pared_ext), corte, PARED_GROSOR_LOBULO, fc="#f5b041",
                             ec="#b9770e", lw=0.8))
    xi, xd = usb["x_paredes"]
    cota(zoom, (xi, usb["y_fondo"] + 1.6), (xd, usb["y_fondo"] + 1.6),
         f"ranura {mm(USB_RANURA_ANCHO)}", (0, 0.6), tam=7)
    cota(zoom, (xd + 1.2, usb["y_borde"]), (xd + 1.2, usb["y_fondo"]),
         f"{mm(USB_RANURA_FONDO)}", (0.8, 0), tam=7, rot=90)
    zoom.plot([x - 6, x + 6], [usb["y_borde"]] * 2, color="#0e5a32", lw=0.6, ls=":")
    zoom.text(x - 12.5, usb["y_borde"] + 0.25, "borde PCB", fontsize=6.5, color="#0e5a32")
    zoom.text(x + 7.2, yb - 0.6, f"boca a {mm(usb['boca_a_pared'])} de la pared",
              fontsize=6.5, color="#222")
    for t in resultado["taladros"][2:]:
        zoom.add_patch(Circle(t["xy"], TALADRO_M2_D / 2, fc="white", ec="#a8330a", lw=1.0))
    zoom.set_aspect("equal")
    zoom.set_xlim(x - 22, x + 22)
    zoom.set_ylim(-133, -113)
    zoom.grid(True, lw=0.3, color="#ddd")
    zoom.tick_params(labelsize=7)
    zoom.set_title("Lóbulo trasero: ranura del USB-C de montaje medio y corte de la pared", fontsize=9)

    lineas = [
        f"Holgura PCB-pared: {mm(resultado['holgura_min'], 3)} mín., {mm(resultado['holgura_max'], 2)} máx.",
        f"  (nominal {mm(HOLGURA_MM)}; JLCPCB ±0,2 + FDM ±0,2)",
        f"PCB: {mm(resultado['caja'][2] - resultado['caja'][0])} × "
        f"{mm(resultado['caja'][3] - resultado['caja'][1])}, {mm(resultado['area'], 0)} mm², grosor {mm(PCB_GROSOR, 1)}",
        f"Separadores: {mm(SEPARADOR_MM, 1)} sobre el suelo (z {mm(SUELO_Z, 3)})",
        f"Centro del USB-C: z {mm(alt['z_centro_usb'])} ({mm(alt['centro_sobre_suelo'])} sobre el suelo)",
        "",
        "Taladros M2 Ø2,3 (borde de agujero a borde de PCB):",
    ]
    for k, t in enumerate(resultado["taladros"], start=1):
        lineas.append(f"  H{k} ({mm(t['xy'][0])}; {mm(t['xy'][1])}): {mm(t['borde'])} mm")
    libre = min(m["libre"] for m in resultado["muescas"])
    lineas += ["", f"Agujeros originales de la base: muesca R {mm(muesca_r, 1)}",
               f"  (torreta Ø{mm(TORRETA_D, 1)} supuesta + {mm(muesca_r - TORRETA_D / 2, 1)} de holgura;"
               f" PCB a ≥ {mm(libre)} del centro)",
               "", "Rojo punteado: torreta del cuerpo (supuesta)", "Magenta: exclusión del mecanismo"]
    fig.text(0.665, 0.46, "\n".join(lineas), va="top", fontsize=8.5, family="monospace")
    fig.savefig(ruta)
    plt.close(fig)


def render_lateral(ruta, usb, alt, taladros):
    """Corte por x = USB_X (plano y-z), mirando desde la derecha (+x)."""
    fig, ax = plt.subplots(figsize=(13, 6.4), dpi=150)
    y_pared_int = usb["y_pared_int"]
    y_pared_ext = y_pared_int - PARED_GROSOR_LOBULO
    y_borde, y_boca, y_fondo = usb["y_borde"], usb["y_boca"], usb["y_fondo"]
    y_lados = min(usb["y_borde_lados"])
    gris = dict(fc="#9a9a9a", ec="#555", lw=0.6)
    ax.add_patch(Rectangle((y_pared_ext - 1.0, 0), 33, SUELO_Z, **gris))
    ax.add_patch(Rectangle((y_pared_ext, SUELO_Z), PARED_GROSOR_LOBULO, alt["corte_inf"] - SUELO_Z, **gris))
    ax.add_patch(Rectangle((y_pared_ext, alt["corte_sup"]), PARED_GROSOR_LOBULO, 22 - alt["corte_sup"], **gris))
    ax.add_patch(Rectangle((y_pared_ext, alt["corte_inf"]), PARED_GROSOR_LOBULO,
                           alt["corte_sup"] - alt["corte_inf"], fc="#f5b041", ec="#b9770e", lw=0.8, alpha=0.5))

    # En x = USB_X la PCB empieza en el fondo de la ranura; a los lados de la
    # ranura llega hasta el borde (en línea discontinua, por detrás del corte).
    ax.add_patch(Rectangle((y_lados, alt["z_pcb_inf"]), y_fondo - y_lados, PCB_GROSOR, fill=False,
                           ec="#0e5a32", lw=0.8, ls="--"))
    ax.add_patch(Rectangle((y_fondo, alt["z_pcb_inf"]), 26, PCB_GROSOR, fc="#2e8b57", ec="#0e5a32",
                           lw=0.8, alpha=0.8))
    y_sep = max(t[1] for t in taladros if t[1] < -110)
    ax.add_patch(Rectangle((y_sep - 2.5, SUELO_Z), 5.0, SEPARADOR_MM, fill=False, ec="#555", lw=0.7,
                           ls="--", hatch="xx"))
    ax.add_patch(Rectangle((y_boca, alt["carcasa_inf"]), USB_LARGO, USB_CARCASA[1], fc="#c9c9c9",
                           ec="#222", lw=0.9))
    ax.plot([y_pared_ext - 3, y_fondo + 4], [alt["z_centro_usb"]] * 2, color="#222", lw=0.5, ls="-.")
    largo_funda = 14
    ax.add_patch(Rectangle((y_boca - largo_funda, alt["funda_inf"]), largo_funda, SOBREMOLDEADO[1],
                           fc="#5d6d7e", ec="#1b2631", lw=0.8, alpha=0.55))

    ax.text(y_boca - 10, alt["z_centro_usb"] + 0.9, f"funda del cable\n{mm(SOBREMOLDEADO[0], 0)} × "
            f"{mm(SOBREMOLDEADO[1], 1)}", ha="center", va="bottom", fontsize=8, color="white")
    ax.text(y_boca - largo_funda + 0.3, alt["funda_inf"] - 0.3,
            f"funda a {mm(alt['funda_inf'] - SUELO_Z)} del suelo", fontsize=7, va="top")
    cota(ax, (y_pared_ext - 0.7, alt["corte_inf"]), (y_pared_ext - 0.7, alt["corte_sup"]), "",
         color="#b9770e")
    ax.text(y_pared_ext - 0.4, alt["corte_sup"] + 0.4,
            f"corte {mm(alt['corte_ancho'], 1)} × {mm(alt['corte_sup'] - alt['corte_inf'])}\n"
            f"z {mm(alt['corte_inf'], 3)} (suelo) a {mm(alt['corte_sup'])}", ha="right", va="bottom",
            fontsize=8, color="#b9770e")
    ax.text(y_pared_ext + PARED_GROSOR_LOBULO / 2, 17, "pared\n1,70", ha="center", fontsize=7.5)
    ax.text(y_boca + USB_LARGO / 2, alt["carcasa_sup"] + 0.3, "USB-C montaje medio", ha="center", fontsize=7.5)
    ax.text(y_boca + 0.1, alt["carcasa_inf"] - 0.3, f"boca a {mm(usb['boca_a_pared'])}\nde la pared",
            ha="left", va="top", fontsize=7)
    ax.text(y_fondo + 9, alt["z_pcb_sup"] + 0.3, "PCB", fontsize=8, color="#0e5a32")
    ax.text(y_sep + 2.8, SUELO_Z + SEPARADOR_MM / 2, "separador H3/H4\n(proyectado)", ha="left",
            va="center", fontsize=6.5, color="#555")
    ax.text(y_fondo + 26.5, 21.5,
            f"En x = {mm(usb['x'], 1)} la PCB empieza en el fondo de la ranura (y {mm(y_fondo)}).\n"
            f"A los lados de la ranura llega hasta y {mm(usb['y_borde_lados'][0])} (x {mm(usb['x_paredes'][0])}) "
            f"e y {mm(usb['y_borde_lados'][1])} (x {mm(usb['x_paredes'][1])}): en discontinua.\n"
            f"y {mm(y_borde)} es el borde nominal en el eje del conector (origen de la huella).\n"
            "Separadores en H3/H4, fuera de este corte: dibujados en discontinua.",
            ha="right", va="top", fontsize=7.5, color="#333")
    ax.text(y_pared_ext + 4, 0.95, f"suelo {mm(SUELO_Z, 3)}", fontsize=7.5, va="center")
    cota(ax, (y_fondo + 13, SUELO_Z), (y_fondo + 13, alt["z_centro_usb"]),
         f"{mm(alt['centro_sobre_suelo'])} sobre el suelo\n(z {mm(alt['z_centro_usb'])})", (3.0, 0), tam=7.5)
    cota(ax, (y_fondo + 22, SUELO_Z), (y_fondo + 22, alt["z_pcb_inf"]),
         f"sep. {mm(SEPARADOR_MM, 1)}", (1.6, 0), tam=7.5)
    cota(ax, (y_fondo + 22, alt["z_pcb_inf"]), (y_fondo + 22, alt["z_pcb_sup"]),
         f"PCB {mm(PCB_GROSOR, 1)}", (1.6, 0), tam=7.5)
    ax.set_aspect("equal")
    ax.set_xlim(y_pared_ext - 16, y_fondo + 27)
    ax.set_ylim(-1, 23)
    ax.grid(True, lw=0.3, color="#ddd")
    ax.set_xlabel("y (mm, STL) · detrás a la izquierda")
    ax.set_ylabel("z (mm)")
    ax.set_title(f"Corte por x = {mm(usb['x'], 1)}: lóbulo trasero, USB-C y corte de la pared "
                 "(cotas z del STL)", fontsize=11)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


# ---------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--suelo", type=Path, required=True,
                        help="DXF con la polilínea del suelo interior (capa SueloInterior)")
    parser.add_argument("--capa", default=CAPA_SUELO)
    parser.add_argument("--holgura", type=float, default=HOLGURA_MM, help="PCB a pared, mm (0,5)")
    parser.add_argument("--simplificacion", type=float, default=SIMPLIFICACION_MM)
    parser.add_argument("--desviacion", type=float, default=DESVIACION_MM)
    parser.add_argument("--mecanismo", type=float, nargs=2, default=MECANISMO_XY, metavar=("X", "Y"),
                        help="centro del agujero del mecanismo (supuesto)")
    parser.add_argument("--usb-x", type=float, default=USB_X)
    parser.add_argument("--taladro", type=float, nargs=2, action="append", metavar=("X", "Y"),
                        help="centro de un taladro M2 (repetir); por defecto los 4 propuestos")
    parser.add_argument("--muesca-r", type=float, default=MUESCA_R,
                        help="radio libre alrededor de cada agujero original del suelo, mm (3,0)")
    parser.add_argument("--muesca-redondeo", type=float, default=MUESCA_REDONDEO_MM,
                        help="radio de las esquinas entre el borde y la muesca, mm (0,5)")
    args = parser.parse_args()

    suelo, pared, agujeros_base = leer_suelo(args.suelo, args.capa)
    suelo = quitar_colineales(antihorario(suelo))
    encogido = encoger_inglete(suelo, args.holgura)
    simplificado = simplificar_por_dentro(encogido, args.simplificacion)
    fillets = calcular_fillets(simplificado, args.desviacion, args.holgura)
    primitivas = construir_contorno(simplificado, fillets)
    primitivas, usb = abrir_ranura_usb(primitivas, args.usb_x)
    if len(agujeros_base) != 4:
        raise ValueError(f"Se esperaban 4 agujeros en la capa {CAPA_AGUJEROS_BASE} y hay {len(agujeros_base)}")
    muescas = [centro for centro, _ in agujeros_base]
    for centro in muescas:
        primitivas = abrir_muesca(primitivas, centro, args.muesca_r, args.muesca_redondeo)

    taladros = [tuple(t) for t in (args.taladro or TALADROS_XY)]
    mecanismo = tuple(args.mecanismo)
    resultado = validar(suelo, primitivas, args.holgura, taladros, mecanismo, usb, muescas,
                        args.muesca_r, args.muesca_redondeo)

    pared_trasera = LineString(np.vstack([suelo, suelo[:1]]))
    usb["boca_a_pared"] = pared_trasera.distance(Point(usb["x"], usb["y_boca"]))
    usb["y_pared_int"] = usb["y_boca"] - usb["boca_a_pared"]
    alt = alturas()

    escribir_dxf(DXF_SALIDA, primitivas, taladros, mecanismo, usb, agujeros_base, args.muesca_r)
    muestras = muestrear(primitivas, paso=0.01)
    RENDER_PLANTA.parent.mkdir(parents=True, exist_ok=True)
    render_planta(RENDER_PLANTA, suelo, pared, agujeros_base, muestras, taladros, mecanismo, usb,
                  resultado, alt, args.muesca_r)
    render_lateral(RENDER_LATERAL, usb, alt, taladros)

    geometria = {
        "nota": "Coordenadas del STL de la base, mm. Generado por scripts/contorno_suelo.py",
        "contorno": a_json(primitivas),
        "mecanismo": {"centro": list(mecanismo), "diametro": MECANISMO_D,
                      "exclusion_diametro": MECANISMO_D + 2 * EXCLUSION_MECANISMO_MM},
        "funda": {"ancho": SOBREMOLDEADO[0], "alto": SOBREMOLDEADO[1], "supuesto": True},
        "taladros": [list(t) for t in taladros], "taladro_diametro": TALADRO_M2_D,
        "usb": {**usb, "ranura_ancho": USB_RANURA_ANCHO, "ranura_fondo": USB_RANURA_FONDO},
        "muescas": {"centros": [list(c) for c in muescas], "radio": args.muesca_r,
                    "redondeo": args.muesca_redondeo, "torreta_diametro": TORRETA_D},
        "alturas": alt, "resultado": resultado,
    }
    JSON_SALIDA.write_text(json.dumps(geometria, indent=1, ensure_ascii=False, default=float) + "\n")

    arcos = [p for p in primitivas if p["tipo"] == "arco"]
    radios = sorted(p["r"] for p in arcos)
    print(f"Suelo: {len(suelo)} vértices útiles; encogido: {len(encogido)}; simplificado: {len(simplificado)}")
    print(f"Primitivas: {len(arcos)} arcos, {len(primitivas) - len(arcos)} rectas; "
          f"radios {radios[0]:.2f} a {radios[-1]:.1f} mm")
    print(f"Holgura a la pared: mín {resultado['holgura_min']:.4f}, máx {resultado['holgura_max']:.3f} mm")
    print(f"Caja PCB: x {resultado['caja'][0]:.3f}…{resultado['caja'][2]:.3f}, "
          f"y {resultado['caja'][1]:.3f}…{resultado['caja'][3]:.3f}; área {resultado['area']:.1f} mm²")
    print(f"USB-C: borde PCB y={usb['y_borde']:.3f}, boca y={usb['y_boca']:.3f} "
          f"(a {usb['boca_a_pared']:.3f} de la pared), fondo ranura y={usb['y_fondo']:.3f}")
    for k, t in enumerate(resultado["taladros"], start=1):
        print(f"  H{k} {t['xy']}: borde {t['borde']:.2f} mm, al mecanismo {t['mecanismo']:.2f} mm")
    print(f"Mecanismo a borde de PCB: {resultado['mecanismo']:.2f} mm")
    for m in resultado["muescas"]:
        print(f"  Muesca R {args.muesca_r:.2f} en ({m['xy'][0]:.2f}; {m['xy'][1]:.2f}): PCB a "
              f"{m['libre']:.3f} mm del centro; borde de la muesca a {m['al_taladro']:.2f} mm del taladro más cercano")
    for clave, valor in alt.items():
        print(f"  {clave}: {valor:.3f}")


if __name__ == "__main__":
    main()
