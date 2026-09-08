import json
import subprocess
import ipaddress

resultado = subprocess.run(["ip" , "-j" , "addr"], capture_output=True, text=True)
interfaces = json.loads(resultado.stdout)

lista_resultado = []

for interfas in interfaces:
    for direccion in interfas["addr_info"]:
        if direccion["family"] == "inet":
            ip_cidr = direccion["local"] + "/" + str(direccion["prefixlen"])
            interfaz = ipaddress.ip_interface(ip_cidr)
            lista_resultado.append({
                "interfas": interfas["ifname"],
                "ip": direccion["local"],
                "cidr": direccion["prefixlen"],
                "red" : str(interfaz.network)
            })

print(lista_resultado)