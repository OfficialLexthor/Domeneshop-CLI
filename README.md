<div align="center">

# Domeneshop CLI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()

Et kraftig kommandolinjeverktøy for [Domeneshop API](https://api.domeneshop.no/docs/).

[Funksjoner](#funksjoner) • [Hurtigstart](#hurtigstart) • [Installasjon](#installasjon) • [Dokumentasjon](#bruk) • [Bidra](#bidra)

</div>

---

## Funksjoner

| Funksjon | Beskrivelse |
|----------|-------------|
| 📋 **Domener** | List og vis domenedetaljer |
| 🌐 **DNS** | Administrer DNS-poster (A, AAAA, CNAME, MX, TXT, SRV) |
| 🔄 **Forwards** | Administrer HTTP-videresendinger |
| 📄 **Fakturaer** | List og vis fakturaer |
| ⚡ **DDNS** | Oppdater dynamisk DNS |

## Hurtigstart

<table>
<tr>
<td width="33%">

### macOS
```bash
./domeneshop.command
```

</td>
<td width="33%">

### Linux
```bash
./domeneshop.sh
```

</td>
<td width="33%">

### Windows
```batch
domeneshop.bat
```

</td>
</tr>
</table>

> **Note**
> Første gang opprettes virtuelt miljø og avhengigheter installeres automatisk.

### Interaktivt menysystem

Når du starter programmet får du en brukervennlig meny:

```
 ____                                       _                    ____ _     ___
|  _ \  ___  _ __ ___   ___ _ __   ___  ___| |__   ___  _ __    / ___| |   |_ _|
| | | |/ _ \| '_ ` _ \ / _ \ '_ \ / _ \/ __| '_ \ / _ \| '_ \  | |   | |    | |
| |_| | (_) | | | | | |  __/ | | |  __/\__ \ | | | (_) | |_) | | |___| |___ | |
|____/ \___/|_| |_| |_|\___|_| |_|\___||___/_| |_|\___/| .__/   \____|_____|___|
                                                       |_|

HOVEDMENY

  1) 📋 Domener
  2) 🌐 DNS
  3) 🔄 HTTP-videresendinger
  4) 📄 Fakturaer
  5) ⚡ Dynamisk DNS (DDNS)

  8) ⚙️  Innstillinger
  9) 📖 Avansert modus
  0) 🚪 Avslutt
```

<details>
<summary><strong>Vis alle menyvalg</strong></summary>

| Meny | Funksjoner |
|------|------------|
| **Domener** | Liste og vise domenedetaljer |
| **DNS** | Liste, legge til, oppdatere og slette DNS-poster (med TTL-støtte) |
| **HTTP-videresendinger** | Administrere videresendinger |
| **Fakturaer** | Se alle eller kun ubetalte fakturaer |
| **DDNS** | Oppdatere dynamisk DNS |
| **Innstillinger** | Konfigurere API-credentials |
| **Avansert modus** | Skrive kommandoer direkte |

</details>

## Installasjon

### Via pip (anbefalt)

```bash
git clone https://github.com/OfficialLexthor/Domeneshop-CLI.git
cd Domeneshop-CLI
pip install -e .
```

### Manuelt

```bash
git clone https://github.com/OfficialLexthor/Domeneshop-CLI.git
cd Domeneshop-CLI
pip install -r requirements.txt
```

## Oppsett

### 1. Hent API-credentials

1. Logg inn på [Domeneshop](https://www.domeneshop.no)
2. Gå til [API-administrasjon](https://www.domeneshop.no/admin?view=api)
3. Generer et nytt API-token

### 2. Konfigurer CLI

<details open>
<summary><strong>Alternativ 1: Interaktiv innlogging (anbefalt)</strong></summary>

```bash
domeneshop configure
# Følg instruksjonene for å lagre credentials
```

Credentials lagres sikkert i `~/.domeneshop-credentials`.

</details>

<details>
<summary><strong>Alternativ 2: Miljøvariabler</strong></summary>

```bash
export DOMENESHOP_TOKEN='din-token'
export DOMENESHOP_SECRET='din-hemmelighet'
```

Legg i `~/.bashrc` eller `~/.zshrc` for permanent konfigurasjon.

</details>

## Bruk

### Domener

```bash
domeneshop domains list              # List alle domener
domeneshop domains list --filter .no # Filtrer domener
domeneshop domains show 12345        # Vis domenedetaljer
domeneshop domains list --json       # JSON-output
```

### DNS

```bash
# List og vis
domeneshop dns list 12345                    # List alle poster
domeneshop dns list 12345 --type A           # Filtrer på type
domeneshop dns show 12345 67890              # Vis spesifikk post

