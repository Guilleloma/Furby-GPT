#!/usr/bin/env python3
"""Genera FurbyBoard.kicad_pcb: contorno, colocación, zonas, reglas y serigrafía.

Se ejecuta con el Python de KiCad:
    $KICAD_PY scripts/gen_pcb.py [--sin-rutado]

- Contorno, taladros y agujero del mecanismo: Hardware/PCB-suelo/geometria.json.
- Colocación: scripts/layout.py (coordenadas del STL).
- Redes: scripts/design.py. Las huellas se enlazan con los símbolos por UUID
  (paridad esquemático↔PCB).
- Rutado: el par USB va trazado a mano (scripts/rutas_fijas.py). El resto, si
  existe scripts/rutado.ses (Freerouting sobre el DSN de exportar_dsn.py), se
  importa; si no, el PCB queda colocado y sin rutar.
- Serigrafía: nombre y versión, logo y rótulos colocados solos (scripts/serigrafia.py).
- Planos: GND en In1 (L2) entero; In2 (L3) es capa de señal con relleno de VSYS; relleno de GND en F.Cu y B.Cu tras el rutado.
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
    """Plano de GND en In1 y relleno de VSYS en lo que dejen libre las señales de In2.
    Rellenos de GND en F.Cu y B.Cu solo con el rutado hecho."""
    cu = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
    c = GEO["resultado"]["caja"]
    todo = caja(c[0] - 1, c[2] + 1, c[1] - 1, c[3] + 1)
    poly_zone(board, [pcbnew.In1_Cu], todo, net=netmap["GND"])
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


def silk(board):
    F, B = pcbnew.F_SilkS, pcbnew.B_SilkS
    # Franja entre el módulo y el borde delantero: la única cara superior que no tapa la batería
    # y donde no hay cobre (zona de la antena).
    text(board, F, "FurbyBoard %s" % P.BOARD_REV, -73.0, -54.45, 0.8, 0.15)
    # Nombre y versión a la derecha del logo (zona trasera izquierda, bajo la batería, sin pads en la cara B)
    lx, ly = LAY.LOGO_INFERIOR["x"], LAY.LOGO_INFERIOR["y"]
    tx = lx[1] + 6.0
    text(board, B, "FurbyBoard", tx, -106.6, 1.2, 0.15, mirror=True)
    text(board, B, "%s · %s" % (P.BOARD_REV, P.BOARD_DATE), tx, -104.9, 1.0, 0.15, mirror=True)
    # Recuadro en blanco para numerar la placa a rotulador (TEST-PLAN.md), a la derecha del logo
    x0, x1, y0, y1 = lx[1] + 1.5, lx[1] + 9.5, -117.0, -113.0
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        shape(board, B, pcbnew.SHAPE_T_SEGMENT, a=a, b=b, width=0.15)
    text(board, B, "PLACA", (x0 + x1) / 2, y1 + 0.8, 0.8, 0.15, mirror=True)


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
    """Obstáculos para rotular una cara: pads, serigrafía y cuerpos de las piezas montadas."""
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
    mec = GEO["mecanismo"]
    circulos = [(mec["centro"][0], mec["centro"][1], mec["exclusion_diametro"] / 2)]
    circulos += [(x, y, GEO["taladro_diametro"] / 2 + 0.8) for x, y in GEO["taladros"]]
    return SG.Colocador(contorno_muestreado(), circulos, pads, silk, cuerpos)


def rotulo(board, cara, txt, xy=None):
    t = text(board, pcbnew.F_SilkS if cara == "F" else pcbnew.B_SilkS, txt, *(xy or (0, 0)),
             SG.TEXTO, SG.GROSOR, mirror=(cara == "B"))
    if xy is None:
        bb = t.GetBoundingBox()
        board.Remove(t)
        return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
    return t


def caja_pads(fp, numeros=None, silk=None):
    """Caja de los pads (o de algunos) más, si se pide, la serigrafía propia de la pieza."""
    cajas = [caja_stl(p.GetBoundingBox()) for p in fp.Pads() if numeros is None or p.GetNumber() in numeros]
    if silk is not None:
        cajas += [caja_stl(g.GetBoundingBox()) for g in fp.GraphicalItems() if g.GetLayer() == silk]
    return SG.Caja(min(c.x0 for c in cajas), min(c.y0 for c in cajas), max(c.x1 for c in cajas), max(c.y1 for c in cajas))


def rotulos(board):
    """Rótulos de serigrafía (scripts/serigrafia.py). Devuelve los que no caben."""
    fallos = []
    arriba = colocador(board, "F")
    for ref, txt in SG.ARRIBA.items():
        fp = board.FindFootprintByReference(ref)
        lados = SG.LADO_ARRIBA.get(ref, "") + "RLUD"
        xy = arriba.coloca(ref, caja_pads(fp, silk=pcbnew.F_SilkS), rotulo(board, "F", txt), lados, ref)
        if xy:
            rotulo(board, "F", txt, xy)
    abajo = colocador(board, "B")
    for ref, etiquetas in SG.PADS.items():
        fp = board.FindFootprintByReference(ref)
        pads = {p.GetNumber(): p for p in fp.Pads()}
        if ref in SG.LEYENDA:
            # Leyenda al lado con la disposición de los pads (mismas filas, columnas más anchas)
            lado, paso = SG.LEYENDA[ref]
            xs = sorted({round(pcbnew.ToMM(p.GetPosition().x) - P.STL_OX, 2) for p in pads.values()})
            caja = caja_pads(fp)
            w_max = max(rotulo(board, "B", t)[0] for t in etiquetas.values())
            for num, txt in etiquetas.items():
                col = xs.index(round(pcbnew.ToMM(pads[num].GetPosition().x) - P.STL_OX, 2))
                if lado == "L":
                    x = caja.x0 - SG.HUECO - w_max / 2 - (len(xs) - 1 - col) * paso
                else:
                    x = caja.x1 + SG.HUECO + w_max / 2 + col * paso
                y = P.STL_OY - pcbnew.ToMM(pads[num].GetPosition().y)
                w, h = rotulo(board, "B", txt)
                hueco = SG.Caja(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
                if abajo.libre(hueco):
                    abajo.silk.append(hueco)
                    rotulo(board, "B", txt, (x, y))
                else:
                    abajo.fallos.append("%s.%s" % (ref, num))
            continue
        for num, txt in etiquetas.items():
            lados = SG.LADO_PADS.get(ref, "RLUD")
            xy = abajo.coloca("%s.%s" % (ref, num), caja_pads(fp, [num]), rotulo(board, "B", txt), lados + "RLUD")
            if xy:
                rotulo(board, "B", txt, xy)
    # Nombre de cada TP en la cara inferior (preferencia: TEST-PLAN sobre la placa sin plano)
    for ref, txt in SG.TP_ABAJO.items():
        fp = board.FindFootprintByReference(ref)
        xy = abajo.coloca(ref, caja_pads(fp, silk=pcbnew.B_SilkS), rotulo(board, "B", txt), SG.LADO_TP)
        if xy:
            rotulo(board, "B", txt, xy)
    for ref, txt in SG.PUENTES_ABAJO.items():
        fp = board.FindFootprintByReference(ref)
        xy = abajo.coloca("abajo " + ref, caja_pads(fp), rotulo(board, "B", txt), "CUDLR")
        if xy:
            rotulo(board, "B", txt, xy)
    for ref, txt in SG.TITULOS.items():
        fp = board.FindFootprintByReference(ref)
        xy = abajo.coloca("titulo " + ref, caja_pads(fp), rotulo(board, "B", txt), "UDLR")
        if xy:
            rotulo(board, "B", txt, xy)
    fallos = arriba.fallos + abajo.fallos
    if fallos:
        print("Rótulos sin sitio:", ", ".join(fallos))
    return fallos


def rutas_fijas(board, netmap):
    """Pistas y vías trazadas a mano (scripts/rutas_fijas.py), bloqueadas para el autorrutado."""
    capas = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu, "In2.Cu": pcbnew.In2_Cu}
    for capa, ancho, red, puntos in RF.TRACKS:
        for a, b in zip(puntos, puntos[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pt(*a))
            t.SetEnd(pt(*b))
            t.SetWidth(mm(ancho))
            t.SetLayer(capas[capa])
            t.SetNet(netmap[red])
            t.SetLocked(True)
            board.Add(t)
    for red, xy in RF.VIAS:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pt(*xy))
        v.SetWidth(mm(RF.VIA[0]))
        v.SetDrill(mm(RF.VIA[1]))
        v.SetNet(netmap[red])
        v.SetLocked(True)
        board.Add(v)


def import_ses(board):
    ses = os.path.join(P.ROOT, "scripts", "rutado.ses")
    if not os.path.exists(ses):
        return False
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
    silk(board)
    rotulos(board)
    board.SetFileName(P.PCB)
    pcbnew.SaveBoard(P.PCB, board)
    board = pcbnew.LoadBoard(P.PCB)
    setup_board(board)
    netmap = {n: board.FindNet(n) for n in D.nets()}
    # In1 es el plano de GND (no se ruta). In2 es capa de señal con relleno de VSYS en lo libre.
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_SIGNAL)
    rutado = "--sin-rutado" not in sys.argv and import_ses(board)
    if rutado:
        rutas_fijas(board, netmap)
    zones(board, netmap, exteriores=rutado)
    if "--rellenar" in sys.argv:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(P.PCB, board)
    print("PCB escrito:", os.path.basename(P.PCB))


if __name__ == "__main__":
    main()
