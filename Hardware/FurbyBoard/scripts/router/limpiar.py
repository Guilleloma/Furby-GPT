#!/usr/bin/env python3
"""Limpieza del rutado (tras importar el SES de Freerouting o rematar a mano).

Se ejecuta con el Python de KiCad:
    $KICAD_PY scripts/router/limpiar.py [--informe]

Por capa, red y ancho:
1. Une los tramos colineales que se tocan (un segmento por tramo recto) y quita los
   repetidos y los de longitud nula.
2. Quita las puntas colgando (tramos con un extremo que no toca nada).
3. Informa de los tramos que no van a 0°, 45° o 90° y de los ángulos agudos entre
   tramos seguidos (trampas de ácido): esos se rehacen con el rutador por rejilla.
"""
import math
import os
import sys
from collections import defaultdict

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import params as P  # noqa: E402

TOL = pcbnew.FromMM(0.001)


def mm(v):
    return pcbnew.ToMM(v)


def xy(p):
    return (int(p.x), int(p.y))


def clave(p):
    p = xy(p) if not isinstance(p, tuple) else p
    return (round(p[0] / TOL), round(p[1] / TOL))


def colineales(a, b, c):
    """a-b y b-c en la misma recta y sentido."""
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return True
    seno = (v1[0] * v2[1] - v1[1] * v2[0]) / (n1 * n2)
    return abs(seno) < 1e-4 and v1[0] * v2[0] + v1[1] * v2[1] > 0


def anclajes(board):
    """Puntos donde termina legítimamente una pista: pads y vías."""
    out = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            out.append(pad)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            out.append(t)
    return out


def toca(item_list, p, capa, red):
    for it in item_list:
        if it.GetNetname() != red or not it.IsOnLayer(capa):
            continue
        if it.HitTest(p):
            return True
    return False


def fusionar(segs):
    """Une segmentos (tuplas de puntos) colineales que se tocan; quita nulos y repetidos."""
    segs = [tuple(sorted((a, b))) for a, b in segs if a != b]
    segs = list(dict.fromkeys(segs))
    cambiado = True
    while cambiado:
        cambiado = False
        extremos = defaultdict(list)
        for k, (a, b) in enumerate(segs):
            extremos[a].append(k)
            extremos[b].append(k)
        for punto, ks in extremos.items():
            if len(ks) != 2:
                continue
            i, j = ks
            a = segs[i][0] if segs[i][1] == punto else segs[i][1]
            c = segs[j][0] if segs[j][1] == punto else segs[j][1]
            if colineales(a, punto, c):
                segs[i] = tuple(sorted((a, c)))
                segs.pop(j)
                cambiado = True
                break
    return segs


def unir_colineales(board):
    grupos = defaultdict(list)
    for t in list(board.GetTracks()):
        if t.GetClass() == "PCB_TRACK":
            grupos[(t.GetLayer(), t.GetNetCode(), t.GetWidth(), t.IsLocked())].append(t)
    quitados = 0
    for (capa, red, ancho, fijo), tramos in grupos.items():
        segs = [(xy(t.GetStart()), xy(t.GetEnd())) for t in tramos]
        nuevos = fusionar(segs)
        if len(nuevos) == len(segs):
            continue
        quitados += len(segs) - len(nuevos)
        net = tramos[0].GetNet()
        for t in tramos:
            board.Delete(t)
        for a, b in nuevos:
            n = pcbnew.PCB_TRACK(board)
            n.SetStart(pcbnew.VECTOR2I(*a))
            n.SetEnd(pcbnew.VECTOR2I(*b))
            n.SetWidth(ancho)
            n.SetLayer(capa)
            n.SetNet(net)
            n.SetLocked(fijo)
            board.Add(n)
    return quitados


def quitar_puntas(board):
    total = 0
    while True:
        anc = anclajes(board)
        tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
        quitar = []
        for t in tracks:
            for p in (t.GetStart(), t.GetEnd()):
                otros = [o for o in tracks if o is not t and o.GetNetCode() == t.GetNetCode()
                         and o.GetLayer() == t.GetLayer() and o.HitTest(p)]
                if not otros and not toca(anc, p, t.GetLayer(), t.GetNetname()):
                    quitar.append(t)
                    break
        if not quitar:
            return total
        for t in quitar:
            board.Delete(t)
        total += len(quitar)


def informe(board):
    raros, agudos = [], []
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    for t in tracks:
        dx, dy = t.GetEnd().x - t.GetStart().x, t.GetEnd().y - t.GetStart().y
        ang = math.degrees(math.atan2(dy, dx)) % 45
        if min(ang, 45 - ang) > 0.5:
            raros.append(t)
    porpunto = defaultdict(list)
    for t in tracks:
        s0, e0 = xy(t.GetStart()), xy(t.GetEnd())
        porpunto[(t.GetLayer(), t.GetNetCode(), clave(s0))].append((t, s0, e0))
        porpunto[(t.GetLayer(), t.GetNetCode(), clave(e0))].append((t, e0, s0))
    for lista in porpunto.values():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                _, c, a = lista[i]
                _, _, b = lista[j]
                v1 = (a[0] - c[0], a[1] - c[1])
                v2 = (b[0] - c[0], b[1] - c[1])
                n1, n2 = math.hypot(*v1), math.hypot(*v2)
                if n1 == 0 or n2 == 0:
                    continue
                cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
                if cos > math.cos(math.radians(89.5)):
                    agudos.append(c)
    return raros, agudos


def main():
    board = pcbnew.LoadBoard(P.PCB)
    n0 = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK")
    u = unir_colineales(board)
    p = quitar_puntas(board)
    u += unir_colineales(board)
    n1 = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK")
    raros, agudos = informe(board)
    print("Tramos: %d -> %d (unidos o repetidos: %d; puntas colgando: %d)" % (n0, n1, u, p))
    print("Fuera de 0/45/90°: %d; ángulos agudos: %d" % (len(raros), len(agudos)))
    if "--informe" in sys.argv:
        for t in raros[:30]:
            print("  ángulo", t.GetNetname(), t.GetLayerName(), (round(mm(t.GetStart().x), 2), round(mm(t.GetStart().y), 2)))
        for c in agudos[:30]:
            print("  agudo", (round(mm(c[0]), 2), round(mm(c[1]), 2)))
    pcbnew.SaveBoard(P.PCB, board)


if __name__ == "__main__":
    main()
