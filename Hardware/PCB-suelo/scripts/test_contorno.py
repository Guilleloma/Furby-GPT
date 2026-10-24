#!/usr/bin/env python3
"""Comprobaciones de contorno-pcb.dxf. Sale con código 1 si alguna falla.

- El contorno (capa Contorno) es un único polígono cerrado y sin autointersecciones.
- Hay 4 taladros M2 de Ø2,3 en sus posiciones, a 2,5 mm o más del borde.
- El agujero del mecanismo y su zona de exclusión están dentro de la PCB.
- Los 4 agujeros originales del suelo (capa AgujerosBase) están en su sitio.
  Por defecto la PCB no tiene muescas: cada centro queda bajo la PCB, a 1,0 mm
  o más de su borde, y no hay capa Muescas. Con --muescas, en cambio, no hay
  PCB a menos de --muesca-r (3,0 mm por defecto) de cada centro.
- geometria.json, que lee el script de la base, coincide con el DXF: taladros,
  mecanismo y su exclusión, y las muescas ("muescas": null sin muescas;
  centros y radio con --muescas); y trae la funda del cable.
- Con --suelo, además, el contorno queda dentro del suelo y a 0,5 mm o más de
  la pared. El DXF del suelo no está en el repositorio, así que sin --suelo
  esa comprobación se salta.

Uso (desde Hardware/PCB-suelo):
    python -I scripts/test_contorno.py
    python -I scripts/test_contorno.py --suelo <ruta a suelo-interior.dxf>
    python -I scripts/test_contorno.py --muescas --muesca-r 3.5
"""

import argparse
import json
import math
import sys
from pathlib import Path

import ezdxf
import numpy as np
import shapely
from shapely.geometry import LinearRing, Point, Polygon

DXF_PCB = Path(__file__).resolve().parent.parent / "contorno-pcb.dxf"
JSON_GEOMETRIA = DXF_PCB.parent / "geometria.json"

TALADROS_ESPERADOS = [(-97.0, -68.5), (-50.0, -68.5), (-86.7, -121.9), (-60.3, -121.9)]
TALADRO_D = 2.3
AGUJEROS_BASE_ESPERADOS = [(-105.51, -78.23), (-41.33, -78.15), (-105.77, -106.80), (-41.23, -106.83)]
AGUJERO_BASE_D = 2.134
MUESCA_R = 3.0
# Sin muescas y con holgura de 1,0, el borde de la PCB pasa a 0,57-0,65 mm por fuera de
# cada centro. Los agujeros están tapados en la base, así que basta con que queden debajo.
AGUJERO_BAJO_PCB_MIN = 0.5
BORDE_TALADRO_MIN = 2.5
HOLGURA_MIN = 1.0
TOL_POSICION = 0.01
TOL_EXTREMOS = 1e-4
PASO_MM = 0.01


def extremos(entidad):
    if entidad.dxftype() == "LINE":
        return np.array(entidad.dxf.start)[:2], np.array(entidad.dxf.end)[:2]
    return np.array(entidad.start_point)[:2], np.array(entidad.end_point)[:2]


def puntos(entidad):
    """Puntos de la entidad desde su inicio DXF hasta su final (arcos antihorarios)."""
    inicio, fin = extremos(entidad)
    if entidad.dxftype() == "LINE":
        n = max(2, int(np.linalg.norm(fin - inicio) / PASO_MM))
        return inicio + np.linspace(0, 1, n)[:, None] * (fin - inicio)
    a0 = math.radians(entidad.dxf.start_angle)
    barrido = math.radians((entidad.dxf.end_angle - entidad.dxf.start_angle) % 360)
    r = entidad.dxf.radius
    n = max(4, int(barrido * r / PASO_MM))
    a = a0 + np.linspace(0, barrido, n)
    centro = np.array(entidad.dxf.center)[:2]
    return centro + r * np.column_stack([np.cos(a), np.sin(a)])


