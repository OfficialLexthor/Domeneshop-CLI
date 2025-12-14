# Kommandoer

## Domener

| Kommando | Beskrivelse |
|----------|-------------|
| `domeneshop domains list` | List alle domener |
| `domeneshop domains list --filter .no` | Filtrer domener |
| `domeneshop domains show <id>` | Vis domenedetaljer |
| `domeneshop domains list --json` | JSON-output |

## DNS

| Kommando | Beskrivelse |
|----------|-------------|
| `domeneshop dns list <domain-id>` | List DNS-poster |
| `domeneshop dns list <domain-id> --type A` | Filtrer på type |
| `domeneshop dns show <domain-id> <record-id>` | Vis en post |
| `domeneshop dns add <domain-id> --type A --host www --data 1.2.3.4` | Opprett post |
| `domeneshop dns update <domain-id> <record-id> --data 1.2.3.5` | Oppdater post |
| `domeneshop dns delete <domain-id> <record-id>` | Slett post |

### DNS-typer

- `A` - IPv4-adresse
- `AAAA` - IPv6-adresse
- `CNAME` - Alias
- `MX` - E-post (krever `--priority`)
- `TXT` - Tekst
- `SRV` - Tjeneste (krever `--priority`, `--weight`, `--port`)

## Videresendinger

| Kommando | Beskrivelse |
|----------|-------------|
| `domeneshop forwards list <domain-id>` | List videresendinger |
| `domeneshop forwards add <domain-id> --host www --url https://...` | Opprett |
| `domeneshop forwards update <domain-id> <host> --url https://...` | Oppdater |
| `domeneshop forwards delete <domain-id> <host>` | Slett |

## Fakturaer

| Kommando | Beskrivelse |
|----------|-------------|
| `domeneshop invoices list` | Alle fakturaer |
| `domeneshop invoices list --status unpaid` | Kun ubetalte |
| `domeneshop invoices show <id>` | Vis detaljer |

## DDNS

| Kommando | Beskrivelse |
|----------|-------------|
| `domeneshop ddns example.com` | Oppdater med din IP |
| `domeneshop ddns example.com --ip 1.2.3.4` | Spesifikk IP |
| `domeneshop ddns "a.com,b.com"` | Flere hostnames |

## Globale flagg

- `--json` - Output i JSON-format
- `--help` - Vis hjelp
- `--version` - Vis versjon
