import subprocess
import re
import ipaddress

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

red = ipaddress.ip_network("192.168.1.0/28")

for host in red.hosts():
    ip_texto = str(host)
    resultado_ping = hacer_ping(ip_texto)
    
    if resultado_ping["activo"] == True:
        print(resultado_ping)