def encadenar(entidades):
    """Recorre las entidades por sus extremos y devuelve los puntos del anillo.
    Falla si sobra alguna entidad (más de un anillo) o si el anillo no cierra."""
    pendientes = list(entidades)
    primera = pendientes.pop(0)
    anillo = [puntos(primera)]
    actual = extremos(primera)[1]
    inicio = extremos(primera)[0]
    while pendientes:
        for k, entidad in enumerate(pendientes):
            a, b = extremos(entidad)
            if np.linalg.norm(a - actual) < TOL_EXTREMOS:
                anillo.append(puntos(entidad))
                actual = b
                break
            if np.linalg.norm(b - actual) < TOL_EXTREMOS:
                anillo.append(puntos(entidad)[::-1])
                actual = a
                break
        else:
            raise AssertionError(f"{len(pendientes)} entidades no continúan el contorno en {actual}")
        pendientes.pop(k)
    if np.linalg.norm(actual - inicio) > TOL_EXTREMOS:
        raise AssertionError(f"El contorno no cierra: termina en {actual} y empieza en {inicio}")
    # Cada tramo repite el extremo del anterior: shapely trata los puntos
    # repetidos seguidos como una autointersección.
    muestras = np.vstack(anillo)
    salto = np.linalg.norm(np.diff(muestras, axis=0), axis=1)
    muestras = muestras[np.r_[True, salto > 1e-9]]
    return muestras[:-1] if np.linalg.norm(muestras[-1] - muestras[0]) < 1e-9 else muestras


def leer_pcb(ruta):
    msp = ezdxf.readfile(ruta).modelspace()
    contorno = [e for e in msp.query("LINE ARC") if e.dxf.layer == "Contorno"]
    circulos = {}
    for c in msp.query("CIRCLE"):
        circulos.setdefault(c.dxf.layer, []).append((tuple(c.dxf.center)[:2], 2 * c.dxf.radius))
    return contorno, circulos


def comprobar_contorno(contorno):
    if not contorno:
        raise AssertionError("No hay entidades en la capa Contorno")
    muestras = encadenar(contorno)
    anillo = LinearRing(muestras)
    if not anillo.is_simple:
        raise AssertionError("El contorno se corta a sí mismo")
    placa = Polygon(anillo)
    if not placa.is_valid:
        raise AssertionError("El contorno no forma un polígono válido")
    return placa, f"{len(contorno)} entidades, cerrado y simple, área {placa.area:.1f} mm²"


def comprobar_taladros(placa, taladros):
    if len(taladros) != len(TALADROS_ESPERADOS):
        raise AssertionError(f"Hay {len(taladros)} taladros y se esperaban {len(TALADROS_ESPERADOS)}")
    margenes = []
    for esperado in TALADROS_ESPERADOS:
        cercano = min(taladros, key=lambda t: math.dist(t[0], esperado))
        centro, diametro = cercano
        if math.dist(centro, esperado) > TOL_POSICION:
            raise AssertionError(f"No hay taladro en {esperado} (el más cercano está en {centro})")
        if abs(diametro - TALADRO_D) > TOL_POSICION:
            raise AssertionError(f"Taladro en {esperado} de Ø{diametro:.3f}, se esperaba Ø{TALADRO_D}")
        if not placa.contains(Point(centro)):
            raise AssertionError(f"Taladro en {esperado} fuera de la PCB")
        margen = placa.exterior.distance(Point(centro)) - diametro / 2
        if margen < BORDE_TALADRO_MIN:
            raise AssertionError(f"Taladro en {esperado} a {margen:.3f} mm del borde (mínimo {BORDE_TALADRO_MIN})")
        margenes.append(margen)
    return f"4 × Ø{TALADRO_D}; borde mínimo {min(margenes):.2f} mm"


def comprobar_mecanismo(placa, circulos):
    detalles = []
    for capa in ("Mecanismo", "ExclusionMecanismo"):
        if len(circulos.get(capa, [])) != 1:
            raise AssertionError(f"Se esperaba un círculo en la capa {capa}")
        centro, diametro = circulos[capa][0]
        disco = Point(centro).buffer(diametro / 2, quad_segs=256)
        if not placa.contains(disco):
            raise AssertionError(f"{capa} (Ø{diametro:.2f}) no está dentro de la PCB")
        margen = placa.exterior.distance(Point(centro)) - diametro / 2
        detalles.append(f"{capa} Ø{diametro:.1f} a {margen:.2f} mm del borde")
    return "; ".join(detalles)


