# LOLIUM-COMUN

Módulo común de las 8 apps de *Lolium multiflorum* de PREDWEEM (Bordenave, Lartigau, Tres Arroyos, Azul, Olavarría,
Balcarce, Pergamino y San Pedro). Reúne el código que antes se copiaba a mano en cada app:

| Módulo | Contenido |
|---|---|
| `lolium_comun.alerta_lolmu` | Alerta validada de grandes flujos (≥ 5 % de la campaña en 7 días) por niveles de información, flujos tardíos (1/05–30/06), recorridas de julio a septiembre y riesgo para el residual a la siembra (ventana de −10 a +45 días, niveles en pl/m², con la densidad del sitio o la infestación del lote informada: baja ≈ 200, media ≈ 1.000, alta ≈ 4.000 pl/m² por campaña) |
| `lolium_comun.visualizacion_alerta_lolmu` | Tarjetas, recuadros, gráficos y reporte Excel de la alerta en Streamlit |
| `lolium_comun.acceso_predweem` | Control de acceso (ingreso con Google y usuarios aprobados) |

Lo propio de cada sitio **no** está acá: cada app conserva su `alerta_lolmu_params.json` (calendario, coeficientes,
historia local, tabla del residual) y su clima.

## Cómo lo usa cada app

1. `requirements.txt` fija la versión, por commit (con la versión como comentario) o por etiqueta:

   ```
   lolium-comun @ git+https://github.com/PREDWEEM/LOLIUM-COMUN@<commit>  # v1.0.0
   lolium-comun @ git+https://github.com/PREDWEEM/LOLIUM-COMUN@v1.1.0
   ```

2. Los archivos `alerta_lolmu.py`, `visualizacion_alerta_lolmu.py` y `acceso_predweem.py` de la app son **puentes**
   (copias de `puentes/`): indican dónde están los parámetros de la app (variable de entorno `LOLIUM_ALERTA_PARAMS`) y hacen
   que `import alerta_lolmu` devuelva el módulo común. El resto del código de la app no cambia, incluido el
   `importlib.reload` que evita usar una versión vieja en memoria.

## Cómo hacer un cambio

1. Cambiar el código en `src/lolium_comun/`, agregar o ajustar pruebas en `tests/` y correr `pytest`.
2. Subir la versión en `pyproject.toml` y en `src/lolium_comun/__init__.py` y fusionar en `main`. Opcional: crear la
   etiqueta o *release* `v1.1.0` en GitHub (Releases → Draft a new release).
3. Con las apps clonadas al lado de este repositorio: `python scripts/actualizar_apps.py v1.1.0` (si hay etiqueta) o
   `python scripts/actualizar_apps.py <commit> v1.1.0`; revisar y abrir un PR en cada app. Al fusionarlo, Streamlit Cloud
   reinstala el paquete con la versión nueva.

Cada app queda fijada a una versión: un cambio en `main` no llega a las apps hasta que se actualiza su `requirements.txt`,
así se puede probar en una app antes de pasarlo a las demás.

## Pruebas

`pytest` corre con los parámetros y el clima 2026 de Bordenave (`tests/datos/`). Verifica que la alerta dé exactamente los
mismos valores que el código de las apps antes de pasar al paquete, los niveles del residual, la lectura de parámetros
(incluida la recarga del módulo) y que una app con los puentes use el paquete. GitHub Actions las corre en cada PR.

## Visibilidad

Streamlit Cloud instala el paquete con `pip` desde GitHub, así que este repositorio tiene que ser **público** mientras las
apps lo usen de esta forma. Si se privatiza, hay que dar acceso a pip con un token (por ejemplo,
`git+https://<token>@github.com/...` cargado desde los secretos de Streamlit) o volver a copiar los archivos en cada app.

## Propiedad intelectual

Ver `COPYRIGHT.md`. Copyright © 2026 Guillermo R. Chantre / PREDWEEM. Todos los derechos reservados.

## Versiones

| Versión | Cambios |
|---|---|
| 1.3.0 | En el semáforo semanal, la fila «Flujos tardíos» se reemplaza por «Residual (siembra)»: para cada semana del 1/05 al 31/07, el riesgo para el residual si se siembra esa semana (rojo: alto o muy alto, ≥ 20 pl/m²; amarillo: medio, 5–20; verde: bajo, < 5), con la infestación del lote si se indicó. El recuadro de flujos tardíos sigue igual. |
| 1.3.1 | Semáforo del residual: con fecha de siembra cargada, las semanas empiezan ese día, así la celda de la siembra coincide con el recuadro del residual (antes la celda se calculaba con el primer día de una semana fija y podía mostrar otro nivel). El recuadro usa los mismos colores que el semáforo (alto en rojo). |
| 1.2.0 | La fecha de siembra prevista se marca en el gráfico con una línea y una flecha con cartel. Se quitan de la app las menciones a «17 campañas» (título de la alerta, curvas y textos). |
| 1.1.0 | Dato opcional «Infestación de raigrás del lote» (baja / media / alta): el riesgo para el residual en pl/m² se calcula con esa densidad en lugar de la del sitio, con recomendaciones acordes (medio: residual opcional; bajo: no hace falta). |
| 1.0.0 | Primera versión: código de las 8 apps al 13/11/2026. |
