#!/usr/bin/env python3
"""
Credentials-håndtering for Domeneshop CLI/GUI

Støtter flere kontoer med navngitte profiler.

Prioritert rekkefølge for enkelt-konto (bakoverkompatibilitet):
1. Miljøvariabler (DOMENESHOP_TOKEN, DOMENESHOP_SECRET)
2. System keychain (kryptert)
3. Fil-basert fallback (~/.domeneshop-credentials)

Multi-konto struktur (versjon 2):
{
  "version": 2,
  "accounts": {
    "Konto-navn": {"token": "xxx", "secret": "yyy"},
    ...
  }
}
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Tuple, List, Dict

# Konfigurasjon
SERVICE_NAME = "domeneshop-cli"
CONFIG_FILE = Path.home() / ".domeneshop-credentials"
CREDENTIAL_VERSION = 2

# Sjekk om keyring er tilgjengelig
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


class CredentialStorage:
    """Abstraksjon for credential-lagring med prioritert fallback"""
    
    @staticmethod
    def is_keyring_available() -> bool:
        """Sjekk om keyring er tilgjengelig og fungerer"""
        if not KEYRING_AVAILABLE:
            return False
        try:
            keyring.get_keyring()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_storage_type() -> str:
        """Returner hvilken lagringstype som brukes"""
        token = os.environ.get("DOMENESHOP_TOKEN")
        if token:
            return "environment"
        if CredentialStorage.is_keyring_available():
            try:
                # Sjekk for multi-konto først
                accounts = _list_keychain_accounts()
                if accounts:
                    return "keychain"
                # Sjekk for legacy enkelt-konto
                stored_token = keyring.get_password(SERVICE_NAME, "token")
                if stored_token:
                    return "keychain"
            except Exception:
                pass
        if CONFIG_FILE.exists():
            return "file"
        return "none"


# ==================== INTERNAL HELPERS ====================

def _get_keychain_key(account_name: str, key_type: str) -> str:
    """Generer keychain-nøkkel for en konto"""
    return f"{account_name}:{key_type}"


def _read_file_data() -> dict:
    """Les rå data fra konfigurasjonsfil"""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _write_file_data(data: dict) -> bool:
    """Skriv data til konfigurasjonsfil"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if sys.platform != "win32":
            CONFIG_FILE.chmod(0o600)
        return True
    except Exception as e:
        print(f"Kunne ikke lagre til fil: {e}", file=sys.stderr)
        return False


def _is_legacy_format(data: dict) -> bool:
    """Sjekk om data er i gammelt enkelt-konto format"""
    return "token" in data and "secret" in data and "version" not in data


def _is_multi_account_format(data: dict) -> bool:
    """Sjekk om data er i nytt multi-konto format"""
    return data.get("version") == CREDENTIAL_VERSION and "accounts" in data


def _list_keychain_accounts() -> List[str]:
    """List kontonavn lagret i keychain"""
    if not KEYRING_AVAILABLE:
        return []
    
    # Keychain har ikke native "list all" - vi må tracke kontonavn i en egen nøkkel
    try:
        accounts_json = keyring.get_password(SERVICE_NAME, "_accounts")
        if accounts_json:
            return json.loads(accounts_json)
    except Exception:
        pass
    return []


def _save_keychain_account_list(accounts: List[str]) -> bool:
    """Lagre liste over kontonavn i keychain"""
    if not KEYRING_AVAILABLE:
        return False
    try:
        keyring.set_password(SERVICE_NAME, "_accounts", json.dumps(accounts))
        return True
    except Exception:
        return False


# ==================== MULTI-ACCOUNT API ====================

