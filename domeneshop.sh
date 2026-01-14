#!/bin/bash
# Domeneshop CLI - Kjør med ./domeneshop.sh (Linux)

cd "$(dirname "$0")"

# Farger
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m'
BOLD='\033[1m'

show_logo() {
    clear
    echo -e "${CYAN}"
    echo ' ____                                       _                    ____ _     ___ '
    echo '|  _ \  ___  _ __ ___   ___ _ __   ___  ___| |__   ___  _ __    / ___| |   |_ _|'
    echo '| | | |/ _ \| '\''_ ` _ \ / _ \ '\''_ \ / _ \/ __| '\''_ \ / _ \| '\''_ \  | |   | |    | | '
    echo '| |_| | (_) | | | | | |  __/ | | |  __/\__ \ | | | (_) | |_) | | |___| |___ | | '
    echo '|____/ \___/|_| |_| |_|\___|_| |_|\___||___/_| |_|\___/| .__/   \____|_____|___|'
    echo '                                                       |_|                      '
    echo -e "${NC}"
    echo -e "${GRAY}──────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${GRAY}  Utviklet av Martin Clausen${NC}"
    echo -e "${GRAY}──────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
}

# Opprett venv hvis det ikke finnes
setup_env() {
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}▸ Oppretter virtuelt miljø...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        echo -e "${YELLOW}▸ Installerer avhengigheter...${NC}"
        pip install -q -r requirements.txt
        echo -e "${GREEN}✓ Ferdig!${NC}"
        sleep 1
    else
        source venv/bin/activate
    fi
}

run_cmd() {
    echo ""
    python domeneshop_cli.py "$@"
    echo ""
    echo -e "${GRAY}Trykk Enter for å fortsette...${NC}"
    read
}

select_domain() {
    echo -e "${BOLD}Velg domene:${NC}"
    echo ""
    domains=$(python domeneshop_cli.py domains list --json 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo -e "${RED}Kunne ikke hente domener. Kjør 'Innstillinger' først.${NC}"
        echo ""
        echo -e "${GRAY}Trykk Enter for å fortsette...${NC}"
        read
        return 1
    fi

    # Parse domains and show menu
    i=1
    domain_ids=()
    while IFS= read -r line; do
        id=$(echo "$line" | cut -d'|' -f1)
        name=$(echo "$line" | cut -d'|' -f2)
        domain_ids+=("$id")
        echo -e "  ${CYAN}$i)${NC} $name ${GRAY}(ID: $id)${NC}"
        ((i++))
    done < <(echo "$domains" | python3 -c "import sys, json; data = json.load(sys.stdin); [print(f\"{d['id']}|{d['domain']}\") for d in data]")

    echo ""
    echo -e "  ${CYAN}0)${NC} Tilbake"
    echo ""
    read -p "Valg: " choice

    if [ "$choice" = "0" ] || [ -z "$choice" ]; then
        return 1
    fi

    idx=$((choice - 1))
    if [ $idx -ge 0 ] && [ $idx -lt ${#domain_ids[@]} ]; then
        SELECTED_DOMAIN=${domain_ids[$idx]}
        return 0
    fi
    return 1
}

menu_domains() {
    while true; do
        show_logo
        echo -e "${BOLD}📋 DOMENER${NC}"
        echo ""
        echo -e "  ${CYAN}1)${NC} List alle domener"
        echo -e "  ${CYAN}2)${NC} Vis domenedetaljer"
        echo ""
        echo -e "  ${CYAN}0)${NC} ← Tilbake til hovedmeny"
        echo ""
        read -p "Valg: " choice

        case $choice in
            1) run_cmd domains list ;;
            2)
                show_logo
                if select_domain; then
                    run_cmd domains show $SELECTED_DOMAIN
                fi
                ;;
            0|"") break ;;
        esac
    done
}

menu_dns() {
    while true; do
        show_logo
        echo -e "${BOLD}🌐 DNS${NC}"
        echo ""
        echo -e "  ${CYAN}1)${NC} List DNS-poster"
        echo -e "  ${CYAN}2)${NC} Legg til DNS-post"
        echo -e "  ${CYAN}3)${NC} Oppdater DNS-post"
        echo -e "  ${CYAN}4)${NC} Slett DNS-post"
        echo ""
        echo -e "  ${CYAN}0)${NC} ← Tilbake til hovedmeny"
        echo ""
        read -p "Valg: " choice

        case $choice in
            1)
                show_logo
                if select_domain; then
                    run_cmd dns list $SELECTED_DOMAIN
                fi
                ;;
            2)
                show_logo
                if select_domain; then
                    echo ""
                    echo -e "${BOLD}Velg DNS-type:${NC}"
                    echo ""
                    echo -e "  ${CYAN}1)${NC} A     (IPv4-adresse)"
                    echo -e "  ${CYAN}2)${NC} AAAA  (IPv6-adresse)"
                    echo -e "  ${CYAN}3)${NC} CNAME (Alias)"
                    echo -e "  ${CYAN}4)${NC} MX    (E-post)"
                    echo -e "  ${CYAN}5)${NC} TXT   (Tekst)"
                    echo -e "  ${CYAN}6)${NC} SRV   (Tjeneste)"
                    echo ""
                    read -p "Valg: " type_choice

                    case $type_choice in
                        1) dns_type="A" ;;
                        2) dns_type="AAAA" ;;
                        3) dns_type="CNAME" ;;
                        4) dns_type="MX" ;;
                        5) dns_type="TXT" ;;
                        6) dns_type="SRV" ;;
                        *) continue ;;
                    esac

                    echo ""
                    read -p "Host (@ for rot): " host
                    read -p "Data (IP/hostname/tekst): " data
                    read -p "TTL i sekunder [3600]: " ttl
                    ttl=${ttl:-3600}

                    extra_opts="--ttl $ttl"
                    if [ "$dns_type" = "MX" ]; then
                        read -p "Prioritet: " priority
                        extra_opts="$extra_opts --priority $priority"
                    elif [ "$dns_type" = "SRV" ]; then
                        read -p "Prioritet: " priority
                        read -p "Vekt: " weight
                        read -p "Port: " port
                        extra_opts="$extra_opts --priority $priority --weight $weight --port $port"
                    fi

                    run_cmd dns add $SELECTED_DOMAIN --type $dns_type --host "$host" --data "$data" $extra_opts
                fi
                ;;
            3)
                show_logo
                if select_domain; then
                    echo ""
                    python domeneshop_cli.py dns list $SELECTED_DOMAIN
                    echo ""
                    read -p "Record ID som skal oppdateres (0 for å avbryte): " record_id
                    if [ -n "$record_id" ] && [ "$record_id" != "0" ]; then
                        echo ""
                        echo -e "${GRAY}La felt stå tomt for å beholde eksisterende verdi${NC}"
                        echo ""
                        read -p "Ny data (IP/hostname/tekst): " new_data
                        read -p "Ny TTL: " new_ttl

                        update_opts=""
                        if [ -n "$new_data" ]; then
                            update_opts="$update_opts --data \"$new_data\""
                        fi
                        if [ -n "$new_ttl" ]; then
                            update_opts="$update_opts --ttl $new_ttl"
                        fi

                        if [ -n "$update_opts" ]; then
                            eval "python domeneshop_cli.py dns update $SELECTED_DOMAIN $record_id $update_opts"
                            echo ""
                            echo -e "${GRAY}Trykk Enter for å fortsette...${NC}"
                            read
                        fi
                    fi
                fi
                ;;
            4)
                show_logo
                if select_domain; then
                    echo ""
                    python domeneshop_cli.py dns list $SELECTED_DOMAIN
                    echo ""
                    read -p "Record ID som skal slettes (0 for å avbryte): " record_id
                    if [ -n "$record_id" ] && [ "$record_id" != "0" ]; then
                        run_cmd dns delete $SELECTED_DOMAIN $record_id
                    fi
                fi
                ;;
            0|"") break ;;
        esac
    done
}

menu_forwards() {
    while true; do
        show_logo
        echo -e "${BOLD}🔄 HTTP-VIDERESENDINGER${NC}"
        echo ""
        echo -e "  ${CYAN}1)${NC} List videresendinger"
        echo -e "  ${CYAN}2)${NC} Legg til videresending"
        echo -e "  ${CYAN}3)${NC} Oppdater videresending"
        echo -e "  ${CYAN}4)${NC} Slett videresending"
        echo ""
        echo -e "  ${CYAN}0)${NC} ← Tilbake til hovedmeny"
        echo ""
        read -p "Valg: " choice

        case $choice in
            1)
                show_logo
                if select_domain; then
                    run_cmd forwards list $SELECTED_DOMAIN
                fi
                ;;
            2)
                show_logo
                if select_domain; then
                    echo ""
                    read -p "Host (@ for rot): " host
                    read -p "Mål-URL (inkl. https://): " url
                    run_cmd forwards add $SELECTED_DOMAIN --host "$host" --url "$url"
                fi
                ;;
            3)
                show_logo
                if select_domain; then
                    echo ""
                    python domeneshop_cli.py forwards list $SELECTED_DOMAIN
                    echo ""
                    read -p "Host som skal oppdateres (0 for å avbryte): " host
                    if [ -n "$host" ] && [ "$host" != "0" ]; then
                        echo ""
                        read -p "Ny mål-URL (inkl. https://): " new_url
                        if [ -n "$new_url" ]; then
                            run_cmd forwards update $SELECTED_DOMAIN "$host" --url "$new_url"
                        fi
                    fi
                fi
                ;;
            4)
                show_logo
                if select_domain; then
                    echo ""
                    python domeneshop_cli.py forwards list $SELECTED_DOMAIN
                    echo ""
                    read -p "Host som skal slettes (0 for å avbryte): " host
                    if [ -n "$host" ] && [ "$host" != "0" ]; then
                        run_cmd forwards delete $SELECTED_DOMAIN "$host"
                    fi
                fi
                ;;
            0|"") break ;;
        esac
    done
}

menu_invoices() {
    while true; do
        show_logo
        echo -e "${BOLD}📄 FAKTURAER${NC}"
        echo ""
        echo -e "  ${CYAN}1)${NC} List alle fakturaer"
        echo -e "  ${CYAN}2)${NC} Vis ubetalte fakturaer"
        echo -e "  ${CYAN}3)${NC} Vis fakturadetaljer"
        echo ""
        echo -e "  ${CYAN}0)${NC} ← Tilbake til hovedmeny"
        echo ""
        read -p "Valg: " choice

        case $choice in
            1) run_cmd invoices list ;;
            2) run_cmd invoices list --status unpaid ;;
            3)
                show_logo
                echo -e "${BOLD}Velg faktura:${NC}"
                echo ""
                python domeneshop_cli.py invoices list
                echo ""
                read -p "Faktura-ID (eller 0 for å avbryte): " invoice_id
                if [ -n "$invoice_id" ] && [ "$invoice_id" != "0" ]; then
                    run_cmd invoices show $invoice_id
                fi
                ;;
            0|"") break ;;
        esac
    done
}

menu_ddns() {
    while true; do
        show_logo
        echo -e "${BOLD}⚡ DYNAMISK DNS${NC}"
        echo ""
        echo -e "  ${CYAN}1)${NC} Oppdater DDNS (bruk min IP)"
        echo -e "  ${CYAN}2)${NC} Oppdater DDNS (spesifiser IP)"
        echo ""
        echo -e "  ${CYAN}0)${NC} ← Tilbake til hovedmeny"
        echo ""
        read -p "Valg: " choice

        case $choice in
            1)
                echo ""
                read -p "Hostname (f.eks. www.example.com): " hostname
                if [ -n "$hostname" ]; then
                    run_cmd ddns "$hostname"
                fi
                ;;
            2)
                echo ""
                read -p "Hostname (f.eks. www.example.com): " hostname
                read -p "IP-adresse: " ip
                if [ -n "$hostname" ] && [ -n "$ip" ]; then
                    run_cmd ddns "$hostname" --ip "$ip"
                fi
                ;;
            0|"") break ;;
        esac
    done
}

menu_settings() {
    while true; do
        show_logo
        echo -e "${BOLD}⚙️  INNSTILLINGER${NC}"
        echo ""
        echo -e "  ${CYAN}1)${NC} Sett opp API-credentials"
        echo -e "  ${CYAN}2)${NC} Slett lagrede credentials"
        echo -e "  ${CYAN}3)${NC} Vis gjeldende status"
        echo ""
        echo -e "  ${CYAN}0)${NC} ← Tilbake til hovedmeny"
        echo ""
        read -p "Valg: " choice

        case $choice in
            1)
                echo ""
                python domeneshop_cli.py configure
                echo ""
                echo -e "${GRAY}Trykk Enter for å fortsette...${NC}"
                read
                ;;
            2) run_cmd configure --delete ;;
            3)
                echo ""
                if [ -f ~/.domeneshop-credentials ]; then
                    echo -e "${GREEN}✓ Credentials er lagret${NC}"
                else
                    echo -e "${YELLOW}⚠ Ingen credentials lagret${NC}"
                fi
                if [ -n "$DOMENESHOP_TOKEN" ]; then
                    echo -e "${GREEN}✓ Miljøvariabel DOMENESHOP_TOKEN er satt${NC}"
                fi
                echo ""
                echo -e "${GRAY}Trykk Enter for å fortsette...${NC}"
                read
                ;;
            0|"") break ;;
        esac
    done
}

main_menu() {
    while true; do
        show_logo
        echo -e "${BOLD}HOVEDMENY${NC}"
        echo ""
        echo -e "  ${CYAN}1)${NC} 📋 Domener"
        echo -e "  ${CYAN}2)${NC} 🌐 DNS"
        echo -e "  ${CYAN}3)${NC} 🔄 HTTP-videresendinger"
        echo -e "  ${CYAN}4)${NC} 📄 Fakturaer"
        echo -e "  ${CYAN}5)${NC} ⚡ Dynamisk DNS (DDNS)"
        echo ""
        echo -e "  ${CYAN}7)${NC} 🌍 Web GUI (nettleser)"
        echo -e "  ${CYAN}8)${NC} ⚙️  Innstillinger"
        echo -e "  ${CYAN}9)${NC} 📖 Avansert modus (skriv kommandoer)"
        echo -e "  ${CYAN}0)${NC} 🚪 Avslutt"
        echo ""
        read -p "Valg: " choice

        case $choice in
            1) menu_domains ;;
            2) menu_dns ;;
            3) menu_forwards ;;
            4) menu_invoices ;;
            5) menu_ddns ;;
            7)
                echo -e "${YELLOW}▸ Starter Web GUI på http://localhost:5050${NC}"
                python domeneshop_gui.py
                ;;
            8) menu_settings ;;
            9)
                show_logo
                echo -e "${BOLD}Avansert modus${NC} - Skriv kommandoer direkte"
                echo -e "${GRAY}Skriv 'exit' for å gå tilbake til menyen${NC}"
                echo ""
                while true; do
                    echo -ne "${GREEN}domeneshop${NC}${BOLD}>${NC} "
                    read cmd
                    if [ "$cmd" = "exit" ] || [ "$cmd" = "quit" ]; then
                        break
                    fi
                    if [ "$cmd" = "help" ]; then
                        python domeneshop_cli.py --help
                    elif [ -n "$cmd" ]; then
                        python domeneshop_cli.py $cmd
                    fi
                    echo ""
                done
                ;;
            0|"")
                show_logo
                echo -e "${CYAN}Ha det! 👋${NC}"
                echo ""
                exit 0
                ;;
        esac
    done
}

# Start
setup_env
main_menu
