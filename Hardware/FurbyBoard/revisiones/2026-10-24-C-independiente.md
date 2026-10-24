# Revisión C colocación (independiente) — FurbyBoard v1.0

- Fecha: 2026-10-24 · Commit: `5479572` (colocación, puerta C del autor) sobre `1f90f98` · Revisor: electronics-engineer, revisor independiente (modelo T0, Fable 5.1), sin participación en el diseño
- Tipo de placa: L · Capas: 4 · Fabricante: JLCPCB (JLC04161H-7628)
- Material revisado: `FurbyBoard.kicad_pcb`, `FurbyBoard.kicad_sch`, `.kicad_dru`, `.kicad_pro`, `pcb-toolkit.toml`, `NOTAS.md`, `scripts/layout.py`, `scripts/comprobar_colocacion.py`, `scripts/serigrafia.py`, `../PCB-suelo/geometria.json` e `interfaz-base.md`, informes A/B/C del autor; herramientas vueltas a ejecutar sobre el commit (tabla); 15 PNG de `pcb-toolkit png-revision --ratsnest` y `comprobar-flujo --png` leídos (fuera del repo). Coordenadas en el sistema del STL (`layout.py`): x_kicad = x + 220, y_kicad = −40 − y.

## Resultado
**NO PASA** — 0 críticos, **9 importantes**, 6 mejoras abiertos.

El autor informó de puerta C «PASA» con 0 importantes. Las herramientas confirman lo automático (DRC 0/0, paridad 0, `comprobar-flujo` PASS), pero la revisión encuentra importantes que el autor dio por buenos o no midió: dos TP a más de 5 mm de su fuente (`revisar-rutado` ya falla hoy), un componente que asoma del contorno, el buck-boost y el elevador fuera de su layout de referencia, el único hueco previsto para la NTC pegado al cargador, y el logo quitando sitio a los rótulos de J_EXP y a las vías del buck-boost. Todos se corrigen moviendo piezas pequeñas o la serigrafía; la planta (bloques, pasillos, pines) es correcta y se conserva.

## Herramientas
| Herramienta | Comando | Resultado |
|-------------|---------|-----------|
| Comprobación de herramientas (§1.1) | `kicad-cli version`, `pcb-toolkit --version`, kicad-happy, Freerouting, rsvg-convert, ngspice | kicad-cli 10.0.7, pcb-toolkit 0.1.0 (venv del repo), rsvg-convert y ngspice presentes; **kicad-happy y Freerouting no instalados** |
| ERC | `kicad-cli sch erc --severity-all --exit-code-violations --format json` | **0/0** en las 9 hojas |
| DRC | `kicad-cli pcb drc --schematic-parity --severity-all --format json` (sin `--refill-zones`) | **0 infracciones, 0 de paridad**; 362 elementos sin conectar (sin rutar, esperable) |
| Flujo | `pcb-toolkit comprobar-flujo FurbyBoard.kicad_pcb --png … --json …` | **PASS**: 0 errores, 4 avisos (C10 1,90 · C32 1,08 · C28 1,02 · C29 1,02 mm), 232 conexiones, 9 zonas calientes, demanda máxima de celda 0,58 |
| Geometría | `pcb-toolkit revisar-rutado FurbyBoard.kicad_pcb --json …` (sin pistas, solo TP) | **FAIL: 2 errores `tp-lejos`** (TP9 a 7,9 mm de U7:1; TP6 a 5,9 mm de C8:1; máximo 5,0) → R1 |
| Configuración | `pcb-toolkit.toml` frente a la plantilla del repo | Sin reglas en `off` ni umbrales relajados; margen 1,0 en «puente H» y «clase D» justificado en `NOTAS.md`. **Falta `BQ_TS` en `criticas`** cuando entre la NTC (R4) |
| Colocación propia del autor | `scripts/comprobar_colocacion.py` (Python de KiCad) | OK: 64 piezas bajo la batería, la más alta L1 (2,10 mm) para 4,1 de hueco; calzos libres; nada bajo el flex |
| Mecánica | `pcbnew` en subproceso: caja, taladros, J1 y contorno contra `geometria.json` | H1–H4 en (−97; −68,5), (−50; −68,5), (−86,7; −121,9), (−60,3; −121,9) exactos; J1 en (−73,5; −128,494) = boca del USB; caja (−107,97…−39,03) × (−127,84…−53,16) coincide; keepout de antena x −85…−61, y > −62 en las 4 capas (pistas, vías, relleno y pads) |
| CPL | — | No aplica (puerta C) |
| Análisis | kicad-happy v2.3.2 | **No ejecutado** (no instalado; degradación de `kicad-automatizacion.md` §1.2) |
| PNG | `png-revision --ratsnest --zona L1,L2,J2,J3,Q1` (410 ficheros) y `comprobar-flujo --png` | 15 leídos y comentados abajo |

