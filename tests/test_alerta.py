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


@pytest.mark.parametrize("inf,densidad", [("Baja", 200), ("Media", 1000), ("Alta", 4000)])
def test_residual_con_infestacion_del_lote(inf, densidad):
    sin = al.riesgo_residual(pd.Timestamp("2026-06-01"))
    con = al.riesgo_residual(pd.Timestamp("2026-06-01"), infestacion=inf)
    assert con["infestacion"] == inf and con["densidad_lote"] == densidad
    assert con["residual"]["mediana"] == sin["residual"]["mediana"]  # misma fracción de la campaña
    assert con["residual"]["plm2"] == pytest.approx(sin["residual"]["mediana"] * densidad)
    assert con["residual"]["nivel"] == al.nivel_residual(con["residual"]["plm2"], al.NIVELES_PLM2)


def test_infestacion_ordena_el_riesgo():
    orden = ["Bajo", "Medio", "Alto", "Muy alto"]
    niv = [orden.index(al.riesgo_residual(pd.Timestamp("2026-07-01"), infestacion=i)["residual"]["nivel"]) for i in ("Baja", "Media", "Alta")]
    assert niv == sorted(niv)
    assert al.riesgo_residual(pd.Timestamp("2026-06-01"), infestacion=None)["infestacion"] is None


# ---- 1.12.0: riesgo del residual con la emergencia de los 30 días previos (siembras desde el 15/06) ----
def _cont(fechas, plm2):
    return pd.DataFrame({"Fecha": pd.to_datetime(fechas), "PLM2": plm2})


def test_residual_reciente_usa_los_30_dias_previos():
    c = _cont(["2026-05-20", "2026-06-20", "2026-07-01", "2026-07-08"], [500, 10, 8, 6])
    r = al.riesgo_residual_reciente(pd.Timestamp("2026-07-10"), c)
    assert r["plm2"] == 24 and r["nivel"] == "Alto" and r["n_conteos"] == 3 and r["completo"]


def test_residual_reciente_solo_conteos_hechos_y_siembras_tardias():
    c = _cont(["2026-06-25", "2026-07-08"], [3, 60])
    # emisión antes del último conteo: solo cuenta lo que ya se sabe
    r = al.riesgo_residual_reciente(pd.Timestamp("2026-07-10"), c, emision=pd.Timestamp("2026-07-01"))
    assert r["plm2"] == 3 and r["nivel"] == "Bajo" and not r["completo"]
    assert al.riesgo_residual_reciente(pd.Timestamp("2026-06-01"), c) is None  # antes del 15/06: riesgo histórico
    assert al.riesgo_residual_reciente(pd.Timestamp("2026-07-10"), None) is None
    assert al.riesgo_residual_reciente(pd.Timestamp("2026-09-10"), c) is None  # sin conteos en los 30 días previos


def test_con_reciente_conserva_el_historico():
    rr = al.riesgo_residual(pd.Timestamp("2026-07-15"))
    rec = al.riesgo_residual_reciente(pd.Timestamp("2026-07-15"), _cont(["2026-07-01", "2026-07-10"], [40, 30]))
    out = al.con_reciente(rr, rec)
    assert out["residual"]["nivel"] == "Muy alto" and out["residual"]["nivel_historico"] == rr["residual"]["nivel"]
    assert out["reciente"] is rec and rr["residual"].get("nivel_historico") is None  # no modifica el original
    assert al.con_reciente(rr, None) is rr
