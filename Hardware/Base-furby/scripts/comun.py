"""Lectura de parámetros, medidas del STL original y operaciones de la base modificada.

Lo comparten modificar_base.py, verificar_base.py y render_base.py, así las
tres leen las mismas cotas y construyen los mismos cortadores.

Coordenadas del STL de la base del Furby de 1998: mm, vista desde arriba,
delante = y máxima, detrás (lóbulo y USB-C) = y mínima, z 0 sobre la cama.
"""

import hashlib
import json
import math
from pathlib import Path

import manifold3d as m3
import numpy as np
import trimesh
from shapely.geometry import Point, Polygon

DIR_BASE = Path(__file__).resolve().parent.parent
PARAMETROS = DIR_BASE / "parametros-base.json"
GEOMETRIA = DIR_BASE.parent / "PCB-suelo" / "geometria.json"

NOMBRE_BASE = "FurbyGPT-base-modificada.stl"
NOMBRE_PRUEBA = "prueba-lobulo.stl"
NOMBRE_CUPON = "cupon-pilotos.stl"
NOMBRE_FANTASMA = "pcb-fantasma.stl"
NOMBRE_VERIFICACION = "verificacion.json"


# -------------------------------------------------------------------- entrada y salida

def leer_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def raiz_repo(ruta):
    """Primer directorio con .git (carpeta o fichero de worktree) hacia arriba, o None."""
    for d in [ruta, *ruta.parents]:
        if (d / ".git").exists():
            return d
    return None


def comprobar_salida_fuera_del_repo(salida):
    """Los STL y renders son de un diseño de terceros: nunca dentro del repositorio."""
    repo = raiz_repo(DIR_BASE)
    destino = Path(salida).expanduser().resolve()
    if repo is not None and (destino == repo or repo in destino.parents):
        raise SystemExit("La salida está dentro del repositorio; los STL y renders van fuera.")
    return destino


def leer_malla(ruta):
    """STL con vértices fusionados (trimesh process=True)."""
    return trimesh.load(str(ruta), force="mesh")


def a_manifold(malla):
    mesh = m3.Mesh64(vert_properties=np.ascontiguousarray(malla.vertices, dtype=np.float64),
                     tri_verts=np.ascontiguousarray(malla.faces, dtype=np.uint64))
    solido = m3.Manifold(mesh)
    if solido.status() != m3.Error.NoError:
        raise SystemExit(f"Manifold no acepta la malla: {solido.status()}")
    return solido


def a_trimesh(solido):
    mesh = solido.to_mesh64()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)


def escribir_stl(solido, ruta):
    a_trimesh(solido).export(str(ruta), file_type="stl")


# -------------------------------------------------------------------- 2D

def muestrear_arco(p, segmentos):
    """Puntos de un arco de geometria.json (inicio, medio, fin, centro), sin el último."""
    c = np.array(p["centro"])
    a0, am, a1 = (math.atan2(q[1] - c[1], q[0] - c[0]) for q in (p["inicio"], p["medio"], p["fin"]))
    barrido = (a1 - a0) % (2 * math.pi)
    if (am - a0) % (2 * math.pi) > barrido:   # el medio no está en sentido antihorario: horario
        barrido -= 2 * math.pi
    n = max(2, math.ceil(abs(barrido) / (2 * math.pi) * segmentos))
    return [(c[0] + p["radio"] * math.cos(a0 + barrido * i / n),
             c[1] + p["radio"] * math.sin(a0 + barrido * i / n)) for i in range(n)]


