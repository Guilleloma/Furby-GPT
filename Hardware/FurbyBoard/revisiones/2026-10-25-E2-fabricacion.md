# Revisión E2 ficheros de fabricación — FurbyBoard v1.0

- Fecha: 2026-10-25 · Commit: `fbace1e` (ficheros) sobre el diseño de `d99273f` · Revisor: electronics-engineer (T1, Opus 5.5), puerta propia
- Tipo de placa: L · Capas: 6 (JLC06161H-7628) · Fabricante: JLCPCB (montaje Economic a una cara)
- Material revisado: `fabricacion/` (Gerber, taladros, BOM, CPL, informes), `render/furbyboard-*`, el `.kicad_pcb` y los scripts de fabricación. Antes de exportar: E1 propia y re-revisión independiente de la vuelta 1, **PASA** (`2026-10-25-E1-rutado.md`, `2026-10-25-E-independiente.md`)
- Herramientas: kicad-cli 10.0.7, pcb-toolkit 0.1.0, rsvg-convert; Gerber rasterizados con gerbonara 1.6.3 en un venv del scratchpad (nada instalado fuera de él); API de piezas de JLCPCB y de huellas de EasyEDA, consultadas el 2026-10-25

## Resultado
**PASA** — 0 críticos, 0 importantes, 3 mejoras abiertas. El cobre no ha cambiado: lo único que se tocó del diseño son los modelos 3D de cinco huellas y el relleno, que ahora se hace con las reglas del proyecto (`d99273f`).

## Herramientas
| Herramienta | Comando | Resultado |
|-------------|---------|-----------|
| Rellenos al día | `make_fab.sh`: copia del PCB rellenada con `kicad-cli pcb drc --refill-zones --save-board` y `cmp` con la placa | **Idénticos byte a byte** |
| Áreas de relleno | Volcado con pcbnew por red y capa (subproceso, `os._exit`) | In1/In4 3313,1 mm² en 1 trozo; GND F 2084,6 en 21; GND B 2773,2 en 10; VSYS In2 2616,3 en 3; BAT F 31,2 en 1: **iguales a la re-revisión independiente** |
| ERC | `kicad-cli sch erc --severity-all --exit-code-violations` | **0 / 0** (`fabricacion/erc.rpt`) |
| DRC final | `kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations`, sin relleno | **0 infracciones, 0 sin unir, 0 de paridad** (`fabricacion/drc.rpt`) |
| Cobre frente a `05cabf1` | Comparación propia de pistas, vías, zonas, textos y huellas (referencia, cara y posición) | 1044 pistas, 334 vías, 6 zonas, 87 textos y 156 huellas: **idénticos**; solo cambian 5 rutas de modelo 3D |
| CPL | `pcb-toolkit cpl-rotaciones fabricacion/cpl-jlcpcb.csv FurbyBoard.kicad_pcb --bom fabricacion/bom-jlcpcb.csv --gerber fabricacion/gerber` | **PASS, 0 errores**; 124 piezas; origen del CPL (220; −40) = origen del Gerber; 8 avisos `giro-sin-tabla` (E2-M1). Con la tabla completada con esos 8 códigos: PASS, 0 errores, 0 avisos |
| Giros contra EasyEDA | Script propio: pads de la huella EasyEDA de cada LCSC frente a los de la huella colocada en el PCB, con giros de 0/90/180/270° y la función de cada pin | 21 códigos (todos los que no son R ni C): el giro y el origen de `jlc_post.py` son los únicos que hacen coincidir la geometría **y** el pin 1 (tabla abajo) |
| Gerber en imagen | gerbonara → SVG → `rsvg-convert`, desde `fabricacion/gerber/` (no desde el `.kicad_pcb`) | 15 capas sueltas y 2 vistas compuestas leídas (sección «Gerber en imagen») |
| Render 3D | `kicad-cli pcb render` (arriba, abajo, iso) | Leídos; los 5 CI con modelo nuevo tienen cuerpo |
| Datos personales | `grep -r '/Users/'` en `Hardware/FurbyBoard`, texto del PDF, cabecera del STEP | Nada |

## Capas y taladros
| Comprobación | Resultado |
|--------------|-----------|
| Capas de cobre | 6 (`TF.FileFunction` Copper L1…L6; `LayerNumber` 6 y grosor 1,6 en el `.gbrjob`) |
| Resto de capas | Máscara, pasta y serigrafía de las dos caras y contorno; la pasta inferior está vacía (montaje a una cara) |
| Taladros PTH (`FurbyBoard-PTH.drl`) | 0,2 mm × 3 (vías del par USB) + 0,3 mm × 331 = **334 vías**, las del PCB; 0,8 mm × 4 ranuras (G85) de las patas del USB-C; 1,0 mm × 44 (pads de cable de J3, J5, J7, J8, J9 y J11); 1,2 mm × 1 (J2) |
| Taladros NPTH (`FurbyBoard-NPTH.drl`) | 2,3 mm × 4 (H1–H4). PTH y NPTH van ya en ficheros separados (antes iban en uno, «MixedPlating») |
| Agujero del mecanismo (Ø 11,3) | Círculo cerrado en `Edge_Cuts`: se fresa como recorte interior |
| Mismo origen | Gerber con `--use-drill-file-origin`, taladros con `--drill-origin plot` y CPL con `--use-drill-file-origin`: todos con el origen auxiliar (0,0 del STL). Comprobado por `cpl-rotaciones` (CPL y contorno) y a mano (NPTH en (−97,0; −68,5) etc., en el mismo marco que el CPL) |

