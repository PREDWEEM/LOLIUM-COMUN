from pathlib import Path

import pandas as pd
import pytest

DATOS = Path(__file__).parent / "datos"


@pytest.fixture(autouse=True)
def params_bordenave(monkeypatch):
    """Usa los parámetros de Bordenave en todas las pruebas."""
    monkeypatch.setenv("LOLIUM_ALERTA_PARAMS", str(DATOS / "alerta_lolmu_params_bordenave.json"))


@pytest.fixture
def meteo():
    return pd.read_csv(DATOS / "meteo_bordenave_2026.csv")
