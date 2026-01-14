#!/usr/bin/env python3
"""
Domeneshop CLI - Et kommandolinjeverktøy for Domeneshop API

Bruk: domeneshop [KOMMANDO] [ALTERNATIVER]

Krever miljøvariabler:
  DOMENESHOP_TOKEN  - API-token fra domeneshop.no/admin?view=api
  DOMENESHOP_SECRET - API-hemmelighet

Eller lagrede credentials via 'domeneshop configure'
"""

import os
import sys
import json
import click
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from tabulate import tabulate

# Import av sikkerhetsmoduler
from credentials import (
    load_credentials, save_credentials, delete_credentials,
    migrate_file_to_keychain, get_credentials_info, CONFIG_FILE,
    KEYRING_AVAILABLE, list_accounts, save_account, load_account,
    delete_account, rename_account, migrate_single_to_multi, needs_migration
)
from audit import (
    log_auth_success, log_auth_failure, log_credentials_saved,
    log_credentials_deleted, log_credentials_migrated, log_dns_change,
    log_account_created, log_account_deleted, log_account_renamed,
    log_account_selected
)

# Global variabel for valgt konto
_selected_account: Optional[str] = None

# API konfigurasjon
API_BASE_URL = "https://api.domeneshop.no/v0"


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

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
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
            if e.response.status_code == 401:
                log_auth_failure("Invalid credentials")
                raise click.ClickException("Autentisering feilet. Sjekk DOMENESHOP_TOKEN og DOMENESHOP_SECRET.")
            elif e.response.status_code == 404:
                raise click.ClickException(f"Ressurs ikke funnet: {endpoint}")
            elif e.response.status_code == 400:
                raise click.ClickException(f"Ugyldig forespørsel: {e.response.text}")
            elif e.response.status_code == 409:
                raise click.ClickException(f"Konflikt: {e.response.text}")
            else:
                raise click.ClickException(f"API-feil ({e.response.status_code}): {e.response.text}")
        except requests.exceptions.ConnectionError:
            raise click.ClickException("Kunne ikke koble til Domeneshop API")

    # Domener
    def get_domains(self, domain_filter: Optional[str] = None) -> List[Dict]:
        params = {"domain": domain_filter} if domain_filter else None
        return self._request("GET", "/domains", params=params)

    def get_domain(self, domain_id: int) -> Dict:
        return self._request("GET", f"/domains/{domain_id}")

    # DNS
    def get_dns_records(self, domain_id: int, host: Optional[str] = None, record_type: Optional[str] = None) -> List[Dict]:
        params = {}
        if host:
            params["host"] = host
        if record_type:
            params["type"] = record_type
        return self._request("GET", f"/domains/{domain_id}/dns", params=params or None)

    def get_dns_record(self, domain_id: int, record_id: int) -> Dict:
        return self._request("GET", f"/domains/{domain_id}/dns/{record_id}")

    def create_dns_record(self, domain_id: int, record: Dict) -> Dict:
        return self._request("POST", f"/domains/{domain_id}/dns", data=record)

    def update_dns_record(self, domain_id: int, record_id: int, record: Dict) -> None:
        return self._request("PUT", f"/domains/{domain_id}/dns/{record_id}", data=record)

    def delete_dns_record(self, domain_id: int, record_id: int) -> None:
        return self._request("DELETE", f"/domains/{domain_id}/dns/{record_id}")

    # Forwards
    def get_forwards(self, domain_id: int) -> List[Dict]:
        return self._request("GET", f"/domains/{domain_id}/forwards/")

    def get_forward(self, domain_id: int, host: str) -> Dict:
        return self._request("GET", f"/domains/{domain_id}/forwards/{host}")

    def create_forward(self, domain_id: int, forward: Dict) -> None:
        return self._request("POST", f"/domains/{domain_id}/forwards/", data=forward)

    def update_forward(self, domain_id: int, host: str, forward: Dict) -> Dict:
        return self._request("PUT", f"/domains/{domain_id}/forwards/{host}", data=forward)

    def delete_forward(self, domain_id: int, host: str) -> None:
        return self._request("DELETE", f"/domains/{domain_id}/forwards/{host}")

    # Invoices
    def get_invoices(self, status: Optional[str] = None) -> List[Dict]:
        params = {"status": status} if status else None
        return self._request("GET", "/invoices", params=params)

    def get_invoice(self, invoice_id: int) -> Dict:
        return self._request("GET", f"/invoices/{invoice_id}")

    # DDNS
    def update_ddns(self, hostname: str, myip: Optional[str] = None) -> None:
        params = {"hostname": hostname}
        if myip:
            params["myip"] = myip
        return self._request("GET", "/dyndns/update", params=params)


