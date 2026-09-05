import json
import subprocess

resultado = subprocess.run(["ip" , "-j" , "addr"], capture_output=True, text=True)
interfaces = json.loads(resultado.stdout)

lista_resultado = []

for interfaz in interfaces:
    for direccion in interfaz["addr_info"]:
        if direccion["family"] == "inet":
            lista_resultado.append({
                "interfas": interfaz["ifname"],
                "ip": direccion["local"],
                "cidr": direccion["prefixlen"]
            })

print(lista_resultado)