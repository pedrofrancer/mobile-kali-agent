# MOBILE KALI AGENT

Usa o **Claude Code no PC** como agente de administração de um **Kali Linux
rootless** rodando no **Motorola Moto G35 5G** (Android 15), alcançado por SSH
sobre Tailscale. O Kali vira um ambiente Linux remoto ARM64 para estudo de Red
Team, pentest e auditoria, **limitado à rede doméstica autorizada**.

Construído a partir de `config/spec-origem.txt` (o pedido MOBILE KALI AGENT) e
regido por `config/politica-redteam.txt` + [`SECURITY.md`](SECURITY.md).

## O que é, em uma frase

Um módulo Python (`mobile_kali.py`) que centraliza a conexão SSH e as operações
remotas, mais seis comandos de Claude Code (`/mobile-*`) que o acionam. Sem
dependência externa: fala com o cliente `ssh` do sistema.

## Por que rootless

O bootloader deste G35 está travado por e-fuse (`lcs: 5`, `secure: true`), sem
comando de unlock no fastboot. Root é impossível por software neste aparelho.
NetHunter **Rootless** entrega recon, enumeração, password auditing, vuln
assessment e exploração de camada de aplicação — tudo que não exige
`CAP_NET_RAW`. Wi-Fi monitor mode, deauth, `tcpdump` e `scapy` raw ficam de
fora (precisam de root → outro hardware). Detalhe em [`SECURITY.md`](SECURITY.md).

## Instalação

Passo a passo dos dois lados (celular e PC) em [`INSTALL.md`](INSTALL.md).

## Uso

```bash
cd mobile-kali-agent
python mobile_kali.py connect      # prova a conexao, identifica o sistema
python mobile_kali.py status       # ARM64, CPU, RAM, disco
python mobile_kali.py tools        # estado das ferramentas (--install instala)
python mobile_kali.py run "<cmd>"  # comando arbitrario no Kali remoto
python mobile_kali.py network      # ping sweep na rede autorizada
python mobile_kali.py audit        # inventario de servicos (nmap -sT -sV)
python mobile_kali.py report       # consolida logs em reports/
```

No Claude Code, os mesmos fluxos por slash command: `/mobile-status`,
`/mobile-connect`, `/mobile-tools`, `/mobile-network`, `/mobile-audit`,
`/mobile-report`.

## Escopo (não negociável)

Toda varredura é recusada, em código (`_validar_alvo`), se o alvo não for rede
privada ou não estiver em `config/targets.txt`. Isso implementa a cláusula
INTEGRIDADE da política: sistemas próprios ou expressamente autorizados, nunca
terceiros. Edite `config/targets.txt` com a sua faixa doméstica antes de rodar.

## Estrutura

```
mobile-kali-agent/
├── README.md
├── INSTALL.md
├── SECURITY.md
├── mobile_kali.py            # modulo central (SSH + operacoes remotas)
├── config/
│   ├── mobile.conf.example   # host, user, porta, chave
│   ├── targets.txt           # CIDRs autorizados (trava de escopo)
│   ├── sshd_config.termux    # trecho do sshd no Termux (porta 8022)
│   ├── spec-origem.txt       # o pedido original
│   └── politica-redteam.txt  # a politica operacional
├── scripts/
│   ├── termux-bootstrap.sh   # roda no celular: base + sshd + persistencia
│   └── nethunter-rootless.sh # roda no celular: instala o Kali rootless
├── modules/                  # espaco para modulos Python adicionais
├── reports/                  # relatorios gerados
├── logs/                     # logs por operacao
└── .claude/commands/         # os seis /mobile-*
```

## Limites de hardware (resumo)

| Capacidade | Neste G35 |
|---|---|
| recon, `nmap -sT -sV`, dns, whois, nikto, sqlmap | funciona |
| password auditing / brute force (hydra), hash (john) | funciona (alvo autorizado) |
| metasploit | roda (RAM 3.4 GB aperta; sniff/spoof limitado) |
| Wi-Fi monitor/deauth, tcpdump, scapy raw, arp-scan | indisponível (precisa root) |
