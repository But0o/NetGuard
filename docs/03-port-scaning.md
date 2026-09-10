# Fase 3 — Port Scanning

Conceptos de networking aprendidos y aplicados en esta fase del proyecto NetGuard.

---

## Motivación: la limitación de ICMP encontrada en Fase 2

En la red de la facultad, ICMP estaba bloqueado para la gran mayoría de los ~2046 hosts posibles de la subred — solo 2 respondieron al ping. Esto no significa que solo hubiera 2 dispositivos activos, sino que ICMP **no es confiable** como único método de descubrimiento en redes con seguridad activa.

Alternativa: en vez de preguntar "¿estás ahí?" (ICMP), se puede preguntar algo más específico: "¿tenés un servicio corriendo en tal puerto?". Si la respuesta es afirmativa (o incluso si es un rechazo explícito), se puede confirmar que el host está activo, sin depender de ICMP.

## Puertos

Una IP identifica una máquina, pero una misma máquina puede correr muchos servicios distintos a la vez (servidor web, base de datos, SSH, etc.). El **puerto** (número de 0 a 65535) identifica, dentro de una misma IP, a qué servicio específico va dirigido un paquete — análogo al piso/número de puerta dentro de un edificio identificado por su dirección (la IP).

### Well-known ports (0–1023)

Puertos reservados por convención para servicios estándar:

- **80**: HTTP
- **443**: HTTPS
- **22**: SSH
- **53**: DNS
- **21**: FTP

Una dirección con puerto explícito se escribe `IP:puerto` (ej. `192.168.1.1:80`).

Confirmado empíricamente: la interfaz de administración de un router doméstico típico corre en **HTTP puro (puerto 80)**, no HTTPS — el navegador mostraba `http://` al acceder, no `https://`.

## TCP y el three-way handshake

TCP establece una conexión confiable antes de intercambiar datos, a través de un intercambio de 3 pasos:

1. **SYN**: el cliente pide iniciar una conexión.
2. **SYN-ACK**: si hay un servicio escuchando en ese puerto, el servidor acepta.
3. **ACK**: el cliente confirma, la conexión queda establecida.

### Los 3 resultados posibles al intentar conectar a un puerto

| Respuesta | Qué significa | Certeza sobre el host |
|---|---|---|
| **SYN-ACK** | Puerto abierto, servicio activo | Alta — hay un servicio real |
| **RST** (reset) | Puerto cerrado, pero el destino respondió explícitamente | Alta — el host existe, aunque nada escucha en ese puerto |
| **Silencio / timeout** | Firewall descartando el paquete, o host realmente inactivo | Baja — no se puede distinguir la causa |

Esto es la base de un **TCP connect scan**: probar conectar a uno o varios puertos comunes permite confirmar actividad de un host (vía SYN-ACK o RST) incluso cuando ICMP está bloqueado — el caso de RST es tan útil como el de puerto abierto para efectos de "host discovery", aunque no indique un servicio disponible.

### Estrategia: probar varios puertos, no solo uno

Un único puerto filtrado puede dar un falso negativo. Port scanners reales prueban una lista de puertos comunes (ej. 80, 443, 22, 21, 23) y consideran el host activo si **cualquiera** responde (SYN-ACK o RST).

---

## El módulo `socket`

A diferencia de `subprocess` (usado en Fases 1 y 2 para ejecutar comandos externos como `ip` y `ping`), `socket` es un módulo built-in que permite hablar **directamente** con la red desde Python, sin depender de ningún programa externo — es la misma capa que usan internamente comandos como `ping` o un navegador.

```python
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
resultado = s.connect_ex((ip, puerto))
s.close()
```

- `socket.AF_INET`: direcciones IPv4.
- `socket.SOCK_STREAM`: socket de tipo **TCP** (existe `SOCK_DGRAM` para UDP).
- `s.settimeout(segundos)`: define cuánto esperar antes de darse por vencido — equivalente en espíritu al flag `-W` usado con `ping`.
- `s.connect_ex((ip, puerto))`: intenta conectar, pero en vez de lanzar una excepción ante un fallo (como haría `.connect()`), devuelve un **código numérico**: `0` = conexión exitosa (puerto abierto), cualquier otro valor = algún tipo de fallo. Recibe una **tupla** `(ip, puerto)`, no dos argumentos separados.
- `s.close()`: libera el socket al terminar.

### Códigos de error verificados

- **`0`**: conexión exitosa → puerto abierto.
- **`111`** (`ECONNREFUSED`, "connection refused"): RST recibido → puerto cerrado, pero host confirmado activo. Verificado localmente contra un puerto cerrado en `127.0.0.1`.
- **`socket.timeout`** (excepción, no código numérico): sin respuesta de ningún tipo → filtrado o host inactivo, ambiguo.

---

## Duda abierta: código `11` (EAGAIN) en vez de `111`

Al probar `connect_ex()` con `settimeout(1)` contra `10.255.150.1:80` (la IP identificada como probable router/gateway de la facultad en Fase 2, con TTL 255), se obtuvo el código **`11`** (`EAGAIN` / `EWOULDBLOCK`, "Resource temporarily unavailable") en vez del `111` esperado para un puerto cerrado.

