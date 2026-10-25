#!/usr/bin/env python3
"""Genera FurbyBoard.kicad_pcb: contorno, colocación, zonas, reglas y serigrafía.

Se ejecuta con el Python de KiCad:
    $KICAD_PY scripts/gen_pcb.py [--sin-rutado]

- Contorno, taladros y agujero del mecanismo: Hardware/PCB-suelo/geometria.json.
- Colocación: scripts/layout.py (coordenadas del STL).
- Redes: scripts/design.py. Las huellas se enlazan con los símbolos por UUID
  (paridad esquemático↔PCB).
- Rutado: lo crítico va escrito en scripts/rutas_fijas.py (bloqueado); con --ses <fichero>
  se importa además el resultado de Freerouting sobre esas rutas; con --sin-rutado el PCB
  queda colocado y sin rutar (puerta C).
- Serigrafía: nombre y versión, logo y rótulos colocados solos tras el rutado (scripts/serigrafia.py).
- Planos (6 capas, params.STACKUP): GND en In1 (L2) e In4 (L5) enteros; In2 (L3) es capa de señal
  con relleno de VSYS; In3 (L4) señal; relleno de GND en F.Cu y B.Cu tras el rutado.
- Áreas de reglas: sin cobre bajo la antena (todas las capas) y sin vías ni pads
  pasantes bajo el logo de la cara inferior.
"""
import json
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D  # noqa: E402
import gen_sch  # noqa: E402
import layout as LAY  # noqa: E402
import params as P  # noqa: E402
import rutas_fijas as RF  # noqa: E402
import serigrafia as SG  # noqa: E402

GEO = json.load(open(P.GEOMETRIA, encoding="utf-8"))


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    """Punto del STL a KiCad."""
    return pcbnew.VECTOR2I(mm(x + P.STL_OX), mm(P.STL_OY - y))


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = P.FP_LIB if lib == "FurbyBoard" else os.path.join(P.KICAD_FP_DIR, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError("huella no encontrada: " + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def shape(board, layer, kind, **kw):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(kind)
    s.SetLayer(layer)
    s.SetWidth(mm(kw.get("width", 0.1)))
    if kind == pcbnew.SHAPE_T_SEGMENT:
        s.SetStart(pt(*kw["a"]))
        s.SetEnd(pt(*kw["b"]))
    elif kind == pcbnew.SHAPE_T_ARC:
        s.SetArcGeometry(pt(*kw["a"]), pt(*kw["m"]), pt(*kw["b"]))
    elif kind == pcbnew.SHAPE_T_CIRCLE:
        s.SetCenter(pt(*kw["c"]))
        s.SetEnd(pt(kw["c"][0] + kw["r"], kw["c"][1]))
    board.Add(s)
    return s


def outline(board):
    for p in GEO["contorno"]:
        if p["tipo"] == "linea":
            shape(board, pcbnew.Edge_Cuts, pcbnew.SHAPE_T_SEGMENT, a=p["inicio"], b=p["fin"])
        else:
            shape(board, pcbnew.Edge_Cuts, pcbnew.SHAPE_T_ARC, a=p["inicio"], m=p["medio"], b=p["fin"])
    mec = GEO["mecanismo"]
    shape(board, pcbnew.Edge_Cuts, pcbnew.SHAPE_T_CIRCLE, c=mec["centro"], r=mec["diametro"] / 2)
    shape(board, pcbnew.Cmts_User, pcbnew.SHAPE_T_CIRCLE, c=mec["centro"], r=mec["exclusion_diametro"] / 2,
          width=0.08)


def text(board, layer, txt, x, y, size=1.0, thick=0.15, mirror=False, angle=0, just="center"):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(pt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(thick))
    t.SetMirrored(mirror)
    if angle:
        t.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    t.SetHorizJustify({"left": pcbnew.GR_TEXT_H_ALIGN_LEFT, "right": pcbnew.GR_TEXT_H_ALIGN_RIGHT,
                       "center": pcbnew.GR_TEXT_H_ALIGN_CENTER}[just])
    board.Add(t)
    return t


def setup_board(board):
    ds = board.GetDesignSettings()
    board.SetCopperLayerCount(P.COPPER_LAYERS)
    ds.SetCopperLayerCount(P.COPPER_LAYERS)
    ds.SetBoardThickness(mm(P.BOARD_THICKNESS))
    ds.m_MinClearance = mm(P.RULE_CLEARANCE)
    ds.m_TrackMinWidth = mm(P.RULE_TRACK_MIN)
    ds.m_ViasMinSize = mm(0.5)
    ds.m_MinThroughDrill = mm(P.RULE_VIA_DRILL)
    ds.m_CopperEdgeClearance = mm(P.RULE_EDGE_CLEARANCE)
    ds.m_HoleClearance = mm(0.2)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_ViasMinAnnularWidth = mm(0.13)
    # Origen de taladros y de posiciones = origen del STL (lección de la Game Boy:
    # Gerber y CPL con el mismo origen)
    ds.SetAuxOrigin(pt(0, 0))
    ds.SetGridOrigin(pt(0, 0))


def place(board, netmap):
    parts = {p["ref"]: p for p in D.parts()}
    lay = LAY.placement()
    caras = LAY.caras()
    faltan = sorted(set(parts) - set(lay))
    sobran = sorted(set(lay) - set(parts))
    if faltan or sobran:
        raise SystemExit("Sin colocar: %s; sin pieza: %s" % (", ".join(faltan), ", ".join(sobran)))
    for ref, part in parts.items():
        x, y, rot = lay[ref]
        fp = load_fp(part["footprint"])
        fp.SetReference(ref)
        fp.SetValue(part["value"])
        fp.SetPath(pcbnew.KIID_PATH("/%s/%s" % (gen_sch.sheet_uuid(part["sheet"]), gen_sch.suuid("sym", ref))))
        fp.SetSheetname(dict(D.SHEETS)[part["sheet"]])
        fp.SetSheetfile("hojas/%s.kicad_sch" % part["sheet"])
        for key in ("LCSC", "JLC_Class", "MPN"):
            val = {"LCSC": part["lcsc"], "JLC_Class": part["jlc"], "MPN": part["mpn"]}[key]
            f = pcbnew.PCB_FIELD(fp, pcbnew.FIELD_T_USER, key)
            f.SetText(val)
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab)
            fp.Add(f)
        fp.SetField("Description", part.get("desc", ""))
        board.Add(fp)
        fp.SetPosition(pt(x, y))
        if caras[ref] == "B":
            # Puntos de test en la cara inferior, sobre una vía de su red junto a la fuente.
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        fp.SetDNP(bool(part["dnp"]))
        fp.SetExcludedFromBOM(not part["in_bom"])
        fp.SetExcludedFromPosFiles(not part["in_pos"])
        # Las vías de 0,2 mm que traen dentro de los pads las huellas de KiCad (pad central del
        # módulo, SW del TPS61089) serían vía en pad sin rellenar: el estaño se escaparía por ellas
        # y JLCPCB no taladra por debajo de 0,3 mm sin coste extra. Se quitan; GND se cose con vías
        # alrededor y el nodo SW no debe bajar a capas internas.
        for pad in list(fp.Pads()):
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and pad.GetDrillSizeX() < mm(P.RULE_VIA_DRILL):
                fp.Remove(pad)
        nombres = gen_sch.pin_names(part["lib_id"])
        for pad in fp.Pads():
            num = pad.GetNumber()
            net = part["pins"].get(num, "")
            if net:
                pad.SetNet(netmap[net])
            elif num in nombres:
                nc = "unconnected-(%s-%s-Pad%s)" % (ref, nombres[num], num)
                if nc not in netmap:
                    netmap[nc] = pcbnew.NETINFO_ITEM(board, nc)
                    board.Add(netmap[nc])
                pad.SetNet(netmap[nc])
        fp.Reference().SetLayer(pcbnew.B_Fab if caras[ref] == "B" else pcbnew.F_Fab)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.5), mm(0.5)))
        fp.Reference().SetTextThickness(mm(0.08))
        fp.Reference().SetPosition(fp.GetPosition())
        fp.Value().SetVisible(False)


