# FurbyBoard v1.0: notas de diseño

Decisiones, cálculos y revisiones de la placa. La arquitectura (componentes, presupuesto de potencia, costes) está en `../PCB-suelo/ARQUITECTURA.md`; donde no coincidan, manda este fichero y el esquema. Sigue la plantilla `plantilla-notas-pcb` del Cerebro.

## Requisitos
| Requisito | Valor | Origen |
|-----------|-------|--------|
| Entradas y rango | USB-C 5 V (4,75–5,5 V, cargadores baratos hasta 6 V en vacío); LiPo 1S 1400 mAh (3,0–4,2 V) soldada a pads | el autor del proyecto |
| Consumo | Pico 2,9 A en la batería (motor bloqueado + TX + cámara + ampli); media en conversación 0,2–0,35 A; dormido ≈ 80 µA | `ARQUITECTURA.md` §11 (estimado) |
| Entorno | Interior, dentro del Furby, 0–50 °C; la batería tumbada sobre la placa con calzos de 4,1 mm | el autor del proyecto |
| Tamaño, carcasa, holgura | Suelo de la base de un Furby de 1998, holgura 1,0 mm a la pared, 4 × M2, agujero del mecanismo Ø11,3 (`../PCB-suelo/geometria.json`) | el autor del proyecto / medido |
| Cantidad, coste, fabricante | 5 PCB, 2–5 montadas, JLCPCB, montaje Economic a una cara, ≈ 104–152 USD | el autor del proyecto |
| Señales especiales | USB FS (par de 90 Ω), bus DVP de cámara a 20 MHz, 3 convertidores a ≈ 1 MHz y un clase D, antena WiFi del módulo | Diseño |

## Arquitectura
Diagrama de bloques en `../PCB-suelo/ARQUITECTURA.md` §1: USB-C → PTC + ESD → BQ24073 (power path) ↔ batería (P-MOSFET de polaridad) → VSYS → TPS63802 (3V3), TPS61089 (6 V → DRV8231A → motor), MAX98357A (altavoz); ESP32-S3-WROOM-1 (cámara DVP, I2S, I2C al TCA9535).

### Tabla de raíles
| Raíl | Fuente | V ± tol. | I pico (× 1,3 salvo picos simultáneos por diseño) | Regulador | P disipada | Tj peor caso (Ta 50 °C) | Ancho mínimo |
|------|--------|----------|-----------------------------------------------------|-----------|------------|--------------------------|--------------|
| VBUS_IN / VBUS | USB-C, PTC | 5 V ± 5 % | 1,34 A (ILIM) → limitado por el PTC de 1,5 A; por defecto USB500 (0,5 A) | — | PTC ≈ 0,1 W | — | 0,5 |
| BAT / BAT_PAD | Celda y Q1 | 3,0–4,2 V | 2,9 A simultáneos (sin × 1,3) | Q1 9,8 mΩ | 0,08 W | 57 °C | 0,8 + polígono |
| VSYS | BQ24073 OUT | 4,4 V con USB; VBAT − 50 mV sin USB | 2,9 A | BQ24073 | 0,87 W cargando | ≈ 87 °C (θJA ≈ 42 °C/W con pad) | 0,6 + relleno de In2 |
| 3V3 | TPS63802 | 3,30 V ± 2 % | 0,55 A (TX 0,34 + cámara 0,15 + lógica) → 0,7 A | TPS63802 (2 A) | ≈ 0,2 W | ≈ 62 °C | 0,4 |
| V6 | TPS61089 | 5,94 V ± 2 % | 1,0 A (ITRIP); entrada 2,2 A a 3,0 V | TPS61089 (ILIM 3,8 A) | ≈ 0,6 W | ≈ 74 °C | 0,5 |
| CAM_2V8 | ME6211C28 | 2,8 V | 0,1 A | LDO | 0,05 W | 63 °C | 0,3 |
| CAM_DVDD | ME6211C12/C15 | 1,2 / 1,5 V | 0,08 A | LDO desde 2,8 V | 0,13 W | ≈ 82 °C (SOT-23-5, 250 °C/W) | 0,3 |
| MOT_OUT1/2 | DRV8231A | ± 6 V PWM 20 kHz | 1,0 A (3,7 A OCP durante µs) | — | 0,6 W en el DRV | ≈ 76 °C | 0,5 |
| SPK_P/N | MAX98357A | clase D ≈ 300 kHz | 0,9 A de pico | — | ≈ 0,2 W | — | 0,4 |
| IR_LED_A/K | VSYS, R54 | — | 0,1 A en pulsos | — | R54 0,24 W al 33 % | — | 0,3 |
| BST_SW, BB_SW1/2 | Nodos SW | — | 2,8 A / 2 A | — | — | — | 0,8 / 0,6 (cortos, sin vías) |

