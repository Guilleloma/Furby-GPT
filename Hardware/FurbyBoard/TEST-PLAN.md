# FurbyBoard v1.0: plan de pruebas de hardware

Bring-up paso a paso para cuando llegue la placa montada de JLCPCB. Los designadores, valores y TP son los del esquema y el PCB de `Hardware/FurbyBoard/` (generados por `scripts/design.py`). Sustituye al borrador de la fase 1 (`Hardware/PCB-suelo/TEST-PLAN.md`).

**Reglas:**

- Se hace en orden, y no se pasa de un paso con un FAIL sin entenderlo.
- Se anota el valor medido junto al esperado, en una copia de estas tablas por placa. La placa se numera a rotulador en el recuadro «PLACA» de la serigrafía de la cara inferior.
- La batería no se suelda hasta el paso 8, después de probar la protección contra la inversión (8.1) y de medir su polaridad (8.2).

## Dónde está cada punto de medida

Todos los TP, LED, botones y puentes quedan fuera de la batería: se miden con ella montada. Coordenadas del STL de la base, en mm (delante = y mayor).

| TP | Red | Rótulo | Posición (x, y) | Dónde | Esperado |
|----|-----|--------|-----------------|-------|----------|
| TP1 | VBUS | VBUS | (−70,6; −110,8) | Cara inferior, detrás del cargador U2, junto a C1, C2 y C5 | 5,00 V con USB |
| TP2 | USB_DP | D+ | (−84,3; −81,3) | Cara inferior, a la izquierda del módulo, sobre el canal del par USB | — (osciloscopio) |
| TP3 | USB_DN | D- | (−74,5; −118,85) | Cara inferior, junto a U1 (ESD), al lado del USB-C | — (osciloscopio) |
| TP4 | BAT | BAT | (−64,5; −120,4) | Cara inferior, entre J2 (BAT+), J3 (BAT−) y Q1 | VBAT 3,0–4,2 V (tras Q1) |
| TP5 | VSYS | VSYS | (−66,45; −105,0) | Cara inferior, junto a C3 y C17 (salida del cargador) | 4,40 V con USB; VBAT − 0,05 sin USB |
| TP6 | 3V3 | 3V3 | (−84,5; −110,0) | Cara inferior, junto a C8 (salida del buck-boost, zona trasera izquierda) | 3,30 V |
| TP7 | V6 | 6V | (−54,0; −118,0) | Cara inferior, esquina trasera derecha, junto a la compensación del elevador | 5,94 V con EN_6V = 1 |
| TP8 | IPROPI | IPR | (−51,3; −100,9) | Cara inferior, junto a R28 y al puente H U6 | 2,25 V por amperio de motor |
| TP9 | I2S_DOUT | I2S | (−91,5; −92,0) | Cara inferior, al sureste del amplificador U7 | Datos I2S al amplificador |
| TP10 | CAM_2V8 | 2V8 | (−53,0; −90,6) | Cara inferior, junto a U8 (LDO de 2,8 V), bajo el FPC | 2,80 V con la cámara encendida |
| TP11 | CAM_DVDD | 1V2 | (−50,1; −98,5) | Cara inferior, junto a U11 y C29, a la izquierda de J9 | 1,20 V (1,50 V con ME6211C15) |
| TP12, TP13, TP14 | GND | G | (−74,5; −75,0), (−57,5; −107,4), (−98,3; −86,4) | Cara inferior: bajo el módulo (TP12), junto a los LED del cargador D1/D2 (TP13) y junto al amplificador, al lado de C41 (TP14) | 0 V (pinza del osciloscopio) |

Coordenadas del STL de la base (las del PCB, en mm). Cada TP lleva su rótulo al lado en la cara inferior.

Otras medidas sin TP propio:

| Red | Dónde se mide |
|-----|---------------|
| EN | Pad de SW1 (RST) que no va a GND, o R17 |
| GPIO0 (BOOT) | Pad de SW2 (BOOT) que no va a GND, o R18 |
| CHG | Cátodo de D1 (LED rojo junto al cargador) |
| PGOOD | Cátodo de D2 (LED verde junto al cargador) |
| U0TX / U0RX | J_EXP (J11) pines 7 y 10 (cara inferior: «IO43 TX», «IO44 RX»): consola UART0, ver «Consola serie» |
| VBAT_SNS | C5 (100 nF del divisor de VBAT) |

### Consola serie (UART0 en J_EXP)

