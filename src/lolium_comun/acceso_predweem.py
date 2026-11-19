# -*- coding: utf-8 -*-
"""Control de acceso de las apps PREDWEEM: ingreso con cuentas corporativas (Microsoft, Google u otro proveedor
OpenID Connect) y/o con usuario y contraseña, y lista de usuarios aprobados.

Formas de ingreso (se combinan: la pantalla muestra un botón por proveedor y, si hay usuarios con contraseña, un
formulario):

- **Cuenta corporativa o de Google** (``proveedores``): por ejemplo, el personal de una empresa entra con su cuenta
  Microsoft de la empresa y el resto con Google. Sin ``proveedores``, un único botón «Ingresar con Google» con la
  sección ``[auth]`` (como hasta la versión 1.14).
- **Usuario y contraseña** (``[acceso.usuarios]`` y/o ``usuarios_url``): para quien no tiene cuenta corporativa. Las
  contraseñas se guardan cifradas (scrypt) y se generan con ``python -m lolium_comun.acceso_predweem``. La sesión
  dura mientras la pestaña esté abierta. Tras 5 intentos fallidos el usuario queda bloqueado 15 minutos.

Quién entra con una cuenta corporativa o de Google:

- **Registro libre** (``registro_libre = true``): cualquiera, sin aprobación. Opcionalmente cada ingreso se anota en
  un formulario de Google (``[acceso.registro]``), cuyas respuestas quedan en una planilla.
- **Con aprobación** (por defecto): los administradores, los emails de la lista (``emails``, ``lista_url``) y los de
  los dominios aprobados (``dominios_aprobados``: todo el personal de la empresa sin cargarlo uno por uno).

Los usuarios con contraseña están aprobados por figurar en la lista de usuarios (salvo un ``estado`` no aprobado).

Se activa solo cuando los secretos de la app (Streamlit Community Cloud → Settings → Secrets) incluyen la sección
``[acceso]`` con ``activo = true``. Mientras no estén configurados, la app funciona como siempre (sin login).

Secretos, combinando Microsoft (empresa), Google y usuarios con contraseña::

    [auth]
    redirect_uri = "https://<app>.streamlit.app/oauth2callback"
    cookie_secret = "<texto aleatorio largo>"

    [auth.microsoft]                                      # app registrada en Microsoft Entra ID de la empresa
    client_id = "<id de aplicación>"
    client_secret = "<secreto de cliente>"
    server_metadata_url = "https://login.microsoftonline.com/<id de inquilino>/v2.0/.well-known/openid-configuration"

    [auth.google]
    client_id = "<id de cliente OAuth de Google>"
    client_secret = "<secreto de cliente OAuth de Google>"
    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

    [acceso]
    activo = true
    proveedores = ["microsoft", "google"]                 # botones, en este orden (nombres de las secciones [auth.*])
    dominios_aprobados = ["empresa.com"]                  # emails de estos dominios entran sin estar en la lista
    administradores = ["admin@ejemplo.com"]               # siempre habilitados
    lista_url = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"  # planilla de emails aprobados
    # (o varias: lista_url = ["<planilla manual>", "<respuestas del formulario>"])
    contacto = "admin@ejemplo.com"                        # a quién se pide acceso
    formulario_url = "https://forms.gle/..."              # opcional: formulario de solicitud
    registro_libre = false                                # true: cualquier cuenta entra (sin lista)
    usuarios_url = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"  # opcional: usuarios con contraseña

    [acceso.textos]                                       # opcional: texto de cada botón
    microsoft = "Ingresar con la cuenta de la empresa"

    [acceso.usuarios.jperez]                              # un bloque por usuario con contraseña
    nombre = "Juan Pérez"
    email = "jperez@ejemplo.com"                          # opcional
    hash = "scrypt$16384$8$1$...$..."                     # python -m lolium_comun.acceso_predweem

    [acceso.registro]                                     # opcional: anota cada ingreso en un formulario de Google
    url = "https://docs.google.com/forms/d/e/<ID>/formResponse"
    email = "entry.1111111111"                            # campo del formulario para el email
    nombre = "entry.2222222222"                           # campo para el nombre
    app = "entry.3333333333"                              # campo para la app (localidad)

La planilla de emails publicada como CSV debe tener una columna ``email``; si además tiene una columna ``estado``,
solo se habilitan las filas con ``aprobado`` (o ``sí``/``si``/``ok``). La planilla de usuarios (``usuarios_url``) tiene
las columnas ``usuario`` y ``hash`` y, opcionales, ``nombre``, ``email`` y ``estado``: como la leen todas las apps,
evita repetir los usuarios en los secretos de cada una. Su enlace no debe difundirse (tiene los hashes).
"""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import os
import re
import time
import urllib.parse
import urllib.request

