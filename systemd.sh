#!/usr/bin/env bash
# ==============================================================================
#  🤖 UBOT - Systemd Service Management Script
# ==============================================================================
#  Fitur:
#    - Setup virtual environment
#    - Install requirements.txt
#    - Load .env
#    - Install / Enable systemd service
#    - Start / Stop / Restart
#    - Status
#    - Live Logs
#    - Uninstall
# ==============================================================================

set -u

# ==============================================================================
# KONFIGURASI
# ==============================================================================

SERVICE_NAME="$(basename "$(pwd)")"
APP_DIR="$(pwd)"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

VENV_DIR="${APP_DIR}/venv"
ENV_FILE="${APP_DIR}/.env"
REQUIREMENTS_FILE="${APP_DIR}/requirements.txt"
START_SCRIPT="${APP_DIR}/start.sh"

# User asli, bukan root ketika menggunakan sudo
CURRENT_USER="${SUDO_USER:-$(whoami)}"

# ==============================================================================
# DETEKSI PYTHON
# ==============================================================================

if [ -x "${VENV_DIR}/bin/python3" ]; then
    PYTHON_EXEC="${VENV_DIR}/bin/python3"
else
    PYTHON_EXEC="$(command -v python3 2>/dev/null || true)"
fi

# ==============================================================================
# WARNA TERMINAL
# ==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ==============================================================================
# ROOT CHECK
# ==============================================================================

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}[!] Script harus dijalankan dengan sudo / root!${NC}"
        echo
        echo -e "Contoh:"
        echo -e "  ${BOLD}sudo bash systemd.sh install${NC}"
        exit 1
    fi
}

# ==============================================================================
# VALIDASI FILE
# ==============================================================================

check_files() {
    if [ ! -f "${REQUIREMENTS_FILE}" ]; then
        echo -e "${RED}[✘] requirements.txt tidak ditemukan!${NC}"
        echo -e "    ${REQUIREMENTS_FILE}"
        exit 1
    fi

    if [ ! -f "${START_SCRIPT}" ]; then
        echo -e "${RED}[✘] start.sh tidak ditemukan!${NC}"
        echo -e "    ${START_SCRIPT}"
        exit 1
    fi
}

# ==============================================================================
# SETUP VIRTUAL ENVIRONMENT
# ==============================================================================

setup_venv() {
    echo -e "${CYAN}[*] Menyiapkan virtual environment...${NC}"

    if [ ! -d "${VENV_DIR}" ]; then
        echo -e "${YELLOW}[*] Membuat virtual environment...${NC}"

        if ! python3 -m venv "${VENV_DIR}"; then
            echo -e "${RED}[✘] Gagal membuat virtual environment.${NC}"
            exit 1
        fi

        echo -e "${GREEN}[✔] Virtual environment dibuat.${NC}"
    else
        echo -e "${YELLOW}[!] Virtual environment sudah ada.${NC}"
    fi

    PYTHON_EXEC="${VENV_DIR}/bin/python3"

    echo -e "${BLUE}[*] Python:${NC} ${PYTHON_EXEC}"

    echo -e "${YELLOW}[*] Upgrade pip...${NC}"
    "${PYTHON_EXEC}" -m pip install --upgrade pip

    echo -e "${YELLOW}[*] Install dependencies...${NC}"
    "${PYTHON_EXEC}" -m pip install -r "${REQUIREMENTS_FILE}"

    echo -e "${GREEN}[✔] Dependencies berhasil dipasang.${NC}"
}

# ==============================================================================
# 1. INSTALL SERVICE
# ==============================================================================

