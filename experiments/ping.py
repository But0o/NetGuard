import subprocess
import re

def hacer_ping(ip):
    resultado = subprocess.run(
        ["ping", "-c", "1", ip],
        capture_output=True,
        text=True
    )

    if resultado.returncode != 0:
        return {"ip": ip, "activo": False}

    texto = resultado.stdout
    ttl = re.search(r"ttl=(\d+)", texto)
    tiempo = re.search(r"tiempo=(\d+\.\d+)", texto)

    return {
        "ip": ip,
        "activo": True,
        "ttl": int(ttl.group(1)),
        "tiempo_ms": float(tiempo.group(1))
    }

print(hacer_ping("192.168.1.100"))