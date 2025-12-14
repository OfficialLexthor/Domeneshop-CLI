# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Domeneshop CLI is a Python command-line tool for the [Domeneshop API](https://api.domeneshop.no/docs/). It manages domains, DNS records, HTTP forwards, invoices, and dynamic DNS for Norwegian domain registrar Domeneshop.

## Build & Run Commands

```bash
# Install in development mode
pip install -e .

# Install dependencies only
pip install -r requirements.txt

# Run CLI directly
python domeneshop_cli.py [command]

# Run installed CLI
domeneshop [command]
```

## Architecture

The entire CLI is a single-file Python application (`domeneshop_cli.py`) built with Click framework:

- **DomeneshopClient class** (lines 26-129): HTTP client wrapper using requests with Basic Auth. All API calls go through `_request()` which handles errors and returns JSON.
- **Credential management** (lines 132-190): Loads credentials from environment variables, config file (`~/.domeneshop-credentials`), or prompts interactively.
- **CLI groups**: `domains`, `dns`, `forwards`, `invoices` - each is a Click group with `list`, `show`, and CRUD commands.
- **DDNS**: Standalone command at root level (`domeneshop ddns`).

## API Details

- Base URL: `https://api.domeneshop.no/v0`
- Auth: HTTP Basic Auth. Credentials loaded in priority order:
  1. Environment variables `DOMENESHOP_TOKEN` and `DOMENESHOP_SECRET`
  2. Config file `~/.domeneshop-credentials`
  3. Interactive prompt (with option to save)
- Full OpenAPI spec in `docs/openapi.json`

## Dependencies

- click (CLI framework)
- requests (HTTP client)
- tabulate (table formatting)

## Code Conventions

- Language: Norwegian comments and user-facing strings
- All commands support `--json` flag for machine-readable output
- Destructive operations prompt for confirmation unless `--yes` flag provided