def list_accounts() -> List[str]:
    """
    List alle lagrede kontoer.
    Sjekker både keychain og fil.
    
    Returns:
        Liste med kontonavn
    """
    accounts = set()
    
    # Fra keychain
    if KEYRING_AVAILABLE:
        keychain_accounts = _list_keychain_accounts()
        accounts.update(keychain_accounts)
    
    # Fra fil
    data = _read_file_data()
    if _is_multi_account_format(data):
        accounts.update(data.get("accounts", {}).keys())
    elif _is_legacy_format(data):
        # Legacy format - returner som "Standard"
        accounts.add("Standard")
    
    return sorted(list(accounts))


def save_account(name: str, token: str, secret: str, prefer_keychain: bool = True) -> Tuple[bool, str]:
    """
    Lagre en konto med navn.
    
    Args:
        name: Kontonavn
        token: API-token
        secret: API-secret
        prefer_keychain: Om keychain skal forsøkes først
    
    Returns:
        Tuple av (success: bool, storage_type: str)
    """
    if not name or not name.strip():
        return False, "Kontonavn kan ikke være tomt"
    
    name = name.strip()
    
    # Prøv keychain først
    if prefer_keychain and KEYRING_AVAILABLE:
        try:
            keyring.set_password(SERVICE_NAME, _get_keychain_key(name, "token"), token)
            keyring.set_password(SERVICE_NAME, _get_keychain_key(name, "secret"), secret)
            
            # Oppdater kontolisten
            accounts = _list_keychain_accounts()
            if name not in accounts:
                accounts.append(name)
                _save_keychain_account_list(accounts)
            
            return True, "keychain"
        except Exception as e:
            print(f"Kunne ikke lagre i keychain: {e}", file=sys.stderr)
    
    # Fallback til fil
    data = _read_file_data()
    
    # Migrer til nytt format hvis nødvendig
    if _is_legacy_format(data):
        old_token = data.get("token")
        old_secret = data.get("secret")
        data = {
            "version": CREDENTIAL_VERSION,
            "accounts": {
                "Standard": {"token": old_token, "secret": old_secret}
            }
        }
    elif not _is_multi_account_format(data):
        data = {"version": CREDENTIAL_VERSION, "accounts": {}}
    
    data["accounts"][name] = {"token": token, "secret": secret}
    
    if _write_file_data(data):
        return True, "file"
    
    return False, "failed"