def mechanical(board):
    for i, (x, y) in enumerate(GEO["taladros"], start=1):
        fp = load_fp("FurbyBoard:MountingHole_2.3mm_M2")
        fp.SetReference("H%d" % i)
        board.Add(fp)
        fp.SetPosition(pt(x, y))
    fp = load_fp("FurbyBoard:Logo_Furby_PixelArt")
    fp.SetReference("LOGO1")
    board.Add(fp)
    lx, ly = LAY.LOGO_INFERIOR["x"], LAY.LOGO_INFERIOR["y"]
    fp.SetPosition(pt((lx[0] + lx[1]) / 2, (ly[0] + ly[1]) / 2 + 0.4))
    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for x, y, nombre in LAY.CALZOS:
        shape(board, pcbnew.Cmts_User, pcbnew.SHAPE_T_CIRCLE, c=(x, y), r=LAY.CALZO_D / 2, width=0.1)
        text(board, pcbnew.Cmts_User, "calzo " + nombre, x, y, 0.6, 0.08)


def poly_zone(board, layers, pts_stl, net=None, rule=None, priority=0, clearance=0.25):
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    if rule:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks("tracks" in rule)
        z.SetDoNotAllowVias("vias" in rule)
        z.SetDoNotAllowPads("pads" in rule)
        z.SetDoNotAllowZoneFills("fills" in rule)
        z.SetDoNotAllowFootprints("footprints" in rule)
    else:
        z.SetNet(net)
        z.SetLocalClearance(mm(clearance))
        z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.35))
        z.SetAssignedPriority(priority)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts_stl:
        p = pt(x, y)
        ol.Append(p.x, p.y)
    board.Add(z)
    return z


