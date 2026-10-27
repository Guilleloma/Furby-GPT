# Revisión independiente de M3 (piezas contra el contorno fresado; E1 y E2 repetidas) — FurbyBoard v1.0

- Fecha: 2026-10-27 · Commits revisados: `ce455a2` (piezas movidas), `e558d6a` (fabricación), `3807781` (documentación) de `fix/furbyboard-m3` sobre `trunk` `402eeb9` · Revisor: electronics-engineer, revisor independiente (T0, Fable 5.1), sin participación en M3
- Tipo de placa: L · Capas: 6 (JLC06161H-7628) · Fabricante: JLCPCB (Economic a una cara)
- Material revisado: `FurbyBoard.kicad_pcb` y `.kicad_sch` (en `3807781` y en `402eeb9` para el antes), `scripts/design.py`, `layout.py`, `rutas_fijas.py`, informe del autor `revisiones/2026-10-27-M3.md`, `NOTAS.md`, `fabricacion/` (Gerber, taladros, BOM, CPL, README). Todas las cifras de abajo salen de mis propios volcados y de volver a ejecutar las herramientas; no se ha copiado ninguna del informe del autor.
- Skills cargadas: `hardware-design-review` (y sus referencias del Cerebro enteras: `revision-de-diseno`, `plantilla-informe-revision`, `layout-pcb`, `kicad-automatizacion`, `fabricacion-pcb`, `fabricante-jlcpcb`, `preferencias-pcb-guillermo`).
- Herramientas (§1.1 de `kicad-automatizacion.md`): kicad-cli 10.0.7; pcb-toolkit 0.1.0 del venv de `~/development/pcb-toolkit`; kicad-happy v2.3.2 (`2fd9aa0f`); Freerouting 1.9.0 presente (no usado); rsvg-convert y ngspice presentes; sin `~*.lck`. Nada instalado: los Gerber se rasterizaron con un parser propio y el Pillow del venv de pcb-toolkit; el Bode del lazo con el numpy de `~/tools/venv-electronica`.

## Resultado
**PASA** — 0 críticos, 0 importantes, 3 mejoras (dos ya documentadas por el autor, una nueva). **A2 resuelto por cálculo y aplicado** en la rama `fix/furbyboard-m3-a2` (commit `598f268`, sobre `fix/furbyboard-m3`): R24 pasa de 30 kΩ 0402 extended (C25776) a **33 kΩ 0402 básica (C25779)**, con la E2 repetida sobre los ficheros regenerados. **A1 aceptado** tal como lo documenta el autor.

