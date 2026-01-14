#!/usr/bin/env python3
"""
Domeneshop GUI - Et web-basert grensesnitt for Domeneshop API

Kjør: python domeneshop_gui.py
Åpne: http://localhost:5050

Sikkerhetsfunksjoner:
- Rate limiting på autentiseringsendepunkter
- CSRF-beskyttelse
- Sikre session-cookies
- Audit logging
"""

import os
import sys
import re
import secrets
import time
from pathlib import Path
from functools import wraps
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests

# Import av sikkerhetsmoduler
from credentials import (
    load_credentials, save_credentials, delete_credentials,
    get_credentials_info, migrate_file_to_keychain, KEYRING_AVAILABLE,
    list_accounts, save_account, load_account, delete_account,
    rename_account
)
from audit import (
    log_auth_success, log_auth_failure, log_credentials_saved,
    log_credentials_deleted, log_dns_change, log_forward_change,
    log_rate_limit, log_csrf_failure, log_invalid_input,
    get_client_ip, get_user_agent,
    log_account_created, log_account_deleted, log_account_renamed,
    log_account_selected
)

# API konfigurasjon
API_BASE_URL = "https://api.domeneshop.no/v0"
SECRET_KEY_FILE = Path.home() / ".domeneshop-gui-secret"

app = Flask(__name__)

# ==================== SESSION-SIKKERHET ====================

def get_or_create_secret_key() -> bytes:
    """Hent eller opprett persistent secret key"""
    if SECRET_KEY_FILE.exists():
        try:
            return SECRET_KEY_FILE.read_bytes()
        except Exception:
            pass
    
    # Generer ny secret key
    secret = secrets.token_bytes(32)
    try:
        SECRET_KEY_FILE.write_bytes(secret)
        if sys.platform != "win32":
            SECRET_KEY_FILE.chmod(0o600)
    except Exception:
        pass  # Bruk in-memory key hvis fil ikke kan skrives
    
    return secret


app.secret_key = get_or_create_secret_key()

# Session-konfigurasjon
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,     # Ikke tilgjengelig via JavaScript
    SESSION_COOKIE_SAMESITE='Lax',    # CSRF-beskyttelse
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
)

# I produksjon bør dette settes til True (krever HTTPS)
# app.config['SESSION_COOKIE_SECURE'] = True


# ==================== RATE LIMITING ====================

rate_limit_store: dict = {}  # {ip: [timestamp, ...]}


def rate_limit(max_requests: int = 5, window_seconds: int = 60):
    """
    Rate limiting dekorator.
    Begrenser antall forespørsler per IP-adresse.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = get_client_ip() or "unknown"
            now = time.time()
            
            # Rydd opp gamle entries
            if ip in rate_limit_store:
                rate_limit_store[ip] = [
                    t for t in rate_limit_store[ip] 
                    if now - t < window_seconds
                ]
            else:
                rate_limit_store[ip] = []
            
            # Sjekk rate limit
            if len(rate_limit_store[ip]) >= max_requests:
                log_rate_limit(ip, request.path)
                return jsonify({
                    "error": "For mange forespørsler. Vent litt før du prøver igjen.",
                    "retry_after": window_seconds
                }), 429
            
            # Registrer forespørsel
            rate_limit_store[ip].append(now)
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ==================== CSRF-BESKYTTELSE ====================

def generate_csrf_token() -> str:
    """Generer CSRF-token for session"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def validate_csrf_token() -> bool:
    """Valider CSRF-token fra request"""
    token_from_request = request.headers.get('X-CSRF-Token') or \
                         (request.json or {}).get('csrf_token')
    token_from_session = session.get('csrf_token')
    
    if not token_from_request or not token_from_session:
        return False
    
    return secrets.compare_digest(token_from_request, token_from_session)


