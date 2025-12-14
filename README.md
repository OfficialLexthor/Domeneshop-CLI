# Domeneshop CLI

Et kommandolinjeverktøy for [Domeneshop API](https://api.domeneshop.no/docs/).

## Funksjoner

- 📋 **Domener** - List og vis domenedetaljer
- 🌐 **DNS** - Administrer DNS-poster (A, AAAA, CNAME, MX, TXT, SRV)
- 🔄 **Forwards** - Administrer HTTP-videresendinger
- 📄 **Fakturaer** - List og vis fakturaer
- ⚡ **DDNS** - Oppdater dynamisk DNS

## Hurtigstart

**Mac:** Dobbeltklikk på `domeneshop.command`

**Windows:** Dobbeltklikk på `domeneshop.bat`

Første gang opprettes virtuelt miljø og avhengigheter installeres automatisk.

### Interaktivt menysystem

Når du starter programmet får du en brukervennlig meny:

```
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

Hver undermeny lar deg enkelt:
- **Domener** - Liste og vise domenedetaljer
- **DNS** - Liste, legge til, oppdatere og slette DNS-poster (med TTL-støtte)
- **HTTP-videresendinger** - Administrere videresendinger
- **Fakturaer** - Se alle eller kun ubetalte fakturaer
- **DDNS** - Oppdatere dynamisk DNS
- **Innstillinger** - Konfigurere API-credentials
- **Avansert modus** - Skrive kommandoer direkte

## Installasjon (manuell)

```bash
# Klon repositoriet
git clone https://github.com/officiallexthor/domeneshop-cli.git
cd domeneshop-cli

# Installer med pip
pip install -e .

# Eller installer avhengigheter manuelt
pip install -r requirements.txt
```

## Oppsett

1. Logg inn på [Domeneshop](https://www.domeneshop.no)
2. Gå til [API-administrasjon](https://www.domeneshop.no/admin?view=api)
3. Generer et nytt API-token

### Alternativ 1: Interaktiv innlogging (anbefalt)

Kjør en vilkårlig kommando, og du blir bedt om å skrive inn credentials:

```bash
domeneshop domains list
# Blir spurt om token og secret, med mulighet for å lagre
```

Eller kjør configure direkte:

```bash
domeneshop configure
```

Credentials lagres i `~/.domeneshop-credentials`.

### Alternativ 2: Miljøvariabler

```bash
export DOMENESHOP_TOKEN='din-token'
export DOMENESHOP_SECRET='din-hemmelighet'
```

Legg disse linjene i din `~/.bashrc` eller `~/.zshrc` for permanent konfigurasjon.

## Bruk

### Domener

```bash
# List alle domener
domeneshop domains list

# Filtrer domener
domeneshop domains list --filter ".no"

# Vis detaljer for et domene
domeneshop domains show 12345

# JSON-output
domeneshop domains list --json
```

### DNS

```bash
# List DNS-poster for et domene
domeneshop dns list 12345

# Filtrer på type
domeneshop dns list 12345 --type A

# Filtrer på host
domeneshop dns list 12345 --host www

# Vis en spesifikk DNS-post
domeneshop dns show 12345 67890

# Legg til A-post
domeneshop dns add 12345 --type A --host www --data 192.168.1.1

# Legg til CNAME
domeneshop dns add 12345 --type CNAME --host blog --data www.example.com

# Legg til MX-post
domeneshop dns add 12345 --type MX --host @ --data mx.example.com --priority 10

# Legg til TXT-post (f.eks. SPF)
domeneshop dns add 12345 --type TXT --host @ --data "v=spf1 include:_spf.domeneshop.no ~all"

# Legg til SRV-post
domeneshop dns add 12345 --type SRV --host _sip._tcp --data sip.example.com \
    --priority 10 --weight 100 --port 5060

# Oppdater en DNS-post
domeneshop dns update 12345 67890 --data 192.168.1.2

# Slett en DNS-post
domeneshop dns delete 12345 67890

# Slett uten bekreftelse
domeneshop dns delete 12345 67890 --yes
```

### HTTP-videresendinger

```bash
# List videresendinger
domeneshop forwards list 12345

# Vis en videresending
domeneshop forwards show 12345 www

# Legg til videresending
domeneshop forwards add 12345 --host www --url https://www.example.com

# Oppdater videresending
domeneshop forwards update 12345 www --url https://ny-url.com

# Slett videresending
domeneshop forwards delete 12345 www
```

### Fakturaer

```bash
# List alle fakturaer
domeneshop invoices list

# Filtrer på status
domeneshop invoices list --status unpaid

# Vis en faktura
domeneshop invoices show 12345
```

### Dynamisk DNS (DDNS)

```bash
# Oppdater DDNS med din egen IP
domeneshop ddns www.example.com

# Oppdater DDNS med spesifikk IP
domeneshop ddns www.example.com --ip 192.168.1.1

# Oppdater flere hostnames samtidig
domeneshop ddns "example.com,www.example.com"

# Oppdater med både IPv4 og IPv6
domeneshop ddns www.example.com --ip "1.2.3.4,2001:db8::1"
```

### Hjelpefunksjoner

```bash
# Vis hjelp
domeneshop --help
domeneshop dns --help

# Vis versjon
domeneshop --version

# Sett opp credentials interaktivt
domeneshop configure

# Slett lagrede credentials
domeneshop configure --delete
```

## JSON-output

Alle `list` og `show` kommandoer støtter `--json` for maskinlesbar output:

```bash
domeneshop domains list --json | jq '.[] | .domain'
```

## Eksempler

### Finn domain-ID fra domenenavn

```bash
# List domener og finn ID
domeneshop domains list --json | jq '.[] | select(.domain=="example.no") | .id'
```

### Backup av DNS-poster

```bash
# Eksporter alle DNS-poster til JSON
domeneshop dns list 12345 --json > dns-backup.json
```

### Batch-oppdatering med jq og xargs

```bash
# Slett alle TXT-poster
domeneshop dns list 12345 --type TXT --json | \
    jq '.[].id' | \
    xargs -I {} domeneshop dns delete 12345 {} --yes
```

## Feilsøking

### Autentisering feilet

Kjør configure for å sette opp credentials på nytt:

```bash
domeneshop configure
```

Eller sjekk at miljøvariablene er satt:

```bash
echo $DOMENESHOP_TOKEN
echo $DOMENESHOP_SECRET
```

### API-feil

Bruk `--json` for å se detaljert feilmelding:

```bash
domeneshop domains list --json
```

## Ansvarsfraskrivelse

Dette er et uoffisielt prosjekt og er ikke tilknyttet Domeneshop AS.
Prosjektet bruker [Domeneshop sitt offentlige API](https://api.domeneshop.no/docs/).

## Lisens

MIT License - se [LICENSE](LICENSE) for detaljer.

## Bidra

Pull requests er velkomne! For større endringer, opprett gjerne en issue først.

## Lenker

- [Domeneshop API-dokumentasjon](https://api.domeneshop.no/docs/)
- [Domeneshop](https://www.domeneshop.no)