def caja(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def zones(board, netmap, exteriores):
    """Planos de GND en In1 e In4 y relleno de VSYS en lo que dejen libre las señales de In2.
    Rellenos de GND en F.Cu y B.Cu solo con el rutado hecho."""
    cu = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
    c = GEO["resultado"]["caja"]
    todo = caja(c[0] - 1, c[2] + 1, c[1] - 1, c[3] + 1)
    poly_zone(board, [pcbnew.In1_Cu], todo, net=netmap["GND"])
    poly_zone(board, [pcbnew.In4_Cu], todo, net=netmap["GND"])
    poly_zone(board, [pcbnew.In2_Cu], todo, net=netmap["VSYS"])
    if exteriores:
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            poly_zone(board, [layer], todo, net=netmap["GND"])
    a = LAY.ANTENA_SIN_COBRE
    poly_zone(board, cu, caja(a["x"][0], a["x"][1], a["y"][0], a["y"][1] + 5), rule=("tracks", "vias", "pads", "fills"))
    lg = LAY.LOGO_INFERIOR
    poly_zone(board, [pcbnew.B_Cu], caja(lg["x"][0], lg["x"][1], lg["y"][0], lg["y"][1]), rule=("vias", "pads"))
    # Cabeza del tornillo M2: sin cobre ni piezas en las dos caras exteriores (layout-pcb.md 4.1).
    r = LAY.TORNILLO_KEEPOUT_D / 2
    for x, y in GEO["taladros"]:
        circulo = [(x + r * math.cos(2 * math.pi * k / 24), y + r * math.sin(2 * math.pi * k / 24)) for k in range(24)]
        # Solo cobre: las piezas las aparta el patio de Ø5 de la propia huella del taladro.
        poly_zone(board, [pcbnew.F_Cu, pcbnew.B_Cu], circulo, rule=("tracks", "vias", "fills"))
    # Franja del flex de la cámara hasta la pared: sin piezas (pistas y vías sí). Va como dibujo en
    # Cmts.User y la vigila comprobar_colocacion.py (como área de reglas, KiCad la cruza con el
    # propio J6 por su serigrafía).
    fl = LAY.FLEX_SIN_PIEZAS
    for a, b in (((fl["x"][0], fl["y"][0]), (fl["x"][1], fl["y"][0])), ((fl["x"][1], fl["y"][0]), (fl["x"][1], fl["y"][1])),
                 ((fl["x"][1], fl["y"][1]), (fl["x"][0], fl["y"][1])), ((fl["x"][0], fl["y"][1]), (fl["x"][0], fl["y"][0]))):
        shape(board, pcbnew.Cmts_User, pcbnew.SHAPE_T_SEGMENT, a=a, b=b, width=0.1)
    text(board, pcbnew.Cmts_User, "flex", (fl["x"][0] + fl["x"][1]) / 2, (fl["y"][0] + fl["y"][1]) / 2, 0.8, 0.1)


def silk_abajo(board, abajo):
    """Nombre, versión y recuadro para numerar la placa, junto al logo y sin pisar vías."""
    B = pcbnew.B_SilkS
    lx, ly = LAY.LOGO_INFERIOR["x"], LAY.LOGO_INFERIOR["y"]
    lineas = [("FurbyBoard", 1.2), ("%s · %s" % (P.BOARD_REV, P.BOARD_DATE), SG.TEXTO)]
    medidas = [medir(board, "B", t, a) for t, a in lineas]
    w, h = max(m[0] for m in medidas), sum(m[1] for m in medidas) + 0.3
    xy = abajo.busca("nombre y versión", lx[1] + 6.0, -105.75, w, h, radio=20.0)
    if xy:
        y = xy[1] + h / 2
        for (t, a), (_, hl) in zip(lineas, medidas):
            rotulo(board, "B", t, (xy[0], y - hl / 2), a)
            y -= hl + 0.3
    # Recuadro en blanco para numerar la placa a rotulador (TEST-PLAN.md), con su título encima;
    # dentro no puede haber vías (se escribe encima y la serigrafía no se recortaría).
    bw, bh = 7.0, 3.5
    tw, th = medir(board, "B", "PLACA", SG.TEXTO)
    xy = abajo.busca("recuadro PLACA", lx[1] + 5.5, -114.0, bw, bh + th + 0.3, radio=20.0)
    if xy:
        x0, x1 = xy[0] - bw / 2, xy[0] + bw / 2
        y0 = xy[1] - (bh + th + 0.3) / 2
        y1 = y0 + bh
        for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            shape(board, B, pcbnew.SHAPE_T_SEGMENT, a=a, b=b, width=SG.GROSOR)
        rotulo(board, "B", "PLACA", (xy[0], y1 + 0.3 + th / 2))


def contorno_muestreado(paso=0.5):
    """Contorno de la PCB como polilínea (coordenadas del STL)."""
    puntos = []
    for p in GEO["contorno"]:
        a = p["inicio"]
        if p["tipo"] == "linea":
            puntos.append(tuple(a))
            continue
        c, r = p["centro"], p["radio"]
        t0 = math.atan2(a[1] - c[1], a[0] - c[0])
        tm = math.atan2(p["medio"][1] - c[1], p["medio"][0] - c[0])
        t1 = math.atan2(p["fin"][1] - c[1], p["fin"][0] - c[0])
        barrido = (t1 - t0) % (2 * math.pi)
        if (tm - t0) % (2 * math.pi) > barrido:
            barrido -= 2 * math.pi
        n = max(2, int(abs(barrido) * r / paso))
        puntos += [(c[0] + r * math.cos(t0 + barrido * k / n), c[1] + r * math.sin(t0 + barrido * k / n))
                   for k in range(n)]
    return puntos


def caja_stl(bb):
    return SG.Caja(pcbnew.ToMM(bb.GetLeft()) - P.STL_OX, P.STL_OY - pcbnew.ToMM(bb.GetBottom()),
                   pcbnew.ToMM(bb.GetRight()) - P.STL_OX, P.STL_OY - pcbnew.ToMM(bb.GetTop()))


def colocador(board, cara):
    """Obstáculos para rotular una cara: pads, vías, pistas, serigrafía y cuerpos de las piezas montadas."""
    silk_capa = pcbnew.F_SilkS if cara == "F" else pcbnew.B_SilkS
    cu = pcbnew.F_Cu if cara == "F" else pcbnew.B_Cu
    montadas = {p["ref"] for p in D.parts() if p["in_pos"]}
    pads, silk, cuerpos = [], [], []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.IsOnLayer(cu) or pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                pads.append(caja_stl(pad.GetBoundingBox()))
        for g in fp.GraphicalItems():
            if g.GetLayer() == silk_capa:
                silk.append(caja_stl(g.GetBoundingBox()))
        if cara == "F" and fp.GetReference() in montadas:
            # El cuerpo es el contorno de F.Fab (el courtyard lleva margen y, en el módulo,
            # toda la zona de la antena)
            fab = [caja_stl(g.GetBoundingBox()) for g in fp.GraphicalItems()
                   if g.GetLayer() == pcbnew.F_Fab and g.GetClass() != "PCB_TEXT"]
            if fab:
                cuerpos.append((fp.GetReference(), SG.Caja(min(c.x0 for c in fab), min(c.y0 for c in fab),
                                                           max(c.x1 for c in fab), max(c.y1 for c in fab))))
    for d in board.GetDrawings():
        if d.GetLayer() == silk_capa:
            silk.append(caja_stl(d.GetBoundingBox()))
    # Las vías son pasantes: obstáculo en las dos caras. Las pistas, solo en la suya.
    vias, pistas = [], []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            x, y = pcbnew.ToMM(t.GetPosition().x) - P.STL_OX, P.STL_OY - pcbnew.ToMM(t.GetPosition().y)
            vias.append((x, y, pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2))
        elif t.GetLayer() == cu:
            a, b = t.GetStart(), t.GetEnd()
            pistas.append((pcbnew.ToMM(a.x) - P.STL_OX, P.STL_OY - pcbnew.ToMM(a.y),
                           pcbnew.ToMM(b.x) - P.STL_OX, P.STL_OY - pcbnew.ToMM(b.y), pcbnew.ToMM(t.GetWidth()) / 2))
    mec = GEO["mecanismo"]
    circulos = [(mec["centro"][0], mec["centro"][1], mec["exclusion_diametro"] / 2)]
    circulos += [(x, y, GEO["taladro_diametro"] / 2 + 0.8) for x, y in GEO["taladros"]]
    return SG.Colocador(contorno_muestreado(), circulos, pads, silk, cuerpos, vias, pistas)


TINTA = {}   # (cara, texto, alto) -> desplazamiento del centro de la tinta respecto al punto del texto


def medir(board, cara, txt, alto):
    """Ancho y alto de la tinta del texto (la caja de KiCad lleva el interlineado: 1,7 mm de alto
    para letras de 1,0). Guarda dónde cae el centro de la tinta para colocarlo luego con precisión."""
    t = text(board, pcbnew.F_SilkS if cara == "F" else pcbnew.B_SilkS, txt, 0, 0, alto, SG.GROSOR,
             mirror=(cara == "B"))
    bb = t.GetEffectiveTextShape().BBox()
    c = bb.GetCenter()
    TINTA[(cara, txt, alto)] = (pcbnew.ToMM(c.x) - P.STL_OX, P.STL_OY - pcbnew.ToMM(c.y))
    board.Remove(t)
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())