def prompt_for_credentials() -> Tuple[str, str]:
    """Spør bruker om credentials interaktivt"""
    click.echo("\nMangler API-credentials.")
    click.echo("Generer token og secret på: https://www.domeneshop.no/admin?view=api\n")

    token = click.prompt("API-token", type=str)
    secret = click.prompt("API-secret", type=str, hide_input=True)

    return token, secret


def select_account_interactive() -> Optional[str]:
    """Interaktiv konto-velger"""
    accounts = list_accounts()
    
    if len(accounts) == 0:
        return None
    elif len(accounts) == 1:
        return accounts[0]
    
    click.echo("\nVelg konto:")
    for i, name in enumerate(accounts, 1):
        click.echo(f"  {i}) {name}")
    
    while True:
        try:
            choice = click.prompt("\nValg", type=int, default=1)
            if 1 <= choice <= len(accounts):
                selected = accounts[choice - 1]
                log_account_selected(selected)
                return selected
            click.echo(f"Ugyldig valg. Velg 1-{len(accounts)}.")
        except ValueError:
            click.echo("Skriv inn et tall.")


def get_client(account_name: Optional[str] = None) -> DomeneshopClient:
    """Hent API-klient med autentisering
    
    Args:
        account_name: Navn på konto å bruke. Hvis None, bruk global valg eller velg interaktivt.
    """
    global _selected_account
    
    # Sjekk for migrering først
    if needs_migration():
        click.echo("\nEksisterende credentials funnet (gammelt format).")
        name = click.prompt("Gi kontoen et navn", default="Standard")
        success, msg = migrate_single_to_multi(name)
        if success:
            click.echo(f"✓ {msg}")
    
    # Bestem hvilken konto å bruke
    effective_account = account_name or _selected_account
    
    # Sjekk om vi trenger å velge interaktivt
    accounts = list_accounts()
    if len(accounts) > 1 and not effective_account:
        effective_account = select_account_interactive()
        _selected_account = effective_account
    elif len(accounts) == 1:
        effective_account = accounts[0]
    
    # Last credentials
    token, secret = load_credentials(effective_account)

    # Spør interaktivt hvis ingen credentials
    if not token or not secret:
        token, secret = prompt_for_credentials()

        # Verifiser at credentials fungerer
        client = DomeneshopClient(token, secret)
        try:
            client.get_domains()  # Test API-kall
            log_auth_success()
            click.echo("\nAutentisering vellykket!")

            if click.confirm("Vil du lagre credentials for fremtidig bruk?", default=True):
                name = click.prompt("Gi kontoen et navn", default="Standard")
                success, storage_type = save_account(name, token, secret)
                if success:
                    log_account_created(name, storage_type)
                    log_credentials_saved(storage_type)
                    if storage_type == "keychain":
                        click.echo(f"✓ Konto '{name}' lagret sikkert i system keychain")
                    else:
                        click.echo(f"✓ Konto '{name}' lagret til {CONFIG_FILE}")
                else:
                    click.echo("Kunne ikke lagre credentials", err=True)
        except click.ClickException:
            log_auth_failure("Invalid credentials on first setup")
            raise click.ClickException("Autentisering feilet. Sjekk token og secret.")

        return client

    return DomeneshopClient(token, secret)


# Hjelpefunksjoner for output
def format_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def print_table(data: List[Dict], headers: List[str], keys: List[str]):
    """Skriv ut data som tabell"""
    rows = [[row.get(k, "") for k in keys] for row in data]
    click.echo(tabulate(rows, headers=headers, tablefmt="simple"))


