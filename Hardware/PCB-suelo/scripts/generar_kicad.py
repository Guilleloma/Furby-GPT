#!/usr/bin/env python3
"""Genera el proyecto KiCad de la PCB del FurbyGPT con forma de suelo.

Lee geometria.json (lo escribe contorno_suelo.py) y crea en kicad/:
- Furby.pretty con el taladro M2 y el USB-C HRO TYPE-C-31-M-28A,
- el esquema mínimo: USB-C de solo alimentación con 5,1 k en CC1 y CC2,
- la placa: Edge.Cuts (con las muescas de los agujeros de la base, si
  geometria.json las trae), recorte del mecanismo, taladros, USB-C y
  resistencias colocados y rutados, y un plano de GND en la cara inferior.

Se ejecuta con el Python de KiCad, que trae el módulo pcbnew:
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
        scripts/generar_kicad.py
Sobrescribe la placa y el esquema: si ya tienen trabajo a mano, usa --forzar.

Coordenadas: la placa usa las del STL de la base con el eje Y invertido,
x_kicad = x + 220 y y_kicad = -40 - y. El origen auxiliar y el de la rejilla
están en (220; -40), el origen del STL.
"""

import argparse
import json
import re
import uuid
from pathlib import Path

import pcbnew

DIR = Path(__file__).resolve().parent.parent
KICAD_DIR = DIR / "kicad"
PROYECTO = "FurbyGPT-suelo"
LIB = "Furby"
FP_TALADRO = "MountingHole_2.3mm_M2"
FP_USB = "USB_C_Receptacle_HRO_TYPE-C-31-M-28A"
KICAD_SHARE = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport")

ORIGEN = (220.0, -40.0)
UUID_BASE = uuid.UUID("3c9a7e10-52b4-4f0d-9d1e-8a6b2f0c5e01")
BORDE_COBRE_MM = 0.3       # cobre a borde fresado; JLCPCB pide 0,2 como mínimo
PISTA_MM = 0.3
PISTA_VBUS_MM = 0.5
VIA_MM, VIA_TALADRO_MM = 0.6, 0.3


def uuid_estable(nombre):
    return str(uuid.uuid5(UUID_BASE, nombre))


def a_kicad(x, y):
    return ORIGEN[0] + x, ORIGEN[1] - y


