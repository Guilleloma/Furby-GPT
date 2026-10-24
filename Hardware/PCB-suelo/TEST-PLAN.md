# FurbyBoard v1.0: plan de pruebas de hardware (borrador)

Bring-up paso a paso para cuando llegue la placa montada de JLCPCB. Es un **borrador de la fase 1**: los valores salen de `ARQUITECTURA.md`. En la fase 2, con el esquema y el layout, se completan los designadores, la posición de cada TP y las resistencias que falten.

**Reglas:**

- Se hace en orden, y no se pasa de un paso con un FAIL sin entenderlo.
- Se anota el valor medido junto al esperado, en una copia de esta tabla por placa. La placa se numera a rotulador en el recuadro en blanco de la serigrafía de la cara inferior.
- La batería no se conecta hasta el paso 8.

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
| Altavoz de 8 Ω de referencia, motor del Furby o motor DC de prueba | Audio y motor |
| Módulo de cámara OV2640 (o el elegido) y su flex | Cámara |
| Otro ESP32 de referencia | Comparar el RSSI del WiFi |
| Batería LiPo 1S de 1400 mAh con PCM | Pasos 8 a 17 |

## 1. Inspección visual (sin alimentar)

| Comprobar | PASS | Si falla |
|-----------|------|----------|
| Orientación de U1 (WROOM-1), de los QFN (BQ24073, MAX98357A), TSSOP (TCA9535), SOT y LED | Pin 1 coincide con la serigrafía | Reclamar a JLCPCB o resoldar. Revisar las rotaciones del CPL para el siguiente pedido |
| Puentes de estaño en los QFN, TSSOP, conector USB-C y FPC | Ninguno (lupa ×10) | Retirar con malla y flux |
| Conector USB-C asentado en la ranura, con las patas soldadas | Sin holgura | Resoldar las patas de la carcasa |
| Polaridad del JST frente a la batería | El + de la serigrafía coincide con el rojo del cable de la batería (polímetro en el conector de la batería) | **No conectar.** Cambiar los pines del conector de la batería |
| Jumpers JP1–JP4 y JP_LED | Cerrados de fábrica | Cerrarlos con estaño |
| Zona de la antena | Sin cobre ni componentes (x −85 a −61, delante) | Defecto de diseño: anotarlo |

## 2. Cortos y continuidad (sin alimentar)

Polímetro en ohmios, punta negra en GND (TP GND).

| Carril | Esperado | PASS | Si falla |
|--------|----------|------|----------|
| VBUS–GND | > 10 kΩ | No es un corto (< 10 Ω) | Revisar el PTC, el USBLC6 y la entrada del BQ24073 |
| VBAT–GND | ≈ 200 kΩ (divisor 100k + 100k) en paralelo con el BQ | > 50 kΩ | Revisar el divisor, el BQ y el JST |
| VSYS–GND | > 1 kΩ | > 100 Ω | Revisar el TPS63802, el TPS61089 y el MAX98357A |
| 3V3–GND | Del orden de kΩ (módulo sin alimentar) | > 100 Ω | Levantar el TPS63802 y medir otra vez para aislar |
| 6V–GND | > 10 kΩ | > 1 kΩ | Revisar el DRV8231A y los condensadores |
| 2V8 y 1V2–GND | > 10 kΩ | > 1 kΩ | Revisar los LDO de la cámara |
| VBUS–VSYS, VSYS–3V3, 3V3–6V | Sin continuidad directa | > 100 Ω | Puente entre carriles: buscarlo con la lupa |
| D+ y D− del conector a los pads 19/20 del módulo | < 1 Ω | Continuidad | Revisar soldaduras |

## 3. Primer arranque por la entrada de batería (fuente limitada)

Fuente de laboratorio en el JST (o en el TP VBAT y GND): **3,70 V, límite de 150 mA**. Sin USB, sin cámara, sin motor ni altavoz.

