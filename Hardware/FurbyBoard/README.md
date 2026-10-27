# FurbyBoard v1.0: hoja de datos

> **Explicación interactiva de cada bloque, con señales y diagnóstico:** [makerisland.es/projects/furby-gpt/placa](https://makerisland.es/projects/furby-gpt/placa)

Placa principal del Furby-GPT: va atornillada en el suelo de la base de un Furby de 1998 y sustituye a su electrónica. Lleva un ESP32-S3 con WiFi, cámara, micro y altavoz, mueve el motor original del mecanismo, lee los sensores del muñeco y se alimenta de una LiPo de una celda que se carga por USB-C.

Este documento es la referencia para quien coja la placa sin contexto: qué hace cada bloque, qué hay en cada conector, qué pin usa el firmware, dónde se mide y qué límites tiene. El porqué de cada decisión está en [`NOTAS.md`](NOTAS.md); el plan de pruebas, en [`TEST-PLAN.md`](TEST-PLAN.md); las simulaciones, en [`sim/RESULTADOS.md`](sim/RESULTADOS.md). Si este documento y el esquema no coinciden, manda el esquema (`scripts/design.py`).

## Estado (2026-10-27)

| | |
|---|---|
| Versión | **v1.0** (serigrafía «v1.0 · 2026-10») |
| Rama | `feature/electronica-v1` |
| Esquema | 8 hojas, 152 referencias (126 piezas montadas por el fabricante, 52 códigos LCSC). ERC 0 errores y 0 avisos |
| PCB | 6 capas, **rutada al completo** (0 conexiones sin unir). DRC con paridad esquema-PCB: 0 errores, 0 avisos. `pcb-toolkit revisar-rutado`: PASS, 0 errores |
| Puertas pasadas | A (arquitectura), B (esquema), C (colocación, con revisión independiente), D (rutado, propia), S (serigrafía), **E1** (diseño listo para fabricar, con revisión independiente) y **E2** (ficheros de fabricación). El 2026-10-27 se cerraron las mejoras **M7** (series de 33 Ω en los relojes de la cámara) y **M1** (paralelos In2/In3) con la E1 y la E2 repetidas (`revisiones/2026-10-27-M7-M1.md`); **pendiente su revisión independiente**. Informes en [`revisiones/`](revisiones/) y tabla «Revisiones» de `NOTAS.md` |
| Ficheros de fabricación | Gerber, taladros, BOM y CPL de JLCPCB en [`fabricacion/`](fabricacion/README.md), con la puerta E2 pasada (2026-10-25) y regenerados el 2026-10-27 tras M7 y M1. Antes de pedir: lista «Confirmar antes de pedir» de [`fabricacion/README.md`](fabricacion/README.md) |
| Fabricada | No. Nadie ha medido todavía una placa real: todo lo que sigue es diseño y simulación |
| Firmware | No existe. Las reglas que debe cumplir están en «Reglas para el firmware» |

## Resumen

| Característica | Valor |
|----------------|-------|
| Tamaño | ≈ 68,8 × 74,6 mm, forma del suelo de la base; 1,6 mm de grosor |
| Fijación | 4 tornillos M2 (taladros de 2,3 mm); agujero central de Ø11,3 mm para el eje del mecanismo |
| Alimentación | USB-C de 5 V (solo carga, Rd de 5,1 kΩ) y LiPo 1S de 1400 mAh soldada a pads, con protección contra la inversión |
| Carga | BQ24073 con power path: 0,49 A de carga; entrada de 0,475 A (USB500, por defecto) o 1,34 A (ILIM) |
| Raíles | VSYS (4,4 V con USB; VBAT − 50 mV sin USB), 3V3 (2 A), V6 (5,94 V para el motor), 2V8 y 1V2 de la cámara |
| Procesador | ESP32-S3-WROOM-1-N16R8 (16 MB de flash, 8 MB de PSRAM octal), WiFi y BLE con antena de PCB |
| Motor | Puente H DRV8231A a 6 V, PWM de 20 kHz, corriente limitada a 1,0 A y medida (2,25 V/A) |
| Audio | Amplificador clase D MAX98357A (altavoz de 4 Ω, 0,9–1,9 W según la batería) y micro I2S ICS-43434 en una plaquita aparte |
| Cámara | DVP de 8 bits por FPC de 24 pines (OV2640; OV3660 u OV5640 cambiando U9), con 33 Ω en serie en XCLK (R59, junto al módulo) y en PCLK (R60, junto al FPC) |
| Sensores | Inclinación, lengua, barriga y espalda por un expansor TCA9535; leva y encoder del mecanismo, luz e infrarrojos directos al módulo |
| Depuración | 5 LED, 14 puntos de test, botones RST y BOOT, consola UART en J_EXP y 5 puentes de soldadura |
| Consumo | Dormido ≈ 80 µA; escuchando 85–120 mA; pico ≈ 2,9 A en la batería (estimado) |
| Temperatura | 0–50 °C de ambiente dentro del Furby |

## Diagrama de bloques

```
USB-C (J1) ─ ESD USBLC6 (U1) ─ PTC 1,5 A (F1) ─ VBUS ─┐
                                                       │
                          BQ24073 (U2), power path ◄───┘
                          │  BAT ◄──► Q1 SI7615ADN ◄──► J2 (BAT+) / J3 (BAT−)  LiPo 1S
                          ▼
                        VSYS 4,4 V / VBAT
        ┌──────────────┬──────┴──────────┬───────────────────┬────────────┐
        ▼              ▼                 ▼                   ▼            ▼
  TPS63802 (U3)   TPS61089 (U5)    MAX98357A (U7)     LED IR (J7)    J_EXP.3
  buck-boost      elevador          clase D → J8        por R54 y Q3
  3V3, 2 A        V6 5,94 V         (altavoz)
        │              │
        │              └─► DRV8231A (U6) → motor (J9 M1/M2)
        ├─► ESP32-S3-WROOM-1 (U4) ── I2C ── TCA9535 (U10) ── sensores (J8, J9), LED RUN, LED del encoder (EN_6V por R51), control de la potencia
        │                         ├─ I2S ── U7 y micro (J5)
        │                         ├─ DVP ── cámara (J6)
        │                         └─ USB ── J1
        ├─► ME6211 2V8 (U8) → ME6211 1V2 (U9) → cámara (J6), encendidas por el expansor
        └─► pull-ups, LED, Schmitt del encoder (U11), J_EXP.2
```

| Bloque | Piezas | Qué hace |
|--------|--------|----------|
| Entrada USB | J1, U1, F1, R1, R2 | USB-C de 16 pines de montaje medio. Rd de 5,1 kΩ en CC1 y CC2: cualquier fuente da 5 V. **La placa no lee las líneas CC**, así que no sabe cuánta corriente ofrece el cargador. D+ y D− van al USB nativo del ESP32-S3 |
| Cargador y power path | U2, R4–R7, C1–C4, RT1 | BQ24073: carga a 0,494 A (R4) con ventana de temperatura de 0–50 °C medida por la NTC RT1 bajo la batería. Arranca en USB500 (EN1 = 1, EN2 = 0); el firmware puede pasar a ILIM (1,34 A, R5). VSYS sale regulado a 4,4 V con USB y sigue a la batería sin él |
| Batería | J2, J3, Q1, R12, R13, R14, C5 | P-MOSFET SI7615ADN con la puerta a GND: con la batería al revés no llega tensión negativa a nada (probado también con USB en la simulación). Divisor 470k/470k a VBAT_SNS (ADC) |
| 3V3 | U3, L1, R15, R16, C6–C8 | Buck-boost TPS63802: 3,30 V desde VSYS (2,3–4,4 V), hasta 2 A; alimenta el módulo, el expansor, la cámara y la lógica |
| 6 V y motor | U5, L2, R20–R25, C12–C22, U6, R26–R30, JP1–JP3 | Elevador TPS61089 a 5,94 V (ILIM 3,8 A), solo encendido cuando hace falta (EN_6V). Puente H DRV8231A con ITRIP de 1,0 A (VREF por R26/R27) y salida de corriente IPROPI (2,25 V/A, R28) al ADC |
| Audio | U7, C24–C26, C41, R31, R32, J5 | MAX98357A desde VSYS, ganancia de 6 dB, controlado por AMP_SD. El micro ICS-43434 va en una plaquita con cable (≤ 15 cm) a J5; comparte BCLK y WS con el amplificador (bus I2S full duplex) |
| Cámara | J6, U8, U9, R33–R35, R59, R60, C27–C31 | FPC de 24 pines con el pinout habitual de los módulos OV2640/OV3660/OV5640 para ESP32 (**verificar con el módulo concreto**). AVDD de 2,8 V y DVDD de 1,2 V (1,5 V cambiando U9 por ME6211C15) con CAM_EN; DOVDD a 3V3 |
| Expansor y sensores | U10, R36–R52, C32–C39, U11, JP4 | TCA9535 en 0x20 sobre el I2C del módulo (el mismo bus que el SCCB de la cámara). Entradas con pull-up, 1 kΩ en serie y 100 nF; Schmitt 74LVC1G17 para el encoder |
| IR y luz | Q3, R53–R56, C40, J7 | Emisor IR con AO3400A (≈ 100 mA en pulsos por R54 de 22 Ω desde VSYS), receptor alimentado por el expansor (P17), LDR con 470 kΩ a GND |
| LED y depuración | D1–D5, R10, R11, R19, R57, R58, SW1, SW2, JP5, TP1–TP14, J11 | Ver «LED», «Botones y puentes» y «Puntos de test» |

## Capas y rutado

**6 capas, 1,6 mm, apilado JLC06161H-7628 de JLCPCB** (cobre de 1 oz fuera y 0,5 oz dentro; espesores a confirmar en el presupuesto del pedido):

| Capa | Uso | Dieléctrico debajo |
|------|-----|--------------------|
| L1 F.Cu | Todas las piezas, par USB (0,28/0,15 mm, ≈ 87 Ω diferencial) y bus de la cámara sobre GND; relleno de GND | prepreg 0,21 mm |
| L2 In1 | **GND continuo** (salvo bajo la antena) | núcleo 0,40 mm |
| L3 In2 | Señales (I2S, sensado, señales lentas bajo el módulo) con relleno de VSYS | prepreg 0,21 mm |
| L4 In3 | Señales lentas: autopistas este-oeste y norte-sur (expansor, J9, UART, IR, I2C a J_EXP) | núcleo 0,40 mm |
| L5 In4 | **GND continuo** (referencia de In3 y de B.Cu) | prepreg 0,21 mm |
| L6 B.Cu | Señales, TP, pads de cable y relleno de GND; logos y rótulos | — |

Vías pasantes de 0,6/0,3 mm (0,45/0,2 solo en el par USB); sin ciegas ni enterradas. Las vías térmicas de los pads expuestos (U2, U4, U6, U7) van rellenas y tapadas (POFV, de serie en 6 capas en JLCPCB). Toda la placa está cosida a GND entre In1, In4 y las caras exteriores (paso de ≈ 4 mm en el borde).

**Por qué 6 y no 4:** con 4 capas, el rutado crítico (lazos de los convertidores, par USB, bus de la cámara, I2S) y la colocación aprobada dejaban encerrado al expansor: 57 conexiones no tenían camino. Pasar a 6 capas (In3 de señal e In4 de GND) conservó todo lo rutado y abrió los pasillos; cuesta del orden de 15–30 USD más por pedido de 5 placas (decisión del autor del proyecto, 2026-10-24).

**Cómo está rutada:** a mano, por bloques de señales, en [`scripts/rutas_fijas.py`](scripts/rutas_fijas.py): cada pista, vía y polígono está escrito con su red, su capa y su ancho, y `gen_pcb.py` lo resuelve contra los pads reales. **No hay autorrutador** (Freerouting se probó con la colocación de 4 capas y se descartó). Lo primero fueron los lazos de potencia según el layout de referencia de cada chip, el par USB, la cámara y el I2S; después, las señales lentas por bloques (A1…U2), los arreglos de la simulación (bloque F), el cosido de GND (bloque E) y la serigrafía (bloque S). Anchos mínimos por red (tabla de raíles de `NOTAS.md`) comprobados por el DRC y por `revisar-rutado`.

## Serigrafía

- **Cara superior:** qué es cada LED, botón y puente, y «FURBYBOARD V1.0».
- **Cara inferior:** la función de cada pad de cable y los GPIO de J_EXP, el nombre de cada TP, «FurbyBoard», versión y fecha, el recuadro PLACA para numerarla y dos logos: el Furby en pixel art (esquina trasera, junto a J_EXP) y el de **@GuilleMaker** (11,0 × 10,7 mm, sobre el nombre de la placa, junto al agujero del mecanismo).
- Los rótulos y el logo de GuilleMaker se colocan por script **después del rutado**, sin pisar vías (≥ 0,15 mm), pads ni otros rótulos; el logo va el último porque es decoración. Letra de 1,0 mm (0,8 donde no cabe, ver «Limitaciones conocidas») y trazo de 0,15 mm, los mínimos de JLCPCB.
- Logo de GuilleMaker: [`scripts/logo_guillemaker.py`](scripts/logo_guillemaker.py) lo vectoriza desde [`serigrafia/logo-guillemaker.png`](serigrafia/logo-guillemaker.png); el texto mide 1,48 mm de alto con trazo de 0,18 mm. Vista de la cara inferior: [`render/serigrafia-logo-guillemaker.png`](render/serigrafia-logo-guillemaker.png).

## Conectores y pads

Las vistas «desde abajo» son como se ve la placa por la cara inferior, donde se sueldan los cables. Los pads de cable son pasantes de 2,54 mm; el pad 1 es el cuadrado.

### J1: USB-C (16 pines, HRO TYPE-C-31-M-13C)

| Pin | Red | Notas |
|-----|-----|-------|
| A4, A9, B4, B9 | VBUS_IN | 5 V; pasa por U1 (ESD) y F1 (PTC de 1,5 A) a VBUS |
| A5 / B5 | CC1 / CC2 | Rd de 5,1 kΩ a GND (R1, R2): sumidero por defecto |
| A6, B6 / A7, B7 | USB_DP / USB_DN | USB nativo del ESP32-S3 (GPIO20/19, USB Serial/JTAG); protegidos por U1 |
| A1, A12, B1, B12, carcasa | GND | |
| A8, B8 | — | SBU sin conectar |

### J2 y J3: batería

| Pad | Forma | Red | Rótulos |
|-----|-------|-----|---------|
| J2 | Cuadrado de 3 × 3 mm, taladro de 1,2 | BAT_PAD (+), antes de Q1 | «+» arriba, «BAT+» abajo |
| J3 | Redondo de Ø2,6 mm, taladro de 1,0 | GND (−) | «-» arriba, «BAT-» abajo |

Celda LiPo 1S de 1400 mAh **con PCM** y resistencia interna (con el PCM) **≤ 100 mΩ** («Reglas para el firmware»). Antes de soldarla se prueba la protección contra la inversión (`TEST-PLAN.md` §8.1).

### J5: micro I2S (2 × 3, en el borde izquierdo)

| Pad | Rótulo | Red | Pin del micro |
|-----|--------|-----|---------------|
| 1 | SD | I2S_DIN (GPIO17) | SD (datos) |
| 2 | G | GND | GND |
| 3 | SCK | I2S_SCK_MIC (BCLK por R31 de 33 Ω) | SCK |
| 4 | WS | I2S_WS_MIC (WS por R32 de 33 Ω) | WS |
| 5 | 3V3 | 3V3 | VDD |
| 6 | G | GND | GND (y L/R, según el canal elegido en la plaquita) |

La selección L/R del ICS-43434 se fija en la plaquita del micro. Cable de ≤ 15 cm.

### J6: cámara (FPC de 24 pines, paso 0,5 mm, AFC01-S24FCA-00)

En el borde derecho, pin 1 abajo, con el flex saliendo hacia la pared de la base.

| Pin | Red | Pin | Red |
|-----|-----|-----|-----|
| 1 | — | 13 | CAM_XCLK (GPIO13 por R59 de 33 Ω) |
| 2 | GND | 14 | CAM_Y8 (GPIO14) |
| 3 | I2C_SDA (SIOD) | 15 | GND |
| 4 | CAM_2V8 (AVDD) | 16 | CAM_Y7 (GPIO21) |
| 5 | I2C_SCL (SIOC) | 17 | CAM_PCLK_CAM (GPIO47 por R60 de 33 Ω) |
| 6 | CAM_RST (RC de R35/C31) | 18 | CAM_Y6 (GPIO48) |
| 7 | CAM_VSYNC (GPIO10) | 19 | CAM_Y2 (GPIO38) |
| 8 | CAM_PWDN (P15 del expansor) | 20 | CAM_Y5 (GPIO39) |
| 9 | CAM_HREF (GPIO11) | 21 | CAM_Y3 (GPIO40) |
| 10 | CAM_DVDD (1,2 V) | 22 | CAM_Y4 (GPIO41) |
| 11 | 3V3 (DOVDD) | 23, 24 | — |
| 12 | CAM_Y9 (GPIO12) | Patas | GND |

Pinout de facto de los módulos para ESP32 (OV2640/OV3660/OV5640): **compruébese con el módulo comprado antes de enchufarlo**. RESETB no da un flanco limpio al encender: el firmware resetea la cámara por SCCB.

### J7: IR y luz (2 × 4, delante a la izquierda)

| Pad | Rótulo | Red | Qué se conecta |
|-----|--------|-----|----------------|
| 1 | IR+ | IR_LED_A (VSYS por R54 de 22 Ω) | Ánodo del LED IR emisor |
| 2 | IR- | IR_LED_K (drenador de Q3, GPIO45) | Cátodo del LED IR emisor |
| 3 | G | GND | GND del receptor IR |
| 4 | RX | IR_RX_PAD (GPIO42 por R56 de 1 kΩ) | Salida del receptor IR |
| 5 | 3V3 | 3V3 | Un extremo de la LDR |
| 6 | LDR | LIGHT (GPIO2, 470 kΩ a GND) | Otro extremo de la LDR |
| 7 | G | GND | |
| 8 | RXV | IR_PWR (P17 del expansor) | Alimentación del receptor IR (se apaga para dormir) |

Leyenda en la cara inferior a la derecha de los pads, fila por fila. J7.3 y J7.8 se permutaron en el rutado (bloque U2): el receptor IR usa 8 (alimentación), 3 (GND) y 4 (salida).

### J8: inclinación, lengua y altavoz (1 × 7, borde izquierdo)

| Pad | Rótulo | Red | Qué se conecta |
|-----|--------|-----|----------------|
| 1 | TLA | TILT_A_PAD (P00, 220 kΩ de pull-up) | Contacto A del sensor de inclinación |
| 2 | TLB | TILT_B_PAD (P01, 220 kΩ) | Contacto B del sensor de inclinación |
| 3 | G | GND | Común del sensor de inclinación |
| 4 | LNG | TONGUE_PAD (P02, 47 kΩ) | Interruptor de la lengua |
| 5 | G | GND | Otro lado del interruptor de la lengua |
| 6 | SP+ | SPK_P | Altavoz + (4 Ω) |
| 7 | SP- | SPK_N | Altavoz − |

Las salidas del altavoz son las del clase D en puente (BTL): ninguna de las dos va a GND.

### J9: mecanismo, barriga y espalda (2 × 6, borde derecho)

| Pad | Rótulo | Red | Qué se conecta |
|-----|--------|-----|----------------|
| 1 | ENF | ENC_PT (10 kΩ a 3V3, Schmitt U11 → GPIO8) | Colector del fototransistor del encoder |
| 2 | G | GND | Emisor del fototransistor |
| 3 | EN+ | ENC_LED_A (EN_6V, P12 del TCA9535, por R51 de 220 Ω: 5,4–10 mA, ≈ 8 mA típico) | Ánodo del LED IR del encoder. Luce solo con EN_6V = 1 (elevador encendido); apagado no gasta nada. No cuelga de V6 porque el elevador apagado deja V6 ≈ VSYS − 0,4 V |
| 4 | G | GND | Cátodo del LED del encoder |
| 5 | LEVA | HOME_PAD (GPIO18, 100 kΩ de pull-up) | Interruptor de la leva (posición de reposo) |
| 6 | G | GND | Otro lado de la leva |
| 7 | BAR | TUMMY_PAD (P13, 47 kΩ) | Interruptor de la barriga |
| 8 | G | GND | |
| 9 | ESP | BACK_PAD (P14, 47 kΩ) | Interruptor de la espalda |
| 10 | G | GND | |
| 11 | M2 | MOT_OUT2 | Motor |
| 12 | M1 | MOT_OUT1 | Motor |

Columna exterior (borde de la placa): pads 1–6; interior: 7–12. **La leyenda de J9 no cabe junto a sus pads** (vías, TP y el agujero del mecanismo): está unos 22 mm por encima, con el título «J9», en la misma disposición que los pads vistos desde abajo y con el rótulo del pad 1 («ENF») recuadrado. El motor no tiene polaridad fija: si gira al revés, se corrige en el firmware.

### J11 (J_EXP): expansión y consola (2 × 5, sin montar)

| Pad | Rótulo | Red | Notas |
|-----|--------|-----|-------|
| 1 | G | GND | |
| 2 | 3V3 | 3V3 | Comparte el TPS63802 (2 A) con la placa, que pide hasta ≈ 0,7 A de pico |
| 3 | VSYS | VSYS | 3,0–4,4 V; directo del power path |
| 4 | 5V | VBUS | 5 V solo con USB, tras el PTC de 1,5 A |
| 5 | P04 | EXP_P07 (puerto **P04** del TCA9535) | E/S libre de 3,3 V del expansor (la red conserva su nombre antiguo) |
| 6 | IO5 SCL | I2C_SCL (GPIO5) | Bus I2C de la placa (4,7 kΩ de pull-up; ojo a las direcciones 0x20 y la de la cámara) |
| 7 | IO43 TX | U0TX (GPIO43) | **Consola UART0, salida de la placa** |
| 8 | G | GND | |
| 9 | IO4 SDA | I2C_SDA (GPIO4) | Bus I2C |
| 10 | IO44 RX | U0RX (GPIO44) | **Consola UART0, entrada de la placa** |

**Consola serie:** adaptador USB-serie **de 3,3 V** (nunca de 5 V), 115 200 baudios, 8N1: GND a J11.1 u 8, RX del adaptador a J11.7, TX del adaptador a J11.10; el 3V3 del adaptador no se conecta. Por J11.7 sale el log del ROM al arrancar, y D3 (TX) parpadea con él. El orden de J11 se cambió en el rutado (bloque U): 5 P04, 6 SCL, 7 TX, 9 SDA, 10 RX.

## Mapa de pines para el firmware

**El firmware debe seguir este mapa** (también en `NOTAS.md`, «Pines»).

### ESP32-S3-WROOM-1 (U4)

| GPIO | Pin | Red | Función |
|------|-----|-----|---------|
| GPIO0 | 27 | BOOT | Botón BOOT (SW2), pull-up R18; pin de arranque |
| GPIO1 | 39 | VBAT_SNS | ADC1_CH0: VBAT / 2 |
| GPIO2 | 38 | LIGHT | ADC1_CH1: LDR |
| GPIO3 | 15 | IPROPI_IO | ADC1_CH2: corriente del motor, 2,25 V/A (por JP3); pin de arranque de JTAG, inocuo sin eFuse |
| GPIO4 / GPIO5 | 4 / 5 | I2C_SDA / I2C_SCL | I2C a 400 kHz: TCA9535 (0x20), cámara (SCCB), J_EXP |
| GPIO6 | 6 | EXP_INT | INT del TCA9535 (activa a 0); despierta del sueño profundo |
| GPIO7 | 7 | I2S_BCLK | Reloj de bit I2S |
| GPIO8 | 12 | ENC_IO | Encoder del mecanismo (por JP4) |
| GPIO9 | 17 | MOT_IN1_IO | IN1 del puente H (PWM, por JP1) |
| GPIO10–GPIO14 | 18–22 | CAM_VSYNC, CAM_HREF, CAM_Y9, CAM_XCLK_IO, CAM_Y8 | Cámara (XCLK sale por R59 de 33 Ω, junto al pin) |
| GPIO15 | 8 | I2S_WS | Selección de canal I2S |
| GPIO16 | 9 | I2S_DOUT | Datos al amplificador |
| GPIO17 | 10 | I2S_DIN | Datos del micro |
| GPIO18 | 11 | HOME | Leva del mecanismo (activa a 0) |
| GPIO19 / GPIO20 | 13 / 14 | USB_DN / USB_DP | USB nativo |
| GPIO21 | 23 | CAM_Y7 | Cámara |
| GPIO35–GPIO37 | 28–30 | — | Ocupados por la PSRAM octal |
| GPIO38–GPIO41 | 31–34 | CAM_Y2, CAM_Y5, CAM_Y3, CAM_Y4 | Cámara |
| GPIO42 | 35 | IR_RX | Receptor IR (RMT) |
| GPIO43 / GPIO44 | 37 / 36 | U0TX / U0RX | Consola UART0 (J_EXP.7 / .10); LED D3 en TX |
| GPIO45 | 26 | IR_TX | Emisor IR por Q3 (RMT); pin de arranque de VDD_SPI: R55 lo mantiene a 0 (flash de 3,3 V) |
| GPIO46 | 16 | MOT_IN2_IO | IN2 del puente H (PWM, por JP2); pin de arranque: R30 lo mantiene a 0 |
| GPIO47 / GPIO48 | 24 / 25 | CAM_PCLK / CAM_Y6 | Cámara (PCLK llega por R60 de 33 Ω, junto a J6) |
| EN | 3 | EN | Reset (SW1), RC de R17 y C11 (≈ 10 ms) |

GPIO3, GPIO45 y GPIO46 son pines de arranque: el firmware no los debe forzar durante el reset (los pull-downs de la placa ya dan el valor correcto). No quedan GPIO del módulo libres: para usar uno, se corta su puente (JP1–JP4, ver abajo) o se usa J_EXP.

### Expansor TCA9535 (U10, dirección 0x20)

| Puerto | Pin | Red | Dirección | Función |
|--------|-----|-----|-----------|---------|
| P00 | 4 | TILT_A | Entrada | Inclinación A (J8 «TLA») |
| P01 | 5 | TILT_B | Entrada | Inclinación B (J8 «TLB») |
| P02 | 6 | TONGUE | Entrada | Lengua (J8 «LNG») |
| P03 | 7 | LED_RUN_K | Salida | LED RUN (D5): 0 = encendido |
| P04 | 8 | EXP_P07 | Libre | J_EXP.5 «P04» |
| P05 | 9 | AMP_SD | Salida | 1 = amplificador activo |
| P06 | 10 | PGOOD | Entrada | 0 = USB presente y válido |
| P07 | 11 | CHG | Entrada | 0 = cargando |
| P10 | 13 | BQ_EN1 | Salida | Modo de entrada del cargador (con P11) |
| P11 | 14 | BQ_EN2 | Salida | EN2 = 0, EN1 = 1: USB500 (arranque); EN2 = 1, EN1 = 0: ILIM (1,34 A) |
| P12 | 15 | EN_6V | Salida | 1 = elevador de 6 V encendido y LED del encoder (R51, ≤ 10 mA desde el puerto) |
| P13 | 16 | TUMMY | Entrada | Barriga (J9 «BAR») |
| P14 | 17 | BACK | Entrada | Espalda (J9 «ESP») |
| P15 | 18 | CAM_PWDN | Salida | 1 = cámara en reposo (pull-up R34 al arrancar) |
| P16 | 19 | CAM_EN | Salida | 1 = LDO de la cámara encendidos |
| P17 | 20 | IR_PWR | Salida | Alimentación del receptor IR (J7.8) |

Al arrancar, con el expansor en entradas, los pull-ups y pull-downs dejan la placa en reposo: cargador en USB500, elevador apagado (R25), motor parado (R29, R30), cámara sin alimentar (R33) y amplificador apagado (SD_MODE del MAX98357A tiene un pull-down interno según su hoja de datos). Las entradas no tienen histéresis: antirrebote por firmware de ≥ 30 ms.

## Puntos de test

Todos en la cara inferior, con su rótulo al lado y a ≤ 5 mm de la pieza que genera la señal. Coordenadas de la base en mm (las del PCB).

| TP | Rótulo | Red | Posición | Valor esperado |
|----|--------|-----|----------|----------------|
| TP1 | VBUS | VBUS | (−70,6; −110,8) | 5,00 V ± 0,25 con USB |
| TP2 | D+ | USB_DP | (−84,3; −81,3) | Señal USB (osciloscopio) |
| TP3 | D- | USB_DN | (−74,5; −118,85) | Señal USB (osciloscopio) |
| TP4 | BAT | BAT | (−64,5; −120,4) | 3,0–4,2 V (batería tras Q1) |
| TP5 | VSYS | VSYS | (−66,45; −105,0) | 4,40 V ± 0,10 con USB; VBAT − 0,05 sin USB |
| TP6 | 3V3 | 3V3 | (−84,5; −110,0) | 3,30 V ± 0,10 |
| TP7 | 6V | V6 | (−54,0; −118,0) | 5,94 V ± 0,15 con EN_6V = 1; ≈ VSYS − 0,4 V apagado |
| TP8 | IPR | IPROPI | (−51,3; −100,9) | 2,25 V por amperio de motor (≈ 2,25 V con el motor bloqueado) |
| TP9 | I2S | I2S_DOUT | (−91,5; −92,0) | Datos I2S al amplificador |
| TP10 | 2V8 | CAM_2V8 | (−53,0; −90,6) | 2,80 V ± 0,06 con CAM_EN = 1 |
| TP11 | 1V2 | CAM_DVDD | (−50,1; −98,5) | 1,20 V ± 0,05 (1,50 V con ME6211C15) |
| TP12, TP13, TP14 | G | GND | (−74,5; −75,0), (−57,5; −107,4), (−98,3; −86,4) | Masa para la sonda |

## LED

| LED | Color | Rótulo | Se enciende cuando… | Corriente |
|-----|-------|--------|---------------------|-----------|
| D1 | Rojo | — (junto al cargador) | La batería se está cargando (CHG a 0); parpadea a 1 Hz si la carga se suspende por temperatura o fallo | ≈ 1,4 mA desde VBUS (R10), solo con USB |
| D2 | Verde | — (junto al cargador) | Hay un USB válido (PGOOD a 0) | ≈ 1,4 mA desde VBUS (R11), solo con USB |
| D3 | Rojo | TX | Sale un carácter por la consola UART0 (log del ROM al arrancar, resets, firmware) | ≈ 1 mA (R19 de 1,5 kΩ) |
| D4 | Verde | PWR | Hay 3,3 V | 0,5–0,9 mA (R57 de 1 kΩ); se apaga cortando JP5 |
| D5 | Verde | RUN | El firmware pone P03 del expansor a 0 (latido) | 0,5–0,9 mA (R58 de 1 kΩ) |

D1 y D2 se alimentan del USB y no gastan batería. D4 y D5 son verdes de InGaN (VF 2,6–3,1 V): con resistencias mayores casi no se verían.

## Botones y puentes

| Pieza | Rótulo | Qué hace |
|-------|--------|----------|
| SW1 | RST | Reset del módulo (EN a GND) |
| SW2 | BOOT | GPIO0 a GND: mantenido durante el reset, entra en modo descarga (también por USB sin botones, desde `esptool`) |
| JP1 | IO9 | **Cerrado de fábrica.** Une GPIO9 con IN1 del puente H. Cortado, GPIO9 queda libre y el motor no gira en ese sentido |
| JP2 | IO46 | Cerrado. Une GPIO46 con IN2 del puente H |
| JP3 | IO3 | Cerrado. Une GPIO3 (ADC) con IPROPI |
| JP4 | IO8 (solo en la cara inferior) | Cerrado. Une GPIO8 con la salida del Schmitt del encoder |
| JP5 | LED | Cerrado. Une el cátodo de D4 (PWR) con GND; cortarlo ahorra hasta 0,9 mA dormido |

Los puentes son de soldadura con un puente de cobre entre los dos medios pads: se abren cortando con un cúter entre las dos mitades y se vuelven a cerrar con una gota de estaño. Cada uno lleva su rótulo arriba (salvo JP4) y abajo.

## Simulación

Simulaciones con ngspice y modelos de comportamiento declarados (no hay modelos SPICE de estos chips para ngspice): cada `.cir` de [`sim/`](sim/) dice qué supone; `python3 -I sim/analiza.py` las repite. **La simulación no sustituye a la medida**: el bring-up (`TEST-PLAN.md`) manda.

| Bloque | Resultado | Lo importante |
|--------|-----------|---------------|
| Elevador de 6 V | PASS | Pico de bobina 2,82 A frente a ILIM 3,8 A; rizado de 19 mV. Isat de L2 por verificar (≥ 3,4 A) |
| 3V3 (TPS63802) | PASS | Mínimo 3,20 V en el peor caso con picos de TX; rizado < 6 mV |
| Batería y Q1 | PASS | Ningún nodo negativo con la batería al revés, con o sin USB |
| Power path (BQ24073) | **2 FAIL** | Con USB500 y un pico de 2,9 A, VBAT − VSYS supera VO(SC2) y la placa se reiniciaría; al enchufar con ≥ 4,3 W de carga en ILIM, VSYS se queda en supplement. **Lo cubre el firmware** |
| Puente H y motor | PASS | Corriente regulada a 1,0 A; Tj del DRV8231A 103 °C con el motor bloqueado continuo (límite 110 °C) |
| Amplificador | PASS con C41 | 70 mV pp de rizado en VDD (87 en el peor caso; 258 sin C41) |
| LDO de la cámara | PASS | Arranque monótono, DVDD nunca por encima de AVDD |
| NTC en TS | PASS | Ventana de carga de 0,2–51,2 °C |
| Señales | PASS con condición | I2C a 400 kHz justo; LED verdes visibles con 1 kΩ; **ADC solo con lecturas a ≤ 1 kHz** |
| Arranque y caída de batería | **FAIL** | El pico de 10,2 W (motor bloqueado + TX + audio) hunde VSYS bajo el UVLO del elevador con la batería < 3,36 V (celda nominal) o < 4,0 V (celda vieja): el motor da tirones; 3V3 aguanta. **Lo cubren el firmware y una celda de ≤ 100 mΩ** |

## Reglas para el firmware

La v1.0 depende del firmware para no pasar de estos límites (`NOTAS.md`, «Reglas para el firmware», con el porqué de cada una; se miden en `TEST-PLAN.md` §18):

1. **Con USB enchufado** (PGOOD a 0, P06): motor con PWM ≤ 50 % y audio ≤ −12 dBFS mientras se mueve; carga total de VSYS ≤ ≈ 2,0 A. El límite se aplica antes de mover el motor.
2. **Al enchufar el USB** (flanco de PGOOD): pausar motor y audio ≈ 5 ms para que VSYS suba a 4,4 V.
3. **Modo ILIM** (EN2 = 1, EN1 = 0) solo con una fuente **declarada** de ≥ 1,5 A y la placa fría; si no, USB500. **La placa no lee CC**: no puede saber qué da el cargador.
4. **Motor y audio a plena potencia a la vez solo con VBAT ≥ 3,7 V** (VBAT_SNS medido en carga); por debajo, PWM ≤ 60 % y audio ≤ −12 dBFS.
5. **Celda con resistencia interna ≤ 100 mΩ** (con su PCM), medida antes de soldarla.
6. **ADC de VBAT_SNS y LIGHT en lecturas sueltas a ≤ 1 kHz de media**, nunca en modo continuo (divisor de 235 kΩ).
7. Bloqueo del motor cortado a **≤ 150 ms** (encoder o IPROPI); portadora IR continua **≤ 50 ms**; antirrebote **≥ 30 ms** en la INT del TCA9535; reset de la cámara por **SCCB**.

## Limitaciones conocidas

- **Sin lectura de CC:** el cargador arranca en USB500 (0,475 A) y solo puede subir a 1,34 A si el firmware sabe por configuración que la fuente lo aguanta. El PTC es de 1,5 A, poco margen frente a ILIM.
- **Picos de potencia con la batería baja:** con VBAT < 3,7 V el firmware tiene que repartir la potencia (regla 4) o el elevador se corta en los picos.
- **VO(SC2) con USB500:** un pico de 2,9 A con el USB enchufado puede apagar VSYS 60 ms (regla 1).
- **DRV8231A con el motor bloqueado:** 103 °C de unión en régimen; depende del corte por firmware a 150 ms.
- **Agujero del mecanismo dado por bueno sin medir** (Ø11,3 mm, decisión del autor del 2026-10-24). El cobre más cercano a su borde es MOT_IN2 a 0,34 mm, IPROPI a 0,43, HOME a 0,63 y MOT_IN1 a 0,64 (medido en el PCB, 2026-10-25): cumple el mínimo del fabricante (0,2 mm), pero agrandar el agujero cortaría pistas.
- **Rizado de VDD del amplificador:** 70 mV pp simulados (87 en el peor caso): C41 no cabe pegado a los pines 7/8 (con él pegado serían 25 mV pp).
- **Pinout de la cámara de facto:** el FPC sigue el pinout habitual de los módulos para ESP32; hay que comprobarlo con el módulo comprado.
- **Antes del pedido:** lista «Confirmar antes de pedir» de [`fabricacion/README.md`](fabricacion/README.md); la NTC RT1 (C13564) es NRND, con alternativa C440252 en la misma huella.
- **Sin GPIO libres:** solo J_EXP (I2C, UART, P04 y alimentaciones); los puentes JP1–JP4 liberan GPIO9, GPIO46, GPIO3 y GPIO8 si se renuncia a su función.
- **Serigrafía:** la leyenda de J9 está aparte (22 mm por encima de sus pads), «IO8» de JP4 solo en la cara inferior, J5 sin título y 12 textos a 0,8 mm de letra, en cuatro grupos (nombre de la cara superior, leyenda de J7, «I2S» de TP9, «BAT» de TP4 y «BAT-» de J3), por debajo del 1,0 mm recomendado por JLCPCB.
- **Pendiente para la v1.1:** TVS en VBUS, agujeros para atar los cables de la batería, PTC de 2 A, pull-ups de I2C según la medida, RC de VBAT_SNS y LIGHT junto al módulo, F1 entre J1 y U2, leer CC, NTC de B 3950–4100 K si la celda pide 0–45 °C, R54 en 1206, sitio para la leyenda de J9 junto a sus pads y un header de GPIO libres.

## Cómo regenerar

Todo se genera desde [`scripts/`](scripts/); **el PCB no se edita a mano en KiCad** (se perdería en la siguiente regeneración) y no se regenera con el proyecto abierto en KiCad. Herramientas: KiCad 10 (`kicad-cli` y su Python, que trae `pcbnew`), Python 3 del sistema, ngspice para `sim/` y, para las comprobaciones de rutado y las imágenes de revisión, pcb-toolkit (herramienta propia del autor, fuera de este repositorio; sin ella, el DRC de KiCad sigue siendo la puerta mínima).

```sh
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli

python3 scripts/gen_lib.py                       # símbolos y huellas propias (lib/)
python3 scripts/gen_sch.py                       # esquema jerárquico desde design.py
for f in FurbyBoard.kicad_sch hojas/*.kicad_sch; do $KC sch upgrade "$f"; done
python3 scripts/gen_pro.py                       # proyecto, clases de red, reglas y .kicad_dru
python3 scripts/logo_guillemaker.py              # huella del logo de GuilleMaker (lib/; numpy, Pillow y matplotlib)
$KP scripts/gen_pcb.py                           # coloca, ruta (rutas_fijas.py) y rotula; zonas sin rellenar
python3 scripts/gen_pro.py                       # otra vez: guardar el PCB reescribe el .kicad_pro
scripts/rellenar.sh                              # rellena las zonas con las reglas del proyecto (kicad-cli) y pasa el DRC

$KC sch erc --severity-all --exit-code-violations FurbyBoard.kicad_sch
$KC pcb drc --schematic-parity --severity-all --exit-code-violations FurbyBoard.kicad_pcb
pcb-toolkit revisar-rutado FurbyBoard.kicad_pcb --ancho VSYS:0.6,BAT:0.8,…   # anchos de params.ANCHOS_MINIMOS
$KP scripts/comprobar_colocacion.py              # TP accesibles, calzos de la batería libres, alturas

scripts/make_fab.sh                              # BOM, CPL, Gerber, renders y STEP (solo tras la puerta E1)
```

| Script | Qué hace |
|--------|----------|
| `params.py` | Números de la placa: apilado, reglas de JLCPCB, anchos mínimos por red, versión |
| `design.py` | **Fuente de verdad**: piezas, valores, huellas, códigos LCSC y la red de cada pin |
| `layout.py` | Posición y giro de cada pieza (coordenadas de la base), zonas y pasillos |
| `rutas_fijas.py` | Todo el rutado: pistas, vías y polígonos por bloques, con el motivo de cada decisión |
| `serigrafia.py` | Rótulos y su colocación automática (sin pisar vías, pads ni otros rótulos) |
| `logo_guillemaker.py` | Huella del logo de GuilleMaker desde `serigrafia/logo-guillemaker.png` (contornos rellenos en serigrafía) |
| `gen_lib.py`, `gen_sch.py`, `gen_pro.py`, `gen_pcb.py` | Generadores de librería, esquema, proyecto y PCB |
| `comprobar_colocacion.py` | Comprobaciones mecánicas que el DRC no ve |
| `jlc_post.py`, `make_fab.sh` | BOM y CPL en formato de JLCPCB (giros corregidos) y ficheros de fabricación |
| `gen_modelos3d.py`, `render_montaje.py` | Modelos 3D propios (FreeCAD) y render de la placa montada en la base (Blender) |
| `rellenar.sh` | Rellena las zonas con las reglas del proyecto (kicad-cli) y pasa el DRC; va después de `gen_pro.py` |
| `exportar_dsn.py`, `ensanchar_potencia.py`, `vias_extra.py`, `router/` | Del intento de 4 capas con autorrutador: **no se usan** |

## Estructura de la carpeta

| Ruta | Qué es |
|------|--------|
| `FurbyBoard.kicad_pro`, `FurbyBoard.kicad_sch`, `hojas/` | Proyecto y esquema jerárquico (usb, alimentación, mcu, motor, audio, cámara, sensores, led_tp) |
| `FurbyBoard.kicad_pcb`, `FurbyBoard.kicad_dru` | PCB de 6 capas y reglas a medida (anchos por red, vías del par USB, pads del USB-C y del FPC) |
| `pcb-toolkit.toml` | Configuración de las comprobaciones: redes críticas, anchos, zonas calientes, grupos de buses |
| `lib/` | Símbolos, huellas y modelos 3D propios (USB-C, FPC, TPS63802, SI7615ADN, pads de cable y de batería, logos) |
| `serigrafia/` | Fuente del logo de GuilleMaker (PNG en gris, sin metadatos) |
| `scripts/` | Generadores (ver arriba) |
| `sim/` | Simulaciones ngspice, modelos, `analiza.py` y [`RESULTADOS.md`](sim/RESULTADOS.md) |
| `revisiones/` | Informes de las puertas de revisión |
| `fabricacion/` | Ficheros para JLCPCB y su [`README.md`](fabricacion/README.md) (se rellena con `make_fab.sh`) |
| `render/` | Renders e imágenes (las de colocación y «rutado pendiente» son del intento de 4 capas) |
| `NOTAS.md`, `TEST-PLAN.md` | Decisiones y cálculos; plan de pruebas de bring-up |

Documentos relacionados: la arquitectura y el presupuesto de potencia en [`../PCB-suelo/ARQUITECTURA.md`](../PCB-suelo/ARQUITECTURA.md) (donde no coincida, mandan `NOTAS.md` y el esquema), y la geometría compartida con la base en [`../PCB-suelo/interfaz-base.md`](../PCB-suelo/interfaz-base.md) y `geometria.json`.