def load_account(name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Les credentials for en spesifikk konto.
    
    Args:
        name: Kontonavn
    
    Returns:
        Tuple av (token, secret) eller (None, None)
    """
    if not name:
        return None, None
    
    # Prøv keychain først
    if KEYRING_AVAILABLE:
        try:
            token = keyring.get_password(SERVICE_NAME, _get_keychain_key(name, "token"))
            secret = keyring.get_password(SERVICE_NAME, _get_keychain_key(name, "secret"))
            if token and secret:
                return token, secret
        except Exception:
            pass
    
    # Prøv fil
    data = _read_file_data()
    
    if _is_multi_account_format(data):
        account = data.get("accounts", {}).get(name, {})
        return account.get("token"), account.get("secret")
    elif _is_legacy_format(data) and name == "Standard":
        return data.get("token"), data.get("secret")
    
    return None, None


def delete_account(name: str) -> bool:
    """
    Slett en konto.
    
    Args:
        name: Kontonavn
    
    Returns:
        True hvis slettet
    """
    deleted = False
    
    # Slett fra keychain
    if KEYRING_AVAILABLE:
        try:
            keyring.delete_password(SERVICE_NAME, _get_keychain_key(name, "token"))
            keyring.delete_password(SERVICE_NAME, _get_keychain_key(name, "secret"))
            
            accounts = _list_keychain_accounts()
            if name in accounts:
                accounts.remove(name)
                _save_keychain_account_list(accounts)
            
            deleted = True
        except Exception:
            pass
    
    # Slett fra fil
    data = _read_file_data()
    if _is_multi_account_format(data):
        if name in data.get("accounts", {}):
            del data["accounts"][name]
            _write_file_data(data)
            deleted = True
    
    return deleted


def rename_account(old_name: str, new_name: str) -> Tuple[bool, str]:
    """
    Endre navn på en konto.
    
    Args:
        old_name: Gammelt navn
        new_name: Nytt navn
    
    Returns:
        Tuple av (success: bool, message: str)
    """
    if not new_name or not new_name.strip():
        return False, "Nytt navn kan ikke være tomt"
    
    new_name = new_name.strip()
    
    # Sjekk at gammelt navn eksisterer
    token, secret = load_account(old_name)
    if not token or not secret:
        return False, f"Konto '{old_name}' finnes ikke"
    
    # Sjekk at nytt navn ikke eksisterer
    existing_accounts = list_accounts()
    if new_name in existing_accounts and new_name != old_name:
        return False, f"Konto '{new_name}' eksisterer allerede"
    
    # Lagre med nytt navn
    success, storage = save_account(new_name, token, secret)
    if not success:
        return False, "Kunne ikke lagre med nytt navn"
    
    # Slett gammelt navn
    delete_account(old_name)
    
    return True, f"Konto omdøpt fra '{old_name}' til '{new_name}'"


def migrate_single_to_multi(account_name: str = "Standard") -> Tuple[bool, str]:
    """
    Migrer eksisterende enkelt-konto til multi-konto struktur.
    
    Args:
        account_name: Navn å gi den eksisterende kontoen
    
    Returns:
        Tuple av (success: bool, message: str)
    """
    # Sjekk for legacy fil-data
    data = _read_file_data()
    if _is_legacy_format(data):
        token = data.get("token")
        secret = data.get("secret")
        
        new_data = {
            "version": CREDENTIAL_VERSION,
            "accounts": {
                account_name: {"token": token, "secret": secret}
            }
        }
        
        if _write_file_data(new_data):
            return True, f"Migrert fil-credentials til konto '{account_name}'"
    
    # Sjekk for legacy keychain-data
    if KEYRING_AVAILABLE:
        try:
            token = keyring.get_password(SERVICE_NAME, "token")
            secret = keyring.get_password(SERVICE_NAME, "secret")
            
            if token and secret:
                # Lagre med nytt format
                keyring.set_password(SERVICE_NAME, _get_keychain_key(account_name, "token"), token)
                keyring.set_password(SERVICE_NAME, _get_keychain_key(account_name, "secret"), secret)
                
                # Oppdater kontolisten
                accounts = _list_keychain_accounts()
                if account_name not in accounts:
                    accounts.append(account_name)
                    _save_keychain_account_list(accounts)
                
                # Slett gamle nøkler
                try:
                    keyring.delete_password(SERVICE_NAME, "token")
                    keyring.delete_password(SERVICE_NAME, "secret")
                except Exception:
                    pass
                
                return True, f"Migrert keychain-credentials til konto '{account_name}'"
        except Exception:
            pass
    
    return False, "Ingen legacy credentials å migrere"


def needs_migration() -> bool:
    """
    Sjekk om det finnes legacy credentials som bør migreres.
    
    Returns:
        True hvis migrering trengs
    """
    # Sjekk fil
    data = _read_file_data()
    if _is_legacy_format(data):
        return True
    
    # Sjekk keychain
    if KEYRING_AVAILABLE:
        try:
            token = keyring.get_password(SERVICE_NAME, "token")
            if token:
                return True
        except Exception:
            pass
    
    return False


# ==================== LEGACY COMPATIBILITY API ====================

def save_credentials(token: str, secret: str, prefer_keychain: bool = True) -> Tuple[bool, str]:
    """
    Lagre credentials (legacy API - bruker "Standard" som kontonavn).
    
    For bakoverkompatibilitet. Nye implementasjoner bør bruke save_account().
    """
    return save_account("Standard", token, secret, prefer_keychain)


def load_credentials(account_name: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Les credentials.
    
    Args:
        account_name: Spesifikk konto å lese. Hvis None, brukes miljøvariabler
                     eller første/eneste konto.
    
    Returns:
        Tuple av (token, secret) eller (None, None)
    """
    # 1. Miljøvariabler har alltid høyest prioritet
    token = os.environ.get("DOMENESHOP_TOKEN")
    secret = os.environ.get("DOMENESHOP_SECRET")
    if token and secret:
        return token, secret
    
    # 2. Spesifikk konto forespurt
    if account_name:
        return load_account(account_name)
    
    # 3. Sjekk for legacy format (enkelt-konto)
    if KEYRING_AVAILABLE:
        try:
            token = keyring.get_password(SERVICE_NAME, "token")
            secret = keyring.get_password(SERVICE_NAME, "secret")
            if token and secret:
                return token, secret
        except Exception:
            pass
    
    data = _read_file_data()
    if _is_legacy_format(data):
        return data.get("token"), data.get("secret")
    
    # 4. Multi-konto - returner første hvis bare én finnes
    accounts = list_accounts()
    if len(accounts) == 1:
        return load_account(accounts[0])
    
    # Flere kontoer eller ingen - returner None (bruker må velge)
    return None, None


def delete_credentials() -> bool:
    """
    Slett alle lagrede credentials (alle kontoer).
    """
    accounts = list_accounts()
    for account in accounts:
        delete_account(account)
    
    # Slett også legacy nøkler
    if KEYRING_AVAILABLE:
        try:
            keyring.delete_password(SERVICE_NAME, "token")
            keyring.delete_password(SERVICE_NAME, "secret")
            keyring.delete_password(SERVICE_NAME, "_accounts")
        except Exception:
            pass
    
    # Slett fil helt
    try:
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
    except Exception:
        pass
    
    return True


def migrate_file_to_keychain() -> Tuple[bool, str]:
    """
    Migrer alle kontoer fra fil til keychain.
    """
    if not KEYRING_AVAILABLE:
        return False, "Keyring er ikke tilgjengelig. Installer med: pip install keyring"
    
    data = _read_file_data()
    
    if _is_legacy_format(data):
        # Migrer først til multi-format
        migrate_single_to_multi("Standard")
        data = _read_file_data()
    
    if not _is_multi_account_format(data):
        return False, "Ingen fil-credentials å migrere"
    
    migrated = 0
    for name, creds in data.get("accounts", {}).items():
        token = creds.get("token")
        secret = creds.get("secret")
        if token and secret:
            try:
                keyring.set_password(SERVICE_NAME, _get_keychain_key(name, "token"), token)
                keyring.set_password(SERVICE_NAME, _get_keychain_key(name, "secret"), secret)
                
                accounts = _list_keychain_accounts()
                if name not in accounts:
                    accounts.append(name)
                    _save_keychain_account_list(accounts)
                
                migrated += 1
            except Exception:
                pass
    
    if migrated > 0:
        # Slett fil
        try:
            CONFIG_FILE.unlink()
        except Exception:
            pass
        return True, f"Migrert {migrated} konto(er) til keychain"
    
    return False, "Ingen kontoer ble migrert"


def get_credentials_info() -> dict:
    """
    Returner informasjon om credential-lagring.
    """
    accounts = list_accounts()
    
    info = {
        "keyring_available": KEYRING_AVAILABLE,
        "keyring_backend": None,
        "file_exists": CONFIG_FILE.exists(),
        "file_path": str(CONFIG_FILE),
        "env_configured": bool(os.environ.get("DOMENESHOP_TOKEN")),
        "storage_type": CredentialStorage.get_storage_type(),
        "account_count": len(accounts),
        "accounts": accounts,
        "needs_migration": needs_migration(),
    }
    
    if KEYRING_AVAILABLE:
        try:
            info["keyring_backend"] = type(keyring.get_keyring()).__name__
        except Exception:
            pass
    
    return info