def vec(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


# ------------------------------------------------------------- footprints

def footprint_taladro(diametro):
    radio_cabeza = 2.2      # cabeza M2 ISO 7045 (dk = 4,0 mm) con margen
    return f"""(footprint "{FP_TALADRO}"
\t(version 20260206)
\t(generator "generar_kicad")
\t(layer "F.Cu")
\t(descr "Taladro de montaje {diametro} mm para M2, sin cobre (NPTH)")
\t(tags "mountinghole M2 NPTH")
\t(property "Reference" "REF**" (at 0 -3.2 0) (layer "F.SilkS") (hide yes) (effects (font (size 1 1) (thickness 0.15))))
\t(property "Value" "M2" (at 0 3.2 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
\t(attr board_only exclude_from_pos_files exclude_from_bom)
\t(fp_circle (center 0 0) (end {radio_cabeza} 0) (stroke (width 0.15) (type solid)) (fill no) (layer "Cmts.User"))
\t(fp_circle (center 0 0) (end 2.5 0) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))
\t(fp_circle (center 0 0) (end 2.5 0) (stroke (width 0.05) (type solid)) (fill no) (layer "B.CrtYd"))
\t(pad "" np_thru_hole circle (at 0 0) (size {diametro} {diametro}) (drill {diametro}) (layers "*.Cu" "*.Mask"))
)
"""


def footprint_usb():
    """HRO TYPE-C-31-M-28A (LCSC C2848622) en PCB de 1,6 mm.

    Origen en el borde de la PCB y en el eje del conector; la boca mira a +Y
    (hacia fuera de la placa) y sobresale 0,2 mm. Cotas del layout recomendado
    del fabricante, salvo las pads de señal: empiezan 0,3 mm detrás del fondo
    de la ranura (en el dibujo tocan el borde) para respetar la distancia de
    cobre a borde fresado.
    """
    pads_y, pads_largo = -7.55, 1.1
    senales = [("B12", -2.75, 0.9), ("B9", -1.52, 0.8), ("A5", -0.5, 0.7),
               ("B5", 0.5, 0.7), ("A9", 1.52, 0.8), ("A12", 2.75, 0.9)]
    pads = [f'\t(pad "{n}" smd roundrect (at {x} {pads_y}) (size {w} {pads_largo}) '
            f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))' for n, x, w in senales]
    for x in (-5.575, 5.575):
        pads.append(f'\t(pad "SH" thru_hole oval (at {x} -2.6) (size 1.0 2.2) (drill oval 0.5 1.7) '
                    f'(layers "*.Cu" "*.Mask"))')
        pads.append(f'\t(pad "SH" thru_hole oval (at {x} -6.2) (size 1.0 1.8) (drill oval 0.5 1.3) '
                    f'(layers "*.Cu" "*.Mask"))')

    def rect(x0, y0, x1, y1, capa, ancho):
        esquinas = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return "\n".join(
            f'\t(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width {ancho}) (type solid)) '
            f'(layer "{capa}"))' for a, b in zip(esquinas, esquinas[1:] + esquinas[:1]))

    return f"""(footprint "{FP_USB}"
\t(version 20260206)
\t(generator "generar_kicad")
\t(layer "F.Cu")
\t(descr "USB-C 6P solo alimentación, montaje medio en ranura de PCB de 1,6 mm, HRO TYPE-C-31-M-28A (LCSC C2848622). Origen en el borde de la PCB, boca hacia +Y, eje de la boca a ras de la cara superior")
\t(tags "USB C Type-C receptacle power-only 6P mid-mount sinking")
\t(property "Reference" "REF**" (at 0 -9.6 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
\t(property "Value" "USB_C_PowerOnly_6P" (at 0 1.4 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
\t(attr smd)
{rect(-4.47, 0.2, 4.47, -6.6, "F.Fab", 0.1)}
{rect(-6.35, 0.45, 6.35, -8.35, "F.CrtYd", 0.05)}
\t(fp_line (start -6 0) (end 6 0) (stroke (width 0.1) (type dash)) (layer "Dwgs.User"))
\t(fp_text user "borde PCB" (at 0 -0.6 0) (layer "Dwgs.User") (effects (font (size 0.5 0.5) (thickness 0.08))))
\t(fp_text user "ranura 9,24 x 6,70 en Edge.Cuts" (at 0 -3.5 0) (layer "Cmts.User") (effects (font (size 0.5 0.5) (thickness 0.08))))
{chr(10).join(pads)}
)
"""


def escribir_libreria():
    biblioteca = KICAD_DIR / f"{LIB}.pretty"
    biblioteca.mkdir(parents=True, exist_ok=True)
    (biblioteca / f"{FP_TALADRO}.kicad_mod").write_text(footprint_taladro(2.3))
    (biblioteca / f"{FP_USB}.kicad_mod").write_text(footprint_usb())
    # Las librerías de KiCad van en las tablas del proyecto porque las globales
    # de este Mac están vacías; así el proyecto abre igual en cualquier equipo.
    (KICAD_DIR / "fp-lib-table").write_text(
        f'(fp_lib_table\n\t(version 7)\n\t(lib (name "{LIB}") (type "KiCad") '
        f'(uri "${{KIPRJMOD}}/{LIB}.pretty") (options "") (descr "Footprints del FurbyGPT"))\n'
        '\t(lib (name "Resistor_SMD") (type "KiCad") (uri "${KICAD10_FOOTPRINT_DIR}/Resistor_SMD.pretty") '
        '(options "") (descr ""))\n)\n')
    simbolos = "".join(f'\t(lib (name "{n}") (type "KiCad") (uri "${{KICAD10_SYMBOL_DIR}}/{n}.kicad_sym") '
                       f'(options "") (descr ""))\n' for n in ("Connector", "Device", "power"))
    (KICAD_DIR / "sym-lib-table").write_text(f"(sym_lib_table\n\t(version 7)\n{simbolos})\n")
    return biblioteca


# ---------------------------------------------------------------- esquema

def simbolo_de_libreria(fichero, nombre, prefijo):
    """Copia la definición de un símbolo de la librería de KiCad para lib_symbols."""
    lineas = (KICAD_SHARE / "symbols" / fichero).read_text().splitlines()
    inicio = lineas.index(f'\t(symbol "{nombre}"')
    profundidad, bloque = 0, []
    for linea in lineas[inicio:]:
        bloque.append(linea)
        profundidad += linea.count("(") - linea.count(")")
        if profundidad == 0:
            break
    bloque[0] = f'\t\t(symbol "{prefijo}:{nombre}"'
    return "\n".join("\t" + l if i else l for i, l in enumerate(bloque))