import streamlit as st

_ESTADOS_OK = {"aprobado", "aprobada", "si", "sí", "ok", "habilitado", "habilitada", "1", "true"}
_TEXTOS_PROVEEDOR = {"google": "Ingresar con Google", "microsoft": "Ingresar con cuenta Microsoft (empresa)"}
_SESION = "_predweem_usuario"           # usuario con contraseña conectado en esta sesión
_INTENTOS_MAX, _BLOQUEO_SEG = 5, 15 * 60
_SCRYPT = dict(n=2 ** 14, r=8, p=1)
_CONTACTO_POR_DEFECTO = "chantreguillermo@gmail.com"


def _config() -> dict:
    try:
        return dict(st.secrets.get("acceso", {}))
    except Exception:  # noqa: BLE001  (sin archivo de secretos)
        return {}


# ---------------------------------------------------------------- contraseñas
def hash_contrasena(contrasena: str, sal: bytes | None = None) -> str:
    """Hash scrypt de la contraseña, como texto ``scrypt$n$r$p$sal$hash`` (base64)."""
    sal = sal or os.urandom(16)
    h = hashlib.scrypt(contrasena.encode("utf-8"), salt=sal, dklen=32, **_SCRYPT)
    b64 = lambda x: base64.b64encode(x).decode("ascii")  # noqa: E731
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${b64(sal)}${b64(h)}"


def verificar_contrasena(contrasena: str, guardado: str) -> bool:
    """True si la contraseña corresponde al hash guardado (comparación en tiempo constante)."""
    try:
        tipo, n, r, p, sal, h = str(guardado).strip().split("$")
        if tipo != "scrypt":
            return False
        esperado = base64.b64decode(h)
        obtenido = hashlib.scrypt(contrasena.encode("utf-8"), salt=base64.b64decode(sal), dklen=len(esperado),
                                  n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(obtenido, esperado)
    except Exception:  # noqa: BLE001  (hash mal formado)
        return False


def emails_aprobados_desde_csv(texto: str) -> set[str]:
    """Emails habilitados en el CSV de la planilla (columna email y, opcional, estado)."""
    filas = list(csv.reader(io.StringIO(texto.lstrip("﻿"))))
    if not filas:
        return set()
    encabezado = [c.strip().lower() for c in filas[0]]
    col_email = next((i for i, c in enumerate(encabezado) if "mail" in c), None)
    col_estado = next((i for i, c in enumerate(encabezado) if c in ("estado", "aprobado", "habilitado")), None)
    datos = filas[1:] if col_email is not None else filas
    col_email = 0 if col_email is None else col_email
    aprobados = set()
    for fila in datos:
        if len(fila) <= col_email:
            continue
        email = fila[col_email].strip().lower()
        if "@" not in email:
            continue
        if col_estado is not None:
            estado = fila[col_estado].strip().lower() if len(fila) > col_estado else ""
            if estado not in _ESTADOS_OK:
                continue
        aprobados.add(email)
    return aprobados


def url_descarga_csv(url: str) -> str:
    """Convierte el enlace normal de una planilla (…/d/<ID>/edit…#gid=N) al CSV de su pestaña.

    Ese CSV se sirve directo desde docs.google.com (sin pasar por googleusercontent.com) y requiere que
    la planilla esté compartida como «Cualquier persona con el enlace: Lector». Los enlaces publicados
    (…/d/e/…/pub?…output=csv) se dejan como están.
    """
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]{20,})", url)
    if not m or "/d/e/" in url:
        return url
    gid = re.search(r"[#&?]gid=(\d+)", url)
    destino = f"https://docs.google.com/spreadsheets/d/{m.group(1)}/gviz/tq?tqx=out:csv"
    return destino + (f"&gid={gid.group(1)}" if gid else "")


