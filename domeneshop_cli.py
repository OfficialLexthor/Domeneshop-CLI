#!/usr/bin/env python3
"""
Domeneshop CLI - Et kommandolinjeverktøy for Domeneshop API

Bruk: domeneshop [KOMMANDO] [ALTERNATIVER]

Krever miljøvariabler:
  DOMENESHOP_TOKEN  - API-token fra domeneshop.no/admin?view=api
  DOMENESHOP_SECRET - API-hemmelighet
"""

import os
import sys
import json
import click
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from tabulate import tabulate

# API konfigurasjon
API_BASE_URL = "https://api.domeneshop.no/v0"
CONFIG_FILE = Path.home() / ".domeneshop-credentials"


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


def load_credentials_from_file() -> Tuple[Optional[str], Optional[str]]:
    """Les credentials fra konfigurasjonsfil"""
    if not CONFIG_FILE.exists():
        return None, None
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
            return data.get("token"), data.get("secret")
    except (json.JSONDecodeError, IOError):
        return None, None


def save_credentials_to_file(token: str, secret: str) -> None:
    """Lagre credentials til konfigurasjonsfil"""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"token": token, "secret": secret}, f)
    # Sett filrettigheter til kun eier (fungerer på Unix/Mac, ignoreres på Windows)
    if sys.platform != "win32":
        CONFIG_FILE.chmod(0o600)


def prompt_for_credentials() -> Tuple[str, str]:
    """Spør bruker om credentials interaktivt"""
    click.echo("\nMangler API-credentials.")
    click.echo("Generer token og secret på: https://www.domeneshop.no/admin?view=api\n")

    token = click.prompt("API-token", type=str)
    secret = click.prompt("API-secret", type=str, hide_input=True)

    return token, secret


def get_client() -> DomeneshopClient:
    """Hent API-klient med autentisering"""
    # 1. Prøv miljøvariabler først
    token = os.environ.get("DOMENESHOP_TOKEN")
    secret = os.environ.get("DOMENESHOP_SECRET")

    # 2. Prøv konfigurasjonsfil
    if not token or not secret:
        token, secret = load_credentials_from_file()

    # 3. Spør interaktivt
    if not token or not secret:
        token, secret = prompt_for_credentials()

        # Verifiser at credentials fungerer
        client = DomeneshopClient(token, secret)
        try:
            client.get_domains()  # Test API-kall
            click.echo("\nAutentisering vellykket!")

            if click.confirm("Vil du lagre credentials for fremtidig bruk?", default=True):
                save_credentials_to_file(token, secret)
                click.echo(f"Lagret til {CONFIG_FILE}\n")
        except click.ClickException:
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
@click.version_option(version="1.0.0", prog_name="domeneshop")
def cli():
    """Domeneshop CLI - Administrer domener, DNS og mer via kommandolinjen.
    
    Krever miljøvariabler DOMENESHOP_TOKEN og DOMENESHOP_SECRET.
    """
    pass


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
    click.echo(f"✓ DNS-post opprettet med ID: {result.get('id')}")


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
    
    client.delete_dns_record(domain_id, record_id)
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


# === HJELPEFUNKSJONER ===
@cli.command()
@click.option("--delete", is_flag=True, help="Slett lagrede credentials")
def configure(delete: bool):
    """Sett opp eller administrer autentisering"""
    if delete:
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
            click.echo("Credentials slettet.")
        else:
            click.echo("Ingen lagrede credentials funnet.")
        return

    # Vis nåværende status
    token_env = os.environ.get("DOMENESHOP_TOKEN")
    file_token, _ = load_credentials_from_file()

    click.echo("\nNåværende konfigurasjon:")
    if token_env:
        click.echo(f"  Miljøvariabel: DOMENESHOP_TOKEN er satt")
    if file_token:
        click.echo(f"  Fil: {CONFIG_FILE} finnes")
    if not token_env and not file_token:
        click.echo("  Ingen credentials konfigurert")

    click.echo()

    if click.confirm("Vil du sette opp nye credentials?", default=True):
        token, secret = prompt_for_credentials()

        # Test credentials
        client = DomeneshopClient(token, secret)
        try:
            client.get_domains()
            click.echo("\nAutentisering vellykket!")
            save_credentials_to_file(token, secret)
            click.echo(f"Lagret til {CONFIG_FILE}")
        except click.ClickException:
            raise click.ClickException("Autentisering feilet. Sjekk token og secret.")


if __name__ == "__main__":
    cli()
