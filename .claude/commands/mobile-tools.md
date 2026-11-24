---
description: Estado das ferramentas do lab no Kali; instala as que faltam
---
Rode `python mobile_kali.py tools` para o estado. Se o usuario pedir instalacao,
rode `python mobile_kali.py tools --install`. Lembre o limite: scapy/tcpdump/
arp-scan/tshark precisam de CAP_NET_RAW (root) e nao capturam L2 neste aparelho.
