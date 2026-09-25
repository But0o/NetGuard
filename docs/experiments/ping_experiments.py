import json
import subprocess
import re
import ipaddress
import time
import socket
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from datetime import datetime
#
#
#
#timestamp = datetime.now()
#str_times_tamp = timestamp.strftime("%Y-%m-%d-%H-%M-%S")
#
#
#def obtener_interfaces():
#    resultado = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True)
#    interfaces = json.loads(resultado.stdout)
#
#    lista_resultado = []
#
#    for interfas in interfaces:
#        for direccion in interfas["addr_info"]:
#            if direccion["family"] == "inet":
#                ip_cidr = direccion["local"] + "/" + str(direccion["prefixlen"])
#                interfaz = ipaddress.ip_interface(ip_cidr)
#                lista_resultado.append({
#                    "interfas": interfas["ifname"],
#                    "ip": direccion["local"],
#                    "cidr": direccion["prefixlen"],
#                    "red": str(interfaz.network)
#                })
#
#    return lista_resultado
#
#
#def hacer_ping(ip, timeout=1):
#    resultado = subprocess.run(
#        ["ping", "-c", "4", "-W", str(timeout), ip],
#        capture_output=True,
#        text=True
#    )
#
#    if resultado.returncode != 0:
#        return {"ip": ip, "activo": False}
#
#    texto = resultado.stdout
#    ttl = re.search(r"ttl=(\d+)", texto)
#    tiempo = re.search(r"rtt min/avg/max/mdev = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)", texto)
#    perdida = re.search(r"(\d+)% packet loss", texto)
#
#    return {
#        "ip": ip,
#        "activo": True,
#        "ttl": int(ttl.group(1)),
#        "tiempo_ms": float(tiempo.group(2)),
#        "perdida": float(perdida.group(1))
#    }
#
#patrones = {
#    "A": r"\bA\b[ \t]+(\d+\.\d+\.\d+\.\d+)",
#    "AAAA": r"\bAAAA\b[ \t]+(\S+)",
#    "MX": r"\bMX\b[ \t]+\d+[ \t]+(\S+)",
#    "NS": r"\bNS\b[ \t]+(\S+)",
#    "CNAME": r"\bCNAME\b[ \t]+(\S+)",
#    "TXT": r"\bTXT\b[ \t]+\"(.+)\""
#}
#
#def consultar_dns(dominio, tipo ="A"):
#    patrones_elegidos = patrones.get(tipo, "None")
#
#    if patrones_elegidos == None:
#        return {"dominio": dominio, "ip": None, "error": "Tipo de registro no soportado"}
#
#    resultado = subprocess.run(
#        ["dig", dominio, tipo],
#        capture_output=True,
#        text=True
#    )
#
#    texto = resultado.stdout
#    ip_encontrada = re.search(patrones_elegidos, texto)
#
#    if ip_encontrada == None:
#        return {"dominio": dominio, "ip": None}
#
#    else:
#        return {
#            "dominio": dominio,
#            "ip": ip_encontrada.group(1)
#        }
#
#
#servicios = {80: "HTTP", 443: "HTTPS", 22: "SSH", 21: "FTP", 23: "Telnet"}
#
#def reverse_dns(ip):
#    resultado = subprocess.run(["dig", "-x", ip], capture_output=True, text=True)
#    texto = resultado.stdout
#    nombre_encontrado = re.search(r"\bPTR\b[ \t]+(\S+)", texto)
#
#    if nombre_encontrado == None:
#        return {"ip": ip, "dominio": None}
#    else:
#        return{
#            "ip": ip,
#            "dominio": nombre_encontrado.group(1)
#        }
#
#def escanear_puerto(ip, puerto, timeout=1):
#    nombre_servicio = servicios.get(puerto,"Desconocido")
#
#    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#    s.settimeout(timeout)
#
#    try:
#        resultado = s.connect_ex((ip, puerto))
#        s.close()
#
#        if resultado == 0:
#            return {"ip": ip, "puerto": puerto, "estado": "Abierto", "codigo": resultado, "servicio": nombre_servicio}
#        else:
#            return {"ip": ip, "puerto": puerto, "estado": "Cerrado", "codigo": resultado, "servicio": nombre_servicio}
#
#    except socket.timeout:
#        s.close()
#        return {"ip": ip, "puerto": puerto, "estado": "No Determinado", "codigo": None, "servicio": nombre_servicio}
#
#
#def escanear_host(ip, tabla_arp, puertos=None):
#    if puertos is None:
#        puertos = [80, 443, 22, 21, 23]
#
#    resultado_ping = hacer_ping(ip)
#
#    if resultado_ping["activo"] == False:
#        return {"ip": ip,"mac": None,"hostname" : None, "activo": False, "puertos": [], "timestamp": None}
#
#    puertos_distintos = partial(escanear_puerto, ip, timeout=1)
#
#    with ThreadPoolExecutor(max_workers=5) as pool:
#        resultados_puertos = list(pool.map(puertos_distintos, puertos))
#
#    mac = buscar_mac(ip, tabla_arp)
#    resultado_dns = reverse_dns(ip)
#
#    timestamp = datetime.now()
#    str_times_tamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
#
#    return {"ip": ip,"mac": mac,"hostname": resultado_dns["dominio"], "activo": True, "puertos": resultados_puertos, "timestamp": str_times_tamp}
#
#
#def obtener_tabla_arp():
#    resultado = subprocess.run(["ip", "-j", "neigh"], capture_output=True, text=True)
#    tabla_arp = json.loads(resultado.stdout)
#
#    lista_arp = []
#
#    for arp in tabla_arp:
#        lista_arp.append({"ip": arp["dst"], "mac": arp.get("lladdr", None)})
#
#    return lista_arp
#
#
#
#def buscar_mac(ip, lista_arp):
#
#    mac_encontrada = None
#
#    for entrada in lista_arp:
#        if entrada["ip"] == ip:
#            mac_encontrada = entrada["mac"]
#
#    return mac_encontrada
#
#
#
#
## --- Auto-detección de la propia red (sin hardcodear IP) ---
#
#interfaces = obtener_interfaces()
#
#interfaz_encontrada = None
#
#for interfaz in interfaces:
#    if interfaz["interfas"] != "lo":
#        interfaz_encontrada = interfaz
#
#red = ipaddress.ip_network(interfaz_encontrada["red"])
#
#print(f"Red detectada automáticamente: {red}")
#
#
## --- Escaneo de red completo, usando la red auto-detectada ---
#
#lista_ip = []
#for host in red.hosts():
#    ip_texto = str(host)
#    lista_ip.append(ip_texto)
#
#timeout_ping = partial(hacer_ping, timeout=1)
#
#inicio = time.time()
#with ThreadPoolExecutor(max_workers=60) as pool:
#    resultados = list(pool.map(timeout_ping, lista_ip))
#fin = time.time()
#
#print(f"Tardó {fin - inicio:.2f} segundos en el ping")
#
#tabla_arp = obtener_tabla_arp()
#
#inventario_completo=[]
#
#for activos in resultados:
#    if activos["activo"] == True:
#        inventario_completo.append(escanear_host(activos["ip"], tabla_arp))
#
#
#carpeta_actual = os.path.dirname(__file__)
#raiz_proyecto = os.path.dirname(os.path.dirname(carpeta_actual))
#carpeta_logs = os.path.join(raiz_proyecto, "logs")
#os.makedirs(carpeta_logs, exist_ok=True)
#nombre_archivo = os.path.join(carpeta_logs, "inventario_" + str_times_tamp + ".json") 
#
#print("A punto de guardar el archivo...")
#with open(nombre_archivo, "w") as archivo:
#    json.dump(inventario_completo, archivo, indent=4)
#    print("Archivo guardado con éxito")
#
#
#print(f"Tardó {fin - inicio:.2f} segundos")
## Caso 1: sin especificar tipo, debería usar "A" por defecto (mismo comportamiento de siempre)
#print(consultar_dns("google.com"))
#
## Caso 2: especificando "A" explícitamente, debería dar el mismo resultado que el caso 1
#print(consultar_dns("google.com", "A"))
#
## Caso 3: especificando "MX" — acá es donde vamos a confirmar el problema del regex
#print(consultar_dns("google.com", "MX"))
#
## Caso 4: especificando "NS" — otro tipo de registro, mismo problema esperado
#print(consultar_dns("google.com", "NS"))
#
## Caso 5: especificando "PTR" - otro tipo de registo que no esta identificado
#print(consultar_dns("google.com", "PTR"))
#
#print(reverse_dns("8.8.8.8"))          # debería darte "dns.google."
#print(reverse_dns("192.168.1.1"))      # tu router de casa — probablemente no tenga PTR configurado, buen caso para probar el None
#
#print(obtener_tabla_arp())
#
#
#