## Hallazgos
| ID | Severidad | Área | Hallazgo | Evidencia | Verificado / supuesto | Corrección propuesta | Estado |
|----|-----------|------|----------|-----------|-----------------------|----------------------|--------|
| R1 | **Importante** | TP | **TP6 (3V3) a 5,9 mm de C8:1 y TP9 (I2S_DOUT) a 7,9 mm de U7:1 (14,5 de U4:9)**: incumplen «TP a ≤ 5 mm de su fuente» y `revisar-rutado` ya da FAIL, así que la puerta D no pasará con esta colocación. El informe C del autor afirma «14 TP a ≤ 5 mm», que no es cierto | `revisar-rutado` `tp-lejos` #1 y #2; medida pad a pad | Verificado | TP6 a ≤ 5 mm de C7/C8 o del pin 6 de U3 (p. ej. (−84; −111), cara B, fuera del área del logo); TP9 a ≤ 5 mm del pin 1 de U7 (−94,56; −90,35), p. ej. (−93; −93) cara B | Abierto |
| R2 | **Importante** | Buck-boost U3 (TPS63802) | **Cout fuera del lazo:** C7 (22 µF) a 2,45 mm del pin 6 (VOUT) con el pad 2 de L1 (BB_SW2) en medio, y su GND a 4,46 mm del pin 8 (PGND); C8 a 4,4/6,2 mm; Cin C6 a 1,98 mm de VIN y 2,48 de GND. No es el layout de referencia del datasheet (Cin y Cout pegados a VIN/VOUT y PGND); la pista de VOUT tendrá que rodear el pad de la bobina y el retorno del lazo de salida cerrará por vías en el plano | Medida pad a pad (`pads.json`), PNG `ratsnest_zona-U3` | Verificado | C7 girado 90° en la esquina sureste de U3 (≈ (−88,3; −106,3), pad 3V3 a ≤ 1 mm del pin 6) con sus vías de GND al sur; C8 a su lado; C6 bajado a ≤ 1 mm de los pines 1/10 (≈ y −100,6). Exige recortar el área del logo (R6) | Abierto |
| R3 | **Importante** | Elevador U5 (TPS61089) | **Cout C18 en vertical:** pad V6 a 0,70 mm del pin 6 (bien) pero pad GND a 2,60 mm del pin 5, así que el lazo caliente del boost (SW → VOUT → Cout → GND) cierra por vías en el plano, contra `layout-pcb.md` §6 («≤ 1 mm pad a pad, sin vías dentro del lazo»). Cin C16 está «al revés»: su pad GND queda a la altura del pin 9 (VIN) y el de VSYS a 2,06 mm. C18 además a 0,37 mm del borde | Medida pad a pad; PNG `ratsnest_zona-U5` | Verificado | C18 a 0° centrado en (−50,5; −117,3): sus dos pads quedan bajo los pines 5 y 6 a ≈ 0,6 mm (cabe: C15 a 0,6 mm, borde a 1,9 mm); C16 girado 180° (VSYS hacia el pin 9) | Abierto |
| R4 | **Importante** | NTC (decisión de Maestro, crítico B7) | **El único hueco disponible «junto a los pads de batería» es el de R3** (10 kΩ fijos de TS, en (−68,8; −114,6)), y está a **1,5 mm del cuerpo de U2** (0,87 W cargando, Tj ≈ 87 °C a Ta 50 °C) y 0,8 mm fuera de la huella de la batería. Una NTC ahí mide el calentamiento del cargador, no el de la celda: con Ta 25–35 °C el cobre junto a U2 sube a ≈ 45–55 °C (estimación con θJA 42 °C/W) y el comparador TS del BQ24073 suspendería la carga de forma intermitente | `pads.json` (R3:1 a 3,78 mm del pin TS; cuerpo de U2 x −67,16…−62,84); tabla de raíles | Verificado (posiciones); estimado (temperaturas) | NTC 0603 sustituyendo a R3 pero **bajo la batería y lejos de lo que calienta**: zona libre en F.Cu x −86…−78, y −110…−117 (p. ej. (−81; −113): ≥ 14 mm de U2, 8 de F1, fuera del pasillo norte-sur y del logo). BQ_TS a In2 o B.Cu cruzando el pasillo del USB con vía de retorno; añadir `BQ_TS` a `[redes] criticas` (clase D); GND de la NTC a la isla de GND de señal de U2. Liberar la posición de R3 deja sitio al «+» de J2 (R7) | Abierto |
| R5 | **Importante** | Compensación del elevador | **C14 (BST_RC, 4,7 nF) a 8,2 mm del pin COMP**, en la columna de pull-ups del cargador (R9…R7, x −60,4) y en el borde de la zona caliente de L2; el nodo BST_RC (clase D) recorre 5 mm desde R24. R21 (390 kΩ) a 3,8 mm del pin FB y su toma de V6 a 7 mm de C18 (no Kelvin) | Medida pad a pad; PNG `ratsnest_zona-U2` (C14 abajo a la derecha) | Verificado | C14 a (−57; −118,8), bajo R24 (hueco libre; Q1 a 7 mm); R21/R22 pegados al pin FB cuando C18 pase a horizontal (R3) y toma de V6 desde el pad de C18 | Abierto |
| R6 | **Importante** | Logo frente a diseño | **El área de reglas del logo (B.Cu, x −101,5…−87,1, y −117,6…−104, 196 mm², sin vías ni pads) quita sitio al diseño:** (a) linda con J_EXP y deja sin rótulo 6 de sus 10 pads (solo hay `G`, `P07`, `3V3`, `VSYS`; faltan 1 G, 4 5V, 5 IO4 SDA, 6 IO5 SCL, 9 IO43 TX, 10 IO44 RX), contra la preferencia «GPIO libres con su número serigrafiado»; (b) prohíbe las vías de GND del Cout del buck-boost en la esquina sureste de U3 (R2); (c) impide el cosido de GND en rejilla ≤ 10 mm en esa zona | Textos de B.Silkscreen extraídos; PNG `montaje-B_placa` y `ratsnest_zona-J11`; área de reglas 6 | Verificado | Reducir el logo a ≈ 10 × 10 mm y moverlo a donde no estorbe (p. ej. x −100…−90, y −118…−108, dejando 3 mm hasta J_EXP y hasta x −88), o quitar la prohibición de vías y aceptar que el fabricante recorte la serigrafía en ellas. Rótulos de J_EXP con número de GPIO en la cara inferior | Abierto |
| R7 | **Importante** | Serigrafía funcional (preferencias de Guillermo) | (a) **Falta el «+» de J2 en la cara superior**, que es por donde se suelda el cable (el «−» de J3 sí está; en la cara inferior están `BAT+`/`BAT−`). (b) **Ningún TP lleva nombre** en B.Silkscreen: `serigrafia.py` los deja para `router/aplicar.py`, un flujo descartado, así que hoy el `TEST-PLAN.md` no se puede seguir sobre la placa. Las formas de J2 (cuadrado 3 × 3) y J3 (redondo Ø2,6) sí son distintas y están a 6,5 mm | Textos extraídos (F.Silkscreen: solo `-`); `serigrafia.py` `TP_ABAJO`; PNG `montaje-F_placa`, `montaje-B_placa` | Verificado | «+» de ≥ 1 mm sobre J2 (hueco de 1,7 mm hasta R3; más aún cuando R3 se mueva por R4); rótulo de cada TP desde `gen_pcb.py`/`serigrafia.py` en la colocación, sin depender del rutado | Abierto |
| R8 | **Importante** | DFM, borde | **R23 (RILIM del elevador, (−45; −115,6)) asoma del contorno: patio 0,12 mm fuera**, cuerpo a ≈ 0,1 mm del borde fresado (tolerancia del fresado ±0,2 mm). J11 también 0,11 mm fuera (solo patio de pads pasantes de cable, aceptable), C18 a 0,37 mm (se resuelve con R3). El DRC no vigila patios contra el borde | `pcbnew` (`GetBoardPolygonOutlines` frente a `F.CrtYd`) | Verificado | R23 ≥ 0,5 mm dentro: p. ej. (−46; −115,6) o girado a 0° bajo C16 | Abierto |
| R9 | **Importante** | Mecánica (checklist 4.6, punto C «interfaz con piezas reales medida») | **El centro del agujero del mecanismo (Ø11,3 en (−60,88; −95,32)) sigue siendo un supuesto** (`interfaz-base.md` §4) y la colocación lo abraza: 8 piezas a < 1,1 mm de su borde (C27 patio tocando, R33 0,55, JP3 0,60, R30 0,84, R29 0,95, D1 0,96, U8 0,96, JP4 1,02). Si la medida mueve el agujero 1 mm, hay que recolocar el bloque de los LDO y los puentes después de rutar | Distancias calculadas; PNG `ratsnest_placa` | Verificado (distancias); el centro real, sin medir | Medir el mecanismo en el Furby **antes de rutar** (acción de Guillermo, ya pendiente en `interfaz-base.md`); si no se puede, dejar un anillo de 2 mm libre de piezas (como la exclusión Ø15,3 de la base) moviendo C27, R33, JP3, R29, R30, D1, U8 y JP4 | Abierto |
| R10 | Mejora | Antena | La huella de la batería (bolsa de aluminio) queda a 4,9–6,0 mm del área de la antena, 4,1 mm por encima de la placa; Espressif pide ≥ 15 mm sin metal. Decisión de arquitectura con plan B (WROOM-1U) y prueba de RSSI en el bring-up | `layout.py` BATERIA (esquina en (−66,3; −68,0)); `ARQUITECTURA.md` §12 | Verificado | Nada ahora; medir RSSI frente a un ESP32 de referencia (ya en la arquitectura) | Aceptado |
| R11 | Mejora | Flujo de VBUS | F1 (PTC) en (−82,5; −121) al oeste de J1 mientras el cargador está al noreste: VBUS_IN va 9 mm al oeste y VBUS vuelve 17 mm al este (retroceso; ≈ 20 mΩ, inofensivo) | `layout.py`; PNG `ratsnest_placa` | Verificado | Si cabe, F1 entre J1 y U2 (≈ (−70; −121)); si no, aceptar | Abierto |
| R12 | Mejora | Filtros de ADC | C5 (nodo del divisor de VBAT_SNS) a 44 mm del pin 39 y el filtro de LIGHT a ≈ 28 mm del pin 38: para medidas lentas vale, pero `layout-pcb.md` §8 pide el RC junto al pin | Posiciones de R13/R14/C5 y Q3/R53 frente a los pads 38/39 | Verificado | v1.1: RC junto a los pines 38/39 (hay sitio al este del módulo, y −64…−66) | Abierto |
| R13 | Mejora | Rutabilidad del canal | El canal x −86,5…−82,5 (4 mm) tiene que llevar en F.Cu el I2S (4 líneas, ≈ 1,6 mm) y el par USB (≈ 1,7 mm con 3W), con C10/C9 ocupando su lado este entre y −64,5 y −70; I2C/INT y HOME/ENC_IO solo caben si van por In2 como dice `NOTAS.md`. Factible pero sin holgura | Geometría; `comprobar-flujo` (demanda 0,58) | Verificado | Fijar en el rutado: I2S y par USB en F.Cu, el resto por In2 con vía bajo C10/C9; vigilar los cruces de las salidas de los pines 15–17 con el par a la altura de y −83 | Abierto |
| R14 | Mejora | Plano de VSYS en In2 | In2 lleva el relleno de VSYS y además señales lentas bajo el módulo (EN, BOOT, LED_RUN, pines 35–39): cada pista corta el relleno. VSYS tiene que llegar a U7 (−96; −89,6) y a R54 (−92,2; −72,9) por el oeste del módulo, justo donde pasan las vías del canal | `NOTAS.md` «Apilado», «Pasillos» | Verificado (plan); supuesto (resultado) | Al rutar, comprobar la continuidad del relleno de VSYS hacia el frente izquierdo y, si se estrangula, pista de VSYS de 0,6 mm en F.Cu por el borde izquierdo | Abierto |
| R15 | Mejora | Desacoplo | C10 (100 nF del módulo) a 1,81 mm del pin 2 y C32 a 1,05 del pin 24 de U10: dentro del máximo de 2 mm, fuera del ideal de 1 mm. Igual que C1 del autor | `comprobar-flujo` avisos #1–#4 | Verificado | Aceptado (el pad del módulo y J9 no dejan acercarlos más) | Aceptado |