## Herramientas
| Herramienta | Comando | Resultado |
|-------------|---------|-----------|
| ERC | `kicad-cli sch erc --severity-all --exit-code-violations` | **0 errores, 0 avisos** (también en `598f268`) |
| DRC | `kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations` sobre la placa guardada | **0 infracciones, 0 sin unir, 0 de paridad** (`3807781` y `598f268`); `make_fab.sh` confirma que la copia rellenada por kicad-cli es idéntica a la guardada |
| Flujo | `pcb-toolkit comprobar-flujo --png --json` | Solo los dos cruces ya aceptados en NOTAS (I2S_DIN a 0,40 del clase D; MOT_VREF a 2,58 de L2) y los 4 desacoplos de siempre (C10, C32, C22, C2) |
| Geometría | `pcb-toolkit revisar-rutado --json` (anchos de `pcb-toolkit.toml`) sobre `3807781` y sobre `402eeb9` | **0 errores, 152 avisos** frente a 151: el único aviso nuevo es `entrada-pad-descentrada` R23:1 0,225 (BST_ILIM, en el eje del pad); los 13 `entrada-asimetrica` que cambian de texto solo invierten el orden «pad 1/pad 2» del mensaje. Igual en `598f268` |
| Configuración | `pcb-toolkit.toml`, `.kicad_dru` | Sin cambios respecto a `402eeb9`; ninguna regla apagada |
| CPL | `pcb-toolkit cpl-rotaciones cpl-jlcpcb.csv FurbyBoard.kicad_pcb --bom … --gerber …` | **PASS, 0 errores, 3 avisos** `giro-sin-tabla` (C25105 ×2 y el 0402 de R24; sin polaridad); origen del CPL = origen auxiliar (220; −40) = origen del Gerber; 98 montado-verificado, 25 comparado-sin-montar |
| Análisis | `kicad-happy.sh analizar` sobre una copia (v2.3.2) | Puerta WARN (152 símbolos frente a 158 huellas = 152 + H1–H4 + LOGO1 + LOGO2). Nivel error: FD-001 (fiduciales), KO-001 ×6 (H1–H4, LOGO1 y la vía de IR_TX junto a H1, comprobación por caja), PM-002 (J1 fuera del contorno), PP-001 (U6.5 en V6), EMC DC-002, SU-001, U3 armónicos, SW-003: **los mismos de E1-12 y M9, nada nuevo** |
| Volcados propios (pcbnew en subproceso) | `borde.py` (patio, cuerpo F.Fab y pads de las 158 huellas contra `GetBoardPolygonOutlines`, de borde a borde, con el agujero del mecanismo), `local.py` (geometría de la esquina), `zonas_rev.py` (trozos y área por red y capa; contenido de cada trozo de GND de F.Cu de la esquina; cobre dentro de cada área de reglas), `paralelos_rev.py` (In2/In3, ≤ 8°, solape ≥ 2 mm, < 1 mm borde a borde), `keepout_rev.py` | Resultados en las secciones de abajo |
| Gerber | Parser propio RS-274X (aperturas C/R/O/RoundRect, regiones, polaridad) sobre `fabricacion/gerber/`: raster de dos ventanas y comparación por geometría | Ventanas leídas; BOM = CPL = huellas con LCSC (126); zip = carpeta (18/18); 383 PTH + 4 NPTH |
| Simulación | `ngspice -b drv8231a_motor.cir` y `arranque_brownout.cir` con R24 = 33 k (A2) | Mismos resultados que `sim/RESULTADOS.md` salvo el rizado de V6 (119 mV pp bloqueado, 18 mV pp en PWM; antes 130 y 19) |
| PNG | `pcb-toolkit capturas` a 60 px/mm (esquina del elevador y zona de R50/R23/J9, antes y después) + raster de los Gerber | **15 leídos** (tabla abajo) |

## Punto 1 — Distancia al contorno fresado (volcado propio, mm; `402eeb9` → `3807781`)
Criterio: pads y cuerpo de toda pieza montada a ≥ 0,5 mm del contorno real (tolerancia del contorno ±0,2 mm, `fabricante-jlcpcb.md` §2); cobre ≥ 0,3 (DRC) y ≥ 0,2 (JLCPCB).

| Pieza | Patio | Cuerpo | Pads | Observación |
|-------|-------|--------|------|-------------|
| **R24** (0603 → 0402) | 0,086 → **0,597** | 0,359 → **0,803** | 0,336 → **0,774** | (−53,88; −119,10) a 180°, coincide con el autor (0,60 / 0,80 / 0,77) |
| **R23** | 0,216 → **0,396** | 0,821 → **0,997** | 0,650 → **0,827** | 0,30 al norte; coincide (0,40 / 1,00 / 0,83) |
| **R50** | 0,410 → **0,568** | 1,102 → **1,260** | 0,789 → **0,947** | 0,15 al oeste y 0,05 al norte; coincide (0,57 / 1,26 / 0,95) |
| R42 | 0,500 | 1,191 | 0,873 | Sin cambio |
| D3, C16, C18, R40 | 0,70 / 0,76 / 0,98 / 1,01 | ≥ 1,39 | ≥ 1,14 | Sin cambio |
| J9 (pads de cable) | 0,282 | — | 0,720 | Sin cambio |
| J7, J8, J11 (pads de cable) | 0,101 / 0,008 / −0,111 (vértice fuera) | — | 0,446 / 0,344 / 0,347 | Sin cambio (A1) |
| J1 (USB-C de montaje medio) | −0,945 | −0,765 | 0,140 | Regla propia del `.kicad_dru` (0,12 a la ranura), sin cambio |
| U4 (módulo) | −18,75 (antena fuera) | 0,889 | 7,35 | Sin cambio |
| LOGO1 (serigrafía) | 0,605 | 0,574 | — | Sin cambio |

