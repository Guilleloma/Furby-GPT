# Revisión C colocación — FurbyBoard v1.0

- Fecha: 2026-10-24 · Commit: el de la colocación de esta rama (ver `git log`) · Revisor: electronics-engineer (replanteo independiente, modelo T0; revisión propia, no independiente)
- Tipo de placa: L · Capas: 4 · Fabricante: JLCPCB (reglas del perfil en el `.kicad_pro`)
- Material revisado: `FurbyBoard.kicad_pcb` generado por `scripts/gen_pcb.py --sin-rutado` desde `scripts/layout.py`; PNG de `pcb-toolkit png-revision --ratsnest --zona L1,L2` (fuera del repo) y `comprobar-flujo --png`; `render/colocacion-arriba.png` y `render/colocacion-abajo.png`

## Resultado
**PASA** — 0 críticos, 0 importantes, 4 mejoras anotadas. En placa L el encargo termina aquí: la revisión independiente de la colocación la lanza Maestro antes del rutado.

## Herramientas
| Herramienta | Comando | Resultado |
|-------------|---------|-----------|
| ERC | `kicad-cli sch erc --severity-all --exit-code-violations` | 0/0 |
| DRC | `kicad-cli pcb drc --schematic-parity --severity-all` (sin `--refill-zones`) | **0 infracciones, paridad 0**; 362 conexiones sin rutar (esperable) |
| Flujo | `pcb-toolkit comprobar-flujo FurbyBoard.kicad_pcb --png … --json …` | **PASS**: 0 errores, 4 avisos (desacoplo a 1,02–1,9 mm), 232 conexiones, 9 zonas calientes, demanda máxima de celda 0,58 (umbral 0,8), 0 celdas congestionadas |
| Colocación propia | `scripts/comprobar_colocacion.py` | OK: TP, puentes, LED, botones y pads de cable fuera de la batería; calzos libres; 64 piezas bajo la batería, la más alta L1 (2,1 mm) para 4,1 de hueco; nada bajo el flex |
| Geometría | `pcb-toolkit revisar-rutado` | No aplica (sin rutado) |
| Configuración | `pcb-toolkit.toml` frente a `ejemplos/pcb-toolkit.toml` | Sin reglas en `off` ni umbrales relajados; margen 1,0 mm en las zonas del puente H y de la clase D, justificado en `NOTAS.md` |
| kicad-happy | — | no ejecutado (no instalado) |
| PNG | 12 leídos: `ratsnest_placa`, `montaje-F_placa`, `montaje-B_placa`, zonas U2, U3, U4, U5, U6, U7, U10, J1, J6, J9 | Comentados abajo |

## Hallazgos
| ID | Sev. | Área | Hallazgo | Evidencia | Verificado / supuesto | Corrección | Estado |
|----|------|------|----------|-----------|-----------------------|------------|--------|
| C1 | Mejora | Desacoplo | C10 (100 nF del módulo) a 1,9 mm del pin 2 y C32 (TCA9535) a 1,08 mm: por encima del 1,0 mm ideal, dentro del máximo de 2 mm. C28/C29 (LDO) a 1,02 | `comprobar-flujo` avisos #1–#4 | Verificado | El pad del módulo y el patio de J9 no dejan acercarlos más; aceptado | Aceptado |
| C2 | Mejora | Serigrafía | Rótulos sin sitio: «+» de J2 arriba (BAT+ y BAT− sí están abajo y los pads tienen forma distinta), parte de la leyenda de J_EXP, J5 y los pads 1 y 7 de J9 | `gen_pcb.py` («Rótulos sin sitio») | Verificado | Se recolocan en la fase de rutado con el cobre definitivo; manda el diseño | Abierto (rutado) |
| C3 | Mejora | Buses | `cruces-en-bus` (info): DVP 15, I2S 13, sensado 3 cruces entre líneas rectas del ratsnest | JSON de `comprobar-flujo` | Verificado | Son cruces geométricos de líneas rectas entre una fila de pines y una columna de pads (rutado «de río» sin cruces reales, ver `NOTAS.md` «Pasillos»); los pines del módulo ya siguen el orden de los pads de J6 | Aceptado |
| C4 | Mejora | Batería | La fila trasera de J7 queda con el borde del pad a 0,05 mm del borde delantero nominal de la batería (centro del pad 0,8 mm fuera) | Linter de colocación | Verificado | El cable se suelda por delante; si molesta, J7 sube 0,1 mm a costa del área restringida del módulo | Aceptado |