Adaptador USB-serie **de 3,3 V** (nunca de 5 V: los pines del ESP32-S3 no lo toleran), a 115 200 baudios, 8N1:

| Adaptador | J_EXP (J11) | Rótulo en la cara inferior |
|-----------|-------------|-----------------------------|
| GND | 1 u 8 | «G» |
| RX | 7 (U0TX, GPIO43) | «IO43 TX» |
| TX | 10 (U0RX, GPIO44) | «IO44 RX» |

No se conecta el 3V3 del adaptador: la placa se alimenta por USB-C o por la batería. El LED TX (D3) parpadea con cada carácter que sale por U0TX.

## Equipo

| Equipo | Para qué |
|--------|----------|
| Polímetro con continuidad y escala de µA | Cortos, tensiones y consumo en reposo |
| Fuente de laboratorio de 0–6 V con límite de corriente | Primer arranque por la entrada de batería y simulación de la batería |
| Medidor USB-C en línea (tensión y corriente) y cargador de 5 V / 2 A | Primer arranque por USB y corriente de entrada |
| Osciloscopio de ≥ 50 MHz | Rizado, PWM del motor, I2S, clase D, D+/D− |
| Resistencias de potencia: 10 Ω / 5 W y 4,7 Ω / 10 W | Carga del elevador de 6 V |
| Termómetro de contacto o cámara térmica | Temperaturas |
| PC con `esptool` y ESP-IDF o Arduino; cable USB-C de datos | Enumeración, flasheo y firmwares de prueba |
| Altavoz del Furby (4 Ω, 3 W), motor del Furby o motor DC de prueba | Audio y motor |
| Dos cables con pinzas o puntas para soldar provisionalmente a J2 (BAT+) y J3 (BAT−) | Pruebas con la fuente en la entrada de batería |
| Módulo de cámara OV2640 (o el elegido) y su flex | Cámara |
| Otro ESP32 de referencia | Comparar el RSSI del WiFi |
| Batería LiPo 1S de 1400 mAh con PCM | Pasos 8 a 17 |

## 1. Inspección visual (sin alimentar)

| Comprobar | PASS | Si falla |
|-----------|------|----------|
| Pin 1 de U1 (USBLC6), U2 (BQ24073), U3 (TPS63802), U4 (WROOM-1), U5 (TPS61089), U6 (DRV8231A), U7 (MAX98357A), U8 y U9 (ME6211), U10 (TCA9535), U11 (74LVC1G17), Q1 (SI7615ADN) y Q3 (AO3400A) | Coincide con el punto o el chaflán de la serigrafía | Reclamar a JLCPCB o resoldar. Revisar `GIRO` en `scripts/jlc_post.py` para el siguiente pedido |
| Polaridad de los LED D1–D5 | Cátodo hacia el pad 1 de la huella (marca de la serigrafía) | Ídem |
| Puentes de estaño en los QFN, el TSSOP, el USB-C y el FPC | Ninguno (lupa ×10) | Retirar con malla y flux |
| USB-C (J1) asentado en la ranura, con las cuatro patas de la carcasa soldadas | Sin holgura | Resoldar las patas |
| Pads de la batería | J2 cuadrado con «+» (arriba) y «BAT+» (abajo); J3 redondo con «-» (arriba) y «BAT-» (abajo) | Defecto de serigrafía: marcar a mano antes de seguir |
| Puentes JP1–JP5 | Cerrados de fábrica (puente de cobre entre los dos medios pads) | Cerrarlos con estaño |
| Zona de la antena | Sin cobre ni componentes delante del módulo (x −85 a −61) | Defecto de diseño: anotarlo |
| Prueba en seco en la base del Furby, **antes de soldar la batería**: placa atornillada con los 4 × M2 y el mecanismo girado a mano una vuelta completa | El eje del mecanismo pasa por el agujero de Ø11,3 sin rozar el borde | **Descartar la placa, no limar**: MOT_IN2 e IPROPI pasan a 0,34–0,43 mm del borde del agujero (revisión E independiente, M10). El agujero se dio por bueno sin medirlo en el Furby |

## 2. Cortos y continuidad (sin alimentar)

Polímetro en ohmios, punta negra en GND (TP12–TP14).

