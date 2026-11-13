"""Fija una versión de LOLIUM-COMUN en las apps de Lolium y copia los archivos puente.

Uso (con las apps clonadas en la misma carpeta que este repositorio):

    python scripts/actualizar_apps.py v1.1.0

En cada app reemplaza (o agrega) la línea de ``lolium-comun`` en ``requirements.txt`` y copia ``puentes/*.py``. No hace
commit: revisar los cambios y abrir un PR en cada app.
"""
import re
import shutil
import sys
from pathlib import Path

APPS = ["lolium_bor2026", "lolium_lartigau-2026", "loliumta_2026", "lolium_azul2026", "lolium_olava2026",
        "lolium_bal2026", "lolium-perga2026", "lolium_sanpedro2026"]
RAIZ = Path(__file__).resolve().parents[1]
LINEA = "lolium-comun @ git+https://github.com/PREDWEEM/LOLIUM-COMUN@{v}"


def main(version: str, base: Path = RAIZ.parent) -> None:
    for app in APPS:
        d = base / app
        if not d.is_dir():
            print(f"{app}: no está en {base}, se omite")
            continue
        req = d / "requirements.txt"
        lineas = [x for x in req.read_text(encoding="utf-8").splitlines() if not re.match(r"\s*lolium-comun\b", x)]
        req.write_text("\n".join(lineas + [LINEA.format(v=version)]) + "\n", encoding="utf-8")
        for f in (RAIZ / "puentes").glob("*.py"):
            shutil.copy(f, d / f.name)
        print(f"{app}: lolium-comun {version}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].startswith("v"):
        sys.exit("Uso: python scripts/actualizar_apps.py vX.Y.Z")
    main(sys.argv[1])