## Giros y orígenes comparados con EasyEDA
| LCSC | Ref. | Giro | Origen (mm, local KiCad) | Pin 1 EasyEDA cae en |
|------|------|------|--------------------------|----------------------|
| C2286, C2297 | D1–D5 | 0 | — | Ánodo (pad 1 EasyEDA) sobre el ánodo de KiCad (pad 2): **cátodo bien** |
| C20917 | Q3 | 180 | — | G sobre G |
| C553966 | Q1 | 270 | — | S sobre pad 1 (S); el pad expuesto de EasyEDA (−0,56 → +0,56) sobre el drenador de KiCad |
| C2687116 | U1 | 270 | — | I/O1 sobre I/O1 (6/6) |
| C53099, C7836 | U8, U11 | 180 | — | 5/5 pines con su función |
| C236672 | U9 | 270 | — | 5/5 |
| C130204 | U10 | 270 | — | 24/24 |
| C5139865 | U6 | 270 | — | 8/8 más el pad expuesto |
| C910544 | U7 | 270 | — | 16/16 más el pad expuesto |
| C15220, C165129, C2845237 | U2, U5, U3 | 0 | — | 16/16, 11/11 y 10/10 |
| C2848620 | J1 | 0 | (0; −4,700) | 20/20 pads |
| C2913202 | U4 | 0 | (0; 3,628) | 49/49 pads (KiCad tiene uno más, del pad expuesto partido) |
| C262669 | J6 | 0 | — | Pin 1 sobre pin 1 (26/26) |
| C602026, C602028, C720477, C883133, C13564 | L1, L2, SW1/SW2, F1, RT1 | 0 | — | Sin polaridad |

## BOM y piezas
- **BOM agrupada:** 51 líneas, una por huella y LCSC. Antes salían dos líneas con C720477 (SW1 «RESET» y SW2 «BOOT»): `jlc_post.py` ya agrupa por huella y código (E2-I1, corregido).
- 124 piezas en BOM y CPL, con las mismas referencias (lo comprueba `jlc_post.py` y `cpl-rotaciones` con `--bom`). Fuera: TP1–TP14, JP1–JP5, J2, J3, J5, J7, J8, J9, J11, H1–H4, LOGO1 y LOGO2.
- Clase y stock de las 51 líneas consultados en la API de JLCPCB: 30 basic, 3 preferred extended y 18 extended; **ninguna sin stock**; la clase de `design.py` coincide con la de JLCPCB en todas. Tabla completa en `fabricacion/README.md`.
- C22962 (R51) y C19702 (C41): basic, con stock. C23179 ya no está en la BOM.
- **FHD4020S-1R0MT (L2):** Isat 8,7 A máx. y 11 A típ., Irms 5,8 A (datasheet de Changjiang, tabla FHD4020S, leída en el PDF de LCSC); hacía falta ≥ 3,4 A. **Cerrado.**
- **C13564 (RT1, Murata NCP18XH103F03RB):** NRND confirmado (aviso de Murata; DigiKey la marca «Not For New Designs»; última compra prevista en 2032). 275 482 en stock en JLCPCB: vale para la v1.0. Alternativa en la misma huella: C440252 (NCU18XH103F60RB, sucesora de Murata, B 3380 K), extended, 30 597 en stock.

## Gerber en imagen
Leídos (en el scratchpad, no van al repo):

- **Vista compuesta superior:** contorno, muesca del USB-C con sus 4 ranuras, agujero del mecanismo, 4 M2, bloque sin cobre bajo la antena, todas las huellas con su máscara, rótulos «FURBYBOARD V1.0», PWR/RUN/TX/LED, RST/BOOT, IO9/IO46/IO3, «+» y «−» de la batería.
- **Vista compuesta inferior:** sin piezas, puntos de test con su rótulo, leyendas de J7, J8, J9 y J_EXP, **logo de GuilleMaker con «@GuilleMaker» legible**, «FurbyBoard v1.0 · 2026-10» y el Furby en píxeles. El agujero del mecanismo sale medio verde y medio negro: es un fallo de relleno de gerbonara; en `Edge_Cuts` solo el círculo es completo y cerrado.
- **In1 e In4:** GND enteros con los antipads de las vías y el hueco de la antena. **In2:** relleno de VSYS con las señales. **In3:** solo pistas. **F.Cu y B.Cu:** rellenos de GND a ≥ 0,3 mm del borde, el margen del proyecto (antes, 0,55).
- **Máscara:** aberturas en todos los pads y en los TP inferiores; **pasta superior** en todas las piezas montadas, con la ventana partida en los pads expuestos; **pasta inferior** vacía.
- **Taladros:** vías, pads de cable, 4 ranuras y 4 NPTH donde corresponde.