SIMBOLOS = {
    "usb": ("Connector.kicad_sym", "USB_C_Receptacle_PowerOnly_6P", "Connector"),
    "r": ("Device.kicad_sym", "R", "Device"),
    "gnd": ("power.kicad_sym", "GND", "power"),
    "vbus": ("power.kicad_sym", "VBUS", "power"),
    "flag": ("power.kicad_sym", "PWR_FLAG", "power"),
}

# Componentes del esquema: referencia, símbolo, posición, valor, footprint, LCSC
USB_SCH = (101.6, 76.2)
COMPONENTES = [
    ("J1", "usb", USB_SCH, "USB_C_PowerOnly_6P", f"{LIB}:{FP_USB}", "C2848622",
     ["A5", "A9", "A12", "B5", "B9", "B12", "SH"]),
    ("R1", "r", (132.08, 91.44), "5k1", "Resistor_SMD:R_0603_1608Metric", "C23186", ["1", "2"]),
    ("R2", "r", (124.46, 91.44), "5k1", "Resistor_SMD:R_0603_1608Metric", "C23186", ["1", "2"]),
]
ALIMENTACION = [
    ("#PWR01", "vbus", (129.54, 68.58), "VBUS"),
    ("#FLG01", "flag", (119.38, 68.58), "PWR_FLAG"),
    ("#PWR02", "gnd", (101.6, 93.98), "GND"),
    ("#FLG02", "flag", (83.82, 93.98), "PWR_FLAG"),
    ("#PWR03", "gnd", (132.08, 95.25), "GND"),
    ("#PWR04", "gnd", (124.46, 95.25), "GND"),
]
CABLES = [
    ((116.84, 68.58), (119.38, 68.58)), ((119.38, 68.58), (129.54, 68.58)),   # VBUS
    ((116.84, 81.28), (132.08, 81.28)), ((132.08, 81.28), (132.08, 87.63)),   # CC1
    ((116.84, 83.82), (124.46, 83.82)), ((124.46, 83.82), (124.46, 87.63)),   # CC2
    ((93.98, 93.98), (101.6, 93.98)), ((83.82, 93.98), (93.98, 93.98)),       # SH y GND
]
ETIQUETAS = [("CC1", (120.65, 81.28)), ("CC2", (120.65, 83.82))]


def propiedad(nombre, valor, x, y, oculta=False, justificar=None):
    extra = " (hide yes)" if oculta else ""
    just = f" (justify {justificar})" if justificar else ""
    return (f'\t\t(property "{nombre}" "{valor}" (at {x} {y} 0){extra} '
            f'(effects (font (size 1.27 1.27)){just}))')


def instancia(referencia, clave, xy, valor, footprint, lcsc, pines, raiz):
    _, nombre, prefijo = SIMBOLOS[clave]
    x, y = xy
    es_power = referencia.startswith("#")
    props = [propiedad("Reference", referencia, x + 2.54, y - 1.27, oculta=es_power, justificar="left"),
             propiedad("Value", valor, x + 2.54, y + 1.27, justificar="left"),
             propiedad("Footprint", footprint, x, y, oculta=True),
             propiedad("Datasheet", "~", x, y, oculta=True)]
    if lcsc:
        props.append(propiedad("LCSC", lcsc, x, y, oculta=True))
    # Valor de los símbolos de alimentación donde lo pone la librería de KiCad
    desplazamiento_valor = {"gnd": 3.81, "vbus": -3.56, "flag": -3.81}
    if clave in desplazamiento_valor:
        props[1] = propiedad("Value", valor, x, y + desplazamiento_valor[clave])
    if clave == "usb":
        props[0] = propiedad("Reference", referencia, x, y - 17.78, justificar="bottom")
        props[1] = propiedad("Value", valor, x, y - 15.24, justificar="bottom")
    pines_txt = "\n".join(f'\t\t(pin "{p}" (uuid "{uuid_estable(referencia + p)}"))' for p in pines)
    return f"""\t(symbol
\t\t(lib_id "{prefijo}:{nombre}")
\t\t(at {x} {y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom {"no" if es_power else "yes"})
\t\t(on_board {"no" if es_power else "yes"})
\t\t(dnp no)
\t\t(uuid "{uuid_estable("sim-" + referencia)}")
{chr(10).join(props)}
{pines_txt}
\t\t(instances (project "{PROYECTO}" (path "/{raiz}" (reference "{referencia}") (unit 1))))
\t)"""


