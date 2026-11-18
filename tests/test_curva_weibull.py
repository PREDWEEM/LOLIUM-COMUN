"""Curva acumulada Weibull en tiempo térmico (1.11.0) y fracción inicial del calendario anclado."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lolium_comun import alerta_lolmu as al
from lolium_comun import visualizacion_alerta_lolmu as vis

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("curva_tt_weibull", RAIZ / "scripts" / "curva_tt_weibull.py")
cw = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(cw)


def test_forma_weibull():
    c = cw.curva()
    tt, m, lo, hi = (np.array(c[k]) for k in ("tt", "media", "p10", "p90"))
    assert abs(m[0] - 0.15) < 0.01 and lo[0] < m[0] < hi[0]  # al ver las primeras plántulas ya nació ~15 %
    assert np.all(np.diff(m) >= 0) and np.all(lo <= m) and np.all(m <= hi)
    for p, objetivo in ((0.25, 89), (0.5, 294), (0.75, 544), (0.9, 800)):
        assert abs(np.interp(p, m, tt) - objetivo) < 15


def test_curva_tiempo_termico_con_weibull(tmp_path, monkeypatch):
    base = json.loads((RAIZ / "tests" / "datos" / "alerta_lolmu_params_bordenave.json").read_text(encoding="utf-8"))
    archivo = tmp_path / "p.json"; archivo.write_text(json.dumps(base), encoding="utf-8")
    cw.actualizar(archivo)
    nuevo = json.loads(archivo.read_text(encoding="utf-8"))
    assert nuevo["curva_tt"]["tt_diario_clima"] == base["curva_tt"]["tt_diario_clima"]  # el clima medio no se toca
    monkeypatch.setenv("LOLIUM_ALERTA_PARAMS", str(archivo))
    m = al.AlertaLolmu()
    prim = pd.Timestamp("2026-03-01")
    dg = pd.Series(10.0, index=pd.date_range("2026-01-01", "2026-09-30"))  # 10 °Cd por día
    c = m.curva_tiempo_termico(dg, prim, pd.DatetimeIndex([prim, prim + pd.Timedelta(days=36)]))
    assert abs(c["media"].iloc[0] - 0.15) < 0.01
    assert abs(c["media"].iloc[1] - 0.57) < 0.02  # 360 °Cd desde las primeras plántulas ≈ 57 %


def test_fraccion_inicial_del_calendario_no_cambia():
    # antes salía de curva_tt.media[0] de los parámetros de las apps (0,1797); ahora es un valor propio con el mismo número
    base = json.loads((RAIZ / "tests" / "datos" / "alerta_lolmu_params_bordenave.json").read_text(encoding="utf-8"))
    assert vis.FRACCION_INICIAL_PRIMERAS == base["curva_tt"]["media"][0]