def medida(board, cara, txt, alto=SG.TEXTO):
    return SG.Medida(lambda a: medir(board, cara, txt, a), alto)


def rotulo(board, cara, txt, xy, alto=SG.TEXTO):
    """Texto con el centro de su tinta en xy (medido antes con medir())."""
    if (cara, txt, alto) not in TINTA:
        medir(board, cara, txt, alto)
    ox, oy = TINTA[(cara, txt, alto)]
    return text(board, pcbnew.F_SilkS if cara == "F" else pcbnew.B_SilkS, txt, xy[0] - ox, xy[1] - oy,
                alto, SG.GROSOR, mirror=(cara == "B"))


def caja_pads(fp, numeros=None, silk=None):
    """Caja de los pads (o de algunos) más, si se pide, la serigrafía propia de la pieza."""
    cajas = [caja_stl(p.GetBoundingBox()) for p in fp.Pads() if numeros is None or p.GetNumber() in numeros]
    if silk is not None:
        cajas += [caja_stl(g.GetBoundingBox()) for g in fp.GraphicalItems() if g.GetLayer() == silk]
    return SG.Caja(min(c.x0 for c in cajas), min(c.y0 for c in cajas), max(c.x1 for c in cajas), max(c.y1 for c in cajas))


def celdas_leyenda(board, _ref, etiquetas, alto, sep, lado, caja, xy, xs):
    """Celdas de una leyenda con la disposición de los pads: mismas filas que los pads y columnas
    separadas por el rótulo más ancho, a la derecha (R) o a la izquierda (L) de la caja."""
    med = {n: medir(board, "B", t, alto) for n, t in etiquetas.items()}
    w_max = max(w for w, _ in med.values())
    paso = w_max + sep
    celdas = {}
    for n in etiquetas:
        col = xs.index(round(xy[n][0], 2))
        k = len(xs) - 1 - col if lado == "L" else col
        x = caja.x0 - SG.HUECO - w_max / 2 - k * paso if lado == "L" else caja.x1 + SG.HUECO + w_max / 2 + k * paso
        celdas[n] = SG.centrada(x, xy[n][1], *med[n])
    return celdas


