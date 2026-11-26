#!/usr/bin/env bash
# shellcheck shell=bash
# ============================================================================
#  Morning Briefing – Proxmox VE LXC Installer (Community-Scripts-Stil)
# ----------------------------------------------------------------------------
#  Erstellt einen unprivilegierten LXC (naechste freie ID), installiert die
#  App als systemd-Service und verifiziert Web-UI + Service.
#
#  Einzeiler:
#    bash -c "$(wget -qLO - https://raw.githubusercontent.com/HatchetMan111/Morning-Briefing/main/install/morning-briefing.sh)"
#
#  Optionen:
#    --ctid <id>        CT-ID (Standard: naechste freie)
#    --storage <name>   Storage fuer Rootfs (Standard: local)
#    --bridge <name>    Netzwerk-Bridge (Standard: vmbr0)
#    --port <port>      Web-UI-Port (Standard: 8080)
#    --repo <owner/re>  GitHub-Repo (Standard: unten in GITHUB_REPO)
#    --source <pfad>    Lokaler Quellordner auf dem PVE-Host (statt GitHub)
#    --unattended       Keine Rueckfragen, alles mit Defaults
#    --debug            Ausfuehrliches Logging (bash -x + Logdatei)
#    --dry-run          Nur anzeigen, was passieren wuerde
#
#  Update:  Script erneut ausfuehren – existiert ein CT mit gleichem Namen,
#           wird die App aktualisiert (Code neu, Neustart, Verifikation).
# ============================================================================
set -euo pipefail

# ----------------------------- Variablen -----------------------------------
APP_NAME="Morning Briefing"
CT_NAME="morning-briefing"
APP_PORT="8080"
GITHUB_REPO="${GITHUB_REPO:-HatchetMan111/Morning-Briefing}"  # z.B. "user/morning-briefing"
LOCAL_SOURCE="${LOCAL_SOURCE:-}"        # alternativ: Pfad auf dem Host
DISK_SIZE="4"                           # GB
CORES="1"
RAM_SIZE="1024"                         # MiB
NET_BRIDGE="vmbr0"
STORAGE="${STORAGE:-local}"
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-local}"
APP_DIR="/opt/morning-briefing"
TAGS="community-script;morning-briefing"

CT_ID=""
UNATTENDED=0
DEBUG=0
DRY_RUN=0
LOG_FILE="/tmp/morning-briefing-install-$(date +%Y%m%d-%H%M%S).log"

# ------------------------------ Farbbibliothek ------------------------------
YW="\033[33m"; GN="\033[32m"; RD="\033[1;31m"; BL="\033[36m"; CL="\033[0m"; BFR="\r\033[K"
HEADER_LINES=(
  " _____  _   _ _   _  ____ ___ _   _ _____     _ _   "
  "|  ___| | | | | | | |/ ___|_ _| \ | | ____|   | | | |"
  "| |_ | | | | | | | | | |  | ||  \| |  _|     | | | |"
  "|  _|| |_| | |_| | | |___ | || |\  | |___  |_| |___"
  "|_|   \___/ \___/   \____|___|_| \_|_____|  (_)____/"
  "           P r o x m o x   L X C   I n s t a l l e r"
)

msg_info()    { echo -e "${BFR}  ${BL}[i]${CL} ${1}"; }
msg_ok()      { echo -e "${BFR}  ${GN}[ok]${CL} ${1}"; }
msg_warn()    { echo -e "${BFR}  ${YW}[!]${CL} ${1}"; }
header_info() { printf "\e[1;92m\e[J"; printf "%s\n" "${HEADER_LINES[@]}"; printf "\e[0m"; }

# ------------- Fehler-Handler: KOMPLETTE Fehlermeldungskette ----------------
on_error() {
  local exit_code=$1 line=$2 cmd=$3
  echo ""
  echo -e "${RD}━━━━━━━━ FEHLER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
  echo -e "${RD}Exit-Code :${CL} ${exit_code}"
  echo -e "${RD}Zeile     :${CL} ${line}"
  echo -e "${RD}Befehl    :${CL} ${cmd}"
  echo -e "${RD}Logdatei  :${CL} ${LOG_FILE} (mit --debug)"
  echo ""
  echo -e "${RD}Naechste Schritte:${CL}"
  echo "  1) Erneut mit Debug-Logging laufen lassen:"
  echo "     bash -x install/morning-briefing.sh --debug"
  echo "  2) Falls der Fehler IM Container auftrat, dort Logs zeigen:"
  echo "     pct exec ${CT_ID:-<ID>} -- journalctl -u ${CT_NAME} -n 100 --no-pager"
  echo "     pct exec ${CT_ID:-<ID>} -- bash -c 'cat ${APP_DIR}/*.log 2>/dev/null; true'"
  echo -e "${RD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
  exit "$exit_code"
}
trap 'on_error $? $LINENO "$BASH_COMMAND"' ERR