Las otras 144 huellas quedan a > 1,0 mm en los tres conceptos. **Ninguna pieza montada tiene pads ni cuerpo a < 0,5 mm**: objetivo de M3 cumplido. Solo se han movido R24 (y cambia de huella), R23 y R50; las 155 restantes están en la misma posición y giro que en `402eeb9`.

## Punto 2 — R24 en 0402
| Comprobación | Resultado |
|--------------|-----------|
| Valor | `hojas/motor.kicad_sch`: Value 30k, LCSC C25776, JLC_Class ext, huella `Resistor_SMD:R_0402_1005Metric`; PCB: pads 1 = BST_COMP, 2 = BST_RC; BOM `30k,R24,R_0402_1005Metric,C25776`; CPL `R24,-53.880mm,-119.100mm,Top,180.0`; paridad DRC 0. El diff del esquema respecto a `402eeb9` son exactamente esas cuatro propiedades |
| C25776 | API de EasyEDA/LCSC y de JLCPCB (2026-10-27): UNI-ROYAL 0402WGF3002TCE, 30 kΩ, R0402; JLCPCB `componentLibraryType = expand` (extended), 1 351 354 en stock, 0,0012 USD. Confirmado lo que dice el autor |
| Nodo COMP | C15.1 → R24.1: 0,505 mm pad a pad; red BST_COMP 3,89 mm en F.Cu (U5.4 → C15.1 → diagonal de 0,43 → R24.1), sin vías |
| Nodo RC | R24.2 → C14.1: 1,42 mm pad a pad; red BST_RC 2,34 mm en F.Cu (oeste, 45° a la fila y −118,6, entra en C14.1 por el eje), sin vías |
| Zona caliente de L2 | Patio de R24 a 5,09 mm del patio de L2 y a 5,38 de sus pads (margen 3 mm) |
| Keepout de H4 | Patio de R24 a 3,49 mm del área de reglas Ø5 de H4 |
| Gerber | F.Cu, F.Mask y F.Paste con flash RoundRect 0,54 × 0,64 en (−54,39; −119,10) y (−53,37; −119,10); F.Silkscreen con el mismo flash en claro (máscara restada) |

## Punto 3 — A2: 30 kΩ (C25776, extended) o 33 kΩ (C25779, básica)
Verificación de la pieza: API de JLCPCB (2026-10-27) → **C25779 = UNI-ROYAL 0402WGF3302TCE, 33 kΩ ±1 %, R0402, `componentLibraryType = base`, 2 540 677 en stock, 0,0019 USD**; API de EasyEDA/LCSC: 352 600 en stock, 0,0041 USD. (El 0603 anterior, C22984 de 30 kΩ, también es básica.)

Cálculo con SLVSD38C, sección 9.2.2.8 (leída en el PDF): planta de la ecuación 11 (Rsense 0,08 Ω, polo de la 13, cero de ESR de la 14, RHPZ de la 15), amplificador de la 16 (GEA 190 µS, VREF 1,212 V de la tabla 7.5; REA no publicada, 10 MΩ como en `sim/models/furby.lib`) y red real R24 + C14 4,7 nF + C15 10 pF; D = 1 − η·VIN/VOUT con η 0,9. Esquinas: VIN 2,7 / 3,0 / 3,7 / 4,4 V; IOUT 0,2 / 0,5 / 1,0 A; Cout 42 / 52 / 70 µF efectivos (4 × 22 µF 0805 a 6 V ≈ 13 µF cada uno, ±20 %); L 0,8 / 1,0 / 1,2 µH. Criterio del datasheet: fC ≤ mín(fSW/10 = 96 kHz, fRHPZ/5).

