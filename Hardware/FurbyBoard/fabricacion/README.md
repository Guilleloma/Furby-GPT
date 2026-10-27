# FurbyBoard v1.0: ficheros de fabricación

Generados el 2026-10-27 desde el diseño de la rama `fix/furbyboard-m3-a2` (A2: R24 a 33 kΩ 0402 básica, C25779, tras la revisión independiente de M3, [`../revisiones/2026-10-27-M3-independiente.md`](../revisiones/2026-10-27-M3-independiente.md), que repitió la puerta E2 sobre estos ficheros; antes M3 `ce455a2`: R24 en 0402 y R23/R50 separadas del borde fresado; antes M7 `f2f73dd`: R59 y R60 de 33 Ω en los relojes de la cámara, y M1 `4156112`: paralelos In2/In3) con `scripts/make_fab.sh`; la puerta E2 se repitió sobre ellos ([`../revisiones/2026-10-27-M3.md`](../revisiones/2026-10-27-M3.md); la anterior, [`../revisiones/2026-10-27-M7-M1.md`](../revisiones/2026-10-27-M7-M1.md)). Primera puerta E2 (ficheros del 2026-10-25, commit `d99273f`) pasada el 2026-10-25: [`../revisiones/2026-10-25-E2-fabricacion.md`](../revisiones/2026-10-25-E2-fabricacion.md) y tabla «Revisiones» de `../NOTAS.md`. **Desde aquí no se pide nada:** el pedido se hace a mano en jlcpcb.com.

## Qué subir

| Fichero | Dónde se sube | Qué es |
|---------|---------------|--------|
| `gerber-jlcpcb.zip` | «Add gerber file» | 6 capas de cobre, máscara, pasta, serigrafía, contorno, taladros PTH y NPTH (Excellon) y sus mapas, con el origen en el (0,0) del STL de la base, **el mismo que el CPL** |
| `bom-jlcpcb.csv` | PCB Assembly → BOM | Una línea por pieza (huella y LCSC): 52 líneas, 126 piezas |
| `cpl-jlcpcb.csv` | PCB Assembly → CPL | Posición y giro de las 126 piezas, ya corregidos para las huellas EasyEDA de JLCPCB (`scripts/jlc_post.py`) |

| Fichero | No se sube | Qué es |
|---------|------------|--------|
| `gerber/` | — | Los mismos ficheros del zip, sueltos, para revisarlos |
| `erc.rpt`, `drc.rpt` | — | ERC y DRC con paridad del momento de la exportación: 0 errores, 0 avisos, 0 sin unir |
| `esquematico.pdf` | — | Esquema completo (8 hojas) |
| `../render/furbyboard-arriba.png`, `-abajo.png`, `-iso.png` | — | Placa montada en 3D (cara superior, inferior y perspectiva) |
| `../render/furbyboard.step` | — | Modelo 3D de la placa montada, para la carcasa |

## Apilado

**JLC06161H-7628**, 6 capas, 1,6 mm, cobre exterior 1 oz e interior 0,5 oz.

| Capa | Uso |
|------|-----|
| L1 F.Cu | Todas las piezas, par USB (0,28/0,15 mm) y bus de la cámara; relleno de GND |
| L2 In1 | GND continuo (salvo bajo la antena) |
| L3 In2 | Señales y relleno de VSYS |
| L4 In3 | Señales lentas |
| L5 In4 | GND continuo |
| L6 B.Cu | Señales, puntos de test, pads de cable, relleno de GND, logos y rótulos |

Vías pasantes de 0,6/0,3 mm en toda la placa y tres de 0,45/0,2 en el par USB; sin ciegas ni enterradas. Los pads expuestos de U2, U4, U6 y U7 llevan vías térmicas dentro del pad: en 6 capas JLCPCB las rellena y tapa (POFV) sin coste extra.

## Opciones del formulario de PCB

