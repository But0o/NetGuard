import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from datetime import datetime

# Agrega la raiz del proyecto a sys.path, para poder hacer "from app...."
# sin importar desde donde se ejecute este script (mismo problema que
# resolvimos con __file__ en app/core/inventory.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.network.interfaces import detectar_red_local
from app.network.ping import hacer_ping
from app.network.arp import obtener_tabla_arp
from app.scanner.host_scanner import escanear_host
from app.core.inventory import guardar_inventario


def main():
    timestamp_inicio = datetime.now()
    str_timestamp = timestamp_inicio.strftime("%Y-%m-%d-%H-%M-%S")

    red = detectar_red_local()
    if red is None:
        print("No se pudo detectar ninguna interfaz de red real.")
        return

    print(f"Red detectada automáticamente: {red}")

    lista_ip = []
    for host in red.hosts():
        lista_ip.append(str(host))

    timeout_ping = partial(hacer_ping, timeout=1)

    inicio = time.time()
    with ThreadPoolExecutor(max_workers=30) as pool:
        resultados = list(pool.map(timeout_ping, lista_ip))
    fin = time.time()

    print(f"Ping completo: {fin - inicio:.2f} segundos")

    tabla_arp = obtener_tabla_arp()

    inventario_completo = []
    for activo in resultados:
        if activo["activo"] == True:
            inventario_completo.append(escanear_host(activo["ip"], tabla_arp))

    nombre_archivo = guardar_inventario(inventario_completo, str_timestamp)
    print(f"Inventario guardado en: {nombre_archivo}")


if __name__ == "__main__":
    main()