# CLI-grupper og kommandoer
@click.group()
@click.version_option(version="1.2.0", prog_name="domeneshop")
@click.option("--account", "-a", "account_name", 
              help="Velg konto å bruke (hopp over interaktiv velger)")
@click.pass_context
def cli(ctx, account_name: Optional[str]):
    """Domeneshop CLI - Administrer domener, DNS og mer via kommandolinjen.
    
    Credentials kan konfigureres via:
    - Miljøvariabler (DOMENESHOP_TOKEN, DOMENESHOP_SECRET)
    - System keychain (anbefalt)
    - Konfigurasjonsfil (~/.domeneshop-credentials)
    
    Støtter flere kontoer. Bruk --account for å velge konto direkte.
    """
    global _selected_account
    ctx.ensure_object(dict)
    
    if account_name:
        # Verifiser at kontoen finnes
        accounts = list_accounts()
        if account_name not in accounts:
            raise click.ClickException(f"Konto '{account_name}' finnes ikke. Tilgjengelige: {', '.join(accounts)}")
        _selected_account = account_name
        ctx.obj["account"] = account_name


# === DOMENER ===
@cli.group()
def domains():
    """Administrer domener"""
    pass


@domains.command("list")
@click.option("--filter", "-f", "domain_filter", help="Filtrer domener (f.eks. '.no')")
@click.option("--json", "as_json", is_flag=True, help="Output som JSON")
def domains_list(domain_filter: Optional[str], as_json: bool):
    """List alle domener"""
    client = get_client()
    domains = client.get_domains(domain_filter)
    
    if as_json:
        click.echo(format_json(domains))
    else:
        if not domains:
            click.echo("Ingen domener funnet.")
            return
        headers = ["ID", "Domene", "Status", "Utløper", "Fornyes"]
        keys = ["id", "domain", "status", "expiry_date", "renew"]
        print_table(domains, headers, keys)


@domains.command("show")
@click.argument("domain_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output som JSON")
def domains_show(domain_id: int, as_json: bool):
    """Vis detaljer for et domene"""
    client = get_client()
    domain = client.get_domain(domain_id)
    
    if as_json:
        click.echo(format_json(domain))
    else:
        click.echo(f"\n{'='*50}")
        click.echo(f"Domene: {domain.get('domain')}")
        click.echo(f"{'='*50}")
        click.echo(f"ID:           {domain.get('id')}")
        click.echo(f"Status:       {domain.get('status')}")
        click.echo(f"Registrant:   {domain.get('registrant')}")
        click.echo(f"Registrert:   {domain.get('registered_date')}")
        click.echo(f"Utløper:      {domain.get('expiry_date')}")
        click.echo(f"Auto-fornyes: {'Ja' if domain.get('renew') else 'Nei'}")
        
        nameservers = domain.get('nameservers', [])
        if nameservers:
            click.echo(f"\nNavneservere:")
            for ns in nameservers:
                click.echo(f"  - {ns}")
        
        services = domain.get('services', {})
        if services:
            click.echo(f"\nTjenester:")
            click.echo(f"  Registrar: {'Ja' if services.get('registrar') else 'Nei'}")
            click.echo(f"  DNS:       {'Ja' if services.get('dns') else 'Nei'}")
            click.echo(f"  E-post:    {'Ja' if services.get('email') else 'Nei'}")
            click.echo(f"  Webhotell: {services.get('webhotel', 'none')}")


# === DNS ===
@cli.group()
def dns():
    """Administrer DNS-poster"""
    pass


@dns.command("list")
@click.argument("domain_id", type=int)
@click.option("--host", "-h", help="Filtrer på host")
@click.option("--type", "-t", "record_type", help="Filtrer på type (A, AAAA, CNAME, MX, TXT, SRV)")
@click.option("--json", "as_json", is_flag=True, help="Output som JSON")
def dns_list(domain_id: int, host: Optional[str], record_type: Optional[str], as_json: bool):
    """List DNS-poster for et domene"""
    client = get_client()
    records = client.get_dns_records(domain_id, host, record_type)
    
    if as_json:
        click.echo(format_json(records))
    else:
        if not records:
            click.echo("Ingen DNS-poster funnet.")
            return
        headers = ["ID", "Type", "Host", "Data", "TTL", "Pri"]
        rows = []
        for r in records:
            rows.append([
                r.get("id"),
                r.get("type"),
                r.get("host"),
                r.get("data"),
                r.get("ttl"),
                r.get("priority", "")
            ])
        click.echo(tabulate(rows, headers=headers, tablefmt="simple"))


