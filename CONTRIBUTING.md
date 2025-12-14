# Bidra til Domeneshop CLI

Takk for at du vil bidra til prosjektet!

## Komme i gang

1. **Fork** repositoriet
2. **Klon** din fork:
   ```bash
   git clone https://github.com/DITT-BRUKERNAVN/Domeneshop-CLI.git
   cd Domeneshop-CLI
   ```
3. **Installer** avhengigheter:
   ```bash
   pip install -r requirements.txt
   ```

## Utvikling

### Kjør CLI lokalt

```bash
python domeneshop_cli.py --help
```

### Test endringene dine

Sørg for at CLI-en fortsatt fungerer:

```bash
python domeneshop_cli.py domains list
python domeneshop_cli.py dns list <domain-id>
```

## Sende inn endringer

### 1. Opprett en branch

```bash
git checkout -b feature/min-nye-funksjon
```

Bruk beskrivende navn:
- `feature/ny-funksjon` - Ny funksjonalitet
- `fix/fiks-bug` - Bugfiks
- `docs/oppdater-readme` - Dokumentasjon

### 2. Gjør endringer

- Følg eksisterende kodestil
- Hold endringene fokuserte og små
- Test at alt fungerer

### 3. Commit

```bash
git add .
git commit -m "Kort beskrivelse av endringen"
```

### 4. Push og opprett Pull Request

```bash
git push origin feature/min-nye-funksjon
```

Gå til GitHub og opprett en Pull Request.

## Retningslinjer

- **Norsk** brukes i brukergrensesnittet
- **Engelsk** kan brukes i kodekommentarer
- Hold koden enkel og lesbar
- Test på både macOS og Windows om mulig

## Spørsmål?

Opprett en [issue](https://github.com/OfficialLexthor/Domeneshop-CLI/issues) hvis du har spørsmål.