| R24 | fC (ec. 17 y Bode) | fRHPZ/5 en la misma esquina | Margen de fase | Margen de ganancia |
|-----|--------------------|-----------------------------|----------------|--------------------|
| 30 kΩ, nominal (3,0 V, 1 A, 52 µF, 1 µH) | 20,2 kHz | 39,1 kHz | 82,7° | > 20 dB |
| 30 kΩ, peor esquina (2,7 V, 1 A, 42 µF, 1,2 µH) | 22,7 kHz | 26,4 kHz | **79,9°** | 17,0 dB |
| 30 kΩ, fC máxima (4,4 V, 1 A, 42 µF) | 36,7 kHz | 70 kHz | 83,1° | > 20 dB |
| 33 kΩ, nominal | 22,2 kHz | 39,1 kHz | 83,0° | > 20 dB |
| 33 kΩ, peor esquina | 25,1 kHz | 26,4 kHz | **78,8°** | 16,2 dB |
| 33 kΩ, fC máxima | 40,4 kHz | 70 kHz | 82,1° | > 20 dB |

- Con 33 kΩ, fC sube un 10 % (R5 ∝ fC, ecuación 17) y queda **por debajo de fRHPZ/5 y de fSW/10 en las 108 esquinas**; el margen de fase mínimo baja de 79,9° a 78,8° y el de ganancia de 17,0 a 16,2 dB, muy por encima de los 45° y 10 dB que pide el datasheet. La peor esquina (2,7 V con 1 A) ni siquiera es alcanzable: según `sim/RESULTADOS.md` el elevador corta por UVLO antes (VSYS < 2,5 V con 10,2 W); en la esquina realista (3,0 V, 1 A, L +20 %, Cout −20 %) fC = 27,7 kHz frente a 32,6 kHz (85 %).
- Comprobación de C14 y C15 con el valor nuevo: C5 = RO·CO/(2·R5) = 5,94 × 52 µF / 66 k = 4,7 nF (ecuación 18, exacto a 1 A); C6 = RESR·CO/R5 = 5 mΩ × 52 µF / 33 k = 8 pF < 10 pF (ecuación 19: «se puede dejar abierto»; los 10 pF se quedan).
- Simulación repetida con 33 k (`drv8231a_motor.cir`, `arranque_brownout.cir`): arranque 1,00 A, V6 mín. 5,876 V, VSYS 3,314 V; bloqueado 0,935 / 0,998 / 0,742 A, IPROPI 2,246 V, **rizado de V6 119 mV pp** (antes 130); PWM 18 mV pp (antes 19); inversión 1,007 A, V6 5,854–5,967 V; arranque con batería a 3,0 V idéntico (3,33 V, 2,43 V, 14,3 ms, 3,24 V, 3,27 V).
- **Decisión: 33 kΩ (C25779) aplicado** en `fix/furbyboard-m3-a2` `598f268`: `design.py` (RES0402 con C25779 base, R24 «33k»), esquema y PCB regenerados (el diff de la placa, sin UUID y ordenado, son solo las cuatro propiedades de R24; 44 vértices de relleno de 85 099 difieren en 1e-6 mm por el rellenador, con las mismas áreas y trozos), `furby.lib`, `RESULTADOS.md`, NOTAS (decisión y «Cálculos») y README de fabricación (18 referencias extended, carga 55,26 USD, totales ≈ 115–145 / 165–200 USD). E2 repetida sobre los ficheros nuevos (abajo). Ahorro: 3,07 USD por pedido y una referencia extended menos.

## Punto 4 — A1: pads de cable y piezas del borde
J7, J8 y J11 son `Pads_*_P2.54mm` sin cuerpo: el patio no es cobre ni pieza, y lo que importa al fresado es el cobre, que queda a 0,344–0,446 mm (≥ 0,3 del DRC y ≥ 0,2 de JLCPCB; en el peor caso de ±0,2 quedan ≥ 0,14 de FR-4 y, si el fresado se comiera 0,05 del anillo exterior de un pad de cable, la soldadura del cable no se ve afectada). J9 está a 0,72. J1 es el USB-C de montaje medio con la regla propia del fabricante del conector (0,14 a la ranura) y U4 lleva la antena fuera de la placa por diseño, los dos aceptados en C. **Aceptable para JLCPCB; no hace falta mover nada.** Como mejora (v1.1) queda lo que ya propone el autor: si se reabre el rutado del borde, pads de cable a ≥ 0,5 del contorno.

