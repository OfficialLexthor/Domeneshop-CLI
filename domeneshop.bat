@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

:setup
if not exist "venv" (
    echo [33m▸ Oppretter virtuelt miljo...[0m
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [33m▸ Installerer avhengigheter...[0m
    pip install -q -r requirements.txt
    echo [32m✓ Ferdig![0m
    timeout /t 2 >nul
) else (
    call venv\Scripts\activate.bat
)
goto main_menu

:show_logo
cls
echo.
echo  [36m ____                                       _                    ____ _     ___ [0m
echo  [36m^|  _ \  ___  _ __ ___   ___ _ __   ___  ___^| ^|__   ___  _ __    / ___^| ^|   ^|_ _^|[0m
echo  [36m^| ^| ^| ^|/ _ \^| '_ ` _ \ / _ \ '_ \ / _ \/ __^| '_ \ / _ \^| '_ \  ^| ^|   ^| ^|    ^| ^| [0m
echo  [36m^| ^|_^| ^| (_) ^| ^| ^| ^| ^| ^|  __/ ^| ^| ^|  __/\__ \ ^| ^| ^| (_) ^| ^|_) ^| ^| ^|___^| ^|___ ^| ^| [0m
echo  [36m^|____/ \___/^|_^| ^|_^| ^|_^|\___^|_^| ^|_^|\___^|^|___/_^| ^|_^|\___/^| .__/   \____^|_____^|___^|[0m
echo  [36m                                                       ^|_^|                      [0m
echo.
echo [90m──────────────────────────────────────────────────────────────────────────────[0m
echo   [90mUtviklet av Martin Clausen[0m
echo [90m──────────────────────────────────────────────────────────────────────────────[0m
echo.
goto :eof

:main_menu
call :show_logo
echo [1mHOVEDMENY[0m
echo.
echo   [36m1)[0m 📋 Domener
echo   [36m2)[0m 🌐 DNS
echo   [36m3)[0m 🔄 HTTP-videresendinger
echo   [36m4)[0m 📄 Fakturaer
echo   [36m5)[0m ⚡ Dynamisk DNS (DDNS)
echo.
echo   [36m8)[0m ⚙️  Innstillinger
echo   [36m9)[0m 📖 Avansert modus
echo   [36m0)[0m 🚪 Avslutt
echo.
set /p choice="Valg: "
if "%choice%"=="1" goto menu_domains
if "%choice%"=="2" goto menu_dns
if "%choice%"=="3" goto menu_forwards
if "%choice%"=="4" goto menu_invoices
if "%choice%"=="5" goto menu_ddns
if "%choice%"=="8" goto menu_settings
if "%choice%"=="9" goto advanced_mode
if "%choice%"=="0" goto exit_app
goto main_menu

:menu_domains
call :show_logo
echo [1m📋 DOMENER[0m
echo.
echo   [36m1)[0m List alle domener
echo   [36m2)[0m Vis domenedetaljer
echo.
echo   [36m0)[0m ← Tilbake til hovedmeny
echo.
set /p choice="Valg: "
if "%choice%"=="1" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    pause
)
if "%choice%"=="2" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    set /p domain_id="Domene-ID: "
    if not "!domain_id!"=="" (
        python domeneshop_cli.py domains show !domain_id!
        echo.
        pause
    )
)
if "%choice%"=="0" goto main_menu
goto menu_domains

:menu_dns
call :show_logo
echo [1m🌐 DNS[0m
echo.
echo   [36m1)[0m List DNS-poster
echo   [36m2)[0m Legg til DNS-post
echo   [36m3)[0m Oppdater DNS-post
echo   [36m4)[0m Slett DNS-post
echo.
echo   [36m0)[0m ← Tilbake til hovedmeny
echo.
set /p choice="Valg: "
if "%choice%"=="1" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    set /p domain_id="Domene-ID: "
    if not "!domain_id!"=="" (
        python domeneshop_cli.py dns list !domain_id!
        echo.
        pause
    )
)
if "%choice%"=="2" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    set /p domain_id="Domene-ID: "
    echo.
    echo Velg DNS-type:
    echo   1^) A      2^) AAAA    3^) CNAME
    echo   4^) MX     5^) TXT     6^) SRV
    echo.
    set /p type_choice="Valg: "
    if "!type_choice!"=="1" set dns_type=A
    if "!type_choice!"=="2" set dns_type=AAAA
    if "!type_choice!"=="3" set dns_type=CNAME
    if "!type_choice!"=="4" set dns_type=MX
    if "!type_choice!"=="5" set dns_type=TXT
    if "!type_choice!"=="6" set dns_type=SRV
    echo.
    set /p host="Host (@ for rot): "
    set /p data="Data: "
    set /p ttl="TTL i sekunder [3600]: "
    if "!ttl!"=="" set ttl=3600
    set extra_opts=--ttl !ttl!
    if "!dns_type!"=="MX" (
        set /p priority="Prioritet: "
        set extra_opts=!extra_opts! --priority !priority!
    )
    if "!dns_type!"=="SRV" (
        set /p priority="Prioritet: "
        set /p weight="Vekt: "
        set /p port="Port: "
        set extra_opts=!extra_opts! --priority !priority! --weight !weight! --port !port!
    )
    python domeneshop_cli.py dns add !domain_id! --type !dns_type! --host "!host!" --data "!data!" !extra_opts!
    echo.
    pause
)
if "%choice%"=="3" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    set /p domain_id="Domene-ID: "
    echo.
    python domeneshop_cli.py dns list !domain_id!
    echo.
    set /p record_id="Record-ID (0 for aa avbryte): "
    if not "!record_id!"=="" if not "!record_id!"=="0" (
        echo.
        echo [90mLa felt staa tomt for aa beholde eksisterende verdi[0m
        echo.
        set /p new_data="Ny data: "
        set /p new_ttl="Ny TTL: "
        set update_opts=
        if not "!new_data!"=="" set update_opts=!update_opts! --data "!new_data!"
        if not "!new_ttl!"=="" set update_opts=!update_opts! --ttl !new_ttl!
        if not "!update_opts!"=="" (
            python domeneshop_cli.py dns update !domain_id! !record_id! !update_opts!
            echo.
            pause
        )
    )
)
if "%choice%"=="4" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    set /p domain_id="Domene-ID: "
    echo.
    python domeneshop_cli.py dns list !domain_id!
    echo.
    set /p record_id="Record-ID (0 for aa avbryte): "
    if not "!record_id!"=="" if not "!record_id!"=="0" (
        python domeneshop_cli.py dns delete !domain_id! !record_id!
        echo.
        pause
    )
)
if "%choice%"=="0" goto main_menu
goto menu_dns

:menu_forwards
call :show_logo
echo [1m🔄 HTTP-VIDERESENDINGER[0m
echo.
echo   [36m1)[0m List videresendinger
echo   [36m2)[0m Legg til videresending
echo   [36m3)[0m Oppdater videresending
echo   [36m4)[0m Slett videresending
echo.
echo   [36m0)[0m ← Tilbake til hovedmeny
echo.
set /p choice="Valg: "
if "%choice%"=="1" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    set /p domain_id="Domene-ID: "
    if not "!domain_id!"=="" (
        python domeneshop_cli.py forwards list !domain_id!
        echo.
        pause
    )
)
if "%choice%"=="2" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    set /p domain_id="Domene-ID: "
    set /p host="Host (@ for rot): "
    set /p url="Maal-URL (inkl. https://): "
    python domeneshop_cli.py forwards add !domain_id! --host "!host!" --url "!url!"
    echo.
    pause
)
if "%choice%"=="3" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    set /p domain_id="Domene-ID: "
    echo.
    python domeneshop_cli.py forwards list !domain_id!
    echo.
    set /p host="Host som skal oppdateres (0 for aa avbryte): "
    if not "!host!"=="" if not "!host!"=="0" (
        set /p new_url="Ny maal-URL (inkl. https://): "
        if not "!new_url!"=="" (
            python domeneshop_cli.py forwards update !domain_id! "!host!" --url "!new_url!"
            echo.
            pause
        )
    )
)
if "%choice%"=="4" (
    echo.
    python domeneshop_cli.py domains list
    echo.
    set /p domain_id="Domene-ID: "
    echo.
    python domeneshop_cli.py forwards list !domain_id!
    echo.
    set /p host="Host som skal slettes (0 for aa avbryte): "
    if not "!host!"=="" if not "!host!"=="0" (
        python domeneshop_cli.py forwards delete !domain_id! "!host!"
        echo.
        pause
    )
)
if "%choice%"=="0" goto main_menu
goto menu_forwards

:menu_invoices
call :show_logo
echo [1m📄 FAKTURAER[0m
echo.
echo   [36m1)[0m List alle fakturaer
echo   [36m2)[0m Vis ubetalte fakturaer
echo   [36m3)[0m Vis fakturadetaljer
echo.
echo   [36m0)[0m ← Tilbake til hovedmeny
echo.
set /p choice="Valg: "
if "%choice%"=="1" (
    echo.
    python domeneshop_cli.py invoices list
    echo.
    pause
)
if "%choice%"=="2" (
    echo.
    python domeneshop_cli.py invoices list --status unpaid
    echo.
    pause
)
if "%choice%"=="3" (
    echo.
    echo [1mVelg faktura:[0m
    echo.
    python domeneshop_cli.py invoices list
    echo.
    set /p invoice_id="Faktura-ID (eller 0 for aa avbryte): "
    if not "!invoice_id!"=="" if not "!invoice_id!"=="0" (
        python domeneshop_cli.py invoices show !invoice_id!
        echo.
        pause
    )
)
if "%choice%"=="0" goto main_menu
goto menu_invoices

:menu_ddns
call :show_logo
echo [1m⚡ DYNAMISK DNS[0m
echo.
echo   [36m1)[0m Oppdater DDNS (bruk min IP)
echo   [36m2)[0m Oppdater DDNS (spesifiser IP)
echo.
echo   [36m0)[0m ← Tilbake til hovedmeny
echo.
set /p choice="Valg: "
if "%choice%"=="1" (
    echo.
    set /p hostname="Hostname (f.eks. www.example.com): "
    if not "!hostname!"=="" (
        python domeneshop_cli.py ddns "!hostname!"
        echo.
        pause
    )
)
if "%choice%"=="2" (
    echo.
    set /p hostname="Hostname (f.eks. www.example.com): "
    set /p ip="IP-adresse: "
    if not "!hostname!"=="" if not "!ip!"=="" (
        python domeneshop_cli.py ddns "!hostname!" --ip "!ip!"
        echo.
        pause
    )
)
if "%choice%"=="0" goto main_menu
goto menu_ddns

:menu_settings
call :show_logo
echo [1m⚙️  INNSTILLINGER[0m
echo.
echo   [36m1)[0m Sett opp API-credentials
echo   [36m2)[0m Slett lagrede credentials
echo   [36m3)[0m Vis gjeldende status
echo.
echo   [36m0)[0m ← Tilbake til hovedmeny
echo.
set /p choice="Valg: "
if "%choice%"=="1" (
    echo.
    python domeneshop_cli.py configure
    echo.
    pause
)
if "%choice%"=="2" (
    echo.
    python domeneshop_cli.py configure --delete
    echo.
    pause
)
if "%choice%"=="3" (
    echo.
    if exist "%USERPROFILE%\.domeneshop-credentials" (
        echo [32m✓ Credentials er lagret[0m
    ) else (
        echo [33m⚠ Ingen credentials lagret[0m
    )
    if defined DOMENESHOP_TOKEN (
        echo [32m✓ Miljovariabel DOMENESHOP_TOKEN er satt[0m
    )
    echo.
    pause
)
if "%choice%"=="0" goto main_menu
goto menu_settings

:advanced_mode
call :show_logo
echo [1mAvansert modus[0m - Skriv kommandoer direkte
echo [90mSkriv 'exit' for aa gaa tilbake til menyen[0m
echo.
:advanced_loop
set /p cmd="[32mdomeneshop[0m[1m>[0m "
if "%cmd%"=="exit" goto main_menu
if "%cmd%"=="quit" goto main_menu
if "%cmd%"=="help" (
    python domeneshop_cli.py --help
    echo.
    goto advanced_loop
)
if not "%cmd%"=="" (
    python domeneshop_cli.py %cmd%
    echo.
)
goto advanced_loop

:exit_app
call :show_logo
echo [36mHa det! 👋[0m
echo.
timeout /t 2 >nul
exit