| Medida | Esperado | PASS / FAIL | Si falla |
|--------|----------|-------------|----------|
| Corriente al encender | Pico < 150 mA y luego 30–60 mA (el módulo arranca en blanco o con la prueba de fábrica) | PASS: < 100 mA estable. FAIL: la fuente limita | Apagar. Medir VSYS y 3V3 con la fuente limitada a 50 mA y buscar el carril que cae |
| VSYS | 3,65 V ± 0,05 (VBAT − ≈ 50 mV) | ± 0,1 | BQ24073 sin soldar o en cortocircuito |
| 3V3 | 3,30 V ± 0,10 | ± 0,10 | TPS63802: comprobar el divisor de realimentación y la bobina |
| LED PWR | Encendido | | Polaridad del LED o JP_LED abierto |
| LED PROG | Parpadea al arrancar y al pulsar RESET | | Revisar el LED y GPIO43 |
| U0TX (J_EXP 9) a 115 200 baudios | Log del ROM: `ESP-ROM:esp32s3…` | | Revisar EN (TP EN a 3,3 V) y el condensador de EN |

Luego, la fuente a **3,0 V**: 3V3 tiene que seguir en 3,30 ± 0,10 (buck-boost elevando). A **4,2 V**: igual.

## 4. Primer arranque por USB

Medidor USB-C en línea, con un cargador de 5 V. Se quita la fuente del paso 3: sin batería.

| Medida | Esperado | Si falla |
|--------|----------|----------|
| Corriente de entrada | < 150 mA | Desenchufar y volver al paso 2 |
| VBUS | 5,0 V ± 0,25 | Cable, PTC, CC (5,1 kΩ) |
| VSYS | 4,40 V ± 0,10 (OUT regulado del BQ24073) | BQ24073: ILIM, EN1 y EN2 (sin firmware: USB500) |
| LED PG | Encendido | PGOOD o LED |
| LED CHG | Apagado o parpadeando (sin batería, el BQ detecta que falta) | Normal sin batería |

## 5. Enumeración USB y primer flasheo

| Paso | PASS | Si falla |
|------|------|----------|
| `lsusb` (macOS: `system_profiler SPUSBDataType`) | Aparece «USB JTAG/serial debug unit» (VID 303A) | Revisar D+ y D− (¿cruzados?), el USBLC6 y el cable de datos. Probar con BOOT pulsado al enchufar |
| `esptool.py chip_id` y `flash_id` | ESP32-S3, 16 MB de flash; PSRAM de 8 MB detectada en el log de arranque | Para entrar en descarga a mano: mantener BOOT, pulsar y soltar RESET, soltar BOOT |
| Flashear el firmware de prueba (`furbyboard-test`) | Se graba y arranca | Ver el log por U0TX (J_EXP 9) |
| LED RUN | Parpadea a 1 Hz (latido del firmware de prueba) | I2C al TCA9535 (escaneo: 0x20) |

## 6. LED

| LED | Prueba | PASS |
|-----|--------|------|
| PWR | 3V3 presente | Encendido; se apaga al cortar JP_LED (no cortarlo hasta acabar las pruebas) |
| PROG | Reset y entrada en modo descarga | Parpadea en cada reset y al entrar en descarga |
| RUN | Firmware de prueba | Parpadea; apagado durante el flasheo |
| CHG | Con batería descargada y USB | Encendido mientras carga |
| PG | Con USB | Encendido |

## 7. Medida de cada carril (con el firmware de prueba)

| TP | Condición | Esperado | Tolerancia | Rizado (osciloscopio, 20 MHz de banda) |
|----|-----------|----------|------------|----------------------------------------|
| VBUS | USB | 5,00 V | ± 0,25 | — |
| VSYS | USB / sin USB | 4,40 V / VBAT − 0,05 | ± 0,10 | < 100 mVpp |
| 3V3 | WiFi transmitiendo | 3,30 V | ± 0,10; caídas < 150 mV en los picos de TX | < 50 mVpp |
| 6V | EN_6V = 1, sin carga | 5,94 V | ± 0,15 | < 100 mVpp |
| 2V8 | Cámara encendida (P1.5 = 1) | 2,80 V | ± 0,06 | < 30 mVpp |
| 1V2 o 1V5 | Cámara encendida | 1,20 o 1,50 V | ± 0,05 | < 30 mVpp |
| EN | En marcha | 3,3 V | ± 0,1 | — |

## 8. Batería, carga y power path

Con la batería real, tras comprobar la polaridad del JST (paso 1).