@st.cache_data(ttl=300, show_spinner=False)
def _leer_planilla(url: str) -> set[str]:
    url = url_descarga_csv(url)
    pedido = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "text/csv,text/plain,*/*",
    })
    with urllib.request.urlopen(pedido, timeout=20) as respuesta:  # noqa: S310 (URL fija de los secretos)
        texto = respuesta.read().decode("utf-8", errors="replace")
    if texto.lstrip().lower().startswith(("<!doctype", "<html")):
        raise ValueError("el enlace devolvió una página web, no un CSV (¿falta publicarlo o es el enlace /edit?)")
    return emails_aprobados_desde_csv(texto)


def _aprobados(cfg: dict) -> tuple[set[str], list[int], int]:
    """Devuelve (emails habilitados, números de lista que no se pudieron leer, cantidad de listas)."""
    emails = {str(e).strip().lower() for e in cfg.get("administradores", [])}
    emails |= {str(e).strip().lower() for e in cfg.get("emails", [])}
    urls = cfg.get("lista_url", [])
    urls = [urls] if isinstance(urls, str) else list(urls)
    urls = [str(u).strip() for u in urls if str(u).strip()]
    fallidas = []
    for n, url in enumerate(urls, start=1):
        try:
            emails |= _leer_planilla(url)
        except Exception as error:  # noqa: BLE001
            fallidas.append(f"{n} ({type(error).__name__}: {str(error)[:120]})")
    return emails, fallidas, len(urls)


# ---------------------------------------------------------------- usuarios con contraseña
def usuarios_desde_csv(texto: str) -> dict[str, dict]:
    """Usuarios con contraseña de la planilla CSV (columnas usuario y hash; opcionales nombre, email y estado)."""
    out = {}
    for fila in csv.DictReader(io.StringIO(texto.lstrip("﻿"))):
        f = {str(k).strip().lower(): str(v or "").strip() for k, v in fila.items() if k}
        usuario, h = f.get("usuario", "").lower(), f.get("hash", "")
        if not usuario or not h:
            continue
        if f.get("estado") and f["estado"].lower() not in _ESTADOS_OK:
            continue
        out[usuario] = {"nombre": f.get("nombre", ""), "email": f.get("email", ""), "hash": h}
    return out


@st.cache_data(ttl=300, show_spinner=False)
def _leer_usuarios(url: str) -> dict[str, dict]:
    pedido = urllib.request.Request(url_descarga_csv(url), headers={"User-Agent": "Mozilla/5.0 PREDWEEM",
                                                                   "Accept": "text/csv,text/plain,*/*"})
    with urllib.request.urlopen(pedido, timeout=20) as respuesta:  # noqa: S310 (URL fija de los secretos)
        texto = respuesta.read().decode("utf-8", errors="replace")
    if texto.lstrip().lower().startswith(("<!doctype", "<html")):
        raise ValueError("el enlace de usuarios devolvió una página web, no un CSV")
    return usuarios_desde_csv(texto)


def _usuarios(cfg: dict) -> tuple[dict[str, dict], list[str]]:
    """Usuarios con contraseña: los de ``usuarios_url`` y los de los secretos (estos mandan). Devuelve (usuarios, errores)."""
    out, errores = {}, []
    url = str(cfg.get("usuarios_url", "") or "").strip()
    if url:
        try:
            out.update(_leer_usuarios(url))
        except Exception as error:  # noqa: BLE001
            errores.append(f"{type(error).__name__}: {str(error)[:120]}")
    for usuario, datos in dict(cfg.get("usuarios", {}) or {}).items():
        usuario, datos = str(usuario).strip().lower(), dict(datos or {})
        if datos.get("estado") and str(datos["estado"]).strip().lower() not in _ESTADOS_OK:
            out.pop(usuario, None)
        elif datos.get("hash"):
            out[usuario] = {"nombre": str(datos.get("nombre", "")), "email": str(datos.get("email", "")),
                            "hash": str(datos["hash"])}
    return out, errores


def _con_contrasena(cfg: dict) -> bool:
    return bool(cfg.get("usuarios")) or bool(str(cfg.get("usuarios_url", "") or "").strip())