def contorno_pcb(geo, segmentos, con_agujeros=True):
    puntos = []
    for p in geo["contorno"]:
        puntos += muestrear_arco(p, segmentos) if p["tipo"] == "arco" else [tuple(p["inicio"])]
    poligono = Polygon(puntos)
    if con_agujeros:
        agujeros = [Point(t).buffer(geo["taladro_diametro"] / 2, quad_segs=segmentos // 4)
                    for t in geo["taladros"]]
        mec = geo["mecanismo"]
        agujeros.append(Point(mec["centro"]).buffer(mec["diametro"] / 2, quad_segs=segmentos // 4))
        for a in agujeros:
            poligono = poligono.difference(a)
    return poligono


def caja_usb(geo, par):
    """Planta del cuerpo del USB-C: (x0, y0, x1, y1), desde la boca hacia dentro."""
    u = geo["usb"]
    ancho = par["usb_cuerpo_ancho"]
    return (u["x"] - ancho / 2, u["y_boca"], u["x"] + ancho / 2, u["y_boca"] + par["usb_cuerpo_largo"])


def seccion(malla, z):
    """Polígonos (shapely) de la sección horizontal en z."""
    s = malla.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return []
    plano, _ = s.to_2D(to_2D=np.eye(4))
    return list(plano.polygons_full)


def seccion_vertical(malla, eje, valor):
    """Sección por x = valor (eje 'x', polígonos en (y, z)) o y = valor (eje 'y', en (x, z))."""
    normal = [1, 0, 0] if eje == "x" else [0, 1, 0]
    origen = [valor, 0, 0] if eje == "x" else [0, valor, 0]
    s = malla.section(plane_origin=origen, plane_normal=normal)
    if s is None:
        return []
    # Lleva los puntos del plano a XY: (y, z) o (x, z), sin girar ni desplazar.
    if eje == "x":
        m = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -valor], [0, 0, 0, 1]], dtype=float)
    else:
        m = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, -valor], [0, 0, 0, 1]], dtype=float)
    plano, _ = s.to_2D(to_2D=m)
    return list(plano.polygons_full)


# -------------------------------------------------------------------- medidas del original

def rayos(malla, origenes, direccion):
    """Para cada origen, coordenadas de todos los impactos ordenados a lo largo del rayo."""
    origenes = np.asarray(origenes, dtype=float)
    d = np.tile(np.asarray(direccion, dtype=float), (len(origenes), 1))
    puntos, indice, _ = malla.ray.intersects_location(origenes, d, multiple_hits=True)
    puntos = np.asarray(puntos, dtype=float).reshape(-1, 3)
    eje = int(np.argmax(np.abs(direccion)))
    signo = np.sign(direccion[eje])
    impactos = []
    for i in range(len(origenes)):
        valores = puntos[indice == i][:, eje]
        impactos.append(sorted(set(np.round(valores, 9)), key=lambda v: signo * v))
    return impactos


def puntos_suelo(cavidad, agujeros, n, margen=1.0):
    """n puntos deterministas sobre el suelo interior, lejos de paredes y agujeros."""
    zona = cavidad.buffer(-margen)
    for a in agujeros:
        zona = zona.difference(Point(a["centro"]).buffer(a["d"] / 2 + margen))
    x0, y0, x1, y1 = zona.bounds
    rng = np.random.default_rng(0)
    puntos = []
    while len(puntos) < n:
        p = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if zona.contains(Point(p)):
            puntos.append(p)
    return puntos


