# Base del Furby de 1998 modificada para la PCB del suelo

La base original se modifica lo justo para alojar la PCB de `Hardware/PCB-suelo/`: **4 separadores** con piloto para tornillo M2 × 4 y una **ventana para el USB-C** en la pared trasera del lóbulo. Todo lo demás queda igual que en el original, incluidos los 4 agujeros del suelo.

El STL original es de un tercero y no está en el repositorio. Tampoco lo están los STL de salida ni los renders. Aquí solo están los scripts y los parámetros.

## Ficheros

| Fichero | Qué es |
|---------|--------|
| `parametros-base.json` | Cotas propias de la base y tolerancias de verificación |
| `scripts/comun.py` | Lectura de parámetros, medidas del STL original, cortadores y piezas auxiliares |
| `scripts/modificar_base.py` | Genera la base, la prueba del lóbulo, el cupón de pilotos y la PCB fantasma |
| `scripts/verificar_base.py` | Comprobaciones A a I; escribe `verificacion.json` y sale con 1 si algo falla |
| `scripts/render_base.py` | Planta y cortes acotados (matplotlib); llama a `render_blender.py` para las vistas 3/4 |
| `scripts/render_blender.py` | Vistas 3/4 con y sin PCB (Blender en segundo plano) |

## Uso

```sh
cd Hardware/Base-furby
python3.13 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python -I scripts/modificar_base.py --base-stl <STL original> --salida <carpeta>
.venv/bin/python -I scripts/verificar_base.py --base-stl <STL original> --salida <carpeta>
.venv/bin/python -I scripts/render_base.py   --base-stl <STL original> --salida <carpeta>
```

- `--salida` tiene que quedar **fuera del repositorio**. Si no, el script se niega a escribir.
- `modificar_base.py` verifica antes de escribir. Si alguna comprobación falla, solo escribe `verificacion.json` y sale con 1. Con `--forzar` escribe también los STL, para inspeccionarlos.
- `--geometria` y `--parametros` permiten trabajar con copias de los JSON.
- Si el sha256 del STL original no coincide con `sha256_base`, avisa y sigue.
- `manifold3d` necesita Python 3.12 o 3.13: a 24-10-2026 no había wheel para 3.14.

Salidas: `FurbyGPT-base-modificada.stl`, `prueba-lobulo.stl`, `cupon-pilotos.stl`, `pcb-fantasma.stl` (solo para renders), `verificacion.json` y `render/` (5 PNG).

## Método

- **Booleanas de malla con `manifold3d`**, en doble precisión (`Mesh64`). `trimesh` lee y escribe y lanza los rayos y las secciones; `shapely` hace el 2D.
- **Una sola fuente de cotas:**
  - La geometría de la PCB (contorno, taladros, mecanismo, `usb.*` y `alturas.*`) se lee de `Hardware/PCB-suelo/geometria.json`.
  - Lo propio de la base está en `parametros-base.json`.
  - El resto se **mide en el STL**: el z del suelo, las caras de la pared del lóbulo y los agujeros originales. El código no lleva cotas.
- **El z del suelo se mide con 20 rayos.** Sale 1,90541 (el valor exacto de la malla) y se compara con `alturas.corte_inf` (1,905). Si se separan más de 0,01, el script aborta.
- **Coplanares:** la ventana corta a ras de la cara superior del suelo. Manifold resuelve bien el género y el volumen, pero deja una docena de astillas de 1e-10 mm². Un `simplify(1e-6)` las colapsa y el volumen cambia en 1e-5 mm³. Si aun así la malla no sale limpia (género, un cuerpo, cerrada y sin degenerados), se repite bajando la ventana `eps_coplanar`. Hoy no hace falta.

## Operaciones

| Feature | Qué hace |
|---------|----------|
| `Separador_H1…H4` | Cilindro de Ø `separador_d`, desde z_suelo − `separador_empotrado` hasta z_pcb_inf (3,905). Se une a la base |
| `Ventana_USBC` | Perfil XZ de x −80 a −67 y de z_suelo a `corte_sup`, con las esquinas superiores en R `ventana_radio_sup`. Atraviesa la pared en Y. Lleva un chaflán exterior a 45° de `ventana_chaflan_ext` en las jambas y el techo |
| `Piloto_H1…H4` | Ø `piloto_d` desde z_piloto_fondo (1,205) más un cono de chaflán `piloto_chaflan` en la boca. Se resta |
| `Rebaje_Mecanismo` | Solo si `mecanismo_rebaje` > 0. Hoy vale 0: el suelo queda intacto |

Derivados (en `verificacion.json`): piloto_prof = tornillo_largo − grosor PCB + margen = **2,7**; suelo bajo el piloto = **1,205** (mínimo 1,0); separador **2,0** de alto.

### Chaflán exterior de la ventana: plano de referencia