def leyenda_al_lado(board, abajo, etiquetas, alto, sep, lado, caja, xy, xs, ys):
    """Celdas de la leyenda junto a los pads. Primero toda con el mismo desplazamiento (columnas
    alineadas); si no cabe, fila a fila. Cada fila puede subir o bajar ≤ 0,6 mm y se reserva
    entera (ningún otro rótulo se mete entre sus celdas). Devuelve (celdas puestas, reservas,
    pads sin sitio); no deja nada reservado si falta alguna fila."""
    signo = -1 if lado == "L" else 1
    dys = (0, 0.15, -0.15, 0.3, -0.3, 0.45, -0.45, 0.6, -0.6)
    dxs = [k * 0.25 for k in range(int(SG.DESPLAZA_MAX / 0.25) + 1)]
    celdas = celdas_leyenda(board, None, etiquetas, alto, sep, lado, caja, xy, xs)
    filas = [{n: c for n, c in celdas.items() if round(xy[n][1], 2) == y} for y in ys]

    def prueba(fila, dx, dy):
        movidas = {n: c.mueve(signo * dx, dy) for n, c in fila.items()}
        if not all(abajo.libre(c) for c in movidas.values()):
            return None
        # La reserva va del borde de los pads a la última celda: nada se mete entre ellos
        x0 = min([c.x0 for c in movidas.values()] + ([caja.x1] if lado == "R" else []))
        x1 = max([c.x1 for c in movidas.values()] + ([caja.x0] if lado == "L" else []))
        return movidas, SG.Caja(x0, min(c.y0 for c in movidas.values()), x1, max(c.y1 for c in movidas.values()))

    def suelta(reservas):
        for r in reservas:
            abajo.rotulos.remove(r)

    for dx in dxs:
        puestas, reservas = [], []
        for fila in filas:
            r = next((r for r in (prueba(fila, dx, dy) for dy in dys) if r), None)
            if r is None:
                break
            puestas += list(r[0].items())
            reservas.append(r[1])
            abajo.rotulos.append(r[1])
        if len(reservas) == len(filas):
            return puestas, reservas, []
        suelta(reservas)
    puestas, reservas, sin_sitio = [], [], []
    for fila in filas:
        r = next((r for r in (prueba(fila, dx, dy) for dx in dxs for dy in dys) if r), None)
        if r is None:
            sin_sitio += list(fila)
            continue
        puestas += list(r[0].items())
        reservas.append(r[1])
        abajo.rotulos.append(r[1])
    if sin_sitio:
        suelta(reservas)
    return puestas, reservas, sin_sitio


