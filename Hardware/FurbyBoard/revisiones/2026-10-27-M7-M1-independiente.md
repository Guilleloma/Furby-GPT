# Revisión independiente de las mejoras M7 y M1 (E1 y E2 repetidas sobre los cambios) — FurbyBoard v1.0

- Fecha: 2026-10-27 · Commits revisados: `f2f73dd` (M7), `4156112` (M1), `28fb821` (fabricación regenerada) y `f64f744` (documentación), rama `fix/furbyboard-m7-m1` desde `trunk` `7f1f637` · Revisor: electronics-engineer, revisor independiente (modelo T0, Fable 5.1), sin participación en M7 ni en M1
- Tipo de placa: L · Capas: 6 (JLC06161H-7628) · Fabricante: JLCPCB (Economic a una cara)
- Material revisado: `scripts/design.py`, `layout.py`, `rutas_fijas.py` y `pcb-toolkit.toml` (diff de los cuatro commits), `hojas/camara.kicad_sch` y `hojas/mcu.kicad_sch`, `FurbyBoard.kicad_pcb` (la de `f64f744` y, para comparar, la de `7f1f637` y la de `f2f73dd`), `fabricacion/` completa, `NOTAS.md`, `README.md`, `TEST-PLAN.md`, `revisiones/2026-10-27-M7-M1.md` y `2026-10-25-E-independiente.md`; herramientas vueltas a ejecutar sobre una copia en el scratchpad; **volcado propio con pcbnew** en subproceso (1061 pistas, 334 vías, 526 pads, 158 huellas, 6 rellenos, 6 áreas de reglas) y **scripts propios** de paralelos In2/In3, holguras pista‑vía y pista‑pista, rellenos, keepout de la antena y cotejo numérico de los Gerber con la placa (sin usar los scripts del autor); hoja del DRV8231A (SLVSFZ8A, enero de 2026) leída para IPROPI; 11 PNG propios y 2 raster locales de los Gerber. Coordenadas en el sistema del STL (x_kicad = x + 220, y_kicad = −40 − y). Skills cargadas: hardware-design-review (con `revision-de-diseno.md`, `plantilla-informe-revision.md`, `kicad-automatizacion.md` §1.1, §5, §6.1 y §10, `diseno-de-circuito.md` §7.3).

## Resultado
**PASA** — 0 críticos, 0 importantes, 2 mejoras (documentales, las dos resueltas en esta misma rama: cifra de NOTAS y una línea más en TEST-PLAN §14).

Todo lo que afirma el autor en `2026-10-27-M7-M1.md` se reproduce con mediciones propias: ERC 0, DRC con paridad 0/0/0 con el relleno guardado idéntico al de kicad-cli, `revisar-rutado` 0 errores y los mismos 151 avisos, `comprobar-flujo` solo con los dos cruces ya aceptados en NOTAS, kicad-happy sin críticos, rellenos con los mismos trozos y áreas (ningún trozo nuevo), antena limpia en las 6 capas, **19 pares paralelos In2/In3** (28 en `trunk`) con las mismas separaciones que la tabla de NOTAS, R59 y R60 en el extremo que genera cada reloj y con la pieza correcta, bus DVP íntegro en F.Cu sobre In1 sin vías nuevas (334), Gerber cotejados pad a pad y pista a pista con la placa, 383 PTH + 4 NPTH, BOM 52/126 y CPL 126 con `cpl-rotaciones` en PASS.