| Prueba | Procedimiento | PASS | Si falla |
|--------|---------------|------|----------|
| Corriente de carga | Batería a ≈ 3,6 V, USB, firmware en reposo. Polímetro en serie con la batería | 0,44–0,54 A en corriente constante (RISET 1,8 kΩ) | RISET y la temperatura del BQ (por encima de 125 °C regula a la baja) |
| Fin de carga | Dejar cargar | CHG se apaga con VBAT = 4,20 V ± 0,02 y < 50 mA (10 % de ICHG) | Temporizador (TMR) o TS (10 kΩ a GND) |
| Conmutación sin reinicio | Firmware que imprime el tiempo desde el arranque y el motivo de reset. Enchufar y desenchufar el USB 20 veces, con WiFi activo | El tiempo no se reinicia; ningún reset por brown-out | Condensadores de VSYS y 3V3. Medir VSYS en el osciloscopio durante el cambio (caída < 300 mV) |
| Modo suplemento | USB de 500 mA (puerto de ordenador) y motor en marcha | El sistema no se reinicia y la batería aporta la diferencia | Si salta «VO(SC2)»: subir a ILIM (EN1 = 0, EN2 = 1) con un cargador bueno, o bajar ITRIP |
| USB500 al arrancar | Sin firmware (BOOT pulsado) | Corriente de entrada ≤ 0,5 A | EN1 y EN2 (pull-up de 100 kΩ en EN1 y pull-down en EN2) |

## 9. Medida de la batería por ADC

| Procedimiento | PASS | Si falla |
|---------------|------|----------|
| Fuente en el JST a 3,40, 3,80 y 4,20 V. Comparar la lectura del ADC (GPIO1, divisor × 2, calibración de eFuse) con el polímetro | Error ≤ 2 % (≤ 80 mV) | Valor de las resistencias del divisor, el condensador de 100 nF o la atenuación del ADC (12 dB) |

## 10. Elevador de 6 V

| Prueba | PASS | Si falla |
|--------|------|----------|
| En vacío (EN_6V = 1) | 5,94 V ± 0,15 | Divisor de realimentación (390k/100k) |
| Con 10 Ω (≈ 0,6 A) | ≥ 5,80 V, rizado < 150 mVpp | Bobina, condensadores de salida, RFREQ |
| Con 4,7 Ω (≈ 1,26 A), 10 s | ≥ 5,70 V; TPS61089 < 80 °C; corriente de la batería ≈ 2,3 A a 3,7 V | ILIM (RILIM 270 kΩ) o protección de la batería |
| Con EN_6V = 0 | ≈ VSYS − 0,4 V (diodo del FET alto); el DRV en reposo | Normal en este elevador |

## 11. Motor

Con el motor del Furby y el mecanismo montado, o con un motor de prueba de la misma clase.

| Prueba | Procedimiento | PASS | Si falla |
|--------|---------------|------|----------|
| Arranque seguro | Encender sin firmware (BOOT pulsado) | El motor no se mueve | Pull-downs de IN1 e IN2 (GPIO48 y GPIO46) |
| Dos sentidos | PWM a 20 kHz, 70 %, decaimiento lento, en cada sentido | Gira en los dos; OUT1 y OUT2 conmutan a 20 kHz | Pines, JP1 y JP2 |
| Corriente en marcha | IPROPI (TP) / 2,25 V por A | Anotar el valor (se esperan 0,1–0,3 A) | — |
| Bloqueo | Frenar el eje con cuidado 200 ms (o con el motor de prueba) | IPROPI ≈ 2,7 V (≈ 1,2 A, regulado); el ESP no se reinicia y el PCM no corta | Bajar ITRIP (divisor de VREF) |
| Inversiones | Bucle de 5 min alternando cada 0,4 s, con freno de 20–30 ms y rampa | Sin reinicios; DRV8231A < 80 °C | Alargar el freno o la rampa, o bajar ITRIP |
| Posición | Ir al final de carrera (GPIO47) y contar pulsos del encoder (GPIO14) en un ciclo completo | Mismo número de pulsos (± 1) en 10 ciclos | Schmitt, pull-up del fototransistor (10 kΩ, ajustable de 4,7 a 47 kΩ), LED del encoder (P1.2) |

## 12. Sensores del Furby