# Opprett poster
domeneshop dns add 12345 --type A --host www --data 192.168.1.1
domeneshop dns add 12345 --type CNAME --host blog --data www.example.com
domeneshop dns add 12345 --type MX --host @ --data mx.example.com --priority 10
domeneshop dns add 12345 --type TXT --host @ --data "v=spf1 include:_spf.domeneshop.no ~all"

# Oppdater og slett
domeneshop dns update 12345 67890 --data 192.168.1.2
domeneshop dns delete 12345 67890 --yes
```

### HTTP-videresendinger

```bash
domeneshop forwards list 12345                              # List alle
domeneshop forwards add 12345 --host www --url https://example.com
domeneshop forwards update 12345 www --url https://ny-url.com
domeneshop forwards delete 12345 www
```

### Fakturaer

```bash
domeneshop invoices list                 # Alle fakturaer
domeneshop invoices list --status unpaid # Kun ubetalte
domeneshop invoices show 12345           # Vis detaljer
```

### Dynamisk DNS (DDNS)

```bash
domeneshop ddns www.example.com                    # Bruk din IP
domeneshop ddns www.example.com --ip 192.168.1.1   # Spesifikk IP
domeneshop ddns "example.com,www.example.com"      # Flere hostnames
```

## Avanserte eksempler

<details>
<summary><strong>Finn domain-ID fra domenenavn</strong></summary>

```bash
domeneshop domains list --json | jq '.[] | select(.domain=="example.no") | .id'
```

</details>

<details>
<summary><strong>Backup av DNS-poster</strong></summary>

```bash
domeneshop dns list 12345 --json > dns-backup.json
```

</details>

<details>
<summary><strong>Batch-sletting av TXT-poster</strong></summary>

```bash
domeneshop dns list 12345 --type TXT --json | \
    jq '.[].id' | \
    xargs -I {} domeneshop dns delete 12345 {} --yes
```

</details>

## Feilsøking

| Problem | Løsning |
|---------|---------|
| Autentisering feilet | Kjør `domeneshop configure` |
| API-feil | Bruk `--json` for detaljert feilmelding |
| Mangler credentials | Sjekk `~/.domeneshop-credentials` eller miljøvariabler |

## Ansvarsfraskrivelse

> **Warning**
> Dette er et **uoffisielt** prosjekt og er ikke tilknyttet Domeneshop AS.
> Prosjektet bruker [Domeneshop sitt offentlige API](https://api.domeneshop.no/docs/).

## Bidra

Bidrag er velkomne! Se [CONTRIBUTING](CONTRIBUTING.md) for retningslinjer.

1. Fork prosjektet
2. Opprett en feature branch (`git checkout -b feature/ny-funksjon`)
3. Commit endringene (`git commit -m 'Legg til ny funksjon'`)
4. Push til branchen (`git push origin feature/ny-funksjon`)
5. Åpne en Pull Request

## Lisens

Distribuert under MIT-lisensen. Se [`LICENSE`](LICENSE) for mer informasjon.

---

<div align="center">

**[Domeneshop API-dokumentasjon](https://api.domeneshop.no/docs/)** • **[Domeneshop](https://www.domeneshop.no)**

Utviklet av [Martin Clausen](https://github.com/OfficialLexthor)

</div>