| Carril | Esperado | PASS | Si falla |
|--------|----------|------|----------|
| VBUS (TP1)–GND | > 10 kΩ | No es un corto (< 10 Ω) | Revisar F1, U1 (USBLC6) y la entrada de U2 |
| BAT (TP4)–GND | ≈ 940 kΩ (R13 + R14, 470k + 470k) en paralelo con U2 | > 50 kΩ | Revisar el divisor y U2 |
| J2 (BAT+)–GND | > 100 kΩ (Q1 cortado sin alimentar) | No es un corto | Revisar Q1 |
| VSYS (TP5)–GND | > 1 kΩ | > 100 Ω | Revisar U3, U5 y U7 |
| 3V3 (TP6)–GND | Del orden de kΩ (módulo sin alimentar) | > 100 Ω | Levantar L1 y medir otra vez para aislar U3 |
| 6V (TP7)–GND | > 10 kΩ | > 1 kΩ | Revisar U6 y C18–C22 |
| 2V8 (TP10) y 1V2 (TP11)–GND | > 10 kΩ | > 1 kΩ | Revisar U8, U9 y C28–C29 |
| VBUS–VSYS, VSYS–3V3, 3V3–6V | Sin continuidad directa | > 100 Ω | Puente entre carriles: buscarlo con la lupa |
| D+ y D− de J1 (TP2, TP3) a los pads 14 (D+) y 13 (D−) del módulo | < 1 Ω | Continuidad | Revisar soldaduras |

## 3. Primer arranque por la entrada de batería (fuente limitada)

Fuente de laboratorio en **J2 (BAT+) y J3 (BAT−)**, con pinzas o cables soldados provisionalmente: **3,70 V, límite de 150 mA**. Sin USB, sin cámara, sin motor ni altavoz.

| Medida | Esperado | PASS / FAIL | Si falla |
|--------|----------|-------------|----------|
| Corriente al encender | Pico < 150 mA y luego 30–60 mA (el módulo arranca en blanco o con la prueba de fábrica) | PASS: < 100 mA estable. FAIL: la fuente limita | Apagar. Medir VSYS y 3V3 con la fuente limitada a 50 mA y buscar el carril que cae |
| VSYS (TP5) | 3,65 V ± 0,05 (VBAT − ≈ 50 mV) | ± 0,1 | U2 sin soldar o en cortocircuito |
| Caída en Q1 (J2 − TP4) | < 5 mV a 50 mA | < 10 mV | Q1 sin conducir: puerta a GND por R12 (10 kΩ) |
| 3V3 (TP6) | 3,30 V ± 0,10 | ± 0,10 | U3: divisor R15/R16 (510k/91k) y L1 |
| LED PWR (D4) | Encendido (0,5–0,9 mA con R57 de 1 kΩ) | | Polaridad de D4, R57 o JP5 abierto |
| LED TX (D3) | Parpadea al arrancar y al pulsar RST | | D3, R19 y GPIO43 |
| Consola en J11.7 (IO43 TX) a 115 200 baudios («Consola serie») | Log del ROM: `ESP-ROM:esp32s3…` | | EN en SW1 a 3,3 V y C11 (RC de EN con R17) |

Luego, la fuente a **3,0 V**: 3V3 tiene que seguir en 3,30 ± 0,10 (U3 elevando). A **4,2 V**: igual.

## 4. Primer arranque por USB

Medidor USB-C en línea, con un cargador de 5 V. Se quita la fuente del paso 3: sin batería.

| Medida | Esperado | Si falla |
|--------|----------|----------|
| Corriente de entrada | < 150 mA | Desenchufar y volver al paso 2 |
| VBUS (TP1) | 5,0 V ± 0,25 | Cable, F1, R1/R2 (5,1 kΩ en CC1/CC2) |
| VSYS (TP5) | 4,40 V ± 0,10 (OUT regulado de U2) | U2: R5 (ILIM 1,2 kΩ), EN1 (R6 a VSYS) y EN2 (R7 a GND): USB500 sin firmware |
| LED PG (D2, verde junto al cargador) | Encendido | PGOOD o D2/R11 |
| LED CHG (D1, rojo) | Apagado o parpadeando (sin batería, U2 detecta que falta) | Normal sin batería |

## 5. Enumeración USB y primer flasheo

| Paso | PASS | Si falla |
|------|------|----------|
| `lsusb` (macOS: `system_profiler SPUSBDataType`) | Aparece «USB JTAG/serial debug unit» (VID 303A) | D+ y D− (¿cruzados?), U1 y el cable de datos. Probar con BOOT (SW2) pulsado al enchufar |
| `esptool.py chip_id` y `flash_id` | ESP32-S3, 16 MB de flash; PSRAM de 8 MB en el log de arranque | Modo descarga a mano: mantener BOOT, pulsar y soltar RST, soltar BOOT |
| Flashear el firmware de prueba (`furbyboard-test`) | Se graba y arranca | Ver el log por J11 pin 7 |
| LED RUN (D5) | Parpadea a 1 Hz (latido del firmware de prueba, P03 de U10) | I2C a U10 (escaneo: 0x20), R36/R37 |

