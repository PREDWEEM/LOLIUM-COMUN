"""Pruebas del módulo común con los parámetros y el clima 2026 de Bordenave.

Los valores de referencia se obtuvieron con ``alerta_lolmu.py`` de las apps (13/11/2026), antes de pasar al paquete:
el módulo común tiene que dar exactamente lo mismo.
"""
import importlib

import pandas as pd
import pytest

from lolium_comun import alerta_lolmu as al

PRIMERAS = pd.Timestamp("2026-03-10")
CONTEOS = pd.DataFrame({"Fecha": pd.to_datetime(["2026-03-03", "2026-03-10", "2026-03-17"]), "PLM2": [0, 12, 40]})
# fecha: [(probabilidad, nivel de información, probabilidad tardía) solo clima, + primeras plántulas, + conteos]
REFERENCIA = {
    "2026-03-01": [(0.37557072, 1, None), (0.37557072, 1, None), (0.37557072, 1, None)],
    "2026-04-15": [(0.45242443, 1, None), (0.53112599, 2, None), (0.68033326, 3, None)],
    "2026-05-20": [(0.24371221, 1, 0.41059949), (0.31324515, 2, 0.64293892), (0.5307243, 3, 0.94866641)],
}


@pytest.mark.parametrize("fecha", sorted(REFERENCIA))
def test_evaluar_igual_a_las_apps(meteo, fecha):
    f = pd.Timestamp(fecha)
    res = [al.evaluar(meteo, f), al.evaluar(meteo, f, primeras_plantulas=PRIMERAS),
           al.evaluar(meteo, f, primeras_plantulas=PRIMERAS, conteos=CONTEOS)]
    for r, (p, nivel, pt) in zip(res, REFERENCIA[fecha]):
        assert r["probabilidad"] == pytest.approx(p, abs=1e-7)
        assert r["nivel_info"] == nivel
        assert (r["probabilidad_tardia"] is None) if pt is None else r["probabilidad_tardia"] == pytest.approx(pt, abs=1e-7)
        assert 0 <= r["probabilidad"] <= 1


def test_niveles_de_alerta():
    assert al.nivel_de(0.10) == "baja" and al.nivel_de(0.15) == "atencion" and al.nivel_de(0.25) == "alerta"


@pytest.mark.parametrize("valor,nivel", [(60, "Muy alto"), (50, "Muy alto"), (20, "Alto"), (19.9, "Medio"), (5, "Medio"), (4.9, "Bajo")])
def test_nivel_residual_plm2(valor, nivel):
    assert al.nivel_residual(valor, al.NIVELES_PLM2) == nivel


def test_riesgo_residual_bordenave():
    r = al.riesgo_residual(pd.Timestamp("2026-06-01"))
    assert r["ventana"] == (-10, 45) and r["por_densidad"] and r["fuente"] == "local" and r["n"] == 17
    assert r["residual"]["nivel"] == "Muy alto" and r["residual"]["plm2"] == pytest.approx(56.3, abs=0.5)
    assert al.riesgo_residual(pd.Timestamp("2026-03-01")) is None  # fuera de la ventana de siembra


def test_params_por_variable_de_entorno(tmp_path, monkeypatch):
    destino = tmp_path / "alerta_lolmu_params.json"
    destino.write_text(al.archivo_params().read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv(al.ENV_PARAMS, str(destino))
    assert al.archivo_params() == destino and al.AlertaLolmu().p["calendario"]


def test_recarga_conserva_los_parametros():
    """Las apps recargan el módulo en cada ejecución (importlib.reload): tiene que seguir encontrando los parámetros."""
    antes = al.AlertaLolmu().p["modelos"]
    assert importlib.reload(al).AlertaLolmu().p["modelos"] == antes
