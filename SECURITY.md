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

Dette prosjektet:
- Lagrer aldri API-credentials i kildekoden
- Bruker sikker filrettigheter (600) for credential-filer
- Kommuniserer kun over HTTPS med Domeneshop API

## Kjente begrensninger

- Credentials lagres i klartekst i `~/.domeneshop-credentials`
- Anbefaler bruk av miljøvariabler i produksjonsmiljøer
