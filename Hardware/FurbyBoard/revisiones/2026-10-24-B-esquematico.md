# Revisión B esquemático — FurbyBoard v1.0

- Fecha: 2026-10-24 · Commit: fe588cc (partida) → correcciones en esta rama · Revisor: electronics-engineer (replanteo independiente, modelo T0)
- Tipo de placa: L · Capas: 4 · Fabricante: JLCPCB
- Material revisado: `scripts/design.py` (fuente del esquema), las 8 hojas de `hojas/`, símbolos de KiCad 10 y propios (`lib/`), `ARQUITECTURA.md`, datasheets consultados: BQ2407x (ZHCSIF0N/SLUS810, pines TD, TMR, CE), TPS61089 (SLVSD38C, FSW e ILIM), tabla de strapping del ESP32-S3

## Resultado
**PASA con un crítico escalado** — 1 crítico abierto que exige una decisión de el autor del proyecto (B7), 0 importantes abiertos, 4 mejoras anotadas en `NOTAS.md`.

## Herramientas
| Herramienta | Comando | Resultado |
|-------------|---------|-----------|
| ERC | `kicad-cli sch erc --severity-all --exit-code-violations FurbyBoard.kicad_sch` | **0 infracciones** (tras regenerar con `gen_sch.py`) |
| Simulación | `ngspice -b sim/elevador_6v.cir` | Pico de bobina 2,82 A < ILIM 3,8 A; rizado 19 mV (`sim/RESULTADOS.md`) |
| Pinout frente al símbolo | `gen_sch.pin_names()` contra las redes de `design.py` (todos los CI) | Coincide pin a pin; ver «Verificado» |
| kicad-happy (esquema) | — | **no ejecutado** (no instalado) |

