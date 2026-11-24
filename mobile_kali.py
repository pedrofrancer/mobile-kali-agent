#!/usr/bin/env python3
"""mobile_kali.py — conexao SSH e operacoes remotas no Kali do Moto G35.

Centraliza o acesso ao Kali NetHunter Rootless rodando em Termux no celular,
alcancado por SSH (porta 8022) sobre a rede Tailscale. Nao usa dependencia
externa: fala com o cliente `ssh` do proprio sistema (OpenSSH no Windows,
Linux e macOS). Toda operacao de rede e limitada, por codigo, a prefixos
privados declarados em config/targets.txt.

Uso:
    python mobile_kali.py status
    python mobile_kali.py connect
    python mobile_kali.py tools [--install]
    python mobile_kali.py run "<comando>"
    python mobile_kali.py network [--cidr 192.168.0.0/24]
    python mobile_kali.py audit [--cidr ...]
    python mobile_kali.py report

A configuracao vem de config/mobile.conf (JSON). Veja config/mobile.conf.example.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import ipaddress
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CONF = RAIZ / "config" / "mobile.conf"
TARGETS = RAIZ / "config" / "targets.txt"
REPORTS = RAIZ / "reports"
LOGS = RAIZ / "logs"

# Ferramentas do laboratorio. O terceiro campo marca se a ferramenta precisa de
# CAP_NET_RAW (root), ausente no Android rootless: fica documentada, nao some.
FERRAMENTAS = [
    ("nmap", "nmap", False),
    ("netcat", "netcat-traditional", False),
    ("whois", "whois", False),
    ("dnsutils", "dnsutils", False),
    ("python3", "python3", False),
    ("scapy", "python3-scapy", True),
    ("tcpdump", "tcpdump", True),
    ("arp-scan", "arp-scan", True),
    ("tshark", "tshark", True),
    ("metasploit", "metasploit-framework", False),
    # Password auditing / vuln assessment: clientes TCP ou offline, sem raw socket.
    # Autorizados pela politica do lab, SEMPRE contra host dentro de targets.txt.
    ("hydra", "hydra", False),
    ("john", "john", False),
    ("hashcat", "hashcat", False),   # modo CPU no ARM; sem OpenCL na Mali T760
    ("nikto", "nikto", False),
    ("sqlmap", "sqlmap", False),
    ("wordlists", "wordlists", False),  # traz rockyou.txt.gz em /usr/share/wordlists
]


class ErroConfig(RuntimeError):
    pass


def carregar_config() -> dict:
    if not CONF.exists():
        raise ErroConfig(
            f"config nao encontrada: {CONF}\n"
            f"copie config/mobile.conf.example para config/mobile.conf e preencha."
        )
    dados = json.loads(CONF.read_text(encoding="utf-8"))
    for campo in ("host", "user", "port"):
        if not dados.get(campo):
            raise ErroConfig(f"campo obrigatorio ausente em mobile.conf: {campo}")
    dados.setdefault("identity_file", "")
    dados.setdefault("connect_timeout", 10)
    return dados


def _base_ssh(cfg: dict) -> list[str]:
    """Argumentos comuns de ssh: chave, porta, nao-interativo, sem senha."""
    args = [
        "ssh",
        "-p", str(cfg["port"]),
        "-o", "BatchMode=yes",            # nunca pergunta senha; chave ou falha
        "-o", f"ConnectTimeout={cfg['connect_timeout']}",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=15",
    ]
    if cfg.get("identity_file"):
        ident = os.path.expanduser(cfg["identity_file"])
        args += ["-o", "IdentitiesOnly=yes", "-i", ident]
    args.append(f"{cfg['user']}@{cfg['host']}")
    return args


def ssh_exec(cfg: dict, comando: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Roda UM comando no Kali remoto. Retorna o CompletedProcess cru."""
    argv = _base_ssh(cfg) + [comando]
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout
    )


def _log(nome: str, texto: str) -> Path:
    LOGS.mkdir(exist_ok=True)
    carimbo = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = LOGS / f"{carimbo}-{nome}.log"
    destino.write_text(texto, encoding="utf-8")
    return destino


# --------------------------------------------------------------------------- #
# Subcomandos
# --------------------------------------------------------------------------- #
def cmd_connect(cfg: dict, _args) -> int:
    """Prova a conexao e identifica o sistema remoto."""
    r = ssh_exec(cfg, "uname -a; echo '---'; id")
    if r.returncode != 0:
        print(f"[FALHA] ssh retornou {r.returncode}", file=sys.stderr)
        print(r.stderr.strip(), file=sys.stderr)
        _dica_falha(cfg)
        return r.returncode
    print(r.stdout.strip())
    return 0