## Punto 5 — Regresiones
| Comprobación | Resultado |
|--------------|-----------|
| ERC / DRC con paridad | 0/0 y 0/0/0 (arriba) |
| `revisar-rutado` | 0 errores; 152 avisos = 151 + R23:1 (0,225 en el eje del pad, aceptado en NOTAS) |
| `comprobar-flujo` | Sin cruces nuevos |
| Rellenos (`zonas_rev.py`, `402eeb9` → `3807781`) | In1 e In4 **3313,1 mm² en 1 trozo** (sin cambio); GND B.Cu 2773,2 → 2773,3 en 10; VSYS In2 2619,0 → 2617,8 en 3; BAT F.Cu 31,2 en 1; **GND F.Cu 2082,9 en 21 → 2080,3 en 19**. Trozo a trozo en la esquina: la bolsa de C18.2 (4,30 mm², 1 vía) **se une** al trozo grande (65,3 → 70,3 mm², ahora con C18.2, C12.2, C15.2, R22.2, C14.2, R25.2, R7.2, R12.2 y 9 vías) y la bolsa de C16.2 (3,99 mm², 2 vías) **se une** a la de R23.2 (6,34 → 6,99 mm², con R23.2, C16.2 y 3 vías). Los 11 trozos restantes de la esquina son los mismos de antes. **Son uniones, no islas borradas**; ningún pad de GND queda en un trozo sin vía (los dos trozos sin vía, U2.4 0,48 mm² y U2.15/17 con 5 vías, ya estaban así) |
| Dedo entre R40/R42/R50 | Visto en los PNG de F.Cu antes y después: la franja de 0,25 mm entre las dos columnas de pads desaparece; no contenía pads ni vías de GND |
| Paralelos In2/In3 (`paralelos_rev.py`) | **21 pares, idénticos antes y después** (mi criterio da 21 frente a los 19 del autor por contar también dos pares de EN‖U0RX/U0TX ya en la tabla de NOTAS; lo que importa es que no hay ninguno nuevo). ENC_IO (In3) ‖ HOME_PAD (In2): 0,375 de eje a eje en 1,545 mm, por debajo de los 2 mm del criterio |
| ENC_IO frente a la vía de TUMMY | 0,225 mm borde a borde (antes 0,475); clearance de diseño 0,15: DRC 0 |
| ILIM entre los pads de C16 | 0,245 al pad 1 (VSYS) y 0,405 al pad 2 (GND), borde a borde; entra en R23.1 por su eje desde el sur |
| Vías de la esquina | Solo se mueven las de HOME (−46,35; −112,75), HOME_PAD (−43,825; −114,0) y GND de R23.2 (−44,65; −114,845); las 27 restantes (GND, VSYS, V6, EN_6V, TUMMY, TUMMY_PAD) están donde estaban |
| Keepouts | Área de la antena (24 × 17 mm, 6 capas): **sin pistas, vías, pads ni relleno** a más de 0,05 mm dentro del borde; H1–H4 (Ø5, F/B): solo el propio taladro. Área del logo (B.Cu): tiene un tramo y relleno de GND dentro porque solo prohíbe huellas, como antes de M3 (no afecta) |
| `comprobar_colocacion.py` | No repetido por mí (el autor lo arregló para R_0402 y el logo); las alturas de la esquina no cambian con M3 |