def leer_inventario(ruta):

    with open(ruta, "r") as archivo:
        datos = json.load(archivo)

    return datos

def buscar_host(ip, inventario):
    host_encontrado = None

    for encontrado in inventario:
        if encontrado["ip"] == ip:
            host_encontrado = encontrado

    return host_encontrado


def buscar_puerto(numero_puerto, lista_puerto):
    puerto_encontrado = None

    for encontrado in lista_puerto:
        if encontrado["puerto"] == numero_puerto:
            puerto_encontrado = encontrado

    return puerto_encontrado

inventario_viejo = leer_inventario("logs/inventario_2026-09-15-01-52-29.json")
inventario_nuevo = leer_inventario("logs/inventario_2026-09-15-02-07-28.json")


ip_buscar = "192.168.0.1"

archivos = os.listdir("logs")

rutas_completas = []

for nombre_archivo in archivos:
    rutas_completas.append(os.path.join("logs", nombre_archivo))

inventario = []

for archivo in rutas_completas:
    inventario.append(leer_inventario(archivo))

veces_activo = 0
sumar_tiempo_ms = 0
sumar_perdida = 0

for escaneo in inventario:
    resultado_busqueda = buscar_host(ip_buscar,escaneo)
    if resultado_busqueda is not None and resultado_busqueda["activo"] == True:
        veces_activo += 1
        sumar_tiempo_ms += resultado_busqueda.get("tiempo_ms", 0)
        sumar_perdida += resultado_busqueda.get("perdida", 0)