## Hallazgos
| ID | Sev. | Área | Hallazgo | Evidencia | Verificado / supuesto | Corrección | Estado |
|----|------|------|----------|-----------|-----------------------|------------|--------|
| B1 | Importante | Nombres de red | `BB_L1`/`BB_L2` (nodos SW del buck-boost) y `MIC_SCK`/`MIC_WS` (bus I2S tras las resistencias serie) no seguían la convención, así que `comprobar-flujo` no los reconocía como SW ni como bus | `diseno-de-circuito.md` §14 | Verificado | `BB_SW1`, `BB_SW2`, `I2S_SCK_MIC`, `I2S_WS_MIC` | Corregido |
| B2 | Importante | Comprobaciones | No existía `pcb-toolkit.toml`: sin redes críticas, sin anchos mínimos ni zonas calientes declaradas | `layout-pcb.md` §2.7 | Verificado | `pcb-toolkit.toml` con clases B/C/D, anchos de la tabla de raíles, grupos explícitos (USB, DVP, I2S, sensado) y zonas del puente H y de la clase D | Corregido |
| B3 | Importante | Reglas | `.kicad_dru` solo tenía la excepción de borde del USB-C: sin anchos mínimos por red ni control del tamaño de vía | `kicad-automatizacion.md` §5 | Verificado | `gen_pro.py` genera una regla de ancho por red de potencia (`params.ANCHOS_MINIMOS`), cuellos de ≤ 1 mm dentro de los patios de los QFN y de J1, y vías de 0,6/0,3 en toda la placa salvo la clase USB (0,45/0,2 para el cruce del par en J1) | Corregido |
| B4 | Importante | Pines | La asignación de GPIO de la columna izquierda del módulo (I2S, HOME, EXP_INT) y la de los puertos del TCA9535 no seguían la geometría de la planta nueva | Ratsnest de `comprobar-flujo` | Verificado | Pines 6–11 del módulo: EXP_INT, BCLK, WS, DOUT, DIN, HOME (sin tocar strapping, USB ni ADC); TCA9535: P0x hacia J8/J11/J7/amplificador, P1x hacia cargador, elevador, J9, cámara y LED. **El firmware debe seguir el mapa de `NOTAS.md`** | Corregido |
| B5 | Importante | Encoder | El AO3400A (Q2) que encendía el LED del encoder con EN_6V no tenía sitio junto a J9 ni al elevador | Colocación | Verificado | El LED se alimenta de V6 por R51 = 470 Ω (≈ 9,9 mA, 46 mW en 0603): luce solo con el elevador encendido, misma función, una pieza menos. Código C23179 **por confirmar** en la API de JLCPCB antes del pedido | Corregido |
| B6 | Importante | Pads de cable | J_EXP 1 × 10 no cabe en el borde izquierdo junto a J8 y el micro; J9 tenía el fototransistor del encoder pegado a las salidas del motor | Linter de colocación y `comprobar-flujo` (sensado cruzaba el puente H) | Verificado | J_EXP pasa a 2 × 5 (mismas 10 señales); J9 reordenado (encoder y leva en la columna exterior, barriga, espalda y motor en la interior); J5 con DIN en el pad 1. Serigrafía actualizada | Corregido |
| B7 | **Crítico** | Batería | El BQ24073 lleva TS con 10 kΩ fijos: carga sin medir la temperatura de la celda. La celda trae PCM pero no NTC | `revision-de-diseno.md` 4.1 (C); `ARQUITECTURA.md` §7 | Verificado | Opciones: (a) NTC de 10 kΩ 0603 en la placa junto a los pads de la batería, que mide la PCB bajo la celda, no la celda (código LCSC por verificar, +0,05 USD); (b) aceptar la carga sin sensor con la celda sobre la placa en interior (0–45 °C) y el PCM de la celda. Decisión para el autor del proyecto | **Abierto, escalado** |
| B8 | Importante | Protección | PTC de 1,5 A frente a 1,34 A en modo ILIM: derating 1,12 < 1,25 | `diseno-de-circuito.md` 4.4 | Verificado | El firmware arranca y se queda en USB500 (0,5 A); el modo ILIM solo con una fuente conocida y placa fría. Con 0,5 A el derating es 3. Se anota en `NOTAS.md` y en el TEST-PLAN (pendiente de actualizar). Alternativa v1.1: PTC de 2 A | Cerrado con restricción |
| B9 | Importante | Simulación | No había `sim/` | `revision-de-diseno.md` 4.4 | Verificado | Simulación del elevador en el peor caso (`sim/`); lo que no se simula y por qué, en `sim/RESULTADOS.md`. Isat de la FHD4020S-1R0MT ≥ 3,4 A por verificar en su hoja de datos | Corregido (Isat por verificar) |
| B10 | Mejora | I2C | 4,7 kΩ a 400 kHz: con Cb ≈ 100 pF (pistas, flex de 150 mm, entradas) tr ≈ 0,85 · R · Cb ≈ 0,4 µs > 0,3 µs | Cálculo | Estimado | Medir tr en el bring-up; si no cumple, 100 kHz por firmware o 2,2 kΩ | Abierto |
| B11 | Mejora | Cámara | C30 (100 nF de DOVDD) no cabe junto al pin 11 del FPC: va con el LDO. El módulo de cámara trae sus propios condensadores | Colocación | Verificado | Nada (en `pcb-toolkit.toml`, `desacoplo_ignorar`) | Aceptado |
| B12 | Mejora | Protección | Sin TVS de potencia en VBUS: la protección es la OVP del BQ24073 (6,6 V) y el clamp de ESD del USBLC6 | `diseno-de-circuito.md` 5.2 | Verificado | TVS de 5 V (SMAJ5.0A o similar) junto a J1 en v1.1 | Abierto |
| B13 | Mejora | Batería | Sin agujeros de Ø1,2 para atar los cables (propuesta de la arquitectura) | `ARQUITECTURA.md` §7.1 | Verificado | v1.1 si hay sitio | Abierto |

