<div align="center">

<img src="https://api.domeneshop.no/static/domeneshop-logo.svg" alt="Domeneshop" width="180" />

# Domeneshop CLI & Web GUI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()

**Kraftig CLI og Web GUI for administrasjon av domener, DNS og videresendinger via [Domeneshop API](https://api.domeneshop.no/docs/)**

[Funksjoner](#-funksjoner) · [Hurtigstart](#-hurtigstart) · [CLI-bruk](#-cli-bruk) · [Web GUI](#-web-gui) · [Sikkerhet](#-sikkerhet)

</div>

---

## ✨ Funksjoner

<table>
<tr>
<td width="50%">

### CLI (Kommandolinje)

- **Domener** — List og vis detaljer
- **DNS** — Full CRUD for alle posttyper
- **Forwards** — HTTP-videresendinger
- **Fakturaer** — Oversikt og status
- **DDNS** — Dynamisk DNS-oppdatering
- **Multi-konto** — Bytt mellom kontoer

</td>
<td width="50%">

### Web GUI

- **Visuell administrasjon** — Domener, DNS, forwards
- **Domenedetaljer** — Fane-basert navigasjon
- **Inline-redigering** — Rediger direkte i tabeller
- **Responsivt design** — Mobil og desktop
- **Multi-konto** — Bytt konto i innstillinger

</td>
</tr>
</table>

---

## 🚀 Hurtigstart

### Krav

- Python 3.9+
- API-token fra [Domeneshop](https://www.domeneshop.no/admin?view=api)

### Installasjon

```bash
git clone https://github.com/OfficialLexthor/Domeneshop-CLI.git
cd Domeneshop-CLI
pip install -r requirements.txt
```

### Start

<table>
<tr>
<td><strong>macOS</strong></td>
<td><strong>Linux</strong></td>
<td><strong>Windows</strong></td>
</tr>
<tr>
<td>

```bash
./domeneshop.command
```

</td>
<td>

```bash
./domeneshop.sh
```

</td>
<td>

```batch
domeneshop.bat
```

</td>
</tr>
</table>

Første gang opprettes virtuelt miljø og avhengigheter installeres automatisk.

---

## 📟 CLI-bruk

### Konfigurer credentials

```bash
# Interaktiv konfigurasjon (lagres i system keychain)
domeneshop configure

# Sjekk status
domeneshop configure --status

# Migrer fra fil til keychain
domeneshop configure --migrate-to-keychain
```

<details>
<summary><strong>Alternativ: Miljøvariabler</strong></summary>

```bash
export DOMENESHOP_TOKEN='din-token'
export DOMENESHOP_SECRET='din-hemmelighet'
```

</details>

### Multi-konto

```bash
# List alle kontoer
domeneshop accounts list

# Legg til konto
domeneshop accounts add "Firma" --token xxx --secret yyy

# Bruk spesifikk konto
domeneshop --account "Firma" domains list

# Test tilkobling
domeneshop accounts test "Firma"
```

### Domener

```bash
domeneshop domains list                # List alle domener
domeneshop domains list --filter .no   # Filtrer på TLD
domeneshop domains show 12345          # Vis detaljer
domeneshop domains list --json         # JSON-output
```

### DNS

```bash
# List poster
domeneshop dns list 12345
domeneshop dns list 12345 --type A

# Opprett poster
domeneshop dns add 12345 --type A --host www --data 192.168.1.1
domeneshop dns add 12345 --type MX --host @ --data mx.example.com --priority 10
domeneshop dns add 12345 --type TXT --host @ --data "v=spf1 include:_spf.domeneshop.no ~all"

# Oppdater og slett
domeneshop dns update 12345 67890 --data 192.168.1.2
domeneshop dns delete 12345 67890 --yes
```

### HTTP-videresendinger

```bash
domeneshop forwards list 12345
domeneshop forwards add 12345 --host www --url https://example.com
domeneshop forwards delete 12345 www
```

### Fakturaer

```bash
domeneshop invoices list                 # Alle fakturaer
domeneshop invoices list --status unpaid # Kun ubetalte
```

### Dynamisk DNS

```bash
domeneshop ddns www.example.com                  # Bruk din IP
domeneshop ddns www.example.com --ip 192.168.1.1 # Spesifikk IP
```

---

## 🌐 Web GUI

Start web-grensesnittet:

```bash
python domeneshop_gui.py
```

Åpne **http://localhost:5050** i nettleseren.

### Funksjoner

| Funksjon | Beskrivelse |
|----------|-------------|
| **Domeneoversikt** | Paginert liste med søk og filtrering |
| **Domenedetaljer** | Statistikk, DNS og forwards i faner |
| **Inline-redigering** | Hover for rediger/slett-knapper |
| **Multi-konto** | Bytt mellom kontoer i innstillinger |
| **Responsivt** | Optimalisert for mobil og desktop |

<details>
<summary><strong>Skjermbilder</strong></summary>

Web GUI inkluderer:
- Sidebar-navigasjon med domeneliste
- Domenedetalj-side med faner (Oversikt, DNS, Videresendinger)
- Skeleton loading states
- Breadcrumb-navigasjon

</details>

---

## 🔒 Sikkerhet

| Funksjon | Beskrivelse |
|----------|-------------|
| **Keychain** | Kryptert lagring via OS keychain (macOS/Windows/Linux) |
| **CSRF** | Token-validering for alle modifiserende operasjoner |
| **Rate limiting** | Beskyttelse mot brute-force på auth-endepunkter |
| **Audit logging** | Logger sikkerhetshendelser til `~/.domeneshop-audit.log` |
| **Sikre sessions** | HttpOnly, SameSite, Secure cookies |

Se [SECURITY.md](SECURITY.md) for fullstendig dokumentasjon.

### Credential-prioritet

1. **System keychain** (anbefalt for desktop)
2. **Miljøvariabler** (anbefalt for CI/CD)
3. **Fil-basert** (`~/.domeneshop-credentials` med 600-rettigheter)

---

## 🛠 Feilsøking

| Problem | Løsning |
|---------|---------|
| Autentisering feilet | `domeneshop configure` |
| Mangler credentials | `domeneshop configure --status` |
| Keychain utilgjengelig | `pip install keyring` |
| API-feil | Bruk `--json` for detaljert feilmelding |

---

## 📁 Prosjektstruktur

```
domeneshop-cli/
├── domeneshop_cli.py      # CLI-applikasjon
├── domeneshop_gui.py      # Flask Web GUI
├── credentials.py         # Credential-håndtering
├── audit.py               # Audit logging
├── templates/
│   ├── index.html         # Hoved-UI
│   └── settings.html      # Innstillinger
├── domeneshop.sh          # Linux/macOS launcher
├── domeneshop.command     # macOS launcher
└── domeneshop.bat         # Windows launcher
```

---

## 🤝 Bidra

Bidrag er velkomne! Se [CONTRIBUTING.md](CONTRIBUTING.md) for retningslinjer.

```bash
# Fork og klon
git clone https://github.com/YOUR_USERNAME/Domeneshop-CLI.git

# Opprett feature branch
git checkout -b feature/ny-funksjon

# Commit og push
git commit -m 'Legg til ny funksjon'
git push origin feature/ny-funksjon
```

---

## ⚠️ Ansvarsfraskrivelse

> Dette er et **uoffisielt** prosjekt og er ikke tilknyttet Domeneshop AS.
> Prosjektet bruker [Domeneshop sitt offentlige API](https://api.domeneshop.no/docs/).

---

## 📄 Lisens

Distribuert under MIT-lisensen. Se [LICENSE](LICENSE) for mer informasjon.

---

<div align="center">

**[Domeneshop API-dokumentasjon](https://api.domeneshop.no/docs/)** · **[Domeneshop](https://www.domeneshop.no)**

Utviklet av [Martin Clausen](https://github.com/OfficialLexthor)

</div>
