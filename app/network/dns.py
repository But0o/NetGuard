import subprocess
import re

# Patrones regex por tipo de registro DNS (Fase 4).
# \b evita coincidencias parciales dentro de otras palabras (ej. "NS" dentro de "ANSWER").
# [ \t]+ evita que el patron cruce saltos de linea (a diferencia de \s+).
patrones = {
    "A": r"\bA\b[ \t]+(\d+\.\d+\.\d+\.\d+)",
    "AAAA": r"\bAAAA\b[ \t]+(\S+)",
    "MX": r"\bMX\b[ \t]+\d+[ \t]+(\S+)",
    "NS": r"\bNS\b[ \t]+(\S+)",
    "CNAME": r"\bCNAME\b[ \t]+(\S+)",
    "TXT": r"\bTXT\b[ \t]+\"(.+)\""
}


def consultar_dns(dominio, tipo="A"):
    """Consulta un registro DNS de un dominio usando dig.
    tipo puede ser "A", "AAAA", "MX", "NS", "CNAME" o "TXT".
    """
    patron_elegido = patrones.get(tipo, None)

    if patron_elegido is None:
        return {"dominio": dominio, "ip": None, "error": "Tipo de registro no soportado"}

    resultado = subprocess.run(
        ["dig", dominio, tipo],
        capture_output=True,
        text=True
    )

    texto = resultado.stdout
    ip_encontrada = re.search(patron_elegido, texto)

    if ip_encontrada is None:
        return {"dominio": dominio, "ip": None}

    return {"dominio": dominio, "ip": ip_encontrada.group(1)}


def reverse_dns(ip):
    """Consulta el nombre (PTR) asociado a una IP, usando dig -x."""
    resultado = subprocess.run(["dig", "-x", ip], capture_output=True, text=True)
    texto = resultado.stdout
    nombre_encontrado = re.search(r"\bPTR\b[ \t]+(\S+)", texto)

    if nombre_encontrado is None:
        return {"ip": ip, "dominio": None}

    return {"ip": ip, "dominio": nombre_encontrado.group(1)}