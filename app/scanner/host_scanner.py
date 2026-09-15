from concurrent.futures import ThreadPoolExecutor
from functools import partial
from datetime import datetime

from app.network.ping import hacer_ping
from app.network.arp import buscar_mac
from app.network.dns import reverse_dns
from app.scanner.port_scanner import escanear_puerto

PUERTOS_COMUNES = [80, 443, 22, 21, 23]


def escanear_host(ip, tabla_arp, puertos=None):
    """Escaneo completo de un host: ping, puertos comunes (concurrente),
    MAC (via tabla ARP ya obtenida) y hostname (reverse DNS).

    Fase 5 — Network Inventory.
    """
    if puertos is None:
        puertos = PUERTOS_COMUNES

    resultado_ping = hacer_ping(ip)

    if resultado_ping["activo"] == False:
        return {"ip": ip, "mac": None, "hostname": None, "activo": False, "puertos": [], "timestamp": None}

    puertos_distintos = partial(escanear_puerto, ip, timeout=1)

    with ThreadPoolExecutor(max_workers=5) as pool:
        resultados_puertos = list(pool.map(puertos_distintos, puertos))

    mac = buscar_mac(ip, tabla_arp)
    resultado_dns = reverse_dns(ip)

    timestamp = datetime.now()
    str_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    return {
        "ip": ip,
        "mac": mac,
        "hostname": resultado_dns["dominio"],
        "activo": True,
        "puertos": resultados_puertos,
        "timestamp": str_timestamp
    }