# ------------------------------ Argumente -----------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --ctid)       CT_ID="$2"; shift 2 ;;
    --storage)    STORAGE="$2"; shift 2 ;;
    --bridge)     NET_BRIDGE="$2"; shift 2 ;;
    --port)       APP_PORT="$2"; shift 2 ;;
    --repo)       GITHUB_REPO="$2"; shift 2 ;;
    --source)     LOCAL_SOURCE="$2"; shift 2 ;;
    --template-storage) TEMPLATE_STORAGE="$2"; shift 2 ;;
    --unattended) UNATTENDED=1; shift ;;
    --debug)      DEBUG=1; shift ;;
    --dry-run)    DRY_RUN=1; shift ;;
    -h|--help)    grep '^#' "$0" | head -30; exit 0 ;;
    *) echo "Unbekannte Option: $1"; exit 1 ;;
  esac
done

if [ "$DEBUG" -eq 1 ]; then
  exec > >(tee -a "$LOG_FILE") 2>&1
  set -x
else
  exec > >(tee -a "$LOG_FILE") 2>&1
fi

# ------------------------------ Checks --------------------------------------
if [ "$DRY_RUN" -eq 0 ]; then
  if [ "$(id -u)" -ne 0 ]; then
    echo "Dieses Script muss als root auf dem Proxmox-Host laufen." >&2
    exit 1
  fi
  if ! command -v pveversion >/dev/null 2>&1; then
    echo "pveversion nicht gefunden – ist das ein Proxmox-Host?" >&2
    exit 1
  fi
fi

if [ -z "$GITHUB_REPO" ] && [ -z "$LOCAL_SOURCE" ] && [ "$DRY_RUN" -eq 0 ]; then
  echo ""
  echo "Kein Quell-Repo konfiguriert!"
  echo "  a) Repo-Variable im Script setzen (GITHUB_REPO=\"user/morning-briefing\")"
  echo "  b) oder installieren mit:  ... install/morning-briefing.sh --repo user/morning-briefing"
  echo "  c) oder lokal testen mit:  ... install/morning-briefing.sh --source /pfad/zum/repo"
  exit 1
fi

# ------------------------------ Start ---------------------------------------
header_info
echo -e "  ${YW}App:${CL} ${APP_NAME}   ${YW}CT-Name:${CL} ${CT_NAME}   ${YW}Port:${CL} ${APP_PORT}"
[ "$DRY_RUN" -eq 1 ] && echo -e "\n  ${RD}[dry-run]${CL} Es wird nichts ausgeführt – nur Plan:\n"
run() {  # dry-run-tauglicher Wrapper
  if [ "$DRY_RUN" -eq 1 ]; then
    echo -e "  ${YW}[dry]${CL} $*"
  else
    "$@"
  fi
}

