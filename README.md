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
| 1.3.2 | Recuadro de flujos tardíos en invierno: muestra solo el texto de `tardia.recorrida` (recorrer cada 2 semanas para definir uso de graminicida postemergente); el período de la recorrida en la ayuda y el Excel sale de los parámetros (ahora 1/08–1/10). |
| 1.3.3 | Sin referencias a la calibración en Bordenave en las apps de otras localidades: título de la alerta sin «(modelo calibrado en Bordenave)»; la curva y la ayuda hablan del «calendario de referencia regional». |
| 1.4.0 | Ayuda a la decisión: recuadro «Qué hacer esta semana» arriba de la alerta (y en el Excel); la ventana de 600–800 °Cd pasa a ser la del **graminicida de barbecho** (raigrás de 4 a 6 macollos) en tarjetas, gráfico y Excel; lluvia para activar el residual (registrada y pronosticada en los 7 días desde la siembra, ≥ 10 mm); recuadro de julio (entre el aviso de flujos tardíos y la recorrida): la emergencia de la siembra se controla con el residual. |
| 1.4.1 | Flujos tardíos solo del 1/08 al 1/10 (recorrida cada 2 semanas): se quitan el recuadro de probabilidad de mayo–junio y el de julio, porque ese período lo cubre el riesgo para el residual; también de la ayuda, el resumen y el Excel. |
| 1.5.0 | Nuevo `lolium_comun.pagina` (encabezado, barra lateral, clima del repositorio y descarga en Excel): las apps dejan de ejecutar el motor PREDWEEM (red neuronal y balance hídrico) y muestran solo la alerta. |
| 1.6.0 | Control de ingreso con **registro libre** (`registro_libre = true`): cualquier cuenta de Google entra sin aprobación; opcionalmente cada ingreso se anota en un formulario de Google (`[acceso.registro]`). |
| 1.7.0 | Recuadro «Muestreo hasta el inicio»: «a esta fecha, en el X % de las 31 campañas de la región ya se habían visto las primeras plántulas» (y cuándo se llega al 90 %). Se usa la distribución regional porque una fecha propia por sitio predijo peor (13,9 contra 11,6 días). Se quita la mención al motor PREDWEEM del subtítulo de la alerta. |
| 1.8.0 | Orden cronológico de la temporada: qué hacer esta semana → muestreo hasta el inicio → alerta de grandes flujos y graminicida de barbecho → residual a la siembra → flujos tardíos (agosto–octubre); los puntos de «Qué hacer» siguen el mismo orden. |
| 1.9.0 | El residual se muestra recién con la fecha de siembra prevista cargada (recuadro, fila «Residual» del semáforo y Excel); sin fecha, una línea invita a cargarla. Ya no se muestra la siembra de referencia del 1/06. |
| 1.10.0 | «Muestreo hasta el inicio» con tacómetro: % de las 31 campañas de la región con primeras plántulas ya vistas a la fecha de emisión, con la ventana habitual del inicio (p10–mediana–p90) marcada; al lado, qué hacer (recorrer, lluvias, último conteo en cero). |
| 1.11.0 | Curva acumulada en tiempo térmico con forma Weibull (`scripts/curva_tt_weibull.py` la escribe en el `alerta_lolmu_params.json` de cada app): arranca en 0 % en las primeras plántulas, 50 % a 357 °Cd, sin la cola larga de la media anterior; validada en 38 campañas dejando cada una afuera (error del acumulado 13,7 → 12,8 puntos; banda 10–90 % con 63 % de cobertura contra 43 %). La fracción inicial del calendario anclado a las primeras plántulas (17,97 %, apps de Tres Arroyos, Balcarce y Azul) pasa a ser un valor propio (`fraccion_inicial_primeras`), así esas apps no cambian. |
| 1.12.0 | Residual en siembras desde el 15/06: si hay conteos en los 30 días previos a la siembra, el nivel sale de esas plántulas (`riesgo_residual_reciente`; ≥ 20 pl/m² = alto); el riesgo histórico queda de referencia. En 38 campañas, para siembras de julio la tabla histórica no anticipaba el año (AUC 0,43; detectaba 20 % de los casos con ≥ 20 pl/m² en la ventana) y la emergencia reciente sí (AUC 0,75; 75 % detectados, 65 % de especificidad; cada conteo se prorratea según los días de su intervalo dentro de los 30 días). Sin conteos recientes, el recuadro pide un conteo 2–4 semanas antes de sembrar. |
| 1.2.0 | La fecha de siembra prevista se marca en el gráfico con una línea y una flecha con cartel. Se quitan de la app las menciones a «17 campañas» (título de la alerta, curvas y textos). |
| 1.1.0 | Dato opcional «Infestación de raigrás del lote» (baja / media / alta): el riesgo para el residual en pl/m² se calcula con esa densidad en lugar de la del sitio, con recomendaciones acordes (medio: residual opcional; bajo: no hace falta). |
| 1.0.0 | Primera versión: código de las 8 apps al 13/11/2026. |