porcentaje_uptime = (veces_activo / len(inventario)) * 100
promedio_tiempo_ms = sumar_tiempo_ms / veces_activo
promedio_perdida = sumar_perdida / veces_activo


print(porcentaje_uptime)
print(promedio_tiempo_ms)
print(promedio_perdida)



ips_viejas = set([dato["ip"] for dato in inventario_viejo])
ips_nuevas = set([dato["ip"] for dato in inventario_nuevo])

ip_referencia_vieja = next(iter(ips_viejas))
octetos_viejo = ip_referencia_vieja.split(".")[:3]

ip_referencia_nueva = next(iter(ips_nuevas))
octetos_nuevo = ip_referencia_nueva.split(".")[:3]

nuevos = ips_nuevas - ips_viejas
desaparecidas = ips_viejas - ips_nuevas


if octetos_viejo == octetos_nuevo:
    print("Esta es la comparacion de la red")
    print(nuevos)
    print(desaparecidas)
else:
    print("Se reviso la red y los logs que desea comparar son en redes distintas")

ips_comunes = ips_nuevas & ips_viejas

for ip in ips_comunes:
    host_viejo = buscar_host(ip, inventario_viejo)
    host_nuevo = buscar_host(ip, inventario_nuevo)

    for puerto_viejo in host_viejo["puertos"]:
        puerto_nuevo = buscar_puerto(puerto_viejo["puerto"], host_nuevo["puertos"])

        if puerto_viejo["estado"] != puerto_nuevo["estado"]:
            print(f"Puerto {puerto_nuevo['puerto']} de {ip} cambió de {puerto_viejo['estado']} a {puerto_nuevo['estado']}")