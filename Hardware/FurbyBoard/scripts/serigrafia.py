"""Rótulos de serigrafía de la FurbyBoard y su colocación automática.

Arriba: qué es cada TP, LED, botón y puente, para medir y depurar con la placa
montada. Abajo: la función de cada pad de cable y los GPIO del J_EXP, donde se
sueldan los cables. Cada rótulo prueba varias posiciones alrededor de su pieza
y se queda con la primera que no pisa pads, otra serigrafía, cuerpos de piezas,
el borde ni el agujero del mecanismo. Si ninguna vale, el rótulo no se pone y se
avisa (manda el diseño, no el dibujo).
"""
import math

TEXTO = 0.8          # alto mínimo de JLCPCB
GROSOR = 0.15
HUECO = 0.25         # entre el rótulo y su pieza
MARGEN_PAD = 0.2     # serigrafía a cobre descubierto
MARGEN_SILK = 0.12
MARGEN_BORDE = 0.4

# Referencia -> texto. Orden de preferencia de posición: derecha, izquierda, arriba, abajo.
ARRIBA = {
    "J2": "+", "J3": "-",   # polaridad de la batería también arriba, por donde se suelda
    "SW1": "RST", "SW2": "BOOT",
    "D4": "PWR", "D5": "RUN", "D3": "TX",
    "JP1": "IO9", "JP2": "IO46", "JP3": "IO3", "JP4": "IO8", "JP5": "LED",
}

# TP: van en la cara inferior, sobre una vía de su red junto a la fuente; su rótulo se pone
# en la colocación (gen_pcb.py), como los demás, para poder seguir el TEST-PLAN sobre la placa.
TP_ABAJO = {
    "TP1": "VBUS", "TP2": "D+", "TP3": "D-", "TP4": "BAT", "TP5": "VSYS", "TP6": "3V3",
    "TP7": "6V", "TP8": "IPR",
    "TP9": "I2S", "TP10": "2V8", "TP11": "1V2", "TP12": "G", "TP13": "G", "TP14": "G",
}

# Lado preferido de cada rótulo de arriba (por defecto RLUD).
LADO_ARRIBA = {r: "D" for r in ("SW1", "SW2", "JP5")}
LADO_ARRIBA["J2"] = "U"
LADO_ARRIBA.update({r: "U" for r in ("D4", "D5", "D3")})
# D1 (CHG, rojo) y D2 (PG, verde) se distinguen por el color y no llevan rótulo.

# Los puentes se cortan desde arriba, pero no siempre cabe su rótulo: en la cara inferior,
# en el mismo sitio, va siempre qué GPIO libera cada uno.
PUENTES_ABAJO = {"JP1": "IO9", "JP2": "IO46", "JP3": "IO3", "JP4": "IO8", "JP5": "LED"}

# Pads de cable (cara inferior, donde se sueldan): referencia -> {pad: texto}
PADS = {
    "J11": {"1": "G", "2": "3V3", "3": "VSYS", "4": "5V", "5": "IO4 SDA", "6": "IO5 SCL",
            "7": "P07", "8": "G", "9": "IO43 TX", "10": "IO44 RX"},
    "J8": {"1": "TLA", "2": "TLB", "3": "G", "4": "LNG", "5": "G", "6": "SP+", "7": "SP-"},
    "J7": {"1": "IR+", "2": "IR-", "3": "RXV", "4": "RX", "5": "3V3", "6": "LDR", "7": "G", "8": "G"},
    "J9": {"1": "ENF", "2": "G", "3": "EN+", "4": "G", "5": "LEVA", "6": "G",
           "7": "BAR", "8": "G", "9": "ESP", "10": "G", "11": "M1", "12": "M2"},
    "J5": {"1": "SD", "2": "G", "3": "SCK", "4": "WS", "5": "3V3", "6": "G"},
    "J2": {"1": "BAT+"}, "J3": {"1": "BAT-"},
}
# Lado preferido del rótulo de cada pad. Los grupos de dos filas o columnas que no tienen
# sitio alrededor (J9 y J5 pegados al borde derecho, J7 pegado al delantero) llevan al lado
# una leyenda con la misma disposición que los pads: (lado, separación entre columnas).
LADO_PADS = {"J8": "R", "J2": "D", "J3": "D"}
LADO_TP = "UDRL"
LEYENDA = {"J9": ("L", 3.6), "J5": ("R", 3.0), "J7": ("R", 3.0), "J11": ("R", 5.8)}
TITULOS = {"J9": "J9", "J7": "J7", "J8": "J8", "J11": "J_EXP"}


class Caja:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    def crece(self, m):
        return Caja(self.x0 - m, self.y0 - m, self.x1 + m, self.y1 + m)

    def toca(self, o):
        return self.x0 < o.x1 and o.x0 < self.x1 and self.y0 < o.y1 and o.y0 < self.y1

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


class Colocador:
    """Obstáculos de una cara y rótulos ya puestos; prueba posiciones candidatas."""

    def __init__(self, contorno, circulos, pads, silk, cuerpos):
        self.contorno = contorno
        self.circulos = circulos        # [(cx, cy, r)] sin serigrafía (mecanismo, taladros)
        self.pads = pads                # [Caja]
        self.silk = silk                # [Caja]
        self.cuerpos = cuerpos          # [(ref, Caja)]
        self.fallos = []

    def libre(self, caja, ref_propia=None):
        if any(caja.toca(p.crece(MARGEN_PAD)) for p in self.pads):
            return False
        if any(caja.toca(s.crece(MARGEN_SILK)) for s in self.silk):
            return False
        if any(caja.toca(c) for r, c in self.cuerpos if r != ref_propia):
            return False
        for cx, cy, r in self.circulos:
            px, py = min(max(cx, caja.x0), caja.x1), min(max(cy, caja.y0), caja.y1)
            if math.hypot(px - cx, py - cy) < r + MARGEN_BORDE:
                return False
        for p in caja.puntos():
            if not dentro(self.contorno, p) or dist_borde(self.contorno, p) < MARGEN_BORDE:
                return False
        return True

    def candidatos(self, ancla, w, h, lados):
        x0, y0, x1, y1 = ancla.x0, ancla.y0, ancla.x1, ancla.y1
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        desliz = (0, h * 0.6, -h * 0.6, h * 1.2, -h * 1.2)
        for lado in lados:
            if lado == "C":
                yield (cx, cy)
                continue
            for d in desliz:
                if lado == "R":
                    yield (x1 + HUECO + w / 2, cy + d)
                elif lado == "L":
                    yield (x0 - HUECO - w / 2, cy + d)
                elif lado == "U":
                    yield (cx + d * w / h / 2, y1 + HUECO + h / 2)
                elif lado == "D":
                    yield (cx + d * w / h / 2, y0 - HUECO - h / 2)

    def coloca(self, nombre, ancla, medida, lados, ref_propia=None):
        """medida(texto) -> (w, h). Devuelve el centro elegido o None."""
        w, h = medida
        for x, y in self.candidatos(ancla, w, h, lados):
            caja = Caja(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
            if self.libre(caja, ref_propia):
                self.silk.append(caja)
                return (x, y)
        self.fallos.append(nombre)
        return None