### Comprobado sin hallazgo
- **Mecánica:** taladros, USB-C (boca en y −128,49), contorno con holgura 1,0 (0,47 en las orejetas) y caja coinciden con `geometria.json`; keepouts Ø5 de las cabezas de tornillo en F/B (pistas, vías y relleno) y patio Ø5 en la huella; H3/H4 a 2,56/2,60 mm del borde. Nada en la franja del flex (x −46…−39, y −88…−72).
- **Antena:** área de reglas en las 4 capas (pistas, vías, relleno y pads) x −85…−61, y > −62; los pads 1 y 40 del módulo quedan 0,5 mm fuera; ninguna otra pieza dentro; el extremo del módulo a 2,3 mm del borde delantero. Solo serigrafía (`FurbyBoard v1.0`) dentro, sin cobre.
- **Zonas calientes y buses:** el DVP (12 líneas) va por el pasillo de la cámara (y −74…−81, 7 mm para ≈ 4,8 necesarios) hasta J6 sin tocar ninguna zona caliente; el elevador queda a > 3,5 mm de cualquier bus; la clase D y el puente H solo rozan el I2S que entra en U7 y las salidas del motor. IPROPI/MOT_VREF (R28/C23) al oeste de U6, a 0,67 mm de sus pines, fuera de la zona de L2.
- **Desacoplo ≤ 1,1 mm pad a pad:** C2/C3/C4 de U2 (0,70–0,87), C22 de U6 (0,98), C26 de U7 (0,67), C12 de U5 (0,62), C27 de U8 (0,73), C28/C29 (1,03). Bobinas a ≤ 1 mm de su pin SW (L1 0,99; L2 0,75).
- **Par USB:** U1 a 1,1 mm (D−) y 3,05 mm (D+) de los pads de J1, pines 13/14 del módulo en la parte baja de la columna izquierda; el plan del cruce en J1 con vías 0,45/0,2 solo en la clase USB está en el `.kicad_dru` y es coherente.
- **Pads de batería:** BAT+ cuadrado 3 × 3 con taladro 1,2 y BAT− redondo Ø2,6 con taladro 1,0, a 6,5 mm; Q1 (polaridad) entre ambos y el cargador; cables saliendo por la esquina trasera derecha de la batería como pide la arquitectura.
- **Accesibles con la batería puesta:** LED PWR/RUN/TX, RST, BOOT, JP5 delante a la derecha; D1/D2 (CHG/PG) fuera de la batería; JP1–JP4 en el pasillo sur con su GPIO rotulado en las dos caras.
- **Térmica:** U2 (0,87 W), U5 (0,6 W) y U6 (0,6 W) fuera de la batería y con pad expuesto; bajo la batería solo U3 (0,2 W) y los LDO.
- **Montaje:** 139 huellas en F.Cu; en B.Cu solo los 14 TP y el logo (Economic a una cara).
- **Pin 1:** cuadrado en J2, J5, J7, J8, J9, J11 y en el mismo sentido (arriba o arriba-derecha).