@st.cache_resource(show_spinner=False)
def _intentos() -> dict:
    """Intentos fallidos por usuario, compartidos por todas las sesiones de la app: {usuario: (n, desde)}."""
    return {}


def _bloqueado(usuario: str, ahora: float | None = None) -> int:
    """Segundos de bloqueo que le quedan al usuario (0 si puede intentar)."""
    ahora = time.time() if ahora is None else ahora
    n, desde = _intentos().get(usuario, (0, 0.0))
    if n < _INTENTOS_MAX:
        return 0
    if ahora - desde < _BLOQUEO_SEG:
        return int(_BLOQUEO_SEG - (ahora - desde))
    _intentos().pop(usuario, None)
    return 0


def ingresar_con_contrasena(cfg: dict, usuario: str, contrasena: str) -> str | None:
    """Valida usuario y contraseña: si son correctos guarda la sesión y devuelve None; si no, el mensaje de error."""
    usuario = str(usuario or "").strip().lower()
    if not usuario or not contrasena:
        return "Completá el usuario y la contraseña."
    espera = _bloqueado(usuario)
    if espera:
        return f"Demasiados intentos fallidos. Probá de nuevo en {max(1, round(espera / 60))} minutos."
    datos = _usuarios(cfg)[0].get(usuario)
    if datos and verificar_contrasena(contrasena, datos["hash"]):
        _intentos().pop(usuario, None)
        st.session_state[_SESION] = {"usuario": usuario, "nombre": datos.get("nombre") or usuario,
                                     "email": str(datos.get("email") or "").strip().lower(), "via": "contraseña"}
        return None
    n, _ = _intentos().get(usuario, (0, 0.0))
    _intentos()[usuario] = (n + 1, time.time())
    return "Usuario o contraseña incorrectos."


# ---------------------------------------------------------------- identidad
def _conectado_oidc() -> bool:
    try:
        return bool(st.user.get("is_logged_in", False))
    except Exception:  # noqa: BLE001
        return False


def _conectado() -> bool:
    return bool(st.session_state.get(_SESION)) or _conectado_oidc()


def usuario_actual() -> dict | None:
    """Usuario conectado, {email, nombre, via} (via: «contraseña» u «oidc»), o None."""
    if st.session_state.get(_SESION):
        return dict(st.session_state[_SESION])
    if _conectado_oidc():
        # Microsoft Entra no siempre manda «email»: se usa el nombre de usuario principal
        email = st.user.get("email") or st.user.get("preferred_username") or st.user.get("upn") or ""
        return {"email": str(email).strip(), "nombre": st.user.get("name") or str(email), "via": "oidc"}
    return None


def _cerrar_sesion() -> None:
    if st.session_state.get(_SESION):
        st.session_state.pop(_SESION, None)
    else:
        st.logout()


def _dominio_aprobado(cfg: dict, email: str) -> bool:
    dominios = cfg.get("dominios_aprobados", [])
    dominios = [dominios] if isinstance(dominios, str) else list(dominios)
    dom = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
    for d in dominios:
        d = str(d).strip().lower().lstrip("@")
        if d and dom and (dom == d or dom.endswith("." + d)):
            return True
    return False


def _proveedores(cfg: dict) -> list[str]:
    p = cfg.get("proveedores", [])
    return [p] if isinstance(p, str) else [str(x).strip() for x in p if str(x).strip()]


def _encabezado(nombre_app: str) -> None:
    st.set_page_config(page_title=f"PREDWEEM {nombre_app} · Ingreso", page_icon="🌾", layout="centered")
    st.markdown(
        f"<h2 style='margin-bottom:0'>🌾 PREDWEEM — {nombre_app}</h2>"
        "<p style='color:#4b5563;margin-top:.3rem'>Predicción de emergencia de <i>Lolium multiflorum</i></p>",
        unsafe_allow_html=True,
    )