def csrf_protect(f):
    """CSRF-beskyttelse dekorator for POST/PUT/DELETE"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE'):
            if not validate_csrf_token():
                log_csrf_failure(get_client_ip(), request.path)
                return jsonify({"error": "Ugyldig CSRF-token"}), 403
        return f(*args, **kwargs)
    return wrapper


# ==================== INPUT-VALIDERING ====================

def validate_token_format(token: str) -> bool:
    """Valider at token har gyldig format"""
    if not token or len(token) < 10 or len(token) > 200:
        return False
    # Domeneshop tokens er typisk alfanumeriske
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', token))


def validate_secret_format(secret: str) -> bool:
    """Valider at secret har gyldig format"""
    if not secret or len(secret) < 10 or len(secret) > 200:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', secret))


# ==================== API-KLIENT ====================

class DomeneshopClient:
    """Klient for Domeneshop API"""

    def __init__(self, token: str, secret: str):
        self.token = token
        self.secret = secret
        self.session = requests.Session()
        self.session.auth = (token, secret)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def _request(self, method: str, endpoint: str, data=None, params=None):
        """Utfør HTTP-forespørsel mot API"""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params
            )
            response.raise_for_status()
            
            if response.status_code == 204:
                return None
            if response.content:
                return response.json()
            return None
            
        except requests.exceptions.HTTPError as e:
            error_msg = e.response.text if e.response else str(e)
            raise Exception(f"API-feil ({e.response.status_code}): {error_msg}")
        except requests.exceptions.ConnectionError:
            raise Exception("Kunne ikke koble til Domeneshop API")

    # Domener
    def get_domains(self, domain_filter=None):
        params = {"domain": domain_filter} if domain_filter else None
        return self._request("GET", "/domains", params=params)

    def get_domain(self, domain_id: int):
        return self._request("GET", f"/domains/{domain_id}")

    # DNS
    def get_dns_records(self, domain_id: int, host=None, record_type=None):
        params = {}
        if host:
            params["host"] = host
        if record_type:
            params["type"] = record_type
        return self._request("GET", f"/domains/{domain_id}/dns", params=params or None)

    def create_dns_record(self, domain_id: int, record: dict):
        return self._request("POST", f"/domains/{domain_id}/dns", data=record)

    def update_dns_record(self, domain_id: int, record_id: int, record: dict):
        return self._request("PUT", f"/domains/{domain_id}/dns/{record_id}", data=record)

    def delete_dns_record(self, domain_id: int, record_id: int):
        return self._request("DELETE", f"/domains/{domain_id}/dns/{record_id}")

    # Forwards
    def get_forwards(self, domain_id: int):
        return self._request("GET", f"/domains/{domain_id}/forwards/")

    def create_forward(self, domain_id: int, forward: dict):
        return self._request("POST", f"/domains/{domain_id}/forwards/", data=forward)

    def update_forward(self, domain_id: int, host: str, forward: dict):
        return self._request("PUT", f"/domains/{domain_id}/forwards/{host}", data=forward)

    def delete_forward(self, domain_id: int, host: str):
        return self._request("DELETE", f"/domains/{domain_id}/forwards/{host}")

    # Invoices
    def get_invoices(self, status=None):
        params = {"status": status} if status else None
        return self._request("GET", "/invoices", params=params)

    # DDNS
    def update_ddns(self, hostname: str, myip=None):
        params = {"hostname": hostname}
        if myip:
            params["myip"] = myip
        return self._request("GET", "/dyndns/update", params=params)


def get_client(account_name: str = None):
    """Hent API-klient for en spesifikk konto eller valgt konto i session"""
    # Bruk konto fra parameter, session, eller default
    account = account_name or session.get('active_account')
    
    if account:
        token, secret = load_account(account)
    else:
        # Fallback til legacy eller enkelt-konto
        token, secret = load_credentials()
    
    if not token or not secret:
        return None
    return DomeneshopClient(token, secret)


# ==================== CONTEXT PROCESSOR ====================

@app.context_processor
def inject_csrf_token():
    """Inject CSRF-token i alle templates"""
    return {'csrf_token': generate_csrf_token()}


# ==================== ROUTES ====================

@app.route("/")
def index():
    """Hovedside"""
    client = get_client()
    if not client:
        return redirect(url_for("settings"))
    return render_template("index.html")


@app.route("/settings")
def settings():
    """Innstillinger-side"""
    info = get_credentials_info()
    accounts = list_accounts()
    active_account = session.get('active_account')
    
    # Auto-velg hvis bare én konto
    if not active_account and len(accounts) == 1:
        active_account = accounts[0]
    
    return render_template(
        "settings.html", 
        has_credentials=info['storage_type'] != 'none',
        storage_type=info['storage_type'],
        keyring_available=KEYRING_AVAILABLE,
        accounts=accounts,
        active_account=active_account,
        account_count=len(accounts)
    )


# ==================== API ENDPOINTS ====================

@app.route("/api/csrf-token")
def api_csrf_token():
    """Hent CSRF-token"""
    return jsonify({"csrf_token": generate_csrf_token()})


@app.route("/api/auth/status")
def api_auth_status():
    """Sjekk autentiseringsstatus"""
    client = get_client()
    if not client:
        return jsonify({"authenticated": False})
    try:
        client.get_domains()
        return jsonify({
            "authenticated": True,
            "storage_info": get_credentials_info()
        })
    except Exception:
        return jsonify({"authenticated": False})


@app.route("/api/auth/save", methods=["POST"])
@rate_limit(max_requests=5, window_seconds=60)
@csrf_protect
def api_auth_save():
    """Lagre credentials"""
    data = request.json or {}
    token = data.get("token", "").strip()
    secret = data.get("secret", "").strip()
    prefer_keychain = data.get("prefer_keychain", True)
    
    ip = get_client_ip()
    
    # Valider input
    if not token or not secret:
        log_invalid_input("token/secret", "missing", ip)
        return jsonify({"success": False, "error": "Token og secret er påkrevd"}), 400
    
    if not validate_token_format(token):
        log_invalid_input("token", "invalid format", ip)
        return jsonify({"success": False, "error": "Ugyldig token-format"}), 400
    
    if not validate_secret_format(secret):
        log_invalid_input("secret", "invalid format", ip)
        return jsonify({"success": False, "error": "Ugyldig secret-format"}), 400
    
    # Test credentials
    client = DomeneshopClient(token, secret)
    try:
        client.get_domains()
        
        # Lagre credentials
        success, storage_type = save_credentials(token, secret, prefer_keychain=prefer_keychain)
        
        if success:
            log_auth_success(ip, get_user_agent())
            log_credentials_saved(storage_type, ip)
            return jsonify({
                "success": True, 
                "storage_type": storage_type,
                "message": f"Credentials lagret i {storage_type}"
            })
        else:
            return jsonify({"success": False, "error": "Kunne ikke lagre credentials"}), 500
            
    except Exception as e:
        log_auth_failure(str(e), ip, get_user_agent())
        return jsonify({"success": False, "error": str(e)}), 401


@app.route("/api/auth/delete", methods=["POST"])
@rate_limit(max_requests=3, window_seconds=60)
@csrf_protect
def api_auth_delete():
    """Slett credentials"""
    ip = get_client_ip()
    
    if delete_credentials():
        log_credentials_deleted(ip)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Ingen credentials å slette"})


@app.route("/api/auth/migrate", methods=["POST"])
@rate_limit(max_requests=3, window_seconds=60)
@csrf_protect
def api_auth_migrate():
    """Migrer credentials til keychain"""
    if not KEYRING_AVAILABLE:
        return jsonify({"success": False, "error": "Keyring ikke tilgjengelig"}), 400
    
    success, message = migrate_file_to_keychain()
    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "error": message}), 400


# ==================== ACCOUNT ENDPOINTS ====================

@app.route("/api/accounts")
def api_accounts_list():
    """List alle kontoer"""
    accounts = list_accounts()
    active = session.get('active_account')
    
    # Hvis ingen aktiv konto er valgt, bruk første/eneste
    if not active and len(accounts) == 1:
        active = accounts[0]
    
    return jsonify({
        "accounts": accounts,
        "active_account": active,
        "count": len(accounts)
    })


@app.route("/api/accounts/select", methods=["POST"])
@csrf_protect
def api_accounts_select():
    """Velg aktiv konto for session"""
    data = request.json or {}
    account_name = data.get("account")
    
    if not account_name:
        return jsonify({"success": False, "error": "Kontonavn påkrevd"}), 400
    
    # Verifiser at kontoen finnes
    accounts = list_accounts()
    if account_name not in accounts:
        return jsonify({"success": False, "error": f"Konto '{account_name}' finnes ikke"}), 404
    
    # Verifiser at credentials fungerer
    token, secret = load_account(account_name)
    if not token or not secret:
        return jsonify({"success": False, "error": "Kunne ikke laste credentials"}), 500
    
    try:
        client = DomeneshopClient(token, secret)
        client.get_domains()
    except Exception as e:
        return jsonify({"success": False, "error": f"Autentisering feilet: {e}"}), 401
    
    # Lagre i session
    session['active_account'] = account_name
    log_account_selected(account_name, get_client_ip())
    
    return jsonify({
        "success": True,
        "active_account": account_name
    })


@app.route("/api/accounts", methods=["POST"])
@rate_limit(max_requests=5, window_seconds=60)
@csrf_protect
def api_accounts_create():
    """Opprett ny konto"""
    data = request.json or {}
    name = data.get("name", "").strip()
    token = data.get("token", "").strip()
    secret = data.get("secret", "").strip()
    prefer_keychain = data.get("prefer_keychain", True)
    
    ip = get_client_ip()
    
    # Valider input
    if not name:
        log_invalid_input("name", "missing", ip)
        return jsonify({"success": False, "error": "Kontonavn er påkrevd"}), 400
    
    if not token or not secret:
        log_invalid_input("token/secret", "missing", ip)
        return jsonify({"success": False, "error": "Token og secret er påkrevd"}), 400
    
    if not validate_token_format(token):
        log_invalid_input("token", "invalid format", ip)
        return jsonify({"success": False, "error": "Ugyldig token-format"}), 400
    
    if not validate_secret_format(secret):
        log_invalid_input("secret", "invalid format", ip)
        return jsonify({"success": False, "error": "Ugyldig secret-format"}), 400
    
    # Sjekk at navn ikke er i bruk
    if name in list_accounts():
        return jsonify({"success": False, "error": f"Konto '{name}' finnes allerede"}), 409
    
    # Test credentials
    try:
        client = DomeneshopClient(token, secret)
        domains = client.get_domains()
        domain_count = len(domains) if domains else 0
    except Exception as e:
        log_auth_failure(str(e), ip, get_user_agent())
        return jsonify({"success": False, "error": f"Autentisering feilet: {e}"}), 401
    
    # Lagre konto
    success, storage_type = save_account(name, token, secret, prefer_keychain)
    
    if success:
        log_auth_success(ip, get_user_agent())
        log_account_created(name, storage_type, ip)
        
        # Sett som aktiv konto
        session['active_account'] = name
        
        return jsonify({
            "success": True,
            "storage_type": storage_type,
            "domain_count": domain_count,
            "message": f"Konto '{name}' opprettet ({storage_type})"
        })
    else:
        return jsonify({"success": False, "error": f"Kunne ikke lagre konto: {storage_type}"}), 500


@app.route("/api/accounts/<name>", methods=["DELETE"])
@rate_limit(max_requests=3, window_seconds=60)
@csrf_protect
def api_accounts_delete(name):
    """Slett en konto"""
    ip = get_client_ip()
    
    if name not in list_accounts():
        return jsonify({"success": False, "error": f"Konto '{name}' finnes ikke"}), 404
    
    if delete_account(name):
        log_account_deleted(name, ip)
        
        # Fjern fra session hvis det var aktiv konto
        if session.get('active_account') == name:
            session.pop('active_account', None)
        
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Kunne ikke slette konto"}), 500


@app.route("/api/accounts/<old_name>/rename", methods=["POST"])
@csrf_protect
def api_accounts_rename(old_name):
    """Endre navn på en konto"""
    data = request.json or {}
    new_name = data.get("new_name", "").strip()
    
    if not new_name:
        return jsonify({"success": False, "error": "Nytt navn er påkrevd"}), 400
    
    success, message = rename_account(old_name, new_name)
    
    if success:
        log_account_renamed(old_name, new_name, get_client_ip())
        
        # Oppdater session hvis det var aktiv konto
        if session.get('active_account') == old_name:
            session['active_account'] = new_name
        
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "error": message}), 400


@app.route("/api/accounts/<name>/test")
def api_accounts_test(name):
    """Test tilkobling for en konto"""
    if name not in list_accounts():
        return jsonify({"success": False, "error": f"Konto '{name}' finnes ikke"}), 404
    
    token, secret = load_account(name)
    if not token or not secret:
        return jsonify({"success": False, "error": "Kunne ikke laste credentials"}), 500
    
    try:
        client = DomeneshopClient(token, secret)
        domains = client.get_domains()
        domain_count = len(domains) if domains else 0
        return jsonify({
            "success": True,
            "domain_count": domain_count,
            "message": f"OK - {domain_count} domener"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/domains")
def api_domains():
    """Hent alle domener"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        domains = client.get_domains()
        return jsonify(domains)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/domains/<int:domain_id>")