| Opción | Valor | Por qué |
|--------|-------|---------|
| Base material | FR-4 | — |
| Layers | **6** | Planos de GND enteros en In1 e In4 y dos capas de señal interiores |
| Dimensions | Las lee del Gerber: **68,9 × 74,7 mm** | — |
| PCB Qty | 5 | Mínimo de JLCPCB |
| Different design | 1 | — |
| Delivery format | Single PCB | Sin panel: la placa tiene forma de suelo y el USB-C sale por una muesca del borde |
| PCB thickness | **1,6 mm** | Obligatorio: el USB-C de montaje medio (HRO M-13C) es para 1,6 mm, y la altura del eje en la base sale de ahí |
| Layer stackup | **JLC06161H-7628** | Con el que se calculó el par USB (≈ 87 Ω diferencial). Si solo ofrecen el 3313, vale: a 12 Mbit/s el par no es crítico (`../NOTAS.md`, «Apilado») |
| Impedance control | No | El USB es de 12 Mbit/s y la pista mide 55 mm |
| Outer / inner copper | 1 oz / 0,5 oz | Los de serie del apilado |
| Via covering | **Epoxy filled & capped (POFV)** | De serie en 6 capas; lo piden las vías térmicas dentro de los pads expuestos |
| Min via hole size / diameter | **0,2 / 0,45 mm** | Las tres vías del par USB; si el formulario cobra por ello, mirar el sobrecoste antes de pagar |
| Surface finish | **ENIG** | Pads planos para los QFN y WSON de 0,5 mm y el FPC de 0,5. En 6 capas JLCPCB ya no lo da gratis (OSP sí); si encarece mucho, OSP también vale para un prototipo que se monta enseguida |
| PCB color | Verde | El más rápido; la placa no se ve con el Furby cerrado |
| Silkscreen | Blanca | — |
| Board outline tolerance | ±0,2 mm (normal) | Holgura a la pared de la base de 1,0 mm (0,47 en las orejetas del USB-C) |
| Mark on PCB | «Remove mark» si lo ofrece | No hay sitio reservado para el número de pedido |
| Electrical test | Flying probe (incluido) | — |
| Gold fingers, castellated holes, edge plating | No | — |

## Opciones de montaje (PCB Assembly)

| Opción | Valor | Por qué |
|--------|-------|---------|
| PCBA type | **Economic** | Admite 6 capas, 1,6 mm, montaje a una cara y paso de 0,4 mm o más (el más fino es 0,5) |
| Assembly side | **Top side** | La cara inferior no lleva piezas: solo serigrafía, logos y puntos de test (su capa de pasta está vacía) |
| PCBA Qty | **2** (o 5) | Con 2 se prueba el bring-up y quedan 3 placas desnudas |
| Tooling holes | Added by JLCPCB | — |
| Confirm parts placement | **Yes** | Ver «Revisar en el visor» |

## Revisar en el visor de JLCPCB antes de pagar

Los giros y orígenes del CPL se compararon por geometría con la huella EasyEDA de cada LCSC el 2026-10-25 (`pcb-toolkit cpl-rotaciones`: PASS, 0 errores); el 2026-10-27, tras añadir R59 y R60 (0402 sin polaridad, giro 0) y pasar R24 a 0402 (M3, giro 180, sin polaridad), PASS con 3 avisos `giro-sin-tabla` por C25105 y C25779 (R24 de 33 kΩ desde A2; pendientes de añadir a la tabla de pcb-toolkit). **Ninguna de estas piezas se ha montado todavía en JLCPCB**: la vista previa no basta, hay que mirarlas una a una.

| Pieza | Qué mirar |
|-------|-----------|
| U2, U3, U5, U6, U7 (QFN, VSON, WSON) | Pin 1 junto al punto de la serigrafía |
| U1, U8, U9, U11 (SOT-23-5/6), Q3 (SOT-23) | Pin 1 en la esquina marcada; JLCPCB los gira 180° o 270° respecto a KiCad, y es lo esperado |
| U10 (TSSOP-24) | Pin 1 (INT) arriba a la izquierda, junto a la marca |
| Q1 (PowerPAK 1212-8) | Placa girada 180°: los cuatro pines S/G hacia el este y el pad de drenador hacia el oeste; G es el pin del norte (pin 1, S, el del sur) |
| D1–D5 (LED) | Cátodo hacia la marca de la serigrafía (en EasyEDA el cátodo es el pad 2, y está bien así) |
| J1 (USB-C) | La boca hacia el borde inferior, dentro de la muesca; el CPL corrige 4,70 mm de origen |
| U4 (ESP32-S3-WROOM-1) | La antena hacia el borde superior, sobre la zona sin cobre; el CPL corrige 3,63 mm de origen |
| J6 (FPC de 24 pines) | Pin 1 junto al punto blanco de la serigrafía |
| R59 y R60 (0402, 33 Ω) y R24 (0402, 33 kΩ) | Las tres piezas 0402 de la placa: R59 pegada a la fila inferior del módulo (bajo el pin 21), R60 a 2 mm a la izquierda del FPC y R24 (M3) la última de la columna a la izquierda del elevador, pegada al borde trasero; sin polaridad, solo comprobar que están |

