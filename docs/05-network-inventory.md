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

## Hostname (reverse DNS integrado)

Se integró `reverse_dns()` (ya implementada en Fase 4) dentro de `escanear_host()`. La función devuelve el diccionario completo `{"ip": ..., "dominio": ...}` — hay que extraer específicamente `resultado_dns["dominio"]` para guardar solo el nombre, no el diccionario anidado completo.

## Timestamp

Se usa el módulo `datetime` para marcar el momento de cada escaneo:

```python
from datetime import datetime

ahora = datetime.now()
ahora.strftime("%Y-%m-%d %H:%M:%S")  # → "2026-09-15 00:48:35"
```

`datetime.now()` da un objeto con microsegundos; `.strftime(...)` lo convierte a un string legible con el formato deseado (`%Y` año, `%m` mes, `%d` día, `%H` hora, `%M` minutos, `%S` segundos).

**Decisión de ubicación — timestamp por host**: se calcula al **final** de `escanear_host()` (no al principio), ya que la diferencia entre el momento del ping y el momento en que termina todo el procesamiento del host (puertos, ARP, DNS) es de pocos segundos, irrelevante para el propósito de inventario.

**Decisión de ubicación — timestamp del escaneo completo (nombre de archivo)**: se calcula al **principio** de todo el pipeline (antes de detectar la red), ya que representa "cuándo arrancó esta foto de la red" — el dato más relevante para ordenar y comparar escaneos cronológicamente en Fase 6, a diferencia del timestamp por host.

### Dato observado: la propia MAC no aparece en su tabla ARP

Al escanear la propia IP de la máquina, `"mac"` da `None` — la tabla ARP registra las MACs de *otros* dispositivos con los que hubo comunicación; una máquina no necesita resolverse a sí misma vía ARP, así que no aparece en su propia tabla. Comportamiento esperado, no un bug.

---

## Persistencia: guardado en JSON

### Formato elegido: un archivo por escaneo

Se decidió generar **un archivo nuevo por cada corrida completa** (en vez de sobreescribir un único archivo), pensando en Fase 6: comparar el estado de la red a lo largo del tiempo requiere conservar cada "foto" por separado — un archivo que se sobreescribe perdería todo el histórico.

### Nombre de archivo: timestamp sin caracteres problemáticos

El formato de timestamp usado dentro de cada host (`%Y-%m-%d %H:%M:%S`, con espacio y `:`) no es apto para nombres de archivo — el espacio y los `:` son problemáticos en muchos sistemas de archivos y en la línea de comandos. Se usa un formato distinto, con `-` como único separador:

```python
str_times_tamp = timestamp.strftime("%Y-%m-%d-%H-%M-%S")
# → "2026-09-15-01-52-29"
```

Se descartó `|` como separador entre fecha y hora (alternativa considerada) por ser un carácter con significado especial en la terminal (pipes), que obligaría a escapar el nombre del archivo en cualquier operación de línea de comandos.

### Escribiendo el archivo: `open()` + `json.dump()`

```python
with open(nombre_archivo, "w") as archivo:
    json.dump(inventario_completo, archivo, indent=4)
```

- `open(ruta, "w")`: abre (o crea) un archivo en modo escritura — sobreescribe si ya existe con ese nombre exacto.
- `json.dump(datos, archivo, indent=4)`: variante de `json.dumps()` que escribe directo a un archivo abierto, en vez de devolver un string.
- El `with` cierra el archivo automáticamente al terminar, mismo patrón que `ThreadPoolExecutor`.

### Bug: rutas relativas dependen del directorio de trabajo, no de la ubicación del script

Primer intento: `os.makedirs("logs", exist_ok=True)`. Al ejecutar el script con `python /ruta/completa/a/ping.py` desde el directorio home (`~`), la carpeta `logs/` se creó en el **home** (`/home/usuario/logs`), no en la raíz del proyecto.

**Causa**: una ruta relativa como `"logs"` se resuelve en base al **directorio de trabajo actual** de la terminal en el momento de ejecutar — no en base a dónde está guardado el archivo `.py` en el disco. Pasarle la ruta completa del script a `python` no cambia cuál es el directorio de trabajo.

**Solución robusta con `__file__`**: variable especial que Python define automáticamente en cada archivo, con la ruta real de ese archivo en el disco — constante sin importar desde dónde se ejecute el script.

```python
carpeta_actual = os.path.dirname(__file__)
# .../NetGuard/docs/experiments

raiz_proyecto = os.path.dirname(os.path.dirname(carpeta_actual))
# .../NetGuard  (sube 2 niveles: experiments → docs → NetGuard)

carpeta_logs = os.path.join(raiz_proyecto, "logs")
```

`os.path.dirname(ruta)` quita el último componente de una ruta (archivo o carpeta) y devuelve el padre — aplicado 3 veces en total (una para pasar de `__file__` a `carpeta_actual`, dos más para subir de `experiments` a `docs` y de `docs` a la raíz). `os.path.join(...)` une componentes de ruta de forma segura, sin concatenar strings a mano con `+` (evita errores de barras `/` mal puestas o duplicadas).

### Bloque final del pipeline

```python
os.makedirs(carpeta_logs, exist_ok=True)
nombre_archivo = os.path.join(carpeta_logs, "inventario_" + str_times_tamp + ".json")

with open(nombre_archivo, "w") as archivo:
    json.dump(inventario_completo, archivo, indent=4)
```

### Resultado final

Ejecución completa contra la red doméstica (`192.168.1.0/24`, 6 hosts activos): genera `logs/inventario_2026-09-15-01-52-29.json` con el inventario completo (IP, MAC, hostname, puertos, servicios, timestamp por host), en la raíz del proyecto, sin importar desde dónde se ejecute el script.

---

## Dudas / pendientes

- **Pendiente**: evaluar si guardar el archivo con nombre timestamped como único mecanismo de histórico es suficiente, o si más adelante conviene una estructura más consultable (ej. un índice, o nombrar por rango de red además de fecha).