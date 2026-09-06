"""Connexion tastytrade depuis le dashboard, sans copier-coller.

Remplace la gymnastique de `python -m gex.tt_auth` (ouvrir une URL, atterrir
sur une page d'erreur, recopier le `code=` de la barre d'adresse, puis `setx`)
par deux clics : « Connecter », approuver.

Ce qui rend ça possible : l'URI de redirection enregistrée côté tastytrade est
`http://localhost:8050/oauth/callback`, donc le navigateur revient sur le
dashboard lui-même — qui peut alors lire le code et faire l'échange.

⚠️ Portée. Ces routes ne servent QUE l'autorisation, en scope `read`. Ce
serveur n'écoute qu'en local (cf. gex/api.py) et le projet n'exécute aucun
ordre : un jeton obtenu ici ne peut pas trader, par construction.

Sécurité de l'échange :
- un `state` aléatoire à usage unique est vérifié au retour. Sans lui, une
  page tierce pourrait déclencher notre callback avec SON code
  d'autorisation, et le dashboard enregistrerait le jeton de quelqu'un
  d'autre (« OAuth code injection ») ;
- le `code` et le `client_secret` ne transitent que vers l'API tastytrade ;
- le refresh token obtenu n'est jamais affiché ni journalisé, seulement
  rangé là où `rtquote._env` le lit déjà (cf. tt_auth.store_refresh).
"""
from __future__ import annotations

import logging
import secrets
import threading

from flask import Flask, redirect, request

from . import tt_auth
from .rtquote import credentials_present

log = logging.getLogger(__name__)

# `state` en attente, à usage unique. Un dict plutôt qu'une valeur simple :
# rien n'interdit à l'utilisateur de cliquer deux fois puis de terminer la
# première autorisation. Borné pour ne pas croître indéfiniment si des
# tentatives sont abandonnées.
_PENDING: dict[str, float] = {}
_PENDING_LOCK = threading.Lock()
_MAX_PENDING = 8


def _page(titre: str, message: str, ok: bool) -> str:
    """Page de retour minimale, aux couleurs du dashboard."""
    couleur = "#22c55e" if ok else "#ef4444"
    redirect_tag = '<meta http-equiv="refresh" content="3;url=/">' if ok else ''
    redirect_msg = '<p style="font-size:0.85rem;color:#898781;margin-top:1rem">Redirigiendo automáticamente al dashboard en 3 segundos...</p>' if ok else ''
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{redirect_tag}
<title>{titre}</title></head>
<body style="background:#0d0d0d;color:#e5e5e5;font-family:system-ui,-apple-system,sans-serif;
             display:flex;align-items:center;justify-content:center;
             min-height:100vh;margin:0;padding:1rem;box-sizing:border-box">
  <div style="max-width:32rem;width:100%;padding:2.2rem;border-radius:8px;border:1px solid #2c2c2a;border-left:4px solid {couleur};
              background:#151515;box-shadow:0 16px 40px rgba(0,0,0,0.7)">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.8rem">
      <span style="font-size:1.4rem">{'✅' if ok else '❌'}</span>
      <h1 style="margin:0;font-size:1.25rem;font-weight:600;color:{couleur}">{titre}</h1>
    </div>
    <p style="margin:0 0 1.5rem;line-height:1.6;color:#c3c2b7;font-size:0.95rem">{message}</p>
    <a href="/" style="display:inline-block;padding:0.6rem 1.2rem;background:#2563eb;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:500;font-size:0.9rem;transition:background 0.2s">Volver al Dashboard</a>
    {redirect_msg}
  </div>
</body></html>"""


def _remember_state() -> str:
    import time

    state = secrets.token_urlsafe(24)
    with _PENDING_LOCK:
        if len(_PENDING) >= _MAX_PENDING:
            plus_vieux = min(_PENDING, key=_PENDING.get)
            _PENDING.pop(plus_vieux, None)
        _PENDING[state] = time.time()
    return state


def _consume_state(state: str | None) -> bool:
    """Vrai si le state était bien en attente. À usage unique : un même state
    ne peut pas servir deux fois."""
    if not state:
        return False
    with _PENDING_LOCK:
        return _PENDING.pop(state, None) is not None


def connection_status() -> tuple[str, str]:
    """(état, message) de la connexion courtier, pour l'affichage."""
    from .rtquote import _env, _is_real_val

    if _is_real_val(_env("DXFEED_AUTH_TOKEN")):
        return "connecte", "Token direct dxFeed actif (temps réel)."

    cid = _env("TASTYTRADE_CLIENT_ID")
    secret = _env("TASTYTRADE_CLIENT_SECRET")
    refresh = _env("TT_REFRESH")

    if not _is_real_val(cid) or not _is_real_val(secret):
        return "absent", "Sin credenciales (introduce Client ID y Client Secret para activar tiempo real)."
    if not _is_real_val(refresh):
        return "deconnecte", "Credenciales guardadas — pendiente autorizar conexión con Tastytrade."
    return "connecte", "Cuenta Tastytrade conectada (Tiempo real activo en todas las herramientas)."