## 6. LED

| LED | Prueba | PASS |
|-----|--------|------|
| D4 PWR (verde, fila de arriba) | 3V3 presente | Encendido, visible a la luz de la habitación (0,5–0,9 mA: verde InGaN con R57 de 1 kΩ); se apaga al cortar JP5 «LED» (no cortarlo hasta acabar las pruebas) |
| D3 TX (rojo, fila de arriba) | Reset y entrada en modo descarga | Parpadea en cada reset y al entrar en descarga |
| D5 RUN (verde, fila de arriba) | Firmware de prueba (P03 de U10 a 0 enciende) | Parpadea, con el mismo brillo que D4 (R58 de 1 kΩ); apagado durante el flasheo |
| D1 CHG (rojo, junto al cargador) | Batería descargada y USB | Encendido mientras carga |
| D2 PG (verde, junto al cargador) | Con USB | Encendido |

## 7. Medida de cada carril (con el firmware de prueba)

| TP | Condición | Esperado | Tolerancia | Rizado (osciloscopio, 20 MHz de banda) |
|----|-----------|----------|------------|----------------------------------------|
| TP1 VBUS | USB | 5,00 V | ± 0,25 | — |
| TP5 VSYS | USB / sin USB | 4,40 V / VBAT − 0,05 | ± 0,10 | < 100 mVpp |
| TP6 3V3 | WiFi transmitiendo | 3,30 V | ± 0,10; caídas < 150 mV en los picos de TX | < 50 mVpp |
| TP7 6V | EN_6V = 1, sin carga | 5,94 V | ± 0,15 | < 100 mVpp |
| TP10 2V8 | Cámara encendida (CAM_EN, P16 = 1) | 2,80 V | ± 0,06 | < 30 mVpp |
| TP11 1V2 | Cámara encendida | 1,20 V (1,50 V con U9 = ME6211C15) | ± 0,05 | < 30 mVpp |
| EN (pad de SW1) | En marcha | 3,3 V | ± 0,1 | — |

## 8. Batería, carga y power path

### 8.1 Prueba de la protección contra la polaridad inversa (antes de soldar la batería)

| Paso | PASS | Si falla |
|------|------|----------|
| Fuente a **4,2 V con límite de 100 mA**, conectada **al revés**: + a J3 (BAT−) y − a J2 (BAT+). Sin USB | Corriente < 1 mA. TP4, TP5 y TP6 entre 0 y +0,1 V, **nunca negativos**. Nada se calienta | Cortar la fuente. Revisar la orientación de Q1 (pin 1) y R12 |
| Igual, pero con el **USB enchufado** (5 V con medidor) | Corriente por la fuente invertida de 4 a 11 mA (detección de cortocircuito de U2). TP4 entre +0,4 y +1,6 V, positivo. D1 apagado o parpadeando. Q1 < 40 °C a los 2 min | Con más de 60 mA: U2 ha entrado en precarga. Si la VGS(th) de Q1 está en el límite, sigue siendo seguro (≈ 0,3 W). Anotarlo para la v1.1 |
| Quitar la fuente, conectarla bien (3,7 V) y repetir el paso 3 | Todo funciona igual que antes de la prueba | Revisar U2 y el divisor R13/R14 |

### 8.2 Polaridad de la batería y soldadura

| Paso | PASS | Si falla |
|------|------|----------|
| Medir con el polímetro en continua entre los dos cables de la batería, con la punta roja en el cable que se piensa soldar a BAT+ | +3,0 a +4,2 V. Si sale negativo, ese cable es el −. Marcar el + con cinta | Si sale 0 V: la protección de la batería está cortada. Despertarla con una fuente limitada a 4,2 V / 100 mA |
| Soldar el cable + al pad **cuadrado J2 («+»)** y el − al **redondo J3 («-»)**. Volver a medir entre J2 y TP12 | +3,0 a +4,2 V | Desoldar y corregir. La protección evita daños (8.1), pero la placa no funcionará |

### 8.3 Carga y power path

Con la batería real, ya soldada (8.2).

