#!/usr/bin/env python3
"""Rutador por rejilla de la FurbyBoard (sustituye a Freerouting).

    python3 scripts/router/rutar.py <geometria.json> <rutas.json> [--orden fichero]

Necesita numpy y matplotlib (contains_points para rasterizar) y un compilador de C
(astar.c se compila al vuelo). Entrada: la salida de extraer.py. Salida: pistas y
vías nuevas, que aplica aplicar.py.

Modelo:
- Rejilla de 0,05 mm en tres capas de señal: F.Cu, In2.Cu y B.Cu. In1.Cu es el
  plano de GND y no se ruta; las vías la atraviesan (KiCad le hace el hueco).
- Para cada red, una celda está libre si el cobre de las demás redes queda a más
  de holgura + medio ancho + margen, el borde a más de 0,3 + medio ancho y fuera
  de las áreas prohibidas. El margen cubre el error de la rejilla, así que lo que
  sale aquí pasa el DRC.
- Cerca de sus propios pads una red ancha puede salir con el ancho de señal
  (0,2): es lo que entra entre pads de 0,5 de paso.
- Las redes de varios pads se rutan como árbol: cada vez se une el pad más
  cercano a lo ya rutado (A* desde todo el árbol).
- GND no se ruta como árbol: cada pad SMD de GND baja con una vía al plano.
- Orden: potencia, GND, USB, I2S, cámara y lo demás. Las redes que fallan se
  reintentan al principio de la siguiente vuelta, quitando lo rutado.
"""
import ctypes
import json
import math
import os
import subprocess
import sys
import tempfile
import time

import numpy as np
from matplotlib.path import Path

G = 0.05            # paso de la rejilla, mm
MARGEN = 0.09       # cubre la discretización de la pista y la del cobre ajeno (2 × media diagonal)
CAPAS = ["F", "I", "B"]
ANCHO_SALIDA = 0.2  # ancho con el que una red ancha sale de sus pads finos
ZONA_SALIDA = 0.8   # mm alrededor de sus pads donde se permite ese ancho
COSTE_VIA = 400     # en décimas de celda (10 = una celda recta): una vía «cuesta» 2 mm de pista
COSTE_CAPA = [0, 2, 1]  # pequeña preferencia: F, luego B, luego In2

AQUI = os.path.dirname(os.path.abspath(__file__))

# Test points: pad de 1,5 mm en B.Cu sobre una vía de su red pegada a la fuente (tramo
# de F.Cu de pocas décimas, sin pista propia). Se colocan antes de rutar para que cojan
# el mejor sitio. TP -> (referencia, pad) de la fuente.
FUENTES_TP = {
    "TP1": ("F1", "2"), "TP2": ("U1", "1"), "TP3": ("U1", "3"), "TP4": ("Q1", "1"),
    "TP5": ("U2", "10"), "TP6": ("U3", "6"), "TP7": ("U5", "6"), "TP8": ("U6", "1"),
    "TP9": ("U7", "1"), "TP10": ("U8", "5"), "TP11": ("U9", "5"), "TP12": ("J1", "A1"),
    "TP13": ("U5", "5"), "TP14": ("U6", "7"),
}
R_TP = 0.75
P_VIA_PAD = 0.45        # del borde de un pad SMD al centro de una vía de abanico (sin vía en pad)


def compilar():
    so = os.path.join(tempfile.gettempdir(), "furbyboard_astar_%d.so" % os.getuid())
    src = os.path.join(AQUI, "astar.c")
    if not os.path.exists(so) or os.path.getmtime(so) < os.path.getmtime(src):
        subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-o", so, src], check=True)
    lib = ctypes.CDLL(so)
    P = ctypes.POINTER
    lib.astar.restype = ctypes.c_int
    lib.astar.argtypes = [ctypes.c_int] * 3 + [P(ctypes.c_uint8)] * 3 + [P(ctypes.c_int32), ctypes.c_int,
                                                                         ctypes.c_int, P(ctypes.c_int32)] \
        + [ctypes.c_int] * 8 + [P(ctypes.c_int32), ctypes.c_int]
    lib.edt.restype = None
    lib.edt.argtypes = [ctypes.c_int, ctypes.c_int, P(ctypes.c_uint8), P(ctypes.c_float)]
    return lib


def ptr(a, t):
    return a.ctypes.data_as(ctypes.POINTER(t))


