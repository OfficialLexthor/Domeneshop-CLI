#!/usr/bin/env python3
"""
Audit logging for Domeneshop CLI/GUI

Logger sikkerhetshendelser til fil for overvåking og feilsøking.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from functools import wraps

# Konfigurasjon
AUDIT_LOG_FILE = Path.home() / ".domeneshop-audit.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Hendelsestyper
class AuditEvent:
    """Konstanter for audit-hendelser"""
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    CREDENTIALS_SAVED = "CREDENTIALS_SAVED"
    CREDENTIALS_DELETED = "CREDENTIALS_DELETED"
    CREDENTIALS_MIGRATED = "CREDENTIALS_MIGRATED"
    # Konto-hendelser
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    ACCOUNT_DELETED = "ACCOUNT_DELETED"
    ACCOUNT_RENAMED = "ACCOUNT_RENAMED"
    ACCOUNT_SELECTED = "ACCOUNT_SELECTED"
    # DNS/Forward-hendelser
    DNS_CREATED = "DNS_CREATED"
    DNS_UPDATED = "DNS_UPDATED"
    DNS_DELETED = "DNS_DELETED"
    FORWARD_CREATED = "FORWARD_CREATED"
    FORWARD_UPDATED = "FORWARD_UPDATED"
    FORWARD_DELETED = "FORWARD_DELETED"
    # Sikkerhetshendelser
    RATE_LIMIT_HIT = "RATE_LIMIT_HIT"
    CSRF_FAILURE = "CSRF_FAILURE"
    INVALID_INPUT = "INVALID_INPUT"


# Opprett logger
_audit_logger: Optional[logging.Logger] = None


def _get_logger() -> logging.Logger:
    """Hent eller opprett audit logger"""
    global _audit_logger
    
    if _audit_logger is not None:
        return _audit_logger
    
    _audit_logger = logging.getLogger("domeneshop.audit")
    _audit_logger.setLevel(logging.INFO)
    
    # Unngå duplikate handlers
    if not _audit_logger.handlers:
        try:
            # Fil-handler
            file_handler = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
            _audit_logger.addHandler(file_handler)
            
            # Sett filrettigheter til kun eier
            if sys.platform != "win32":
                AUDIT_LOG_FILE.chmod(0o600)
        except Exception as e:
            # Fallback til stderr hvis fil ikke kan opprettes
            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
            _audit_logger.addHandler(stderr_handler)
            _audit_logger.warning(f"Kunne ikke opprette audit-loggfil: {e}")
    
    return _audit_logger


def log_event(
    event_type: str,
    message: str = "",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    domain_id: Optional[int] = None,
    record_id: Optional[int] = None,
    extra: Optional[dict] = None
) -> None:
    """
    Logg en sikkerhetshendelse.
    
    Args:
        event_type: Type hendelse (bruk AuditEvent-konstanter)
        message: Beskrivende melding
        ip_address: Klient IP-adresse (for GUI)
        user_agent: Klient User-Agent (for GUI)
        domain_id: Relatert domene-ID
        record_id: Relatert post-ID (DNS, forward, etc.)
        extra: Ekstra metadata
    """
    logger = _get_logger()
    
    # Bygg loggmelding
    parts = [event_type]
    
    if message:
        parts.append(message)
    
    if ip_address:
        parts.append(f"IP: {ip_address}")
    
    if user_agent:
        # Kutt User-Agent til rimelig lengde
        ua_short = user_agent[:100] + "..." if len(user_agent) > 100 else user_agent
        parts.append(f"UA: {ua_short}")
    
    if domain_id is not None:
        parts.append(f"Domain: {domain_id}")
    
    if record_id is not None:
        parts.append(f"Record: {record_id}")
    
    if extra:
        for key, value in extra.items():
            parts.append(f"{key}: {value}")
    
    log_message = " | ".join(parts)
    
    # Velg loggnivå basert på hendelsestype
    if event_type in (AuditEvent.AUTH_FAILURE, AuditEvent.RATE_LIMIT_HIT, 
                      AuditEvent.CSRF_FAILURE, AuditEvent.INVALID_INPUT):
        logger.warning(log_message)
    else:
        logger.info(log_message)


# ==================== CONVENIENCE FUNCTIONS ====================

def log_auth_success(ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
    """Logg vellykket autentisering"""
    log_event(AuditEvent.AUTH_SUCCESS, ip_address=ip_address, user_agent=user_agent)


def log_auth_failure(reason: str = "", ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
    """Logg mislykket autentisering"""
    log_event(AuditEvent.AUTH_FAILURE, message=reason, ip_address=ip_address, user_agent=user_agent)


def log_credentials_saved(storage_type: str, ip_address: Optional[str] = None) -> None:
    """Logg at credentials ble lagret"""
    log_event(AuditEvent.CREDENTIALS_SAVED, message=f"Storage: {storage_type}", ip_address=ip_address)


def log_credentials_deleted(ip_address: Optional[str] = None) -> None:
    """Logg at credentials ble slettet"""
    log_event(AuditEvent.CREDENTIALS_DELETED, ip_address=ip_address)


def log_credentials_migrated(from_storage: str, to_storage: str) -> None:
    """Logg at credentials ble migrert"""
    log_event(AuditEvent.CREDENTIALS_MIGRATED, message=f"From: {from_storage} To: {to_storage}")


def log_dns_change(action: str, domain_id: int, record_id: Optional[int] = None, 
                   record_type: Optional[str] = None, ip_address: Optional[str] = None) -> None:
    """Logg DNS-endring"""
    event_map = {
        "create": AuditEvent.DNS_CREATED,
        "update": AuditEvent.DNS_UPDATED,
        "delete": AuditEvent.DNS_DELETED,
    }
    event_type = event_map.get(action, AuditEvent.DNS_UPDATED)
    extra = {"type": record_type} if record_type else None
    log_event(event_type, domain_id=domain_id, record_id=record_id, ip_address=ip_address, extra=extra)


def log_forward_change(action: str, domain_id: int, host: str, ip_address: Optional[str] = None) -> None:
    """Logg forward-endring"""
    event_map = {
        "create": AuditEvent.FORWARD_CREATED,
        "update": AuditEvent.FORWARD_UPDATED,
        "delete": AuditEvent.FORWARD_DELETED,
    }
    event_type = event_map.get(action, AuditEvent.FORWARD_UPDATED)
    log_event(event_type, message=f"Host: {host}", domain_id=domain_id, ip_address=ip_address)


def log_rate_limit(ip_address: str, endpoint: str) -> None:
    """Logg at rate limit ble nådd"""
    log_event(AuditEvent.RATE_LIMIT_HIT, message=f"Endpoint: {endpoint}", ip_address=ip_address)


def log_csrf_failure(ip_address: Optional[str] = None, endpoint: Optional[str] = None) -> None:
    """Logg CSRF-valideringsfeil"""
    message = f"Endpoint: {endpoint}" if endpoint else ""
    log_event(AuditEvent.CSRF_FAILURE, message=message, ip_address=ip_address)


def log_invalid_input(field: str, reason: str = "", ip_address: Optional[str] = None) -> None:
    """Logg ugyldig input"""
    message = f"Field: {field}"
    if reason:
        message += f" Reason: {reason}"
    log_event(AuditEvent.INVALID_INPUT, message=message, ip_address=ip_address)


# ==================== ACCOUNT LOGGING ====================

def log_account_created(account_name: str, storage_type: str, ip_address: Optional[str] = None) -> None:
    """Logg at en konto ble opprettet"""
    log_event(AuditEvent.ACCOUNT_CREATED, message=f"Account: {account_name} Storage: {storage_type}", ip_address=ip_address)


def log_account_deleted(account_name: str, ip_address: Optional[str] = None) -> None:
    """Logg at en konto ble slettet"""
    log_event(AuditEvent.ACCOUNT_DELETED, message=f"Account: {account_name}", ip_address=ip_address)


def log_account_renamed(old_name: str, new_name: str, ip_address: Optional[str] = None) -> None:
    """Logg at en konto ble omdøpt"""
    log_event(AuditEvent.ACCOUNT_RENAMED, message=f"From: {old_name} To: {new_name}", ip_address=ip_address)


def log_account_selected(account_name: str, ip_address: Optional[str] = None) -> None:
    """Logg at en konto ble valgt"""
    log_event(AuditEvent.ACCOUNT_SELECTED, message=f"Account: {account_name}", ip_address=ip_address)


# ==================== FLASK HELPERS ====================

def get_client_ip() -> Optional[str]:
    """
    Hent klient IP fra Flask request.
    Håndterer X-Forwarded-For for reverse proxies.
    """
    try:
        from flask import request
        
        # Sjekk X-Forwarded-For først (for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Første IP i listen er klienten
            return forwarded.split(",")[0].strip()
        
        return request.remote_addr
    except Exception:
        return None


def get_user_agent() -> Optional[str]:
    """Hent User-Agent fra Flask request"""
    try:
        from flask import request
        return request.headers.get("User-Agent")
    except Exception:
        return None


def audit_route(event_type: str):
    """
    Dekorator for å automatisk logge Flask-route-kall.
    
    Bruk:
        @app.route("/api/something", methods=["POST"])
        @audit_route(AuditEvent.SOME_EVENT)
        def some_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            log_event(
                event_type,
                ip_address=get_client_ip(),
                user_agent=get_user_agent()
            )
            return result
        return wrapper
    return decorator


# ==================== UTILITY ====================

def get_audit_log_path() -> Path:
    """Returner path til audit-loggfilen"""
    return AUDIT_LOG_FILE


def get_recent_events(count: int = 50) -> list:
    """
    Les de siste N hendelsene fra audit-loggen.
    
    Args:
        count: Antall hendelser å returnere
    
    Returns:
        Liste med logglinjer (nyeste først)
    """
    if not AUDIT_LOG_FILE.exists():
        return []
    
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Returner de siste N linjene, reversert (nyeste først)
        return [line.strip() for line in reversed(lines[-count:])]
    except Exception:
        return []