def cmd_status(cfg: dict, _args) -> int:
    """Arquitetura, CPU, RAM, armazenamento e uptime do Kali remoto."""
    script = (
        "echo '## IDENTIDADE'; "
        "(lsb_release -ds 2>/dev/null || cat /etc/os-release | head -1); "
        "uname -m; uname -r; "
        "echo '## CPU'; "
        "(nproc) ; (grep -m1 'model name' /proc/cpuinfo 2>/dev/null || grep -m1 Hardware /proc/cpuinfo); "
        "echo '## RAM'; free -h | awk 'NR<=2'; "
        "echo '## DISCO'; df -h / /home 2>/dev/null | awk 'NR==1||/\\//'; "
        "echo '## UPTIME'; uptime -p 2>/dev/null || uptime"
    )
    r = ssh_exec(cfg, script)
    saida = r.stdout.strip() or r.stderr.strip()
    print(saida)
    _log("status", saida)
    if r.returncode != 0:
        _dica_falha(cfg)
    return r.returncode


def cmd_tools(cfg: dict, args) -> int:
    """Lista o estado de cada ferramenta; com --install, instala as que faltam."""
    nomes = " ".join(bin_ for bin_, _, _ in FERRAMENTAS)
    check = (
        "for b in " + nomes + "; do "
        "if command -v $b >/dev/null 2>&1; then echo \"OK  $b\"; "
        "else echo \"--  $b\"; fi; done"
    )
    r = ssh_exec(cfg, check)
    print("estado atual (OK=presente, --=ausente):")
    print(r.stdout.strip())

    if not getattr(args, "install", False):
        print("\nfaltando raw-socket (root): scapy/tcpdump/arp-scan/tshark nao "
              "capturam L2 no Android rootless.")
        print("para instalar o que falta: python mobile_kali.py tools --install")
        return r.returncode

    faltam = [pkg for (binname, pkg, _raw) in FERRAMENTAS
              if f"--  {binname}" in r.stdout]
    if not faltam:
        print("\nnada a instalar.")
        return 0
    print(f"\ninstalando: {', '.join(faltam)}")
    inst = "sudo apt-get update && sudo apt-get install -y " + " ".join(faltam)
    r2 = ssh_exec(cfg, inst, timeout=1800)
    log = _log("tools-install", r2.stdout + "\n--- STDERR ---\n" + r2.stderr)
    print(f"log: {log}")
    return r2.returncode


def cmd_run(cfg: dict, args) -> int:
    """Executa um comando arbitrario no Kali remoto."""
    if not args.comando:
        print("uso: python mobile_kali.py run \"<comando>\"", file=sys.stderr)
        return 2
    r = ssh_exec(cfg, args.comando, timeout=args.timeout)
    if r.stdout:
        print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="", file=sys.stderr)
    return r.returncode


def _cidrs_autorizados() -> list[str]:
    if not TARGETS.exists():
        raise ErroConfig(
            f"alvos nao declarados: {TARGETS}\n"
            f"escreva um CIDR privado por linha (ex.: 192.168.0.0/24)."
        )
    linhas = []
    for ln in TARGETS.read_text(encoding="utf-8").splitlines():
        ln = ln.split("#", 1)[0].strip()
        if ln:
            linhas.append(ln)
    return linhas


def _validar_alvo(cidr: str) -> ipaddress._BaseNetwork:
    """So aceita rede PRIVADA e que esteja na lista de autorizados.

    Esta e a trava de escopo do SECURITY.md: alvo fora de RFC1918 ou fora da
    lista declarada e recusado antes de qualquer pacote sair.
    """
    rede = ipaddress.ip_network(cidr, strict=False)
    if not rede.is_private:
        raise ErroConfig(
            f"alvo recusado: {cidr} nao e rede privada (RFC1918/ULA). "
            f"a ferramenta so varre a rede domestica autorizada."
        )
    autorizados = [ipaddress.ip_network(c, strict=False) for c in _cidrs_autorizados()]
    if not any(rede.subnet_of(a) or rede == a for a in autorizados):
        raise ErroConfig(
            f"alvo recusado: {cidr} nao esta em config/targets.txt. "
            f"autorizados: {', '.join(str(a) for a in autorizados)}"
        )
    return rede


def cmd_network(cfg: dict, args) -> int:
    """Descoberta de hosts (ping sweep) na rede autorizada. nmap -sn."""
    cidr = args.cidr or _cidrs_autorizados()[0]
    _validar_alvo(cidr)
    print(f"[scope] varredura de descoberta em {cidr} (autorizado)")
    # -sn: so descoberta, sem port scan. -T4 ritmo de LAN domestica.
    cmd = f"nmap -sn -T4 {shlex.quote(cidr)}"
    r = ssh_exec(cfg, cmd, timeout=600)
    saida = r.stdout.strip() or r.stderr.strip()
    print(saida)
    _log("network", saida)
    return r.returncode


