"""Rótulos de serigrafía de la FurbyBoard y su colocación automática.

Arriba: qué es cada LED, botón y puente, para medir y depurar con la placa montada.
Abajo: la función de cada pad de cable y los GPIO del J_EXP, donde se sueldan los
cables, y el nombre de cada TP. Se colocan después del rutado (gen_pcb.py): cada
rótulo prueba varias posiciones alrededor de su pieza y se queda con la primera que
no pisa pads, vías, otra serigrafía, cuerpos de piezas, el borde ni el agujero del
mecanismo, prefiriendo las que tampoco pisan pistas de su cara. Si a 1,0 mm no cabe,
prueba a 0,8 mm; si tampoco, el rótulo no se pone y se avisa (manda el diseño, no el
dibujo).
"""
import math

TEXTO = 1.0          # alto mínimo de JLCPCB (fabricante-jlcpcb.md: texto ≥ 1,0 mm, trazo ≥ 0,15)
TEXTO_MIN = 0.8      # solo si a 1,0 no cabe; es el mínimo del DRC del proyecto (gen_pro.py)
TEXTO_BAT = 1.5      # polaridad de la batería: rótulo grande (preferencias del autor del proyecto)
GROSOR = 0.15
HUECO = 0.25         # entre el rótulo y su pieza
MARGEN_PAD = 0.2     # serigrafía a cobre descubierto
MARGEN_VIA = 0.15    # las vías van tapadas y JLCPCB recorta la serigrafía que las pisa
MARGEN_PISTA = 0.05  # solo para preferir sitios sin pistas debajo (más legibles)
MARGEN_SILK = 0.15   # a la serigrafía de las huellas y a los dibujos (el DRC pide 0,1)
MARGEN_ROTULO = 0.5  # entre rótulos: que no se lean juntos (medio carácter)
MARGEN_BORDE = 0.3   # al borde de la placa (DRC: 0,1; tolerancia del fresado de JLCPCB ± 0,2)
DESPLAZA_MAX = 10.0  # cuánto puede alejarse una fila de una leyenda de sus pads, mm
RADIO_ROTULO = 2.0   # hueco máximo entre un rótulo suelto y su pieza, mm

# Referencia -> texto. Orden de preferencia de posición: derecha, izquierda, arriba, abajo.
ARRIBA = {
    "J2": "+", "J3": "-",   # polaridad de la batería también arriba, por donde se suelda
    "SW1": "RST", "SW2": "BOOT",
    "D4": "PWR", "D5": "RUN", "D3": "TX",
    "JP1": "IO9", "JP2": "IO46", "JP3": "IO3", "JP4": "IO8", "JP5": "LED",
}
TAMANO = {"J2": TEXTO_BAT, "J3": TEXTO_BAT}

# TP: van en la cara inferior, sobre su red junto a la fuente; su nombre, para poder seguir el
# TEST-PLAN sobre la placa.
TP_ABAJO = {
    "TP1": "VBUS", "TP2": "D+", "TP3": "D-", "TP4": "BAT", "TP5": "VSYS", "TP6": "3V3",
    "TP7": "6V", "TP8": "IPR",
    "TP9": "I2S", "TP10": "2V8", "TP11": "1V2", "TP12": "G", "TP13": "G", "TP14": "G",
}

# Lado preferido de cada rótulo de arriba (por defecto RLUD).
LADO_ARRIBA = {r: "D" for r in ("SW1", "JP5")}
LADO_ARRIBA["SW2"] = "DR"
LADO_ARRIBA["J2"] = "U"
LADO_ARRIBA.update({r: "U" for r in ("D4", "D5", "D3")})
# D1 (CHG, rojo) y D2 (PG, verde) se distinguen por el color y no llevan rótulo.

# Los puentes se cortan desde arriba, pero no siempre cabe su rótulo: en la cara inferior,
# en el mismo sitio, va siempre qué GPIO libera cada uno.
PUENTES_ABAJO = {"JP1": "IO9", "JP2": "IO46", "JP3": "IO3", "JP4": "IO8", "JP5": "LED"}

