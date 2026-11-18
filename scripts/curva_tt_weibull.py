# -*- coding: utf-8 -*-
"""Escribe la curva acumulada en tiempo térmico (``curva_tt``) con forma Weibull en el ``alerta_lolmu_params.json`` de una app.

    python scripts/curva_tt_weibull.py ruta/alerta_lolmu_params.json [más archivos...]

Solo reemplaza ``tt``, ``media``, ``p10``, ``p90``, ``descripcion`` y ``validacion`` de ``curva_tt``, y agrega ``forma``; el
clima medio de tiempo térmico (``tt_diario_clima*``) queda como está.

Curva: F(TT) = 1 − exp(−((TT + TT0)/λ)^k), con λ = t50 / ln(2)^(1/k). TT0 corre el origen hacia atrás: cuando se ven las
primeras plántulas ya nació una parte de la campaña (15 %), así que el cero de la curva es anterior a esa fecha.
Ajuste (noviembre de 2026) con 38 campañas ancladas en las primeras plántulas como en la app: Bordenave 2008–2015,
2018–2022 y 2026; Tres Arroyos, Pergamino, San Pedro y Balcarce (3 cada uno), Azul, Olavarría y Lartigau 2026; UBA
2022–2024; Red DIMA 2024 (6 localidades). La banda usa la misma forma con el t50 de los percentiles 10 y 90 de las campañas.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

T50, K, TT0 = 528.0, 1.786, 234.0    # escala (°Cd desde el origen), forma y origen anterior a las primeras plántulas
T50_RAPIDA, T50_LENTA = 302.0, 838.0  # percentiles 10 y 90 de la escala por campaña (curva p90 y p10)
EJE = np.arange(0, 3001, 25)


def weibull(tt: np.ndarray, t50: float, k: float = K, tt0: float = TT0) -> np.ndarray:
    lam = t50 / np.log(2) ** (1 / k)
    return 1 - np.exp(-(np.maximum(np.asarray(tt, float) + tt0, 0) / lam) ** k)


def curva() -> dict:
    return {
        "tt": EJE.tolist(),
        "media": np.round(weibull(EJE, T50), 4).tolist(),
        "p10": np.round(weibull(EJE, T50_LENTA), 4).tolist(),
        "p90": np.round(weibull(EJE, T50_RAPIDA), 4).tolist(),
        "forma": {"tipo": "weibull", "t50": T50, "k": K, "tt0": TT0, "t50_p10": T50_LENTA, "t50_p90": T50_RAPIDA},
        "descripcion": ("Emergencia acumulada (fracción de la campaña) en función del tiempo térmico desde las primeras "
                        "plántulas (°Cd, base 2, óptima 20, crítica 30 °C). Curva Weibull con el origen 234 °Cd antes de las "
                        "primeras plántulas, F = 1 − exp(−((TT + 234)/λ)^k), k = 1,786: al ver las primeras plántulas ya nació "
                        "el 15 %, y 25/50/75/90 % a 89/294/544/800 °Cd. Ajustada con 40 campañas (Bordenave, apps, UBA, Red DIMA, "
                        "Cabildo y Frapal) ancladas en la fecha en que se ven las primeras plántulas."),
        "validacion": {
            "nota": ("Error medio (puntos %) de la emergencia acumulada desde la fecha en que se ven las primeras plántulas, "
                     "40 campañas: [Weibull desde 0 (1.11), Weibull con origen anterior (1.13)]. Dejando cada campaña afuera: "
                     "14,3 → 13,7. Anclando en la mitad entre el último cero y el primer conteo con plantas (la app con "
                     "conteos), las dos dan 13,1–13,5. Banda 10–90 %: 65 % de los conteos."),
            "Todas (40)": [14.7, 13.4], "Apps (15)": [12.8, 10.5], "Bordenave (14)": [13.1, 14.2],
            "Cabildo y Frapal 2020 (2)": [30.2, 22.9],
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
