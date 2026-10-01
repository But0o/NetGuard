import json
import os


def leer_inventario(ruta):
    """Lee un archivo de inventario JSON y devuelve su contenido
    como lista de hosts.

    Fase 6 — Monitoring.
    """
    with open(ruta, "r") as archivo:
        datos = json.load(archivo)

    return datos


def listar_inventarios(carpeta_logs):
    """Devuelve las rutas completas de todos los archivos de inventario
    dentro de una carpeta de logs.
    """
    archivos = os.listdir(carpeta_logs)

    rutas_completas = []
    for nombre_archivo in archivos:
        rutas_completas.append(os.path.join(carpeta_logs, nombre_archivo))

    return rutas_completas


def buscar_host(ip, inventario):
    """Busca el diccionario completo de un host por IP dentro de un
    inventario (lista de hosts). Devuelve None si no se encuentra.

    Fase 6 — Monitoring.
    """
    host_encontrado = None

    for encontrado in inventario:
        if encontrado["ip"] == ip:
            host_encontrado = encontrado

    return host_encontrado


def buscar_puerto(numero_puerto, lista_puerto):
    """Busca el diccionario de un puerto especifico por numero, dentro
    de la lista de puertos de un host. Devuelve None si no se encuentra.

    Fase 6 — Monitoring.
    """
    puerto_encontrado = None

    for encontrado in lista_puerto:
        if encontrado["puerto"] == numero_puerto:
            puerto_encontrado = encontrado

    return puerto_encontrado