## Coste estimado (consultado el 2026-10-25)

**Estimado.** Componentes con la API de piezas de JLCPCB del 2026-10-25; PCB y montaje con la tarifa publicada (*PCB Assembly Price*, 2026-10-22) y la página de 6 capas. Lo que vale es el presupuesto del formulario.

| Concepto | 5 PCB, 2 montadas (USD) | 5 PCB, 5 montadas (USD) |
|----------|------------------------|-------------------------|
| PCB de 6 capas, 68,9 × 74,7 mm, 1,6 mm (5 unidades) | ≈ 15–45 (con ENIG; desde ≈ 2 con OSP en promoción) | ≈ 15–45 |
| Montaje Economic: puesta en marcha 8,18 + plantilla 1,53 + confirmación 0,45 + juntas (≈ 0,0017 cada una) | ≈ 12 | ≈ 15 |
| Carga de 18 referencias extended × 3,07 (con M3, R24 en 0402 pasó a extended, C25776; con A2 vuelve a básica, C25779 de 33 kΩ) | 55,26 | 55,26 |
| Componentes (16,29 por placa, sin contar mínimos de compra; R59 y R60 añaden 0,002) | ≈ 33 | ≈ 81 |
| Envío y aranceles | No incluidos | No incluidos |
| **Total sin envío** | **≈ 115–145** | **≈ 165–200** |

Lo que más pesa por placa: el WROOM-1-N16R8 (5,35), los 11 condensadores de 22 µF (2,10), TCA9535, MAX98357A y DRV8231A (≈ 1,32 cada uno). Las tres resistencias *preferred extended* (C23265, C23150, C22965) no pagan carga en Economic.

## Confirmar antes de pedir

| Pieza | Estado el 2026-10-25 | Qué hacer |
|-------|----------------------|-----------|
| RT1, NTC Murata NCP18XH103F03RB (C13564) | **NRND** (Murata no la recomienda para diseños nuevos; última compra prevista en 2032). En JLCPCB: extended, 275 482 en stock | Sirve para la v1.0. Si al pedir no hay stock: **C440252** (NCU18XH103F60RB, sucesora de Murata, 10 kΩ 1 %, B 3380 K, 0603; extended, 30 597 en stock), misma huella |
| L2, FHD4020S-1R0MT (C602028) | **Cerrado:** Isat 8,7 A (máx., caída < 30 %) y 11 A (típ.), Irms 5,8 A según el datasheet de Changjiang; hacía falta ≥ 3,4 A | Nada |
| R51, 220 Ω (C22962) | **Cerrado:** basic, 3 288 255 en stock | Nada |
| R59, R60, 33 Ω 0402 (C25105) | **Cerrado** (2026-10-27): basic, 2 162 519 en stock, 0,0011 USD | Nada; si faltara, cualquier 33 Ω 0402 1 % básica |
| R24, 33 kΩ 0402 (C25779, UNI-ROYAL 0402WGF3302TCE; A2) | **Cerrado** (2026-10-27): básica según la API de JLCPCB, 2 540 677 en stock, 0,0019 USD. Sustituye al 30 kΩ 0402 (C25776, extended, 3,07 USD de carga): fC del lazo del TPS61089 +10 %, margen de fase ≥ 78,8° en todas las esquinas (cálculo en [`../revisiones/2026-10-27-M3-independiente.md`](../revisiones/2026-10-27-M3-independiente.md)) | Nada; si faltara, cualquier 33 kΩ 0402 1 % básica (o el 30 kΩ C25776, extended) |
| C41, 10 µF 0603 (C19702) | **Cerrado:** basic, 13 044 359 en stock | Nada |
| 470 Ω (C23179) | Ya no está en la BOM | Nada |
| J1, USB-C HRO M-13C (C2848620) | 2 202 en stock (el más bajo) | Mirar el stock el día del pedido; JLCPCB lo da como SMD (las cuatro patas de la carcasa son ranuras metalizadas del Gerber). Si el formulario lo marca como pasante y Economic no lo admite, pasar a Standard o soldarlo a mano |
| L1, FHD4020S-R47MT (C602026) | 2 359 en stock | Mirar el stock el día del pedido |
| U10 TCA9535 (C130204), U11 74LVC1G17 (C7836), U5 TPS61089 (C165129) | 7 257, 9 599 y 10 353 en stock | Ídem |
| Apilado, ENIG y vía de 0,2 mm | Precio no confirmado | Mirar el presupuesto: si JLC06161H-7628 no está, el 3313 vale; si ENIG o la vía de 0,2 encarecen mucho, OSP y aceptar el sobrecoste de la vía (no se puede quitar sin cambiar el par USB) |