## Punto 6 — E2 sobre los ficheros (`e558d6a` y, repetida, `598f268`)
| Comprobación | Resultado |
|--------------|-----------|
| Origen | Gerber, taladros (`--drill-origin plot`) y CPL con el origen auxiliar (220; −40); `cpl-rotaciones` lo confirma |
| Gerber ↔ placa | R24, R23 y R50 con sus flashes de F.Cu, F.Mask y F.Paste en las posiciones de la PCB (tabla del punto 2; R23 en (−45,25; −115,895/−114,245), R50 en (−45,475/−44,45; −112,75)); zip = carpeta (18 ficheros, byte a byte); 383 PTH + 4 NPTH, como en M7/M1 |
| Gerber de `598f268` ↔ `e558d6a` | Comparados por geometría (flashes, trazos y regiones con la forma de su apertura): **idénticos** en las 13 capas y los dos mapas de taladros salvo 4 polígonos de relleno con vértices que difieren en 1e-6 mm; taladros idénticos sin los comentarios de fecha |
| BOM | 52 líneas, 126 piezas, sin líneas repetidas, sin DNP; BOM = CPL = huellas con campo LCSC (126); 18 extended en `598f268` (19 en `e558d6a`) |
| CPL | 126 líneas; R24 a 180° (0402 sin polaridad, como el 0603 que sustituye); sin cambios entre `e558d6a` y `598f268` |
| README de fabricación | Coste, lista «Confirmar antes de pedir» y tabla de la BOM actualizados en `598f268` |

## PNG leídos
| PNG | Qué se ve | Pasa |
|-----|-----------|------|
| Esquina del elevador, F.Cu (antes y después, 60 px/mm) | Antes: R24 0603 con los pads casi en el contorno y una bolsa de GND bajo C18.2. Después: R24 0402 bajo C15; COMP recto desde C15.1 con la diagonal final; RC al oeste y a 45° hasta la fila de C14; franja de GND continua bajo R24 hasta la zona de C18. Solo 0°/45°/90°, sin escaleras ni agudos | Sí |
| Esquina, F.CrtYd | R24 pequeño bajo C15 con hueco al contorno; R23 separado del arco; sin solapes | Sí |
| Esquina, todo el cobre | Lo de arriba con In2 y B.Cu: nada nuevo sobre el nodo SW ni sobre el lazo VOUT–C18–GND | Sí |
| Esquina, In2 | Diagonal de HOME a 45° hasta su vía; nada más cambia en el plano de VSYS | Sí |
| Esquina, In3 | Solo vías en la ventana | Sí |
| Esquina, B.Cu | V6 por y −118,0 con las vías dobles de C18 y EN_6V por x −48,4, sin cambios | Sí |
| Esquina, F.Silkscreen | Solo marcas de pasivos y el pin 1 de U5; nada sobre pads ni vías (DRC con `silk_over_copper` en error) | Sí |
| Zona R50/R23/J9, F.Cu (antes y después) | R23 0,30 más arriba con su stub de GND a 45° al SE; ILIM entre los pads de C16 y entrada por el eje; el dedo de 0,25 mm entre las columnas de R40/R42/R50 desaparece | Sí |
| Zona R50/R23/J9, In2 | Columna de HOME_PAD por x −43,825 entre las vías de TUMMY y TUMMY_PAD hasta el canal de J9 | Sí |
| Zona R50/R23/J9, In3 | ENC_IO baja por x −44,2 a la fila de y −109,3 y su vía; TUMMY_PAD por el canal | Sí |
| Zona R50/R23/J9, F.CrtYd | R23, R50, R42, R40 y JP4 sin solape (huecos de centésimas) | Sí |
| Gerber de la esquina (F.Cu + Mask + Paste + Silk + Edge, `e558d6a` y `598f268`) | Mismos pads, pistas y contorno que los PNG de la placa; máscara y pasta sobre los dos pads del 0402 | Sí |
| Gerber de la zona R50/R23/J9 | Igual que la placa; R23 con sus dos flashes y la pista de ILIM | Sí |