def comprobar_agujeros_base(placa, agujeros, muesca_r):
    """Con `muesca_r` None se espera la PCB sin muescas, tapando los agujeros."""
    if len(agujeros) != len(AGUJEROS_BASE_ESPERADOS):
        raise AssertionError(f"Hay {len(agujeros)} agujeros de la base y se esperaban "
                             f"{len(AGUJEROS_BASE_ESPERADOS)}")
    libres = []
    for esperado in AGUJEROS_BASE_ESPERADOS:
        centro, diametro = min(agujeros, key=lambda a: math.dist(a[0], esperado))
        if math.dist(centro, esperado) > TOL_POSICION:
            raise AssertionError(f"No hay agujero de la base en {esperado} (el más cercano está en {centro})")
        if abs(diametro - AGUJERO_BASE_D) > TOL_POSICION:
            raise AssertionError(f"Agujero de la base en {esperado} de Ø{diametro:.3f}, "
                                 f"se esperaba Ø{AGUJERO_BASE_D}")
        if muesca_r is None:
            if not placa.contains(Point(centro)):
                raise AssertionError(f"El agujero de la base en {esperado} queda fuera de la PCB: "
                                     "hay muesca y se esperaba sin muescas")
            bajo_pcb = placa.exterior.distance(Point(centro))
            if bajo_pcb < AGUJERO_BAJO_PCB_MIN:
                raise AssertionError(f"Borde de la PCB a {bajo_pcb:.3f} mm del agujero de la base en {esperado} "
                                     f"(se piden {AGUJERO_BAJO_PCB_MIN} sin muescas)")
            libres.append(bajo_pcb)
            continue
        # Las muestras del contorno son cuerdas de 0,01 mm: en un arco cóncavo
        # de R 3 se acercan 4e-6 mm al centro.
        libre = placa.distance(Point(centro))
        if libre < muesca_r - 1e-5:
            raise AssertionError(f"PCB a {libre:.3f} mm del agujero de la base en {esperado} "
                                 f"(se piden {muesca_r})")
        libres.append(libre)
    if muesca_r is None:
        return f"4 × Ø{AGUJERO_BASE_D} bajo la PCB, sin muescas; borde a ≥ {min(libres):.3f} mm de cada centro"
    return f"4 × Ø{AGUJERO_BASE_D} libres; PCB a ≥ {min(libres):.3f} mm de cada centro (se piden {muesca_r})"


def comprobar_geometria_json(ruta, circulos, muesca_r):
    try:
        return comparar_geometria_json(json.loads(ruta.read_text()), circulos, muesca_r)
    except KeyError as error:
        raise AssertionError(f"Falta el campo {error} en {ruta.name}") from error


def comparar_geometria_json(geometria, circulos, muesca_r):

    def mismos_circulos(capa, centros, diametro, nombre):
        en_dxf = circulos.get(capa, [])
        if len(en_dxf) != len(centros):
            raise AssertionError(f"{nombre}: {len(centros)} en el JSON y {len(en_dxf)} en la capa {capa}")
        for centro in centros:
            dxf_centro, dxf_diametro = min(en_dxf, key=lambda c: math.dist(c[0], centro))
            if math.dist(dxf_centro, centro) > 1e-6 or abs(dxf_diametro - diametro) > 1e-6:
                raise AssertionError(f"{nombre} en {centro} Ø{diametro} no coincide con el DXF "
                                     f"({dxf_centro} Ø{dxf_diametro:.3f})")

    mismos_circulos("Taladros", geometria["taladros"], geometria["taladro_diametro"], "Taladros")
    mecanismo = geometria["mecanismo"]
    mismos_circulos("Mecanismo", [mecanismo["centro"]], mecanismo["diametro"], "Mecanismo")
    mismos_circulos("ExclusionMecanismo", [mecanismo["centro"]], mecanismo["exclusion_diametro"],
                    "Exclusión del mecanismo")
    muescas = geometria["muescas"]
    if muesca_r is None:
        if muescas is not None:
            raise AssertionError(f"El JSON trae muescas y se esperaba \"muescas\": null: {muescas}")
        mismos_circulos("Muescas", [], 0, "Muescas")
        texto_muescas = "sin muescas (null)"
    else:
        if not muescas:
            raise AssertionError(f"El JSON no trae muescas (\"muescas\": {json.dumps(muescas)}) y se piden")
        mismos_circulos("Muescas", muescas["centros"], 2 * muescas["radio"], "Muescas")
        if muescas["radio"] < muesca_r - 1e-9:
            raise AssertionError(f"Muescas de R {muescas['radio']} en el JSON (se piden {muesca_r})")
        texto_muescas = f"muescas R {muescas['radio']}"
    funda = geometria["funda"]
    if not (funda["ancho"] > 0 and funda["alto"] > 0):
        raise AssertionError(f"Funda del cable sin medidas: {funda}")
    return (f"exclusión Ø{mecanismo['exclusion_diametro']}, {texto_muescas}, "
            f"funda {funda['ancho']} × {funda['alto']}{' (supuesto)' if funda.get('supuesto') else ''}")