La cara exterior del lóbulo es curva: está en y −130,50 en x −73,5, pero en −130,11 en x −80 y en −130,03 en x −67. Tiene una flecha de 0,39 a 0,47 en las jambas. Si el chaflán se referencia a la y del centro, en las jambas se queda en 0,03 a 0,11 y no llega al mínimo de 0,2. Por eso el plano de referencia es la **media de las tres y**. El chaflán real medido en la salida es **0,40 / 0,79 / 0,32** (x −80 / −73,5 / −67), dentro del rango de 0,2 a 0,8.

## Piezas de prueba

- **`prueba-lobulo.stl`**: recorte de x −96 a −50, y −133 a −112 y z 0 a 12, con la ventana, H3 y H4. Sirve para probar el cable real y el tornillo antes de imprimir la base entera.
- **`cupon-pilotos.stl`**: placa de 40 × 10 del grosor del suelo con 4 separadores, con pilotos de Ø1,6 / 1,7 / 1,8 / 1,9 cada 10 mm (`cupon_paso`). El de Ø1,6 está junto a la esquina recortada (`cupon_marca`). Se elige el Ø que agarre bien el M2 × 4 y se lleva a `piloto_d`.

## Impresión

- La pieza se imprime como el original, con z 0 sobre la cama. No necesita soportes: el techo de la ventana es un puente de 13 mm con chaflán a 45°, y los separadores y pilotos son verticales.
- Capa de 0,2 (o 0,16), 4 perímetros y 5 capas arriba y abajo. Pata de elefante de 0,1 a 0,15. La costura, lejos de las jambas.
- Primero se imprimen la prueba del lóbulo y el cupón, y después la base.

## Parámetros y prueba de parametricidad

Lo que se toca a mano está en `parametros-base.json`, sobre todo `separador_d`, `piloto_d`, `tornillo_largo`, `ventana_radio_sup`, `ventana_chaflan_ext`, `mecanismo_rebaje`, `funda_ancho` y `funda_alto`. Si la PCB cambia, se regenera `geometria.json` en `Hardware/PCB-suelo/` y se vuelve a ejecutar el script.

Prueba hecha con copias de los dos JSON: con `separador_d` = 4,8 y `alturas.corte_sup` = 9,5, la base se regenera y se verifica sin tocar código. Los separadores salen de Ø4,798 (96 lados), la ventana llega a z 9,5 y la malla sale limpia.

## Verificación

El detalle está en `verificacion.json`. Resultado con los parámetros del plan:

| | Comprobación | Resultado |
|-|--------------|-----------|
| A | Cotas z del original | Suelo a 1,90541 en los 20 rayos y cara inferior a 0. Pared del lóbulo de 1,70 a 1,73 en x −80, −73,5 y −67 |
| B | PCB frente a la pared | PCB a **0,4997** como mínimo (criterio 0,5 ± 0,001), sin vértices dentro del prisma. **USB-C a 0,090** (criterio 0,25): **en rojo**, ver Pendiente |
| C | Malla de salida | Cerrada, normales coherentes, 1 cuerpo, género 4 → 5, sin degenerados |
| D | Volumen | Error de 1e-5 mm³ |
| E | Lo no tocado | Distancia máxima 4e-9. Los 4 agujeros siguen pasantes y miden Ø2,130 |
| F | Medidas | Ventana en x −80,00 … −67,00 y z 1,905 … 9,255. Separadores con error de centro ~1e-14, Ø4,998 y cara superior a 3,905. Pilotos de Ø1,799 y 2,70 de profundidad, con 1,205 de suelo debajo |
| G | Exclusiones | 0 mm³ dentro de la exclusión de Ø15,3. Separador a agujero original 9,36 como mínimo; a muesca, 7,43 |
| H | Cable | Funda a **0,293** de la base (criterio 0,3): **en rojo**, ver Pendiente. Cuerpo del USB-C a 2,02 |
| I | Apoyo | La PCB apoya en los 4 separadores con una separación de 4e-16 y no corta la base |

## Pendiente

- **B, cuerpo del USB-C contra la pared al montar.** La cara interior del lóbulo es curva. La boca del conector queda a 0,30 de la pared en el centro, pero las esquinas del cuerpo (8,94 de ancho) quedan a 0,09 y 0,125. En la base montada no toca, porque la ventana despeja esa altura. Al bajar la PCB en vertical, sin embargo, pasa junto a la pared intacta de encima de la ventana con 0,09 de holgura.
- **H, funda contra la esquina R 1,0 de la ventana.** La funda se modela como una caja de esquinas vivas y su esquina queda a 0,293 del arco. Con `ventana_radio_sup` ≤ 0,98 se cumple el criterio de 0,3 (con 0,9 queda a 0,334).
- Siguen pendientes de confirmar los supuestos del plan: el centro y el Ø del mecanismo, la funda del cable real y el Ø de la torreta del cuerpo (las muescas).
- `usb_cuerpo_ancho` y `usb_cuerpo_largo` repiten valores de `contorno_suelo.py`. Convendría que `geometria.json` los exportara.