def api_domain(domain_id):
    """Hent et domene"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        domain = client.get_domain(domain_id)
        return jsonify(domain)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/domains/<int:domain_id>/dns")
def api_dns_list(domain_id):
    """Hent DNS-poster"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        records = client.get_dns_records(domain_id)
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/domains/<int:domain_id>/dns", methods=["POST"])
@csrf_protect
def api_dns_create(domain_id):
    """Opprett DNS-post"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        data = request.json
        result = client.create_dns_record(domain_id, data)
        log_dns_change("create", domain_id, result.get("id"), data.get("type"), get_client_ip())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/domains/<int:domain_id>/dns/<int:record_id>", methods=["PUT"])
@csrf_protect
def api_dns_update(domain_id, record_id):
    """Oppdater DNS-post"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        data = request.json
        client.update_dns_record(domain_id, record_id, data)
        log_dns_change("update", domain_id, record_id, data.get("type"), get_client_ip())
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/domains/<int:domain_id>/dns/<int:record_id>", methods=["DELETE"])
@csrf_protect
def api_dns_delete(domain_id, record_id):
    """Slett DNS-post"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        client.delete_dns_record(domain_id, record_id)
        log_dns_change("delete", domain_id, record_id, ip_address=get_client_ip())
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/domains/<int:domain_id>/forwards")
def api_forwards_list(domain_id):
    """Hent videresendinger"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        forwards = client.get_forwards(domain_id)
        return jsonify(forwards)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/domains/<int:domain_id>/forwards", methods=["POST"])
