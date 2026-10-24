"""Colocación de la FurbyBoard en coordenadas del STL (mm, vista desde arriba, delante = y mayor).

Cada entrada es ref -> (x, y, rotación en grados, sentido antihorario visto desde arriba) y,
opcionalmente, un cuarto valor "B" para las piezas de la cara inferior (solo los puntos de
test: todo lo que se monta va en la cara superior, montaje económico de JLCPCB a una cara).

Replanteo del 2026-10-24 (NOTAS.md, «Planta»). Bloques, de delante hacia atrás:

- delante: módulo con la antena en el borde; a su derecha, LED PWR/RUN/TX, botones y JP5;
  a su izquierda, pads del IR y la luz (J7) con el driver del emisor;
- borde izquierdo (fuera de la batería): J8 (inclinación, lengua, altavoz), J5 (micro) y J_EXP;
- bajo la batería, de delante hacia atrás: expansor pegado a la columna izquierda del módulo
  con el acondicionamiento de J8 entre ambos, amplificador junto a J8 y J5, buck-boost de 3,3 V
  en la zona trasera izquierda;
- borde derecho: FPC de la cámara con el flex hacia la pared; debajo, los LDO de la cámara,
  el Schmitt del encoder, los puentes y el puente H junto a J9;
- esquina trasera derecha: elevador de 6 V; centro trasero: cargador, protección de polaridad
  y pads de la batería; lóbulo: USB-C, ESD, PTC.

Pasillos reservados (sin piezas): el de la cámara (módulo -> J6, y -74..-81), el pasillo sur
(y -83..-89,5 entre el módulo y el agujero del mecanismo), el canal x -86,5..-82,5 a la
izquierda de la columna izquierda del módulo (I2S, par USB, 3V3) y el pasillo norte-sur
x -77..-69 bajo la batería (par USB, señales del motor, VBAT).
"""

BATERIA = {"centro": (-84.5, -91.8), "ancho": 33.0, "largo": 50.0, "giro": -4.0}
ANTENA_SIN_COBRE = {"x": (-85.0, -61.0), "y": (-62.0, -50.0)}
# Logo en la cara inferior (sin vías ni pads), bajo la zona trasera izquierda de la batería,
# entre J_EXP, el buck-boost y el micro: sin piezas arriba y pocas vías previstas. Subordinado al diseño.
LOGO_INFERIOR = {"x": (-101.5, -87.1), "y": (-117.6, -104.0)}
# Franja del flex de la cámara entre J6 y la pared: sin piezas (el flex pasa por encima).
FLEX_SIN_PIEZAS = {"x": (-46.0, -39.0), "y": (-88.0, -72.0)}
CALZOS = [(-75.0, -105.8, "E1"), (-99.5, -113.0, "E2"), (-90.5, -112.5, "E3")]
CALZO_D = 4.0
# Cabeza del tornillo M2 (Ø4) + 0,5: sin cobre ni piezas en las dos caras (layout-pcb.md 4.1).
TORNILLO_KEEPOUT_D = 5.0

