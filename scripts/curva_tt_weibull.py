# -*- coding: utf-8 -*-
"""Escribe la curva acumulada en tiempo térmico (``curva_tt``) con forma Weibull en el ``alerta_lolmu_params.json`` de una app.

    python scripts/curva_tt_weibull.py ruta/alerta_lolmu_params.json [más archivos...]

Solo reemplaza ``tt``, ``media``, ``p10``, ``p90``, ``descripcion`` y ``validacion`` de ``curva_tt``, y agrega ``forma``; el
clima medio de tiempo térmico (``tt_diario_clima*``) queda como está.

Curva: F(TT) = 1 − exp(−(TT/λ)^k), con λ = t50 / ln(2)^(1/k). Vale 0 en las primeras plántulas y sube en S.
Ajuste (noviembre de 2026) con 38 campañas ancladas en las primeras plántulas como en la app: Bordenave 2008–2015,
2018–2022 y 2026; Tres Arroyos, Pergamino, San Pedro y Balcarce (3 cada uno), Azul, Olavarría y Lartigau 2026; UBA
2022–2024; Red DIMA 2024 (6 localidades). La banda usa la misma forma con el t50 de los percentiles 10 y 90 de las campañas.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

T50, K = 357.4, 1.295            # °Cd del 50 % y forma
T50_RAPIDA, T50_LENTA = 192.4, 610.8  # percentiles 10 y 90 del t50 por campaña (curva p90 y p10)
EJE = np.arange(0, 3001, 25)


def weibull(tt: np.ndarray, t50: float, k: float = K) -> np.ndarray:
    lam = t50 / np.log(2) ** (1 / k)
    return 1 - np.exp(-(np.maximum(tt, 0) / lam) ** k)


def curva() -> dict:
    return {
        "tt": EJE.tolist(),
        "media": np.round(weibull(EJE, T50), 4).tolist(),
        "p10": np.round(weibull(EJE, T50_LENTA), 4).tolist(),
        "p90": np.round(weibull(EJE, T50_RAPIDA), 4).tolist(),
        "forma": {"tipo": "weibull", "t50": T50, "k": K, "t50_p10": T50_LENTA, "t50_p90": T50_RAPIDA},
        "descripcion": ("Emergencia acumulada (fracción de la campaña) en función del tiempo térmico desde las primeras "
                        "plántulas (°Cd, base 2, óptima 20, crítica 30 °C). Curva Weibull F = 1 − exp(−(TT/λ)^k), k = 1,295, "
                        "50 % a 357 °Cd (25/75/90 % a 181/610/903 °Cd); banda 10–90 % con el 50 % a 611 y 192 °Cd. Ajustada "
                        "con 38 campañas (Bordenave, apps, UBA y Red DIMA) ancladas en las primeras plántulas."),
        "validacion": {
            "nota": ("Error medio (puntos %) de la emergencia acumulada en los conteos posteriores a las primeras plántulas, "
                     "dejando cada campaña afuera del ajuste: [curva anterior (media de Bordenave), Weibull]. Cobertura de la "
                     "banda 10–90 %: 43 % → 63 % de los conteos."),
            "Todas (38)": [13.7, 12.8], "Apps (15)": [12.7, 11.0], "Bordenave (14)": [12.2, 13.1],
            "UBA (3)": [15.6, 11.3], "Red DIMA 2024 (6)": [19.1, 17.3],
        },
    }


def actualizar(ruta: Path) -> None:
    texto = ruta.read_text(encoding="utf-8")
    p = json.loads(texto)
    p.setdefault("curva_tt", {}).update(curva())
    fin = "\n" if texto.endswith("\n") else ""  # mismo formato que el archivo original
    ruta.write_text(json.dumps(p, ensure_ascii=False, indent=1) + fin, encoding="utf-8")


if __name__ == "__main__":
    for a in sys.argv[1:]:
        actualizar(Path(a)); print("curva Weibull escrita en", a)