Lo que se sabe con certeza:

- `11` (`EAGAIN`) generalmente aparece en contextos de **sockets no bloqueantes**, indicando "la operación no se completó todavía, no es necesariamente un fallo del destino" — es distinto tanto de un rechazo explícito (`111`) como de un timeout por silencio total.
- Se verificó localmente que, en un caso "limpio" (puerto cerrado en `127.0.0.1`), `connect_ex()` sí devuelve `111` como se esperaba — por lo que el `11` obtenido contra la red de la facultad es un resultado real y específico de ese contexto, no un error de código.

Lo que **no** se pudo confirmar con certeza (no reproducible desde un entorno distinto a la red de la facultad):

- Si el `11` se debe a alguna particularidad del firewall/infraestructura de la facultad, a una interacción específica entre `settimeout()` y `connect_ex()` en esa situación de red, o a otra causa.

**Decisión**: para la función de connect scan, tratar cualquier código distinto de `0` (incluyendo `11`) como "no se pudo confirmar que el puerto está abierto", sin necesidad de diferenciar cada subtipo de error por ahora. Revisar esta duda más adelante si se repite el patrón o se encuentra documentación más específica.

**Actualización — el código 11 es reproducible**: se repitió el mismo código `11` en una segunda prueba independiente contra la misma IP (`10.255.150.1:80`), usando la función `escanear_puerto()` ya implementada. Esto descarta que haya sido un evento aislado o ruido puntual — es un comportamiento consistente contra esa IP/red específica, aunque la causa exacta sigue sin confirmarse.

**Actualización — el código 11 también aparece en la red doméstica (Starlink)**: al escanear varios puertos comunes contra el router de casa (`192.168.1.1`), se obtuvo:

```
80  → Abierto  (código 0)
443 → Cerrado  (código 111)
22  → Abierto  (código 0)
21  → Cerrado  (código 11)
23  → Cerrado  (código 11)
```

El código `11` volvió a aparecer, ahora en una red completamente distinta (Starlink en casa, no la facultad), y en puertos distintos al caso anterior (21 y 23, no el 80). Esto descarta que el `11` esté ligado a una red específica.

**Hipótesis (no confirmada con fuente técnica, basada en el patrón observado)**: el código `11` podría estar asociado a puertos con **filtrado activo** por parte del router/firewall, a diferencia de puertos simplemente cerrados sin nada escuchando (que dan el `111` "limpio", como el caso del 443). Los puertos donde apareció el `11` hasta ahora (80 en la facultad, 21 y 23 en casa) tienen algo en común: son puertos "sensibles" — una posible interfaz de administración, y dos protocolos viejos e inseguros (FTP y Telnet, que transmiten credenciales sin cifrar) que routers modernos suelen filtrar activamente por seguridad, en vez de dejarlos simplemente cerrados. No se encontró documentación específica que confirme esta relación causal — queda como hipótesis razonable respaldada por el patrón observado en dos redes distintas, a confirmar con más casos o investigación más adelante.

**Contraevidencia — la hipótesis de "puertos sensibles" no explica todos los casos**: al integrar el pipeline completo (detección automática de red + ping + escaneo de puertos) y correrlo contra la red doméstica completa, se obtuvieron 3 hosts activos con patrones bien distintos:

```
192.168.1.1   (router)    → 80: Abierto(0) | 443: Cerrado(111) | 22: Abierto(0) | 21: Cerrado(11) | 23: Cerrado(11)
192.168.1.28  (desconocido) → 80: Cerrado(11) | 443: Cerrado(11) | 22: Cerrado(11) | 21: Cerrado(11) | 23: Cerrado(11)
192.168.1.202 (notebook)   → 80: Cerrado(111) | 443: Cerrado(111) | 22: Cerrado(111) | 21: Cerrado(111) | 23: Cerrado(111)
```

`192.168.1.28` dio código `11` en **los 5 puertos por igual**, incluyendo 80 y 443 — puertos que no encajan con la idea de "protocolo viejo e inseguro". Esto contradice la hipótesis de que el `11` depende del **puerto** en sí.

**Hipótesis revisada**: el patrón parece estar más ligado al **tipo de dispositivo** que al puerto específico consultado. La propia notebook (Linux estándar) da siempre `111` limpio; el router da una mezcla; y `192.168.1.28` (dispositivo no identificado — posible IoT, celular, u otro tipo de equipo con una pila de red distinta) da `11` de forma uniforme en todos los puertos. Sigue sin confirmarse la causa técnica exacta — queda como línea de investigación abierta, con evidencia de que el factor determinante podría ser el dispositivo/su sistema operativo, no el puerto consultado.

---

## Pipeline completo integrado

Se integraron todas las piezas de las Fases 1, 2 y 3 en un único flujo, sin ningún dato hardcodeado:

