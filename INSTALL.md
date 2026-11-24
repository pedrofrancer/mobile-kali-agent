# INSTALL.md — MOBILE KALI AGENT

Dois lados. O **celular** (Moto G35) hospeda o Kali e o sshd; você roda os
passos 1–4 no próprio aparelho, em Termux. O **PC** (ou iPhone) é o cliente; o
passo 5 é no PC e dirige tudo pelo `mobile_kali.py`.

O aparelho não tem root (bootloader travado por e-fuse). Toda esta instalação é
**rootless**, por isso usa NetHunter Rootless e SSH na porta 8022.

---

## 1. Termux (no celular)

Instale o **Termux** e o **Termux:Boot** pela **F-Droid** (não pela Play Store;
a versão da loja está congelada e quebra `pkg`):

- https://f-droid.org/packages/com.termux/
- https://f-droid.org/packages/com.termux.boot/

Abra o Termux e rode o bootstrap (copie `scripts/termux-bootstrap.sh` para o
aparelho, ou cole o conteúdo):

```bash
bash termux-bootstrap.sh
```

Ele instala `openssh tmux git nodejs-lts python termux-services tailscale`,
configura o `sshd` na porta 8022, cria `~/.ssh/authorized_keys` e o autostart
em `~/.termux/boot/`. No fim ele imprime o `whoami` (o usuário do SSH) e o IP
da LAN.

## 2. Kali NetHunter Rootless (no celular)

```bash
bash nethunter-rootless.sh
./install-nethunter-termux
nethunter            # entra no chroot Kali
# dentro do Kali:
sudo apt update && sudo apt install -y \
  nmap netcat-traditional whois dnsutils hydra john nikto sqlmap metasploit-framework
```

## 3. Chave SSH

**No cliente** (PC/iPhone), gere a chave — nunca no celular:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_moto -C "mobile-kali"
```

Copie a **pública** (`id_ed25519_moto.pub`) e, **no Termux do celular**:

```bash
echo "ssh-ed25519 AAAA... mobile-kali" >> ~/.ssh/authorized_keys
```

## 4. Tailscale (acesso de qualquer lugar)

No celular, instale o app **Tailscale** e faça login; no Termux:

```bash
tailscale up
tailscale status      # anote o nome/IP 100.x do aparelho
```

Instale o Tailscale também no PC, Linux e iPhone, na mesma conta. Ligue
**MagicDNS** no painel para usar nome em vez de IP. Desligue a otimização de
bateria do Termux e do Tailscale (Configurações, Apps), ou o Android derruba os
serviços.

Suba o sshd agora: `termux-wake-lock && sshd`.

## 5. Cliente (no PC)

```bash
cd mobile-kali-agent
cp config/mobile.conf.example config/mobile.conf
# edite host (nome Tailscale do celular), user (o whoami do passo 1), port 8022,
# identity_file (~/.ssh/id_ed25519_moto)

# ajuste a faixa da sua rede:
#   no celular: ip route | grep default   -> descobre o gateway e a /24
# edite config/targets.txt com o SEU CIDR privado

python mobile_kali.py connect     # prova a conexao
python mobile_kali.py status
python mobile_kali.py tools --install
python mobile_kali.py network
python mobile_kali.py audit
python mobile_kali.py report
```

Pré-requisito no PC: Python 3.9+ e o cliente `ssh` (OpenSSH já vem no Windows
10/11 e no Linux). Sem pip install — o módulo usa só a biblioteca padrão.

---

## Limitações do Android (documentadas)

- **Sem root** neste G35: bootloader travado (`lcs: 5`, e-fuse). Não há como
  destravar por software.
- **Sem `CAP_NET_RAW`**: `nmap -sS/-O`, `tcpdump`, `scapy` raw, `arp-scan`,
  monitor mode e deauth Wi-Fi **não funcionam**. Use `nmap -sT`. Para L2:
  adaptador Wi-Fi USB + PC.
- **RAM 3.4 GB**: Metasploit come ~1 GB; feche o resto antes de `msfconsole`.
- **Android mata background**: wake-lock + autostart + bateria sem restrição
  são obrigatórios para servir 24/7.
- **Carga 24/7**: limite em ~80% (Configurações, Bateria) ou tomada com timer;
  sem root não há ACC para isso.
