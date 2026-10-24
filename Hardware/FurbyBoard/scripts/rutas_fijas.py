"""Rutas explícitas de la FurbyBoard (coordenadas del STL, mm), bloqueadas en el PCB.

Encargo 4 (rutado, 2026-10-24): todo lo crítico va aquí escrito a mano, por bloques y en el
orden de layout-pcb.md §13: lazos de potencia (U2, U3, U5, U6, U7) y raíles → par USB → DVP →
I2S → sensado (clase D) → escapes de los pines finos. Lo lento que queda lo remata Freerouting
sobre estas pistas bloqueadas (una ejecución acotada) y el resultado pasa por limpiar-pistas.

Sintaxis (gen_pcb.rutas_fijas resuelve los pads con las posiciones reales de la placa):
    pista(red, capa, ancho, p0, p1, ..., modo="s")
        p = (x, y) | "REF.PAD" | ("REF.PAD", dx, dy)
        Entre dos puntos no alineados a 0/45/90 se mete un codo a 45°: modo "s" = recto
        primero y diagonal al final; "d" = diagonal primero. Un codo por tramo; para
        trayectorias largas se dan los vértices.
    via(red, p, tam=VIA)              VIA = 0,6/0,3; VIA_USB = 0,45/0,2 (solo la clase USB)
    stub(red, "REF.PAD", (dx, dy), ancho, tam=VIA)   pista corta pad -> vía en pad+(dx, dy)
Cada pista comprueba que la red de los pads que toca es la suya.
"""

VIA = (0.6, 0.3)
VIA_USB = (0.45, 0.2)

PISTAS = []   # (red, capa, ancho, [puntos], modo)
VIAS = []     # (red, punto, (diámetro, taladro))
ZONAS = []    # (red, capa, [puntos], clearance, prioridad): polígonos de potencia (conexión sólida)


def pista(red, capa, ancho, *puntos, modo="s"):
    PISTAS.append((red, capa, ancho, list(puntos), modo))


def via(red, p, tam=VIA):
    VIAS.append((red, p, tam))


def zona(red, capa, puntos, clearance=0.2, prioridad=2):
    """Polígono de cobre de una red de potencia (> 1,5 A: layout-pcb.md §5.1), con conexión sólida
    a sus pads; prioridad por encima del relleno de GND de la cara."""
    ZONAS.append((red, capa, list(puntos), clearance, prioridad))


def stub(red, pad, d, ancho, tam=VIA, capa="F.Cu"):
    pista(red, capa, ancho, pad, (pad, d[0], d[1]))
    via(red, (pad, d[0], d[1]), tam)