| Prueba | Procedimiento | PASS | Si falla |
|--------|---------------|------|----------|
| Corriente de carga | Batería a ≈ 3,6 V, USB, firmware en reposo. Polímetro en serie con la batería | 0,44–0,54 A en corriente constante (R4 = 1,8 kΩ: 890 / 1800 = 0,494 A) | R4 y la temperatura de U2 (por encima de 125 °C regula a la baja) |
| Fin de carga | Dejar cargar | D1 se apaga con VBAT = 4,20 V ± 0,02 y < 50 mA (10 % de ICHG) | Temporizador (TMR sin conectar: 5 h por defecto) o TS (RT1, ver la fila siguiente) |
| Sensor de temperatura (RT1, NTC 10 kΩ en TS) | Polímetro entre el pad 1 de RT1 (TS) y GND, cargando, placa a temperatura ambiente | V_TS ≈ 0,75 V a 25 °C (75 µA × 10 kΩ; entre 0,6 y 0,9 V de 15 a 35 °C) y la carga sigue (D1 encendido) | 0 V: RT1 en corto o TS a GND; > 1,2 V: RT1 sin soldar o abierta (U2 suspende la carga con TS al aire) |
| Ventana de carga por temperatura (0–50 °C, fija del BQ24073; se mide la PCB bajo la celda, no la celda) | **Hot:** calentar RT1 con aire caliente a baja temperatura o con el dedo durante 1 min mientras se mide V_TS e I_BAT | Al bajar V_TS de ≈ 0,31 V (RT1 ≈ 4,2 kΩ, ≈ 50–51 °C) la carga se suspende: I_BAT → 0 y D1 parpadea a 1 Hz; al enfriar, se reanuda sola (con el dedo no se llega: solo debe verse bajar V_TS sin cortar la carga) | Si no suspende: comprobar que TS va a RT1 y no a un 10 kΩ fijo; si suspende a temperatura ambiente: RT1 de valor incorrecto (debe ser 10 kΩ, B 3380 K) |
| | **Cold:** spray frío sobre RT1 (o placa en la nevera a ≈ 0 °C unos minutos) | Al subir V_TS por encima de ≈ 2,1 V (RT1 ≈ 28 kΩ, 0 °C) la carga se suspende y se reanuda al volver a temperatura ambiente | Igual que arriba |
| Conmutación sin reinicio | Firmware que imprime el tiempo desde el arranque y el motivo de reset. Enchufar y desenchufar el USB 20 veces, con WiFi activo | El tiempo no se reinicia; ningún reset por brown-out | C3, C6 y C7–C9. Medir VSYS en el osciloscopio durante el cambio (caída < 300 mV) |
| Modo suplemento | USB de 500 mA (puerto de ordenador) y motor en marcha | El sistema no se reinicia y la batería aporta la diferencia | Si salta «VO(SC2)»: aplicar los límites del firmware (§18) o subir a ILIM (EN1 = 0, EN2 = 1: 1,34 A con R5) solo con una fuente de ≥ 1,5 A conocida y la placa fría (restricción B8: la placa no lee CC) |
| USB500 al arrancar | Sin firmware (BOOT pulsado) | Corriente de entrada ≤ 0,5 A | R6 (pull-up de EN1) y R7 (pull-down de EN2) |

## 9. Medida de la batería por ADC

| Procedimiento | PASS | Si falla |
|---------------|------|----------|
| Con la batería soldada, en tres momentos de la carga (≈ 3,5, ≈ 3,9 y 4,2 V, con el USB quitado un momento para medir en reposo). Comparar la lectura del ADC (GPIO1, divisor R13/R14 × 2, calibración de eFuse) con el polímetro en TP4 | Error ≤ 2 % (≤ 80 mV) | R13/R14 (470k), C5 (100 nF) o la atenuación del ADC (12 dB) |

## 10. Elevador de 6 V

| Prueba | PASS | Si falla |
|--------|------|----------|
| En vacío (EN_6V = 1, P12 de U10) | TP7 = 5,94 V ± 0,15 | Divisor de realimentación R21/R22 (390k/100k) |
| Con 10 Ω entre TP7 y GND (≈ 0,6 A) | ≥ 5,80 V, rizado < 150 mVpp | L2, C18–C21, R20 (fSW) |
| Con 4,7 Ω (≈ 1,26 A), 10 s | ≥ 5,70 V; U5 < 80 °C; corriente de la batería ≈ 2,3 A a 3,7 V | R23 (ILIM 270 kΩ) o protección de la batería |
| Con EN_6V = 0 | ≈ VSYS − 0,4 V (diodo del FET alto de U5); U6 en reposo | Normal en este elevador |
| LED del encoder (J9 EN+), polímetro entre los pads de R51 | EN_6V = 1: 1,1–2,3 V en R51 (5–10 mA); EN_6V = 0: 0 V (LED apagado) | Con EN_6V = 0 y tensión en R51: R51 no va a EN_6V (esquema); con EN_6V = 1 y < 1,1 V: LED en corto o al revés en el cable, o P12 sin configurar como salida |

