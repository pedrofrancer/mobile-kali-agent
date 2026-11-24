#!/data/data/com.termux/files/usr/bin/bash
# nethunter-rootless.sh — instala o Kali NetHunter Rootless no Termux.
# Fonte oficial (Offensive Security). Sem root, sem destravar nada.
set -euo pipefail
pkg install -y wget
wget -O install-nethunter-termux \
  https://offs.ec/2MceZWr
chmod +x install-nethunter-termux
echo "rode:  ./install-nethunter-termux"
echo "depois:  nethunter    # entra no chroot"
echo "dentro:  sudo apt update && sudo apt install -y nmap netcat-traditional whois dnsutils metasploit-framework"