def _anotar_ingreso(cfg: dict, nombre_app: str) -> None:
    """Anota el ingreso (email, nombre, app) en el formulario de ``[acceso.registro]``, una vez por sesión.

    Un fallo no impide usar la app."""
    reg = dict(cfg.get("registro", {}) or {})
    url = str(reg.get("url", "")).strip()
    clave = f"_predweem_ingreso_anotado_{nombre_app}"
    if not url or st.session_state.get(clave):
        return
    st.session_state[clave] = True
    datos, u = {}, usuario_actual() or {}
    for campo, valor in (("email", u.get("email", "")), ("nombre", u.get("nombre", "")), ("app", nombre_app)):
        entrada = str(reg.get(campo, "")).strip()
        if entrada:
            datos[entrada] = str(valor or "")
    if not datos:
        return
    try:
        pedido = urllib.request.Request(url, data=urllib.parse.urlencode(datos).encode("utf-8"),
                                        headers={"User-Agent": "Mozilla/5.0 PREDWEEM"})
        urllib.request.urlopen(pedido, timeout=10).read()  # noqa: S310 (URL fija de los secretos)
    except Exception:  # noqa: BLE001
        pass


def _pantalla_ingreso(cfg: dict, nombre_app: str) -> None:
    """Pantalla de ingreso: un botón por proveedor (cuenta corporativa o Google) y, si hay, usuario y contraseña."""
    libre = bool(cfg.get("registro_libre", False))
    proveedores, textos = _proveedores(cfg), dict(cfg.get("textos", {}) or {})
    con_clave = _con_contrasena(cfg)
    _encabezado(nombre_app)
    if not proveedores and not con_clave:  # como hasta 1.14: solo Google, sección [auth] única
        st.info("El acceso a las aplicaciones PREDWEEM es libre y gratuito, con registro: ingresá con tu cuenta de Google."
                if libre else "El acceso a las aplicaciones PREDWEEM es para usuarios registrados. Ingresá con tu cuenta de Google.")
        st.button("Ingresar con Google", type="primary", icon=":material/login:", on_click=st.login, width="stretch")
        st.caption(
            ("Solo se usa tu nombre y tu email para saber quién usa las apps; no se comparten con terceros."
             if libre else "Si es la primera vez, al ingresar vas a poder solicitar el acceso. "
             "Solo se usa tu nombre y tu email para identificarte.")
        )
        return
    st.info("El acceso a las aplicaciones PREDWEEM es para usuarios registrados. Elegí cómo ingresar.")
    for i, prov in enumerate(proveedores):
        st.button(str(textos.get(prov) or _TEXTOS_PROVEEDOR.get(prov, f"Ingresar con {prov}")),
                  type="primary" if i == 0 else "secondary", icon=":material/login:", on_click=st.login, args=(prov,),
                  width="stretch", key=f"predweem_login_{prov}")
    if con_clave:
        if proveedores:
            st.caption("Sin cuenta de las anteriores: ingresá con el usuario y la contraseña que te asignaron.")
        with st.form("predweem_login_clave", border=True):
            usuario = st.text_input("Usuario", key="predweem_usuario")
            contrasena = st.text_input("Contraseña", type="password", key="predweem_contrasena")
            enviar = st.form_submit_button("Ingresar", icon=":material/key:", width="stretch")
        if enviar:
            error = ingresar_con_contrasena(cfg, usuario, contrasena)
            if error is None:
                st.rerun()
            st.error(error)
    st.caption(f"Para pedir acceso o un usuario, escribí a {cfg.get('contacto', _CONTACTO_POR_DEFECTO)}. "
               "Solo se usa tu nombre y tu email para identificarte.")