## PNG leídos
- `colocacion.png` (`comprobar-flujo`): bloques como en «Planta»; DVP (cian) del lado derecho del módulo a J6 sin cruzar zonas calientes; par USB (verde) recto por el pasillo norte-sur; I2S (magenta) de la columna izquierda a U7 y J5; sensado (amarillo) de los pines 38/39 cruzando el módulo (irán por In2); congestión moderada en el canal y en la fila inferior del módulo. Pasa.
- `montaje-F_placa`: rótulos PWR/RUN/TX, RST/BOOT, LED, IO9/IO46/IO3/IO8 legibles; **sin «+» en J2** (R7); sin rótulos de TP (están abajo, pero tampoco: R7).
- `montaje-B_placa`: logo entero bajo la zona trasera izquierda, **pegado a J_EXP** y dejándolo sin 6 rótulos (R6); `BAT+`/`BAT−`, J7, J8, J9 rotulados; TP sin nombre (R7); nombre, versión, fecha y recuadro «PLACA».
- `ratsnest_zona-U5`: SW de U5 pegado al pad de L2; **C18 vertical bajo los pines 5/6** con el GND lejos (R3); C16 con el GND arriba (R3); C18 a 0,4 mm del borde.
- `ratsnest_zona-U3`: L1 al este con BB_SW1/2 a 1 mm; **C7 abajo a la derecha, con el pad de la bobina en medio** (R2); R16 pegado a FB.
- `ratsnest_zona-U2`: C3 al norte, C2 al oeste, C4 al sur, pull-ups al este; **C14 del elevador en la esquina inferior derecha**, en la columna del cargador (R5).
- `ratsnest_zona-Q1`: J2 cuadrado, Q1 y TP4 (cara B) solapando en planta con R12 (sin problema, caras distintas); J3 redondo abajo a la derecha.
- `ratsnest_zona-U7`: C26 al norte a 0,67 mm; I2S entrando por el noreste; salidas al oeste hacia J8. Pasa.
- `ratsnest_zona-J1`: pads A/B con D+ y D− entrelazados, U1 detrás, nada en la ranura. Pasa.
- `ratsnest_zona-U6`: C22 a 1 mm de VM; zona caliente solo sobre las salidas; IPROPI/VREF al oeste. Pasa.
- `ratsnest_zona-U4`: pads 1–3 fuera del keepout; C10/C9 a la izquierda; fila inferior hacia el pasillo de la cámara; el arco del borde pasa por dentro del área de antena de la huella (solo dibujo). Pasa.
- `ratsnest_zona-J6`: los 16 pines centrales reciben el DVP desde el oeste en orden. Pasa.
- `ratsnest_zona-J9`: pin 1 cuadrado arriba a la derecha; encoder en la columna exterior; la zona del puente H solo toca los pads 11/12 del motor. Pasa.
- `ratsnest_zona-U10`: I2C/INT por el este; TP9 bajo los pads del oeste (cara B) **a 7,9 mm de U7** (R1).
- `ratsnest_zona-J11`: **el patio del logo arranca en la columna derecha de J_EXP** (R6); patio 0,11 mm fuera del borde (R8, aceptable).