| Sensor | Procedimiento | PASS |
|--------|---------------|------|
| Barriga, espalda, lengua, inclinación A y B | Puentear cada pad a GND con unas pinzas y leer el TCA9535 | Cambia el bit correcto y salta la INT en GPIO21. Despierta del sueño profundo |
| Leva | Puentear el pad | GPIO47 a 0 |
| Encoder | Girar el mecanismo a mano con el elevador encendido | Pulsos limpios en GPIO14 (osciloscopio: flancos < 1 µs tras el Schmitt) |
| Luz | Tapar el sensor e iluminarlo con una linterna | La lectura del ADC (GPIO2) cambia más de 1 V |
| IR | Mando de TV hacia el receptor (GPIO42) y emisión por RMT (GPIO45) hacia un receptor conocido | Se decodifican tramas en los dos sentidos |

Si falla, se revisa por este orden: la soldadura del cable, el pull-up de 47 kΩ, la serie de 1 kΩ, el condensador y la dirección del TCA9535.

## 13. Audio

| Prueba | Procedimiento | PASS | Si falla |
|--------|---------------|------|----------|
| Micro | Grabar 10 s a 16 kHz (I2S DIN, GPIO41) y escuchar el fichero | Voz clara; ruido de fondo < −60 dBFS en silencio | L/R del micro, BCLK y WS (TP), longitud del cable (≤ 15 cm) |
| Altavoz | Tono de 1 kHz a −12 dBFS con el altavoz de 8 Ω de referencia | Sin distorsión audible; SD_MODE (P1.3) a 1 | SD_MODE, GAIN, I2S DOUT (TP) |
| Full duplex | Reproducir y grabar a la vez | El micro graba mientras suena, sin cortes | Configuración de I2S0 |
| Motor y audio | Motor en marcha mientras se graba | Sin zumbido del PWM (20 kHz, fuera de banda) | Masa del elevador y del puente H, condensadores de 6V |

## 14. Cámara

| Prueba | PASS | Si falla |
|--------|------|----------|
| Encender la cámara (P1.5 = 1, PWDN = 0) y escanear el I2C | Responden la cámara (0x30 el OV2640; 0x3C el OV3660/OV5640) y el TCA9535 (0x20) | Pinout del FPC (lado del contacto), 2V8, 1V2/1V5, RESET |
| Foto JPEG SVGA con el preset ESP32-S3-EYE | Imagen correcta | XCLK (bajar a 10 MHz) y PCLK |
| Con el flex final hasta la cara | 50 fotos seguidas sin error | Acortar el flex, bajar XCLK o la resolución |

## 15. WiFi

| Prueba | PASS | Si falla |
|--------|------|----------|
| RSSI con la placa dentro de la base, la batería en la bandeja y el Furby cerrado, frente a un ESP32 de referencia en el mismo sitio | Diferencia ≤ 6 dB | Revisar la zona sin cobre. Si la diferencia pasa de 10 dB: WROOM-1U con antena externa (misma huella) |
| Rendimiento (iperf o subida de audio por TLS) | ≥ 5 Mbit/s a 3 m del router | Ídem |

## 16. Consumo

| Modo | Esperado | PASS | Si falla |
|------|----------|------|----------|
| Dormido (sueño profundo, cámara y elevador apagados, JP_LED cortado), polímetro en µA en serie con la batería | ≈ 90 µA | ≤ 150 µA | Ir quitando consumidores: LED, divisor, micro, expansor |
| Escuchando la palabra de activación | 85–120 mA | ≤ 130 mA | Frecuencia de CPU, modem sleep |
| Pico (motor bloqueado + TX + cámara + audio) | ≈ 2,9 A a 3,7 V | Sin reinicio y sin corte del PCM | Bajar ITRIP o no solapar el motor con la foto |

## 17. Temperatura

| Prueba | PASS |
|--------|------|
| 30 min cargando a 0,49 A con el sistema activo, dentro de la base cerrada | BQ24073 < 85 °C; aire junto al WROOM-1 < 55 °C (máximo +65 °C para la variante R8) |
| 10 min de conversación con el motor invirtiendo cada 1 s | DRV8231A y TPS61089 < 80 °C; batería < 45 °C |

Si se pasa: bajar ICHG (RISET de 2,2 kΩ → 0,40 A), añadir vías térmicas o separar más el cargador del módulo en la v1.1.