# ----------------------- CT-ID: nächste freie ID -----------------------------
if [ -z "$CT_ID" ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    CT_ID="<nächste freie ID>"
  else
    CT_ID=$(pvesh get /cluster/nextid)
  fi
fi
msg_ok "CT-ID: ${CT_ID}"

# ----------------------- Bestehenden CT prüfen (Update-Modus) ----------------
EXISTING_CT=""
if [ "$DRY_RUN" -eq 0 ]; then
  # pct list: VMID | Status | Lock | Name
  for ct in $(pct list | awk 'NR>1 {print $4}'); do
    if [ "$ct" = "$CT_NAME" ]; then
      EXISTING_CT=$(pct list | awk -v n="$CT_NAME" '$4==n {print $1}')
      break
    fi
  done
fi

# ------------------------------ Interaktive Parameter ------------------------
if [ "$UNATTENDED" -eq 0 ] && [ "$DRY_RUN" -eq 0 ] && [ -z "$EXISTING_CT" ]; then
  read -r -p "Storage für Rootfs [${STORAGE}]: " input
  STORAGE="${input:-$STORAGE}"
  read -r -p "Netzwerk-Bridge [${NET_BRIDGE}]: " input
  NET_BRIDGE="${input:-$NET_BRIDGE}"
  read -r -p "Web-UI-Port [${APP_PORT}]: " input
  APP_PORT="${input:-$APP_PORT}"
fi

# ============================================================================
#  UPDATE-MODUS: CT existiert bereits -> nur App aktualisieren
# ============================================================================
if [ -n "$EXISTING_CT" ]; then
  msg_info "CT '${CT_NAME}' existiert bereits (ID ${EXISTING_CT}) – Update-Modus"
  if [ -n "$LOCAL_SOURCE" ]; then
    tar -C "$LOCAL_SOURCE" --exclude=.git --exclude=node_modules --exclude=data \
        --exclude=__pycache__ --exclude=.venv -czf - . \
      | pct exec "$EXISTING_CT" -- tar -C "$APP_DIR" -xzf -
  else
    pct exec "$EXISTING_CT" -- bash -ec "cd '$APP_DIR' && git fetch --all && git reset --hard origin/main"
  fi
  run pct exec "$EXISTING_CT" -- bash -ec "'$APP_DIR/venv/bin/pip' install -q -r '$APP_DIR/requirements.txt' -r '$APP_DIR/requirements-server.txt'"
  run pct exec "$EXISTING_CT" -- bash -ec "sed 's/__PORT__/$APP_PORT/' '$APP_DIR/systemd/morning-briefing.service' > /etc/systemd/system/morning-briefing.service && systemctl daemon-reload && systemctl restart morning-briefing"
  sleep 5
  pct exec "$EXISTING_CT" -- systemctl is-active --quiet morning-briefing
  CT_IP=$(pct exec "$EXISTING_CT" -- hostname -I | awk '{print $1}')
  msg_ok "Update fertig: http://${CT_IP}:${APP_PORT}"
  exit 0
fi

# ============================================================================
#  NEU-INSTALLATION
# ============================================================================
msg_info "Lade Debian-12-Template (falls nötig)"
run pveam update
TEMPLATE=""
if [ "$DRY_RUN" -eq 1 ]; then
  TEMPLATE="<debian-12-standard>"
else
  TEMPLATE=$(pveam list "$TEMPLATE_STORAGE" 2>/dev/null | awk '/debian-12-standard/{print $1}' | sort -V | tail -1)
  if [ -z "$TEMPLATE" ]; then
    TEMPLATE_NAME=$(pveam available --section system | awk '/debian-12-standard/{print $2}' | sort -V | tail -1)
    pveam download "$TEMPLATE_STORAGE" "$TEMPLATE_NAME"
    TEMPLATE=$(pveam list "$TEMPLATE_STORAGE" 2>/dev/null | awk '/debian-12-standard/{print $1}' | sort -V | tail -1)
  fi
fi
msg_ok "Template: ${TEMPLATE}"

msg_info "Erstelle LXC ${CT_ID} (${CORES} vCPU, ${RAM_SIZE} MB RAM, ${DISK_SIZE} GB Disk, onboot=1)"
run pct create "$CT_ID" "${TEMPLATE:-$TEMPLATE_STORAGE:vztmpl/debian-12-standard_amd64.tar.zst}" \
  --hostname "$CT_NAME" \
  --tags "$TAGS" \
  --onboot 1 \
  --cores "$CORES" \
  --memory "$RAM_SIZE" \
  --rootfs "${STORAGE}:${DISK_SIZE}" \
  --net0 "name=eth0,bridge=${NET_BRIDGE},ip=dhcp,firewall=1" \
  --unprivileged 1 \
  --start 1

msg_info "Öffne Firewall-Port ${APP_PORT} im CT"
run bash -c "cat > /etc/pve/firewall/${CT_ID}.fw <<FW
[OPTIONS]
in: ACCEPT
out: ACCEPT

[RULES]
|IN ACCEPT|0|tcp||${APP_PORT}
|IN ACCEPT|0|tcp||22
FW"

# ----- Code ins App-Verzeichnis (GitHub oder lokal vom Host) -----
if [ -n "$LOCAL_SOURCE" ]; then
  msg_info "Kopiere App aus lokalem Quellordner: ${LOCAL_SOURCE}"
  run bash -c "tar -C '$LOCAL_SOURCE' --exclude=.git --exclude=node_modules --exclude=data --exclude=__pycache__ --exclude=.venv --exclude=dist.tmp -czf - . | pct exec '$CT_ID' -- bash -c 'mkdir -p $APP_DIR && tar -C $APP_DIR -xzf -'"
else
  msg_info "Klone App aus GitHub: ${GITHUB_REPO}"
  run pct exec "$CT_ID" -- bash -ec "apt-get update -qq && apt-get install -yqq git python3 python3-venv python3-pip curl >/dev/null"
  run pct exec "$CT_ID" -- git clone --depth 1 "https://github.com/${GITHUB_REPO}.git" "$APP_DIR"
fi

# ----- Installation im Container -----
msg_info "Installiere Abhängigkeiten (python3-venv, pip, systemd-freundlich)"
run pct exec "$CT_ID" -- bash -ec '
  set -euo pipefail
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -yqq git python3 python3-venv python3-pip curl >/dev/null
  python3 -m venv '"$APP_DIR"'/venv
  '"$APP_DIR"'/venv/bin/pip install --upgrade pip -q
  '"$APP_DIR"'/venv/bin/pip install -q -r '"$APP_DIR"'/requirements.txt -r '"$APP_DIR"'/requirements-server.txt
  echo "[container] Python-Setup abgeschlossen"
'

msg_info "Erstelle Konfiguration (config.yaml bleibt bei Updates erhalten)"
run pct exec "$CT_ID" -- bash -ec "
  set -euo pipefail
  cd $APP_DIR
  [ -f .env ] || cp .env.example .env
  [ -f profile/context.md ] || mkdir -p profile
  echo '[container] Konfiguration bereit'
"

msg_info "Installiere systemd-Service (Restart=always, nach network-online)"
run pct exec "$CT_ID" -- bash -ec "
  sed 's/__PORT__/$APP_PORT/' $APP_DIR/systemd/morning-briefing.service > /etc/systemd/system/morning-briefing.service
  systemctl daemon-reload
  systemctl enable --now morning-briefing
"

# ------------------------------ VERIFIKATION --------------------------------
msg_info "Verifiziere Service (systemctl is-active)"
run pct exec "$CT_ID" -- bash -ec "
  for i in \$(seq 1 20); do
    if systemctl is-active --quiet morning-briefing; then break; fi
    sleep 1
  done
  if ! systemctl is-active --quiet morning-briefing; then
    echo 'FEHLER: Service startet nicht – Logs:' >&2
    journalctl -u morning-briefing -n 80 --no-pager >&2 || true
    exit 1
  fi
  echo '[verify] Service: aktiv'
"

msg_info "Verifiziere Web-UI (HTTP-Check auf localhost:${APP_PORT})"
run pct exec "$CT_ID" -- bash -ec "
  for i in \$(seq 1 30); do
    code=\$(curl -s -o /dev/null -w '%{http_code}' http://localhost:$APP_PORT/api/status || true)
    if [ \"\$code\" = '200' ]; then echo '[verify] Web-UI: HTTP 200'; exit 0; fi
    sleep 1
  done
  echo 'FEHLER: Web-UI antwortet nicht (letzter Code: '\$code')' >&2
  journalctl -u morning-briefing -n 80 --no-pager >&2 || true
  exit 1
"

if [ "$DRY_RUN" -eq 1 ]; then
  CT_IP="<lxc-ip>"
else
  CT_IP=$(pct exec "$CT_ID" -- hostname -I | awk '{print $1}')
fi

# ------------------------------ Zusammenfassung -----------------------------
echo ""
echo -e "${GN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo -e "${GN} ✓ ${APP_NAME} installiert${CL}"
echo -e "${GN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo "  CT-ID      : ${CT_ID}  (Name: ${CT_NAME})"
echo "  Web-UI     : http://${CT_IP}:${APP_PORT}"
echo "  Service    : systemctl status morning-briefing (im CT)"
echo "  Logs       : pct exec ${CT_ID} -- journalctl -u morning-briefing -f"
echo "  Konfig     : pct exec ${CT_ID} -- cat ${APP_DIR}/config.yaml"
echo ""
echo "  Nächste Schritte:"
echo "   1) Web-UI öffnen → Tab 'Einstellungen' → Telegram/Gemini-Keys"
echo "   2) '▶ Jetzt starten' klicken – das erste Briefing entsteht"
echo "   3) Danach läuft der Scheduler täglich um die in config.yaml gesetzte Zeit"
echo -e "${GN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
