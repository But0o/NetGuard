import subprocess
import re
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import time

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
        "perdida" : float(perdida.group(1))
    }

red = ipaddress.ip_network("10.255.144.0/21")

lista_ip = []

for host in red.hosts():
    ip_texto = str(host)
    lista_ip.append(ip_texto)

timeout_ping = partial(hacer_ping, timeout=1)

inicio = time.time()

with ThreadPoolExecutor(max_workers=30) as pool:
    resultados = list(pool.map(timeout_ping, lista_ip))

fin = time.time()

for activos in resultados:
    if activos["activo"] == True:
        print(activos)

print(f"Tardó {fin - inicio:.2f} segundos")