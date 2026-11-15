"""Control de acceso: modo registro libre y anotación de ingresos."""
from types import SimpleNamespace

import pytest

from lolium_comun import acceso_predweem as ac


class _Usuario(dict):
    pass


class _Parar(Exception):
    pass


@pytest.fixture
def st_falso(monkeypatch):
    estado = {}
    falso = SimpleNamespace(
        secrets={}, session_state=estado, user=_Usuario(is_logged_in=True, email="Ana@Ejemplo.com", name="Ana"),
        stop=lambda: (_ for _ in ()).throw(_Parar()), set_page_config=lambda **k: None, markdown=lambda *a, **k: None,
        info=lambda *a, **k: None, button=lambda *a, **k: None, caption=lambda *a, **k: None, warning=lambda *a, **k: None,
        error=lambda *a, **k: None, link_button=lambda *a, **k: None, login=None, logout=None)
    monkeypatch.setattr(ac, "st", falso)
    return falso


def test_sin_configurar_queda_abierta(st_falso):
    ac.requerir_acceso("Bordenave")  # no corta


def test_registro_libre_deja_entrar_y_anota_una_vez(st_falso, monkeypatch):
    st_falso.secrets = {"acceso": {"activo": True, "registro_libre": True,
                                   "registro": {"url": "https://example.com/formResponse", "email": "entry.1", "app": "entry.3"}}}
    enviados = []
    monkeypatch.setattr(ac.urllib.request, "urlopen", lambda req, timeout: enviados.append(req.data) or SimpleNamespace(read=lambda: b""))
    ac.requerir_acceso("Balcarce")
    ac.requerir_acceso("Balcarce")
    assert len(enviados) == 1 and b"entry.1=Ana%40Ejemplo.com" in enviados[0] and b"entry.3=Balcarce" in enviados[0]


def test_registro_libre_sin_ingresar_pide_login(st_falso):
    st_falso.secrets = {"acceso": {"activo": True, "registro_libre": True}}
    st_falso.user = _Usuario(is_logged_in=False)
    with pytest.raises(_Parar):
        ac.requerir_acceso("Azul")


def test_con_aprobacion_bloquea_no_aprobados(st_falso, monkeypatch):
    st_falso.secrets = {"acceso": {"activo": True, "administradores": ["otro@ejemplo.com"]}}
    monkeypatch.setattr(ac, "_leer_planilla", SimpleNamespace(clear=lambda: None))
    with pytest.raises(_Parar):
        ac.requerir_acceso("Azul")


def test_falla_del_formulario_no_corta(st_falso, monkeypatch):
    st_falso.secrets = {"acceso": {"activo": True, "registro_libre": True, "registro": {"url": "https://x/formResponse", "email": "entry.1"}}}
    def _falla(*a, **k):
        raise OSError("sin red")
    monkeypatch.setattr(ac.urllib.request, "urlopen", _falla)
    ac.requerir_acceso("Pergamino")