def cmd_audit(cfg: dict, args) -> int:
    """Inventario de servicos na rede autorizada. nmap -sT -sV (sem root)."""
    cidr = args.cidr or _cidrs_autorizados()[0]
    _validar_alvo(cidr)
    print(f"[scope] auditoria de servicos em {cidr} (autorizado)")
    carimbo = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    remoto_xml = f"/tmp/audit-{carimbo}.xml"
    # -sT connect scan (nao precisa CAP_NET_RAW). -sV versao. --top-ports foco.
    cmd = (
        f"nmap -sT -sV -O --osscan-guess --top-ports 200 -T4 "
        f"-oX {remoto_xml} {shlex.quote(cidr)} 2>&1; "
        f"echo '=== RESUMO ==='; "
        f"nmap -sT -sV --top-ports 200 -T4 {shlex.quote(cidr)}"
    )
    r = ssh_exec(cfg, cmd, timeout=1800)
    saida = r.stdout.strip() or r.stderr.strip()
    log = _log("audit", saida)
    print(saida)
    print(f"\nlog local: {log}")
    print(f"xml remoto: {remoto_xml} (puxe com: python mobile_kali.py run "
          f"\"cat {remoto_xml}\" > reports/audit.xml)")
    return r.returncode


def cmd_device(cfg: dict, args) -> int:
    """Perfil fundo de UM dispositivo autorizado: portas, servicos, superficie.

    Alvo = um IP (ou /32) dentro de config/targets.txt. Marca os vetores comuns
    em TV/IoT/celular: ADB-over-TCP, UPnP, logins de rede. Scan connect (-sT),
    sem root. NSE 'default,safe,vuln' (nao-intrusivo).
    """
    if not args.ip:
        print("uso: python mobile_kali.py device <IP>", file=sys.stderr)
        return 2
    _validar_alvo(args.ip)   # recusa IP fora de RFC1918 / fora da lista
    print(f"[scope] perfil de {args.ip} (autorizado)")
    alvo = shlex.quote(args.ip)
    cmd = (
        f"echo '## PORTAS/SERVICOS'; "
        f"nmap -sT -sV -p- --open -T4 {alvo}; "
        f"echo '## NSE default+safe+vuln'; "
        f"nmap -sT -sV -T4 --script 'default,safe,vuln' {alvo}; "
        f"echo '## FINGERPRINT'; "
        f"nmap -sT -O --osscan-guess -T4 {alvo} 2>/dev/null | sed -n '/Running\\|OS CPE\\|MAC\\|Device type/p'"
    )
    r = ssh_exec(cfg, cmd, timeout=1800)
    saida = r.stdout.strip() or r.stderr.strip()
    print(saida)
    # dica de superficie: aponta vetores classicos encontrados
    dicas = []
    if "5555/tcp" in saida:
        dicas.append("5555 ADB-over-TCP aberto -> adb connect %s:5555 (sem brute)" % args.ip)
    for porta, rot in (("22/tcp", "SSH"), ("23/tcp", "Telnet"), ("80/tcp", "web"),
                       ("443/tcp", "web TLS"), ("1900/tcp", "UPnP/SSDP"),
                       ("8008/tcp", "Chromecast"), ("8009/tcp", "Chromecast TLS"),
                       ("445/tcp", "SMB"), ("3389/tcp", "RDP")):
        if porta in saida:
            dicas.append(f"{porta} {rot}")
    if dicas:
        print("\n## SUPERFICIE\n- " + "\n- ".join(dicas))
    else:
        print("\n## SUPERFICIE\n- nenhuma porta comum aberta: alvo expoe pouco "
              "(normal em celular moderno). Nada a forcar sem login de rede.")
    _log(f"device-{args.ip.replace('/', '_')}", saida)
    return r.returncode


def cmd_crack(cfg: dict, args) -> int:
    """Crack de hash OFFLINE no Kali remoto. Nao usa rede, nao tem alvo.

    Trabalha sobre um arquivo de hashes que VOCE ja possui legitimamente
    (ex.: dump do seu proprio lab). john com rockyou por padrao; --hashcat usa
    hashcat modo CPU. Prepara rockyou se estiver .gz.
    """
    if not args.arquivo:
        print("uso: python mobile_kali.py crack <arquivo_remoto_de_hashes> "
              "[--hashcat] [--mode <num>]", file=sys.stderr)
        return 2
    alvo = shlex.quote(args.arquivo)
    prep = ("ls /usr/share/wordlists/rockyou.txt >/dev/null 2>&1 || "
            "gunzip -kf /usr/share/wordlists/rockyou.txt.gz 2>/dev/null || true")
    if args.hashcat:
        modo = str(args.mode) if args.mode is not None else "0"  # 0 = MD5; ajuste por hash
        cmd = (f"{prep}; hashcat -m {modo} -a 0 --quiet {alvo} "
               f"/usr/share/wordlists/rockyou.txt; "
               f"hashcat -m {modo} --show {alvo} /usr/share/wordlists/rockyou.txt")
    else:
        cmd = (f"{prep}; john --wordlist=/usr/share/wordlists/rockyou.txt {alvo}; "
               f"john --show {alvo}")
    r = ssh_exec(cfg, cmd, timeout=3600)
    saida = r.stdout.strip() or r.stderr.strip()
    print(saida)
    _log("crack", saida)
    return r.returncode