def escribir_esquema():
    raiz = uuid_estable("esquema")
    simbolos = "\n".join(simbolo_de_libreria(*SIMBOLOS[c]) for c in ("usb", "r", "gnd", "vbus", "flag"))
    partes = [instancia(*c, raiz) for c in COMPONENTES]
    for referencia, clave, xy, valor in ALIMENTACION:
        partes.append(instancia(referencia, clave, xy, valor, "", "", ["1"], raiz))
    for k, (a, b) in enumerate(CABLES):
        partes.append(f'\t(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) '
                      f'(stroke (width 0) (type default)) (uuid "{uuid_estable(f"cable-{k}")}"))')
    for texto, (x, y) in ETIQUETAS:
        partes.append(f'\t(label "{texto}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) '
                      f'(justify left bottom)) (uuid "{uuid_estable("etiqueta-" + texto)}"))')
    partes.append(f'\t(text "USB-C solo alimentación (5 V). Rd = 5,1 k en CC1 y CC2: el cargador '
                  f'entrega 5 V como sumidero por defecto." (exclude_from_sim no) (at 88.9 106.68 0) '
                  f'(effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uuid_estable("nota")}"))')
    esquema = f"""(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{raiz}")
\t(paper "A4")
\t(title_block (title "FurbyGPT · PCB con forma de suelo") (rev "0.1") (comment 1 "Esquema mínimo: entrada USB-C de 5 V"))
\t(lib_symbols
{simbolos}
\t)
{chr(10).join(partes)}
\t(sheet_instances (path "/" (page "1")))
\t(embedded_fonts no)
)
"""
    (KICAD_DIR / f"{PROYECTO}.kicad_sch").write_text(esquema)
    return raiz


# ------------------------------------------------------------------ placa

def borde(placa, geometria):
    for k, p in enumerate(geometria["contorno"]):
        forma = pcbnew.PCB_SHAPE(placa)
        forma.SetLayer(pcbnew.Edge_Cuts)
        forma.SetWidth(pcbnew.FromMM(0.1))
        if p["tipo"] == "linea":
            forma.SetShape(pcbnew.SHAPE_T_SEGMENT)
            forma.SetStart(vec(*a_kicad(*p["inicio"])))
            forma.SetEnd(vec(*a_kicad(*p["fin"])))
        else:
            forma.SetShape(pcbnew.SHAPE_T_ARC)
            forma.SetArcGeometry(vec(*a_kicad(*p["inicio"])), vec(*a_kicad(*p["medio"])),
                                 vec(*a_kicad(*p["fin"])))
        placa.Add(forma)
    mecanismo = geometria["mecanismo"]
    circulo = pcbnew.PCB_SHAPE(placa)
    circulo.SetShape(pcbnew.SHAPE_T_CIRCLE)
    circulo.SetLayer(pcbnew.Edge_Cuts)
    circulo.SetWidth(pcbnew.FromMM(0.1))
    cx, cy = a_kicad(*mecanismo["centro"])
    circulo.SetCenter(vec(cx, cy))
    circulo.SetEnd(vec(cx + mecanismo["diametro"] / 2, cy))
    placa.Add(circulo)
    # Con muescas, torreta supuesta del cuerpo en cada agujero original del
    # suelo, como referencia: la muesca del contorno ya deja su holgura.
    muescas = geometria.get("muescas") or {"centros": []}
    for centro in muescas["centros"]:
        torreta = pcbnew.PCB_SHAPE(placa)
        torreta.SetShape(pcbnew.SHAPE_T_CIRCLE)
        torreta.SetLayer(pcbnew.Cmts_User)
        torreta.SetWidth(pcbnew.FromMM(0.1))
        tx, ty = a_kicad(*centro)
        torreta.SetCenter(vec(tx, ty))
        torreta.SetEnd(vec(tx + muescas["torreta_diametro"] / 2, ty))
        placa.Add(torreta)


def red(placa, nombre):
    existente = placa.FindNet(nombre)
    if existente:
        return existente
    nueva = pcbnew.NETINFO_ITEM(placa, nombre)
    placa.Add(nueva)
    return nueva


def colocar(placa, biblioteca, nombre, referencia, valor, x, y, rotacion=0.0, ruta=None, lcsc=None):
    fp = pcbnew.FootprintLoad(str(biblioteca), nombre)
    fp.SetReference(referencia)
    fp.SetValue(valor)
    fp.SetPosition(vec(x, y))
    fp.SetOrientationDegrees(rotacion)
    if ruta:
        fp.SetPath(pcbnew.KIID_PATH(f"/{ruta}"))
    if lcsc:
        fp.SetField("LCSC", lcsc)
        fp.GetField("LCSC").SetVisible(False)
    placa.Add(fp)
    return fp


