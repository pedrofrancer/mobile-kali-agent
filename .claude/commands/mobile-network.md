---
description: Descoberta de hosts (ping sweep) na rede domestica autorizada
---
Rode `python mobile_kali.py network` (ou `--cidr <faixa>` dentro de targets.txt).
O comando recusa alvo fora de RFC1918 ou fora de config/targets.txt. Liste os
hosts vivos encontrados. Nunca aponte para rede que nao seja a autorizada.