def cmd_report(cfg: dict, _args) -> int:
    """Consolida os ultimos logs num relatorio markdown em reports/."""
    REPORTS.mkdir(exist_ok=True)
    carimbo = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = REPORTS / f"relatorio-{carimbo}.md"
    partes = [f"# Relatorio MOBILE KALI AGENT\n\n_Gerado: {carimbo}_\n"]

    st = ssh_exec(cfg, "uname -a; nproc; free -h | awk 'NR==2'")
    partes.append("## Host remoto\n\n```\n" + (st.stdout.strip() or "indisponivel") + "\n```\n")

    logs = sorted(LOGS.glob("*.log"))[-10:]
    if logs:
        partes.append("## Operacoes recentes\n")
        for lg in logs:
            partes.append(f"### {lg.name}\n\n```\n{lg.read_text(encoding='utf-8')[:4000]}\n```\n")
    else:
        partes.append("_Sem logs ainda. Rode status/network/audit primeiro._\n")

    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"relatorio: {destino}")
    return 0


def _dica_falha(cfg: dict) -> None:
    print("\n--- diagnostico ---", file=sys.stderr)
    print(f"alvo: {cfg['user']}@{cfg['host']}:{cfg['port']}", file=sys.stderr)
    print("1. celular ligado, Termux aberto, sshd no ar (comando `sshd` no Termux)?",
          file=sys.stderr)
    print("2. Tailscale UP nos dois lados? teste: tailscale status", file=sys.stderr)
    print("3. chave publica em ~/.ssh/authorized_keys no celular?", file=sys.stderr)
    print("4. teste manual: ssh -p %s %s@%s" % (cfg["port"], cfg["user"], cfg["host"]),
          file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mobile_kali.py", description="Agente SSH do Kali no Moto G35.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("connect", help="prova a conexao e identifica o sistema")
    sub.add_parser("status", help="arquitetura, CPU, RAM, disco")
    tp = sub.add_parser("tools", help="estado das ferramentas")
    tp.add_argument("--install", action="store_true", help="instala as que faltam")
    rp = sub.add_parser("run", help="executa um comando remoto")
    rp.add_argument("comando", nargs="?", help="comando a rodar no Kali")
    rp.add_argument("--timeout", type=int, default=120)
    npp = sub.add_parser("network", help="ping sweep na rede autorizada")
    npp.add_argument("--cidr", help="sobrescreve o CIDR (precisa estar autorizado)")
    ap = sub.add_parser("audit", help="inventario de servicos na rede autorizada")
    ap.add_argument("--cidr", help="sobrescreve o CIDR (precisa estar autorizado)")
    dp = sub.add_parser("device", help="perfil fundo de UM dispositivo autorizado")
    dp.add_argument("ip", nargs="?", help="IP do dispositivo (dentro de targets.txt)")
    cp = sub.add_parser("crack", help="crack de hash offline (sem rede)")
    cp.add_argument("arquivo", nargs="?", help="arquivo remoto de hashes")
    cp.add_argument("--hashcat", action="store_true", help="usa hashcat (CPU) no lugar de john")
    cp.add_argument("--mode", type=int, help="modo -m do hashcat (tipo de hash)")
    sub.add_parser("report", help="consolida logs num markdown")

    args = p.parse_args(argv)

    try:
        cfg = carregar_config()
    except ErroConfig as e:
        print(f"[config] {e}", file=sys.stderr)
        return 3

    despacho = {
        "connect": cmd_connect, "status": cmd_status, "tools": cmd_tools,
        "run": cmd_run, "network": cmd_network, "audit": cmd_audit,
        "device": cmd_device, "crack": cmd_crack, "report": cmd_report,
    }
    try:
        return despacho[args.cmd](cfg, args)
    except ErroConfig as e:
        print(f"[scope] {e}", file=sys.stderr)
        return 4
    except subprocess.TimeoutExpired:
        print("[timeout] o comando remoto estourou o tempo.", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