def register_oauth(app) -> None:
    """`app` : instance Dash (on grimpe à `.server`) ou Flask directement."""
    server: Flask = app.server if hasattr(app, "server") else app
    from flask import jsonify

    @server.route("/api/v1/tastytrade/status")
    def _api_status():
        from .rtquote import _env, _is_real_val
        etat, msg = connection_status()
        cid = _env("TASTYTRADE_CLIENT_ID") or ""
        masked_cid = f"{cid[:4]}...{cid[-4:]}" if len(cid) > 8 else ("***" if cid else "")
        return jsonify({
            "status": etat,
            "message": msg,
            "client_id": masked_cid,
            "has_secret": _is_real_val(_env("TASTYTRADE_CLIENT_SECRET")),
            "has_refresh": _is_real_val(_env("TT_REFRESH")),
            "credentials_present": credentials_present(),
        })

    @server.route("/api/v1/tastytrade/save", methods=["POST"])
    def _api_save():
        data = request.get_json(silent=True) or request.form
        cid = (data.get("client_id") or "").strip()
        secret = (data.get("client_secret") or "").strip()
        refresh = (data.get("refresh_token") or "").strip() or None

        if not cid or not secret:
            return jsonify({"ok": False, "error": "Client ID y Client Secret son obligatorios."}), 400

        tt_auth.save_credentials(cid, secret, refresh)
        if refresh:
            _demarrer_les_flux()

        etat, msg = connection_status()
        return jsonify({"ok": True, "status": etat, "message": msg, "credentials_present": credentials_present()})

    @server.route("/api/v1/tastytrade/disconnect", methods=["POST"])
    def _api_disconnect():
        tt_auth.clear_credentials()
        etat, msg = connection_status()
        return jsonify({"ok": True, "status": etat, "message": msg})

    @server.route("/oauth/start")
    def _oauth_start():
        from .rtquote import _env

        # Permet aussi de passer client_id et client_secret directement en paramètres
        req_cid = request.args.get("client_id")
        req_sec = request.args.get("client_secret")
        if req_cid and req_sec:
            tt_auth.save_credentials(req_cid, req_sec)

        cid = _env("TASTYTRADE_CLIENT_ID")
        if not cid:
            return _page("Configuración incompleta",
                         "TASTYTRADE_CLIENT_ID no encontrado. Ingresa tu "
                         "Client ID y Client Secret en el modal de configuración "
                         "del Dashboard.",
                         ok=False), 400
        return redirect(tt_auth.authorize_url(cid, state=_remember_state()))

    @server.route("/oauth/callback")
    def _oauth_callback():
        erreur = request.args.get("error")
        if erreur:
            return _page("Autorización rechazada / Refusée",
                         f"Tastytrade respondió: {erreur} (refus). "
                         "No se guardó ninguna credencial.", ok=False), 400

        if not _consume_state(request.args.get("state")):
            log.warning("OAuth : state invalide ou expiré, échange refusé")
            return _page("Solicitud no reconocida",
                         "Esta autorización no corresponde a ninguna solicitud "
                         "iniciada desde este dashboard o ha caducado. "
                         "Por seguridad, inténtalo de nuevo.",
                         ok=False), 400

        code = request.args.get("code")
        if not code:
            return _page("Código ausente",
                         "Tastytrade no devolvió el código de autorización.",
                         ok=False), 400

        try:
            cid, secret = tt_auth.credentials()
            data = tt_auth.exchange_code(cid, secret, code)
        except SystemExit as exc:
            log.warning("OAuth : échange refusé (%s)", exc)
            return _page("Intercambio rechazado", str(exc), ok=False), 400
        except Exception:
            log.exception("OAuth : échec de l'échange du code")
            return _page("Error de conexión",
                         "No fue posible contactar a los servidores de Tastytrade. "
                         "Verifica tu conexión a internet y vuelve a intentar.", ok=False), 502

        refresh = data.get("refresh_token")
        if not refresh:
            return _page("Respuesta inesperada",
                         "No se encontró el refresh_token en la respuesta de Tastytrade.",
                         ok=False), 502

        note = tt_auth.store_refresh(refresh)
        log.info("OAuth tastytrade : connexion réussie. %s", note)
        _demarrer_les_flux()
        return _page("¡Conectado a Tastytrade con éxito!",
                     "Tus credenciales han sido verificadas y guardadas. "
                     "Los flujos de datos en tiempo real (Spot, Order Flow / Tape, "
                     "cadenas nativas NQ/ES y tick capture) se han iniciado automáticamente.", ok=True)


def _demarrer_les_flux() -> None:
    """Démarre les flux qui refusaient de tourner faute d'identifiants.

    Sans cela, il faudrait redémarrer le dashboard juste après s'être
    connecté — ce qui reviendrait à remplacer un copier-coller par un
    redémarrage. `start()` est idempotent des deux côtés.
    """
    try:
        if credentials_present():
            from .flowtape import TAPE
            from .rtquote import QUOTES
            from .tickcapture import CAPTURE

            QUOTES.start()
            TAPE.start()
            CAPTURE.start()
    except Exception:  # noqa: BLE001 — un flux qui refuse de démarrer ne doit
        log.exception("Démarrage des flux après connexion")