Los anchos están en `scripts/params.py` (`ANCHOS_MINIMOS`) y de ahí van al `.kicad_dru` (una regla por red) y a `pcb-toolkit.toml`. Dentro de los patios de U2, U3, U5, U6, U7, Q1 y J1 se admite un cuello de ≤ 1 mm (0,25 mm; 0,2 en los pads de 0,3 del USB-C).

### Rúbrica de complejidad
Tipo **L**: 232 conexiones sin contar GND ni planos (≈ 340 con GND), 4 capas, 3 convertidores a ≈ 1 MHz más un clase D, bus DVP a 20 MHz, par USB. Estrategia: lo crítico (clases A–D) explícito y bloqueado en `scripts/rutas_fijas.py` (por reescribir), lo lento con **una** ejecución acotada de Freerouting 1.9.0 por colocación y post-proceso con `pcb-toolkit limpiar-pistas`. Modelo: T0 (fable) para colocación, rutado y revisiones independientes (`revision-de-diseno.md` §6).

## Decisiones
| Fecha | Decisión | Motivo | Quién |
|-------|----------|--------|-------|
| 2026-10-24 | 4 capas (JLC04161H-7628) | Plano de GND continuo bajo USB, cámara y convertidores; ver «Apilado» | agente (encargo 1) |
| 2026-10-24 | Todo el montaje en la cara superior; en la inferior solo TP, logo y serigrafía | Montaje Economic a una cara (≈ 60 USD menos que Standard a dos caras) | agente (replanteo) |
| 2026-10-24 | Replanteo de la planta (sección «Planta») tras dos colocaciones sin converger | Diagnóstico: expansor lejos de sus pads, esquina trasera derecha saturada, sin pasillos | agente (replanteo) |
| 2026-10-24 | GPIO del módulo y puertos del TCA9535 por geometría (sección «Pines») | Evitar cruces; sin tocar strapping, USB ni ADC | agente (replanteo) |
| 2026-10-24 | LED del encoder desde V6 por 470 Ω, sin AO3400A | Misma función (solo luce con el elevador), una pieza menos, no cabía | agente (replanteo) |
| 2026-10-24 | J_EXP 2 × 5; J9 y J5 reordenados | Caben en el borde izquierdo y alejan el fototransistor del motor | agente (replanteo) |
| 2026-10-24 | Vías de 0,45/0,2 solo en la clase USB (regla en `.kicad_dru`); el resto 0,6/0,3 | Cruce del par en el receptáculo de 16 pines; dentro del estándar de JLCPCB (sin sobrecoste según `fabricante-jlcpcb.md`, confirmar en el presupuesto) | agente (replanteo) |
| 2026-10-24 | Logo en la cara inferior bajo la zona trasera izquierda de la batería | Zona sin piezas ni vías previstas; subordinado al diseño | agente (replanteo) |
| **Pendiente** | NTC en el pin TS del BQ24073 o carga sin sensor de temperatura | Crítico B7 de `revisiones/2026-10-24-B-esquematico.md` | **el autor del proyecto** |

