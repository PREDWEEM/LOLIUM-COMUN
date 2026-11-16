import pandas as pd

from lolium_comun.visualizacion_alerta_lolmu import PLANTULAS_VISTAS_REGION, _texto_inicio_acumulado


def test_porcentajes_conocidos():
    assert len(PLANTULAS_VISTAS_REGION) == 31
    assert "<b>52 %</b>" in _texto_inicio_acumulado(pd.Timestamp("2026-03-01"))
    assert "<b>16 %</b>" in _texto_inicio_acumulado(pd.Timestamp("2026-02-15"))
    assert "hacia el 29/03, en el 90 %" in _texto_inicio_acumulado(pd.Timestamp("2026-03-01"))
    assert "hacia el" not in _texto_inicio_acumulado(pd.Timestamp("2026-04-01"))


def test_extremos():
    assert "ninguna" in _texto_inicio_acumulado(pd.Timestamp("2026-01-10"))
    assert "más tardío que todos" in _texto_inicio_acumulado(pd.Timestamp("2026-04-20"))
    assert "<b>" in _texto_inicio_acumulado(pd.Timestamp("2027-02-28"))  # año no bisiesto