## Hallazgos
| ID | Severidad | Área | Hallazgo | Evidencia | Verificado / supuesto | Corrección propuesta | Estado |
|----|-----------|------|----------|-----------|-----------------------|----------------------|--------|
| A1 | Mejora (aceptada) | DFM, borde | Patios de J7, J8 y J11 a 0,0–0,1 mm del contorno (J11 con un vértice 0,11 fuera) y su cobre a 0,34–0,45; J1 y U4 en el borde por diseño | Volcado propio | Verificado | Nada para la v1.0 (punto 4). v1.1: pads de cable a ≥ 0,5 si se reabre el rutado del borde | Cerrado (v1.1) |
| A2 | Mejora | Coste | R24 en 0402 era extended (+3,07 USD por pedido) | API de JLCPCB; cálculo del lazo (punto 3) | Verificado | 33 kΩ C25779 básica: **aplicado** en `fix/furbyboard-m3-a2` `598f268` | Cerrado |
| A3 | Mejora | R23 | Patio a 0,40 (pads 0,83, cuerpo 1,00) por las vías de VSYS de C16.1 y por R50 | Volcado propio | Verificado | v1.1: alimentar C16.1 desde el norte, como propone el autor | Abierto (v1.1) |
| A4 | Mejora (nueva, documental) | pcb-toolkit | `giros-jlcpcb.toml` sin los 0402 C25105 (R59, R60) ni C25779 (R24): 3 avisos `giro-sin-tabla` en cada E2 | `cpl-rotaciones` | Verificado | Añadirlos al toolkit con giro 0/180 comparado contra la huella EasyEDA (ya en «Pendiente» de NOTAS; C25776 sustituido por C25779) | Abierto (toolkit) |

## Checklist de la puerta (E1 y E2, puntos tocados por M3)
| Sev. | Punto | Resultado |
|------|-------|-----------|
| C | DRC con paridad 0/0 y rellenos no desfasados | OK (0/0/0; copia rellenada idéntica) |
| C | `revisar-rutado --ancho` 0 errores; anchos en el `.kicad_dru` | OK (0 errores; `.kicad_dru` sin cambios) |
| C | `pcb-toolkit.toml` sin reglas apagadas | OK, sin cambios |
| C | Huella y pieza comprobadas (0402 de KiCad; C25776 y C25779 en LCSC y JLCPCB) | OK |
| C | Keepout de antena en todas las capas sin cobre | OK (volcado) |
| C | `comprobar-flujo`: ningún bus cruza una zona caliente nueva | OK |
| I | Convertidor como su referencia; compensación corta (COMP 3,9 mm, RC 2,3 mm) y lejos de L2 | OK |
| I | Plano continuo; sin islas ni dedos nuevos | OK (dos uniones, un dedo menos) |
| I | Paralelos In2/In3 | OK, idénticos |
| I | Cálculo clave escrito en NOTAS («Cálculos»: lazo del elevador) | OK (añadido en `598f268`) |
| I | Simulación de lo crítico tras el cambio de valor | OK (repetida con 33 k) |
| C (E2) | Mismo origen; CPL por geometría | OK |
| I (E2) | BOM agrupada; DNP fuera; README con coste | OK |
| C | `TEST-PLAN.md` (sin cambios por M3/A2; el escalón de carga de §10 valida el lazo en el bring-up) | OK |

## Revisión final como revisor senior
- «Isla borrada en silencio» (FurbyBoard, 2026-10-25): medido trozo a trozo con sus pads y vías; los dos trozos que desaparecen se unen a otros con vía.
- «Vía de otra red fuera de la ventana» (2026-10-27): volcadas las 30 vías de la esquina (x > 160, y > 66): solo se mueven las tres previstas.
- «Código de pieza inventado»: C25776, C25779, C25105 y C22984 comprobados en las dos API el 2026-10-27 (valor, encapsulado y clase).
- «Piezas giradas en el CPL; Gerber y CPL con distinto origen»: origen común y 0402 sin polaridad; el CPL no cambia con A2.
- «Herramienta de pipx desfasada»: todo con el pcb-toolkit del venv (`PCB_TOOLKIT`).
- «Regeneración no determinista»: el diff bruto de la placa regenerada es enorme (orden de huellas y UUID); por eso se comparó sin UUID y ordenado, y los Gerber por geometría. Conviene anotarlo en `kicad-automatizacion.md` como trampa conocida.
