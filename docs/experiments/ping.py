import json
import subprocess
import re
import ipaddress
import time
import socket
from concurrent.futures import ThreadPoolExecutor
from functools import partial


def obtener_interfaces():
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


def hacer_ping(ip, timeout=1):
    resultado = subprocess.run(
        ["ping", "-c", "4", "-W", str(timeout), ip],
        capture_output=True,
        text=True
    )

    if resultado.returncode != 0:
        return {"ip": ip, "activo": False}

    texto = resultado.stdout
    ttl = re.search(r"ttl=(\d+)", texto)
    tiempo = re.search(r"rtt min/avg/max/mdev = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)", texto)
    perdida = re.search(r"(\d+)% packet loss", texto)

    return {
        "ip": ip,
        "activo": True,
        "ttl": int(ttl.group(1)),
        "tiempo_ms": float(tiempo.group(2)),
        "perdida": float(perdida.group(1))
    }

patrones = {
    "A": r"\bA\b[ \t]+(\d+\.\d+\.\d+\.\d+)",
    "AAAA": r"\bAAAA\b[ \t]+(\S+)",
    "MX": r"\bMX\b[ \t]+\d+[ \t]+(\S+)",
    "NS": r"\bNS\b[ \t]+(\S+)",
    "CNAME": r"\bCNAME\b[ \t]+(\S+)",
    "TXT": r"\bTXT\b[ \t]+\"(.+)\""
}

def consultar_dns(dominio, tipo ="A"):
    patrones_elegidos = patrones.get(tipo, "None")

    if patrones_elegidos == None:
        return {"dominio": dominio, "ip": None, "error": "Tipo de registro no soportado"}

    resultado = subprocess.run(
        ["dig", dominio, tipo],
        capture_output=True,
        text=True
    )

    texto = resultado.stdout
    ip_encontrada = re.search(patrones_elegidos, texto)

    if ip_encontrada == None:
        return {"dominio": dominio, "ip": None}

    else:
        return {
            "dominio": dominio,
            "ip": ip_encontrada.group(1)
        }


servicios = {80: "HTTP", 443: "HTTPS", 22: "SSH", 21: "FTP", 23: "Telnet"}

def reverse_dns(ip):
    resultado = subprocess.run(["dig", "-x", ip], capture_output=True, text=True)
    texto = resultado.stdout
    nombre_encontrado = re.search(r"\bPTR\b[ \t]+(\S+)", texto)

    if nombre_encontrado == None:
        return {"ip": ip, "dominio": None}
    else:
        return{
            "ip": ip,
            "dominio": nombre_encontrado.group(1)
        }

def escanear_puerto(ip, puerto, timeout=1):
    nombre_servicio = servicios.get(puerto,"Desconocido")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)

    try:
        resultado = s.connect_ex((ip, puerto))
        s.close()

        if resultado == 0:
            return {"ip": ip, "puerto": puerto, "estado": "Abierto", "codigo": resultado, "servicio": nombre_servicio}
        else:
            return {"ip": ip, "puerto": puerto, "estado": "Cerrado", "codigo": resultado, "servicio": nombre_servicio}

    except socket.timeout:
        s.close()
        return {"ip": ip, "puerto": puerto, "estado": "No Determinado", "codigo": None, "servicio": nombre_servicio}


def escanear_host(ip, puertos=None):
    if puertos is None:
        puertos = [80, 443, 22, 21, 23]

    resultado_ping = hacer_ping(ip)

    if resultado_ping["activo"] == False:
        return {"ip": ip, "activo": False, "puertos": []}

    puertos_distintos = partial(escanear_puerto, ip, timeout=1)

    with ThreadPoolExecutor(max_workers=5) as pool:
        resultados_puertos = list(pool.map(puertos_distintos, puertos))

    return {"ip": ip, "activo": True, "puertos": resultados_puertos}

# --- Auto-detección de la propia red (sin hardcodear IP) ---

interfaces = obtener_interfaces()

interfaz_encontrada = None

for interfaz in interfaces:
    if interfaz["interfas"] != "lo":
        interfaz_encontrada = interfaz

red = ipaddress.ip_network(interfaz_encontrada["red"])

print(f"Red detectada automáticamente: {red}")


# --- Escaneo de red completo, usando la red auto-detectada ---

lista_ip = []
for host in red.hosts():
    ip_texto = str(host)
    lista_ip.append(ip_texto)

timeout_ping = partial(hacer_ping, timeout=1)

inicio = time.time()
with ThreadPoolExecutor(max_workers=60) as pool:
    resultados = list(pool.map(timeout_ping, lista_ip))
fin = time.time()

for activos in resultados:
    if activos["activo"] == True:
        print(json.dumps(escanear_host(activos["ip"]), indent=4))

print(f"Tardó {fin - inicio:.2f} segundos")
# Caso 1: sin especificar tipo, debería usar "A" por defecto (mismo comportamiento de siempre)
print(consultar_dns("google.com"))

# Caso 2: especificando "A" explícitamente, debería dar el mismo resultado que el caso 1
print(consultar_dns("google.com", "A"))

# Caso 3: especificando "MX" — acá es donde vamos a confirmar el problema del regex
print(consultar_dns("google.com", "MX"))

# Caso 4: especificando "NS" — otro tipo de registro, mismo problema esperado
print(consultar_dns("google.com", "NS"))

# Caso 5: especificando "PTR" - otro tipo de registo que no esta identificado
print(consultar_dns("google.com", "PTR"))

print(reverse_dns("8.8.8.8"))          # debería darte "dns.google."
print(reverse_dns("192.168.1.1"))      # tu router de casa — probablemente no tenga PTR configurado, buen caso para probar el None