## Checklist de la puerta (4.6)
| Sev. | Punto | Estado |
|------|-------|--------|
| C | Contorno, taladros y conectores coherentes con la carcasa; holgura ≥ 1 mm; la placa la fijan los tornillos | OK (medido contra `geometria.json`) |
| C | Interfaz con piezas reales medida con calibre y comprobada a escala 1:1 | OK para USB-C, contorno y taladros; **el agujero del mecanismo sigue sin medir → R9** |
| C | Keepout de antena como área de reglas en todas las capas, según el datasheet del módulo | OK (4 capas, pistas/vías/relleno/pads); batería a 4,9 mm: R10 (mejora, decisión de arquitectura) |
| C | `comprobar-flujo` PASS | OK |
| I | Bloques compactos; cada convertidor como su layout de referencia; corredores reservados | **R2 (buck-boost), R3 y R5 (elevador)**; U2, U6 y U7 OK; corredores OK (R13 ajustado) |
| I | TP junto a su fuente; LED, botones, puentes y conectores accesibles | **R1 (TP6, TP9)**; accesibilidad OK |
| I | Alturas dentro de la carcasa, por zonas | OK (`comprobar_colocacion.py` ejecutado: 2,10 mm máx. bajo 4,1) |
| I | Taladros con diámetro, keepout de cabeza y distancia al borde; fiduciales | OK (Ø2,3, keepout Ø5 en F/B, ≥ 2,56 al borde; sin fiduciales, Economic) |
| — | Preferencias de Guillermo comprobadas desde la colocación (pads de batería, TP, GPIO rotulados, logo subordinado, montaje a una cara) | Pads y montaje OK; **R6, R7** |
| — | Sitio para la NTC (decisión de Maestro) | **R4**: hay sitio, pero no el que estaba previsto |
| — | DFM: patios dentro del contorno | **R8** |

## Revisión final como revisor senior
- **Bus rápido por un convertidor (FurbyBoard, encargo 1):** no se repite; el DVP va por su pasillo y el par USB a ≥ 3,5 mm de L1. Comprobado en el PNG y con `comprobar-flujo`.
- **TP lejos de su fuente (FurbyBoard, encargo 1):** **se repite en TP6 y TP9** (R1), pese a que el informe del autor dice lo contrario. Lección: la afirmación «TP a ≤ 5 mm» se verifica con `revisar-rutado` también en la puerta C (funciona sin pistas), no solo en la D.
- **«DRC 0» tomado como calidad:** el DRC no mira patios contra el borde (R8) ni la distancia de un condensador a su lazo (R2, R3): hay que medirlo.
- **Piezas giradas y origen del CPL (Game Boy):** no aplica todavía (E2); el origen auxiliar está en el origen del STL (220; −40), igual que en el encargo anterior.
- **Serigrafía por debajo del mínimo o sin sitio (Game Boy):** los rótulos que faltan (R6, R7) se deciden ahora, antes de que el cobre los deje sin hueco.

## Siguiente paso
Vuelta al encargo 2 (colocación) con R1–R9; la planta no cambia. Tras corregir, repetir `comprobar-flujo`, `revisar-rutado` (TP) y `comprobar_colocacion.py`, y añadir `BQ_TS` a `pcb-toolkit.toml`. R9 necesita la medida del mecanismo (Guillermo) o el anillo libre de 2 mm.

---

# Vuelta 1 — re-revisión independiente de la colocación

