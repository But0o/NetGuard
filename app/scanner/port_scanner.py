import socket

# Mapeo puerto -> nombre de servicio, por convencion (well-known ports).
servicios = {80: "HTTP", 443: "HTTPS", 22: "SSH", 21: "FTP", 23: "Telnet"}


def escanear_puerto(ip, puerto, timeout=1):
    """Intenta una conexion TCP a un puerto especifico (Fase 3).

    Devuelve estado "Abierto" (SYN-ACK), "Cerrado" (RST) o
    "No Determinado" (timeout, sin respuesta).
    """
    nombre_servicio = servicios.get(puerto, "Desconocido")

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