@dns.command("show")
@click.argument("domain_id", type=int)
@click.argument("record_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output som JSON")
def dns_show(domain_id: int, record_id: int, as_json: bool):
    """Vis en spesifikk DNS-post"""
    client = get_client()
    record = client.get_dns_record(domain_id, record_id)
    
    if as_json:
        click.echo(format_json(record))
    else:
        click.echo(f"\nDNS-post #{record.get('id')}")
        click.echo(f"{'='*40}")
        for key, value in record.items():
            click.echo(f"{key}: {value}")


@dns.command("add")
@click.argument("domain_id", type=int)
@click.option("--type", "-t", "record_type", required=True, 
              type=click.Choice(["A", "AAAA", "CNAME", "MX", "TXT", "SRV"]),
              help="DNS-posttype")
@click.option("--host", "-h", required=True, help="Host/subdomene (@ for rot)")
@click.option("--data", "-d", required=True, help="Verdi (IP, hostname, tekst)")
@click.option("--ttl", type=int, default=3600, help="TTL i sekunder (standard: 3600)")
@click.option("--priority", "-p", type=int, help="Prioritet (for MX og SRV)")
@click.option("--weight", "-w", type=int, help="Vekt (kun SRV)")
@click.option("--port", type=int, help="Port (kun SRV)")
def dns_add(domain_id: int, record_type: str, host: str, data: str, ttl: int,
            priority: Optional[int], weight: Optional[int], port: Optional[int]):
    """Legg til en DNS-post"""
    client = get_client()
    
    record = {
        "type": record_type,
        "host": host,
        "data": data,
        "ttl": ttl
    }
    
    if record_type == "MX":
        if priority is None:
            raise click.ClickException("MX-poster krever --priority")
        record["priority"] = priority
    elif record_type == "SRV":
        if priority is None or weight is None or port is None:
            raise click.ClickException("SRV-poster krever --priority, --weight og --port")
        record["priority"] = priority
        record["weight"] = weight
        record["port"] = port
    
    result = client.create_dns_record(domain_id, record)
    record_id = result.get('id')
    log_dns_change("create", domain_id, record_id, record_type)
    click.echo(f"✓ DNS-post opprettet med ID: {record_id}")


@dns.command("update")
@click.argument("domain_id", type=int)
@click.argument("record_id", type=int)
@click.option("--host", "-h", help="Ny host/subdomene")
@click.option("--data", "-d", help="Ny verdi")
@click.option("--ttl", type=int, help="Ny TTL")
@click.option("--priority", "-p", type=int, help="Ny prioritet")
@click.option("--weight", "-w", type=int, help="Ny vekt")
@click.option("--port", type=int, help="Ny port")
def dns_update(domain_id: int, record_id: int, host: Optional[str], data: Optional[str],
               ttl: Optional[int], priority: Optional[int], weight: Optional[int], port: Optional[int]):
    """Oppdater en DNS-post"""
    client = get_client()
    
    # Hent eksisterende post først
    existing = client.get_dns_record(domain_id, record_id)
    
    # Oppdater kun angitte felt
    if host is not None:
        existing["host"] = host
    if data is not None:
        existing["data"] = data
    if ttl is not None:
        existing["ttl"] = ttl
    if priority is not None:
        existing["priority"] = priority
    if weight is not None:
        existing["weight"] = weight
    if port is not None:
        existing["port"] = port
    
    client.update_dns_record(domain_id, record_id, existing)
    log_dns_change("update", domain_id, record_id, existing.get("type"))
    click.echo(f"✓ DNS-post #{record_id} oppdatert")


