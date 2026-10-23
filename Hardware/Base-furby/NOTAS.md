# Base del Furby de 1998 modificada para la PCB del suelo

La base original se modifica lo justo para alojar la PCB de `Hardware/PCB-suelo/`:
- **4 separadores** con piloto para tornillo M2 × 4;
- una **ventana para el USB-C** en la pared trasera del lóbulo;
- un **rebaje interior** encima de la ventana, para que el conector libre la pared al montar la PCB;
- **tapones** en los 4 agujeros originales del suelo, que queda macizo.

Todo lo demás queda igual que en el original.

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
  - Todo lo de la PCB se lee de `Hardware/PCB-suelo/geometria.json`: contorno, taladros, mecanismo con `exclusion_diametro`, `funda`, `muescas`, `usb.*` y `alturas.*`. Las `muescas` son opcionales: si no vienen, vienen a `null`, con `"activas": false` o sin centros ni radio, G no las comprueba y la planta no las dibuja.
  - Lo propio de la base está en `parametros-base.json`.
  - El resto se **mide en el STL**: el z del suelo, las caras de la pared del lóbulo, el hueco interior de la pared y los agujeros originales. El código no lleva cotas.
- **El z del suelo se mide con 20 rayos.** Sale 1,90541 (el valor exacto de la malla) y se compara con `alturas.corte_inf` (1,905). Si se separan más de 0,01, el script aborta.
- **Coplanares:** la ventana corta a ras de la cara superior del suelo y los tapones se unen a ras de sus dos caras. Manifold resuelve bien el género y el volumen, pero deja una docena de astillas de 1e-10 mm². Un `simplify(1e-6)` (`tolerancia_malla`) las colapsa y el volumen cambia en 1e-5 mm³. Si aun así la malla no sale limpia (género, un cuerpo, cerrada y sin degenerados), se repite bajando la ventana `eps_coplanar`. Los tapones no se desplazan, porque tienen que quedar a ras. Hoy no hace falta ninguna de las dos cosas.
- **Las z de los tapones salen de los vértices de la pared de cada agujero** (0 y 1,905411720, el float32 de la malla), no de los rayos, que redondean a 1e-9. Así el tapón es exactamente coplanar con las dos caras del suelo.

## Operaciones

| Feature | Qué hace |
|---------|----------|
| `Separador_H1…H4` | Cilindro de Ø `separador_d`, desde z_suelo − `separador_empotrado` hasta z_pcb_inf (3,905). Se une a la base |
| `Tapon_A1…A4` (`Tapon_Agujeros`) | Solo si `tapar_agujeros_originales`. Cilindro en el centro medido de cada agujero, de Ø agujero + 2 × `tapon_margen` (2,93) y de z 0 a z 1,905, a ras de las dos caras del suelo. Se une a la base |
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

## Agujeros originales del suelo tapados

- **Por qué:** en el Furby al que va la PCB no hay nada en los 4 agujeros originales del suelo (Ø2,13, pasantes). Se tapan para que el suelo quede macizo, y la PCB ya no lleva muescas alrededor de ellos (`fix/pcb-sin-muescas`).
- **Dónde están:** se miden en el STL, en la sección a z 1,0: centros (−105,77; −106,80), (−105,51; −78,23), (−41,33; −78,15) y (−41,23; −106,83), Ø2,130, con el borde a 0,54–0,60 de la pared interior y el centro a 4,25–4,34 del borde exterior de la base. Salen iguales a z 0,3, 1,0 y 1,8, así que la medida es robusta y no hace falta una lista en los parámetros.
- **El tapón:** Ø2,93 (`tapon_margen` = 0,4 por lado), algo mayor que el agujero para que se funda con el suelo de alrededor. Está entero en z 0…1,905, dentro de la planta de la base, así que no puede crear material por fuera ni resaltes. Con `tapon_margen` = 1,0 (Ø4,13, llega bajo la pared) el volumen añadido sigue siendo exactamente el de los huecos.
- **Cómo se comprueba:**
  - C: el género baja 4, de 5 a **1**: solo queda el asa de la ventana.
  - D: los tapones añaden **27,1495 mm³**, igual al volumen de los 4 huecos (error 0). Si sobrara volumen, habría material fuera del suelo.
  - E: 9 rayos verticales por agujero (centro y anillo a 0,9 del radio) entran en z 0 y salen en z 1,905, sin caras intermedias ni nada encima. La cara inferior sigue plana en z 0 y pasa de 5082,00 a **5096,25 mm²** (+14,249, el área de los 4 agujeros). La comprobación de lo no tocado excluye las cajas de los tapones dilatadas 1 mm, como las demás operaciones.
