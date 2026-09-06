"""Autorisation OAuth2 tastytrade — à exécuter UNE FOIS.

Le SDK tastytrade s'authentifie avec un refresh token de longue durée, qu'il
échange contre des access tokens courts. Ce module réalise l'étape initiale
(authorization code -> refresh token), qui exige une approbation navigateur.

Usage :
    python -m gex.tt_auth

Le script affiche une URL à ouvrir, tu approuves, ton navigateur est redirigé
vers https://localhost:8050/oauth/callback (page d'erreur attendue : rien
n'écoute en HTTPS sur ce port). Le paramètre `code=` de la barre d'adresse est
à recoller ici. Le refresh token obtenu est ensuite à stocker en variable
d'environnement TT_REFRESH.
"""
from __future__ import annotations

import logging
import os
import sys
import urllib.parse
from pathlib import Path

import requests

log = logging.getLogger(__name__)

AUTH_URL = "https://my.tastytrade.com/auth.html"
TOKEN_URL = "https://api.tastyworks.com/oauth/token"
REDIRECT_URI = "http://localhost:8050/oauth/callback"
SCOPE = "read"


def _env(name: str) -> str | None:
    """Variable d'environnement, avec repli sur le registre utilisateur Windows
    (une session ouverte avant `setx` ne voit pas la nouvelle valeur)."""
    val = os.environ.get(name)
    if not val and sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                val = winreg.QueryValueEx(k, name)[0]
        except OSError:
            pass
    return val


def _find_env_path() -> Path:
    """Localise le fichier .env du projet."""
    p = Path(".env").resolve()
    if p.exists() or (p.parent / "pyproject.toml").exists():
        return p
    return Path(__file__).resolve().parent.parent / ".env"


def _update_env_file(updates: dict[str, str | None]) -> None:
    """Met à jour ou ajoute les clés dans le fichier .env sans écraser le reste."""
    env_path = _find_env_path()
    lines: list[str] = []
    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            lines = []
    elif Path(".env.example").exists():
        try:
            lines = Path(".env.example").read_text(encoding="utf-8").splitlines()
        except Exception:
            lines = []

    remaining = dict(updates)
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in remaining:
                val = remaining.pop(key)
                if val is not None:
                    new_lines.append(f"{key}={val}")
                continue
        new_lines.append(line)

    for key, val in remaining.items():
        if val is not None:
            new_lines.append(f"{key}={val}")

    try:
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as exc:
        log.warning("Impossible d'écrire dans .env: %s", exc)


def save_credentials(client_id: str, client_secret: str, refresh_token: str | None = None) -> None:
    """Enregistre le Client ID, Client Secret et optionnellement le Refresh Token
    dans os.environ, le fichier .env et le registre Windows HKCU."""
    cid = client_id.strip()
    sec = client_secret.strip()
    os.environ["TASTYTRADE_CLIENT_ID"] = cid
    os.environ["TASTYTRADE_CLIENT_SECRET"] = sec

    updates: dict[str, str | None] = {
        "TASTYTRADE_CLIENT_ID": cid,
        "TASTYTRADE_CLIENT_SECRET": sec,
    }
    if refresh_token and refresh_token.strip():
        ref = refresh_token.strip()
        os.environ["TT_REFRESH"] = ref
        updates["TT_REFRESH"] = ref

    _update_env_file(updates)

    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                                winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "TASTYTRADE_CLIENT_ID", 0, winreg.REG_SZ, cid)
                winreg.SetValueEx(k, "TASTYTRADE_CLIENT_SECRET", 0, winreg.REG_SZ, sec)
                if refresh_token and refresh_token.strip():
                    winreg.SetValueEx(k, "TT_REFRESH", 0, winreg.REG_SZ, refresh_token.strip())
        except OSError:
            pass


def clear_credentials() -> None:
    """Supprime les identifiants de session, de .env et du registre Windows."""
    for key in ("TASTYTRADE_CLIENT_ID", "TASTYTRADE_CLIENT_SECRET", "TT_REFRESH"):
        os.environ.pop(key, None)

    _update_env_file({
        "TASTYTRADE_CLIENT_ID": None,
        "TASTYTRADE_CLIENT_SECRET": None,
        "TT_REFRESH": None,
    })

    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                                winreg.KEY_SET_VALUE) as k:
                for key in ("TASTYTRADE_CLIENT_ID", "TASTYTRADE_CLIENT_SECRET", "TT_REFRESH"):
                    try:
                        winreg.DeleteValue(k, key)
                    except OSError:
                        pass
        except OSError:
            pass


def credentials() -> tuple[str, str]:
    cid = _env("TASTYTRADE_CLIENT_ID")
    secret = _env("TASTYTRADE_CLIENT_SECRET")
    if not cid or not secret:
        raise SystemExit(
            "TASTYTRADE_CLIENT_ID / TASTYTRADE_CLIENT_SECRET introuvables "
            "(variables d'environnement ou registre HKCU)."
        )
    return cid, secret


def authorize_url(client_id: str, state: str | None = None) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
    }
    if state:
        params["state"] = state
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def store_refresh(token: str) -> str:
    os.environ["TT_REFRESH"] = token
    _update_env_file({"TT_REFRESH": token})
    if sys.platform != "win32":
        return ("Jeton actif pour cette session. Pour le rendre permanent, "
                'ajoute TT_REFRESH="…" à ton profil shell.')
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                            winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "TT_REFRESH", 0, winreg.REG_SZ, token)
        return "Jeton enregistré (variable utilisateur TT_REFRESH)."
    except OSError as exc:
        return (f"Jeton actif pour cette session, mais non enregistré ({exc}). "
                "Il faudra se reconnecter au prochain démarrage.")


def exchange_code(client_id: str, secret: str, code: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": secret,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise SystemExit(f"Échec de l'échange ({resp.status_code}) : {resp.text[:400]}")
    return resp.json()


def main() -> None:
    cid, secret = credentials()
    print("\n1) Ouvre cette URL dans ton navigateur et approuve l'accès :\n")
    print(authorize_url(cid))
    print(
        "\n2) Tu seras redirigé vers une page d'ERREUR (normal : rien n'écoute"
        f"\n   sur {REDIRECT_URI}). Dans la barre d'adresse, copie la valeur"
        "\n   du paramètre code=... (tout ce qui suit 'code=', avant un '&')\n"
    )
    code = input("3) Colle le code ici : ").strip()
    if not code:
        raise SystemExit("Aucun code fourni.")

    data = exchange_code(cid, secret, code)
    refresh = data.get("refresh_token")
    if not refresh:
        raise SystemExit(f"Pas de refresh_token dans la réponse : {data}")

    print("\n" + "=" * 62)
    print("Refresh token obtenu. Enregistre les DEUX variables ci-dessous")
    print("(noms imposés par le SDK tastytrade), puis relance ta session :\n")
    print(f'  setx TT_REFRESH "{refresh}"')
    print('  setx TT_SECRET "%TASTYTRADE_CLIENT_SECRET%"')
    print("=" * 62)
    print("\nCe token est un secret de longue durée : ne le partage pas et ne")
    print("le committe jamais dans le repo.\n")


if __name__ == "__main__":
    main()
