"""Fija una versión de LOLIUM-COMUN en las apps de Lolium y copia los archivos puente.

Uso (con las apps clonadas en la misma carpeta que este repositorio):

    python scripts/actualizar_apps.py v1.1.0            # etiqueta creada en GitHub
    python scripts/actualizar_apps.py 4367380… v1.0.0   # commit completo (40 caracteres) y versión como comentario

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


def main(version: str, comentario: str = "", base: Path = RAIZ.parent) -> None:
    for app in APPS:
        d = base / app
        if not d.is_dir():
            print(f"{app}: no está en {base}, se omite")
            continue
        req = d / "requirements.txt"
        lineas = [x for x in req.read_text(encoding="utf-8").splitlines() if not re.match(r"\s*lolium-comun\b", x)]
        linea = LINEA.format(v=version) + (f"  # {comentario}" if comentario else "")
        req.write_text("\n".join(lineas + [linea]) + "\n", encoding="utf-8")
        for f in (RAIZ / "puentes").glob("*.py"):
            shutil.copy(f, d / f.name)
        print(f"{app}: lolium-comun {comentario or version}")


if __name__ == "__main__":
    args = sys.argv[1:]
    ok = (len(args) == 1 and args[0].startswith("v")) or (len(args) == 2 and re.fullmatch(r"[0-9a-f]{40}", args[0]))
    if not ok:
        sys.exit("Uso: python scripts/actualizar_apps.py vX.Y.Z   o   python scripts/actualizar_apps.py <commit de 40 caracteres> vX.Y.Z")
    main(*args)