# Pads de cable (cara inferior, donde se sueldan): referencia -> {pad: texto}
PADS = {
    # J_EXP (bloque U, 2026-10-25): 5 EXP_P07 en el puerto P04 del TCA9535, consola UART0 en 7/10
    "J11": {"1": "G", "2": "3V3", "3": "VSYS", "4": "5V", "5": "P04", "6": "IO5 SCL",
            "7": "IO43 TX", "8": "G", "9": "IO4 SDA", "10": "IO44 RX"},
    "J8": {"1": "TLA", "2": "TLB", "3": "G", "4": "LNG", "5": "G", "6": "SP+", "7": "SP-"},
    # J7.3 y J7.8 permutados (bloque U2): 3 GND, 8 alimentación del receptor IR (IR_PWR, P17)
    "J7": {"1": "IR+", "2": "IR-", "3": "G", "4": "RX", "5": "3V3", "6": "LDR", "7": "G", "8": "RXV"},
    "J9": {"1": "ENF", "2": "G", "3": "EN+", "4": "G", "5": "LEVA", "6": "G",
           "7": "BAR", "8": "G", "9": "ESP", "10": "G", "11": "M2", "12": "M1"},   # 11/12 intercambiados en design.py
    "J5": {"1": "SD", "2": "G", "3": "SCK", "4": "WS", "5": "3V3", "6": "G"},
    # Alternativas por orden: si «BAT-» no cabe junto al pad redondo, al menos «-»
    "J2": {"1": ("BAT+", "+")}, "J3": {"1": ("BAT-", "-")},
}
# Rótulos que se pueden confundir con los de la pieza de al lado (polaridad de la batería, puentes
# en fila): el centro del rótulo tiene que quedar claramente más cerca de su pieza que de las otras
# del grupo (distancia a la suya ≤ AMBIGUEDAD × distancia a cualquier otra), en las dos caras.
GRUPOS_AMBIGUOS = [("J2", "J3"), ("JP1", "JP2", "JP3"), ("D4", "D5", "D3"), ("SW1", "SW2")]
AMBIGUEDAD = 0.75
# Los rótulos que no son de un conector de cable se quedan a esta distancia de sus pads: si no, se
# leen como la función de ese pad (p. ej. la «G» de un TP pegada a un pad de J8).
CONECTORES_CABLE = ("J2", "J3", "J5", "J7", "J8", "J9", "J11")
HUECO_CABLE = 1.2
TAMANO_PADS = {"J2": 1.2, "J3": 1.2}
# Lado preferido del rótulo de cada pad. Los grupos de dos filas o columnas que no tienen
# sitio alrededor (J9 y J5 pegados al borde, J7 pegado al delantero) llevan al lado una leyenda
# con la misma disposición que los pads: (lado, separación mínima entre columnas, mm). La
# leyenda se mueve entera, alejándose de los pads, hasta que ninguna celda pisa nada.
LADO_PADS = {"J8": "R", "J2": "D", "J3": "D"}
LADO_TP = "UDRL"
LEYENDA = {"J9": ("L", 0.6), "J5": ("R", 0.6), "J7": ("R", 0.6), "J11": ("R", 0.8)}
TITULOS = {"J9": "J9", "J7": "J7", "J8": "J8", "J5": "J5", "J11": "J_EXP"}


class Caja:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    def crece(self, m):
        return Caja(self.x0 - m, self.y0 - m, self.x1 + m, self.y1 + m)

    def mueve(self, dx, dy):
        return Caja(self.x0 + dx, self.y0 + dy, self.x1 + dx, self.y1 + dy)

    def toca(self, o):
        return self.x0 < o.x1 and o.x0 < self.x1 and self.y0 < o.y1 and o.y0 < self.y1

    def contiene(self, x, y):
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def puntos(self, paso=0.5):
        nx = max(2, int((self.x1 - self.x0) / paso) + 1)
        ny = max(2, int((self.y1 - self.y0) / paso) + 1)
        for i in range(nx):
            x = self.x0 + (self.x1 - self.x0) * i / (nx - 1)
            yield (x, self.y0)
            yield (x, self.y1)
        for j in range(ny):
            y = self.y0 + (self.y1 - self.y0) * j / (ny - 1)
            yield (self.x0, y)
            yield (self.x1, y)


def centrada(x, y, w, h):
    return Caja(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def dentro(poligono, p):
    x, y = p
    c = False
    for (x0, y0), (x1, y1) in zip(poligono, poligono[1:] + poligono[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


def dist_borde(poligono, p):
    x, y = p
    mejor = 1e9
    for (x0, y0), (x1, y1) in zip(poligono, poligono[1:] + poligono[:1]):
        dx, dy = x1 - x0, y1 - y0
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy or 1e-12)))
        mejor = min(mejor, math.hypot(x0 + t * dx - x, y0 + t * dy - y))
    return mejor


def circulo_toca(caja, cx, cy, r):
    px, py = min(max(cx, caja.x0), caja.x1), min(max(cy, caja.y0), caja.y1)
    return math.hypot(px - cx, py - cy) < r