## 11. Motor

Con el motor del Furby y el mecanismo montado, o con un motor de prueba de la misma clase. El motor va a J9 «M1» y «M2» (cara inferior).

| Prueba | Procedimiento | PASS | Si falla |
|--------|---------------|------|----------|
| Bobinado (antes de conectarlo) | Medir la resistencia entre los cables del motor en 5 posiciones del eje; quedarse con la menor (R) | Anotar R. I de bloqueo ≈ 6 V / R. Si pasa de 1,0 A, ITRIP la limita | No hay datos publicados del motor: esta medida manda sobre la estimación (0,6–1,2 A) |
| Arranque seguro | Encender sin firmware (BOOT pulsado) | El motor no se mueve | R29/R30 (pull-downs de IN1 e IN2) |
| Dos sentidos | PWM a 20 kHz, 70 %, decaimiento lento, en cada sentido | Gira en los dos; M1 y M2 conmutan a 20 kHz. Si gira al revés de lo esperado, se cambia en el firmware (M1/M2 no tienen polaridad fija) | GPIO9 (IN1) y GPIO46 (IN2), JP1 y JP2 |
| Corriente en marcha | TP8 (IPROPI) / 2,25 V por A | Anotar el valor (se esperan 0,1–0,3 A) | — |
| Bloqueo | Frenar el eje con cuidado 200 ms | TP8 ≈ 2,25 V (≈ 1,0 A, regulado con ITRIP); el ESP no se reinicia y el PCM no corta | Bajar ITRIP subiendo R26 (4,7 kΩ → 6,8 kΩ: VREF 1,96 V, 0,87 A). Para subirla, R26 = 3,3 kΩ (1,10 A) |
| Inversiones | Bucle de 5 min alternando cada 0,4 s, con freno de 20–30 ms y rampa | Sin reinicios; U6 < 80 °C | Alargar el freno o la rampa, o bajar ITRIP |
| Posición | Ir al final de carrera (GPIO18, J9 «LEVA») y contar pulsos del encoder (GPIO8) en un ciclo completo | Mismo número de pulsos (± 1) en 10 ciclos | U11 (Schmitt), R52 (pull-up del fototransistor, 10 kΩ, ajustable de 4,7 a 47 kΩ), LED del encoder (R51 de 220 Ω desde EN_6V, P12 de U10: solo luce con EN_6V = 1, ≈ 8 mA) |

## 12. Sensores del Furby

Pads en la cara inferior: barriga «BAR» y espalda «ESP» en J9, lengua «LNG» e inclinación «TLA»/«TLB» en J8. La leyenda de J9 no cabe junto a sus pads: está encima, con el título «J9» y el rótulo del pad 1 («ENF») recuadrado, en la misma disposición que los pads vistos desde abajo.

| Sensor | Procedimiento | PASS |
|--------|---------------|------|
| Barriga, espalda, lengua, inclinación A y B | Puentear cada pad a su «G» con unas pinzas y leer U10 | Cambia el bit correcto (P00 TLA, P01 TLB, P02 LNG, P13 BAR, P14 ESP) y salta la INT en GPIO6. Despierta del sueño profundo |
| Leva | Puentear «LEVA» a «G» en J9 | GPIO18 a 0 |
| Encoder | Girar el mecanismo a mano con el elevador encendido (EN_6V = 1) | Pulsos limpios en GPIO8 (osciloscopio en JP4: flancos < 1 µs tras U11) |
| Luz | Tapar el sensor e iluminarlo con una linterna | La lectura del ADC (GPIO2, LDR en J7 «3V3»/«LDR» con R53 de 470 kΩ) cambia más de 1 V |
| IR | Mando de TV hacia el receptor (J7, GPIO42; alimentado desde J7.8 «RXV», P17 de U10 a 1) y emisión por RMT (GPIO45, Q3) hacia un receptor conocido | Se decodifican tramas en los dos sentidos; con P17 a 0, J7.8 a 0 V y el receptor calla |