def medir_original(malla, geo, par):
    """Cotas medidas en el STL original (las que el plan pide no dar por supuestas)."""
    v = par["verificacion"]
    z_min, z_max = float(malla.bounds[0][2]), float(malla.bounds[1][2])

    # Agujeros originales del suelo: huecos de la sección a media altura del suelo.
    plato = max(seccion(malla, v["agujero_z"]), key=lambda q: q.area)
    agujeros = []
    for anillo in plato.interiors:
        h = Polygon(anillo)
        agujeros.append({"centro": [h.centroid.x, h.centroid.y], "d": 2 * math.sqrt(h.area / math.pi)})

    # Cavidad: hueco interior de la pared (paredes verticales, igual a cualquier altura).
    pared = max(seccion(malla, (geo["alturas"]["corte_inf"] + z_max) / 2), key=lambda q: q.area)
    cavidad = Polygon(max(pared.interiors, key=lambda a: Polygon(a).area))

    puntos = puntos_suelo(cavidad, agujeros, v["rayos_suelo"])
    arriba = [h[0] for h in rayos(malla, [(x, y, z_max + 5) for x, y in puntos], (0, 0, -1))]
    abajo = [h[0] for h in rayos(malla, [(x, y, z_min - 5) for x, y in puntos], (0, 0, 1))]

    u, a = geo["usb"], geo["alturas"]
    xs = [u["x"] - a["corte_ancho"] / 2, u["x"], u["x"] + a["corte_ancho"] / 2]
    y_lejos = float(malla.bounds[0][1]) - 5
    pared_lobulo = []
    for x in xs:
        for z in v["pared_z"]:
            h = rayos(malla, [(x, y_lejos, z)], (0, 1, 0))[0]
            pared_lobulo.append({"x": x, "z": z, "y_ext": h[0], "y_int": h[1], "grosor": h[1] - h[0]})

    return {
        "z_min": z_min, "z_max": z_max,
        "z_suelo": float(np.median(arriba)), "z_suelo_rayos": [min(arriba), max(arriba)],
        "z_inferior_rayos": [min(abajo), max(abajo)],
        "puntos_suelo": puntos,
        "agujeros": agujeros,
        "cavidad": cavidad,
        "pared_lobulo": pared_lobulo,
    }


def y_exterior(medidas, x):
    """y de la cara exterior del lóbulo en x (media de las alturas medidas)."""
    ys = [p["y_ext"] for p in medidas["pared_lobulo"] if abs(p["x"] - x) < 1e-9]
    return float(np.mean(ys))


# -------------------------------------------------------------------- derivados

def derivados(geo, par, medidas):
    a, u, mec = geo["alturas"], geo["usb"], geo["mecanismo"]
    z_suelo = medidas["z_suelo"]
    pcb_grosor = a["z_pcb_sup"] - a["z_pcb_inf"]
    piloto_prof = par["tornillo_largo"] - pcb_grosor + par["tornillo_margen_punta"]
    z_piloto_fondo = a["z_pcb_inf"] - piloto_prof
    ventana_x = [u["x"] - a["corte_ancho"] / 2, u["x"] + a["corte_ancho"] / 2]
    # La cara exterior del lóbulo es curva: el chaflán toma como plano de referencia
    # la media de su y en las dos jambas y el centro (desviación del plan, ver NOTAS.md).
    xs = [ventana_x[0], u["x"], ventana_x[1]]
    y_ext = {x: y_exterior(medidas, x) for x in xs}
    y_ext_ref = float(np.mean(list(y_ext.values())))
    c = par["ventana_chaflan_ext"]
    y_chaflan_inicio = y_ext_ref + c
    return {
        "z_suelo": z_suelo,
        "pcb_grosor": pcb_grosor,
        "separador_alto": a["z_pcb_inf"] - z_suelo,
        "piloto_prof": piloto_prof,
        "z_piloto_fondo": z_piloto_fondo,
        "suelo_restante": z_piloto_fondo - medidas["z_min"],
        "ventana_x": ventana_x,
        "ventana_z": [z_suelo, a["corte_sup"]],
        "ventana_y": [u["y_pared_int"] + par["ventana_y_dentro"], y_ext[u["x"]] - par["ventana_y_fuera"]],
        "y_ext_ref": y_ext_ref,
        "y_chaflan_inicio": y_chaflan_inicio,
        "chaflan_real": {f"{x:.2f}": (y_chaflan_inicio - y_ext[x] if c > 0 else 0.0) for x in xs},
        "exclusion_d": mec["exclusion_diametro"],
        "funda_ancho": geo["funda"]["ancho"],
        "funda_alto": geo["funda"]["alto"],
        "funda_z": [a["z_centro_usb"] - geo["funda"]["alto"] / 2, a["z_centro_usb"] + geo["funda"]["alto"] / 2],
    }


