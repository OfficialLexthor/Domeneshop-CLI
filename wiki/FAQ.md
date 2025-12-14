# FAQ - Ofte stilte spørsmål

## Generelt

### Hva er Domeneshop CLI?
Et uoffisielt kommandolinjeverktøy for å administrere Domeneshop-tjenester via deres API.

### Er dette et offisielt Domeneshop-produkt?
Nei, dette er et uavhengig open source-prosjekt som bruker Domeneshop sitt offentlige API.

## Installasjon

### Hvilken Python-versjon trenger jeg?
Python 3.8 eller nyere.

### Fungerer det på både Mac og Windows?
Ja! Det følger med klikkbare startfiler for begge plattformer.

## Autentisering

### Hvor lagres credentials?
I `~/.domeneshop-credentials` (din hjemmemappe).

### Er det trygt?
Filen har begrenset tilgang (chmod 600 på Unix). For ekstra sikkerhet, bruk miljøvariabler.

### Hvordan sletter jeg lagrede credentials?
```bash
domeneshop configure --delete
```

## Feilsøking

### "Autentisering feilet"
Kjør `domeneshop configure` for å sette opp credentials på nytt.

### "Kunne ikke koble til API"
Sjekk internettforbindelsen din og at api.domeneshop.no er tilgjengelig.

### Hvordan ser jeg detaljerte feilmeldinger?
Bruk `--json` flagget for å se rå API-respons.

## Bidra

### Hvordan kan jeg bidra?
Se [CONTRIBUTING.md](https://github.com/OfficialLexthor/Domeneshop-CLI/blob/main/CONTRIBUTING.md) for retningslinjer.

### Fant en bug?
Opprett en [issue](https://github.com/OfficialLexthor/Domeneshop-CLI/issues/new?template=bug_report.md).
