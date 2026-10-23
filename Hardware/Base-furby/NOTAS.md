# Base del Furby de 1998 modificada para la PCB del suelo

La base original se modifica lo justo para alojar la PCB de `Hardware/PCB-suelo/`:
- **4 separadores** con piloto para tornillo M2 × 4;
- una **ventana para el USB-C** en la pared trasera del lóbulo;
- un **rebaje interior** encima de la ventana, para que el conector libre la pared al montar la PCB.

Todo lo demás queda igual que en el original, incluidos los 4 agujeros del suelo.

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
  - Todo lo de la PCB se lee de `Hardware/PCB-suelo/geometria.json`: contorno, taladros, mecanismo con `exclusion_diametro`, `funda`, `muescas`, `usb.*` y `alturas.*`.
  - Lo propio de la base está en `parametros-base.json`.
  - El resto se **mide en el STL**: el z del suelo, las caras de la pared del lóbulo, el hueco interior de la pared y los agujeros originales. El código no lleva cotas.
- **El z del suelo se mide con 20 rayos.** Sale 1,90541 (el valor exacto de la malla) y se compara con `alturas.corte_inf` (1,905). Si se separan más de 0,01, el script aborta.
- **Coplanares:** la ventana corta a ras de la cara superior del suelo. Manifold resuelve bien el género y el volumen, pero deja una docena de astillas de 1e-10 mm². Un `simplify(1e-6)` (`tolerancia_malla`) las colapsa y el volumen cambia en 1e-5 mm³. Si aun así la malla no sale limpia (género, un cuerpo, cerrada y sin degenerados), se repite bajando la ventana `eps_coplanar`. Hoy no hace falta.

## Operaciones

| Feature | Qué hace |
|---------|----------|
| `Separador_H1…H4` | Cilindro de Ø `separador_d`, desde z_suelo − `separador_empotrado` hasta z_pcb_inf (3,905). Se une a la base |
| `Ventana_USBC` | Perfil XZ de x −80 a −67 y de z_suelo a `corte_sup`, con las esquinas superiores en R `ventana_radio_sup`. Atraviesa la pared en Y. Lleva un chaflán exterior a 45° de `ventana_chaflan_ext` en las jambas y el techo |
| `Rebaje_USBC` | En planta es el hueco interior de la pared desplazado `rebaje_usb_fondo` (0,3) hacia fuera, siguiendo la curva, y recortado al ancho de la ventana. Va desde el techo de la ventana menos `rebaje_usb_solape` (0,1) hasta por encima del borde de la pared. Se resta |
| `Piloto_H1…H4` | Ø `piloto_d` desde z_piloto_fondo (1,205) más un cono de chaflán `piloto_chaflan` en la boca. Se resta |
| `Rebaje_Mecanismo` | Solo si `mecanismo_rebaje` > 0. Hoy vale 0: el suelo queda intacto |

Derivados (en `verificacion.json`): piloto_prof = tornillo_largo − grosor PCB + margen = **2,7**; suelo bajo el piloto = **1,205** (mínimo 1,0); separador **2,0** de alto.

## Desviaciones del plan del architect

- **Rebaje interior sobre la ventana (`Rebaje_USBC`)**, por decisión de Maestro.
  - **Por qué:** la cara interior del lóbulo es curva. La boca del USB-C queda a 0,30 de ella en el centro, pero las esquinas del cuerpo (8,94 de ancho) quedaban a **0,09** y 0,125.
  - **El problema:** con la base montada no toca, porque la ventana despeja esa altura. Pero la PCB entra en vertical desde arriba, y al bajar el cuerpo pasaba junto a la pared intacta que queda por encima de la ventana.
  - **Resultado:** el rebaje retira 0,3 de pared hacia fuera y deja **0,39** de holgura. La pared queda en 1,40 en el centro y en 1,43 en las jambas.
  - **Impresión:** el rebaje está abierto por arriba, así que se imprime en vertical sin soportes. No cambia el género, porque es ciego y se une a la ventana.
  - **Cómo se comprueba:** B mide la holgura del USB-C contra la base de salida en toda la altura, y la de la PCB contra el original (0,5). D suma el volumen que el rebaje quita fuera de la ventana. E excluye su caja dilatada 1 mm.
- **`ventana_radio_sup` = 0,9 en vez de 1,0.**
  - La funda se modela como una caja de esquinas vivas. Su esquina superior queda a una distancia del arco de la ventana de **holgura = R − √2 · (R − m)**, donde m = (ancho de la ventana − ancho de la funda) / 2 = 0,5 es el margen lateral, igual al de arriba.
  - Con R = 1,0 la holgura es 0,293, por debajo del criterio de 0,3. Con R = 0,9 es **0,334**. El contrato de la interfaz permite hasta 1 mm.
- **Chaflán exterior referido a la media de la cara curva.**
  - La cara exterior del lóbulo está en y −130,50 en x −73,5, pero en −130,11 en x −80 y en −130,03 en x −67. Tiene una flecha de 0,39 a 0,47, no de 0,3.
  - Con la y del centro como referencia, el chaflán se quedaba en 0,03 a 0,11 en las jambas, por debajo del mínimo de 0,2. Por eso el plano de referencia es la **media de las y en x −80, −73,5 y −67**.
  - Chaflán real medido en la salida: **0,40 / 0,79 / 0,32** (x −80 / −73,5 / −67), dentro del rango de 0,2 a 0,8.