- Fecha: 2026-10-24 · Commits revisados: `6720812` (NTC RT1), `2e3259a` (logo y rótulos), `96d64e1` (colocación vuelta 1) sobre `3575c85` · Revisor: el mismo revisor independiente (T0, Fable 5.1)
- Material: diff de `scripts/layout.py`, `design.py`, `gen_pcb.py`, `serigrafia.py`, `pcb-toolkit.toml`, `NOTAS.md`; sección «Vuelta 1» del informe del autor; herramientas vueltas a ejecutar; placa extraída con pcbnew (pads, patios, áreas de reglas); 11 PNG nuevos leídos; datasheet SLUS810N del BQ2407x (descargado de TI) para el pin TS.

## Resultado de la vuelta 1
**NO PASA** — 0 críticos, **1 importante** (regresión nueva, R16), 5 mejoras abiertas. R1–R9 de la vuelta 0 quedan **resueltos** (R8 y R5 con resto en mejoras). La corrección de R16 es un intercambio de dos piezas en una columna; no toca la planta.

## Herramientas (vuelta 1)
| Herramienta | Comando | Resultado |
|-------------|---------|-----------|
| ERC | `kicad-cli sch erc --severity-all --format json` | **0** infracciones (9 hojas; RT1 integrada) |
| DRC | `kicad-cli pcb drc --schematic-parity --severity-all` (sin `--refill-zones`) | **0** infracciones, **0** de paridad, 362 sin conectar (sin rutar) |
| Flujo | `pcb-toolkit comprobar-flujo --png --json` | **PASS**: 0 errores, 2 avisos (C10 1,90 mm; C32 1,08 mm); los de C28/C29 han desaparecido (ahora 0,62/0,68); demanda máxima de celda 0,64; 232 conexiones |
| Geometría | `pcb-toolkit revisar-rutado --json` | **PASS**, 0 errores: los 14 TP a ≤ 5 mm (R1 resuelto) |
| Colocación propia del autor | `scripts/comprobar_colocacion.py` | OK (64 piezas bajo la batería, máx. 2,10 mm; calzos libres; nada bajo el flex) |
| Mecánica | pcbnew: caja, H1–H4, J1 | Sin cambios: coinciden con `geometria.json` |
| Patios contra el contorno | pcbnew (`GetBoardPolygonOutlines` frente a `F.CrtYd`) | Ningún patio de componente fuera; los más cerca: R50 0,13 mm, C14 0,14, R23 0,24 (R20); J11 0,11 fuera (pads de cable, aceptable) |
| kicad-happy | — | No ejecutado (no instalado) |
| PNG | `png-revision --ratsnest --zona L1,L2,J2,J3,Q1,RT1,TP6,TP9,R23,C14` (450) y `comprobar-flujo --png` | 11 leídos: `colocacion`, `montaje-F_placa`, `montaje-B_placa`, zonas U3, U5, U8, RT1, C14 (más U2, J1, J11 de paso) |

## Estado de los hallazgos de la vuelta 0
| ID | Resolución del autor | Comprobación independiente | Estado |
|----|----------------------|----------------------------|--------|
| R1 | TP6 a (−84,5; −110), TP9 a (−91,5; −92) | `revisar-rutado` 0 `tp-lejos`; TP6 fuera del área del logo (x > −90); TP9 a 1,5 mm de U7:1 | **Resuelto** |
| R2 | C6/C7 pegados a VIN/VOUT, L1 al este | C6–VIN 0,98 mm, C7–VOUT 1,00 mm, L1–SW 1,58 mm (≤ 2). El GND de C6 (3,35) y de C7 (3,90) cierra por el plano: en el DLA el PGND (pin 8) queda entre los pines L1/L2 y no admite un pad de condensador al lado, así que el retorno por vías es el de la figura de layout del datasheet. **Condición para el rutado:** ≥ 2 vías de GND de 0,3 mm pegadas a los pads de GND de C6 y C7 y al pin 8 | **Resuelto** (condición al rutar) |
| R3 | C18 a 0° bajo los pines 5/6; C16 girado | C18: V6 0,79 mm, GND 0,92 mm (lazo VOUT–Cout–GND en F.Cu, sin vías); C16: VSYS 0,72 mm; L2–SW 0,95 mm; C13 BOOT 1,24 mm (antes 1,61) | **Resuelto** |
| R4 | RT1 (NCP18XH103F03RB, C13564) de TS a VSS en (−80,5; −113,5) | RT1 a 15,8 mm de U2, 7,8 de F1, 11,8 de L1, 30 de U5/U6; 3,6 mm dentro de la huella de la batería; a 10 mm de los calzos E1/E3; fuera del pasillo norte-sur (x −77…−69) y del logo; `BQ_TS` en `criticas`. Conexión eléctrica contra el datasheet: ver «TS con NTC» abajo | **Resuelto** |
| R5 | C14 y R21 a la columna oeste de U5 | R21–FB 0,62 mm, R22–FB 0,90, C15–COMP 1,06 ✓. **Pero** R24 (30 kΩ) sigue a 3,99 mm de COMP y C14 a 3,97 mm de R24 (nodo BST_RC de 4 mm); y C12 ha salido de su sitio (R16) | Resuelto en lo esencial; resto en R17 |
| R6 | Logo a 10 × 10 mm en x −100…−90, y −118…−108 | Área de reglas B.Cu comprobada; los 10 pads de J_EXP con su GPIO (`G, 3V3, VSYS, 5V, IO4 SDA, IO5 SCL, P07, G, IO43 TX, IO44 RX`); las vías de GND de C7/C8 caen en x > −90 (fuera); logo a 2 mm de J11 y a 3,7 mm de U3 | **Resuelto** |
| R7 | «+» arriba; nombres de TP | F.Silkscreen: `+` en (−68,9; −116,5) y `-` en J3; B.Silkscreen: 14 rótulos de TP (`VBUS, D+, D-, BAT, VSYS, 3V3, 6V, IPR, I2S, 2V8, 1V2, G×3`) | **Resuelto** |
| R8 | R23 a (−45,55; −115,7) | Patio dentro, a 0,24 mm del borde; cobre a ≥ 0,3 (DRC) y mínimo de JLCPCB 0,2 mm a borde fresado | **Resuelto** (margen en R20) |
| R9 | Anillo de 2 mm | Patios más cercanos al borde del agujero: U11 2,04, R26 2,07, R52 2,11, D1 2,16, U8 2,21 mm; en B.Cu solo TP10 (1,77, sin altura). La medida real del agujero sigue pendiente (Guillermo), ahora con 2 mm de tolerancia | **Resuelto** (medida pendiente, ya anotada) |
| R10–R15 | R11 descartada (J1 ocupa el hueco), R12 a v1.1, el resto sin cambios | Coherente | Mejoras, sin cambios |