## Verificado (sin hallazgo)
- **Pinout de cada CI** contra el símbolo de KiCad 10 (U2 BQ24073: /CE a GND, TD a GND = terminación activa, TMR al aire = temporizadores por defecto, confirmado en el datasheet; U5 TPS61089: RFSW entre FSW y SW, RILIM a GND, confirmado en SLVSD38C; U7 MAX98357A: GAIN_SLOT a VDD = 6 dB; U3 TPS63802: EN a VIN, MODE a GND; U6 DRV8231A; U10 TCA9535 dirección 0x20; U8/U9 ME6211 (1 VIN, 2 GND, 3 CE, 5 VOUT); U11 74LVC1G17; U1 USBLC6-2SC6; Q1 SI7615ADN S/G/D).
- **Strapping del ESP32-S3:** GPIO0 10 kΩ + botón; GPIO45 100 kΩ a GND (puerta del AO3400A del IR); GPIO46 100 kΩ a GND y pull-down interno; GPIO3 con RIPROPI a GND. EN con 10 kΩ y 1 µF y botón.
- **USB-C:** 5,1 kΩ en cada CC; D+/D− unidos por parejas (A6/B6, A7/B7); ESD junto al conector; PTC antes del cargador.
- **Niveles:** nada de 5 V en pines de 3,3 V; PGOOD/CHG a 3V3 por 100 kΩ y el TCA9535 tolera 5,5 V.
- **Estados al arrancar:** EN1/EN2 del cargador (USB500), EN_6V, AMP_SD, CAM_EN, CAM_PWDN, MOT_IN1/2, IR_PWR, LED_RUN definidos por resistencias o pull-downs internos.
- **Desacoplo y bulk:** módulo 22 µF + 100 nF; BQ IN 1 µF/OUT 10 µF/BAT 10 µF; TPS63802 10 µF/2 × 22 µF; TPS61089 2 × 22 µF (uno al VIN más el relleno de VSYS) y 4 × 22 µF de salida (dos en el elevador y dos en el VM del puente H); MAX98357A 2 × 22 µF + 100 nF; LDO 1 µF.
- **Derating:** 22 µF 25 V en 4,4–6 V; 10 µF 10 V en 5 V (≈ 60 % tras DC bias, suficiente); P-MOSFET −20 V con 4,2 V; R54 0805 con 100 mA en pulsos.
- **Polaridad inversa con USB:** análisis de `ARQUITECTURA.md` §7.1 (el BQ se queda en detección de cortocircuito, 4–11 mA); prueba obligatoria en el bring-up.
- **PCM de la celda frente al pico de 2,9 A:** mitigado con ITRIP 1,0 A ajustable, limitador de audio y rampa del motor; medir el corte del PCM (duda 6 de la arquitectura).

## Checklist de la puerta
4.1 alimentación: máximos OK; protección de entrada OK (B12 mejora); batería: **B7**; raíles OK (A2); desacoplo OK; derating OK (B8); PCM OK con mitigación. 4.2 MCU e interfaces: strapping OK; 5 V OK; USB-C OK; pull-ups OK; I2C OK (B10 mejora); consola de rescate OK (J_EXP y botones); conectores: pin 1 cuadrado en todos los pads de cable, FPC con pin 1 marcado, J1 con *keying* propio; cargas: ITRIP y bulk OK. 4.3 componentes: pinout OK; huellas comprobadas por el encargo anterior contra EasyEDA (sin repetir aquí; C23179 y el Isat por verificar); LCSC con stock y precio del 2026-10-24 en `ARQUITECTURA.md`. 4.4 simulación: B9. 4.5 casos especiales: RF por módulo con keepout; sin alta tensión ni analógico de precisión.

## Revisión final como revisor senior
- Piezas giradas en el CPL (Game Boy): no aplica todavía (puerta E2); el encargo anterior dejó los giros en la tabla de pcb-toolkit como `comparado-sin-montar`.
- Bus rápido cruzando un convertidor: lo decide la colocación (puerta C).