def leyenda_aparte(board, abajo, ref, etiquetas, sep, lado, caja, xy, xs, ys):
    """Leyenda aparte con el título del conector y la misma disposición que los pads, en filas
    compactas, en el sitio libre más cercano (primero a ≤ 12 mm, aunque sea a 0,8 mm de letra).
    El rótulo del pad 1 va recuadrado, como su pad. Devuelve True si cabe."""
    ccx, ccy = (caja.x0 + caja.x1) / 2, (caja.y0 + caja.y1) / 2
    for radio, alto in ((12.0, SG.TEXTO), (12.0, SG.TEXTO_MIN), (25.0, SG.TEXTO), (25.0, SG.TEXTO_MIN)):
        # Separación extra para el recuadro del pad 1 (0,3 mm alrededor de su rótulo)
        celdas = celdas_leyenda(board, None, etiquetas, alto, sep + 0.4, lado, caja, xy, xs)
        tw, th = medir(board, "B", SG.TITULOS[ref], alto)
        paso_y = alto * 1.3 + 0.6
        cx = (min(c.x0 for c in celdas.values()) + max(c.x1 for c in celdas.values())) / 2
        compactas = {n: SG.centrada((c.x0 + c.x1) / 2 - cx, ys.index(round(xy[n][1], 2)) * paso_y,
                                    c.x1 - c.x0, c.y1 - c.y0) for n, c in celdas.items()}
        cy_titulo = (len(ys) - 1) * paso_y + alto + 0.8
        todo = [c.crece(0.3) for c in compactas.values()] + [SG.centrada(0, cy_titulo, tw, th)]
        bloque = SG.Caja(min(c.x0 for c in todo), min(c.y0 for c in todo), max(c.x1 for c in todo), max(c.y1 for c in todo))
        sitio = abajo.busca("leyenda aparte " + ref, ccx, ccy, bloque.x1 - bloque.x0, bloque.y1 - bloque.y0, radio=radio)
        if not sitio:
            abajo.fallos.remove("leyenda aparte " + ref)
            continue
        ox, oy = sitio[0] - (bloque.x0 + bloque.x1) / 2, sitio[1] - (bloque.y0 + bloque.y1) / 2
        for n, c in compactas.items():
            c = c.mueve(ox, oy)
            rotulo(board, "B", etiquetas[n], ((c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2), alto)
            if n == "1":
                r = c.crece(0.3)
                for a, b in (((r.x0, r.y0), (r.x1, r.y0)), ((r.x1, r.y0), (r.x1, r.y1)),
                             ((r.x1, r.y1), (r.x0, r.y1)), ((r.x0, r.y1), (r.x0, r.y0))):
                    shape(board, pcbnew.B_SilkS, pcbnew.SHAPE_T_SEGMENT, a=a, b=b, width=0.12)
        rotulo(board, "B", SG.TITULOS[ref], (ox, cy_titulo + oy), alto)
        abajo.aparte.append("%s (a %.0f mm, letra de %.1f mm)" % (ref, math.hypot(sitio[0] - ccx, sitio[1] - ccy), alto))
        return True
    return False


def leyenda(board, abajo, ref, etiquetas):
    """Rótulos de un grupo de pads de dos filas o columnas, en este orden de preferencia:

    1. Leyenda al lado, con la misma disposición que los pads (leyenda_al_lado), a 1,0 mm y, si
       alguna fila no cabe, toda a 0,8 mm.
    2. Si ni así: leyenda aparte con el título del conector (leyenda_aparte).
    3. Si tampoco: las filas que caben al lado a 0,8 mm y aviso de las que faltan."""
    lado, sep = SG.LEYENDA[ref]
    fp = board.FindFootprintByReference(ref)
    xy = {p.GetNumber(): (pcbnew.ToMM(p.GetPosition().x) - P.STL_OX, P.STL_OY - pcbnew.ToMM(p.GetPosition().y))
          for p in fp.Pads()}
    xs = sorted({round(x, 2) for x, _ in xy.values()})
    ys = sorted({round(y, 2) for _, y in xy.values()})
    caja = caja_pads(fp)
    for alto in (SG.TEXTO, SG.TEXTO_MIN):
        puestas, reservas, sin_sitio = leyenda_al_lado(board, abajo, etiquetas, alto, sep, lado, caja, xy, xs, ys)
        if not sin_sitio:
            break
    if sin_sitio:
        if leyenda_aparte(board, abajo, ref, etiquetas, sep, lado, caja, xy, xs, ys):
            return
        # Lo que quepa al lado, fila a fila, sin exigir todas
        filas_ok = []
        for y in ys:
            fila = {n: t for n, t in etiquetas.items() if round(xy[n][1], 2) == y}
            p, r, f = leyenda_al_lado(board, abajo, fila, alto, sep, lado, caja, xy, xs, [y])
            filas_ok += p
            abajo.fallos += ["%s.%s" % (ref, n) for n in f]
        puestas = filas_ok
    for n, c in puestas:
        rotulo(board, "B", etiquetas[n], ((c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2), alto)
    if alto < SG.TEXTO:
        abajo.reducidos.append(ref)


def centro_pads(board, ref):
    c = caja_pads(board.FindFootprintByReference(ref))
    return (c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2


def hueco_cajas(a, b):
    return math.hypot(max(a.x0 - b.x1, b.x0 - a.x1, 0), max(a.y0 - b.y1, b.y0 - a.y1, 0))


def sin_ambiguedad(board, ref):
    """Rótulo inequívoco: claramente más cerca de su pieza que de las otras de su grupo
    (SG.GRUPOS_AMBIGUOS) y, si no es de un conector de cable, lejos de los pads de cable."""
    grupo = next((g for g in SG.GRUPOS_AMBIGUOS if ref in g), ())
    ax, ay = centro_pads(board, ref)
    otras = [centro_pads(board, r) for r in grupo if r != ref]
    cables = [] if ref in SG.CONECTORES_CABLE else [
        caja_stl(p.GetBoundingBox()) for r in SG.CONECTORES_CABLE for p in board.FindFootprintByReference(r).Pads()]

    def valido(caja):
        x, y = (caja.x0 + caja.x1) / 2, (caja.y0 + caja.y1) / 2
        if any(math.hypot(x - ax, y - ay) > SG.AMBIGUEDAD * math.hypot(x - bx, y - by) for bx, by in otras):
            return False
        return all(hueco_cajas(caja, c) >= SG.HUECO_CABLE for c in cables)
    return valido


def pon(board, col, cara, nombre, ancla, txt, lados, ref_propia=None, alto=SG.TEXTO, valido=None,
        limpio_primero=True, anillo=True):
    """Coloca un rótulo (o la primera de sus alternativas que quepa)."""
    textos = txt if isinstance(txt, tuple) else (txt,)
    for i, t in enumerate(textos):
        r = col.coloca(nombre, ancla, medida(board, cara, t, alto), lados, ref_propia, valido, limpio_primero,
                       avisa=(i == len(textos) - 1), anillo=anillo)
        if r:
            rotulo(board, cara, t, *r)
            if i:
                col.reducidos.append("%s «%s»" % (nombre, t))
            return


def rotulos(board):
    """Rótulos de serigrafía (scripts/serigrafia.py), sobre la placa ya rutada. Devuelve los que no caben."""
    arriba = colocador(board, "F")
    # Nombre y versión arriba, en la franja entre el módulo y el borde delantero: la única de la
    # cara superior que no tapa la batería y donde no hay cobre (zona de la antena). En mayúsculas:
    # la «y» de «FurbyBoard» baja de la línea y el texto ya no cabe entre el módulo y el borde.
    nombre = "FURBYBOARD %s" % P.BOARD_REV.upper()
    for alto in (SG.TEXTO, SG.TEXTO_MIN):
        xy = arriba.busca("nombre arriba", -73.0, -54.6, *medir(board, "F", nombre, alto), radio=3.0)
        if xy:
            rotulo(board, "F", nombre, xy, alto)
            arriba.fallos = [f for f in arriba.fallos if f != "nombre arriba"]
            if alto < SG.TEXTO:
                arriba.reducidos.append("nombre arriba")
            break
    for ref, txt in SG.ARRIBA.items():
        fp = board.FindFootprintByReference(ref)
        lados = SG.LADO_ARRIBA.get(ref, "") + "RLUD"
        pon(board, arriba, "F", ref, caja_pads(fp, silk=pcbnew.F_SilkS), txt, lados, ref, SG.TAMANO.get(ref, SG.TEXTO),
            sin_ambiguedad(board, ref))
    abajo = colocador(board, "B")
    # Primero lo que tiene menos sitio: las leyendas de los conectores de cable y sus pads sueltos
    for ref, etiquetas in SG.PADS.items():
        if ref in SG.LEYENDA:
            leyenda(board, abajo, ref, etiquetas)
            continue
        fp = board.FindFootprintByReference(ref)
        for num, txt in etiquetas.items():
            lados = SG.LADO_PADS.get(ref, "") + "RLUD"
            # Pads de cable: manda el lado (todos los rótulos del conector al mismo lado), no las pistas
            pon(board, abajo, "B", "%s.%s" % (ref, num), caja_pads(fp, [num]), txt, lados,
                alto=SG.TAMANO_PADS.get(ref, SG.TEXTO), valido=sin_ambiguedad(board, ref), limpio_primero=False)
    # Nombre de cada TP en la cara inferior (preferencia: TEST-PLAN sobre la placa sin plano)
    for ref, txt in SG.TP_ABAJO.items():
        fp = board.FindFootprintByReference(ref)
        pon(board, abajo, "B", ref, caja_pads(fp, silk=pcbnew.B_SilkS), txt, SG.LADO_TP, valido=sin_ambiguedad(board, ref))
    for ref, txt in SG.PUENTES_ABAJO.items():
        fp = board.FindFootprintByReference(ref)
        pon(board, abajo, "B", "abajo " + ref, caja_pads(fp), txt, "CUDLR", valido=sin_ambiguedad(board, ref))
    for ref, txt in SG.TITULOS.items():
        if any(a.startswith(ref + " ") for a in abajo.aparte):
            continue   # la leyenda aparte ya lleva el título
        fp = board.FindFootprintByReference(ref)
        pon(board, abajo, "B", "titulo " + ref, caja_pads(fp), txt, "UD", anillo=False)
    silk_abajo(board, abajo)
    if arriba.reducidos + abajo.reducidos:
        print("Rótulos a %.1f mm (a %.1f no caben):" % (SG.TEXTO_MIN, SG.TEXTO), ", ".join(arriba.reducidos + abajo.reducidos))
    if abajo.aparte:
        print("Leyendas aparte (no caben junto a sus pads):", ", ".join(abajo.aparte))
    fallos = arriba.fallos + abajo.fallos
    if fallos:
        print("Rótulos sin sitio:", ", ".join(fallos))
    return fallos


def recorta_serigrafia(board):
    """Corta los trazos de serigrafía de las huellas que pasan a < MARGEN_VIA de una vía (el
    fabricante los recorta igual; así los Gerber dicen lo que se imprimirá). Solo segmentos rectos;
    devuelve cuántos tramos se han cortado y de qué piezas."""
    vias = [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y), pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2)
            for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    cortes = {}
    for fp in board.GetFootprints():
        for g in list(fp.GraphicalItems()):
            if g.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS) or g.GetClass() != "PCB_SHAPE" \
                    or g.GetShape() != pcbnew.SHAPE_T_SEGMENT:
                continue
            ax, ay = pcbnew.ToMM(g.GetStart().x), pcbnew.ToMM(g.GetStart().y)
            bx, by = pcbnew.ToMM(g.GetEnd().x), pcbnew.ToMM(g.GetEnd().y)
            largo = math.hypot(bx - ax, by - ay)
            if largo < 1e-6:
                continue
            ux, uy = (bx - ax) / largo, (by - ay) / largo
            fuera = []   # intervalos [t0, t1] del segmento que pisan una vía
            for vx, vy, r in vias:
                lim = r + SG.MARGEN_VIA + pcbnew.ToMM(g.GetWidth()) / 2
                t = (vx - ax) * ux + (vy - ay) * uy
                d = abs((vx - ax) * uy - (vy - ay) * ux)
                if d < lim and -lim < t < largo + lim:
                    m = math.sqrt(lim * lim - d * d)
                    fuera.append((t - m, t + m))
            if not fuera:
                continue
            tramos, t = [], 0.0
            for t0, t1 in sorted(fuera):
                if t0 > t:
                    tramos.append((t, t0))
                t = max(t, t1)
            if t < largo:
                tramos.append((t, largo))
            tramos = [(t0, t1) for t0, t1 in tramos if t1 - t0 >= 0.1]
            for t0, t1 in tramos:
                n = pcbnew.PCB_SHAPE(fp)
                n.SetShape(pcbnew.SHAPE_T_SEGMENT)
                n.SetLayer(g.GetLayer())
                n.SetWidth(g.GetWidth())
                n.SetStart(pcbnew.VECTOR2I(mm(ax + ux * t0), mm(ay + uy * t0)))
                n.SetEnd(pcbnew.VECTOR2I(mm(ax + ux * t1), mm(ay + uy * t1)))
                fp.Add(n)
            fp.Remove(g)
            cortes[fp.GetReference()] = cortes.get(fp.GetReference(), 0) + 1
    if cortes:
        print("Serigrafía de huellas cortada junto a vías:", ", ".join("%s (%d)" % kv for kv in sorted(cortes.items())))
    return cortes


def rutas_fijas(board, netmap):
    """Pistas y vías explícitas (scripts/rutas_fijas.py), bloqueadas para el autorrutado."""
    capas = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu, "In2.Cu": pcbnew.In2_Cu, "In3.Cu": pcbnew.In3_Cu}
    pads = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            pos = pad.GetPosition()
            pads["%s.%s" % (fp.GetReference(), pad.GetNumber())] = (
                (pcbnew.ToMM(pos.x) - P.STL_OX, P.STL_OY - pcbnew.ToMM(pos.y)), pad.GetNetname())

    def pad_xy(nombre):
        if nombre not in pads:
            raise SystemExit("rutas_fijas: pad desconocido " + nombre)
        return pads[nombre][0]

    pistas, vias = RF.rutas(pad_xy)
    for (red, capa, ancho, puntos), (_, _, _, nombres, _) in zip(pistas, RF.PISTAS):
        for n in nombres:
            ref = n if isinstance(n, str) else (n[0] if isinstance(n, tuple) and isinstance(n[0], str) else None)
            if ref and pads[ref][1] != red:
                raise SystemExit("rutas_fijas: %s es de %s, no de %s" % (ref, pads[ref][1], red))
        for a, b in zip(puntos, puntos[1:]):
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-4:
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pt(*a))
            t.SetEnd(pt(*b))
            t.SetWidth(mm(ancho))
            t.SetLayer(capas[capa])
            t.SetNet(netmap[red])
            t.SetLocked(True)
            board.Add(t)
    for red, xy, (diam, taladro) in vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pt(*xy))
        v.SetWidth(mm(diam))
        v.SetDrill(mm(taladro))
        v.SetNet(netmap[red])
        v.SetLocked(True)
        board.Add(v)
    for red, capa, puntos, clearance, prioridad in RF.ZONAS:
        z = poly_zone(board, [capas[capa]], puntos, net=netmap[red], priority=prioridad, clearance=clearance)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetLocked(True)


