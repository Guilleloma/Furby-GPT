# Revisión A arquitectura — FurbyBoard v1.0

- Fecha: 2026-10-24 · Commit: fe588cc (estado de partida) · Revisor: electronics-engineer (replanteo independiente, modelo T0)
- Tipo de placa: **L** · Capas: 4 · Fabricante: JLCPCB (perfil `fabricante-jlcpcb`)
- Material revisado: `../PCB-suelo/ARQUITECTURA.md` (rev. v2), `../PCB-suelo/interfaz-base.md`, `geometria.json`, `NOTAS.md` (estado al pausar), `scripts/design.py`

## Resultado
**PASA tras las correcciones** — 0 críticos, 0 importantes, 2 mejoras abiertas (anotadas en `NOTAS.md`).

## Herramientas
| Herramienta | Comando | Resultado |
|-------------|---------|-----------|
| Cuenta de conexiones | `pcb-toolkit comprobar-flujo … --json` | 232 conexiones sin GND ni planos (≈ 340 con GND): rúbrica **L** |
| kicad-happy | — | **no ejecutado** (no instalado; degradación de `kicad-automatizacion.md` §1.2) |

## Hallazgos
| ID | Severidad | Área | Hallazgo | Evidencia | Verificado / supuesto | Corrección propuesta | Estado |
|----|-----------|------|----------|-----------|-----------------------|----------------------|--------|
| A1 | Importante | Proceso | No había rúbrica S/M/L ni estrategia de rutado escrita; las dos colocaciones anteriores se hicieron sin ella | `NOTAS.md` al pausar | Verificado | Rúbrica **L**: > 150 conexiones, 3 convertidores a ≈ 1 MHz más clase D, bus DVP a 20 MHz, par USB. Layout y revisiones en T0, crítico explícito y fijado, Freerouting acotado solo para lo lento | Corregido (`NOTAS.md`, «Rúbrica») |
| A2 | Importante | Alimentación | La tabla de carriles de la arquitectura no tenía picos simultáneos, margen ×1,3, Tj ni ancho mínimo de pista | `ARQUITECTURA.md` §1 «Carriles» | Verificado | Tabla de raíles completa en `NOTAS.md`; los anchos pasan a `params.py` (`ANCHOS_MINIMOS`), al `.kicad_dru` y a `pcb-toolkit.toml` | Corregido |
| A3 | Importante | Mecánica | Planta anterior: el expansor y su acondicionamiento lejos del módulo y de sus pads de cable; bloque del motor y cargador apretados en la esquina trasera derecha; sin pasillos reservados | Mapa de congestión de `comprobar-flujo` y diagnóstico de `NOTAS.md` («Diagnóstico») | Verificado | Replanteo de la partición en bloques (`NOTAS.md`, «Planta») | Corregido en la colocación (puerta C) |
| A4 | Mejora | Coste | El pedido sigue dentro de lo estimado (4 capas, montaje Economic a una cara, mismas piezas extended; −1 extended al quitar Q2… que era básica). Sin cambio de área ni de capas | Estimación de `ARQUITECTURA.md` §10 | Estimado | Nada | Abierto (informativo) |
| A5 | Mejora | Batería | Los dos agujeros de Ø1,2 para atar los cables de la batería que proponía la arquitectura no están en el diseño | `ARQUITECTURA.md` §7.1 | Verificado | Añadirlos en v1.1 si hay sitio detrás de los pads | Abierto |

## Checklist de la puerta
| Punto | Estado |
|-------|--------|
| Requisitos contestados (`diseno-de-circuito.md` §2): entradas (USB 5 V, LiPo 1S), consumo por modo, entorno (interior, dentro del Furby), tamaño y carcasa (suelo de la base, holgura 1,0, 4 × M2), cantidad y fabricante (5 PCB, JLCPCB), señales especiales (DVP 20 MHz, USB FS, 3 convertidores) | OK (`ARQUITECTURA.md`) |
| Diagrama de bloques | OK (`ARQUITECTURA.md` §1) |
| Tabla de raíles | Hallazgo A2 → OK |
| Rúbrica S/M/L | Hallazgo A1 → OK (L) |
| Riesgos | OK: antena junto a la batería (plan B WROOM-1U), flex de la cámara, pico de 2,9 A frente al PCM (mitigado con ITRIP y limitador) |

## Revisión final como revisor senior
- ¿Un bus rápido cruzando un convertidor por la colocación (FurbyBoard, primera colocación)? La planta nueva reserva el pasillo de la cámara (módulo → J6) lejos del elevador, que baja a la esquina trasera derecha; lo vigila `comprobar-flujo` (puerta C).
- ¿TP lejos de su fuente? Los 14 TP van en la cara inferior sobre una vía de su red junto a la pieza que la genera; lo vigila `revisar-rutado --tp-max`.
- ¿«DRC 0» como calidad? La rúbrica L exige revisión independiente de la colocación y del diseño.