## Hallazgos
| ID | Severidad | Área | Hallazgo | Evidencia | Verificado / supuesto | Corrección propuesta | Estado |
|----|-----------|------|----------|-----------|-----------------------|----------------------|--------|
| E2-I1 | Importante | BOM | C720477 salía en dos líneas (SW1 «RESET», SW2 «BOOT»): BOM sin agrupar, la lección de la Game Boy | `bom-jlcpcb.csv` de la primera exportación | Verificado | Agrupar por huella y LCSC en `jlc_post.py` | **Cerrado** (`fbace1e`: «RESET / BOOT», SW1,SW2) |
| E2-I2 | Importante | Taladros | PTH y NPTH en un solo Excellon («MixedPlating»): el fabricante podría metalizar los M2 | Cabecera de `FurbyBoard.drl` | Verificado | `--excellon-separate-th` en `make_fab.sh` | **Cerrado** (`fbace1e`) |
| E2-M1 | Mejora | CPL | 8 códigos comparados sin entrada en la tabla de giros de pcb-toolkit (C720477, C262669, C2845237, C602026, C15220, C165129, C883133, C13564): 8 avisos `giro-sin-tabla` | Salida de `cpl-rotaciones` | Verificado; la comparación da giro 0 en los 8 | Añadirlos a `ejemplos/giros-jlcpcb.toml` como `comparado-sin-montar`. No se hizo aquí: el repo de pcb-toolkit tiene otra rama en curso | Abierto (NOTAS, «Pendiente») |
| E2-M2 | Mejora | Piezas | RT1 (C13564) es NRND | Aviso de Murata, DigiKey | Verificado | v1.0: se queda (stock alto, última compra en 2032). v1.1: C440252 | Abierto |
| E2-M3 | Mejora | Taladros | Planos interiores a 0,201 mm de los NPTH (E1-8): justo en el mínimo de JLCPCB (0,2) | DRC del proyecto; E1 | Verificado en E1 | Regla de 0,3–0,5 mm en el `.kicad_dru` y volver a rellenar en la v1.1. No se cambia ahora: el DRC del fabricante lo admite y cambiaría las áreas de relleno ya revisadas | Abierto |

## Checklist de la puerta (4.8)
| Sev. | Punto | Estado |
|------|-------|--------|
| C | Gerber, taladros y CPL con el mismo origen | OK: origen auxiliar en los tres; `cpl-rotaciones` PASS |
| C | Giro y origen de cada pieza del CPL comprobados contra la huella del montador por geometría | OK: 21 códigos comparados con la API de EasyEDA (tabla de arriba); R y C por la tabla `montado-verificado` |
| C | Reglas del perfil del fabricante cargadas y respetadas | OK: DRC 0/0/0 con las reglas de JLCPCB del proyecto; vía mínima 0,2/0,45 y anillo 0,125 dentro de la capacidad multicapa (0,15/0,25) |
| I | BOM con líneas agrupadas; DNP fuera de BOM y CPL | OK tras E2-I1; no hay DNP con LCSC |
| I | Serigrafía con los mínimos del fabricante; polaridades visibles; versión y fecha; GPIO libres numerados | OK con el aviso aceptado de E1: 12 textos a 0,8 mm (JLCPCB recomienda 1,0, imprime desde trazo 0,15). Pin 1 y cátodos marcados; «v1.0 · 2026-10»; IO3, IO8, IO9, IO46 y J_EXP numerados |
| I | README de fabricación con opciones de pedido, piezas a mirar en el visor y coste | OK: `fabricacion/README.md` reescrito para 6 capas |

## Revisión final como revisor senior
- **Gerber y CPL con distinto origen (Game Boy):** comprobado con herramienta y a mano.
- **BOM sin agrupar (Game Boy):** apareció (SW1/SW2) y se corrigió (E2-I1).
- **LED girados por comparar por número de pad:** comparados por función del pin; el cátodo cae en su sitio con giro 0.
- **Rellenos desfasados (FurbyBoard, E1-1):** el relleno ya no sale de `gen_pcb.py`; `make_fab.sh` para si la placa guardada no es la rellenada por kicad-cli.
- **Islas de relleno borradas en silencio:** mismas áreas y trozos que en la re-revisión.
- **Color blanco no admitido en Economic (Game Boy):** el README pide verde.
- **Distancia entre taladros que no casaba con la pieza real (Game Boy):** la mecánica no cambió desde la puerta C y el contrato con la base (holgura mínima 0,47 en las orejetas del USB-C); los M2 están en el NPTH donde los pone `geometria.json`.