def pista(placa, a, b, red_, capa=pcbnew.F_Cu, ancho=PISTA_MM):
    t = pcbnew.PCB_TRACK(placa)
    t.SetStart(vec(*a))
    t.SetEnd(vec(*b))
    t.SetWidth(pcbnew.FromMM(ancho))
    t.SetLayer(capa)
    t.SetNet(red_)
    placa.Add(t)


def via(placa, xy, red_):
    v = pcbnew.PCB_VIA(placa)
    v.SetPosition(vec(*xy))
    v.SetWidth(pcbnew.FromMM(VIA_MM))
    v.SetDrill(pcbnew.FromMM(VIA_TALADRO_MM))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(red_)
    placa.Add(v)


def plano_gnd(placa, gnd, geometria):
    xs = [c for p in geometria["contorno"] for c in (p["inicio"][0], p["fin"][0])]
    ys = [c for p in geometria["contorno"] for c in (p["inicio"][1], p["fin"][1])]
    x0, y0 = a_kicad(min(xs) - 1, max(ys) + 1)
    x1, y1 = a_kicad(max(xs) + 1, min(ys) - 1)
    zona = pcbnew.ZONE(placa)
    zona.SetLayer(pcbnew.B_Cu)
    zona.SetNet(gnd)
    zona.SetZoneName("GND inferior")
    zona.SetLocalClearance(pcbnew.FromMM(0.3))
    zona.SetMinThickness(pcbnew.FromMM(0.25))
    zona.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    contorno = zona.Outline()
    contorno.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        contorno.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    placa.Add(zona)


def rellenar_zonas(ruta_placa):
    """Rellena las zonas sobre la placa ya guardada y la vuelve a guardar.

    Es el último paso. Rellenar la placa recién creada en memoria no recorta
    los taladros NPTH ni el agujero del mecanismo (el contorno de la placa y
    la conectividad no están construidos todavía) y el DRC sin
    --refill-zones da errores de hole_clearance y copper_edge_clearance.
    Al cargarla desde el fichero, KiCad lo construye todo.
    """
    placa = pcbnew.LoadBoard(str(ruta_placa))
    placa.BuildConnectivity()
    pcbnew.ZONE_FILLER(placa).Fill(placa.Zones())
    pcbnew.SaveBoard(str(ruta_placa), placa)