P = {
    # ------------------------------------------------ módulo y su soporte (pin 2 = 3V3, 3 = EN)
    "U4": (-73.0, -68.25, 0),
    "C10": (-84.4, -65.5, 90), "C9": (-84.4, -68.9, 90),
    # ------------------------------------------------ delante a la izquierda: IR, luz y RC de EN
    "J7": (-94.5, -62.7, 0),
    "R56": (-88.8, -67.25, 0), "R17": (-88.8, -68.95, 0), "C11": (-88.8, -70.65, 0), "R53": (-88.8, -72.35, 0),
    "Q3": (-92.4, -69.2, 90), "R54": (-92.2, -72.9, 0), "R55": (-95.6, -72.3, 0),
    # ------------------------------------------------ LED, botones y JP5 (delante a la derecha)
    "D4": (-60.0, -63.0, 0), "D5": (-56.4, -63.0, 0), "D3": (-52.8, -63.0, 0),
    "R57": (-60.0, -64.9, 0), "R58": (-56.4, -64.9, 0), "R19": (-52.8, -64.9, 0),
    "SW1": (-61.2, -69.6, 90), "SW2": (-57.4, -69.6, 90), "JP5": (-53.9, -69.4, 90),
    # ------------------------------------------------ cámara: FPC en el borde derecho (pin 1 abajo)
    "J6": (-49.3, -80.0, 90),
    # LDO de la cámara debajo del FPC: 3V3 -> U8 (2,8 V) -> U9 (1,2 V); control debajo
    "U8": (-52.7, -91, 0), "C28": (-49.7, -91.0, 90), "C29": (-47.2, -91.0, 90),
    "R33": (-53.9, -96.6, 90), "C27": (-55.7, -90.35, 270), "U9": (-47.8, -94.5, 0),
    "C30": (-51.8, -96, 90), "C39": (-50.75, -99.2, 90), "U11": (-47.8, -98.1, 180),
    "C31": (-58.8, -84.2, 90), "R34": (-61.1, -84.2, 90), "R35": (-56.5, -84.2, 90),
    # ------------------------------------------------ pasillo sur: puentes del motor, BOOT y JP4
    "JP1": (-65.5, -83.1, 0), "JP2": (-65.5, -85.8, 0), "JP3": (-65.5, -88.5, 0),
    "R18": (-62.8, -83.4, 90), "JP4": (-57.8, -87.5, 0),
    # ------------------------------------------------ puente H junto a los pads del motor (J9.11/12)
    "J9": (-41.8, -92.0, 270),
    "U6": (-49.5, -103.2, 0),
    "C22": (-46.8, -103.6, 90), "C20": (-46.8, -109, 270), "C21": (-49.2, -106.2, 0),
    "R28": (-52.65, -102.3, 180), "C23": (-52.65, -104, 180),
    "R26": (-55.9, -102.3, 0), "R27": (-55.9, -104, 180),
    "R29": (-62.8, -87.3, 90), "R30": (-61.1, -87.3, 90), "R25": (-57.6, -108, 90),
    # Series de barriga, espalda y leva y resistencia del LED del encoder, junto a J9
    "R40": (-44.2, -106.7, 0), "R42": (-44.2, -108.3, 0), "R50": (-44.2, -109.9, 0), "R51": (-44.2, -111.5, 0),
    "R52": (-44, -89.6, 0),
    # ------------------------------------------------ elevador de 6 V (esquina trasera derecha)
    # SW abajo (hacia U5), VIN al este (Cin), VOUT y GND al sur (lazo caliente con Cout).
    "L2": (-50.5, -110.3, 270), "U5": (-50.5, -114.7, 0),
    "C13": (-47, -112.4, 90), "C16": (-47, -115.7, 90), "R23": (-45, -115.6, 90), "C17": (-64.7, -105.4, 0),
    "C18": (-51, -118.1, 270), "C19": (-52.8, -106.2, 0),
    "R20": (-57, -114, 180), "C12": (-53.8, -114, 180), "R22": (-53.8, -115.6, 180),
    "C15": (-53.8, -117.2, 180), "R21": (-57, -115.6, 0), "R24": (-57, -117.2, 180),
    "C14": (-60.4, -113.4, 0),
    # ------------------------------------------------ cargador (centro trasero), girado 90°:
    # IN al oeste (C2 junto al pin), BAT al sur (C4, Q1 y pads), OUT al norte (C3), EN/PGOOD al este.
    "U2": (-65.0, -110.5, 90),
    "C2": (-68.8, -109.75, 180), "C1": (-68.8, -111.4, 180), "R4": (-68.8, -113.0, 0), "R3": (-68.8, -114.6, 0),
    "C3": (-66.6, -107.4, 180), "R5": (-63.5, -107.4, 0),
    "C4": (-64.0, -113.6, 0), "R12": (-65.6, -115.3, 0),
    "R9": (-60.4, -106.9, 0), "R8": (-60.4, -108.5, 0), "R6": (-60.4, -110.1, 0), "R7": (-60.4, -111.7, 0),
    # LED CHG y PG al norte del cargador (visibles); sus resistencias, en VBUS bajo la batería
    "D1": (-61.2, -102.7, 0), "D2": (-61.2, -105.1, 0),
    # Divisor de VBAT (ADC) y resistencias de los LED: columna bajo la batería, junto al cargador
    "R13": (-71.2, -105.7, 90), "R14": (-71.2, -108.9, 90), "C5": (-71.2, -112.1, 90),
    "R10": (-71.2, -115.3, 90), "R11": (-71.2, -118.5, 90),
    # Polaridad y pads de la batería (fuera de la batería, detrás de su esquina derecha)
    "Q1": (-64.0, -118.0, 180), "J2": (-68.3, -118.3, 0), "J3": (-64.5, -123.6, 0),
    # ------------------------------------------------ USB (lóbulo)
    "J1": (-73.5, -128.494, 0), "U1": (-75.8, -118.2, 0),
    "R1": (-78.75, -118.6, 90), "R2": (-72.85, -118.6, 90), "F1": (-82.5, -121.0, 90),
    # ------------------------------------------------ borde izquierdo: J8, micro (2 x 3) y J_EXP (2 x 5)
    "J8": (-101.7, -70.6, 270), "J5": (-102.8, -88.2, 270), "J11": (-102.8, -95.7, 270),
    # ------------------------------------------------ bajo la batería: expansor y su acondicionamiento
    "C32": (-87.3, -75.7, 0), "R36": (-90.5, -75.7, 0), "R37": (-93.7, -75.7, 0), "R38": (-96.9, -75.7, 0),
    "U10": (-89.8, -81, 0),
    "R45": (-95.4, -77.4, 0), "R46": (-95.4, -79.1, 0), "C36": (-95.4, -80.8, 0), "R47": (-95.4, -82.5, 0),
    "R48": (-98.6, -77.4, 0), "C37": (-98.6, -79.1, 0), "R43": (-98.6, -80.8, 0), "R44": (-98.6, -82.5, 0),
    "C35": (-98.6, -84.2, 0),
    # Pull-ups y filtros de barriga, espalda y leva (sus series van junto a J9)
    "C33": (-87.4, -86.2, 0), "C34": (-90.6, -86.2, 0), "C40": (-88.8, -74.05, 0),
    "C38": (-87.4, -87.8, 0), "R49": (-90.6, -87.8, 0),
    "R39": (-87.4, -89.4, 0), "R41": (-90.6, -89.4, 0),
    # ------------------------------------------------ bajo la batería: amplificador junto a J8
    # Girado 180°: salidas al oeste hacia J8.6/7, VDD al norte (C26 junto al pin), I2S al sur, DIN al este.
    "U7": (-96, -89.6, 180), "C26": (-96, -86.6, 0), "C24": (-99.2, -92.6, 90), "C25": (-96, -93.4, 0),
    "R31": (-96, -95.6, 0), "R32": (-96, -97.3, 0),
    # ------------------------------------------------ bajo la batería: buck-boost de 3,3 V
    # VIN/L1/L2/VOUT al este (bobina y condensadores), EN/MODE/AGND/FB al oeste (divisor).
    "C6": (-90, -99.2, 180), "U3": (-90, -102.8, 0), "L1": (-86, -102.8, 270),
    "C7": (-85.9, -106.7, 0), "C8": (-85.9, -108.9, 0),
    "R16": (-92.4, -102.4, 90), "R15": (-94.2, -102.4, 270),
    # ------------------------------------------------ puntos de test: cara inferior, junto a su fuente
    "TP1": (-69.0, -113.8, 0, "B"), "TP2": (-77.0, -116.0, 0, "B"), "TP3": (-74.0, -116.0, 0, "B"),
    "TP4": (-64.6, -115.8, 0, "B"), "TP5": (-66.6, -105.2, 0, "B"), "TP6": (-81, -108.4, 0, "B"),
    "TP7": (-47.5, -116.8, 0, "B"), "TP8": (-55.2, -103.3, 0, "B"), "TP9": (-92.8, -82.6, 0, "B"),
    "TP10": (-53.0, -93.0, 0, "B"), "TP11": (-48.8, -93.0, 0, "B"),
    "TP12": (-67.5, -84.8, 0, "B"), "TP13": (-57.5, -106.0, 0, "B"), "TP14": (-98.8, -79.0, 0, "B"),
}


def placement():
    return {ref: v[:3] for ref, v in P.items()}


def caras():
    """Cara de cada pieza: "F" salvo las marcadas con "B"."""
    return {ref: (v[3] if len(v) > 3 else "F") for ref, v in P.items()}