- **Dilatación euclídea en H.** La funda y el cuerpo del USB-C se dilatan con una suma de Minkowski con una esfera. Dilatar caja a caja alarga las esquinas √2 veces y marca choques que no existen.
- **Parámetros añadidos:**
  - `funda_largo`;
  - `usb_cuerpo_ancho` y `usb_cuerpo_largo`, que repiten valores de `contorno_suelo.py`;
  - `rebaje_usb_*`, `cupon_paso`, `cupon_marca` y `tolerancia_malla`;
  - los bloques `verificacion` y `render`.

  La exclusión del mecanismo y la funda ya no se duplican aquí: salen de `geometria.json`.

## Piezas de prueba

- **`prueba-lobulo.stl`**: recorte de x −96 a −50, y −133 a −112 y z 0 a 12, con la ventana, el arranque del rebaje, H3 y H4. Sirve para probar el cable real, el paso del conector junto a la pared y el tornillo antes de imprimir la base entera.
- **`cupon-pilotos.stl`**: placa de 40 × 10 del grosor del suelo con 4 separadores, con pilotos de Ø1,6 / 1,7 / 1,8 / 1,9 cada 10 mm (`cupon_paso`). El de Ø1,6 está junto a la esquina recortada (`cupon_marca`). Se elige el Ø que agarre bien el M2 × 4 y se lleva a `piloto_d`.

## Impresión

- La pieza se imprime como el original, con z 0 sobre la cama. No necesita soportes: el techo de la ventana es un puente de 13 mm con chaflán a 45°, el rebaje está abierto por arriba y los separadores y pilotos son verticales.
- Capa de 0,2 (o 0,16), 4 perímetros y 5 capas arriba y abajo. Pata de elefante de 0,1 a 0,15. La costura, lejos de las jambas.
- Primero se imprimen la prueba del lóbulo y el cupón, y después la base.

## Parámetros y prueba de parametricidad

Lo que se toca a mano está en `parametros-base.json`, sobre todo `separador_d`, `piloto_d`, `tornillo_largo`, `ventana_radio_sup`, `ventana_chaflan_ext`, `rebaje_usb_fondo` y `mecanismo_rebaje`. Si la PCB, la funda o la exclusión cambian, se regenera `geometria.json` en `Hardware/PCB-suelo/` y se vuelve a ejecutar el script.

Prueba hecha con copias de los dos JSON: con `separador_d` = 4,8 y `alturas.corte_sup` = 9,5, la base se regenera y la verificación sale con 0, sin tocar código. Los separadores salen de Ø4,798 (96 lados), la ventana llega a z 9,5, el USB-C queda a 0,39 de la pared, la funda a 0,35 de la base y la malla tiene 1 cuerpo y género 5.

## Verificación

El detalle está en `verificacion.json`. Resultado con los parámetros actuales: **de la A a la I en verde y salida 0**.

| | Comprobación | Resultado |
|-|--------------|-----------|
| A | Cotas z del original | Suelo a 1,90541 en los 20 rayos y cara inferior a 0. Pared del lóbulo de 1,70 a 1,73 en x −80, −73,5 y −67 |
| B | PCB y USB-C frente a la pared | PCB a 0,4997 del original como mínimo (criterio 0,5 ± 0,001), sin vértices dentro del prisma. USB-C a **0,390** de la base en toda la altura (0,090 sin el rebaje; criterio 0,25) |
| C | Malla de salida | Cerrada, normales coherentes, 1 cuerpo, género 4 → 5, sin degenerados |
| D | Volumen | Error de 1e-5 mm³ (ventana 166,75; rebaje fuera de la ventana 49,94) |
| E | Lo no tocado | Distancia máxima 1e-6. Los 4 agujeros siguen pasantes y miden Ø2,130 |
| F | Medidas | Ventana en x −80,00 … −67,00 y z 1,905 … 9,255. Separadores con error de centro ~1e-14, Ø4,998 y cara superior a 3,905. Pilotos de Ø1,799 y 2,70 de profundidad, con 1,205 de suelo debajo |
| G | Exclusiones | 0 mm³ dentro de la exclusión de Ø15,3. Separador a agujero original 9,36 como mínimo; a muesca, 7,43 |
| H | Cable | Funda a 0,334 de la base (criterio 0,3). Cuerpo del USB-C montado a 2,02 |
| I | Apoyo | La PCB apoya en los 4 separadores con una separación de 4e-16 y no corta la base |

## Pendiente

- Siguen pendientes de confirmar los supuestos del plan: el centro y el Ø del mecanismo, la funda del cable real y el Ø de la torreta del cuerpo (las muescas).
- `usb_cuerpo_ancho` y `usb_cuerpo_largo` repiten valores de `contorno_suelo.py`. Convendría que `geometria.json` los exportara.