def comprobar_holgura(placa, ruta_suelo):
    msp = ezdxf.readfile(ruta_suelo).modelspace()
    polilineas = [e for e in msp.query("LWPOLYLINE") if e.dxf.layer == "SueloInterior"]
    if len(polilineas) != 1:
        raise AssertionError("Se esperaba una LWPOLYLINE en la capa SueloInterior")
    suelo = Polygon([(x, y) for x, y, *_ in polilineas[0].get_points()])
    if not suelo.contains(placa):
        raise AssertionError("La PCB sale del suelo")
    muestras = shapely.points(np.array(placa.exterior.coords))
    holgura = shapely.distance(muestras, suelo.exterior)
    if holgura.min() < HOLGURA_MIN - 1e-6:
        raise AssertionError(f"Holgura mínima {holgura.min():.4f} mm (se pide {HOLGURA_MIN})")
    return f"holgura mínima {holgura.min():.3f} mm"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pcb", type=Path, default=DXF_PCB)
    parser.add_argument("--geometria", type=Path, default=JSON_GEOMETRIA)
    parser.add_argument("--suelo", type=Path, help="DXF del suelo interior (capa SueloInterior)")
    parser.add_argument("--muescas", action="store_true",
                        help="la PCB lleva muescas en los agujeros originales (por defecto, sin muescas)")
    parser.add_argument("--muesca-r", type=float, default=MUESCA_R,
                        help="con --muescas: radio libre de PCB alrededor de cada agujero original, mm")
    args = parser.parse_args()
    muesca_r = args.muesca_r if args.muescas else None

    contorno, circulos = leer_pcb(args.pcb)
    fallos = 0
    placa = None
    comprobaciones = [
        ("contorno cerrado y simple", lambda: comprobar_contorno(contorno)),
        ("taladros M2", lambda: comprobar_taladros(placa, circulos.get("Taladros", []))),
        ("mecanismo y exclusión dentro", lambda: comprobar_mecanismo(placa, circulos)),
        ("agujeros de la base libres" if args.muescas else "agujeros de la base bajo la PCB, sin muescas",
         lambda: comprobar_agujeros_base(placa, circulos.get("AgujerosBase", []), muesca_r)),
        ("geometria.json coincide con el DXF",
         lambda: comprobar_geometria_json(args.geometria, circulos, muesca_r)),
    ]
    if args.suelo:
        comprobaciones.append(("holgura contra el suelo", lambda: comprobar_holgura(placa, args.suelo)))

    for nombre, comprobacion in comprobaciones:
        try:
            resultado = comprobacion()
            if nombre == "contorno cerrado y simple":
                placa, resultado = resultado
            print(f"OK     {nombre}: {resultado}")
        except AssertionError as error:
            fallos += 1
            print(f"FALLO  {nombre}: {error}")
            if placa is None:
                break
    if not args.suelo:
        print("SALTA  holgura contra el suelo: falta --suelo (el DXF del suelo no está en el repositorio)")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
