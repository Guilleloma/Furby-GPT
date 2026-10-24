#!/usr/bin/env python3
"""Genera FurbyBoard.kicad_pcb: contorno, colocación, zonas, reglas y serigrafía.

Se ejecuta con el Python de KiCad:
    $KICAD_PY scripts/gen_pcb.py [--sin-rutado]

- Contorno, taladros y agujero del mecanismo: Hardware/PCB-suelo/geometria.json.
- Colocación: scripts/layout.py (coordenadas del STL).
- Redes: scripts/design.py. Las huellas se enlazan con los símbolos por UUID
  (paridad esquemático↔PCB).
- Rutado: si existe scripts/rutado.ses (Freerouting), se importa; si no, el PCB
  queda colocado y sin rutar.
- Planos: GND en In1 (L2) entero y relleno de GND en F.Cu, In2 y B.Cu.
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
    faltan = sorted(set(parts) - set(lay))
    if faltan:
        raise SystemExit("Sin colocar: " + ", ".join(faltan))
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
        fp.Reference().SetLayer(pcbnew.F_Fab)
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
    fp.SetPosition(pt((lx[0] + lx[1]) / 2, ly[1] - 7.4))
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
        z.SetDoNotAllowFootprints(False)
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


def zones(board, netmap):
    cu = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
    c = GEO["resultado"]["caja"]
    todo = caja(c[0] - 1, c[2] + 1, c[1] - 1, c[3] + 1)
    for layer, prio in ((pcbnew.In1_Cu, 0), (pcbnew.F_Cu, 0), (pcbnew.In2_Cu, 0), (pcbnew.B_Cu, 0)):
        poly_zone(board, [layer], todo, net=netmap["GND"], priority=prio)
    a = LAY.ANTENA_SIN_COBRE
    poly_zone(board, cu, caja(a["x"][0], a["x"][1], a["y"][0], a["y"][1] + 5), rule=("tracks", "vias", "pads", "fills"))
    lg = LAY.LOGO_INFERIOR
    poly_zone(board, [pcbnew.B_Cu], caja(lg["x"][0], lg["x"][1], lg["y"][0], lg["y"][1]), rule=("vias", "pads"))


def silk(board):
    F, B = pcbnew.F_SilkS, pcbnew.B_SilkS
    # Franja entre el módulo y el borde delantero: la única cara superior que no tapa la batería
    # y donde no hay cobre (zona de la antena).
    text(board, F, "FurbyBoard %s" % P.BOARD_REV, -73.0, -54.45, 0.8, 0.15)
    lx = LAY.LOGO_INFERIOR["x"]
    cx = (lx[0] + lx[1]) / 2
    text(board, B, "FurbyBoard", cx, -87.2, 1.6, 0.2, mirror=True)
    text(board, B, "%s · %s" % (P.BOARD_REV, P.BOARD_DATE), cx, -89.5, 1.2, 0.15, mirror=True)


def apply_netclasses(board):
    setup_board(board)


def import_ses(board):
    ses = os.path.join(P.ROOT, "scripts", "rutado.ses")
    if os.path.exists(ses):
        ok = pcbnew.ImportSpecctraSES(board, ses)
        print("Rutado importado de", os.path.basename(ses), "->", ok)


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
    board.SetFileName(P.PCB)
    pcbnew.SaveBoard(P.PCB, board)
    board = pcbnew.LoadBoard(P.PCB)
    setup_board(board)
    netmap = {n: board.FindNet(n) for n in D.nets()}
    if "--sin-rutado" not in sys.argv:
        import_ses(board)
    zones(board, netmap)
    if "--rellenar" in sys.argv:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(P.PCB, board)
    print("PCB escrito:", os.path.basename(P.PCB))


if __name__ == "__main__":
    main()