- Con `tapar_agujeros_originales` = false la base vuelve a tener los agujeros pasantes y E comprueba que siguen abiertos y miden Ø2,13.

## Piezas de prueba

- **`prueba-lobulo.stl`**: recorte de x −96 a −50, y −133 a −112 y z 0 a 12, con la ventana, el arranque del rebaje, H3 y H4. Sirve para probar el cable real, el paso del conector junto a la pared y el tornillo antes de imprimir la base entera.
- **`cupon-pilotos.stl`**: placa de 40 × 10 del grosor del suelo con 4 separadores, con pilotos de Ø1,6 / 1,7 / 1,8 / 1,9 cada 10 mm (`cupon_paso`). El de Ø1,6 está junto a la esquina recortada (`cupon_marca`). Se elige el Ø que agarre bien el M2 × 4 y se lleva a `piloto_d`.

## Impresión

- La pieza se imprime como el original, con z 0 sobre la cama. No necesita soportes: el techo de la ventana es un puente de 13 mm con chaflán a 45°, el rebaje está abierto por arriba y los separadores y pilotos son verticales.
- Capa de 0,2 (o 0,16), 4 perímetros y 5 capas arriba y abajo. Pata de elefante de 0,1 a 0,15. La costura, lejos de las jambas.
- Primero se imprimen la prueba del lóbulo y el cupón, y después la base.

## Parámetros y prueba de parametricidad

Lo que se toca a mano está en `parametros-base.json`, sobre todo `separador_d`, `piloto_d`, `tornillo_largo`, `ventana_radio_sup`, `ventana_chaflan_ext`, `rebaje_usb_fondo`, `mecanismo_rebaje`, `tapar_agujeros_originales` y `tapon_margen`. Si la PCB, la funda o la exclusión cambian, se regenera `geometria.json` en `Hardware/PCB-suelo/` y se vuelve a ejecutar el script.

Prueba hecha con copias de los dos JSON: con `separador_d` = 4,8 y `alturas.corte_sup` = 9,5, la base se regenera y la verificación sale con 0, sin tocar código. Los separadores salen de Ø4,798 (96 lados), la ventana llega a z 9,5, el USB-C queda a 0,39 de la pared, la funda a 0,35 de la base y la malla tiene 1 cuerpo y género 1, con los 4 agujeros macizos. Repetida con la `geometria.json` sin muescas. Con `tapar_agujeros_originales` = false también sale con 0: género 5 y agujeros pasantes.

## Verificación

El detalle está en `verificacion.json`. Resultado con los parámetros actuales: **de la A a la I en verde y salida 0**.

| | Comprobación | Resultado |
|-|--------------|-----------|
| A | Cotas z del original | Suelo a 1,90541 en los 20 rayos y cara inferior a 0. Pared del lóbulo de 1,70 a 1,73 en x −80, −73,5 y −67 |
| B | PCB y USB-C frente a la pared | PCB a 0,4997 del original como mínimo (criterio 0,5 ± 0,001), sin vértices dentro del prisma. USB-C a **0,390** de la base en toda la altura (0,090 sin el rebaje; criterio 0,25) |
| C | Malla de salida | Cerrada, normales coherentes, 1 cuerpo, género 4 → 1 (+1 ventana, −4 tapones), sin degenerados |
| D | Volumen | Error de 1e-5 mm³ (ventana 166,75; rebaje fuera de la ventana 49,94; tapones 27,1495, igual a los huecos) |
| E | Lo no tocado | Distancia máxima 8e-7. Los 4 agujeros, macizos de z 0 a 1,905 en los 36 rayos. Cara inferior plana en z 0: 5082,00 → 5096,25 mm² |
| F | Medidas | Ventana en x −80,00 … −67,00 y z 1,905 … 9,255. Separadores con error de centro ~1e-14, Ø4,998 y cara superior a 3,905. Pilotos de Ø1,799 y 2,70 de profundidad, con 1,205 de suelo debajo |
| G | Exclusiones | 0 mm³ dentro de la exclusión de Ø15,3. Separador a agujero original 9,36 como mínimo. `geometria.json` trae `muescas: null`: la comprobación de muescas se salta y se anota |
| H | Cable | Funda a 0,334 de la base (criterio 0,3). Cuerpo del USB-C montado a 2,02 |
| I | Apoyo | La PCB apoya en los 4 separadores con una separación de 4e-16 y no corta la base |

## Pendiente

- Siguen pendientes de confirmar los supuestos del plan: el centro y el Ø del mecanismo y la funda del cable real.
- `usb_cuerpo_ancho` y `usb_cuerpo_largo` repiten valores de `contorno_suelo.py`. Convendría que `geometria.json` los exportara.