Si falla, se revisa por este orden: la soldadura del cable, el pull-up (R39/R41/R43 de 47 kΩ; R45/R47 de 220 kΩ en la inclinación), la serie de 1 kΩ (R40–R48), el condensador (C33–C37) y la dirección de U10.

## 13. Audio

| Prueba | Procedimiento | PASS | Si falla |
|--------|---------------|------|----------|
| Micro | Grabar 10 s a 16 kHz (J5 «SD», GPIO17) y escuchar el fichero | Voz clara; ruido de fondo < −60 dBFS en silencio | Selección L/R en la placa del micro, R31/R32 (33 Ω en SCK y WS), longitud del cable (≤ 15 cm) |
| Altavoz | Tono de 1 kHz a −12 dBFS con el altavoz del Furby (4 Ω) en J8 «SP+»/«SP-» | Sin distorsión audible; AMP_SD (P05) a 1 | AMP_SD, GAIN, TP9 (I2S DOUT) |
| Potencia máxima | Tono a −6 dBFS (límite del firmware) con la batería a 3,7 V; medir la corriente de VSYS | ≤ 0,45 A de pico, sin reinicios ni distorsión fea | GAIN_SLOT (6 dB) y el limitador |
| Rizado de VDD | Tono de 1 kHz a −6 dBFS; osciloscopio en el pad de VSYS de C41 (al oeste de C26) con masa de muelle en su pad de GND, 20 MHz de ancho de banda | ≤ 200 mV pp (simulado: 70 mV pp, `sim/RESULTADOS.md`) | C41 sin montar o mal soldado; puente de VSYS de B.Cu (2 + 2 vías) |
| Full duplex | Reproducir y grabar a la vez | El micro graba mientras suena, sin cortes | Configuración de I2S0 |
| Motor y audio | Motor en marcha mientras se graba | Sin zumbido del PWM (20 kHz, fuera de banda) | Masa del elevador y del puente H, C18–C22 |

## 14. Cámara

| Prueba | PASS | Si falla |
|--------|------|----------|
| Encender la cámara (CAM_EN, P16 = 1; CAM_PWDN, P15 = 0) y escanear el I2C | Responden la cámara (0x30 el OV2640; 0x3C el OV3660/OV5640) y U10 (0x20) | Pinout del FPC J6 (lado del contacto), TP10, TP11, CAM_RST (R35/C31) |
| Foto JPEG SVGA con el preset ESP32-S3-EYE | Imagen correcta | XCLK (bajar a 10 MHz) y PCLK |
| Flancos de los relojes con la cámara en marcha: sonda ×10 con masa de muelle en el pad de R59 del lado de J6 (XCLK, 20 MHz) y en el pad de R60 del lado del módulo (PCLK), ancho de banda ≥ 200 MHz | Flancos limpios, sobreimpulso ≤ 10 % (≤ 0,33 V) y sin escalón a mitad de flanco; XCLK a 20 MHz con ciclo de trabajo 40–60 % | Anillo: subir R59/R60 a 47 Ω; flanco lento o amplitud baja: bajar a 22 Ω (0402 en la misma huella). Sin señal en XCLK: pin 21 del módulo y R59 |
| Con el flex final hasta la cara | 50 fotos seguidas sin error | Acortar el flex, bajar XCLK o la resolución |

## 15. WiFi

| Prueba | PASS | Si falla |
|--------|------|----------|
| RSSI con la placa dentro de la base, la batería montada y el Furby cerrado, frente a un ESP32 de referencia en el mismo sitio | Diferencia ≤ 6 dB | Revisar la zona sin cobre. Si la diferencia pasa de 10 dB: WROOM-1U con antena externa (misma huella) |
| Rendimiento (iperf o subida de audio por TLS) | ≥ 5 Mbit/s a 3 m del router | Ídem |

## 16. Consumo

