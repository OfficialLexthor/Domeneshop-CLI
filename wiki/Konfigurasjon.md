# Konfigurasjon

## Hent API-credentials

1. Logg inn på [Domeneshop](https://www.domeneshop.no)
2. Gå til [API-administrasjon](https://www.domeneshop.no/admin?view=api)
3. Generer et nytt API-token

## Metode 1: Interaktiv konfigurasjon (anbefalt)

```bash
domeneshop configure
```

Du blir bedt om å skrive inn:
- API Token
- API Secret

Credentials lagres sikkert i `~/.domeneshop-credentials`.

## Metode 2: Miljøvariabler

```bash
export DOMENESHOP_TOKEN='din-token'
export DOMENESHOP_SECRET='din-hemmelighet'
```

Legg disse i `~/.bashrc` eller `~/.zshrc` for permanent konfigurasjon.

## Slett credentials

```bash
domeneshop configure --delete
```

## Prioritering

CLI-en sjekker credentials i denne rekkefølgen:
1. Miljøvariabler
2. Konfigurasjonsfil (`~/.domeneshop-credentials`)
3. Interaktiv input