## Cálculos
- **Par USB** (microstrip acoplado sobre L2, IPC-2141): h 0,2104, w 0,28, t 0,035, εr 4,4 → Z0 ≈ 57 Ω, Zdiff ≈ 87 Ω con s 0,15 (± 10 % de 90 Ω; a 12 Mbit/s el cuello de 0,2 mm en los pads de J1 no cuenta).
- **Elevador**: Vout = 1,212 · (1 + 390/100) = 5,94 V; ILIM = 1 030 000 / 270 k = 3,8 A; fSW ≈ 0,96 MHz con 150 kΩ; pico de bobina en el peor caso 2,82 A (`sim/`). Isat de la FHD4020S-1R0MT ≥ 3,4 A **por verificar**.
- **Buck-boost**: Vout = 0,5 · (1 + 510/91) = 3,30 V; Iq 11 µA.
- **Cargador**: ICHG = 890/1,8 k = 0,494 A; IIN = 1610/1,2 k = 1,34 A (EN2 = 1, EN1 = 0); arranque en USB500.
- **Motor**: ITRIP = VREF / (1,5 k · 1500 µA/A) = 2,245 / 2,25 = 1,0 A; Tj ≈ 50 + 0,6 · 42,8 = 76 °C.
- **LED del encoder**: (5,94 − 1,3) / 470 = 9,9 mA, 46 mW (≤ 50 % de 0,1 W).
- **I2C**: tr ≈ 0,85 · 4,7 k · 100 pF ≈ 0,4 µs: 400 kHz justo; medir (mejora B10).
- **Pistas** (IPC-2221, 1 oz exterior, ΔT 10 °C): 0,3 → 1,0 A; 0,5 → 1,45 A; 0,8 → 2,0 A; vía de 0,3 ≈ 0,7 A → ≥ 2 por cambio de capa de potencia, 5 para VSYS/BAT (2,9 A).

## Simulación
`sim/elevador_6v.cir` (ngspice, etapa de potencia idealizada, declarado): pico 2,82 A < 3,8 A, rizado 19 mV. Lo que no se simula y por qué: `sim/RESULTADOS.md`.

## Apilado e impedancias
JLC04161H-7628: L1 señal · L2 GND continuo (salvo la antena) · L3 señal con relleno de VSYS y espina de 3V3 · L4 señal con relleno de GND. Prepreg 7628 de 0,2104 mm (εr 4,4), núcleo ≈ 1,065 mm, 1 oz exterior. 90 Ω diferenciales ≈ 0,28/0,15 (estimación; la calculadora de JLCPCB manda si se pide impedancia controlada, que a 12 Mbit/s no hace falta).

## Herramientas disponibles al empezar (2026-10-24, replanteo)
kicad-cli 10.0.7, Python de KiCad, pcb-toolkit 0.1.0 (venv local), rsvg-convert, ngspice. **Faltan** kicad-happy (puertas B y C quedan «kicad-happy: no ejecutado») y Freerouting (no se usa en el replanteo).

## Clases de red y zonas calientes
`pcb-toolkit.toml` junto al PCB. Clases: **A** lazos (VSYS/BAT/V6 junto a los convertidores, BST_SW, BB_SW1/2, MOT_OUT*, SPK_*); **B** CAM_* (DVP) e I2S_* (incluidas I2S_SCK_MIC/I2S_WS_MIC); **C** USB_DP/USB_DN; **D** IPROPI, IPROPI_IO, MOT_VREF, VBAT_SNS, LIGHT, ENC_PT y las realimentaciones BB_FB, BST_FB, BST_COMP, BST_RC; **E** VBUS, VSYS, BAT, 3V3, V6; **F** el resto. Zonas calientes automáticas: L1 (con U3 y BB_SW*) y L2 (con U5, C13, R20 y BST_SW), 3 mm; declaradas: «puente H» (MOT_OUT1/2, margen 1,0: PWM de 20 kHz a 1 A, mucho menos agresivo que un convertidor a 1 MHz) y «clase D» (U7, margen 1,0: sus salidas van 6 mm hasta J8 y lo único crítico cerca es el I2S que entra en él). Grupos explícitos (sin automáticos: los prefijos BST_, BB_ y BQ_ formarían grupos que «cruzan» su propio convertidor). Las realimentaciones no van en ningún grupo porque viven dentro de su zona.