def requerir_acceso(nombre_app: str) -> None:
    """Detiene la app hasta que el usuario ingresa (cuenta corporativa, Google o usuario y contraseña) y, salvo registro
    libre, está aprobado."""
    cfg = _config()
    if not cfg.get("activo", False):
        return  # control de acceso todavía no configurado: la app sigue abierta
    libre = bool(cfg.get("registro_libre", False))

    contacto = str(cfg.get("contacto", _CONTACTO_POR_DEFECTO))

    if not _conectado():
        _pantalla_ingreso(cfg, nombre_app)
        st.stop()

    u = usuario_actual() or {}
    if u.get("via") == "contraseña":
        # sigue aprobado mientras figure en la lista de usuarios (una baja corta la sesión en la próxima carga)
        if u.get("usuario") in _usuarios(cfg)[0]:
            _anotar_ingreso(cfg, nombre_app)
            return
        st.session_state.pop(_SESION, None)
        _pantalla_ingreso(cfg, nombre_app)
        st.stop()

    email = str(u.get("email", "")).strip().lower()
    if libre or _dominio_aprobado(cfg, email):
        _anotar_ingreso(cfg, nombre_app)
        return
    aprobados, fallidas, total = _aprobados(cfg)
    if email and email in aprobados:
        _anotar_ingreso(cfg, nombre_app)
        return
    # Puede haber sido aprobado hace instantes: se vuelve a leer la planilla sin usar la copia guardada.
    _leer_planilla.clear()
    aprobados, fallidas, total = _aprobados(cfg)
    if email and email in aprobados:
        _anotar_ingreso(cfg, nombre_app)
        return

    _encabezado(nombre_app)
    nombre = u.get("nombre") or email
    formulario = str(cfg.get("formulario_url", "")).strip()
    if fallidas and len(fallidas) == total:
        st.error("No se pudo verificar la lista de usuarios habilitados. Probá de nuevo en unos minutos.")
        st.caption("Detalle para el administrador: no se pudo leer `lista_url`: " + "; ".join(fallidas))
    elif formulario:
        st.warning(f"Hola {nombre}: tu cuenta **{email}** todavía no está habilitada para usar PREDWEEM.")
        st.link_button("Solicitar acceso", formulario, type="primary", icon=":material/how_to_reg:", width="stretch")
        st.caption(
            f"Completá el formulario con este mismo email ({email}). "
            "Cuando se apruebe tu solicitud vas a poder entrar a todas las apps PREDWEEM; volvé a abrir esta página."
        )
    else:
        st.warning(f"Hola {nombre}: tu cuenta **{email}** todavía no está habilitada para usar PREDWEEM.")
        asunto = f"Solicitud de acceso a PREDWEEM {nombre_app}"
        cuerpo = (
            f"Hola, solicito acceso a la app PREDWEEM {nombre_app}.\n\n"
            f"Nombre: {nombre}\nEmail de la cuenta con que ingresé: {email}\n"
            "Institución / empresa:\nLocalidad:\nUso previsto:\n"
        )
        enlace = f"mailto:{contacto}?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
        st.link_button("Solicitar acceso por email", enlace, type="primary", icon=":material/mail:", width="stretch")
        st.caption(f"La solicitud llega a {contacto}. Cuando se apruebe, volvé a abrir esta página.")
    if fallidas and len(fallidas) < total:
        st.caption(
            "Detalle para el administrador: no se pudo leer la lista n.º "
            + "; ".join(fallidas) + f" (de {total} en `lista_url`)."
        )
    st.button("Cerrar sesión", on_click=_cerrar_sesion)
    st.stop()


def mostrar_sesion() -> None:
    """Muestra en la barra lateral el usuario conectado y el botón para cerrar sesión."""
    if not _config().get("activo", False) or not _conectado():
        return
    u = usuario_actual() or {}
    with st.sidebar:
        st.divider()
        st.caption(f"Sesión: {u.get('email') or u.get('nombre', '')}")
        st.button("Cerrar sesión", on_click=_cerrar_sesion, key="predweem_cerrar_sesion")


def _main() -> None:
    """Genera el bloque de secretos (o la fila de la planilla) de un usuario con contraseña."""
    import getpass

    usuario = input("Usuario (sin espacios): ").strip().lower()
    nombre = input("Nombre y apellido: ").strip()
    email = input("Email (opcional): ").strip()
    while True:
        c1 = getpass.getpass("Contraseña (mínimo 10 caracteres): ")
        if len(c1) < 10:
            print("Muy corta.")
            continue
        if c1 == getpass.getpass("Repetir la contraseña: "):
            break
        print("No coinciden.")
    h = hash_contrasena(c1)
    print(f"\nPara los secretos de la app:\n\n[acceso.usuarios.{usuario}]\nnombre = \"{nombre}\"\n"
          + (f"email = \"{email}\"\n" if email else "") + f"hash = \"{h}\"\n")
    print(f"Para la planilla (usuario,hash,nombre,email,estado):\n\n{usuario},{h},{nombre},{email},aprobado")


if __name__ == "__main__":
    _main()
