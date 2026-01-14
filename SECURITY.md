# Sikkerhetspolicy

## Støttede versjoner

| Versjon | Støttet |
| ------- | ------- |
| 1.x.x   | :white_check_mark: |

## Rapportere en sårbarhet

Hvis du oppdager en sikkerhetssårbarhet, vennligst **ikke** opprett en offentlig issue.

Send i stedet en e-post til: **marticlausen@gmail.com**

Inkluder følgende informasjon:
- Beskrivelse av sårbarheten
- Steg for å reprodusere problemet
- Potensiell påvirkning
- Eventuelle forslag til løsning

### Hva du kan forvente

- Bekreftelse på mottatt rapport innen 48 timer
- Oppdatering på status innen 7 dager
- Kreditt i release notes (hvis ønskelig)

## Sikkerhetspraksis

Dette prosjektet implementerer flere lag med sikkerhet:

### Credential-lagring (prioritert rekkefølge)

1. **Miljøvariabler** (anbefalt for CI/CD og servermiljøer)
   - `DOMENESHOP_TOKEN` og `DOMENESHOP_SECRET`
   - Aldri eksponert i prosesslister

2. **System Keychain** (anbefalt for desktop)
   - macOS: Keychain Access
   - Windows: Credential Locker
   - Linux: Secret Service (GNOME Keyring/KWallet)
   - Kryptert lagring av operativsystemet

3. **Fil-basert** (fallback)
   - Lokasjon: `~/.domeneshop-credentials`
   - Rettigheter: 600 (kun eier kan lese/skrive)
   - Klartekst JSON (ikke anbefalt for produksjon)

### Migrere fra fil til keychain

```bash
domeneshop configure --migrate-to-keychain
```

### GUI-sikkerhet

Web-grensesnittet implementerer:

- **CSRF-beskyttelse**: Alle modifiserende forespørsler krever gyldig CSRF-token
- **Rate limiting**: Autentiseringsendepunkter begrenses til 5 forsøk per minutt
- **Sikre session-cookies**: HttpOnly, SameSite=Lax
- **Input-validering**: Streng validering av API-nøkler

### Audit logging

Alle sikkerhetshendelser logges til `~/.domeneshop-audit.log`:

| Hendelse | Beskrivelse |
|----------|-------------|
| `AUTH_SUCCESS` | Vellykket autentisering |
| `AUTH_FAILURE` | Mislykket autentisering |
| `CREDENTIALS_SAVED` | Credentials lagret |
| `CREDENTIALS_DELETED` | Credentials slettet |
| `DNS_CREATED/UPDATED/DELETED` | DNS-endringer |
| `RATE_LIMIT_HIT` | Rate limit nådd |
| `CSRF_FAILURE` | Ugyldig CSRF-token |

### Kommunikasjon

- All API-kommunikasjon skjer over HTTPS
- API-base: `https://api.domeneshop.no/v0`
- Ingen data sendes til tredjeparter

## Kjente begrensninger

- Fil-basert lagring bruker klartekst JSON
- Audit-loggen lagres lokalt uten kryptering
- GUI bør kun kjøres på localhost (ikke eksponeres til nettverk)

## Anbefalinger

1. **Produksjon**: Bruk miljøvariabler
2. **Desktop**: Migrer til system keychain
3. **GUI**: Kjør kun på localhost, ikke eksponer til nettverk
4. **Overvåking**: Sjekk audit-loggen regelmessig