## TS con NTC directa a VSS, contra el datasheet (SLUS810N, rev. octubre de 2021)
- **Conexión:** tabla 7-1 («TS: External NTC Thermistor Input. Connect the TS input to the NTC thermistor… TS monitors a 10 kΩ NTC thermistor») y §9.3.6: I_NTC se inyecta desde el pin y se compara V_TS con V_COLD y V_HOT; **no hay red de polarización** salvo para *ampliar* la ventana (figura 9-9, Rs/Rp; «the temperature window cannot be tightened… it can only be extended»). La NTC directa de TS a VSS es la conexión nominal. **Verificado.**
- **Umbrales (§8.5, «Battery-pack NTC monitor»):** I_NTC 72/75/78 µA; V_HOT 270/300/330 mV (V_TS bajando), histéresis 30 mV; V_COLD 2,0/2,1/2,2 V (subiendo), histéresis 300 mV; t_DGL(TS) 50 ms; V_DIS(TS) = V_IN − 0,2 V (solo con TD alto; aquí TD va a GND, así que TS está activo). Nota (1): «trip points of 0 °C and 50 °C… with a Vishay Type 2 curve NTC with R25 of 10 kΩ».
- **Ventana con NCP18XH103F03RB (10 kΩ, B25/50 = 3380 K; modelo β):** R_HOT = 0,300 V / 75 µA = 4,00 kΩ → **51 °C** (47–56 °C con los extremos de V_HOT e I_NTC); rearme a 4,40 kΩ → 48 °C (≈ 3 °C de histéresis). R_COLD = 2,1 V / 75 µA = 28,0 kΩ → **0 °C** (−2…+2 °C); rearme a 24 kΩ → 3,6 °C. Con B 3435 (curva tipo 2 de referencia) los puntos se mueven < 0,5 °C. A 25 °C V_TS = 0,75 V; a 45 °C 0,37 V. **Calculado.**
- **Comportamiento fuera de la ventana (§9.3.6):** la carga se suspende, los temporizadores se congelan y CHG sigue bajo; se reanuda sola al volver a la ventana.
- **Valoración:** la ventana 0–50 °C es la fija del chip, 5 °C más ancha por arriba que el 0–45 °C habitual de las celdas, y no se puede estrechar desde fuera; como la NTC mide la PCB bajo la celda (decisión de Maestro, opción a), la protección es gruesa pero real, y queda cubierta por el PCM de la celda y por el `TEST-PLAN.md` (que hay que actualizar con RT1: medir V_TS ≈ 0,75 V a 25 °C y la suspensión al calentar la NTC con el dedo o con aire caliente). Sin hallazgo; R21 (mejora) recoge la nota del TEST-PLAN.
- **Pieza:** NCP18XH103F03RB es 10 kΩ ±1 %, B 3380 ±1 %, 0603: correcta. El autor la marca `extended`; en la puerta E2 se comprueba en la API de JLCPCB si C13564 es básica (en catálogos anteriores lo era), porque cambia el coste de carga.

