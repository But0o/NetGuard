import json
import subprocess
import ipaddress


def obtener_interfaces():
    """Devuelve la lista de interfaces de red reales de la maquina,
    con IP, CIDR y red calculada para cada una (Fase 1)."""
    resultado = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True)
    interfaces = json.loads(resultado.stdout)

    lista_resultado = []

    for interfas in interfaces:
        for direccion in interfas["addr_info"]:
            if direccion["family"] == "inet":
                ip_cidr = direccion["local"] + "/" + str(direccion["prefixlen"])
                interfaz = ipaddress.ip_interface(ip_cidr)
                lista_resultado.append({
                    "interfas": interfas["ifname"],
                    "ip": direccion["local"],
                    "cidr": direccion["prefixlen"],
                    "red": str(interfaz.network)
                })

    return lista_resultado


def detectar_red_local():
    """Detecta automaticamente la red local real de la maquina,
    descartando la interfaz de loopback ('lo').

    Devuelve un objeto ipaddress.IPv4Network, o None si no se
    encontro ninguna interfaz real.
    """
    interfaces = obtener_interfaces()

    interfaz_encontrada = None
    for interfaz in interfaces:
        if interfaz["interfas"] != "lo":
            interfaz_encontrada = interfaz

    if interfaz_encontrada is None:
        return None

    return ipaddress.ip_network(interfaz_encontrada["red"])