@dns.command("delete")
@click.argument("domain_id", type=int)
@click.argument("record_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Bekreft sletting uten spørsmål")
def dns_delete(domain_id: int, record_id: int, yes: bool):
    """Slett en DNS-post"""
    client = get_client()
    
    if not yes:
        # Vis hva som skal slettes
        record = client.get_dns_record(domain_id, record_id)
        click.echo(f"\nDu er i ferd med å slette:")
        click.echo(f"  Type: {record.get('type')}")
        click.echo(f"  Host: {record.get('host')}")
        click.echo(f"  Data: {record.get('data')}")
        
        if not click.confirm("\nEr du sikker?"):
            click.echo("Avbrutt.")
            return
    
    # Hent type for logging før sletting
    record = client.get_dns_record(domain_id, record_id)
    client.delete_dns_record(domain_id, record_id)
    log_dns_change("delete", domain_id, record_id, record.get("type"))
    click.echo(f"✓ DNS-post #{record_id} slettet")


# === FORWARDS ===
@cli.group()
def forwards():
    """Administrer HTTP-videresendinger"""
    pass


@forwards.command("list")
@click.argument("domain_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output som JSON")
def forwards_list(domain_id: int, as_json: bool):
    """List HTTP-videresendinger for et domene"""
    client = get_client()
    fwds = client.get_forwards(domain_id)
    
    if as_json:
        click.echo(format_json(fwds))
    else:
        if not fwds:
            click.echo("Ingen videresendinger funnet.")
            return
        headers = ["Host", "URL", "Frame"]
        keys = ["host", "url", "frame"]
        print_table(fwds, headers, keys)


@forwards.command("show")
@click.argument("domain_id", type=int)
@click.argument("host")
@click.option("--json", "as_json", is_flag=True, help="Output som JSON")
def forwards_show(domain_id: int, host: str, as_json: bool):
    """Vis en videresending"""
    client = get_client()
    fwd = client.get_forward(domain_id, host)
    
    if as_json:
        click.echo(format_json(fwd))
    else:
        click.echo(f"\nVideresending for '{host}'")
        click.echo(f"{'='*40}")
        click.echo(f"Host:  {fwd.get('host')}")
        click.echo(f"URL:   {fwd.get('url')}")
        click.echo(f"Frame: {'Ja' if fwd.get('frame') else 'Nei'}")


@forwards.command("add")
@click.argument("domain_id", type=int)
@click.option("--host", "-h", required=True, help="Host/subdomene (@ for rot)")
@click.option("--url", "-u", required=True, help="Mål-URL (inkl. https://)")
@click.option("--frame", is_flag=True, help="Bruk iframe (ikke anbefalt)")
def forwards_add(domain_id: int, host: str, url: str, frame: bool):
    """Legg til en videresending"""
    client = get_client()
    
    forward = {
        "host": host,
        "url": url,
        "frame": frame
    }
    
    client.create_forward(domain_id, forward)
    click.echo(f"✓ Videresending opprettet: {host} → {url}")


@forwards.command("update")
@click.argument("domain_id", type=int)
@click.argument("host")
@click.option("--url", "-u", help="Ny mål-URL")
@click.option("--frame/--no-frame", default=None, help="Aktiver/deaktiver iframe")
def forwards_update(domain_id: int, host: str, url: Optional[str], frame: Optional[bool]):
    """Oppdater en videresending"""
    client = get_client()
    
    # Hent eksisterende
    existing = client.get_forward(domain_id, host)
    
    if url is not None:
        existing["url"] = url
    if frame is not None:
        existing["frame"] = frame
    
    client.update_forward(domain_id, host, existing)
    click.echo(f"✓ Videresending '{host}' oppdatert")


@forwards.command("delete")
@click.argument("domain_id", type=int)
@click.argument("host")
@click.option("--yes", "-y", is_flag=True, help="Bekreft sletting uten spørsmål")
def forwards_delete(domain_id: int, host: str, yes: bool):
    """Slett en videresending"""
    client = get_client()
    
    if not yes:
        fwd = client.get_forward(domain_id, host)
        click.echo(f"\nDu er i ferd med å slette:")
        click.echo(f"  Host: {fwd.get('host')}")
        click.echo(f"  URL:  {fwd.get('url')}")
        
        if not click.confirm("\nEr du sikker?"):
            click.echo("Avbrutt.")
            return
    
    client.delete_forward(domain_id, host)
    click.echo(f"✓ Videresending '{host}' slettet")


