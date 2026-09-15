import os
import json


def guardar_inventario(inventario_completo, str_timestamp):
    """Guarda una lista de resultados de escaneo en logs/inventario_<timestamp>.json,
    en la raiz del proyecto, sin importar desde donde se ejecute el script.

    Fase 5 — Network Inventory.
    """
    carpeta_actual = os.path.dirname(__file__)
    raiz_proyecto = os.path.dirname(os.path.dirname(carpeta_actual))
    carpeta_logs = os.path.join(raiz_proyecto, "logs")

    os.makedirs(carpeta_logs, exist_ok=True)

    nombre_archivo = os.path.join(carpeta_logs, "inventario_" + str_timestamp + ".json")

    with open(nombre_archivo, "w") as archivo:
        json.dump(inventario_completo, archivo, indent=4)

    return nombre_archivo