## Planta (replanteo del 2026-10-24)
Coordenadas del STL en `scripts/layout.py`. Bloques y cara (todo arriba salvo los TP):

| Bloque | Dónde | Por qué |
|--------|-------|---------|
| Módulo U4 | Delante, antena en el borde (keepout x −85…−61, y > −62 en las 4 capas); C10 y C9 pegados al pin 3V3 por la izquierda | Fijo por la antena |
| IR y luz (J7, Q3, R53–R56, C40) y RC de EN | Delante a la izquierda, J7 en la franja fuera de la batería | Cables a la cara del Furby |
| LED PWR/RUN/TX, RST/BOOT, JP5 | Delante a la derecha | Accesibles fuera de la batería |
| FPC J6 | Borde derecho, pin 1 abajo, flex hacia la pared (franja sin piezas x −46…−39) | Como estaba |
| LDO de cámara (U8, U9) y control (R33–R35, C27–C31) | Debajo de J6 (filas y −91…−100) y, PWDN/RESET, en la banda norte del pasillo sur junto a J6.6/8 | Salidas a los pads 4/10 de J6 a 8–12 mm |
| JP1–JP3, R18, JP4, R29, R30 | Arranque del pasillo sur (x −66…−57, y −83…−88) | En el camino de IO9/IO46/IO3 hacia U6 y de BOOT |
| Puente H U6 | Junto a los pads del motor de J9 (columna interior, abajo); control al oeste, VM y salidas al este | IPROPI/VREF lejos de las salidas |
| Elevador U5/L2 | Esquina trasera derecha: SW arriba contra L2, VIN y BOOT al este, VOUT/GND con C18 al sur, FSW/VCC/FB/COMP al oeste en dos columnas | Lazo de salida mínimo; a > 3,5 mm de cualquier bus |
| Cargador U2 (90°) | Centro trasero: IN al oeste (C2 junto al pin, C1, R4, R3), BAT al sur (C4, Q1, J2/J3), OUT al norte (C3, C17, R5), EN/PGOOD/CHG al este con sus pull-ups y D1/D2 | Entre el USB, los pads de batería y el plano de VSYS |
| USB J1, U1, R1, R2, F1 | Lóbulo; U1 2,3 mm detrás de los pads de J1 | Par corto |
| J8 (1 × 7), J5 (2 × 3), J_EXP (2 × 5) | Borde izquierdo, de delante hacia atrás, fuera de la batería | Cables de inclinación/lengua/altavoz, micro y expansión |
| Expansor U10 | Bajo la batería, pegado a la columna izquierda del módulo; I2C/INT al noreste; RC de J8 (2 columnas) entre U10 y J8; pull-ups y filtros de barriga/espalda/leva al sureste | Hub de señales lentas, cerca del I2C del módulo |
| Amplificador U7 (180°) | Bajo la batería junto a J8: salidas al oeste hacia J8.6/7, VDD al norte (C26), I2S al sur, R31/R32 hacia J5 | I2S corto, altavoz a 6 mm |
| Buck-boost U3/L1 | Bajo la batería, zona trasera izquierda; VIN/L1/VOUT al este, FB al oeste con R15/R16 pegados | A ≥ 3,5 mm del pasillo del USB |
| TP1–TP14 | Cara inferior, a ≤ 5 mm de su fuente, sobre vía de su red | Preferencia de el autor del proyecto |
| Logo | Cara inferior, x −101,5…−87,1, y −117,6…−104,0 (área sin vías ni pads) | Subordinado |