## BOM con clase, stock y precio (API de JLCPCB, 2026-10-25)

Ninguna pieza sin stock ni con el código cambiado. Clase: **B** basic, **P** preferred extended (sin carga en Economic), **E** extended (3,07 USD de carga por referencia).

| LCSC | Pieza | Ref. | Cant. | Clase | Stock | USD/u |
|------|-------|------|-------|-------|-------|-------|
| C19702 | 10 µF 10 V X5R 0603 | C1, C3, C4, C6, C41 | 5 | B | 13 044 359 | 0,0272 |
| C15849 | 1 µF 50 V X5R 0603 | C2, C11, C27, C28, C29 | 5 | B | 13 751 461 | 0,0146 |
| C14663 | 100 nF 50 V X7R 0603 | C5, C10, C13, C22, C23, C26, C30–C37, C39, C40 | 16 | B | 44 096 715 | 0,0084 |
| C45783 | 22 µF 25 V X5R 0805 | C7–C9, C16–C21, C24, C25 | 11 | B | 4 282 207 | 0,1912 |
| C23630 | 2,2 µF 16 V X5R 0603 | C12 | 1 | B | 3 154 831 | 0,0125 |
| C53987 | 4,7 nF 50 V X7R 0603 | C14 | 1 | B | 1 053 901 | 0,0053 |
| C1634 | 10 pF 50 V C0G 0603 | C15 | 1 | B | 1 418 665 | 0,0060 |
| C57112 | 10 nF 50 V X7R 0603 | C38 | 1 | B | 6 093 002 | 0,0109 |
| C2286 | LED rojo 0603 KT-0603R | D1, D3 | 2 | B | 7 822 377 | 0,0077 |
| C2297 | LED verde 0805 KT-0805G | D2, D4, D5 | 3 | B | 2 414 940 | 0,0164 |
| C883133 | PTC 1,5 A 1206 BSMD1206-150-16V | F1 | 1 | E | 46 205 | 0,0676 |
| C2848620 | USB-C 16P HRO TYPE-C-31-M-13C | J1 | 1 | E | 2 202 | 0,2658 |
| C262669 | FPC 24P 0,5 AFC01-S24FCA-00 | J6 | 1 | E | 27 275 | 0,1208 |
| C602026 | 0,47 µH FHD4020S-R47MT | L1 | 1 | E | 2 359 | 0,0707 |
| C602028 | 1 µH FHD4020S-1R0MT | L2 | 1 | E | 13 944 | 0,0740 |
| C553966 | SI7615ADN-T1-GE3 | Q1 | 1 | E | 30 000 | 0,6023 |
| C20917 | AO3400A | Q3 | 1 | B | 1 214 038 | 0,0889 |
| C23186 | 5,1 kΩ | R1, R2 | 2 | B | 22 174 388 | 0,0015 |
| C4177 | 1,8 kΩ | R4 | 1 | B | 735 640 | 0,0021 |
| C22765 | 1,2 kΩ | R5 | 1 | B | 2 382 054 | 0,0034 |
| C25803 | 100 kΩ | R6–R9, R22, R25, R29, R30, R33, R49, R55 | 11 | B | 18 224 986 | 0,0031 |
| C4190 | 2,2 kΩ | R10, R11 | 2 | B | 6 037 217 | 0,0018 |
| C25804 | 10 kΩ | R12, R17, R18, R27, R34, R35, R38, R52 | 8 | B | 40 718 086 | 0,0022 |
| C23178 | 470 kΩ | R13, R14, R53 | 3 | B | 1 127 395 | 0,0030 |
| C23192 | 510 kΩ | R15 | 1 | B | 979 841 | 0,0020 |
| C23265 | 91 kΩ | R16 | 1 | P | 135 025 | 0,0020 |
| C22843 | 1,5 kΩ | R19, R28 | 2 | B | 3 878 411 | 0,0020 |
| C22807 | 150 kΩ | R20 | 1 | B | 955 240 | 0,0017 |
| C23150 | 390 kΩ | R21 | 1 | P | 279 917 | 0,0020 |
| C22965 | 270 kΩ | R23 | 1 | P | 276 774 | 0,0018 |
| C25779 | 33 kΩ 0402 (0402WGF3302TCE; A2, antes C25776 de 30 kΩ en 0402 y C22984 en 0603) | R24 | 1 | B | 2 540 677 (2026-10-27, API de JLCPCB) | 0,0019 |
| C23162 | 4,7 kΩ | R26, R36, R37 | 3 | B | 17 137 163 | 0,0028 |
| C23140 | 33 Ω | R31, R32 | 2 | B | 4 588 092 | 0,0024 |
| C25105 | 33 Ω 0402 (0402WGF330JTCE) | R59, R60 | 2 | B | 2 162 519 (2026-10-27) | 0,0011 |
| C25819 | 47 kΩ | R39, R41, R43 | 3 | B | 3 528 011 | 0,0035 |
| C21190 | 1 kΩ | R40, R42, R44, R46, R48, R50, R56–R58 | 9 | B | 35 105 191 | 0,0017 |
| C22961 | 220 kΩ | R45, R47 | 2 | B | 1 198 102 | 0,0015 |
| C22962 | 220 Ω | R51 | 1 | B | 3 288 255 | 0,0033 |
| C17561 | 22 Ω 0805 | R54 | 1 | B | 1 465 633 | 0,0046 |
| C13564 | NTC 10 kΩ NCP18XH103F03RB (NRND) | RT1 | 1 | E | 275 482 | 0,0508 |
| C720477 | Pulsador TS-1088-AR02016 (RESET / BOOT) | SW1, SW2 | 2 | B | 520 604 | 0,0527 |
| C2687116 | USBLC6-2SC6 | U1 | 1 | E | 121 225 | 0,0478 |
| C15220 | BQ24073RGTR | U2 | 1 | E | 30 206 | 0,8805 |
| C2845237 | TPS63802DLAR | U3 | 1 | E | 37 419 | 0,9083 |
| C2913202 | ESP32-S3-WROOM-1-N16R8 | U4 | 1 | E | 27 472 | 5,3497 |
| C165129 | TPS61089RNRR | U5 | 1 | E | 10 353 | 0,7152 |
| C5139865 | DRV8231ADSGR | U6 | 1 | E | 14 887 | 1,3191 |
| C910544 | MAX98357AETE+T | U7 | 1 | E | 21 278 | 1,3240 |
| C53099 | ME6211C28M5G-N | U8 | 1 | E | 29 409 | 0,0662 |
| C236672 | ME6211C12M5G-N | U9 | 1 | E | 34 481 | 0,0621 |
| C130204 | TCA9535PWR | U10 | 1 | E | 7 257 | 1,3305 |
| C7836 | SN74LVC1G17DBVR | U11 | 1 | E | 9 599 | 0,1549 |