# === INVOICES ===
@cli.group()
def invoices():
    """Administrer fakturaer"""
    pass


@invoices.command("list")
@click.option("--status", "-s", type=click.Choice(["unpaid", "paid", "settled"]),
              help="Filtrer på status")
@click.option("--json", "as_json", is_flag=True, help="Output som JSON")
def invoices_list(status: Optional[str], as_json: bool):
    """List fakturaer (siste 3 år)"""
    client = get_client()
    invs = client.get_invoices(status)
    
    if as_json:
        click.echo(format_json(invs))
    else:
        if not invs:
            click.echo("Ingen fakturaer funnet.")
            return
        headers = ["ID", "Type", "Beløp", "Valuta", "Status", "Utstedt", "Forfaller"]
        rows = []
        for inv in invs:
            rows.append([
                inv.get("id"),
                inv.get("type"),
                inv.get("amount"),
                inv.get("currency"),
                inv.get("status"),
                inv.get("issued_date"),
                inv.get("due_date", "")
            ])
        click.echo(tabulate(rows, headers=headers, tablefmt="simple"))


@invoices.command("show")
@click.argument("invoice_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output som JSON")
def invoices_show(invoice_id: int, as_json: bool):
    """Vis en faktura"""
    client = get_client()
    inv = client.get_invoice(invoice_id)
    
    if as_json:
        click.echo(format_json(inv))
    else:
        click.echo(f"\nFaktura #{inv.get('id')}")
        click.echo(f"{'='*40}")
        click.echo(f"Type:       {inv.get('type')}")
        click.echo(f"Beløp:      {inv.get('amount')} {inv.get('currency')}")
        click.echo(f"Status:     {inv.get('status')}")
        click.echo(f"Utstedt:    {inv.get('issued_date')}")
        if inv.get('due_date'):
            click.echo(f"Forfaller:  {inv.get('due_date')}")
        if inv.get('paid_date'):
            click.echo(f"Betalt:     {inv.get('paid_date')}")
        if inv.get('url'):
            click.echo(f"\nURL: {inv.get('url')}")


# === DDNS ===
@cli.command()
@click.argument("hostnames")
@click.option("--ip", "ips", help="IP-adresse(r), komma-separert (utelat for å bruke din egen)")
def ddns(hostnames: str, ips: Optional[str]):
    """Oppdater dynamisk DNS for ett eller flere hostnames

    Støtter flere hostnames og IP-er (komma-separert).

    \b
    Eksempler:
      domeneshop ddns www.example.com
      domeneshop ddns www.example.com --ip 1.2.3.4
      domeneshop ddns "example.com,www.example.com"
      domeneshop ddns www.example.com --ip "1.2.3.4,2001:db8::1"
    """
    client = get_client()
    client.update_ddns(hostnames, ips)

    hostname_list = hostnames.split(",")
    if ips:
        ip_list = ips.split(",")
        for h in hostname_list:
            click.echo(f"✓ DDNS oppdatert: {h.strip()}")
        click.echo(f"  IP(er): {', '.join(ip_list)}")
    else:
        for h in hostname_list:
            click.echo(f"✓ DDNS oppdatert: {h.strip()} → (din IP)")


