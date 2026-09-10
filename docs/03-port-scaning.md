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

---

## Dudas / pendientes

- **Pendiente**: entender con certeza la causa del código `11` (EAGAIN) en el contexto específico probado.
- **Pendiente**: implementar la función de connect scan completa, probando una lista de puertos comunes por host.
- **Pendiente**: UDP — mencionado en el roadmap original pero no cubierto todavía (UDP no tiene handshake, el descubrimiento de puertos funciona distinto).
- **Pendiente**: detección básica de servicios a partir de qué puerto responde.