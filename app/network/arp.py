import subprocess
import json


def obtener_tabla_arp():
    """Lee la tabla ARP actual del sistema (ip -j neigh) y devuelve
    una lista simplificada de {ip, mac} para cada entrada conocida.

    Fase 5 — Network Inventory.
    """
    resultado = subprocess.run(["ip", "-j", "neigh"], capture_output=True, text=True)
    tabla_arp = json.loads(resultado.stdout)

    lista_arp = []

    for arp in tabla_arp:
        lista_arp.append({"ip": arp["dst"], "mac": arp.get("lladdr", None)})

    return lista_arp


def buscar_mac(ip, lista_arp):
    """Busca la MAC asociada a una IP dentro de una tabla ARP ya obtenida.
    Devuelve None si no se encuentra ninguna entrada para esa IP.
    """
    mac_encontrada = None

    for entrada in lista_arp:
        if entrada["ip"] == ip:
            mac_encontrada = entrada["mac"]

    return mac_encontrada