# === KONFIGURASJON ===
@cli.command()
@click.option("--delete", is_flag=True, help="Slett lagrede credentials")
@click.option("--migrate-to-keychain", is_flag=True, help="Migrer credentials fra fil til system keychain")
@click.option("--status", is_flag=True, help="Vis detaljert status for credential-lagring")
def configure(delete: bool, migrate_to_keychain: bool, status: bool):
    """Sett opp eller administrer autentisering
    
    \b
    Eksempler:
      domeneshop configure                    # Interaktiv oppsett
      domeneshop configure --status           # Vis lagringsinfo
      domeneshop configure --migrate-to-keychain  # Migrer til keychain
      domeneshop configure --delete           # Slett credentials
    """
    # Vis detaljert status
    if status:
        info = get_credentials_info()
        click.echo("\nCredential-lagring status:")
        click.echo(f"{'='*50}")
        click.echo(f"  Aktiv kilde:    {info['storage_type']}")
        click.echo(f"  Keyring:        {'Tilgjengelig' if info['keyring_available'] else 'Ikke tilgjengelig'}")
        if info['keyring_backend']:
            click.echo(f"  Keyring-backend: {info['keyring_backend']}")
        click.echo(f"  Fil eksisterer: {'Ja' if info['file_exists'] else 'Nei'}")
        click.echo(f"  Fil-sti:        {info['file_path']}")
        click.echo(f"  Miljøvariabler: {'Konfigurert' if info['env_configured'] else 'Ikke satt'}")
        return

    # Migrer til keychain
    if migrate_to_keychain:
        if not KEYRING_AVAILABLE:
            click.echo("Keyring er ikke tilgjengelig. Installer med: pip install keyring", err=True)
            return
        
        success, message = migrate_file_to_keychain()
        if success:
            log_credentials_migrated("file", "keychain")
            click.echo(f"✓ {message}")
        else:
            click.echo(f"✗ {message}", err=True)
        return

    # Slett credentials
    if delete:
        if delete_credentials():
            log_credentials_deleted()
            click.echo("✓ Alle credentials slettet (keychain og fil)")
        else:
            click.echo("Ingen lagrede credentials funnet.")
        return

    # Vis nåværende status
    info = get_credentials_info()
    click.echo("\nNåværende konfigurasjon:")
    click.echo(f"  Lagringstype: {info['storage_type']}")
    
    if info['env_configured']:
        click.echo("  Miljøvariabel DOMENESHOP_TOKEN er satt")
    if info['keyring_available'] and info['storage_type'] == 'keychain':
        click.echo("  Credentials lagret i system keychain")
    if info['file_exists']:
        click.echo(f"  Fil: {info['file_path']} finnes")
    if info['storage_type'] == 'none':
        click.echo("  Ingen credentials konfigurert")

    click.echo()

    if click.confirm("Vil du sette opp nye credentials?", default=True):
        token, secret = prompt_for_credentials()

        # Test credentials
        client = DomeneshopClient(token, secret)
        try:
            client.get_domains()
            log_auth_success()
            click.echo("\n✓ Autentisering vellykket!")
            
            # Spør om lagringsmetode hvis keychain er tilgjengelig
            if KEYRING_AVAILABLE:
                use_keychain = click.confirm("Lagre i system keychain (anbefalt)?", default=True)
                success, storage_type = save_credentials(token, secret, prefer_keychain=use_keychain)
            else:
                success, storage_type = save_credentials(token, secret, prefer_keychain=False)
            
            if success:
                log_credentials_saved(storage_type)
                if storage_type == "keychain":
                    click.echo("✓ Lagret sikkert i system keychain")
                else:
                    click.echo(f"✓ Lagret til {CONFIG_FILE}")
            else:
                click.echo("✗ Kunne ikke lagre credentials", err=True)
                
        except click.ClickException:
            log_auth_failure("Invalid credentials during configure")
            raise click.ClickException("Autentisering feilet. Sjekk token og secret.")


# === KONTOER ===
@cli.group()
def accounts():
    """Administrer API-kontoer (multi-konto støtte)"""
    pass


@accounts.command("list")
def accounts_list():
    """List alle lagrede kontoer"""
    account_names = list_accounts()
    
    if not account_names:
        click.echo("Ingen kontoer konfigurert.")
        click.echo("\nBruk 'domeneshop accounts add' for å legge til en konto.")
        return
    
    info = get_credentials_info()
    current = info.get("storage_type", "none")
    
    click.echo(f"\nKontoer ({len(account_names)} stk):")
    click.echo(f"{'='*40}")
    for i, name in enumerate(account_names, 1):
        # Marker hvis dette er eneste/valgte konto
        marker = " ← aktiv" if len(account_names) == 1 else ""
        click.echo(f"  {i}. {name}{marker}")
    
    click.echo(f"\nLagring: {current}")