### Pasillos reservados (sin piezas)
- **Cámara**: de la fila inferior y la columna derecha del módulo a J6 (y −74…−81), 12 líneas en F.Cu en orden de pads (rutado «de río»: el pin de la derecha sube al pad más alto).
- **Sur**: y −83…−89,3 entre el módulo y el agujero del mecanismo, de la columna izquierda a J9, J6 y los LDO (HOME, ENC, MOT_IN*, IPROPI, I2C a J6, CAM_EN/PWDN, EN_6V, BQ_EN*).
- **Canal**: x −86,5…−82,5 a la izquierda de la columna izquierda del módulo (I2S, par USB, I2C/INT con vía a In2 bajo C10/C9).
- **Norte-sur**: x −77…−69 bajo la batería (par USB en F.Cu sin vías, MOT_IN*, VBAT_SNS, 3V3 por In2).
- Las señales de los pines 35–39 del módulo (IR_RX, UART0, LIGHT, VBAT_SNS) salen por debajo del módulo en In2/B.Cu, nunca cruzan el pasillo de la cámara en F.Cu.

### Pines
Módulo (sin tocar GPIO0/3/45/46 ni USB): 4 I2C_SDA, 5 I2C_SCL, 6 EXP_INT, 7 I2S_BCLK, 8 I2S_WS, 9 I2S_DOUT, 10 I2S_DIN, 11 HOME, 12 ENC_IO, 13/14 USB, 15 IPROPI_IO, 16 MOT_IN2_IO, 17 MOT_IN1_IO, 18–25 CAM_VSYNC, HREF, Y9, XCLK, Y8, Y7, PCLK, Y6, 26 IR_TX, 27 BOOT, 31–34 CAM_Y2, Y5, Y3, Y4, 35 IR_RX, 36/37 UART0, 38 LIGHT, 39 VBAT_SNS. GPIO: ver `scripts/design.py`. TCA9535: P00 TILT_A, P01 TILT_B, P02 TONGUE, P03 EXP_P07, P04 IR_PWR, P05 AMP_SD, P06 PGOOD, P07 CHG, P10 BQ_EN1, P11 BQ_EN2, P12 EN_6V, P13 TUMMY, P14 BACK, P15 CAM_PWDN, P16 CAM_EN, P17 LED_RUN_K. **El firmware debe seguir este mapa.**

### Par USB en J1 (resuelto desde las reglas y la colocación; geometría para el rutado)
Pads de 0,3 a 0,5 de paso en el orden B7 (D−), A6 (D+), A7 (D−), B6 (D+): los pares están entrelazados y una de las dos uniones tiene que cruzar por B.Cu. Plan: D+ se une en F.Cu (A6 y B6 bajan rectos y se funden); D− baja de B7 a una vía de 0,45/0,2 a ≈ 1,7 mm del pad, va por B.Cu bajo D+ hasta otra vía bajo A7 y sigue por B.Cu hasta el pin 3/4 de U1 (2,3 mm detrás); con vías de 0,6 no cabe (holgura 0,1 < 0,15). Vías de GND de retorno a ≤ 1 mm de cada vía de D− (a los lados, entre CC1/CC2 y VBUS) y en el pin 2 de U1. El par acoplado (0,28/0,15) empieza en U1 y sube por el pasillo norte-sur y el canal hasta los pines 13/14. D− tendrá 3 vías (aviso `cambios-capa` aceptado: USB FS).

## Desviaciones del layout de referencia
- **TPS61089**: C13 (BOOT) a 2,5 mm del pin y en el lado de L2 (no cabe pegado); RFSW a 3 mm por el oeste. El lazo VOUT–C18–GND es el de la figura del datasheet. Revisar en el PNG al rutar.
- **DRV8231A**: C22 (100 nF de VM) a 1,8 mm del pin (aviso de `comprobar-flujo` no, pero por encima de 1 mm); C20/C21 de 22 µF a 2–3 mm.
- **BQ24073**: C2 (1 µF de IN) a 1,6 mm; ISET (R4) a 2,4 mm.

