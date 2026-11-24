---
description: Inventario de servicos (nmap -sT -sV) na rede autorizada
---
Rode `python mobile_kali.py audit` (ou `--cidr <faixa>` autorizada). Resuma
servicos, portas e versoes por host. Scan connect (-sT), sem root. Escopo
travado em config/targets.txt. Para password auditing contra um host do lab,
use `run` com hydra/john apontando SO para IP dentro do escopo.
