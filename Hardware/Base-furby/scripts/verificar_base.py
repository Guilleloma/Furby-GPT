#!/usr/bin/env python3
"""Verificación de la base modificada del Furby (comprobaciones A a I del plan).

Mide sobre el STL original y sobre el de salida, escribe verificacion.json en la
carpeta de salida y sale con código 1 si alguna comprobación falla.

Uso (desde Hardware/Base-furby, con el venv):
    python -I scripts/verificar_base.py --base-stl <STL original> --salida <carpeta>
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
import trimesh
from shapely.geometry import Point, Polygon, box
from shapely.ops import nearest_points

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402


def resultado(ok, **datos):
    return {"ok": bool(ok), **datos}


def volumen(solido):
    return float(solido.volume())


def dilatar_caja(x0, x1, y0, y1, z0, z1, d, segmentos):
    """Caja dilatada d en distancia euclídea (suma de Minkowski con una esfera):
    una dilatación caja a caja sobredimensiona las esquinas en √2."""
    return comun.caja(x0, x1, y0, y1, z0, z1).minkowski_sum(comun.m3.Manifold.sphere(d, segmentos))


# -------------------------------------------------------------------- A

def comprobar_a(medidas, geo, par):
    v = par["verificacion"]
    z_ref = geo["alturas"]["corte_inf"]
    suelo = medidas["z_suelo_rayos"]
    inferior = medidas["z_inferior_rayos"]
    ok_suelo = all(abs(z - z_ref) <= v["z_tol"] for z in suelo)
    ok_inferior = all(abs(z - medidas["z_min"]) <= v["z_tol"] for z in inferior) and abs(medidas["z_min"]) <= v["z_tol"]
    pared = medidas["pared_lobulo"]
    ok_pared = all(abs(p["grosor"] - v["pared_grosor_esperado"]) <= v["pared_grosor_tol"] for p in pared)
    return resultado(ok_suelo and ok_inferior and ok_pared,
                     z_suelo_mediana=medidas["z_suelo"], z_suelo_min_max=suelo, rayos=v["rayos_suelo"],
                     z_inferior_min_max=inferior, z_min=medidas["z_min"], z_max=medidas["z_max"],
                     pared_lobulo=pared)


# -------------------------------------------------------------------- B

def alturas_seccion(medidas, par):
    v = par["verificacion"]
    z0, z1 = medidas["z_suelo"], medidas["z_max"]
    zs = [z0 + v["vertice_margen_z"]] + list(np.arange(z0 + v["seccion_paso"], z1, v["seccion_paso"]))
    return zs + [z1 - v["vertice_margen_z"]]


def comprobar_b(original, medidas, geo, par):
    v = par["verificacion"]
    seg = par["segmentos_circulo"]
    pcb = comun.contorno_pcb(geo, seg, con_agujeros=False)
    usb = box(*comun.caja_usb(geo, par))
    holgura_pcb, holgura_usb, dentro = math.inf, math.inf, True
    peor_usb = None
    for z in alturas_seccion(medidas, par):
        pared = max(comun.seccion(original, z), key=lambda q: q.area)
        cavidad = Polygon(max(pared.interiors, key=lambda a: Polygon(a).area))
        dentro &= cavidad.contains(pcb) and cavidad.contains(usb)
        holgura_pcb = min(holgura_pcb, cavidad.exterior.distance(pcb))
        d_usb = cavidad.exterior.distance(usb)
        if d_usb < holgura_usb:
            holgura_usb = d_usb
            a, b = nearest_points(cavidad.exterior, usb)
            peor_usb = {"z": float(z), "pared": [a.x, a.y], "usb": [b.x, b.y]}

    vert = original.vertices
    en_altura = (vert[:, 2] >= medidas["z_suelo"] + v["vertice_margen_z"])
    pcb_completa = comun.contorno_pcb(geo, seg)
    invasores = int(np.count_nonzero(shapely.contains_xy(pcb_completa, vert[en_altura, 0], vert[en_altura, 1])))

    ok = (dentro and holgura_pcb >= par["holgura_pcb_pared_min"] - v["holgura_tol"]
          and holgura_usb >= par["holgura_usb_pared_min"] - v["holgura_tol"] and invasores == 0)
    return resultado(ok, secciones=len(alturas_seccion(medidas, par)), holgura_pcb_min=holgura_pcb,
                     holgura_usb_min=holgura_usb, punto_usb_mas_cercano=peor_usb,
                     criterio_pcb=par["holgura_pcb_pared_min"], criterio_usb=par["holgura_usb_pared_min"],
                     vertices_dentro_prisma_pcb=invasores, pcb_y_usb_dentro=bool(dentro))


# -------------------------------------------------------------------- C

def comprobar_c(salida, salida_m, genero_original, par):
    cuerpos = len(salida.split(only_watertight=False))
    degenerados = int(np.count_nonzero(salida.area_faces < par["verificacion"]["triangulo_degenerado_area"]))
    genero = salida_m.genus()
    ok = (salida.is_watertight and salida.is_winding_consistent and cuerpos == 1
          and genero == genero_original + 1 and degenerados == 0)
    return resultado(ok, watertight=bool(salida.is_watertight),
                     normales_coherentes=bool(salida.is_winding_consistent), cuerpos=cuerpos,
                     genero=genero, genero_original=genero_original, genero_esperado=genero_original + 1,
                     triangulos=len(salida.faces), degenerados=degenerados)


# -------------------------------------------------------------------- D

def comprobar_d(original_m, salida_m, ops, par):
    separadores = [s for n, s in ops.items() if n.startswith("Separador_")]
    pilotos = [s for n, s in ops.items() if n.startswith("Piloto_")]
    union_sep = comun.m3.Manifold.batch_boolean(separadores, comun.m3.OpType.Add)
    con_sep = original_m + union_sep
    v_orig = volumen(original_m)
    v_sep = volumen(union_sep - original_m)
    v_ventana = volumen(original_m ^ ops["Ventana_USBC"])
    v_pilotos = volumen(con_sep ^ comun.m3.Manifold.batch_boolean(pilotos, comun.m3.OpType.Add))
    v_rebaje = volumen(con_sep ^ ops["Rebaje_Mecanismo"]) if "Rebaje_Mecanismo" in ops else 0.0
    esperado = v_orig + v_sep - v_ventana - v_pilotos - v_rebaje
    v_salida = volumen(salida_m)
    error = v_salida - esperado
    v_ref = par["volumen_base_esperado"]
    ok_orig = abs(v_orig - v_ref) <= v_ref * par["volumen_base_tolerancia_rel"]
    return resultado(abs(error) < par["verificacion"]["volumen_tol"] and ok_orig,
                     v_original=v_orig, v_original_esperado=v_ref, v_separadores_fuera=v_sep,
                     v_ventana=v_ventana, v_pilotos=v_pilotos, v_rebaje=v_rebaje,
                     v_esperado=esperado, v_salida=v_salida, error=error)


# -------------------------------------------------------------------- E

def comprobar_e(original, salida, medidas, ops, par):
    v = par["verificacion"]
    rng = np.random.default_rng(1)
    muestras, _ = trimesh.sample.sample_surface(original, v["intocado_muestras"], seed=rng)
    puntos = np.vstack([original.vertices, muestras])
    fuera = np.ones(len(puntos), dtype=bool)
    d = v["intocado_dilatacion"]
    for solido in ops.values():
        (x0, y0, z0), (x1, y1, z1) = solido.bounding_box()[:3], solido.bounding_box()[3:]
        dentro = ((puntos[:, 0] >= x0 - d) & (puntos[:, 0] <= x1 + d) & (puntos[:, 1] >= y0 - d)
                  & (puntos[:, 1] <= y1 + d) & (puntos[:, 2] >= z0 - d) & (puntos[:, 2] <= z1 + d))
        fuera &= ~dentro
    _, distancias, _ = salida.nearest.on_surface(puntos[fuera])
    dist_max = float(distancias.max())

    agujeros = []
    plato = max(comun.seccion(salida, v["agujero_z"]), key=lambda q: q.area)
    huecos = [Polygon(a) for a in plato.interiors]
    for a in medidas["agujeros"]:
        c = a["centro"]
        hueco = next((h for h in huecos if h.contains(Point(c))), None)
        d_salida = 2 * math.sqrt(hueco.area / math.pi) if hueco is not None else 0.0
        impactos = comun.rayos(salida, [(c[0], c[1], medidas["z_min"] - 5)], (0, 0, 1))[0]
        agujeros.append({"centro": c, "d": d_salida, "pasante": len(impactos) == 0})
    ok_agujeros = len(agujeros) == 4 and all(
        a["pasante"] and abs(a["d"] - v["agujero_original_d"]) <= v["agujero_original_tol"] for a in agujeros)
    return resultado(dist_max < v["intocado_dist"] and ok_agujeros, puntos_comprobados=int(fuera.sum()),
                     distancia_max=dist_max, agujeros_originales=agujeros)


# -------------------------------------------------------------------- F

def primer_impacto(malla, origen, direccion):
    h = comun.rayos(malla, [origen], direccion)[0]
    return h[0] if h else None


def comprobar_f(salida, medidas, geo, par, der):
    v = par["verificacion"]
    a, u = geo["alturas"], geo["usb"]
    x0, x1 = der["ventana_x"]
    # Plano de medida de la ventana: dentro de la pared, antes de que empiece el chaflán.
    y_int_jambas = max(p["y_int"] for p in medidas["pared_lobulo"])
    y_m = (der["y_chaflan_inicio"] + y_int_jambas) / 2
    z_m = (der["ventana_z"][0] + der["ventana_z"][1]) / 2
    xi = primer_impacto(salida, (u["x"], y_m, z_m), (-1, 0, 0))
    xd = primer_impacto(salida, (u["x"], y_m, z_m), (1, 0, 0))
    zs = primer_impacto(salida, (u["x"], y_m, z_m), (0, 0, 1))
    zi = primer_impacto(salida, (u["x"], y_m, z_m), (0, 0, -1))
    ventana = {"x": [xi, xd], "z": [zi, zs], "y_medida": y_m}
    tol = v["cota_tol"]
    ok_ventana = (None not in (xi, xd, zs, zi) and abs(xi - x0) <= tol and abs(xd - x1) <= tol
                  and abs(zi - der["ventana_z"][0]) <= tol and abs(zs - der["ventana_z"][1]) <= tol)

    # Chaflán real: rayo en +y a 0,01 por fuera de la jamba (o por encima del techo).
    # Choca con el chaflán donde su desplazamiento vale 0,01, así que su profundidad
    # desde la cara exterior original es la del chaflán (45°).
    chaflan = {}
    if par["ventana_chaflan_ext"] > 0:
        y_lejos = medidas["pared_lobulo"][0]["y_ext"] - 10
        z_techo = der["ventana_z"][1] + 0.01
        for x, origen in ((x0, (x0 - 0.01, y_lejos, z_m)), (u["x"], (u["x"], y_lejos, z_techo)),
                          (x1, (x1 + 0.01, y_lejos, z_m))):
            y_hit = primer_impacto(salida, origen, (0, 1, 0))
            chaflan[f"{x:.2f}"] = y_hit - comun.y_exterior(medidas, x) + 0.01 if y_hit is not None else None
    lo, hi_r = par["ventana_chaflan_rango"]
    ok_chaflan = all(c is not None and lo <= c <= hi_r for c in chaflan.values())

    seccion = comun.seccion(salida, v["separador_z_medida"])
    r_sep = par["separador_d"] / 2
    r_chaflan = par["piloto_d"] / 2 + par["piloto_chaflan"]
    separadores = []
    for i, t in enumerate(geo["taladros"], start=1):
        p = Point(t)
        poli = next((q for q in seccion if Polygon(q.exterior).contains(p)), None)
        if poli is None:
            separadores.append({"H": i, "encontrado": False})
            continue
        ext = Polygon(poli.exterior)
        hueco = next((Polygon(h) for h in poli.interiors if Polygon(h).contains(p)), None)
        r_cara = (r_sep + r_chaflan) / 2
        z_cara = primer_impacto(salida, (t[0] + r_cara, t[1], medidas["z_max"] + 5), (0, 0, -1))
        fondo = primer_impacto(salida, (t[0], t[1], medidas["z_max"] + 5), (0, 0, -1))
        apoyo = primer_impacto(salida, (t[0], t[1], medidas["z_min"] - 5), (0, 0, 1))
        separadores.append({
            "H": i, "encontrado": True,
            "error_centro": math.dist((ext.centroid.x, ext.centroid.y), t),
            "d": 2 * math.sqrt(ext.area / math.pi),
            "cara_sup": z_cara,
            "piloto_d": 2 * math.sqrt(hueco.area / math.pi) if hueco is not None else 0.0,
            "piloto_fondo": fondo,
            "piloto_prof": a["z_pcb_inf"] - fondo,
            "suelo_restante": fondo - apoyo,
        })
    dt = v["diametro_tol"]
    ok_sep = all(
        s["encontrado"] and s["error_centro"] < v["centro_tol"] and abs(s["d"] - par["separador_d"]) <= dt
        and abs(s["cara_sup"] - a["z_pcb_inf"]) <= v["z_tol"] and abs(s["piloto_d"] - par["piloto_d"]) <= dt
        and abs(s["piloto_prof"] - der["piloto_prof"]) <= v["z_tol"]
        and s["suelo_restante"] >= par["suelo_restante_min"] for s in separadores)
    return resultado(ok_ventana and ok_chaflan and ok_sep, ventana=ventana,
                     ventana_esperada={"x": der["ventana_x"], "z": der["ventana_z"]},
                     chaflan_real=chaflan, chaflan_rango=par["ventana_chaflan_rango"],
                     chaflan_y_referencia=der["y_ext_ref"], separadores=separadores)


# -------------------------------------------------------------------- G

def comprobar_g(salida_m, medidas, geo, par, der):
    v = par["verificacion"]
    seg = par["segmentos_circulo"]
    mec = geo["mecanismo"]
    zona = comun.cilindro(mec["centro"], der["z_suelo"] + v["exclusion_z_margen"], geo["alturas"]["z_pcb_inf"],
                          der["exclusion_d"], seg)
    v_exclusion = volumen(salida_m ^ zona)
    r_sep = par["separador_d"] / 2
    a_agujeros = min(math.dist(t, a["centro"]) - r_sep - a["d"] / 2
                     for t in geo["taladros"] for a in medidas["agujeros"])
    muescas = geo.get("muescas")
    if muescas:
        a_muescas = min(math.dist(t, c) - muescas["radio"] - r_sep for t in geo["taladros"] for c in muescas["centros"])
        ok_muescas = a_muescas >= 0
    else:
        a_muescas, ok_muescas = None, True
    ok = v_exclusion <= v["volumen_cero"] and a_agujeros >= v["separador_agujero_min"] and ok_muescas
    return resultado(ok, exclusion_d=der["exclusion_d"], volumen_en_exclusion=v_exclusion,
                     separador_a_agujero_min=a_agujeros, criterio_agujero=v["separador_agujero_min"],
                     muescas="comprobadas" if muescas else "sin muescas en geometria.json: se salta",
                     separador_a_muesca_min=a_muescas)


# -------------------------------------------------------------------- H

def distancia_caja(salida, x0, x1, y0, y1, z0, z1, n=20000):
    caja = trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])
    puntos, _ = trimesh.sample.sample_surface_even(caja, n, seed=2)
    puntos = np.vstack([puntos, caja.vertices])
    _, d, _ = salida.nearest.on_surface(puntos)
    return float(d.min())


def comprobar_h(salida, salida_m, geo, par, der):
    v = par["verificacion"]
    u, a = geo["usb"], geo["alturas"]
    f = (u["x"] - der["funda_ancho"] / 2, u["x"] + der["funda_ancho"] / 2,
         u["y_boca"] - par["funda_largo"], u["y_boca"], *der["funda_z"])
    v_funda = volumen(salida_m ^ dilatar_caja(*f, v["funda_dilatacion"], par["segmentos_circulo"]))
    x0, y0, x1, y1 = comun.caja_usb(geo, par)
    c = (x0, x1, y0, y1, a["carcasa_inf"], a["carcasa_sup"])
    v_usb = volumen(salida_m ^ dilatar_caja(*c, par["holgura_usb_pared_min"], par["segmentos_circulo"]))
    return resultado(v_funda <= v["volumen_cero"] and v_usb <= v["volumen_cero"],
                     funda_caja=f, funda_dilatada_interseccion=v_funda,
                     funda_distancia_min=distancia_caja(salida, *f),
                     usb_caja=c, usb_dilatado_interseccion=v_usb, usb_distancia_min=distancia_caja(salida, *c))


# -------------------------------------------------------------------- I

def comprobar_i(salida_m, fantasma_m, f_resultado, geo, par):
    v = par["verificacion"]
    z_inf = geo["alturas"]["z_pcb_inf"]
    fz = fantasma_m.bounding_box()
    tops = [s["cara_sup"] for s in f_resultado["separadores"] if s.get("encontrado")]
    holguras = [z_inf - t for t in tops]
    v_choque = volumen(salida_m ^ fantasma_m)
    ok = (len(tops) == len(geo["taladros"]) and all(abs(h) <= v["apoyo_tol"] for h in holguras)
          and v_choque <= v["volumen_cero"])
    return resultado(ok, z_pcb_inf=z_inf, fantasma_z_min=fz[2], separadores_cara_sup=tops,
                     separacion_pcb_separador=holguras, volumen_interseccion=v_choque)


# -------------------------------------------------------------------- todo

def verificar(original, original_m, salida, salida_m, fantasma_m, geo, par, medidas, der, ops):
    f = comprobar_f(salida, medidas, geo, par, der)
    comprobaciones = {
        "A_cotas_original": comprobar_a(medidas, geo, par),
        "B_interior_pcb": comprobar_b(original, medidas, geo, par),
        "C_malla_salida": comprobar_c(salida, salida_m, original_m.genus(), par),
        "D_volumen": comprobar_d(original_m, salida_m, ops, par),
        "E_intocado": comprobar_e(original, salida, medidas, ops, par),
        "F_medidas_salida": f,
        "G_exclusiones": comprobar_g(salida_m, medidas, geo, par, der),
        "H_cable": comprobar_h(salida, salida_m, geo, par, der),
        "I_apoyo": comprobar_i(salida_m, fantasma_m, f, geo, par),
    }
    return comprobaciones


def informe(comprobaciones, der, medidas, extra):
    datos = {
        "aprobado": all(c["ok"] for c in comprobaciones.values()),
        "derivados": {k: v for k, v in der.items()},
        "medidas_original": {k: v for k, v in medidas.items() if k not in ("cavidad", "puntos_suelo")},
        **extra,
        "comprobaciones": comprobaciones,
    }
    return datos


def a_json(datos):
    def convertir(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
        raise TypeError(type(o))
    return json.dumps(datos, indent=1, ensure_ascii=False, default=convertir)


def resumen(comprobaciones):
    for nombre, c in comprobaciones.items():
        print(f"  {'OK   ' if c['ok'] else 'FALLO'} {nombre}")


def preparar(base_stl, geometria, parametros):
    """Lee entradas, mide el original y construye los cortadores (lo común a modificar y verificar)."""
    par = comun.leer_json(parametros)
    geo = comun.leer_json(geometria)
    huella = comun.sha256(base_stl)
    if huella != par["sha256_base"]:
        print(f"AVISO: el sha256 del STL original ({huella[:12]}…) no es el esperado ({par['sha256_base'][:12]}…)")
    original = comun.leer_malla(base_stl)
    medidas = comun.medir_original(original, geo, par)
    z_ref = geo["alturas"]["corte_inf"]
    if abs(medidas["z_suelo"] - z_ref) > par["verificacion"]["z_suelo_tol_aborto"]:
        raise SystemExit(f"z del suelo medido {medidas['z_suelo']:.4f} ≠ alturas.corte_inf {z_ref}: se aborta")
    der = comun.derivados(geo, par, medidas)
    if der["suelo_restante"] < par["suelo_restante_min"]:
        raise SystemExit(f"Suelo bajo el piloto {der['suelo_restante']:.3f} < {par['suelo_restante_min']}: se aborta")
    return par, geo, original, medidas, der, huella


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base-stl", type=Path, required=True, help="STL original de la base")
    parser.add_argument("--salida", type=Path, required=True, help="carpeta con los STL de modificar_base.py")
    parser.add_argument("--geometria", type=Path, default=comun.GEOMETRIA)
    parser.add_argument("--parametros", type=Path, default=comun.PARAMETROS)
    args = parser.parse_args()

    salida_dir = comun.comprobar_salida_fuera_del_repo(args.salida)
    par, geo, original, medidas, der, huella = preparar(args.base_stl, args.geometria, args.parametros)
    original_m = comun.a_manifold(original)
    desfase = json.loads((salida_dir / comun.NOMBRE_VERIFICACION).read_text()).get("desfase_ventana", 0.0) \
        if (salida_dir / comun.NOMBRE_VERIFICACION).exists() else 0.0
    ops = comun.operaciones(geo, par, der, desfase)
    salida = comun.leer_malla(salida_dir / comun.NOMBRE_BASE)
    salida_m = comun.a_manifold(salida)
    fantasma_m = comun.pcb_fantasma(geo, par, der)
    comprobaciones = verificar(original, original_m, salida, salida_m, fantasma_m, geo, par, medidas, der, ops)
    datos = informe(comprobaciones, der, medidas, {"sha256_original": huella, "desfase_ventana": desfase})
    (salida_dir / comun.NOMBRE_VERIFICACION).write_text(a_json(datos), encoding="utf-8")
    resumen(comprobaciones)
    print("Aprobado" if datos["aprobado"] else "Hay comprobaciones en rojo")
    sys.exit(0 if datos["aprobado"] else 1)


if __name__ == "__main__":
    main()