def escribir_stackup(ruta):
    """Bloque (stackup ...) del apilado de JLCPCB (params.STACKUP) dentro de (setup ...) del fichero
    guardado: el descriptor de apilado no está expuesto en el Python de KiCad 10, así que se escribe
    en el texto. Así el apilado queda en el proyecto (y en el fichero de trabajo de los Gerber)."""
    with open(ruta, encoding="utf-8") as fh:
        txt = fh.read()
    if "(stackup" in txt:
        return
    lineas = ['\t\t(stackup',
              '\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))',
              '\t\t\t(layer "F.Paste" (type "Top Solder Paste"))',
              '\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))']
    for nombre, tipo, grosor, er in P.STACKUP:
        if tipo == "copper":
            lineas.append('\t\t\t(layer "%s" (type "copper") (thickness %s))' % (nombre, grosor))
        else:
            lineas.append('\t\t\t(layer "%s" (type "%s") (thickness %s) (material "FR4") (epsilon_r %s) (loss_tangent 0.02))'
                          % (nombre, tipo, grosor, er))
    lineas += ['\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))',
               '\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))',
               '\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))',
               '\t\t\t(copper_finish "HAL SnPb")',
               '\t\t\t(dielectric_constraints no)',
               '\t\t)']
    marca = "\t(setup\n"
    if marca not in txt:
        raise SystemExit("gen_pcb: no se encuentra (setup) para escribir el apilado")
    txt = txt.replace(marca, marca + "\n".join(lineas) + "\n", 1)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(txt)


