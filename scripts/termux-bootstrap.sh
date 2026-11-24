#!/data/data/com.termux/files/usr/bin/bash
# termux-bootstrap.sh — roda DENTRO do Termux no Moto G35 (nao no PC).
# Prepara pacotes base, sshd na 8022 e persistencia. NetHunter e Tailscale
# sao passos separados (ver INSTALL.md). Nao precisa de root.
set -euo pipefail

echo "[1/5] atualizando pacotes"
pkg update -y && pkg upgrade -y

echo "[2/5] base: openssh, tmux, git, node, python, tailscale"
pkg install -y openssh tmux git nodejs-lts python termux-services tailscale

echo "[3/5] sshd na porta 8022"
mkdir -p "$PREFIX/etc/ssh"
grep -q '^Port 8022' "$PREFIX/etc/ssh/sshd_config" 2>/dev/null \
  || printf '\nPort 8022\nPasswordAuthentication no\nPubkeyAuthentication yes\n' \
       >> "$PREFIX/etc/ssh/sshd_config"

echo "[4/5] authorized_keys"
mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"
touch "$HOME/.ssh/authorized_keys"; chmod 600 "$HOME/.ssh/authorized_keys"
echo "    cole sua chave publica com:"
echo "    echo 'ssh-ed25519 AAAA... comentario' >> ~/.ssh/authorized_keys"

echo "[5/5] persistencia (Termux:Boot)"
mkdir -p "$HOME/.termux/boot"
cat > "$HOME/.termux/boot/10-sshd.sh" <<'BOOT'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
sshd
BOOT
chmod +x "$HOME/.termux/boot/10-sshd.sh"

echo
echo "pronto. suba agora: termux-wake-lock && sshd"
echo "IP na LAN: $(ifconfig wlan0 2>/dev/null | awk '/inet /{print $2}')"
echo "whoami: $(whoami)   (use este nome em config/mobile.conf)"
