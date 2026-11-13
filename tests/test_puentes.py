"""Los archivos puente de ``puentes/`` hacen que una app use el paquete sin cambiar sus ``import``."""
import importlib
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = Path(__file__).parent / "datos"


def test_app_con_puentes(tmp_path):
    for f in (RAIZ / "puentes").glob("*.py"):
        shutil.copy(f, tmp_path)
    shutil.copy(DATOS / "alerta_lolmu_params_bordenave.json", tmp_path / "alerta_lolmu_params.json")
    codigo = (
        "import importlib, os, sys\n"
        "import alerta_lolmu, visualizacion_alerta_lolmu, acceso_predweem\n"
        "import lolium_comun.alerta_lolmu as m\n"
        "assert alerta_lolmu is m\n"
        "assert visualizacion_alerta_lolmu.al is m\n"
        "assert acceso_predweem.__name__ == 'lolium_comun.acceso_predweem'\n"
        "assert os.environ['LOLIUM_ALERTA_PARAMS'].endswith('alerta_lolmu_params.json')\n"
        "importlib.reload(alerta_lolmu); importlib.reload(visualizacion_alerta_lolmu)\n"
        "assert alerta_lolmu.AlertaLolmu().p['residual']['sitio'] == 'Bordenave'\n"
        "print('ok')\n"
    )
    env = {k: v for k, v in __import__("os").environ.items() if k != "LOLIUM_ALERTA_PARAMS"}
    out = subprocess.run([sys.executable, "-c", codigo], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"