@csrf_protect
def api_forwards_create(domain_id):
    """Opprett videresending"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        data = request.json
        client.create_forward(domain_id, data)
        log_forward_change("create", domain_id, data.get("host", ""), get_client_ip())
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/domains/<int:domain_id>/forwards/<host>", methods=["DELETE"])
@csrf_protect
def api_forwards_delete(domain_id, host):
    """Slett videresending"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        client.delete_forward(domain_id, host)
        log_forward_change("delete", domain_id, host, get_client_ip())
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/invoices")
def api_invoices():
    """Hent fakturaer"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        status = request.args.get("status")
        invoices = client.get_invoices(status)
        return jsonify(invoices)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ddns", methods=["POST"])
@csrf_protect
def api_ddns():
    """Oppdater DDNS"""
    client = get_client()
    if not client:
        return jsonify({"error": "Ikke autentisert"}), 401
    try:
        data = request.json
        hostname = data.get("hostname")
        ip = data.get("ip")
        client.update_ddns(hostname, ip)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Opprett templates-mappe hvis den ikke finnes
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Port 5000 er ofte opptatt av AirPlay på Mac, bruk 5050
    PORT = 5050
    
    print("\n" + "="*50)
    print("  Domeneshop GUI")
    print("="*50)
    print(f"\n  Åpne nettleseren på: http://localhost:{PORT}")
    print("\n  Sikkerhetsfunksjoner aktivert:")
    print("  - Rate limiting på auth-endepunkter")
    print("  - CSRF-beskyttelse")
    print("  - Sikre session-cookies")
    print("  - Audit logging")
    print("="*50 + "\n")
    
    app.run(debug=True, port=PORT, host="127.0.0.1")
