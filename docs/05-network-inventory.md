# Fase 5 — Network Inventory

Conceptos de networking aprendidos y aplicados en esta fase del proyecto NetGuard.

---

## Motivación

Hasta Fase 4, todas las funciones son "puras": consultan la red y devuelven un resultado, pero nada persiste entre ejecuciones — cada corrida del script empieza de cero, sin memoria de escaneos anteriores. Network Inventory introduce la idea de **guardar** lo descubierto (dispositivos, IP, MAC, hostname, puertos, servicios, timestamp), sentando la base necesaria para el monitoreo a lo largo del tiempo (Fase 6).

Datos objetivo, según el roadmap: IP, hostname, MAC (cuando sea posible), puertos, servicios, timestamps — guardados inicialmente en JSON.

---

## MAC Address y ARP

### El problema: `ip -j addr` no sirve para esto

`ip -j addr` (usado en Fase 1) muestra la MAC de las **interfaces propias** de la máquina — no tiene forma de reportar la MAC de otros dispositivos de la red, porque esa información no vive en la configuración local.

### ARP (Address Resolution Protocol)

Dentro de una misma red local, la entrega final de un paquete no se hace por IP — se hace por **MAC** (dirección de la capa de enlace). ARP es el protocolo que resuelve "tengo la IP de un dispositivo en mi red local, ¿cuál es su MAC?" — es, en cierto sentido, el equivalente de DNS pero para la capa de enlace, y solo funciona dentro de la misma red local (no a través de routers/internet).

Cada vez que se le hace ping (o cualquier otra comunicación) a un dispositivo de la red local, el sistema operativo resuelve su MAC vía ARP automáticamente, sin intervención del usuario, y guarda el resultado en una tabla local (técnicamente llamada "tabla de vecinos" en la terminología moderna de `ip`, aunque el concepto es el mismo que ARP tradicional).

### Consultando la tabla con `ip -j neigh`

```bash
ip -j neigh
```

```json
{
  "dst": "192.168.100.1",
  "dev": "wlan0",
  "lladdr": "88:66:39:9b:69:5f",
  "state": ["REACHABLE"]
}
```

- `dst`: IP del dispositivo.
- `dev`: interfaz por la que se llega a ese dispositivo.
- `lladdr`: la MAC address ("link-layer address").
- `state`: estado de la entrada — `REACHABLE` (confirmada recientemente), `STALE` (más vieja, podría no ser exacta), y otros estados como `FAILED`/`INCOMPLETE` cuando la resolución no se completó (en cuyo caso el campo `lladdr` puede no existir en el JSON).

La tabla solo contiene entradas para dispositivos con los que la máquina **ya se comunicó recientemente** — no es un descubrimiento activo por sí sola, sino un registro de comunicaciones pasadas. Por eso, para poblarla bien, conviene consultarla **después** de un escaneo de red completo (que ya generó tráfico ARP hacia todos los hosts), no antes.

Una misma MAC puede aparecer asociada a más de una IP (una IPv4 y una IPv6 link-local del mismo dispositivo, por ejemplo) — coherente con lo ya visto en Fase 1 sobre múltiples direcciones por interfaz.

---

## Implementación

### `obtener_tabla_arp()`

```python
def obtener_tabla_arp():
    resultado = subprocess.run(["ip", "-j", "neigh"], capture_output=True, text=True)
    tabla_arp = json.loads(resultado.stdout)

    lista_arp = []

    for arp in tabla_arp:
        lista_arp.append({"ip": arp["dst"], "mac": arp.get("lladdr", None)})

    return lista_arp
```

### Bug encontrado: `KeyError: 'lladdr'`

No todas las entradas de `ip -j neigh` tienen el campo `lladdr` — las entradas en estado `FAILED` o `INCOMPLETE` (resolución ARP intentada pero no completada, ej. un dispositivo que dejó de responder a mitad del escaneo) directamente omiten el campo, en vez de incluirlo con un valor nulo.

**Solución**: usar `arp.get("lladdr", None)` en vez de acceso directo `arp["lladdr"]` — mismo patrón ya usado en Fase 3 con `servicios.get(puerto, "Desconocido")`. Es un recordatorio de que no se puede asumir que todos los diccionarios de una lista real, generada por un sistema externo con estados variables, tengan siempre las mismas claves.

### `buscar_mac()`: buscar la MAC de una IP puntual dentro de la tabla ya obtenida

```python
def buscar_mac(ip, lista_arp):
    mac_encontrada = None

    for entrada in lista_arp:
        if entrada["ip"] == ip:
            mac_encontrada = entrada["mac"]

    return mac_encontrada
```

Devuelve `None` si la IP no está en la tabla (dispositivo del que nunca se obtuvo respuesta ARP).

### Decisión de eficiencia: obtener la tabla ARP una sola vez

`obtener_tabla_arp()` ejecuta un `subprocess.run()` completo — llamarla una vez por cada host escaneado (por ejemplo, 254 veces en una red `/24`) sería un desperdicio de recursos y tiempo. Se decidió obtenerla **una sola vez**, fuera del loop de hosts, y pasarla como parámetro a las funciones que la necesitan (mismo criterio de eficiencia ya aplicado con `ThreadPoolExecutor` en Fase 2 y 3).

### `escanear_host()` actualizada con MAC

```python
def escanear_host(ip, tabla_arp, puertos=None):
    if puertos is None:
        puertos = [80, 443, 22, 21, 23]

    resultado_ping = hacer_ping(ip)

    if resultado_ping["activo"] == False:
        return {"ip": ip, "mac": None, "activo": False, "puertos": []}

    puertos_distintos = partial(escanear_puerto, ip, timeout=1)

    with ThreadPoolExecutor(max_workers=5) as pool:
        resultados_puertos = list(pool.map(puertos_distintos, puertos))

    mac = buscar_mac(ip, tabla_arp)

    return {"ip": ip, "mac": mac, "activo": True, "puertos": resultados_puertos}
```

Ambas ramas (`activo: True` / `activo: False`) incluyen la clave `"mac"`, manteniendo la misma "forma" de diccionario en ambos casos — mismo criterio de consistencia ya aplicado en `escanear_puerto()`.

### Integración en el pipeline completo

```python
tabla_arp = obtener_tabla_arp()

for activos in resultados:
    if activos["activo"] == True:
        print(json.dumps(escanear_host(activos["ip"], tabla_arp), indent=4))
```

`obtener_tabla_arp()` se llama **después** del bloque de ping concurrente a todos los hosts — para ese momento, la tabla ARP ya está bien poblada porque el escaneo previo generó tráfico ARP hacia todos los dispositivos de la red.

### Prueba realizada

```json
{
    "ip": "192.168.100.132",
    "mac": "68:24:99:4d:a1:9f",
    "activo": true,
    "puertos": [...]
}
```

Funcionando de punta a punta: IP, MAC, estado de actividad y puertos con sus servicios, todo en un solo resultado por host.

---

## Dudas / pendientes

- **Pendiente**: agregar hostname al resultado, usando `reverse_dns()` (ya implementada en Fase 4) — falta integrarla a `escanear_host()`.
- **Pendiente**: agregar timestamp a cada resultado, marcando el momento del escaneo.
- **Pendiente**: implementar el guardado de resultados en archivos JSON (persistencia real entre ejecuciones) — el objetivo central de esta fase, todavía no resuelto.
- **Pendiente**: decidir la estructura del archivo JSON de inventario (¿un archivo por escaneo con timestamp en el nombre? ¿un único archivo que se actualiza? ¿histórico acumulativo?) — a definir antes de implementar el guardado.