| Modo | Esperado | PASS | Si falla |
|------|----------|------|----------|
| Dormido (sueño profundo, cámara, elevador, ampli e IR apagados, leva aparcada, JP5 cortado), polímetro en µA en serie con la batería | ≈ 80 µA (60–110) | ≤ 150 µA | Ir quitando consumidores: D4 (JP5), inclinación cerrada (220 kΩ), LDR, micro, U10, módulo |
| Despertar | Dormido, tocar barriga, espalda y lengua, inclinar, enchufar el USB y esperar al temporizador | Despierta en cada caso (INT de U10 en GPIO6 y temporizador) y vuelve a dormirse tras N s | Leer y borrar la INT de U10 antes de dormir; configuración de ext0 |
| Escuchando la palabra de activación | 85–120 mA | ≤ 130 mA | Frecuencia de CPU, modem sleep |
| Pico (motor bloqueado + TX + cámara + audio limitado a −6 dBFS) | ≈ 2,6 A a 3,7 V; ≈ 2,9 A a 3,3 V | Sin reinicio y sin corte del PCM | Bajar ITRIP o no solapar el motor con la foto |

## 17. Temperatura

| Prueba | PASS |
|--------|------|
| 30 min cargando a 0,49 A con el sistema activo, dentro de la base cerrada | U2 < 85 °C; aire junto a U4 < 55 °C (máximo +65 °C para la variante R8) |
| 10 min de conversación con el motor invirtiendo cada 1 s | U6 y U5 < 80 °C; batería < 45 °C |
| 10 min con WiFi transmitiendo y la cámara encendida | U3 (bajo la batería) < 70 °C; batería < 45 °C |

Si se pasa: bajar ICHG (R4 de 2,2 kΩ → 0,40 A), añadir vías térmicas o separar más el cargador del módulo en la v1.1.

## 18. Reglas del firmware (medidas)

Comprueban que el firmware respeta los límites que la v1.0 no cubre sola (`NOTAS.md`, «Reglas para el firmware»; `sim/RESULTADOS.md`). Se hacen con el firmware final, no con el de prueba.

| Regla | Procedimiento | PASS | Si falla |
|-------|---------------|------|----------|
| Celda de ≤ 100 mΩ (con su PCM) | Antes de soldarla a J2/J3: carga electrónica de 0,1 A a 1,1 A en escalón; medir la caída en sus cables | (V a 0,1 A − V a 1,1 A) / 1,0 A ≤ 0,10 Ω | Cambiar de celda: con 0,2–0,4 Ω el pico de 10,2 W hunde VSYS bajo el UVLO del elevador |
| USB enchufado: motor ≤ 50 % y audio ≤ −12 dBFS | USB en USB500 (puerto de ordenador), motor bloqueado + TX + audio a la vez durante 1 s; osciloscopio en TP4 (VBAT) y TP5 (VSYS), resta de canales | VBAT − VSYS < 150 mV y sin reinicio | El firmware no limita: VO(SC2) del BQ24073 apaga OUT 60 ms |
| Pausa al enchufar | Motor en marcha y audio sonando; enchufar el USB 10 veces | VSYS (TP5) llega a 4,40 V en < 20 ms tras PGOOD y D1 enciende (carga); sin reinicios | Falta la pausa de ≈ 5 ms: VSYS se queda en ≈ 3,3 V (supplement) y U2 se calienta |
| ILIM solo con fuente declarada | Cargador de 5 V / 2 A y medidor USB-C; activar ILIM desde el firmware | Corriente de entrada ≤ 1,4 A; F1 no se calienta (< 60 °C); tras 10 min, la cara inferior del lóbulo del USB (pista de VBUS_IN por B.Cu, 0,5 mm) ≤ 15 °C por encima del ambiente (cámara térmica) | Volver a USB500: el PTC es de 1,5 A |
| VBAT ≥ 3,7 V para motor y audio a la vez | Fuente en J2/J3 a 3,6 V (límite 3 A) en vez de la batería; motor bloqueado + audio | El firmware baja el PWM a ≤ 60 % y el audio a −12 dBFS; VSYS (TP5) > 2,7 V y V6 (TP7) sin cortes | El elevador entra en UVLO: motor a tirones y audio cortado |
| Bloqueo del motor ≤ 150 ms | Frenar el eje con la mano; osciloscopio en TP8 (IPROPI) | El firmware corta el motor ≤ 150 ms después de que TP8 llegue a ≈ 2,25 V | Tj del DRV8231A hasta 103 °C con el bloqueo continuo |
| Portadora IR ≤ 50 ms | Emitir una trama larga; osciloscopio en J7.2 («IR-») | Ninguna ráfaga continua > 50 ms | R54 trabaja por encima de su potencia |
| ADC de VBAT_SNS y LIGHT ≤ 1 kHz | Leer VBAT_SNS 100 veces seguidas con el firmware final y comparar con TP4 | Error ≤ 2 % (como §9) | Muestreo continuo: el divisor de 235 kΩ no recarga el condensador del ADC |