install_service() {
    check_root
    check_files

    echo
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${BOLD}              🤖 UBOT SYSTEMD INSTALL${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo

    echo -e "${BLUE}[*] Service Name :${NC} ${SERVICE_NAME}"
    echo -e "${BLUE}[*] App Directory:${NC} ${APP_DIR}"
    echo -e "${BLUE}[*] System User  :${NC} ${CURRENT_USER}"

    # --------------------------------------------------------------------------
    # Setup Venv
    # --------------------------------------------------------------------------

    setup_venv

    # --------------------------------------------------------------------------
    # Environment File
    # --------------------------------------------------------------------------

    if [ -f "${ENV_FILE}" ]; then
        ENV_LINE="EnvironmentFile=${ENV_FILE}"

        echo
        echo -e "${GREEN}[✔] File .env ditemukan.${NC}"
        echo -e "    ${ENV_FILE}"
    else
        ENV_LINE=""

        echo
        echo -e "${YELLOW}[!] File .env tidak ditemukan.${NC}"
        echo -e "    EnvironmentFile dilewati."
    fi

    # --------------------------------------------------------------------------
    # Buat Systemd Service
    # --------------------------------------------------------------------------

    echo
    echo -e "${YELLOW}[*] Membuat systemd service...${NC}"

    cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=Ubot ${SERVICE_NAME}
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple

User=${CURRENT_USER}
WorkingDirectory=${APP_DIR}

${ENV_LINE}

ExecStart=/bin/bash -c 'source ${VENV_DIR}/bin/activate && bash ${START_SCRIPT}'

Restart=always
RestartSec=5s

KillSignal=SIGINT
TimeoutStopSec=15s

Environment=PYTHONUNBUFFERED=1

StandardOutput=journal
StandardError=journal

LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

    chmod 644 "${SERVICE_FILE}"

    # --------------------------------------------------------------------------
    # Reload + Enable
    # --------------------------------------------------------------------------

    echo -e "${YELLOW}[*] Reload systemd...${NC}"
    systemctl daemon-reload

    echo -e "${YELLOW}[*] Enable service...${NC}"
    systemctl enable "${SERVICE_NAME}"

    echo
    echo -e "${GREEN}=====================================================${NC}"
    echo -e "${GREEN}[✔] Service berhasil dipasang!${NC}"
    echo -e "${GREEN}=====================================================${NC}"
    echo
    echo -e "Untuk menjalankan:"
    echo -e "  ${BOLD}sudo bash systemd.sh start${NC}"
}

# ==============================================================================
# 2. START SERVICE
# ==============================================================================

start_service() {
    check_root

    if [ ! -f "${SERVICE_FILE}" ]; then
        echo -e "${YELLOW}[!] Service belum terpasang.${NC}"
        echo -e "${YELLOW}[*] Memasang service terlebih dahulu...${NC}"
        echo

        install_service
    fi

    echo -e "${YELLOW}[*] Menjalankan ${SERVICE_NAME}...${NC}"

    systemctl start "${SERVICE_NAME}"

    sleep 1

    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo
        echo -e "${GREEN}[✔] ${SERVICE_NAME} berhasil online di background.${NC}"
    else
        echo
        echo -e "${RED}[✘] Gagal menjalankan ${SERVICE_NAME}.${NC}"
        echo
        echo -e "${YELLOW}Periksa log:${NC}"
        echo -e "  ${BOLD}sudo bash systemd.sh logs${NC}"

        return 1
    fi
}

# ==============================================================================
# 3. STOP SERVICE
# ==============================================================================

stop_service() {
    check_root

    echo -e "${YELLOW}[*] Menghentikan ${SERVICE_NAME}...${NC}"

    systemctl stop "${SERVICE_NAME}"

    echo -e "${GREEN}[✔] ${SERVICE_NAME} berhasil dihentikan.${NC}"
}

# ==============================================================================
# 4. RESTART SERVICE
# ==============================================================================

restart_service() {
    check_root

    if [ ! -f "${SERVICE_FILE}" ]; then
        echo -e "${RED}[✘] Service belum terpasang.${NC}"
        echo -e "    Gunakan: ${BOLD}sudo bash systemd.sh install${NC}"
        return 1
    fi

    echo -e "${YELLOW}[*] Restart ${SERVICE_NAME}...${NC}"

    systemctl restart "${SERVICE_NAME}"

    sleep 1

    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo -e "${GREEN}[✔] ${SERVICE_NAME} berhasil di-restart.${NC}"
    else
        echo -e "${RED}[✘] Gagal melakukan restart.${NC}"
        echo
        echo -e "${YELLOW}Periksa log:${NC}"
        echo -e "  ${BOLD}sudo bash systemd.sh logs${NC}"

        return 1
    fi
}

# ==============================================================================
# 5. STATUS SERVICE
# ==============================================================================

status_service() {
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${BOLD}              STATUS ${SERVICE_NAME}${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo

    systemctl status "${SERVICE_NAME}" --no-pager
}

# ==============================================================================
# 6. LIVE LOGS
# ==============================================================================

logs_service() {
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${BOLD}           LIVE LOGS - ${SERVICE_NAME}${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo
    echo -e "${YELLOW}Tekan Ctrl+C untuk keluar.${NC}"
    echo

    journalctl -u "${SERVICE_NAME}" -f -n 50
}

# ==============================================================================
# 7. UNINSTALL SERVICE
# ==============================================================================

uninstall_service() {
    check_root

    echo -e "${YELLOW}[*] Menghapus ${SERVICE_NAME}...${NC}"

    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    systemctl disable "${SERVICE_NAME}" 2>/dev/null || true

    rm -f "${SERVICE_FILE}"

    systemctl daemon-reload
    systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true

    echo -e "${GREEN}[✔] Service ${SERVICE_NAME} berhasil dihapus.${NC}"
    echo
    echo -e "${YELLOW}[!] venv, .env, source code, dan file project tidak dihapus.${NC}"
}

# ==============================================================================
# 8. MENU INTERAKTIF
# ==============================================================================

menu() {
    while true; do
        clear

        echo -e "${CYAN}=====================================================${NC}"
        echo -e "${BOLD}                 🤖 UBOT SYSTEMD 🤖${NC}"
        echo -e "${CYAN}=====================================================${NC}"
        echo
        echo -e " [1] 📦 Install / Pasang Service"
        echo -e " [2] ▶️  Jalankan Bot"
        echo -e " [3] ⏹️  Hentikan Bot"
        echo -e " [4] 🔄 Restart Bot"
        echo -e " [5] 📊 Cek Status"
        echo -e " [6] 📜 Pantau Live Logs"
        echo -e " [7] 🗑️  Uninstall Service"
        echo -e " [0] ❌ Keluar"
        echo
        echo -e "${CYAN}-----------------------------------------------------${NC}"

        read -rp "Pilih opsi [0-7]: " opt

        case "${opt}" in
            1)
                install_service
                ;;
            2)
                start_service
                ;;
            3)
                stop_service
                ;;
            4)
                restart_service
                ;;
            5)
                status_service
                ;;
            6)
                logs_service
                ;;
            7)
                uninstall_service
                ;;
            0)
                echo -e "${GREEN}[✔] Keluar.${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}[!] Pilihan tidak valid.${NC}"
                ;;
        esac

        echo
        read -rp "Tekan Enter untuk kembali ke menu..."
    done
}

# ==============================================================================
# 9. CLI ROUTER
# ==============================================================================

case "${1:-}" in
    install|setup)
        install_service
        ;;

    start)
        start_service
        ;;

    stop)
        stop_service
        ;;

    restart|reload)
        restart_service
        ;;

    status)
        status_service
        ;;

    log|logs)
        logs_service
        ;;

    uninstall|remove)
        uninstall_service
        ;;

    *)
        if [ -n "${1:-}" ]; then
            echo -e "${RED}[!] Perintah '${1}' tidak dikenal.${NC}"
            echo
            echo "Gunakan:"
            echo "  $0 install"
            echo "  $0 start"
            echo "  $0 stop"
            echo "  $0 restart"
            echo "  $0 status"
            echo "  $0 logs"
            echo "  $0 uninstall"
            exit 1
        else
            menu
        fi
        ;;
esac