def escribir_placa(geometria, biblioteca, raiz_esquema):
    ruta_placa = KICAD_DIR / f"{PROYECTO}.kicad_pcb"
    placa = pcbnew.NewBoard(str(ruta_placa))
    placa.SetCopperLayerCount(2)
    ajustes = placa.GetDesignSettings()
    ajustes.m_CopperEdgeClearance = pcbnew.FromMM(BORDE_COBRE_MM)
    ajustes.SetAuxOrigin(vec(*ORIGEN))
    ajustes.SetGridOrigin(vec(*ORIGEN))
    ajustes.SetBoardThickness(pcbnew.FromMM(geometria["alturas"]["z_pcb_sup"]
                                            - geometria["alturas"]["z_pcb_inf"]))
    borde(placa, geometria)

    for k, (x, y) in enumerate(geometria["taladros"], start=1):
        colocar(placa, biblioteca, FP_TALADRO, f"H{k}", "M2", *a_kicad(x, y))

    vbus, gnd = red(placa, "VBUS"), red(placa, "GND")
    cc1, cc2 = red(placa, "/CC1"), red(placa, "/CC2")
    usb = geometria["usb"]
    ux, uy = a_kicad(usb["x"], usb["y_borde"])
    rutas = {ref: uuid_estable("sim-" + ref) for ref in ("J1", "R1", "R2")}
    j1 = colocar(placa, biblioteca, FP_USB, "J1", "USB_C_PowerOnly_6P", ux, uy, ruta=rutas["J1"],
                 lcsc="C2848622")
    j1.SetFPID(pcbnew.LIB_ID(LIB, FP_USB))
    redes_usb = {"A5": cc1, "B5": cc2, "A9": vbus, "B9": vbus, "A12": gnd, "B12": gnd, "SH": gnd}
    for pad in j1.Pads():
        pad.SetNet(redes_usb[pad.GetNumber()])

    resistencias = KICAD_SHARE / "footprints" / "Resistor_SMD.pretty"
    r1 = colocar(placa, resistencias, "R_0603_1608Metric", "R1", "5k1", ux - 1.6, uy - 12.4,
                 ruta=rutas["R1"], lcsc="C23186")
    r2 = colocar(placa, resistencias, "R_0603_1608Metric", "R2", "5k1", ux + 1.6, uy - 12.4, 180,
                 ruta=rutas["R2"], lcsc="C23186")
    for fp, cc in ((r1, cc1), (r2, cc2)):
        fp.SetFPID(pcbnew.LIB_ID("Resistor_SMD", "R_0603_1608Metric"))
        for pad in fp.Pads():
            pad.SetNet(cc if pad.GetNumber() == "1" else gnd)

    def local(x, y):
        return ux + x, uy + y

    # Referencias de serigrafía fuera de pistas y vías
    for fp, xy in ((j1, local(0, -17.0)), (r1, local(-4.3, -12.4)), (r2, local(4.3, -12.4))):
        fp.Reference().SetPosition(vec(*xy))
        fp.Reference().SetTextAngleDegrees(0)

    # VBUS: une A9 y B9 por detrás de las pads, rodeando CC1 y CC2.
    for a, b in ((local(1.52, -7.55), local(1.52, -9.6)), (local(1.52, -9.6), local(-1.52, -9.6)),
                 (local(-1.52, -9.6), local(-1.52, -7.55))):
        pista(placa, a, b, vbus, ancho=PISTA_VBUS_MM)
    # CC1 y CC2: bajan a B.Cu bajo la pista de VBUS y suben junto a su resistencia.
    for signo, cc in ((-1, cc1), (1, cc2)):
        pad, via_pad = local(signo * 0.5, -7.55), local(signo * 0.5, -8.7)
        via_r, pad_r = local(signo * 2.425, -10.6), local(signo * 2.425, -12.4)
        pista(placa, pad, via_pad, cc)
        via(placa, via_pad, cc)
        pista(placa, via_pad, via_r, cc, capa=pcbnew.B_Cu)
        via(placa, via_r, cc)
        pista(placa, via_r, pad_r, cc)
    # GND: pads de GND del USB-C y de las resistencias, al plano inferior.
    for signo in (-1, 1):
        pista(placa, local(signo * 2.75, -7.55), local(signo * 2.75, -8.75), gnd)
        via(placa, local(signo * 2.75, -8.75), gnd)
    pista(placa, local(-0.775, -12.4), local(0.775, -12.4), gnd)
    via(placa, local(0, -13.3), gnd)
    pista(placa, local(0, -12.4), local(0, -13.3), gnd)

    texto = pcbnew.PCB_TEXT(placa)
    texto.SetText("FurbyGPT · suelo r0.1")
    texto.SetLayer(pcbnew.F_SilkS)
    texto.SetPosition(vec(*a_kicad(-73.5, -60.0)))
    texto.SetTextSize(vec(1.2, 1.2))
    texto.SetTextThickness(pcbnew.FromMM(0.18))
    placa.Add(texto)
    texto_usb = pcbnew.PCB_TEXT(placa)
    texto_usb.SetText("5V USB-C")
    texto_usb.SetLayer(pcbnew.F_SilkS)
    texto_usb.SetPosition(vec(*local(0, -15.2)))
    texto_usb.SetTextSize(vec(1.0, 1.0))
    texto_usb.SetTextThickness(pcbnew.FromMM(0.15))
    placa.Add(texto_usb)

    plano_gnd(placa, gnd, geometria)
    pcbnew.SaveBoard(str(ruta_placa), placa)
    rellenar_zonas(ruta_placa)
    return ruta_placa


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--forzar", action="store_true", help="sobrescribe placa y esquema existentes")
    args = parser.parse_args()
    geometria = json.loads((DIR / "geometria.json").read_text())
    KICAD_DIR.mkdir(exist_ok=True)
    existentes = [p for p in (KICAD_DIR / f"{PROYECTO}.kicad_pcb", KICAD_DIR / f"{PROYECTO}.kicad_sch")
                  if p.exists()]
    if existentes and not args.forzar:
        raise SystemExit(f"Ya existe {existentes[0].name}: usa --forzar para regenerarlo")
    biblioteca = escribir_libreria()
    raiz = escribir_esquema()
    ruta = escribir_placa(geometria, biblioteca, raiz)
    print(f"Escrito {ruta.relative_to(DIR)} y {PROYECTO}.kicad_sch")


if __name__ == "__main__":
    main()
