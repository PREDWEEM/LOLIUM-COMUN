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


# ---------------------------------------------------------------- acceso combinado (1.15)
class _Form:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def st_login(st_falso, monkeypatch):
    """st falso sin usuario conectado, con botones y formulario registrados."""
    st_falso.user = _Usuario(is_logged_in=False)
    st_falso.botones, st_falso.entradas, st_falso.enviar = [], {}, False
    st_falso.button = lambda texto, **k: st_falso.botones.append((texto, k.get("args"))) or False
    st_falso.form = lambda *a, **k: _Form()
    st_falso.text_input = lambda etiqueta, **k: st_falso.entradas.get(etiqueta, "")
    st_falso.form_submit_button = lambda *a, **k: st_falso.enviar
    st_falso.rerun = lambda: None
    monkeypatch.setattr(ac, "_intentos", lambda d={}: d)  # intentos en memoria, limpios por test
    ac._intentos().clear()
    return st_falso


def test_hash_contrasena():
    h = ac.hash_contrasena("una clave larga")
    assert h.startswith("scrypt$") and ac.verificar_contrasena("una clave larga", h)
    assert not ac.verificar_contrasena("otra clave", h)
    assert not ac.verificar_contrasena("x", "basura") and h != ac.hash_contrasena("una clave larga")


def test_usuarios_desde_csv_respeta_estado():
    h = ac.hash_contrasena("clave12345")
    u = ac.usuarios_desde_csv(f"usuario,hash,nombre,estado\nAna,{h},Ana A,aprobado\nbeto,{h},Beto,baja\n,{h},x,\n")
    assert list(u) == ["ana"] and u["ana"]["nombre"] == "Ana A"


def test_contrasena_entra_y_baja_corta_la_sesion(st_login):
    h = ac.hash_contrasena("clave12345")
    st_login.secrets = {"acceso": {"activo": True, "usuarios": {"jperez": {"nombre": "Juan", "hash": h}}}}
    st_login.entradas, st_login.enviar = {"Usuario": "JPerez", "Contraseña": "clave12345"}, True
    with pytest.raises(_Parar):
        ac.requerir_acceso("Azul")  # ingresa y la app se vuelve a ejecutar
    assert st_login.session_state[ac._SESION]["usuario"] == "jperez"
    st_login.enviar = False
    ac.requerir_acceso("Azul")  # ya conectado: pasa
    st_login.secrets = {"acceso": {"activo": True, "usuarios": {"jperez": {"hash": h, "estado": "baja"}}}}
    with pytest.raises(_Parar):
        ac.requerir_acceso("Azul")
    assert ac._SESION not in st_login.session_state


def test_bloqueo_tras_intentos_fallidos(st_login):
    cfg = {"usuarios": {"ana": {"hash": ac.hash_contrasena("clave12345")}}}
    for _ in range(ac._INTENTOS_MAX):
        assert ac.ingresar_con_contrasena(cfg, "ana", "mala") == "Usuario o contraseña incorrectos."
    assert "Demasiados intentos" in ac.ingresar_con_contrasena(cfg, "ana", "clave12345")
    n, desde = ac._intentos()["ana"]
    ac._intentos()["ana"] = (n, desde - ac._BLOQUEO_SEG - 1)  # pasó el bloqueo
    assert ac.ingresar_con_contrasena(cfg, "ana", "clave12345") is None


def test_pantalla_con_proveedores_y_contrasena(st_login):
    st_login.secrets = {"acceso": {"activo": True, "proveedores": ["microsoft", "google"],
                                   "textos": {"microsoft": "Ingresar con la cuenta de la empresa"},
                                   "usuarios": {"ana": {"hash": ac.hash_contrasena("clave12345")}}}}
    with pytest.raises(_Parar):
        ac.requerir_acceso("Bordenave")
    assert st_login.botones[:2] == [("Ingresar con la cuenta de la empresa", ("microsoft",)), ("Ingresar con Google", ("google",))]


def test_dominio_aprobado_con_cuenta_microsoft_sin_email(st_falso, monkeypatch):
    st_falso.user = _Usuario(is_logged_in=True, preferred_username="Ana.Gomez@Region.Empresa.com", name="Ana")
    st_falso.secrets = {"acceso": {"activo": True, "proveedores": ["microsoft"], "dominios_aprobados": ["empresa.com"]}}
    monkeypatch.setattr(ac, "_aprobados", lambda cfg: (_ for _ in ()).throw(AssertionError("no debería leer la lista")))
    ac.requerir_acceso("Balcarce")  # entra por dominio
    st_falso.secrets["acceso"]["dominios_aprobados"] = ["otra.com"]
    monkeypatch.setattr(ac, "_aprobados", lambda cfg: (set(), [], 0))
    monkeypatch.setattr(ac, "_leer_planilla", SimpleNamespace(clear=lambda: None))
    with pytest.raises(_Parar):
        ac.requerir_acceso("Balcarce")


def test_usuarios_url_y_secretos_se_combinan(monkeypatch):
    h = ac.hash_contrasena("clave12345")
    monkeypatch.setattr(ac, "_leer_usuarios", lambda url: {"ana": {"nombre": "Ana", "email": "", "hash": h},
                                                           "beto": {"nombre": "Beto", "email": "", "hash": h}})
    u, err = ac._usuarios({"usuarios_url": "https://x/pub?output=csv", "usuarios": {"beto": {"estado": "baja"}, "caro": {"hash": h}}})
    assert sorted(u) == ["ana", "caro"] and not err