class Rejilla:
    def __init__(self, geo, lib):
        self.geo, self.lib = geo, lib
        xs = [p[0] for p in geo["contorno"]]
        ys = [p[1] for p in geo["contorno"]]
        self.x0, self.y0 = min(xs) - 1.0, min(ys) - 1.0
        self.W = int((max(xs) + 1.0 - self.x0) / G) + 1
        self.H = int((max(ys) + 1.0 - self.y0) / G) + 1
        gx = self.x0 + (np.arange(self.W) + 0.5) * G
        gy = self.y0 + (np.arange(self.H) + 0.5) * G
        self.XX, self.YY = np.meshgrid(gx, gy)
        self.pts = np.column_stack([self.XX.ravel(), self.YY.ravel()])
        self.reglas = geo["reglas"]
        redes = sorted(geo["anchos"])
        self.nid = {r: i for i, r in enumerate(redes)}
        self.redes = redes
        self.ancho = geo["anchos"]
        # cobre por capa: -1 libre, -3 obstáculo de todas las redes (taladros sin red)
        self.lab = np.full((3, self.H, self.W), -1, dtype=np.int16)
        self.pad_celdas = []       # (pad, [(capa, idx plano)])
        self.fuera = self._fuera_de_placa()
        self.d_borde = self.edt(self.fuera)
        self.ko_pista = np.zeros((3, self.H, self.W), dtype=np.uint8)
        self.ko_via = np.zeros((self.H, self.W), dtype=np.uint8)
        for z in geo["prohibidas"]:
            m = np.zeros((self.H, self.W), dtype=np.uint8)
            for poly in z["poly"]:
                m |= self.poly_mask(poly)
            for c in z["capas"]:
                if z["pistas"] and c in CAPAS:
                    self.ko_pista[CAPAS.index(c)] |= m
            if z["vias"]:
                self.ko_via |= m
        self.d_ko = [self.edt(self.ko_pista[l]) for l in range(3)]
        self.d_kovia = self.edt(self.ko_via)
        for p in geo["pads"]:
            m = np.zeros((self.H, self.W), dtype=np.uint8)
            for poly in p["poly"]:
                m |= self.poly_mask(poly)
            if p["npth"] or not p["red"]:
                r = (p["agujero"][2] + 0.05) if p["agujero"] else 0
                if p["agujero"]:
                    m |= self.disco(p["agujero"][0], p["agujero"][1], r)
                for l in range(3):
                    self.lab[l][m.astype(bool)] = -3
                continue
            n = self.nid[p["red"]]
            celdas = []
            for c in p["capas"]:
                if c not in CAPAS:
                    continue
                l = CAPAS.index(c)
                self.lab[l][m.astype(bool)] = n
                celdas.append((l, m.astype(bool)))
            self.pad_celdas.append((p, celdas))
        # taladros (pads pasantes y vías): las vías nuevas guardan 0,25 de taladro a taladro
        self.agujeros = np.zeros((self.H, self.W), dtype=np.uint8)
        for p in geo["pads"]:
            if p["agujero"]:
                self.agujeros |= self.disco(*p["agujero"])
        for v in geo["vias"]:
            self.agujeros |= self.disco(v["pos"][0], v["pos"][1], self.reglas["via_taladro"] / 2)
        self.d_agujeros = self.edt(self.agujeros)
        self.pad_any = np.zeros((self.H, self.W), dtype=bool)
        for _, celdas in self.pad_celdas:
            for l, m in celdas:
                if l == 0:
                    self.pad_any |= m
        # vías fuera de los pads SMD: centro a 0,4 mm o más de su borde (anillo de 0,3 + 0,1)
        self.lejos_pads = self.edt(self.pad_any.astype(np.uint8)) >= ((P_VIA_PAD) / G) ** 2
        self.pistas_nuevas, self.vias_nuevas = [], []
        self.lab_pistas = np.full((3, self.H, self.W), -1, dtype=np.int16)   # cobre que se puede levantar
        self.bloqueos = {}
        for t in geo["pistas"]:
            self.pinta_segmento(CAPAS.index(t["capa"]), t["a"], t["b"], t["w"], self.nid[t["red"]])
        for v in geo["vias"]:
            self.pinta_via(v["pos"], v["d"], self.nid[v["red"]])

    # ------------------------------------------------------------- rasterizado
    def poly_mask(self, poly):
        path = Path(poly)
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        i0 = max(0, int((min(xs) - self.x0) / G) - 1)
        i1 = min(self.W, int((max(xs) - self.x0) / G) + 2)
        j0 = max(0, int((min(ys) - self.y0) / G) - 1)
        j1 = min(self.H, int((max(ys) - self.y0) / G) + 2)
        m = np.zeros((self.H, self.W), dtype=np.uint8)
        if i1 <= i0 or j1 <= j0:
            return m
        sub = np.column_stack([self.XX[j0:j1, i0:i1].ravel(), self.YY[j0:j1, i0:i1].ravel()])
        m[j0:j1, i0:i1] = path.contains_points(sub, radius=1e-9).reshape(j1 - j0, i1 - i0)
        return m

    def disco(self, x, y, r):
        m = (self.XX - x) ** 2 + (self.YY - y) ** 2 <= r * r
        return m.astype(np.uint8)

    def _fuera_de_placa(self):
        dentro = self.poly_mask(self.geo["contorno"]).astype(bool)
        for h in self.geo["huecos"]:
            dentro &= ~self.poly_mask(h).astype(bool)
        return (~dentro).astype(np.uint8)

    def edt(self, marca):
        out = np.empty((self.H, self.W), dtype=np.float32)
        marca = np.ascontiguousarray(marca, dtype=np.uint8)
        self.lib.edt(self.W, self.H, ptr(marca, ctypes.c_uint8), ptr(out, ctypes.c_float))
        return out          # distancia al cuadrado, en celdas

    def ventana(self, x0, y0, x1, y1, crece):
        i0 = max(0, int((min(x0, x1) - crece - self.x0) / G))
        i1 = min(self.W, int((max(x0, x1) + crece - self.x0) / G) + 1)
        j0 = max(0, int((min(y0, y1) - crece - self.y0) / G))
        j1 = min(self.H, int((max(y0, y1) + crece - self.y0) / G) + 1)
        return i0, j0, i1, j1

    def pinta_segmento(self, l, a, b, w, n, lab=None):
        i0, j0, i1, j1 = self.ventana(a[0], a[1], b[0], b[1], w)
        X, Y = self.XX[j0:j1, i0:i1], self.YY[j0:j1, i0:i1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = np.clip(((X - a[0]) * dx + (Y - a[1]) * dy) / L2, 0, 1) if L2 > 0 else 0
        d2 = (X - a[0] - t * dx) ** 2 + (Y - a[1] - t * dy) ** 2
        sub = (self.lab if lab is None else lab)[l, j0:j1, i0:i1]
        sub[(d2 <= (w / 2) ** 2) & (sub == -1)] = n

    def pinta_via(self, pos, d, n, lab=None):
        i0, j0, i1, j1 = self.ventana(pos[0], pos[1], pos[0], pos[1], d)
        X, Y = self.XX[j0:j1, i0:i1], self.YY[j0:j1, i0:i1]
        m = (X - pos[0]) ** 2 + (Y - pos[1]) ** 2 <= (d / 2) ** 2
        for l in range(3):
            sub = (self.lab if lab is None else lab)[l, j0:j1, i0:i1]
            sub[m & (sub == -1)] = n

    def celda(self, x, y):
        return int((y - self.y0) / G), int((x - self.x0) / G)

    def xy(self, j, i):
        return (round(self.x0 + (i + 0.5) * G, 4), round(self.y0 + (j + 0.5) * G, 4))

    # ------------------------------------------------------------------ libres
    def mascaras(self, n, w, pads_red):
        """libre[3,H,W] para la red n con ancho w, y via_ok[H,W]."""
        hol, borde = self.reglas["holgura"], self.reglas["borde"]
        r_via = self.reglas["via_d"] / 2
        dn = [self.edt(((self.lab[l] >= 0) & (self.lab[l] != n)) | (self.lab[l] == -3)) for l in range(3)]
        lim = lambda r: (r / G) ** 2

        def libre_para(ancho):
            out = np.zeros((3, self.H, self.W), dtype=bool)
            for l in range(3):
                out[l] = ((dn[l] >= lim(hol + ancho / 2 + MARGEN))
                          & (self.d_borde >= lim(borde + ancho / 2 + MARGEN))
                          & (self.d_ko[l] >= lim(ancho / 2 + MARGEN)))
            return out
        libre = libre_para(w)
        # celdas donde cabe al menos una pista estrecha: dentro de los pads propios, la pista
        # solo puede pasar por estas (si no, su borde invadiría el margen del pad vecino)
        self._angosto = libre if w <= ANCHO_SALIDA + 1e-6 else libre_para(ANCHO_SALIDA)
        estrecho = np.zeros_like(libre)
        if w > ANCHO_SALIDA + 1e-6:
            angosto = self._angosto
            for l in range(3):
                propio = np.zeros((self.H, self.W), dtype=np.uint8)
                for capa, m in pads_red:
                    if capa == l:
                        propio |= m.astype(np.uint8)
                if propio.any():
                    cerca = self.edt(propio) <= lim(ZONA_SALIDA)
                    estrecho[l] = angosto[l] & cerca & ~libre[l]
            libre |= estrecho
        via_ok = ((dn[0] >= lim(hol + r_via + MARGEN)) & (dn[1] >= lim(hol + r_via + MARGEN))
                  & (dn[2] >= lim(hol + r_via + MARGEN)) & (self.d_borde >= lim(borde + r_via + MARGEN))
                  & (self.d_kovia >= lim(r_via + MARGEN))
                  & (self.d_agujeros >= lim(self.reglas["via_taladro"] / 2 + self.reglas["agujero_agujero"] + MARGEN)))
        return libre, estrecho, via_ok

    # ------------------------------------------------------------------- rutar
    def astar(self, libre, via_ok, objetivo, fuentes, caja, solo_capas=None):
        lib = libre
        if solo_capas is not None:
            lib = libre.copy()
            for l in range(3):
                if l not in solo_capas:
                    lib[l] = False
        lib8 = np.ascontiguousarray(lib, dtype=np.uint8)
        via8 = np.ascontiguousarray(via_ok, dtype=np.uint8)
        obj8 = np.ascontiguousarray(objetivo, dtype=np.uint8)
        f = np.ascontiguousarray(np.array(fuentes, dtype=np.int32).ravel())
        cc = np.array(COSTE_CAPA, dtype=np.int32)
        tj, ti = np.nonzero(objetivo.any(axis=0))
        if len(tj) == 0:
            return None
        x0, y0, x1, y1 = caja
        max_len = 200000
        out = np.zeros(max_len * 3, dtype=np.int32)
        n = self.lib.astar(self.W, self.H, 3, ptr(lib8, ctypes.c_uint8), ptr(via8, ctypes.c_uint8),
                           ptr(obj8, ctypes.c_uint8), ptr(f, ctypes.c_int32), len(fuentes), COSTE_VIA,
                           ptr(cc, ctypes.c_int32), x0, y0, x1, y1, int(ti.min()), int(tj.min()),
                           int(ti.max()), int(tj.max()), ptr(out, ctypes.c_int32), max_len)
        if n <= 0:
            return None
        return [tuple(out[3 * k:3 * k + 3]) for k in range(n)][::-1]

    # ------------------------------------------------------------ post-proceso
    @staticmethod
    def _linea_octil(a, b, diag_primero):
        """Celdas de a a b en dos tramos (recto y a 45°). Devuelve (celdas, esquina)."""
        dj, di = int(b[0]) - int(a[0]), int(b[1]) - int(a[1])
        sj, si = (dj > 0) - (dj < 0), (di > 0) - (di < 0)
        nd = min(abs(dj), abs(di))
        nr = max(abs(dj), abs(di)) - nd
        recto = (sj, 0) if abs(dj) > abs(di) else (0, si)
        pasos = [(sj, si)] * nd + [recto] * nr if diag_primero else [recto] * nr + [(sj, si)] * nd
        celdas, j, i = [], int(a[0]), int(a[1])
        esquina = None
        for k, (pj, pi) in enumerate(pasos):
            celdas.append(((j, i), (j + pj, i + pi)))
            j, i = j + pj, i + pi
            if k + 1 < len(pasos) and pasos[k + 1] != (pj, pi):
                esquina = (j, i)
        return celdas, esquina

    @staticmethod
    def _libre_linea(m, celdas):
        for (j0, i0), (j1, i1) in celdas:
            if not m[j1, i1]:
                return False
        return True

    def _simplifica(self, nodos, m):
        """Une los nodos con el mínimo de tramos rectos o a 45° que quepan en la máscara m."""
        out = [nodos[0]]
        i, n = 0, len(nodos) - 1
        while i < n:
            j = n
            while True:
                hecho = None
                for diag in (True, False):
                    celdas, esquina = self._linea_octil(nodos[i], nodos[j], diag)
                    if self._libre_linea(m, celdas):
                        hecho = esquina
                        break
                else:
                    if j > i + 1:
                        j = i + max(1, (j - i) // 2)
                        continue
                    hecho = None
                break
            if hecho is not None:
                out.append(hecho)
            out.append(nodos[j])
            i = j
        return out

    def _tramos_capa(self, l, celdas, w, libre_full, lib_ok):
        """Tramos de una capa: se separan los de ancho completo y los estrechos y cada parte
        se simplifica a rectas y 45°."""
        clase = [bool(libre_full[l, j, i]) for j, i in celdas]
        # Sin parpadeo: los tramos de ancho completo de menos de 8 celdas pasan a estrechos
        # (estrechar siempre es seguro) y así no salen trocitos alternos.
        k = 0
        while k < len(clase):
            if clase[k]:
                f = k
                while f < len(clase) and clase[f]:
                    f += 1
                if f - k < 8 and not (k == 0 and f == len(clase)):
                    for q in range(k, f):
                        clase[q] = False
                k = f
            else:
                k += 1
        partes, ini = [], 0
        for k in range(1, len(celdas) + 1):
            if k == len(celdas) or clase[k] != clase[ini]:
                # la frontera se comparte para que los tramos queden unidos
                partes.append((celdas[ini:k + 1] if k < len(celdas) else celdas[ini:k], clase[ini]))
                ini = k
        tramos = []
        n_antes = 0
        for parte, completo in partes:
            if len(parte) < 2:
                continue
            ancho = w if completo else min(w, ANCHO_SALIDA)
            if completo:
                m = libre_full[l]
            else:
                # atajos solo por celdas libres; las del camino original (p. ej. dentro del pad
                # propio) se conservan tal cual
                m = (lib_ok[l] & self._libre_actual[l]).copy()
                for j, i in parte:
                    m[j, i] = True
            vert = self._simplifica(parte, m)
            for a, b in zip(vert, vert[1:]):
                if a != b:
                    tramos.append((l, self.xy(*a), self.xy(*b), ancho))
        # Un remate de una celda al principio o al final del tramo sobra: el extremo ya cae
        # dentro del cobre (pista, pad o vía) al que se une.
        if len(tramos) >= 2 and math.dist(tramos[0][1], tramos[0][2]) < 0.08:
            tramos.pop(0)
        if len(tramos) >= 2 and math.dist(tramos[-1][1], tramos[-1][2]) < 0.08:
            tramos.pop()
        return tramos

    def camino_a_cobre(self, camino, n, w, libre_full, lib_ok, via_final=False, centros=None):
        """Celdas -> tramos rectos o a 45° con el mínimo de vértices, y vías; los pinta.

        centros: {(capa, j, i) de pad -> celda del centro del pad}, para entrar centrado."""
        tramos, vias = [], []
        if via_final:
            l, j, i = camino[-1]
            vias.append(self.xy(j, i))
        runs, actual = [], [camino[0]]
        for a, b in zip(camino, camino[1:]):
            if a[0] != b[0]:
                vias.append(self.xy(a[1], a[2]))
                runs.append(actual)
                actual = [b]
            else:
                actual.append(b)
        runs.append(actual)
        for k, run in enumerate(runs):
            l = run[0][0]
            celdas = [(j, i) for _, j, i in run]
            if centros:
                # entrada por el centro del pad, solo si cabe en recto o a 45°
                m_ok = lib_ok[l] & self._angosto[l]
                if k == 0 and run[0] in centros and centros[run[0]] != celdas[0]:
                    c = centros[run[0]]
                    linea, _ = self._linea_octil(c, celdas[0], True)
                    if self._en_linea(linea, celdas[0]) and self._libre_linea(m_ok | self._pad_de(run[0]), linea):
                        celdas = [c] + celdas
                if k == len(runs) - 1 and run[-1] in centros and centros[run[-1]] != celdas[-1]:
                    c = centros[run[-1]]
                    linea, _ = self._linea_octil(celdas[-1], c, True)
                    if self._en_linea(linea, c) and self._libre_linea(m_ok | self._pad_de(run[-1]), linea):
                        celdas = celdas + [c]
            if len(celdas) >= 2:
                tramos += self._tramos_capa(l, celdas, w, libre_full, lib_ok)
        tramos = self._fusiona(tramos)
        fijo = getattr(self, "_fijo", False)
        for l, pa, pb, ancho in tramos:
            self.pinta_segmento(l, pa, pb, ancho, n)
            if not fijo:
                self.pinta_segmento(l, pa, pb, ancho, n, self.lab_pistas)
            self.pistas_nuevas.append({"red": self.redes[n], "capa": CAPAS[l], "w": ancho, "a": pa, "b": pb,
                                       "fija": fijo})
        for v in vias:
            self.pinta_via(v, self.reglas["via_d"], n)
            if not fijo:
                self.pinta_via(v, self.reglas["via_d"], n, self.lab_pistas)
            self.agujeros |= self.disco(v[0], v[1], self.reglas["via_taladro"] / 2)
            self.vias_nuevas.append({"red": self.redes[n], "pos": v, "fija": fijo})
        if vias:
            self.d_agujeros = self.edt(self.agujeros)
        return len(tramos), len(vias)

    @staticmethod
    def _en_linea(linea, fin):
        """El camino octilineal es una sola recta (sin esquina) que acaba en fin."""
        if not linea:
            return False
        pasos = {(b[0] - a[0], b[1] - a[1]) for a, b in linea}
        return len(pasos) == 1 and tuple(linea[-1][1]) == tuple(fin)

    def _pad_de(self, celda):
        m = np.zeros((self.H, self.W), dtype=bool)
        for p, celdas in self.pad_celdas:
            for l, mm in celdas:
                if l == celda[0] and mm[celda[1], celda[2]]:
                    return mm.astype(bool)
        return m

    @staticmethod
    def _fusiona(tramos):
        """Une tramos seguidos de la misma capa, ancho y dirección; quita los de longitud nula."""
        out = []
        for t in tramos:
            l, a, b, w = t
            if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
                continue
            if out:
                l0, a0, b0, w0 = out[-1]
                if l0 == l and w0 == w and abs(b0[0] - a[0]) < 1e-6 and abs(b0[1] - a[1]) < 1e-6:
                    d0 = (b0[0] - a0[0], b0[1] - a0[1])
                    d1 = (b[0] - a[0], b[1] - a[1])
                    if abs(d0[0] * d1[1] - d0[1] * d1[0]) < 1e-9 and d0[0] * d1[0] + d0[1] * d1[1] > 0:
                        out[-1] = (l, a0, b, w)
                        continue
            out.append(t)
        # Escalones de una celda entre dos tramos: se absorben en el tramo siguiente (que
        # cambia de ángulo menos de 1° en tramos de más de 3 mm; el margen de 0,09 lo cubre).
        k = 1
        while k < len(out) - 1:
            l, a, b, w = out[k]
            lp, ap, bp, wp = out[k - 1]
            ln, an, bn, wn = out[k + 1]
            corto = math.dist(a, b) < 0.12
            seguido = (lp == l == ln and math.dist(bp, a) < 1e-6 and math.dist(b, an) < 1e-6)
            if corto and seguido and math.dist(an, bn) > 3.0:
                out[k + 1] = (ln, a, bn, wn)
                out.pop(k)
                continue
            k += 1
        return out

    def _centros(self, pads):
        """Para cada celda de un pad de la red, la celda de su centro (para entrar centrado)."""
        out = {}
        for p, celdas in pads:
            cj, ci = self.celda(*p["pos"])
            for l, m in celdas:
                if not m[cj, ci]:
                    continue
                for j, i in zip(*np.nonzero(m)):
                    out[(l, j, i)] = (cj, ci)
        return out

    def colocar_tps(self):
        """Un TP por fuente: vía junto al pad (sin entrar en él) con el pad del TP en B.Cu."""
        self._fijo = True
        self.tps = {}
        self.reserva_tp = np.zeros((self.H, self.W), dtype=bool)
        silk = np.zeros((self.H, self.W), dtype=np.uint8)
        for x0, y0, x1, y1 in self.geo.get("silk_b", []):
            silk |= self.poly_mask([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        self.d_silk_b = self.edt(silk)
        hol = self.reglas["holgura"]
        lim = lambda r: (r / G) ** 2
        for tp, (ref, num) in FUENTES_TP.items():
            pad = [(p, c) for p, c in self.pad_celdas if p["ref"] == ref and p["num"] == num]
            if not pad:
                continue
            p, celdas = pad[0]
            n = self.nid[p["red"]]
            w = self.ancho[p["red"]]
            libre, estrecho, via_ok = self.mascaras(n, w, [])
            d_b = self.edt(((self.lab[2] >= 0) & (self.lab[2] != n)) | (self.lab[2] == -3))
            sitio = (via_ok & self.lejos_pads & (d_b >= lim(R_TP + hol + MARGEN))
                     & (self.d_borde >= lim(self.reglas["borde"] + R_TP + MARGEN))
                     & (self.d_silk_b >= lim(R_TP + 0.2)) & ~self.reserva_tp)
            m = [mm for l, mm in celdas if l == 0]
            if not m:
                continue
            m = m[0]
            objetivo = np.zeros((3, self.H, self.W), dtype=bool)
            objetivo[0] = sitio
            js, is_ = np.nonzero(m)
            cx, cy = int(is_.mean()), int(js.mean())
            caja = (max(0, cx - 80), max(0, cy - 80), min(self.W, cx + 81), min(self.H, cy + 81))
            lib_o = libre.copy()
            lib_o[0] |= m.astype(bool)
            camino = self.astar(lib_o, np.zeros_like(via_ok), objetivo, [(0, j, i) for j, i in zip(js, is_)],
                                caja, solo_capas=[0])
            if camino is None:
                continue
            self._libre_actual = libre
            self.camino_a_cobre(camino, n, min(w, 0.3), libre & ~estrecho, lib_o, via_final=True,
                                centros=self._centros([(p, celdas)]))
            pos = self.xy(camino[-1][1], camino[-1][2])
            i0, j0, i1, j1 = self.ventana(pos[0], pos[1], pos[0], pos[1], R_TP)
            X, Y = self.XX[j0:j1, i0:i1], self.YY[j0:j1, i0:i1]
            sub = self.lab[2, j0:j1, i0:i1]
            sub[((X - pos[0]) ** 2 + (Y - pos[1]) ** 2 <= R_TP ** 2) & (sub == -1)] = n
            self.tps[tp] = pos
            # el siguiente TP, a 2,8 mm o más (courtyard de 2,6 y su anillo de serigrafía)
            self.reserva_tp |= self.disco(pos[0], pos[1], 2.8).astype(bool)
        self._fijo = False
        self.lab_base = self.lab.copy()
        self.agujeros_base = self.agujeros.copy()

    def levantar(self, redes):
        """Quita el cobre rutado (no fijo) de esas redes y repinta lo demás."""
        redes = set(redes)
        self.pistas_nuevas = [t for t in self.pistas_nuevas if t["fija"] or t["red"] not in redes]
        self.vias_nuevas = [v for v in self.vias_nuevas if v["fija"] or v["red"] not in redes]
        self.lab = self.lab_base.copy()
        self.lab_pistas[:] = -1
        self.agujeros = self.agujeros_base.copy()
        for t in self.pistas_nuevas:
            if not t["fija"]:
                n = self.nid[t["red"]]
                l = CAPAS.index(t["capa"])
                self.pinta_segmento(l, t["a"], t["b"], t["w"], n)
                self.pinta_segmento(l, t["a"], t["b"], t["w"], n, self.lab_pistas)
        for v in self.vias_nuevas:
            if not v["fija"]:
                n = self.nid[v["red"]]
                self.pinta_via(v["pos"], self.reglas["via_d"], n)
                self.pinta_via(v["pos"], self.reglas["via_d"], n, self.lab_pistas)
                self.agujeros |= self.disco(v["pos"][0], v["pos"][1], self.reglas["via_taladro"] / 2)
        self.d_agujeros = self.edt(self.agujeros)

    def bloqueadores(self, n, w, objetivo, fuentes, caja, via_ok):
        """Camino con el cobre levantable permitido (más caro): redes que estorban."""
        hol, borde = self.reglas["holgura"], self.reglas["borde"]
        lim = lambda r: (r / G) ** 2
        coste = np.zeros((3, self.H, self.W), dtype=np.uint8)
        for l in range(3):
            duro = ((self.lab_base[l] >= 0) & (self.lab_base[l] != n)) | (self.lab_base[l] == -3)
            dd = self.edt(duro)
            ok_duro = ((dd >= lim(hol + w / 2 + MARGEN)) & (self.d_borde >= lim(borde + w / 2 + MARGEN))
                       & (self.d_ko[l] >= lim(w / 2 + MARGEN)))
            coste[l][ok_duro] = 8
        coste[self._libre_ultimo] = 1
        coste[objetivo] = np.maximum(coste[objetivo], 1)
        lib8 = coste
        camino = self.astar_coste(lib8, via_ok, objetivo, fuentes, caja)
        if camino is None:
            return set()
        radio = int((hol + 0.5) / G) + 1
        red_ids = set()
        for l, j, i in camino:
            if lib8[l, j, i] > 1:
                sub = self.lab_pistas[l, max(0, j - radio):j + radio + 1, max(0, i - radio):i + radio + 1]
                red_ids |= set(int(v) for v in np.unique(sub) if v >= 0 and v != n)
        return {self.redes[k] for k in red_ids}

    def astar_coste(self, coste, via_ok, objetivo, fuentes, caja):
        lib8 = np.ascontiguousarray(coste, dtype=np.uint8)
        via8 = np.ascontiguousarray(via_ok, dtype=np.uint8)
        obj8 = np.ascontiguousarray(objetivo, dtype=np.uint8)
        f = np.ascontiguousarray(np.array(fuentes, dtype=np.int32).ravel())
        cc = np.array(COSTE_CAPA, dtype=np.int32)
        tj, ti = np.nonzero(objetivo.any(axis=0))
        x0, y0, x1, y1 = caja
        out = np.zeros(200000 * 3, dtype=np.int32)
        k = self.lib.astar(self.W, self.H, 3, ptr(lib8, ctypes.c_uint8), ptr(via8, ctypes.c_uint8),
                           ptr(obj8, ctypes.c_uint8), ptr(f, ctypes.c_int32), len(fuentes), COSTE_VIA,
                           ptr(cc, ctypes.c_int32), x0, y0, x1, y1, int(ti.min()), int(tj.min()),
                           int(ti.max()), int(tj.max()), ptr(out, ctypes.c_int32), 200000)
        return None if k <= 0 else [tuple(out[3 * q:3 * q + 3]) for q in range(k)][::-1]

    def pads_de(self, red):
        return [(p, c) for p, c in self.pad_celdas if p["red"] == red]

    def rutar_red(self, red):
        n = self.nid[red]
        w = self.ancho[red]
        pads = self.pads_de(red)
        pads_red = [(l, m) for _, celdas in pads for l, m in celdas]
        libre, estrecho, via_ok = self.mascaras(n, w, pads_red)
        if red == "GND":
            return self.rutar_gnd(pads, libre, estrecho, via_ok, n, w)
        # grupos ya unidos por cobre fijo de la red: se tratan como un árbol inicial
        arbol = np.zeros((3, self.H, self.W), dtype=bool)
        arbol |= (self.lab == n) & ~self._celdas_pads(pads)
        pend = list(pads)
        if not arbol.any():
            p0 = pend.pop(0)
            for l, m in p0[1]:
                arbol[l] |= m
        else:
            # quita los pads que ya tocan el cobre fijo
            pend = [p for p in pend if not any((arbol[l] & m).any() for l, m in p[1])]
            if len(pend) == len(pads):
                p0 = pend.pop(0)
                for l, m in p0[1]:
                    arbol[l] |= m
        fallos = 0
        centros = self._centros(pads)
        while pend:
            objetivo = np.zeros_like(arbol)
            for p, celdas in pend:
                for l, m in celdas:
                    objetivo[l] |= self._celdas_utiles(l, m, p)
            pads_utiles = np.zeros_like(arbol)
            for p, celdas in pads:
                for l, m in celdas:
                    pads_utiles[l] |= self._celdas_utiles(l, m, p)
            ls, js, is_ = np.nonzero(arbol & libre | arbol & pads_utiles)
            fuentes = list(zip(ls, js, is_))
            if not fuentes:
                return False
            # ventana: caja de árbol + objetivos, ampliada; si falla, toda la placa
            tj, ti = np.nonzero(objetivo.any(axis=0))
            aj, ai = js, is_
            caja = (max(0, min(ti.min(), ai.min()) - 120), max(0, min(tj.min(), aj.min()) - 120),
                    min(self.W, max(ti.max(), ai.max()) + 121), min(self.H, max(tj.max(), aj.max()) + 121))
            lib_o = libre | objetivo | (arbol & ~self._celdas_pads(pads)) | (arbol & pads_utiles)
            camino = self.astar(lib_o, via_ok, objetivo, fuentes, caja)
            if camino is None:
                camino = self.astar(lib_o, via_ok, objetivo, fuentes, (0, 0, self.W, self.H))
            if camino is None:
                fallos += 1
                self._libre_ultimo = lib_o
                self.bloqueos[red] = self.bloqueadores(n, w, objetivo, fuentes, (0, 0, self.W, self.H), via_ok)
                break
            antes = self.lab == n
            self._libre_actual = libre
            self.camino_a_cobre(camino, n, w, libre & ~estrecho, lib_o, centros=centros)
            arbol |= (self.lab == n) & ~antes          # solo el cobre recién pintado
            fin = camino[-1]
            for k, (p, celdas) in enumerate(pend):
                if any(l == fin[0] and m[fin[1], fin[2]] for l, m in celdas):
                    for l, m in celdas:
                        arbol[l] |= m
                    pend.pop(k)
                    break
            libre, estrecho, via_ok = self.mascaras(n, w, pads_red)
        return fallos == 0

    def _celdas_utiles(self, l, m, p):
        """Celdas del pad por las que puede pasar una pista estrecha; si ninguna, su centro."""
        u = m & self._angosto[l]
        if u.any():
            return u
        u = np.zeros_like(m)
        cj, ci = self.celda(*p["pos"])
        u[cj, ci] = True
        return u

    def _celdas_pads(self, pads):
        m = np.zeros((3, self.H, self.W), dtype=bool)
        for _, celdas in pads:
            for l, mm in celdas:
                m[l] |= mm
        return m

    def _todas_pads_mask(self, pads):
        return self._celdas_pads(pads)

    def rutar_gnd(self, pads, libre, estrecho, via_ok, n, w):
        """Cada pad SMD de GND en F.Cu baja al plano con una vía cercana."""
        ok = True
        for p, celdas in pads:
            if p["agujero"]:
                continue        # los pasantes ya tocan el plano
            if not any(l == 0 for l, _ in celdas):
                continue
            m = [mm for l, mm in celdas if l == 0][0]
            # ¿ya hay una vía de GND dentro del pad o pegada a él? (de otro pad vecino no cuenta)
            js, is_ = np.nonzero(m)
            objetivo = np.zeros((3, self.H, self.W), dtype=bool)
            objetivo[0] = via_ok & self.lejos_pads       # nunca vía en pad
            fuentes = [(0, j, i) for j, i in zip(js, is_)]
            cx, cy = int(is_.mean()), int(js.mean())
            caja = (max(0, cx - 50), max(0, cy - 50), min(self.W, cx + 51), min(self.H, cy + 51))
            lib_o = libre.copy()
            lib_o[0] |= m.astype(bool)
            camino = self.astar(lib_o, np.zeros_like(via_ok), objetivo, fuentes, caja, solo_capas=[0])
            if camino is None:
                ok = False
                p["sin_via"] = True
                continue
            self._libre_actual = libre
            self.camino_a_cobre(camino, n, max(w, 0.3), libre & ~estrecho, lib_o, via_final=True,
                                centros=self._centros([(p, celdas)]))
            libre, estrecho, via_ok = self.mascaras(n, w, [])
        return ok


# Dentro del bloque de potencia, primero las redes de control de cada convertidor (salen de
# pines finos y se quedarían encerradas por las pistas anchas), luego la potencia.
CONTROL = ["BST_FSW", "BST_VCC", "BST_FB", "BST_COMP", "BST_RC", "BST_ILIM", "BST_BOOT", "EN_6V", "BB_FB",
           "BQ_TS", "BQ_ISET", "BQ_ILIM", "BQ_EN1", "BQ_EN2", "BAT_G", "MOT_VREF", "IPROPI", "MOT_IN1", "MOT_IN2"]
POTENCIA = ["VBUS_IN", "VBUS", "BAT", "BAT_PAD", "VSYS", "BST_SW", "V6", "BB_L1", "BB_L2", "MOT_OUT1",
            "MOT_OUT2", "SPK_P", "SPK_N", "IR_LED_A", "IR_LED_K", "3V3"]
USB = ["USB_DP", "USB_DN", "CC1", "CC2"]
I2S = ["I2S_BCLK", "I2S_WS", "I2S_DOUT", "I2S_DIN", "MIC_SCK", "MIC_WS"]


def orden_por_bloques(redes):
    redes = [r for r in redes if r and not r.startswith("unconnected")]
    camara = [r for r in redes if r.startswith("CAM_")] + ["I2C_SDA", "I2C_SCL"]
    primero = CONTROL + POTENCIA + ["GND"] + USB + I2S + camara
    return [r for r in primero if r in redes] + [r for r in redes if r not in primero]


def una_vuelta(geo, lib, redes, verboso=False):
    rj = Rejilla(geo, lib)
    rj.colocar_tps()
    hechas, fallidas = [], []
    for red in redes:
        if red not in rj.nid or (len(rj.pads_de(red)) < 2 and red != "GND"):
            continue
        t1 = time.time()
        ok = rj.rutar_red(red)
        (hechas if ok else fallidas).append(red)
        if verboso:
            print("%-14s %s  %.1f s" % (red, "ok" if ok else "FALLA", time.time() - t1), flush=True)
    fallidas = levantar_y_rerutar(rj, fallidas, redes)
    hechas = [r for r in hechas if r not in fallidas]
    return rj, hechas, fallidas


def levantar_y_rerutar(rj, fallidas, orden, rondas=4, intentos=40):
    """Para cada red que falla: se levantan las redes que le estorban, se ruta ella y
    luego se vuelven a rutar las levantadas. Se acepta si al final fallan menos redes."""
    fallidas = [r for r in fallidas if r != "GND"]
    gnd_falla = "GND" in set(fallidas)
    n_int = 0
    for ronda in range(rondas):
        mejora = False
        for red in list(fallidas):
            if n_int >= intentos:
                break
            bloq = rj.bloqueos.get(red, set()) - {"GND", red}
            if not bloq or len(bloq) > 6:
                continue
            n_int += 1
            copia = (list(rj.pistas_nuevas), list(rj.vias_nuevas))
            rj.levantar(bloq | {red})
            nuevas = []
            for r in [red] + sorted(bloq, key=orden.index):
                if not rj.rutar_red(r):
                    nuevas.append(r)
            antes = len(fallidas)
            resto = [r for r in fallidas if r != red]
            if len(resto) + len(nuevas) < antes:
                fallidas = resto + nuevas
                mejora = True
            else:
                rj.pistas_nuevas, rj.vias_nuevas = copia
                rj.levantar(set())
        if not mejora:
            break
    return fallidas + (["GND"] if gnd_falla else [])


def main():
    geo = json.load(open(sys.argv[1]))
    salida = sys.argv[2]
    vueltas = int(sys.argv[sys.argv.index("--vueltas") + 1]) if "--vueltas" in sys.argv else 6
    lib = compilar()
    orden = json.load(open(sys.argv[sys.argv.index("--orden") + 1])) if "--orden" in sys.argv else None
    redes = orden or orden_por_bloques(sorted(geo["anchos"]))
    mejor = None
    for v in range(vueltas):
        t0 = time.time()
        rj, hechas, fallidas = una_vuelta(geo, lib, redes)
        sin_via = [p["ref"] + "." + p["num"] for p, _ in rj.pad_celdas if p.get("sin_via")]
        print("vuelta %d: %d redes, fallan %d (%s); GND sin vía: %d  [%.0f s]"
              % (v, len(hechas) + len(fallidas), len(fallidas), ", ".join(fallidas), len(sin_via),
                 time.time() - t0), flush=True)
        if mejor is None or len(fallidas) < len(mejor[2]):
            mejor = (rj, hechas, fallidas, sin_via)
        if not fallidas:
            break
        # Las que fallan pasan delante (respetando que la potencia vaya primero)
        redes = [r for r in fallidas if r in CONTROL + POTENCIA] + \
                [r for r in redes if r in CONTROL + POTENCIA and r not in fallidas] + \
                [r for r in fallidas if r not in CONTROL + POTENCIA] + \
                [r for r in redes if r not in CONTROL + POTENCIA and r not in fallidas]
    rj, hechas, fallidas, sin_via = mejor
    json.dump({"pistas": rj.pistas_nuevas, "vias": rj.vias_nuevas, "fallidas": fallidas, "tps": rj.tps,
               "gnd_sin_via": sin_via, "orden": redes}, open(salida, "w"))
    print("Mejor: fallan %d: %s" % (len(fallidas), ", ".join(fallidas)))


if __name__ == "__main__":
    main()