Resistencias: UNI-ROYAL 0603 al 1 % salvo R54 (0805).

## Sin montar (a mano o aparte)

**Fuera de la BOM y del CPL** (cobre de la placa o piezas que se compran aparte):

| Qué | Dónde | Cómo |
|-----|-------|------|
| Batería LiPo 1S 1400 mAh | Pads J2 (BAT+, cuadrado) y J3 (BAT−, redondo), cara inferior junto al USB-C | Cables soldados a mano. La protección contra la inversión está en la placa (Q1) |
| Módulo de cámara OV2640 (FPC de 24 pines) | J6 | Se enchufa al conector FPC, que sí monta JLCPCB |
| Plaquita del micro ICS-43434 (I2S) | Pads J5 (2 × 3) | Cable de ≤ 15 cm soldado a mano |
| Cables del Furby (IR y luz, inclinación, lengua, altavoz, motor, encoder, leva, barriga, espalda) | Pads J7, J8 y J9 | Soldados a mano (`../README.md`, «Conectores y pads») |
| Header de expansión J_EXP (J11) | 2 × 5 pads de 2,54 mm | Sin montar; un header si hace falta la consola |
| Puntos de test TP1–TP14 y puentes JP1–JP5 | Cobre de la placa | Los puentes vienen cerrados en el cobre; se cortan para liberar GPIO |