@accounts.command("add")
@click.argument("name")
@click.option("--token", "-t", help="API-token (spørres interaktivt hvis utelatt)")
@click.option("--secret", "-s", help="API-secret (spørres interaktivt hvis utelatt)")
def accounts_add(name: str, token: Optional[str], secret: Optional[str]):
    """Legg til en ny konto
    
    \b
    Eksempler:
      domeneshop accounts add "Firma AS"
      domeneshop accounts add Privat --token xxx --secret yyy
    """
    # Sjekk at navnet ikke er brukt
    existing = list_accounts()
    if name in existing:
        raise click.ClickException(f"Konto '{name}' finnes allerede")
    
    # Spør om credentials hvis ikke oppgitt
    if not token or not secret:
        click.echo(f"\nLegg til konto: {name}")
        click.echo("Generer token og secret på: https://www.domeneshop.no/admin?view=api\n")
        
        if not token:
            token = click.prompt("API-token", type=str)
        if not secret:
            secret = click.prompt("API-secret", type=str, hide_input=True)
    
    # Test credentials
    client = DomeneshopClient(token, secret)
    try:
        domains = client.get_domains()
        domain_count = len(domains) if domains else 0
        log_auth_success()
        click.echo(f"\n✓ Autentisering vellykket! ({domain_count} domener)")
    except Exception:
        log_auth_failure(f"Invalid credentials for account {name}")
        raise click.ClickException("Autentisering feilet. Sjekk token og secret.")
    
    # Lagre
    success, storage_type = save_account(name, token, secret)
    if success:
        log_account_created(name, storage_type)
        click.echo(f"✓ Konto '{name}' lagt til ({storage_type})")
    else:
        raise click.ClickException(f"Kunne ikke lagre konto: {storage_type}")


@accounts.command("remove")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Bekreft sletting uten spørsmål")
def accounts_remove(name: str, yes: bool):
    """Slett en konto
    
    \b
    Eksempler:
      domeneshop accounts remove "Firma AS"
      domeneshop accounts remove Privat -y
    """
    existing = list_accounts()
    if name not in existing:
        raise click.ClickException(f"Konto '{name}' finnes ikke")
    
    if not yes:
        click.echo(f"\nDu er i ferd med å slette konto '{name}'")
        if not click.confirm("Er du sikker?"):
            click.echo("Avbrutt.")
            return
    
    if delete_account(name):
        log_account_deleted(name)
        click.echo(f"✓ Konto '{name}' slettet")
    else:
        raise click.ClickException("Kunne ikke slette konto")


@accounts.command("rename")
@click.argument("old_name")
@click.argument("new_name")
def accounts_rename(old_name: str, new_name: str):
    """Endre navn på en konto
    
    \b
    Eksempler:
      domeneshop accounts rename "Gammelt Navn" "Nytt Navn"
    """
    success, message = rename_account(old_name, new_name)
    if success:
        log_account_renamed(old_name, new_name)
        click.echo(f"✓ {message}")
    else:
        raise click.ClickException(message)


@accounts.command("test")
@click.argument("name", required=False)
def accounts_test(name: Optional[str]):
    """Test tilkobling for en konto
    
    \b
    Eksempler:
      domeneshop accounts test           # Test alle kontoer
      domeneshop accounts test "Firma"   # Test én konto
    """
    if name:
        account_names = [name]
    else:
        account_names = list_accounts()
    
    if not account_names:
        click.echo("Ingen kontoer å teste.")
        return
    
    click.echo(f"\nTester {len(account_names)} konto(er)...")
    click.echo(f"{'='*50}")
    
    for account in account_names:
        token, secret = load_account(account)
        if not token or not secret:
            click.echo(f"  ✗ {account}: Kunne ikke laste credentials")
            continue
        
        try:
            client = DomeneshopClient(token, secret)
            domains = client.get_domains()
            domain_count = len(domains) if domains else 0
            click.echo(f"  ✓ {account}: OK ({domain_count} domener)")
        except Exception as e:
            click.echo(f"  ✗ {account}: Feil - {e}")


if __name__ == "__main__":
    cli()