## Herramientas
| Herramienta | Comando | Resultado |
|-------------|---------|-----------|
| Comprobación §1.1 | `kicad-cli version`; pcb-toolkit; kicad-happy; rsvg-convert | kicad-cli 10.0.7 (`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, no está en el PATH del shell); pcb-toolkit 0.1.0 del venv de `~/development/pcb-toolkit` (el de pipx no trae la tabla de giros); kicad-happy v2.3.2 (`2fd9aa0f`); rsvg-convert. **No se instaló nada** (ni gerbonara ni gerbv: los Gerber se cotejaron numéricamente y se rasterizaron con un script propio sobre Pillow del venv de pcb-toolkit) |
| ERC | `kicad-cli sch erc --severity-all --format json` | **0** infracciones |
| DRC, placa guardada | `kicad-cli pcb drc --schematic-parity --severity-all --format json` | **0 infracciones, 0 sin unir, 0 de paridad** |
| DRC, relleno de kicad-cli | `--refill-zones --save-board` sobre una copia completa | **0 / 0 / 0** y la copia rellenada es **idéntica byte a byte** a la guardada (`cmp`) |
| Flujo | `pcb-toolkit comprobar-flujo --json --png` (venv, mide el cobre) | FAIL con los **2 errores ya aceptados** en NOTAS (I2S_DIN a 0,40 del clase D; MOT_VREF a 2,58 de L2) y los 4 avisos de desacoplo (C10 1,90; C32 1,08; C22 1,23; C2 1,15); nada nuevo. (El informe del autor los llama «avisos»: en la salida de la herramienta son errores, aceptados en NOTAS «Avisos aceptados») |
| Geometría | `pcb-toolkit revisar-rutado --tp-max 5 --json` (anchos de `pcb-toolkit.toml`) | **PASS: 0 errores, 151 avisos** (entrada-asimétrica 36, descentrada 32, rodeo 27, cuello 21, roce-vía 15, roce-pad 10, pista-entre-pads 6, ancho-mayor-que-pad 3, colineales 1): los mismos que el autor |
| Configuración | `pcb-toolkit.toml` frente a `7f1f637` | Solo cambia `CAM_PCLK`/`CAM_XCLK` → `CAM_PCLK*`/`CAM_XCLK*` en `criticas` y en el grupo DVP (cubre las redes cortas de las series); ninguna regla en `off` ni umbral relajado |
| CPL | `pcb-toolkit cpl-rotaciones cpl-jlcpcb.csv FurbyBoard.kicad_pcb --bom … --gerber …` | **PASS, 0 errores, 2 avisos** `giro-sin-tabla` (R59, R60: C25105, 0402 sin polaridad, giro 0); origen del CPL = origen del Gerber (220; −40), eje Y hacia arriba; 99 montado-verificado, 25 comparado-sin-montar |
| Análisis | `kicad-happy.sh analizar` sobre la copia | Sin críticos; consistencia 152 símbolos / 158 huellas (= 152 + H1–H4 + LOGO1 + LOGO2); BOM 126/126 con MPN; EMC 43/100 sin críticos |
| Volcado y geometría propios | pcbnew en subproceso (`os._exit`) + Python del sistema | Paralelos In2/In3 (criterio ≤ 8°, solape ≥ 2 mm, borde a borde < 1 mm) en `7f1f637` y en `f64f744`; holguras pista‑vía de los 11 movimientos de M1; mínimos globales pista‑vía y pista‑pista por capa; rellenos por red y capa; cobre dentro del keepout de la antena; capas, vías y longitudes del DVP; holguras de los pads de R59/R60 |
| Gerber | Script propio (RS‑274X: aperturas, D03, D01, G36/G37) frente al volcado | F.Cu: 815 flashes, 592 dibujos, 27 regiones; **los 592 dibujos coinciden uno a uno con las 592 pistas de F.Cu** (extremos a < 5 µm y mismo ancho); todos los pads de F.Cu tienen su flash a < 10 µm salvo H1–H4 (NPTH sin cobre, no se flashean). F.Mask y F.Paste: flashes de R59/R60 en (−72,875; −82,35), (−71,855; −82,35), (−54,11; −78,0) y (−53,09; −78,0) con la apertura RoundRect de 0,54 × 0,64 (r 0,135). Taladros: PTH 383 (0,2 × 3; 0,3 × 331; 0,8 × 4 ranuras; 1,0 × 44; 1,2 × 1), NPTH 4 (2,3): = 334 vías + 53 pads pasantes del volcado |
| PNG | `pcb-toolkit capturas` (F.Cu a 80 px/mm de R59 y R60; In2+In3 a 30 px/mm de las 7 zonas de M1) + 2 raster locales de los Gerber (F.Cu, F.Mask, F.Paste) | 11 leídos y comentados (sección «PNG leídos») |

## Hallazgos
| ID | Severidad | Área | Hallazgo | Evidencia (datasheet, cálculo, PNG, medida) | Verificado / supuesto | Corrección propuesta | Estado |
|----|-----------|------|----------|---------------------------------------------|-----------------------|----------------------|--------|
| M1 | Mejora (documental) | NOTAS «Paralelos In2/In3 aceptados», fila 3 (IPROPI ‖ CAM_EN) | La conclusión (aceptable) se sostiene, pero la cifra «< 5 mV durante < 2 ns» es optimista. Con ≈ 0,3 pF de acoplo (9,4 mm a 0,5 mm de borde, planos In1/In4 a 0,4 mm) y el flanco del TCA9535 (push‑pull, ≈ 20–50 ns), la corriente inyectada es C·dV/dt ≈ 0,3 pF × 3,3 V / 30 ns ≈ 30 µA sobre el nodo IPROPI (R28 1,5 kΩ ‖ ≈ 10 pF, τ ≈ 15 ns): **≈ 20–50 mV durante ≈ 30–50 ns**, una vez por encendido de la cámara. Sigue sin importar: equivale a ≤ 25 mA de ITRIP durante < 0,1 µs frente a **tBLK 1,4 µs y tDEG 0,7 µs** del comparador de ITRIP (DRV8231A, SLVSFZ8A, tabla 6.5), y el ADC muestrea a ≤ 1 kHz con promedio (regla 6 del firmware) | Cálculo propio; hoja del DRV8231A leída (`pdftotext`, líneas tOFF 25 µs, tBLK 1,4 µs, tDEG 0,7 µs); la capacidad de acoplo, estimada (sin simulador de campo) | Sustituir la cifra de la fila 3 por la de este hallazgo y citar tBLK/tDEG | **Corregido en esta rama** (commit de documentación de esta revisión) |
| M2 | Mejora | TEST-PLAN §14 | La medida de flancos de §14 solo mira los dos relojes (R59, R60). Los datos y HREF/VSYNC van sin serie (decisión razonable, ver «M7»); conviene mirar también un dato (Y7, la línea más larga tras XCLK/Y8/Y9, 22,9 mm) en el pad 16 de J6 y en el pin 23 del módulo durante la foto SVGA | Longitudes del volcado; `diseno-de-circuito.md` §7.3 («y de los datos si hace falta») | Verificado (longitudes) | Añadir a la fila de §14: «y un dato (Y7) en el pin 23 del módulo: sin escalón a mitad de flanco» | **Añadido a TEST-PLAN §14 en esta rama**; la medida queda para el bring-up (no bloquea el pedido) |

## M7: series de 33 Ω en los relojes del bus DVP
| Qué se pidió comprobar | Medida propia | Veredicto |
|------------------------|---------------|-----------|
| Esquema = PCB | `design.py`: `R0402("R59", "CAM_XCLK_IO", "CAM_XCLK")`, `R0402("R60", "CAM_PCLK", "CAM_PCLK_CAM")`; pin 21 del módulo → `CAM_XCLK_IO`; J6.17 → `CAM_PCLK_CAM`. Volcado: U4.21 = CAM_XCLK_IO, R59.1 = CAM_XCLK_IO, R59.2 = CAM_XCLK, J6.13 = CAM_XCLK; U4.24 = CAM_PCLK, R60.1 = CAM_PCLK, R60.2 = CAM_PCLK_CAM, J6.17 = CAM_PCLK_CAM. Paridad DRC 0; ERC 0; `hojas/camara.kicad_sch` con R59/R60 y `LCSC = C25105`; `hojas/mcu.kicad_sch` con la etiqueta global `CAM_XCLK_IO` | OK |
| Cada serie en el extremo que genera la señal | XCLK lo genera el ESP32: R59 en (−72,365; −82,35) a 0°, pad 1 a 1,8 mm de pista del pin 21 (red corta CAM_XCLK_IO) y pad 2 al bus (CAM_XCLK, 23,2 mm hasta J6.13). PCLK lo genera la cámara: R60 en (−53,6; −78,0) a 0°, pad 2 a 2,6 mm del pad 17 de J6 (CAM_PCLK_CAM) y pad 1 al bus (CAM_PCLK, 17,7 mm hasta U4.24). En esta placa el «origen» de PCLK es el conector del FPC: R60 está lo más cerca posible de él | OK |
| Pieza C25105 | Huella `Resistor_SMD:R_0402_1005Metric` en la PCB (pads 0,54 × 0,64 a 1,02 de paso) y en la BOM (`33, R59,R60, R_0402_1005Metric, C25105`); valor 33 en el símbolo y en la BOM; `design.py` anota básica y 2 162 519 en stock el 2026-10-27 (**no vuelto a consultar**: el stock y la clase se confirman el día del pedido, como las demás piezas) | OK (stock: supuesto del autor con fecha) |
| Orientación en el CPL | `R59,-72.365mm,-82.350mm,Top,0.0` y `R60,-53.600mm,-78.000mm,Top,0.0` = posición y giro de la PCB; 0402 sin polaridad; `cpl-rotaciones` PASS con el aviso de código sin tabla | OK |
| Bus DVP en F.Cu sobre In1, sin vías nuevas | Las 14 redes CAM_* del bus (12 líneas + las dos cortas) **solo en F.Cu**; 0 vías en esas redes; 334 vías en total (= `7f1f637`); In1 en **1 trozo de 3313,1 mm²** (sin ranuras bajo el bus). Longitudes: Y2 16,0 … VSYNC 29,2; XCLK 1,8 + 23,2; PCLK 2,6 + 17,7 | OK |
| Holguras junto a R59/R60 | R59: Y9 (x −73,635) a 0,415 del pad 1, Y8 (x −71,095) a 0,415 del pad 2, diagonal de XCLK_IO de 0,72 mm al eje del pin 21; R60: Y6 (y −77,25) a 0,355, Y7 (y −78,6) a 0,205 (≥ 0,15 de holgura del proyecto; por eso `revisar-rutado` no lo lista como roce). Mínimo global pista‑pista de F.Cu 0,150 (USB_DP/USB_DN, el par acoplado) y pista‑vía 0,168 | OK |
| Valor 33 Ω | IPC‑2141 recalculado: Z0 = 87/√(4,4 + 1,41) · ln(5,98 · 0,2104 / (0,8 · 0,15 + 0,035)) = 36,1 · 2,09 ≈ **75,6 Ω**. Con Rout ≈ 30–40 Ω (ESP32‑S3 al drive por defecto, estimación del autor, marcada como tal; no la he medido en la hoja, que da IOH por nivel de drive y no Rout) Rs + Rout ≈ 63–73 Ω ≈ Z0: amortiguamiento de fuente correcto, sin pasarse. τ = 33 Ω × 10 pF = 0,33 ns ≪ 50 ns de periodo. Para la OV2640 (DOVDD 3,3 V, Rout ≈ 40–50 Ω) 33 + 45 ≈ 78 Ω, también ≈ Z0 | OK (Rout: supuesto; se mide en TEST-PLAN §14 y hay 22/47 Ω de recambio) |
| HREF, VSYNC y datos sin serie | Razonable: HREF/VSYNC conmutan a frecuencia de línea y cuadro; los datos (16–29 mm, tpd ≈ 0,1–0,2 ns) los genera la cámara en un flanco de PCLK y los muestrea el ESP32 en el contrario, con ≥ 20 ns de margen a 24 MHz; cualquier anillo se extingue en < 2 ns. Es lo que hacen los módulos de referencia (ESP32‑CAM, ESP32‑S3‑EYE). Ocho 0402 más no caben en el corredor de 0,3 mm de paso sin rehacer el bus | OK (M2: mirar un dato en el bring‑up) |

## M1: paralelos In2/In3
Volcado y script propios (segmentos In2 frente a In3 a ≤ 8°, solape de proyección ≥ 2 mm, borde a borde = distancia entre ejes − (w1 + w2)/2 < 1 mm, agrupados por par de redes):

- **`7f1f637` (antes): 28 pares de redes** (30 pares de segmentos), los mismos 28 de la revisión E independiente.
- **`f64f744` (ahora): 19 pares de redes** (20 pares de segmentos). Los 9 que desaparecen son exactamente los 9 de la tabla del autor: VBAT_SNS ‖ U0RX (antes 11,4 a 0,46), VBAT_SNS ‖ BQ_EN1 (14,3 a 0,97), I2S_DIN ‖ EN_6V (3,7 a 0,95), BQ_TS ‖ LED_CHG_A (6,5 a 0,70), VBAT_SNS ‖ TUMMY (2,6 a 0,85), 3V3 ‖ CAM_PWDN (9,7 a 0,95), 3V3 ‖ CAM_EN (2,3 a 0,90), I2S_BCLK ‖ EXP_P07 (4,5 a 0,75), MOT_IN2 ‖ HOME (4,4 a 0,50); CAM_2V8 ‖ CAM_EN baja de 4,1 mm a 0,275 (2 segmentos) a 2,0 mm a 0,775 (1 segmento, el tramo sur, fila 4 de NOTAS).
- **Los 19 que quedan, medidos (solape máx / borde mín):** EN ‖ U0RX 13,3 / 0,40 (y 2,0 / 0,20 en x −82,4…−84,4) · IPROPI ‖ CAM_EN 9,3 / 0,50 · I2C_SCL ‖ I2C_SDA 5,1 / 0,83 · EXP_INT ‖ IR_RX 4,9 / −0,165 · HOME_PAD ‖ TUMMY_PAD 4,8 / −0,20 · EXP_INT ‖ TUMMY 4,8 / 0,55 · HOME ‖ BACK 4,6 / 0,25 · EXP_INT ‖ BACK 4,2 / 0,09 · EN ‖ U0TX 4,1 / −0,175 · CC1 ‖ CC2 3,8 / −0,10 · EXP_INT ‖ CAM_PWDN 3,6 / −0,05 · I2C_SCL ‖ LED_RUN_K 3,3 / 0,73 · 3V3 ‖ LED_RUN_K 2,9 / 0,85 · I2C_SDA ‖ IR_RX 2,8 / 0,435 · CAM_DVDD ‖ ENC_IO 2,8 / −0,20 · ENC_PT ‖ TUMMY_PAD 2,5 / −0,20 · HOME ‖ TUMMY 2,4 / −0,20 · 3V3 ‖ IR_TX 2,3 / 0,85 · CAM_2V8 ‖ CAM_EN 2,0 / 0,775. **Coinciden con las 19 filas de NOTAS** (misma pareja, misma longitud y misma separación, redondeos aparte).
- **Clases:** ninguno de los 19 lleva una red de `criticas` (B, C o D) salvo IPROPI (fila 3). Comprobado contra la lista de `pcb-toolkit.toml`.
- **Justificaciones juzgadas una a una:** las 18 sin red crítica son parejas de nivel estático (EN con 1 µF, enables, Rd de CC, raíles desacoplados) o de interruptor filtrado (1 kΩ + 10–100 nF) con señales lentas (UART 115 200, I2C 400 kHz, IR 38 kHz, LED de 1 Hz), y en todas la geometría es la que dice NOTAS (vías o canal único; lo he comprobado en el volcado para EN/U0RX/U0TX bajo la antena, para el canal de J9 y para el carril de x −48,3/−48,75). Las tres que pedía mirar: **EN ‖ U0RX/U0TX**: EN es la entrada de reset del módulo con 10 kΩ/1 µF; 0,4 pF × 3,3 V sobre 1 µF son ≈ 1 µV, y en sentido contrario EN no conmuta; la UART solo vive con el adaptador puesto. Aceptable. **EXP_INT ‖ IR_RX** (4,9 mm superpuestas): ≈ 0,5 pF sobre un nodo de ≈ 10 pF con pull‑up de 10 kΩ → ≤ 0,15 V durante decenas de ns frente a VIL 0,8 V (y el umbral real del ESP32‑S3 ≈ 1,2–1,6 V); la interrupción se filtra con antirrebote ≥ 30 ms y el despertar es por nivel. Aceptable. **IPROPI ‖ CAM_EN**: aceptable con la cifra corregida (hallazgo M1); se confirma que CAM_EN no tiene otro carril: entre el borde del agujero (x −55,23) y las vías de x −53,39/−52,78/−51,83 hay un carril por capa, y la columna de vías de x −54,375 (paso 0,75, antipad 0,55) cierra el paso a la diagonal de vuelta a R33.
- **Por debajo del umbral (no cuentan, pero mirados):** los cuatro que lista el autor (U0RX ‖ EN 2,0 a 0,20 va dentro de la fila 1; CAM_EN ‖ CAM_2V8 1,1 a 0,275; CAM_2V8 ‖ CAM_EN 0,9 a 0,8; VBAT_SNS ‖ ENC_IO 1,6 a 0,7) salen igual en mi volcado.
- **Holguras de los 11 movimientos de M1** (borde a borde, Ø0,6 de vía): BQ_TS 0,225 a la vía de GND (−69,5; −113,425); LED_PG_A 0,200 a (−69,225; −116,3); I2S_BCLK 0,202 a (−93,4; −91,95); CAM_EN 0,250 a la vía de 3V3 (−50,65; −87,8) y 0,303 a la de GND (−51,6; −88,6); EN_6V 0,243 a (−71,2; −99,1); U0RX 0,210 a (−83,0; −62,99); HOME 0,500 a la vía de MOT_IN1 (−66,325; −88,95); VBAT_SNS 0,400 a la de ENC_IO (−79,6; −75,3); BQ_EN1 0,750 a las dos de 3V3 (−85,5; −86,3/−90,5). Todas ≥ 0,15 del proyecto y ≥ 0,2 salvo las tres de 0,200–0,210 (que `revisar-rutado` ya lista como roce‑vía dentro de los 15 aceptados). Mínimos globales: pista‑vía F 0,168 / In2 0,200 / In3 0,150 (I2C_SCL contra la vía de 3V3 (−45,0; −79,5), preexistente) / B 0,165; pista‑pista F 0,150 (par USB) / In2 0,200 / In3 0,200 / B 0,160.
- **Vías de retorno de la clase D:** ninguna vía se ha movido (334 posiciones iguales a `7f1f637`): las distancias medidas en la re‑revisión del 2026-10-25 siguen vigentes.

## Regresiones
| Qué | Medida | Veredicto |
|-----|--------|-----------|
| Rellenos | GND F 2082,9 mm² en 21 trozos (antes 2084,6: antipads de R59/R60), GND B 2773,2 en 10, In1 e In4 3313,1 en **1 trozo** cada una, VSYS In2 2619,0 en 3 (antes 2616,3), BAT F 31,2 en 1. Mismo número de trozos por red y capa que en `7f1f637`; trozo mínimo de GND F 0,2 mm² (el mismo de siempre) | OK, ningún trozo ni isla nuevos |
| Keepout de la antena (x −85…−61, y > −62) | Área de reglas en las 6 capas con pistas, vías, relleno y pads prohibidos; **0 pistas, 0 vías, 0 pads y 0 vértices de relleno** dentro (margen 0,05) en las 6 capas | OK |
| Otras áreas de reglas | 4 keepouts de cabeza de tornillo (F y B, 5 × 5) y el del logo en B.Cu: iguales | OK |
| DVP sobre In1 | In1 continuo (1 trozo); bus solo en F.Cu | OK |
| Serigrafía | DRC con `silk_over_copper`/`silk_overlap` en error: 0 | OK |
| Datos personales | `grep -r '/Users/'` en `Hardware/FurbyBoard`: nada | OK |

## E2 sobre los ficheros regenerados (`28fb821`)
| Comprobación | Resultado |
|--------------|-----------|
| Rellenos al día | Copia rellenada por kicad-cli idéntica a la placa guardada (y `make_fab.sh` lo exige) |
| ERC/DRC de `fabricacion/` | `erc.rpt` y `drc.rpt` del commit sin infracciones; repetidos aquí: 0/0/0 |
| Gerber frente a la placa | Cotejo numérico (tabla «Herramientas»): 592/592 pistas de F.Cu y todos los pads con su flash; R59/R60 en F.Cu, F.Mask y F.Paste en las cuatro posiciones con la apertura del 0402. Raster local de las dos ventanas leído (abajo). Pads sin flash en F.Paste: U2.17, U6.9, U7.17 (pads expuestos con la pasta partida), JP1/JP5 (puentes, sin pasta) y U5.5 (apertura reducida a 0,04 del centro): todos anteriores a M7/M1 y correctos |
| Taladros | 383 PTH + 4 NPTH, iguales a la E2 del 2026-10-25 y al volcado (334 vías + 44 + 4 + 1 + 4 pads pasantes) |
| Origen | Gerber y taladros con el origen auxiliar (220; −40) = CPL (`cpl-rotaciones`: origen común, Y hacia arriba) |
| CPL | 126 filas = 126 huellas con LCSC; posiciones iguales a la PCB salvo **J1 y U4**, cuyo origen corrige `jlc_post.py` a propósito (desplazamientos de 4,7 y 3,6 mm, los mismos que en la E2 anterior); giros corregidos en 9 códigos (los de siempre) |
| BOM | 52 líneas, 126 piezas; BOM = CPL = huellas con LCSC (sin sobras ni faltas); línea nueva `33, R59,R60, R_0402_1005Metric, C25105` |
| README de fabricación | Fecha, commit, 52/126, C25105 en la tabla de piezas, R59/R60 en «Revisar en el visor» y «Confirmar antes de pedir», coste | OK |
| Documentación | README (Resumen, bloque Cámara, tablas de J6 y del módulo, GPIO13/GPIO47), NOTAS (Estado, Decisiones, Cálculos, «Paralelos aceptados», Revisiones) y TEST-PLAN §14 coinciden con `design.py` y con la placa | OK (M1, M2) |

**Pendiente para Guillermo antes de pedir:** nada nuevo. Sigue la lista «Confirmar antes de pedir» de `fabricacion/README.md` (stock de J1, L1, RT1/C440252, C25105 el día del pedido; precio de ENIG y de la vía de 0,2) y, como siempre, mirar R59 y R60 en el visor de JLCPCB (son las dos únicas 0402; sin polaridad).

## PNG leídos
- `png/FurbyBoard-F_Cu-v1` (fila sur del módulo, 80 px/mm): R59 bajo el pin 21; pad 1 sube con la diagonal al eje del pin, pad 2 baja recto a la fila de XCLK; Y9 y Y8 bajan a los lados sin tocar los pads; las filas de Y9/HREF/VSYNC pasan por debajo. Pasa.
- `png/FurbyBoard-F_Cu-v2` (comb de J6, 80 px/mm): R60 entre Y6 (arriba, recta) y Y7 (abajo, con sus dos quiebros más al oeste que los de PCLK); PCLK con los quiebros a 45° a cada lado de R60; el stub de GND de J6.15 a su vía; el resto del comb sin tocar. Pasa.
- `png/gerber-R59` y `png/gerber-R60` (raster propio de los Gerber: F.Cu rojo, F.Mask verde, F.Paste azul, 80 px/mm): la misma geometría que los PNG de la placa; máscara y pasta sobre los cuatro pads del 0402 y sobre los pads del módulo y de J6; ningún flash fuera de sitio. Pasa.
- `png-m1/cobre-v1` (banda bajo la antena, In2 + In3): TX y RX en In3 en dos carriles, RX con el quiebro junto a la vía de GND; EN y VBAT_SNS en In2 debajo del relleno de VSYS; cosido en y −64,9. Pasa.
- `png-m1/cobre-v2` (diagonales EN_6V/BQ_EN2/BQ_EN1 y VBAT_SNS): tres diagonales de In3 al NE de la de In2 con separación visible; octógono de HOME. Pasa.
- `png-m1/cobre-v3` (CAM_EN junto a J6/U8): columna de In3 por x −51,3, fila y −87,9 y bajada a la vía de U8.3; CAM_2V8 (In2) al oeste. Pasa.
- `png-m1/cobre-v4` (BQ_TS y LED bajo la batería): fila de BQ_TS en In2 entre sus vías; LED_CHG_A y LED_PG_A en In3 por debajo, en pareja. Pasa.
- `png-m1/cobre-v5` (autopista de In3 bajo U10): tres filas con sus diagonales y las columnas de In2 cruzando a 90°; fila corta de VBAT_SNS arriba. Pasa.
- `png-m1/cobre-v6` (BCLK/U7): columna de BCLK en In2 con la diagonal a su vía; EXP_P07 al oeste; vías de cosido intactas. Pasa.
- `png-m1/cobre-v7` (HOME/MOT_IN2 alrededor del agujero): fila de HOME en In3 con las diagonales; MOT_IN2 en In2 por encima; octógono. Pasa.

## Checklist (puntos tocados por M7 y M1)
| Ref. | Sev. | Punto | Estado |
|------|------|-------|--------|
| 4.2 | I | Series en los relojes de buses paralelos (`diseno-de-circuito.md` §7.3) | OK |
| 4.3 | C/I | MPN, huella, código, clase y stock con fecha | OK (stock: del autor, 2026-10-27) |
| 4.4 | I | Cálculo de Z0 y de Rs en NOTAS | OK (recalculado) |
| 4.6 | C | Keepout de antena en las 6 capas; `comprobar-flujo` | OK (los dos cruces aceptados) |
| 4.6 | I | Desacoplos sin regresión | OK (ninguno se mueve; mismos 4 avisos) |
| 4.7 | C | DRC con paridad 0/0 y rellenos no desfasados | OK (relleno idéntico) |
| 4.7 | C | `revisar-rutado` 0 errores; anchos en el `.kicad_dru` | OK |
| 4.7 | C | `pcb-toolkit.toml` sin reglas apagadas; redes B/C/D en `criticas` | OK (CAM_XCLK*/CAM_PCLK* cubren las redes cortas) |
| 4.7 | I | PNG; plano continuo bajo B/C/D; sin islas; paralelos In2/In3 | OK (19 aceptados, juzgados) |
| 4.8 | C | Gerber, taladros y CPL con el mismo origen; giros por geometría | OK |
| 4.8 | I | BOM agrupada; README de fabricación | OK |
| 4.9 | C/I | TEST-PLAN | OK (M2 como mejora) |

## Revisión final como revisor senior
- **«DRC 0» tomado como calidad:** no se repite: cada cifra del informe del autor se ha vuelto a medir con un volcado y scripts propios, y los Gerber se han cotejado pad a pad y pista a pista además de rasterizarse.
- **Afirmación del autor no medida:** solo una cifra optimista en una justificación (IPROPI ‖ CAM_EN, hallazgo M1), sin cambio de conclusión; corregida.
- **Piezas giradas en el CPL; Gerber y CPL con distinto origen:** comprobado (origen común, 0402 sin polaridad, J1/U4 con la corrección de origen de siempre).
- **Bus rápido por un convertidor, TP lejos, autorrutado:** no aplica a estos cambios (DVP intacto, ninguna vía ni pieza movida salvo las dos 0402 nuevas).
- **Herramienta que faltaba (rasterizar Gerber):** resuelta sin instalar nada; queda la mejora de NOTAS («Pendiente») de tener los paralelos In2/In3 y la rasterización de Gerber como órdenes de pcb-toolkit.