def import_ses(board):
    """Importa el SES de Freerouting si se pasa --ses <fichero> (sobre las rutas fijas ya puestas)."""
    if "--ses" not in sys.argv:
        return False
    ses = sys.argv[sys.argv.index("--ses") + 1]
    ok = pcbnew.ImportSpecctraSES(board, ses)
    print("Rutado importado de", os.path.basename(ses), "->", ok)
    return ok


def main():
    board = pcbnew.BOARD()
    setup_board(board)
    netmap = {}
    for n in D.nets():
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        netmap[n] = ni
    outline(board)
    place(board, netmap)
    mechanical(board)
    board.SetFileName(P.PCB)
    pcbnew.SaveBoard(P.PCB, board)
    board = pcbnew.LoadBoard(P.PCB)
    setup_board(board)
    netmap = {n: board.FindNet(n) for n in D.nets()}
    # In1 e In4 son planos de GND (no se rutan). In2 (relleno de VSYS en lo libre) e In3 son de señal.
    for nombre, tipo in P.LAYER_TYPES.items():
        board.SetLayerType(board.GetLayerID(nombre), pcbnew.LT_POWER if tipo == "power" else pcbnew.LT_SIGNAL)
    rutado = "--sin-rutado" not in sys.argv
    if rutado:
        rutas_fijas(board, netmap)
        import_ses(board)
    # Rótulos después del cobre: así no pisan vías y prefieren sitios sin pistas debajo
    recorta_serigrafia(board)
    rotulos(board)
    zones(board, netmap, exteriores=rutado)
    pcbnew.SaveBoard(P.PCB, board)
    if rutado or "--rellenar" in sys.argv:
        # Relleno sobre la placa recargada del disco (kicad-automatizacion.md §3 y §10)
        board = pcbnew.LoadBoard(P.PCB)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(P.PCB, board)
    escribir_stackup(P.PCB)
    print("PCB escrito:", os.path.basename(P.PCB))
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
