# SECURITY.md — Política operacional do MOBILE KALI AGENT

Este documento é a política de segurança **executável** do projeto. Ele reúne a
seção SEGURANÇA de `config/spec-origem.txt` e a política de
`config/politica-redteam.txt`, e descreve onde cada regra vive em código.

## Escopo autorizado

Toda operação de rede é limitada a **sistemas próprios ou expressamente
autorizados**, dentro da rede doméstica declarada em `config/targets.txt`.

- Alvo fora de RFC1918 / ULA (rede não privada): **recusado**.
- Alvo fora da lista `config/targets.txt`: **recusado**.
- A recusa acontece em `mobile_kali.py:_validar_alvo`, **antes** de qualquer
  pacote sair. Não é um bloqueio artificial a ferramenta legítima; é a cláusula
  INTEGRIDADE da política do lab transformada em código.

Atacar terceiros ou redes fora do escopo não é suportado por este projeto.
Exfiltração de dado pessoal não é suportada.

## Autenticação e exposição

- SSH **somente por chave** Ed25519 (`BatchMode=yes`; senha desligada no
  `sshd_config` do Termux).
- SSH **não** exposto diretamente na internet. Acesso externo só via Tailscale
  (WireGuard, rede privada).
- Chave privada fica no cliente (PC/iPhone), nunca no celular.

## Operações destrutivas

- Operação destrutiva (sobrescrita, apagamento, flash, mudança de config de
  segurança) exige **confirmação explícita** do operador.
- `mobile_kali.py run` executa o que você mandar; a confirmação é sua
  responsabilidade no comando. Os subcomandos de scan (`network`, `audit`) são
  read-only por construção (`nmap -sn`, `-sT -sV`).

## Ferramentas e o limite de hardware

A política do lab autoriza recon, enumeração, password auditing, brute force,
análise de hash, auditoria Wi-Fi, vuln assessment e exploração controlada
**dentro do escopo autorizado**. O que o Moto G35 entrega, porém, depende de
hardware:

| Classe | Estado neste aparelho |
|---|---|
| recon / enumeração / `nmap -sT -sV` / dns / whois | funciona |
| password auditing / brute force (`hydra`), hash (`john`) | funciona (alvo autorizado) |
| vuln assessment (`nikto`, `sqlmap`, NSE) | funciona |
| exploração / pós-exploração (`metasploit`) | roda; sniff/spoof limitado |
| auditoria Wi-Fi (monitor mode, deauth), `tcpdump`, `scapy` raw, `arp-scan` | **indisponível** |

A indisponibilidade de Wi-Fi/L2 vem da ausência de `CAP_NET_RAW`, que exige
root. O bootloader deste G35 está travado por e-fuse (`lcs: 5`, `secure: true`),
sem comando de unlock. Não há setup rootless que contorne isso. Para camada 2:
adaptador Wi-Fi USB externo + PC, ou aparelho de bootloader destravável.

## Registro

Toda operação relevante grava log em `logs/` com carimbo de tempo. O subcomando
`report` consolida os logs recentes num markdown em `reports/`. Não se simula
conexão nem resultado: o que não rodou não aparece como se tivesse rodado.