# -------------------------------------------------------------------- cortadores y añadidos

def cilindro(centro, z0, z1, d, segmentos, d_sup=None):
    r_sup = (d if d_sup is None else d_sup) / 2
    return m3.Manifold.cylinder(z1 - z0, d / 2, r_sup, segmentos).translate([centro[0], centro[1], z0])


def caja(x0, x1, y0, y1, z0, z1):
    return m3.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def perfil_ventana(x0, x1, z0, z1, radio, desplazamiento, segmentos):
    """Perfil XZ de la ventana con las esquinas superiores redondeadas, desplazado
    hacia fuera `desplazamiento` y recortado a z ≥ z0 (el suelo no se toca)."""
    r = radio + desplazamiento
    xa, xb = x0 - desplazamiento, x1 + desplazamiento
    n = max(2, segmentos // 4)
    puntos = [(xa, z0), (xb, z0)]
    for i in range(n + 1):
        t = math.pi / 2 * i / n
        puntos.append((x1 - radio + r * math.cos(t), z1 - radio + r * math.sin(t)))
    for i in range(n + 1):
        t = math.pi / 2 + math.pi / 2 * i / n
        puntos.append((x0 + radio + r * math.cos(t), z1 - radio + r * math.sin(t)))
    return puntos


def prisma_perfiles(perfil_a, y_a, perfil_b, y_b):
    """Envolvente convexa de dos perfiles XZ (convexos) colocados en y_a e y_b."""
    pts = [(x, y_a, z) for x, z in perfil_a] + [(x, y_b, z) for x, z in perfil_b]
    return m3.Manifold.hull_points(np.array(pts, dtype=float))


def operaciones(geo, par, der, desfase_z=0.0):
    """Añadidos y cortadores con sus nombres de feature del plan.

    desfase_z baja la cara inferior de la ventana (respaldo eps_coplanar)."""
    seg = par["segmentos_circulo"]
    a = geo["alturas"]
    z_suelo = der["z_suelo"]
    ops = {}

    for i, t in enumerate(geo["taladros"], start=1):
        ops[f"Separador_H{i}"] = cilindro(t, z_suelo - par["separador_empotrado"], a["z_pcb_inf"],
                                          par["separador_d"], seg)

    x0, x1 = der["ventana_x"]
    z0, z1 = z_suelo - desfase_z, a["corte_sup"]
    nominal = perfil_ventana(x0, x1, z0, z1, par["ventana_radio_sup"], 0.0, seg)
    y_dentro, y_fuera = der["ventana_y"]
    ventana = prisma_perfiles(nominal, y_dentro, nominal, y_fuera)
    c = par["ventana_chaflan_ext"]
    if c > 0:
        f = par["ventana_y_fuera"]
        ancho = perfil_ventana(x0, x1, z0, z1, par["ventana_radio_sup"], c + f, seg)
        ventana = ventana + prisma_perfiles(nominal, der["y_chaflan_inicio"], ancho, der["y_ext_ref"] - f)
    ops["Ventana_USBC"] = ventana

    for i, t in enumerate(geo["taladros"], start=1):
        d, ch = par["piloto_d"], par["piloto_chaflan"]
        z_boca = a["z_pcb_inf"] + 1.0
        piloto = cilindro(t, der["z_piloto_fondo"], z_boca, d, seg)
        # Cono a 45°: el radio crece lo mismo que sube, desde z_pcb_inf − chaflán.
        z_cono = a["z_pcb_inf"] - ch
        piloto = piloto + cilindro(t, z_cono, z_boca, d, seg, d_sup=d + 2 * (z_boca - z_cono))
        ops[f"Piloto_H{i}"] = piloto

    if par["mecanismo_rebaje"] > 0:
        mec = geo["mecanismo"]
        ops["Rebaje_Mecanismo"] = cilindro(mec["centro"], z_suelo - par["mecanismo_rebaje"],
                                           z_suelo + 1.0, der["exclusion_d"], seg)
    return ops


def aplicar(base, ops, tolerancia):
    """Base ∪ separadores − ventana − pilotos − rebaje, en el orden del plan.

    La ventana corta a ras del suelo (caras coplanares) y deja astillas de
    1e-10 mm²; simplify(tolerancia) las colapsa sin mover la geometría."""
    separadores = [s for n, s in ops.items() if n.startswith("Separador_")]
    cortes = [s for n, s in ops.items() if not n.startswith("Separador_")]
    resultado = m3.Manifold.batch_boolean([base, *separadores], m3.OpType.Add)
    for corte in cortes:
        resultado = resultado - corte
    return resultado.simplify(tolerancia)


# -------------------------------------------------------------------- piezas auxiliares

def prueba_lobulo(base_mod, par):
    c = par["prueba_lobulo_caja"]
    return (base_mod ^ caja(*c["x"], *c["y"], *c["z"])).simplify(par["tolerancia_malla"])


def cupon_pilotos(geo, par, der):
    """Placa del grosor del suelo con un separador por cada Ø de piloto.
    El Ø más estrecho va junto a la esquina recortada."""
    seg = par["segmentos_circulo"]
    a = geo["alturas"]
    z_suelo, paso = der["z_suelo"], par["cupon_paso"]
    diametros = sorted(par["cupon_pilotos_d"])
    largo = paso * len(diametros)
    placa = caja(0, largo, 0, paso, 0, z_suelo)
    m = par["cupon_marca"]
    esquina = m3.Manifold.hull_points(np.array(
        [(-1, -1, -1), (m, -1, -1), (-1, m, -1), (-1, -1, z_suelo + 1), (m, -1, z_suelo + 1), (-1, m, z_suelo + 1)],
        dtype=float))
    pieza = placa - esquina
    ch = par["piloto_chaflan"]
    for i, d in enumerate(diametros):
        centro = (paso / 2 + i * paso, paso / 2)
        pieza = pieza + cilindro(centro, z_suelo - par["separador_empotrado"], a["z_pcb_inf"],
                                 par["separador_d"], seg)
        z_boca = a["z_pcb_inf"] + 1.0
        z_cono = a["z_pcb_inf"] - ch
        pieza = pieza - cilindro(centro, der["z_piloto_fondo"], z_boca, d, seg)
        pieza = pieza - cilindro(centro, z_cono, z_boca, d, seg, d_sup=d + 2 * (z_boca - z_cono))
    return pieza.simplify(par["tolerancia_malla"]), diametros


def pcb_fantasma(geo, par, der, partes=False):
    """PCB extruida desde z_pcb_inf, más el cuerpo del USB-C y la funda del cable."""
    seg = par["segmentos_circulo"]
    a = geo["alturas"]
    poligono = contorno_pcb(geo, seg)
    seccion_pcb = m3.CrossSection([np.array(poligono.exterior.coords[:-1])]
                                  + [np.array(i.coords[:-1]) for i in poligono.interiors],
                                  m3.FillRule.EvenOdd)
    pcb = m3.Manifold.extrude(seccion_pcb, der["pcb_grosor"]).translate([0, 0, a["z_pcb_inf"]])
    x0, y0, x1, y1 = caja_usb(geo, par)
    usb = caja(x0, x1, y0, y1, a["carcasa_inf"], a["carcasa_sup"])
    u = geo["usb"]
    funda = caja(u["x"] - der["funda_ancho"] / 2, u["x"] + der["funda_ancho"] / 2,
                 u["y_boca"] - par["funda_largo"], u["y_boca"], *der["funda_z"])
    if partes:
        return {"pcb": pcb, "usb": usb, "funda": funda}
    return m3.Manifold.batch_boolean([pcb, usb, funda], m3.OpType.Add)