1. `obtener_interfaces()` (Fase 1): detecta las interfaces reales de la máquina.
2. Se filtra la interfaz de loopback (`"lo"`) para quedarse con la interfaz de red real (ej. `wlan0`).
3. Se arma el objeto `ipaddress.ip_network(...)` a partir del campo `"red"` de esa interfaz — la red a escanear ya no se hardcodea, se detecta en el momento de ejecutar.
4. Se escanean todas las IPs de esa red con `hacer_ping()` (Fase 2), usando `ThreadPoolExecutor` para concurrencia.
5. Por cada host que resulta activo, se le escanean los puertos comunes con `escanear_host()` (Fase 3).

```python
interfaces = obtener_interfaces()

interfaz_encontrada = None
for interfaz in interfaces:
    if interfaz["interfas"] != "lo":
        interfaz_encontrada = interfaz

red = ipaddress.ip_network(interfaz_encontrada["red"])

lista_ip = []
for host in red.hosts():
    ip_texto = str(host)
    lista_ip.append(ip_texto)

timeout_ping = partial(hacer_ping, timeout=1)

with ThreadPoolExecutor(max_workers=30) as pool:
    resultados = list(pool.map(timeout_ping, lista_ip))

for activos in resultados:
    if activos["activo"] == True:
        print(json.dumps(escanear_host(activos["ip"]), indent=4))
```

Prueba real contra la red doméstica (`192.168.1.0/24`, detectada automáticamente): **34.84 segundos** para el escaneo completo de ping + puertos de los 3 hosts activos encontrados.

### Bug corregido durante la integración

En `escanear_puerto()`, el bloque `except socket.timeout` intentaba devolver `"codigo": resultado`, pero `resultado` nunca llega a asignarse si la excepción se dispara (la línea `resultado = s.connect_ex(...)` se interrumpe antes de completarse). Corregido a `"codigo": None`, ya que no hay ningún código numérico real que reportar en ese caso.

### `obtener_interfaces()` como función reutilizable

El script de detección de interfaces de Fase 1 (antes código suelto a nivel de módulo) se envolvió en una función, siguiendo el mismo patrón que el resto de las funciones del proyecto — permite reutilizarlo desde cualquier parte del flujo, en vez de ejecutarse automáticamente con solo importar el archivo.

---

## Función completa: `escanear_puerto()`

```python
def escanear_puerto(ip, puerto, timeout=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)

    try:
        resultado = s.connect_ex((ip, puerto))
        s.close()

        if resultado == 0:
            return {"ip": ip, "puerto": puerto, "estado": "Abierto", "codigo": resultado}
        else:
            return {"ip": ip, "puerto": puerto, "estado": "Cerrado", "codigo": resultado}

    except socket.timeout:
        s.close()
        return {"ip": ip, "puerto": puerto, "estado": "No Determinado", "codigo": None}
```

Se agregó la clave `"codigo"` al resultado (guardando el valor crudo de `connect_ex()`) para tener trazabilidad completa de qué código específico originó cada estado — útil para investigar casos como el del código `11` sin tener que reconstruir el contexto manualmente cada vez.

### Pruebas realizadas

- `escanear_puerto("10.255.150.1", 80)` → `{"estado": "Cerrado", "codigo": 11}` (dos veces, mismo resultado — ver duda abierta sobre el código 11).
- Verificado contra `127.0.0.1` con un puerto cerrado conocido → código `111` como se esperaba (caso "limpio", confirma que la función distingue bien el caso estándar).

### Nota sobre organización del código

`hacer_ping()` y `escanear_puerto()` conviven en el mismo archivo de experimentos (`docs/experiments/ping.py`) — son funciones independientes, una al lado de la otra, no anidadas. Separarlas en módulos distintos (`app/network/`, `app/scanner/`, etc., según la estructura definida en el roadmap) tiene sentido más adelante, cuando el proyecto haga la transición a una arquitectura de aplicación real (probablemente en Fase 8, con FastAPI) — no antes, mientras el código sigue siendo material de aprendizaje activo.

---

### Escaneo de múltiples puertos contra un mismo host

Reutilizando `escanear_puerto()`, se recorre una lista de puertos comunes con un `for` simple (secuencial — no se aplicó concurrencia acá, ya que son solo 5 puertos, la diferencia de tiempo sería mínima):

```python
ip = "192.168.1.1"
puertos_comunes = [80, 443, 22, 21, 23]

for puerto in puertos_comunes:
    resultado = escanear_puerto(ip, puerto)
    print(resultado)
```

---

## Dudas / pendientes

- **Pendiente**: investigar si el código `11` depende del tipo/sistema operativo del dispositivo en vez del puerto consultado — hipótesis revisada, sin confirmar.
- **Pendiente**: UDP — mencionado en el roadmap original pero no cubierto todavía (UDP no tiene handshake, el descubrimiento de puertos funciona distinto).
- **Pendiente**: detección básica de servicios a partir de qué puerto responde.
- **Pendiente**: manejar el caso de múltiples interfaces de red reales activas simultáneamente (ej. Wi-Fi + Ethernet a la vez) — por ahora se toma la última interfaz no-loopback encontrada, sin lógica de selección más sofisticada.
- **Pendiente**: mover el escaneo de puertos por host a concurrencia también (actualmente el ping usa `ThreadPoolExecutor`, pero el escaneo de puertos de cada host activo corre de forma secuencial).