def codo(a, b, modo):
    """Vértice intermedio que une a y b con un tramo recto y uno a 45° (o nada si ya están alineados)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    ax, ay = abs(dx), abs(dy)
    # Alineados (o a 45°) salvo por el redondeo de los pads: sin codo (queda dentro de 0,5°)
    if ax < 0.02 or ay < 0.02 or abs(ax - ay) < 0.02:
        return None
    sx, sy = (1 if dx > 0 else -1), (1 if dy > 0 else -1)
    if ax > ay:
        rem = ax - ay
        return (a[0] + sx * rem, a[1]) if modo == "s" else (a[0] + sx * ay, b[1])
    rem = ay - ax
    return (a[0], a[1] + sy * rem) if modo == "s" else (b[0], a[1] + sy * ax)


def resolver(p, pad_xy):
    if isinstance(p, str):
        return pad_xy(p)
    if isinstance(p, tuple) and len(p) == 3 and isinstance(p[0], str):
        x, y = pad_xy(p[0])
        return (x + p[1], y + p[2])
    return (float(p[0]), float(p[1]))


def rutas(pad_xy):
    """Devuelve (pistas, vias) con coordenadas resueltas: pistas = [(red, capa, ancho, [(x, y), ...])]."""
    out_p = []
    for red, capa, ancho, puntos, modo in PISTAS:
        pts = [resolver(p, pad_xy) for p in puntos]
        expandido = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            c = codo(a, b, modo)
            if c is not None:
                expandido.append(c)
            expandido.append(b)
        out_p.append((red, capa, ancho, expandido))
    out_v = [(red, resolver(p, pad_xy), tam) for red, p, tam in VIAS]
    return out_p, out_v


# ============================================================================ bloques
# Nota de geometría: los pads de 0805/0603 girados 90/270 tienen el lado largo en x (C16, C20, C7,
# C8, C24: 1,45 x 1,0; L1/L2: 3,5 x 1,6). Tramos >= 2 x ancho (revisar-rutado).
# ---------------------------------------------------------------- elevador de 6 V (TPS61089)
# Lazo de salida en F.Cu: pin 6 (VOUT) -> C18.1 y pin 5 (GND) -> C18.2 (C18 a 180°: V6 al este,
# GND al oeste; sin cruce ni vías dentro del lazo). SW: pad de L2, pad 11 y los stubs de C13 y RFSW.
# VSYS entra en C16.1 desde dos vías al este del pad (pin 9 con cuello de 0,25 de 1 mm). ILIM pasa
# entre los pads de C16 y EN_6V baja entre C18.1 y C16.2 hasta una vía (sigue por In2 a R25).
# Columna oeste (x -53,8): C12 (VCC), R22 (FB), C15 (COMP), R24 (COMP->RC) en filas de 1,6 mm con
# las pistas FSW (y -113,8), FB (y -115,4) y COMP (y -117,0) entre ellas; GND a vías en x -55,55.
pista("BST_SW", "F.Cu", 0.8, "U5.11", "L2.2")
pista("BST_SW", "F.Cu", 0.8, "C13.2", (-49.2, -112.15))
pista("BST_SW", "F.Cu", 0.8, "R20.2", (-58.13, -112.2), (-50.9, -112.2))
pista("BST_BOOT", "F.Cu", 0.25, "U5.10", (-49.33, -113.7), "C13.1")
pista("BST_FSW", "F.Cu", 0.25, "U5.1", (-51.675, -113.75), "R20.1")
pista("BST_VCC", "F.Cu", 0.25, "U5.2", (-52.355, -115.25), "C12.1")
pista("BST_FB", "F.Cu", 0.25, "U5.3", (-52.51, -115.75), "R22.1")
pista("BST_FB", "F.Cu", 0.25, "R22.1", (-52.98, -115.39), "R21.2")
pista("BST_COMP", "F.Cu", 0.25, "U5.4", (-52.25, -116.25), (-52.25, -116.99), "C15.1")
pista("BST_COMP", "F.Cu", 0.25, "C15.1", "R24.1")
pista("BST_RC", "F.Cu", 0.25, "R24.2", (-55.45, -118.6), "C14.1")
pista("V6", "F.Cu", 0.5, "U5.6", (-50.15, -117.39), "C18.1")
pista("GND", "F.Cu", 0.25, "U5.5", (-50.85, -116.7), (-51.34, -117.19), "C18.2")
pista("GND", "F.Cu", 0.35, "C18.2", (-51.34, -119.3))
via("GND", (-51.34, -119.3))
via("VSYS", (-46.25, -115.25))
via("VSYS", (-46.25, -114.05))
pista("VSYS", "F.Cu", 0.6, (-46.25, -114.05), (-46.25, -115.25), (-48.33, -115.25))
pista("VSYS", "F.Cu", 0.25, "U5.9", (-48.33, -115.25))
pista("GND", "F.Cu", 0.4, "C16.2", (-46.1, -117.15))
via("GND", (-46.1, -117.15))
pista("GND", "F.Cu", 0.6, "C16.2", (-47.3, -118.4))
via("GND", (-47.3, -118.4))
pista("EN_6V", "F.Cu", 0.25, "U5.7", (-49.33, -117.0), (-48.49, -117.0), (-48.49, -119.35))
via("EN_6V", (-48.49, -119.35))
pista("BST_ILIM", "F.Cu", 0.25, "U5.8", (-48.83, -115.75), (-48.38, -116.2), "R23.1")
# V6: vía junto a C18.1; por B.Cu, toma Kelvin hacia R21 (TP7 sobre esa pista) y tronco al puente H
via("V6", (-49.44, -119.5))
pista("V6", "F.Cu", 0.5, "C18.1", (-49.44, -119.5))
pista("V6", "B.Cu", 0.5, (-49.44, -119.5), (-50.94, -118.0), (-56.96, -118.0), (-57.9, -117.06))
via("V6", (-57.9, -117.06))
pista("V6", "F.Cu", 0.5, (-57.9, -117.06), "R21.1")
pista("V6", "B.Cu", 0.5, (-49.44, -119.5), (-49.44, -108.0), (-49.44, -107.85), (-49.0, -107.41), (-46.55, -107.41))
via("V6", (-46.55, -107.41))
# EN_6V sigue por In2 hasta R25 (pull-down); de ahí a U10 lo remata el autorrutado
pista("EN_6V", "In2.Cu", 0.2, (-48.49, -119.35), (-52.54, -115.3), (-61.22, -115.3))
via("EN_6V", (-61.22, -115.3))
pista("EN_6V", "F.Cu", 0.2, (-61.22, -115.3), "R25.1")
# GND de la columna oeste: vías en el hueco entre columnas (x -55,55)
pista("GND", "F.Cu", 0.3, "C12.2", (-55.55, -114.58))
via("GND", (-55.55, -114.58))
pista("GND", "F.Cu", 0.35, "R22.2", "C15.2")
pista("GND", "F.Cu", 0.3, (-54.62, -117.1), (-55.55, -117.1))
via("GND", (-55.55, -117.1))
stub("GND", "C14.2", (-0.97, 0.0), 0.3)
stub("GND", "R23.2", (0.9, 0.0), 0.3)
# ---------------------------------------------------------------- V6 hacia el puente H y el LED del encoder
# Tronco F.Cu por y -105,4 (C19.1, C21.1, U6.5) hasta la vertical x -46,8 que une C22.1 y C20.1;
# en esa vertical, la vía del tronco de B.Cu (desde C18) y la vía del ramal de B.Cu a R51 (junto a J9).
pista("V6", "F.Cu", 0.5, "C22.1", "C20.1")
via("V6", (-46.55, -106.3))
pista("V6", "B.Cu", 0.5, (-46.55, -106.3), (-45.8, -105.55), (-45.8, -89.6))
via("V6", (-45.8, -89.6))
pista("V6", "F.Cu", 0.5, (-45.8, -89.6), "R51.1")
# ---------------------------------------------------------------- buck-boost de 3,3 V (TPS63802)
# Cin (C6) sobre VIN (pines 1/10) con dos vías de VSYS; L1 al este con los nodos SW de 0,6; Cout
# (C7) bajo VOUT (pin 6) y C8 en paralelo; FB (R16/R15) al oeste. GND de los pines 2/3/8 unidos
# bajo el chip y a una vía; toma Kelvin de 3V3 para R15 desde el pad de C7 por B.Cu.
pista("BB_SW1", "F.Cu", 0.3, "U3.9", (-88.25, -102.3))
pista("BB_SW1", "F.Cu", 0.6, (-88.25, -102.3), (-87.4, -101.45), (-86.2, -101.45))
pista("BB_SW2", "F.Cu", 0.3, "U3.7", (-88.25, -103.3))
pista("BB_SW2", "F.Cu", 0.6, (-88.25, -103.3), (-87.4, -104.15), (-86.2, -104.15))
pista("VSYS", "F.Cu", 0.3, "U3.10", (-89.17, -100.82))
pista("VSYS", "F.Cu", 0.6, (-89.17, -100.82), "C6.1")
pista("VSYS", "F.Cu", 0.6, (-89.17, -100.14), (-90.37, -100.14))
via("VSYS", (-89.77, -100.14))
via("VSYS", (-90.37, -100.14))
pista("VSYS", "F.Cu", 0.3, "U3.1", (-90.37, -101.345))
pista("VSYS", "F.Cu", 0.6, (-90.37, -101.345), (-90.37, -100.14))
pista("GND", "F.Cu", 0.25, "U3.2", (-91.55, -102.3))
pista("GND", "F.Cu", 0.25, "U3.3", (-91.55, -102.8), (-91.55, -102.3))
via("GND", (-91.55, -102.55))
pista("GND", "F.Cu", 0.25, "U3.3", "U3.8")
stub("GND", "C6.2", (0.0, 0.925), 0.4)
stub("GND", "C7.2", (0.0, -0.95), 0.4)
stub("GND", "C8.2", (0.0, -0.95), 0.4)
stub("GND", "R16.2", (0.0, 0.955), 0.3)
pista("BB_FB", "F.Cu", 0.25, "U3.4", "R16.1")
pista("BB_FB", "F.Cu", 0.25, "R16.1", "R15.2")
pista("3V3", "F.Cu", 0.3, "U3.6", (-89.17, -104.6))
pista("3V3", "F.Cu", 0.4, (-89.17, -104.6), "C7.1")
pista("3V3", "F.Cu", 0.4, "C7.1", (-87.6, -105.45), "C8.1")
pista("3V3", "F.Cu", 0.4, "C8.1", (-85.5, -106.45))
via("3V3", (-85.5, -106.45))
pista("3V3", "F.Cu", 0.4, (-85.5, -106.45), (-85.5, -107.3))
via("3V3", (-85.5, -107.3))
pista("3V3", "F.Cu", 0.4, "C7.1", (-90.6, -105.45))
via("3V3", (-90.6, -105.45))
pista("3V3", "B.Cu", 0.4, (-90.6, -105.45), (-93.5, -105.45), (-93.5, -103.45), (-95.3, -101.65))
via("3V3", (-95.3, -101.65))
pista("3V3", "F.Cu", 0.4, (-95.3, -101.65), "R15.1")
# ---------------------------------------------------------------- tronco de 3V3 por B.Cu (x -85,5)
# De las vías de C8 al módulo (C9/C10 y pin 2) por el canal; ramales: U10 y pull-ups (fila F y -76,6
# para C32/R36; fila B y -74,75 para R37/R38 y J7.5); J11.2 y J5.5 (fila y -98,24 y columna x -104,07
# entre los pads); lado este (y -103,0) para R26, R52, U11, C39, C27 y U8.
pista("3V3", "B.Cu", 0.4, (-85.5, -107.3), (-85.5, -70.95))
via("3V3", (-85.5, -70.95))
pista("3V3", "F.Cu", 0.4, (-85.5, -70.95), "C9.1")
pista("3V3", "F.Cu", 0.4, "C9.1", (-83.2, -69.85), (-83.2, -64.26), "U4.2")
pista("3V3", "F.Cu", 0.4, (-83.2, -66.28), "C10.1")
via("3V3", (-85.5, -77.42))
pista("3V3", "F.Cu", 0.4, (-85.5, -77.42), "U10.24")
pista("3V3", "F.Cu", 0.4, "U10.24", (-86.94, -76.6), (-89.675, -76.6))
pista("3V3", "F.Cu", 0.4, "C32.1", (-88.08, -76.6))
pista("3V3", "F.Cu", 0.4, "R36.2", (-89.675, -76.6))
pista("3V3", "B.Cu", 0.4, (-85.5, -74.9), (-96.075, -74.9))
via("3V3", (-92.875, -74.9))
pista("3V3", "F.Cu", 0.4, (-92.875, -74.9), "R37.2")
via("3V3", (-96.075, -74.9))
pista("3V3", "F.Cu", 0.4, (-96.075, -74.9), "R38.2")
pista("3V3", "B.Cu", 0.4, (-94.2, -74.9), (-94.2, -66.0))
pista("3V3", "B.Cu", 0.4, (-85.5, -98.24), "J11.2", (-104.07, -98.24), (-104.07, -90.74), "J5.5")
pista("3V3", "B.Cu", 0.4, (-85.5, -103.0), (-57.9, -103.0))
via("3V3", (-57.9, -103.0))
pista("3V3", "F.Cu", 0.4, (-57.9, -103.0), "R26.1")
pista("3V3", "B.Cu", 0.4, (-57.9, -103.0), (-55.25, -100.35), (-52.775, -100.35))
via("3V3", (-52.775, -100.35))
pista("3V3", "F.Cu", 0.4, (-52.775, -100.35), "R52.2")
pista("3V3", "F.Cu", 0.4, "R52.2", (-51.25, -101.3), (-51.25, -97.42), "C39.1")
pista("3V3", "F.Cu", 0.4, (-48.975, -97.42), "C27.1")
pista("3V3", "F.Cu", 0.4, "C27.1", "U8.1")
# ---------------------------------------------------------------- cargador (BQ24073)
# VSYS por los pines 10/11 a C3 y C17 y dos vías; VBUS por el pin 13 a C2.1/C1.1 (verticales) y una
# vía a B.Cu (TP1 sobre la fila; R10/R11 en F; F1.2 por B); BAT como polígono (2,9 A) de los pines
# 2/3 a C4 y Q1, con vías para TP4 y para la toma de R13 (B.Cu); ILIM por In2 a R5; ISET a R4; TS
# por In2 a RT1 con vías de retorno; EP con 4 vías térmicas (declaradas) y los pines 4/8/15 a vías.
pista("VSYS", "F.Cu", 0.25, "U2.10", "U2.11")
pista("VSYS", "F.Cu", 0.25, "U2.11", (-65.25, -108.08))
pista("VSYS", "F.Cu", 0.6, (-65.25, -108.08), "C3.1", "C17.1", (-65.25, -103.75))
via("VSYS", (-65.25, -103.75))
pista("VSYS", "F.Cu", 0.6, (-65.25, -103.75), (-66.45, -103.75))
via("VSYS", (-66.45, -103.75))
pista("VSYS", "B.Cu", 0.6, (-66.45, -103.75), "TP5.1")
stub("GND", "C3.2", (-0.95, 0.0), 0.4)
stub("GND", "C17.2", (0.0, 1.2), 0.6)
pista("VBUS", "F.Cu", 0.25, "U2.13", (-67.42, -109.75))
pista("VBUS", "F.Cu", 0.5, (-67.42, -109.75), "C2.1", "C1.1")
via("VBUS", (-68.5, -110.8))
pista("VBUS", "B.Cu", 0.5, (-68.5, -110.8), (-71.4, -110.8), (-72.2, -111.6), (-72.2, -116.12))
via("VBUS", (-72.2, -116.12))
pista("VBUS", "F.Cu", 0.5, (-72.2, -116.12), "R10.1", "R11.1")
pista("VBUS", "B.Cu", 0.5, (-72.2, -116.12), (-77.3, -116.12), (-79.48, -118.3), (-82.5, -118.3))
via("VBUS", (-82.5, -118.3))
pista("VBUS", "F.Cu", 0.5, (-82.5, -118.3), "F1.2")
stub("GND", "C2.2", (0.0, 0.9), 0.3)
stub("GND", "C1.2", (-1.0, 0.0), 0.3)
pista("BQ_ISET", "F.Cu", 0.25, "U2.16", (-67.3, -111.25), (-67.3, -115.025), "R4.1")
stub("GND", "R4.2", (0.0, -1.0), 0.3)
pista("BQ_ILIM", "F.Cu", 0.25, "U2.12", (-66.85, -109.06), (-66.85, -108.325))
via("BQ_ILIM", (-66.85, -108.325))
pista("BQ_ILIM", "In2.Cu", 0.2, (-66.85, -108.325), (-62.775, -108.325), (-61.6, -109.5))
via("BQ_ILIM", (-61.6, -109.5))
pista("BQ_ILIM", "F.Cu", 0.25, (-61.6, -109.5), (-61.6, -108.725), "R5.1")
stub("GND", "R5.2", (0.0, 0.975), 0.3)
pista("GND", "F.Cu", 0.25, "U2.4", (-64.25, -113.5))
via("GND", (-64.25, -113.5))
pista("GND", "F.Cu", 0.25, "U2.8", (-62.6, -109.75))
via("GND", (-62.6, -109.75))
pista("GND", "F.Cu", 0.25, "U2.15", (-67.7, -110.75))
via("GND", (-67.7, -110.75))
for _xy in ((-65.4, -110.9), (-64.6, -110.9), (-65.4, -110.1), (-64.6, -110.1)):
    via("GND", _xy)
pista("BAT", "F.Cu", 0.25, "U2.2", "U2.3")
pista("BAT", "F.Cu", 0.25, "U2.2", (-65.25, -112.92))
zona("BAT", "F.Cu", [(-67.0, -112.5), (-61.0, -112.5), (-61.0, -121.3), (-67.0, -121.3)])
via("BAT", (-66.2, -120.4))
pista("BAT", "B.Cu", 0.8, (-66.2, -120.4), "TP4.1")
via("BAT", (-66.6, -112.9))
pista("BAT", "B.Cu", 0.8, (-66.6, -112.9), (-66.6, -109.3), (-73.9, -109.3), (-73.9, -106.525))
via("BAT", (-73.9, -106.525))
pista("BAT", "F.Cu", 0.8, (-73.9, -106.525), "R13.1")
stub("GND", "C4.2", (1.0, 0.0), 0.3)
pista("BQ_TS", "F.Cu", 0.25, "U2.1", (-65.75, -113.5))
via("BQ_TS", (-65.75, -113.5))
pista("BQ_TS", "In2.Cu", 0.2, (-65.75, -113.5), (-65.75, -114.8), (-81.1, -114.8), (-82.4, -113.5))
via("BQ_TS", (-82.4, -113.5))
pista("BQ_TS", "F.Cu", 0.25, (-82.4, -113.5), "RT1.1")
via("GND", (-66.55, -113.9))
via("GND", (-83.1, -113.8))
stub("GND", "RT1.2", (0.0, 0.95), 0.3)
# ---------------------------------------------------------------- USB-C: VBUS_IN, CC1, CC2 y GND
# U1 (USBLC6) es de paso: los pines 6-1 (D+) y 4-3 (D-) se unen por debajo del cuerpo con 0,15,
# así que VBUS_IN no puede subir por el hueco entre columnas. Entra en el pin 5 y baja a In2 por
# una vía bajo el cuerpo; A4/B9 (0,3 centrada entre los dos pads) y A9/B4 bajan a In2 con sus
# propias vías y se juntan en la columna x -75,85; de ahí a F1.1 por la fila y -116,6 y la
# columna x -83,9 (sin cruzar la fila de BQ_TS). CC1 (A5) y CC2 (B5) por In2 bajo la fila de
# pads a R1 (oeste de F1; por In2, fila y -120,8) y R2 (oeste de U1; por B.Cu, fila y -120,9,
# porque en In2 la columna de VBUS_IN y el pad de escudo de J1 no dejan sitio a dos filas).
# GND de A12/B1 a una vía; A1/B12 por el relleno.
pista("VBUS_IN", "F.Cu", 0.3, (-75.85, -121.194), (-75.85, -120.2))
via("VBUS_IN", (-75.85, -120.2))
pista("VBUS_IN", "F.Cu", 0.5, "U1.5", (-75.85, -118.2))
via("VBUS_IN", (-75.85, -118.2))
pista("VBUS_IN", "In2.Cu", 0.5, (-75.85, -120.2), (-75.85, -118.2), (-75.85, -115.9), (-83.9, -115.9), (-83.9, -122.41))
via("VBUS_IN", (-83.9, -122.41))
pista("VBUS_IN", "F.Cu", 0.5, (-83.9, -122.41), "F1.1")
pista("VBUS_IN", "F.Cu", 0.4, (-71.05, -121.194), (-71.05, -120.21))
via("VBUS_IN", (-70.95, -120.21))
pista("VBUS_IN", "In2.Cu", 0.5, (-70.95, -120.21), (-70.95, -117.0), (-75.85, -117.0))
pista("CC1", "F.Cu", 0.2, "J1.A5", (-74.75, -120.2))
pista("CC1", "F.Cu", 0.15, (-74.75, -120.2), (-74.99, -119.96))
via("CC1", (-74.99, -119.96))
pista("CC1", "In2.Cu", 0.2, (-74.99, -119.96), (-74.99, -120.8), (-78.8, -120.8), (-79.5, -120.1), (-79.5, -118.925), (-81.0, -117.425))
via("CC1", (-81.0, -117.425))
pista("CC1", "F.Cu", 0.2, (-81.0, -117.425), "R1.1")
pista("CC2", "F.Cu", 0.2, "J1.B5", (-71.75, -120.15))
via("CC2", (-71.75, -120.15))
pista("CC2", "B.Cu", 0.2, (-71.75, -120.15), (-71.75, -120.9), (-79.6, -120.9), (-80.0, -120.5))
via("CC2", (-80.0, -120.5))
pista("CC2", "F.Cu", 0.2, (-80.0, -120.5), "R2.1")
stub("GND", "R1.2", (0.0, 0.9), 0.3)
stub("GND", "R2.2", (0.0, 1.0), 0.3)
stub("GND", "U1.2", (-1.0625, 0.0), 0.3)
stub("GND", "J1.A12", (0.0, 1.09), 0.3)
# ---------------------------------------------------------------- par USB (clase C, 0,28/0,15)
# Campo de pads de J1: 0,2 dentro del patio de J1 y 0,15 hasta U1. D+: A6 sube recta y B6 sube
# con un quiebro a x -72,45, cruza por encima de la vía de D- y entra en el pin 6 recogiendo a A6
# en un cruce a 90°; D-: B7 sube al pin 4 y A7 sube entre A6 y B6 hasta una vía de 0,45 y sigue
# por B.Cu (TP3 sobre esa pista) hasta otra vía en la salida del pin 3. Retornos de GND: vía
# (-73,1, -117,9) a 0,96 mm de la primera (entre A6 y el quiebro de B6) y la vía del pin 2 a
# 0,95 mm de la segunda. Con pads a 0,5 mm de paso, la vía de 0,6 solo cabe si B6 se aparta.
# Paso por U1: pines 6-1 y 4-3 unidos con 0,15 bajo el cuerpo. El par sale por el oeste de U1
# (x -78,7 / -79,13), sube por el pasillo norte-sur, cruza al canal (x -83,5 / -83,93) y entra en
# los pines 14 (D+) y 13 (D-). TP2 (D+) sobre una vía de 0,45 a la entrada del pin 14.
pista("USB_DP", "F.Cu", 0.2, "J1.A6", (-73.75, -120.25))
pista("USB_DP", "F.Cu", 0.15, (-73.75, -120.25), (-73.75, -117.25))
pista("USB_DP", "F.Cu", 0.2, "J1.B6", (-72.75, -120.25))
pista("USB_DP", "F.Cu", 0.15, (-72.75, -120.25), (-72.45, -119.95), (-72.45, -117.25), "U1.6")
pista("USB_DP", "F.Cu", 0.15, "U1.6", "U1.1")
pista("USB_DN", "F.Cu", 0.2, "J1.B7", (-74.25, -120.25))
pista("USB_DN", "F.Cu", 0.15, (-74.25, -120.25), (-74.25, -119.6125), (-74.7125, -119.15), "U1.4")
pista("USB_DN", "F.Cu", 0.15, "U1.4", "U1.3")
pista("USB_DN", "F.Cu", 0.2, "J1.A7", (-73.25, -120.25))
pista("USB_DN", "F.Cu", 0.15, (-73.25, -120.25), (-73.25, -118.85))
via("USB_DN", (-73.25, -118.85), VIA_USB)
pista("USB_DN", "B.Cu", 0.2, (-73.25, -118.85), (-76.9, -118.85), (-77.2, -119.15), (-78.1, -119.15))
via("USB_DN", (-78.1, -119.15), VIA_USB)
via("GND", (-73.1, -117.9))
pista("USB_DP", "F.Cu", 0.28, "U1.1", (-78.7, -117.25), (-78.7, -89.0), (-83.5, -84.2), (-83.5, -79.5), "U4.14")
pista("USB_DN", "F.Cu", 0.28, "U1.3", (-79.13, -119.15), (-79.13, -89.178), (-83.93, -84.378), (-83.93, -78.23), "U4.13")
via("USB_DP", (-83.0, -79.5), VIA_USB)
via("GND", (-82.6, -80.4))
pista("USB_DP", "B.Cu", 0.28, (-83.0, -79.5), (-83.5, -80.0), "TP2.1")
# ---------------------------------------------------------------- puente H (DRV8231A) y V6 local
# V6: C21.1 desde una vía del tronco de B.Cu, de ahí al pin 5 (0,5, ancho mayor que el pad); C19.1 con
# su propia vía; C22.1 y C20.1 por la vertical x -46,6 (con las vías del tronco y del ramal a R51).
# Salidas: OUT2 (pin 8) a J9.11 por F.Cu al noreste; OUT1 (pin 6) por In2 a J9.12 (los pads 11/12
# del motor se intercambiaron en el esquema). IPROPI a R28 y, por una vía, a TP8 (B) y JP3 (In2
# por x -54,6, fuera del anillo del mecanismo). VREF a C23 y por In2 a R27/R26. EP con 2 vías.
via("V6", (-49.44, -108.0))
pista("V6", "F.Cu", 0.5, (-49.44, -108.0), "C21.1")
pista("V6", "F.Cu", 0.25, "U6.5", (-48.55, -105.45))
pista("V6", "F.Cu", 0.5, (-48.55, -105.45), (-48.55, -106.45), (-49.44, -107.34))
pista("V6", "B.Cu", 0.5, (-49.44, -108.3), (-53.85, -108.3))
via("V6", (-53.85, -108.3))
pista("V6", "F.Cu", 0.5, (-53.85, -108.3), "C19.1")
pista("MOT_OUT2", "F.Cu", 0.25, "U6.8", (-48.05, -102.45))
pista("MOT_OUT2", "F.Cu", 0.5, (-48.05, -102.45), (-47.25, -101.65), (-44.34, -101.65))
pista("MOT_OUT1", "F.Cu", 0.25, "U6.6", (-47.55, -103.95))
via("MOT_OUT1", (-47.55, -103.95))
pista("MOT_OUT1", "In2.Cu", 0.5, (-47.55, -103.95), (-46.8, -104.7), "J9.12")
pista("GND", "F.Cu", 0.25, "U6.7", (-49.5, -103.45))
via("GND", (-49.5, -103.3))
via("GND", (-49.5, -104.1))
pista("IPROPI", "F.Cu", 0.25, "U6.1", "R28.1")
pista("IPROPI", "F.Cu", 0.25, "R28.1", (-51.825, -102.0))
via("IPROPI", (-51.825, -102.0))
pista("IPROPI", "B.Cu", 0.2, (-51.825, -102.0), (-51.3, -101.475), "TP8.1")
pista("IPROPI", "In2.Cu", 0.2, (-51.825, -102.0), (-54.6, -102.0), (-54.6, -88.9), (-60.3, -83.2))
via("GND", (-60.3, -84.2))
via("GND", (-50.95, -102.2))
via("IPROPI", (-60.3, -83.2))
pista("IPROPI", "F.Cu", 0.2, (-60.3, -83.2), "JP3.2")
pista("MOT_VREF", "F.Cu", 0.25, "U6.4", "C23.1")
pista("MOT_VREF", "F.Cu", 0.25, "C23.1", (-51.875, -105.3), (-55.275, -105.3), "R27.1")
pista("MOT_VREF", "F.Cu", 0.2, "R27.1", "R26.2")
stub("GND", "R28.2", (-0.825, 0.0), 0.3)
stub("GND", "C23.2", (-0.875, 0.0), 0.3)
stub("GND", "R27.2", (0.0, -0.8), 0.3)
stub("GND", "C19.2", (1.0, 0.0), 0.3)
stub("GND", "C21.2", (0.0, 1.2), 0.3)
stub("GND", "C20.2", (-1.05, 0.0), 0.3)
stub("GND", "C22.2", (0.0, 0.875), 0.3)
# ---------------------------------------------------------------- amplificador de clase D (MAX98357)
# VSYS por los pines 7/8 a C26.1 y a una vía; C25/C24 (bulk) con sus vías; GND de los pines 3/11/15
# al EP (1 vía). SPK_P/SPK_N (0,4) a J8.6/J8.7 en diagonales paralelas separadas.
pista("VSYS", "F.Cu", 0.25, "U7.7", "U7.8")
pista("VSYS", "F.Cu", 0.25, "U7.7", (-96.25, -87.2))
pista("VSYS", "F.Cu", 0.6, (-96.25, -87.2), (-96.25, -85.7))
via("VSYS", (-96.25, -85.7))
pista("VSYS", "F.Cu", 0.25, "U7.2", (-93.6, -89.85))
pista("VSYS", "F.Cu", 0.6, (-93.6, -89.85), (-92.4, -89.85))
via("VSYS", (-92.4, -89.85))
pista("VSYS", "F.Cu", 0.6, "C25.1", (-96.95, -92.2))
via("VSYS", (-96.95, -92.2))
pista("VSYS", "F.Cu", 0.6, "C24.1", (-100.4, -93.55))
via("VSYS", (-100.4, -93.55))
pista("GND", "F.Cu", 0.25, "U7.3", (-95.6, -89.35))
pista("GND", "F.Cu", 0.25, "U7.11", (-96.4, -89.85))
pista("GND", "F.Cu", 0.25, "U7.15", (-95.75, -90.0))
via("GND", (-96.0, -89.6))
stub("GND", "C26.2", (0.0, 0.95), 0.3)
stub("GND", "C25.2", (1.2, 0.0), 0.6)
stub("GND", "C24.2", (0.0, 1.2), 0.6)
pista("SPK_P", "F.Cu", 0.25, "U7.9", (-97.4375, -87.85))
pista("SPK_P", "F.Cu", 0.4, (-97.4375, -87.85), (-101.7, -83.59))
pista("SPK_N", "F.Cu", 0.25, "U7.10", (-98.19, -89.35))
pista("SPK_N", "F.Cu", 0.4, (-98.19, -89.35), "J8.7")
# ---------------------------------------------------------------- vías de VSYS del resto
stub("VSYS", "R54.1", (0.0, -1.2), 0.6)
stub("VSYS", "R6.2", (1.2, 0.0), 0.6)
pista("VSYS", "F.Cu", 0.6, "L2.1", (-53.6, -109.3))
via("VSYS", (-52.9, -109.3))
via("VSYS", (-53.6, -109.3))
# ---------------------------------------------------------------- módulo: EP y GND de los pines 1/40, C9, C10
for _x in (-75.9, -74.5, -73.1):
    for _y in (-69.31, -70.71, -72.11):
        via("GND", (_x, _y))
stub("GND", "U4.1", (-1.25, 0.0), 0.3)
stub("GND", "U4.40", (1.25, 0.0), 0.3)
stub("GND", "C10.2", (0.0, 0.925), 0.3)
stub("GND", "C9.2", (-1.2, 0.0), 0.4)
