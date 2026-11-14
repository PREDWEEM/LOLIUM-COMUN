"""Módulo común de las apps de Lolium multiflorum de PREDWEEM.

* ``alerta_lolmu``: alerta validada de flujos de emergencia, flujos tardíos y riesgo para el residual a la siembra.
* ``visualizacion_alerta_lolmu``: recuadros, gráficos y reporte de la alerta en Streamlit.
* ``acceso_predweem``: control de acceso (ingreso con Google y usuarios aprobados).

Cada app conserva sus parámetros en ``alerta_lolmu_params.json`` y usa este paquete a través de archivos puente con los
mismos nombres (ver ``puentes/``).
"""

__version__ = "1.3.3"