## Intentos de colocación y rutado
| Fecha | Colocación n.º | Freerouting n.º | Resultado | Decisión |
|-------|----------------|-----------------|-----------|----------|
| 2026-10-24 | 1 (encargo 1) | — | El bus de la cámara cruzaba el elevador | Recolocar |
| 2026-10-24 | 2 (encargo 1, commits 5e1d428…9d42d8b) | 1 (1.9.0, −mp 20) + remate por rejilla | 15 pads sin unir, `revisar-rutado` FAIL (318 errores), USB_DN sin resolver | Replanteo independiente (este encargo); el rutado se descarta |
| 2026-10-24 | 3 (replanteo, `scripts/layout.py`) | — | Puerta C: DRC 0/0 con paridad, `comprobar-flujo` PASS | Revisión independiente de la colocación (encargo 3) |

## Revisiones (puertas)
| Fecha | Puerta | Herramientas y resultado | Revisor | Estado |
|-------|--------|--------------------------|---------|--------|
| 2026-10-24 | A | Rúbrica L y tabla de raíles añadidas (`revisiones/2026-10-24-A-arquitectura.md`) | agente T0 (replanteo) | Pasa |
| 2026-10-24 | B | ERC 0/0, simulación del elevador, pinout verificado; 1 crítico escalado (NTC) (`revisiones/2026-10-24-B-esquematico.md`) | agente T0 (replanteo) | Pasa con B7 escalado |
| 2026-10-24 | C | DRC 0/0 paridad 0, `comprobar-flujo` PASS (4 avisos), 12 PNG (`revisiones/2026-10-24-C-colocacion.md`) | agente T0 (replanteo, propia) | Pasa; falta la independiente |

## Avisos aceptados del DRC, del ERC y de pcb-toolkit
| Aviso | Motivo |
|-------|--------|
| `comprobar-flujo` desacoplo-lejos: C10 1,9 mm, C32 1,08, C28/C29 1,02 | Dentro del máximo de 2 mm; el pad del módulo y el patio de J9 no dejan acercarlos más |
| `comprobar-flujo` cruces-en-bus (DVP 15, I2S 13) | Cruces de líneas rectas fila → columna; el pasillo de la cámara se ruta de río sin cruces (orden de pines = orden de pads) |
| J7: borde del pad trasero a 0,05 mm del borde nominal de la batería | Centro del pad 0,8 mm fuera; cable soldado por delante |

## Pendiente para la siguiente versión / otros encargos
- **el autor del proyecto**: NTC en TS (B7). Confirmar C23179 (470 Ω) e Isat de la FHD4020S-1R0MT antes del pedido.
- Rutado (encargo 4): reescribir `scripts/rutas_fijas.py` con el par USB de la sección «Par USB» y los lazos de los convertidores; `scripts/rutado.dsn`/`.ses`, `router/`, `ensanchar_potencia.py` y `vias_extra.py` son del intento anterior y no se reutilizan (el rutador por rejilla queda prohibido como autorrutador).
- `TEST-PLAN.md` desfasado: TP renumerados en la cara inferior, pines nuevos, J9/J5 reordenados, LED del encoder desde V6, restricción de USB500 (B8).
- Serigrafía: rótulos sin sitio (J2 «+», parte de J_EXP/J5/J9) → recolocar con el cobre definitivo.
- v1.1: TVS en VBUS, agujeros para atar los cables de la batería, PTC de 2 A, pull-ups de I2C según la medida.

## Historial (encargo 1, resumen)
Commits 7ccbb60…9d42d8b de esta rama: contorno con holgura 1,0 y USB-C de 16 pines (`../PCB-suelo`), esquema jerárquico, dos colocaciones, par USB a mano, BOM/CPL de JLCPCB con giros comparados (`scripts/jlc_post.py`), TEST-PLAN, modelos 3D, logo, pre-rutado y una ejecución de Freerouting 1.9.0 (release oficial, ejecutada sin red desde el scratchpad) con remate por rejilla que no convergió (15 pads sin unir, `render/rutado-pendiente.png` y `render/remate-*.png`). Lecciones pasadas al Cerebro (`layout-pcb.md`, `kicad-automatizacion.md`): rutador propio prohibido, autorrutado acotado, TP junto a su fuente, «DRC 0» no es calidad, Freerouting ignora el margen a borde (franja en el DSN), el Python de KiCad en subprocesos.