def pista_toca(caja, x0, y0, x1, y1, semiancho):
    """¿Pasa la pista (segmento con su ancho) por la caja? Muestreo cada 0,1 mm."""
    m = semiancho + MARGEN_PISTA
    if max(x0, x1) + m < caja.x0 or min(x0, x1) - m > caja.x1 or max(y0, y1) + m < caja.y0 or min(y0, y1) - m > caja.y1:
        return False
    grande = caja.crece(m)
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.1))
    return any(grande.contiene(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n + 1))


class Colocador:
    """Obstáculos de una cara y rótulos ya puestos; prueba posiciones candidatas."""

    def __init__(self, contorno, circulos, pads, silk, cuerpos, vias=(), pistas=()):
        self.contorno = contorno
        self.circulos = circulos        # [(cx, cy, r)] sin serigrafía (mecanismo, taladros)
        self.pads = pads                # [Caja]
        self.silk = silk                # [Caja] serigrafía de huellas y dibujos
        self.rotulos = []               # [Caja] rótulos ya puestos (y filas de leyenda reservadas)
        self.cuerpos = cuerpos          # [(ref, Caja)]
        self.vias = list(vias)          # [(cx, cy, r)]
        self.pistas = list(pistas)      # [(x0, y0, x1, y1, semiancho)] de esta cara
        self.fallos = []
        self.reducidos = []
        self.aparte = []

    def libre(self, caja, ref_propia=None, limpio=False):
        if any(caja.toca(p.crece(MARGEN_PAD)) for p in self.pads):
            return False
        if any(caja.toca(s.crece(MARGEN_SILK)) for s in self.silk):
            return False
        if any(caja.toca(s.crece(MARGEN_ROTULO)) for s in self.rotulos):
            return False
        if any(caja.toca(c) for r, c in self.cuerpos if r != ref_propia):
            return False
        if any(circulo_toca(caja, cx, cy, r + MARGEN_VIA) for cx, cy, r in self.vias):
            return False
        for cx, cy, r in self.circulos:
            if circulo_toca(caja, cx, cy, r + MARGEN_BORDE):
                return False
        for p in caja.puntos():
            if not dentro(self.contorno, p) or dist_borde(self.contorno, p) < MARGEN_BORDE:
                return False
        if limpio and any(pista_toca(caja, *s) for s in self.pistas):
            return False
        return True

    def candidatos(self, ancla, w, h, lados):
        x0, y0, x1, y1 = ancla.x0, ancla.y0, ancla.x1, ancla.y1
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        desliz = (0, h * 0.6, -h * 0.6, h * 1.2, -h * 1.2, h * 1.8, -h * 1.8)
        for hueco in (HUECO, HUECO + 0.5):
            for lado in lados:
                if lado == "C":
                    yield (cx, cy)
                    continue
                for d in desliz:
                    if lado == "R":
                        yield (x1 + hueco + w / 2, cy + d)
                    elif lado == "L":
                        yield (x0 - hueco - w / 2, cy + d)
                    elif lado == "U":
                        yield (cx + d * w / h / 2, y1 + hueco + h / 2)
                    elif lado == "D":
                        yield (cx + d * w / h / 2, y0 - hueco - h / 2)

    def anillo(self, ancla, w, h, ref_propia=None, radio=None, paso=0.2):
        """Centros alrededor de la pieza, del más cercano al más lejano (hueco entre cajas ≤ radio)."""
        radio = RADIO_ROTULO if radio is None else radio
        nx, ny = int((ancla.x1 - ancla.x0 + w) / 2 / paso + radio / paso) + 1, int((ancla.y1 - ancla.y0 + h) / 2 / paso + radio / paso) + 1
        cx, cy = (ancla.x0 + ancla.x1) / 2, (ancla.y0 + ancla.y1) / 2
        cand = []
        for i in range(-nx, nx + 1):
            for j in range(-ny, ny + 1):
                x, y = cx + i * paso, cy + j * paso
                caja = centrada(x, y, w, h)
                gx = max(ancla.x0 - caja.x1, caja.x0 - ancla.x1, 0)
                gy = max(ancla.y0 - caja.y1, caja.y0 - ancla.y1, 0)
                hueco = math.hypot(gx, gy)
                if HUECO - 1e-6 <= hueco <= radio:
                    cand.append((hueco, x, y))
        cand.sort()
        return [(x, y) for _, x, y in cand]

    def coloca(self, nombre, ancla, medida, lados, ref_propia=None, valido=None, limpio_primero=True,
               avisa=True, anillo=True):
        """medida(alto) -> (w, h). Devuelve (centro, alto) o None.

        A cada alto (el pedido, 1,0 y, si no cabe, 0,8 mm): primero las posiciones de siempre por lado, sin
        pistas debajo (si limpio_primero) y luego con ellas; después, el sitio libre más cercano
        alrededor de la pieza. valido(caja) descarta posiciones ambiguas."""
        for alto in sorted({medida.alto, min(medida.alto, TEXTO), TEXTO_MIN}, reverse=True):
            w, h = medida(alto)
            pruebas = [(c, True) for c in self.candidatos(ancla, w, h, lados)] if limpio_primero else []
            pruebas += [(c, False) for c in self.candidatos(ancla, w, h, lados)]
            if anillo:
                pruebas += [(c, False) for c in self.anillo(ancla, w, h, ref_propia)]
            for (x, y), limpio in pruebas:
                caja = centrada(x, y, w, h)
                if (valido is None or valido(caja)) and self.libre(caja, ref_propia, limpio):
                    self.rotulos.append(caja)
                    if alto < medida.alto:
                        self.reducidos.append(nombre)
                    return (x, y), alto
        if avisa:
            self.fallos.append(nombre)
        return None

    def busca(self, nombre, cx, cy, w, h, radio=8.0, paso=0.25):
        """Sitio libre (y sin pistas, si lo hay) más cercano a (cx, cy) para una caja w × h."""
        n = int(radio / paso)
        ofs = sorted(((i * paso, j * paso) for i in range(-n, n + 1) for j in range(-n, n + 1)),
                     key=lambda d: math.hypot(*d))
        for limpio in (True, False):
            for dx, dy in ofs:
                if math.hypot(dx, dy) > radio:
                    break
                caja = centrada(cx + dx, cy + dy, w, h)
                if self.libre(caja, limpio=limpio):
                    self.rotulos.append(caja)
                    return cx + dx, cy + dy
        self.fallos.append(nombre)
        return None

    def libre_circulo(self, cx, cy, r, limpio=False):
        """Como libre, para un círculo (la caja de un círculo grande taparía sus esquinas libres)."""
        cajas = [p.crece(MARGEN_PAD) for p in self.pads] + [s.crece(MARGEN_SILK) for s in self.silk]
        cajas += [s.crece(MARGEN_ROTULO) for s in self.rotulos] + [c for _, c in self.cuerpos]
        if any(circulo_toca(c, cx, cy, r) for c in cajas):
            return False
        if any(math.hypot(vx - cx, vy - cy) < r + rv + MARGEN_VIA for vx, vy, rv in self.vias):
            return False
        if any(math.hypot(hx - cx, hy - cy) < r + rh + MARGEN_BORDE for hx, hy, rh in self.circulos):
            return False
        for k in range(48):
            p = (cx + r * math.cos(k * math.pi / 24), cy + r * math.sin(k * math.pi / 24))
            if not dentro(self.contorno, p) or dist_borde(self.contorno, p) < MARGEN_BORDE:
                return False
        if limpio:
            for x0, y0, x1, y1, sa in self.pistas:
                n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.1))
                if any(math.hypot(x0 + (x1 - x0) * k / n - cx, y0 + (y1 - y0) * k / n - cy) < r + sa + MARGEN_PISTA
                       for k in range(n + 1)):
                    return False
        return True

    def busca_forma(self, nombre, cx, cy, cajas, circulos, radio=3.0, paso=0.1, valido=None):
        """Como busca, para una forma de cajas y círculos (x, y, r) relativos a su centro: todo libre.
        valido(cajas, circulos) descarta posiciones (ya movidas) por otros motivos."""
        n = int(radio / paso)
        ofs = sorted(((i * paso, j * paso) for i in range(-n, n + 1) for j in range(-n, n + 1)),
                     key=lambda d: math.hypot(*d))
        for limpio in (True, False):
            for dx, dy in ofs:
                if math.hypot(dx, dy) > radio:
                    break
                mc = [c.mueve(cx + dx, cy + dy) for c in cajas]
                mo = [(x + cx + dx, y + cy + dy, r) for x, y, r in circulos]
                if (valido is None or valido(mc, mo)) and all(self.libre(c, limpio=limpio) for c in mc) \
                        and all(self.libre_circulo(*o, limpio=limpio) for o in mo):
                    self.rotulos += mc + [centrada(x, y, 2 * r, 2 * r) for x, y, r in mo]
                    return cx + dx, cy + dy
        self.fallos.append(nombre)
        return None

class Medida:
    """Ancho y alto de un texto según su alto de letra (lo mide KiCad)."""

    def __init__(self, fn, alto=TEXTO):
        self.fn, self.alto = fn, alto

    def __call__(self, alto=None):
        return self.fn(alto or self.alto)