## Hallazgos nuevos de la vuelta 1
| ID | Severidad | Área | Hallazgo | Evidencia | Verificado / supuesto | Corrección propuesta | Estado |
|----|-----------|------|----------|-----------|-----------------------|----------------------|--------|
| R16 | **Importante** | Elevador U5 (regresión) | **C12 (2,2 µF de VCC del TPS61089) ha pasado de 0,62 mm a 3,86 mm del pin VCC** al mover la columna de FB/COMP: ahora está en la segunda columna (x −57, y −116,4) y el VCC (LDO interno que alimenta el driver de puerta) queda con 4 mm de pista. Fuera del criterio de desacoplo (≤ 1 mm, máx. 2 mm) y de la guía de layout del datasheet («VCC capacitor as close as possible to the pin») | `pads.json`: U5:2 (VCC) ↔ C12 3,86 mm (vuelta 0: 0,62); `design.py` l. 212 | Verificado | Intercambiar C12 y R21: C12 a (−53,8; −114,5… −114,9) frente al pin VCC (y −115,25) y R21 a (−57; −116,4). R22 sigue en el pin FB y fija el nodo; R21 toma V6 en Kelvin desde C18 igual desde la columna exterior | Abierto |
| R17 | Mejora | Compensación del elevador | R24 a 3,99 mm del pin COMP y C14 a 3,97 mm de R24 (el nodo BST_RC recorre 4 mm); C15 (10 pF) sí está a 1,06 mm | `pads.json` | Verificado | R24 girado 0° (pad BST_RC hacia el este) y C14 justo debajo de R24, en (−57; −119,6), con el GND de C14 a la isla de GND de señal de U5 | Abierto |
| R18 | Mejora | Pasillo sur | C27 (−48,2; −89,6) y R51 (−44; −89,6) entran 0,5 mm en el extremo este del pasillo sur (y −83…−89,3), donde ya desembocan J6, J9 y los LDO; no estorban al rutado | `layout.py`; comprobación de cajas | Verificado | Nada; anotar que el pasillo sur acaba en x ≈ −52 | Aceptado |
| R19 | Mejora | Serigrafía | J9 con 7 de 12 rótulos (faltan EN+, ESP y un G) porque TP11 y su rótulo «1V2» están en medio de la leyenda; «IO8» de JP4 solo en la cara inferior | PNG `montaje-B_placa`; nota del autor | Verificado | TP11 1,5 mm al oeste (sigue a < 5 mm de U9/C29) para liberar la leyenda; «IO8» arriba si cabe tras el cobre | Abierto (E2) |
| R20 | Mejora | DFM, borde | R50 (0,13 mm), C14 (0,14) y R23 (0,24) con el patio a menos de 0,5 mm del borde fresado; los pads cumplen 0,3 (DRC) y el mínimo de JLCPCB (0,2) | pcbnew contra el contorno | Verificado | Donde haya sitio, ≥ 0,5 mm (R23 y R50 a −0,3 mm en x; C14 se mueve con R17) | Abierto |
| R21 | Mejora | Pruebas | `TEST-PLAN.md` sin RT1: falta medir V_TS (≈ 0,75 V a 25 °C) y la suspensión de carga al calentar la NTC (CHG sigue bajo, I_BAT → 0) | `grep RT1 TEST-PLAN.md` vacío | Verificado | Añadir al TEST-PLAN en el encargo de fabricación (ya figura como desfasado en `NOTAS.md`) | Abierto (E1) |

## PNG leídos (vuelta 1)
- `colocacion.png`: misma planta; RT1 sola bajo la batería al oeste del pasillo del USB; logo pequeño abajo a la izquierda; el DVP, el par USB y el I2S como en la vuelta 0.
- `montaje-F_placa`: «+» sobre J2 y «−» junto a J3; IO9/IO46/IO3 arriba; resto igual.
- `montaje-B_placa`: 14 TP con nombre; J_EXP con sus 10 GPIO; J5 y J7 completos; J9 con la leyenda partida por «1V2» (R19); logo, nombre, versión y recuadro PLACA sin pisar nada.
- `ratsnest_zona-U3`: C6 encima de VIN (pin 10), C7 bajo VOUT (pin 6), C8 al lado, L1 al este con BB_SW1/2; R16 en FB. Pasa (R2).
- `ratsnest_zona-U5`: C18 horizontal bajo los pines 5/6; C16 al este con VSYS hacia el pin 9; C13 sobre BOOT; columna oeste pegada; **C12 en la segunda columna** (R16).
- `ratsnest_zona-C14`: C14 bajo C15, fuera de la zona caliente de L2 y a 0,14 mm del borde (R17, R20).
- `ratsnest_zona-RT1`: NTC sola, sin nada a < 3 mm; el par USB (verde) pasa 3 mm al este.
- `ratsnest_zona-U8`: U8 a 270° con TP10 bajo su pad de entrada (cara B) y C27/C28 pegados; U9 a 270° al este. Pasa.

## Checklist de la puerta (4.6), vuelta 1
| Sev. | Punto | Estado |
|------|-------|--------|
| C | Contorno, taladros y conectores coherentes con la carcasa | OK (sin cambios) |
| C | Interfaz con piezas reales medida | OK salvo el agujero del mecanismo (supuesto, ahora con 2 mm de anillo; medir antes de rutar) |
| C | Keepout de antena en todas las capas | OK (sin cambios; ninguna pieza dentro) |
| C | `comprobar-flujo` PASS | OK |
| I | Convertidores como su layout de referencia | U3 OK; U5: C18/C16/C13 OK, **C12 no (R16)**; U2, U6, U7 OK |
| I | TP junto a su fuente; accesibles | OK (`revisar-rutado` PASS; linter OK) |
| I | Alturas | OK |
| I | Taladros, keepouts, borde | OK; patios al borde en R20 (mejora) |
| — | Preferencias de Guillermo (pads de batería, TP rotulados, GPIO rotulados, logo subordinado) | OK |
| — | NTC | OK (R4 resuelto; conexión según datasheet) |

## Revisión final como revisor senior (vuelta 1)
- Al corregir un hallazgo se rompió otro punto que estaba bien (C12): la lección es volver a medir **todos** los pares pin–condensador del bloque tocado, no solo los del hallazgo; queda recogida en este informe para el Cerebro.
- TP lejos de su fuente: ya no se repite (`revisar-rutado` PASS sin pistas).
- Bus rápido por un convertidor: no se repite.

## Siguiente paso
Vuelta 2 (última, `revision-de-diseno.md` §6.1): intercambiar C12 y R21 (R16), opcionalmente R17/R20, y repetir `comprobar-flujo`, `revisar-rutado` y la medida pin–condensador de U5. Después, revisión independiente breve y rutado.