## PNG leídos
- `ratsnest_placa`: bloques como en `NOTAS.md` («Planta»); el bus DVP (cian) va del lado derecho del módulo a J6 por el pasillo de la cámara sin tocar ninguna zona caliente; el par USB (verde) sube recto por el pasillo norte-sur a 2 mm del hull de L1; el I2S (magenta) va de la columna izquierda a U7 y J5; el sensado (amarillo) solo cruza el módulo (LIGHT, VBAT_SNS por debajo en capas internas). Congestión moderada en el canal de la columna izquierda y en la fila inferior del módulo.
- `montaje-F_placa`: serigrafía de LED, botones y puentes legible; «FurbyBoard v1.0» delante de la antena; polaridades de los LED visibles.
- `montaje-B_placa`: logo entero bajo la zona trasera izquierda de la batería; rótulos de pads de cable y de J_EXP (parciales, C2); BAT+ y BAT−.
- `zona-U5`: SW de U5 arriba, pegado al pad SW de L2; VIN al este con C16; VOUT y GND al sur con C18 (lazo de salida mínimo); compensación y FB al oeste.
- `zona-U2`: C3 (OUT) al norte, C2 (IN) al oeste, C4 (BAT) al sur, EN/PGOOD/CHG al este con sus pull-ups; Q1 y los pads de batería detrás.
- `zona-U6`: lado de control (IPROPI, IN, VREF) al oeste con R28/C23; VM y salidas al este con C22/C20 y los pads del motor de J9; zona caliente solo sobre las salidas.
- `zona-U7`: VDD al norte con C26 a 1,8 mm; salidas al oeste hacia J8.6/7; I2S por el este hacia los pines del sur.
- `zona-U3`: VIN/L1/L2/VOUT al este con la bobina y C7/C8; FB al oeste con R15/R16 pegados.
- `zona-U4`: columna izquierda hacia el expansor y el canal; fila inferior hacia el pasillo de la cámara; pines 35–39 hacia la izquierda por debajo del módulo.
- `zona-J1`: pads del USB-C con U1 detrás y R1/R2 a los lados; nada en la ranura.
- `zona-J6`: pines 7–22 reciben el bus desde el oeste en orden; 1–6 y 10/11 desde los LDO de debajo.
- `zona-U10`: I2C e INT por el este hacia el módulo; acondicionamiento de J8 al oeste.
- `zona-J9`: fototransistor y leva en la columna exterior, lejos de la zona del motor (abajo, columna interior).

## Checklist de la puerta (4.6)
| Sev. | Punto | Estado |
|------|-------|--------|
| C | Contorno, taladros y conectores coherentes con la carcasa; holgura ≥ 1 mm; fijación por tornillos | OK: `geometria.json` sin cambios (H1–H4, USB-C, agujero del mecanismo); la base no se toca |
| C | Interfaz con piezas reales medida | OK para el USB-C y el contorno (encargos anteriores); el centro del agujero del mecanismo sigue siendo un supuesto (pendiente de medir, `interfaz-base.md`) |
| C | Keepout de antena como área de reglas en todas las capas | OK (`gen_pcb.py`: x −85…−61, y > −62 en las 4 capas) + el área restringida propia de la huella del módulo |
| C | `comprobar-flujo` PASS | OK |
| I | Bloques compactos, cada convertidor como su layout de referencia, corredores reservados | OK (PNG de U5, U3, U6, U2; pasillos en `NOTAS.md`) |
| I | TP junto a su fuente; LED, botones, puentes y conectores accesibles | OK: 14 TP en la cara inferior junto a su fuente (lo comprobará `revisar-rutado --tp-max 5` al rutar); LED, botones y puentes arriba fuera de la batería |
| I | Alturas dentro de la carcasa, por zonas | OK: `comprobar_colocacion.py` (≤ 2,1 mm bajo la batería; nada bajo el flex; nada en la cara inferior salvo TP) |
| I | Taladros con keepout de cabeza y distancia al borde; fiduciales | OK: patio Ø5 de la huella y área sin cobre Ø5 en F/B; H3/H4 a 2,56/2,60 del borde (≥ 1,6); sin fiduciales (montaje Economic) |

## Revisión final como revisor senior
- Bus rápido por un convertidor (lección de esta placa): el DVP va por el pasillo de la cámara, el elevador en la esquina trasera derecha y el buck-boost al oeste del pasillo del USB; `comprobar-flujo` lo vigila con 3 mm.
- TP lejos de su fuente: cada TP a ≤ 5 mm de su pieza, en la cara inferior.
- El cruce del par USB en J1 queda resuelto desde las reglas (vías 0,45/0,2 solo en la clase USB) y la colocación de U1 (`NOTAS.md`, «Par USB»).
