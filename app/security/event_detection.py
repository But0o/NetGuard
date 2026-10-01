from datetime import datetime

from app.core.inventory_tools import buscar_host, buscar_puerto

# Puertos considerados sensibles: protocolos viejos e inseguros
# (sin cifrado), que por convencion suelen estar cerrados o filtrados
# por defecto en equipos modernos. Que aparezcan abiertos de repente
# es una senal mas fuerte que un puerto comun (ej. 443, HTTPS).
PUERTOS_SENSIBLES = {21, 23}


def detectar_eventos_seguridad(ips_comunes, inventario_viejo, inventario_nuevo):
    """Compara dos inventarios y detecta puertos que pasaron de
    Cerrado a Abierto, clasificando la severidad segun si el puerto
    es sensible (PUERTOS_SENSIBLES) o no.

    Fase 7 — Network Security.
    """
    casos_alerta = []

    for ip in ips_comunes:
        host_viejo = buscar_host(ip, inventario_viejo)
        host_nuevo = buscar_host(ip, inventario_nuevo)

        for puerto_viejo in host_viejo["puertos"]:
            puerto_nuevo = buscar_puerto(puerto_viejo["puerto"], host_nuevo["puertos"])

            if puerto_viejo["estado"] == "Cerrado" and puerto_nuevo["estado"] == "Abierto":
                timestamp = datetime.now()
                str_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")

                if puerto_nuevo["puerto"] in PUERTOS_SENSIBLES:
                    print(f"🔴 ALERTA CRÍTICA: puerto sensible {puerto_nuevo['puerto']} se abrió en {ip}")
                    casos_alerta.append({
                        "ip": ip,
                        "tipo_alerta": "Critica",
                        "puerto": puerto_nuevo["puerto"],
                        "timestamp": str_timestamp
                    })
                else:
                    print(f"🟡 Alerta: puerto {puerto_nuevo['puerto']} se abrió en {ip}")
                    casos_alerta.append({
                        "ip": ip,
                        "tipo_alerta": "Normal",
                        "puerto": puerto_nuevo["puerto"],
                        "timestamp": str_timestamp
                    })

    return casos_alerta