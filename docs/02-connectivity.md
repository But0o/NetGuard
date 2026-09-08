# Fase 2 — Connectivity

Conceptos de networking aprendidos y aplicados en esta fase del proyecto NetGuard.

---

## ICMP (Internet Control Message Protocol)

Protocolo que vive en la misma capa que IP dentro del modelo TCP/IP, usado para enviar **mensajes de control y diagnóstico** sobre la red — a diferencia de TCP/UDP, que transportan datos de aplicaciones.

ICMP **viaja encapsulado dentro de un paquete IP** (no es un mecanismo aparte): cada mensaje ICMP tiene un paquete IP "por afuera" con origen y destino, por eso puede atravesar routers y llegar a otras redes usando el mismo ruteo que ya se estudió (misma red → directo, otra red → gateway).

Campos relevantes de un mensaje ICMP:

- **Type**: tipo de mensaje (Echo Request = 8, Echo Reply = 0, entre otros no cubiertos todavía como "destino inalcanzable" o "tiempo excedido").
- **Identifier** y **Sequence Number**: permiten emparejar cada respuesta con el pedido que la originó.

## Ping: Echo Request / Echo Reply

"Hacer ping" significa mandar un paquete ICMP **Echo Request** a un destino. Si el destino está activo, responde con un **Echo Reply**.

De esto se puede inferir:

- Si llega respuesta → el host está activo.
- Si no llega nada tras un **timeout** → el host puede estar apagado, desconectado, o bloqueando ICMP.
- El tiempo que tarda en responder → **latencia** (RTT, Round Trip Time).

## TTL (Time To Live)

Campo de todo paquete IP (incluido el que lleva un Echo Request/Reply). No es tiempo en segundos, es un **contador de saltos**: cada vez que un dispositivo recibe el paquete, lo procesa y lo reenvía hacia otro destino (típicamente un router), el TTL se resta en 1. Si llega a 0 antes de alcanzar el destino, el paquete se descarta (evita loops infinitos de ruteo).

Convención (no garantía): distintos sistemas operativos arrancan con un TTL inicial distinto — Linux suele arrancar en 64, Windows en 128. Esto se puede usar como heurística de fingerprinting, pero **no es 100% confiable**: el firmware de cada dispositivo puede configurar un TTL inicial distinto al "de libro".

### Caso de estudio real: TTL 63 en la propia red

Al hacer `ping -c 1 192.168.1.1` (el propio gateway, misma red local), se obtuvo `ttl=63` en vez de `64`. Se esperaría TTL 64 intacto por no haber saltos entre el host y el gateway en una red simple.

Investigando la topología real: la notebook estaba conectada a un **nodo de red mesh** (no al router principal), y ese nodo está configurado en **modo router** (no en modo bridge/access point). La IP `192.168.1.1` corresponde al router principal, no al nodo mesh.

Cadena real del ping:

```
Notebook → [salto] → Nodo mesh (modo router) → Router principal (192.168.1.1)
```

El Echo Reply que arma el router principal viaja de vuelta atravesando el nodo mesh, que sí procesa el paquete a nivel IP (por estar en modo router) y resta 1 al TTL — de ahí el 63 en vez de 64.

**Lección**: el TTL es evidencia útil para inferir la topología de una red, pero hay que interpretarlo con la topología real en mente, no asumir siempre el caso más simple. Un nodo mesh en **modo bridge**, en cambio, no restaría el TTL porque no procesa el paquete a nivel IP, solo retransmite a nivel de enlace.

Pendiente de verificar con `traceroute`/`tracepath`, que muestra salto por salto el camino real hacia un destino.

---

## Implementación: ping desde Python

### Opciones evaluadas para generar el ping

1. **`subprocess` + comando `ping` del sistema** (elegida para esta etapa): simple, reutiliza el patrón ya conocido de `subprocess.run`, no requiere permisos especiales porque el comando `ping` del sistema ya tiene los permisos necesarios configurados de fábrica. Contra: hay que parsear texto en vez de JSON.
2. **Raw sockets con el módulo `socket`** (pendiente, próxima iteración): permite armar el paquete ICMP a mano, mayor aprendizaje y control, pero requiere privilegios de administrador (root) en Linux, porque los raw sockets son una capacidad sensible (podrían usarse para spoofing). Se dejó para una fase posterior, cuando el resto del proyecto esté más maduro. **Objetivo: usar raw sockets en la versión final de NetGuard.**
3. **Librerías de terceros (ej. `ping3`)**: descartada por ahora — es un wrapper sobre raw sockets, mismo requisito de privilegios, menos aprendizaje.

### Ejecución del comando

```python
resultado = subprocess.run(
    ["ping", "-c", "1", ip],
    capture_output=True,
    text=True
)
```

- `-c 1`: manda un solo Echo Request y termina (sin este flag, `ping` corre indefinidamente, lo cual colgaría un script).
- `resultado.returncode`: `0` si el host respondió, distinto de `0` si no hubo respuesta (host inactivo/inalcanzable) — permite saber si el ping tuvo éxito **sin parsear texto**.

### Extracción de datos con expresiones regulares (`re`)

El comando `ping` no tiene salida en JSON (a diferencia de `ip -j addr`), así que hay que extraer TTL y tiempo del texto plano con el módulo built-in `re`.

```python
import re

texto = "64 bytes desde 192.168.1.1: icmp_seq=1 ttl=63 tiempo=51.0 ms"

ttl = re.search(r"ttl=(\d+)", texto)
tiempo = re.search(r"tiempo=(\d+\.\d+)", texto)

ttl.group(1)     # "63"  (string)
tiempo.group(1)  # "51.0" (string)
```

Elementos de sintaxis usados:

- `\d+`: uno o más dígitos seguidos.
- `\.`: punto **literal** (un punto sin escapar, `.`, significa "cualquier carácter" en regex).
- `(...)`: grupo de captura — la parte del patrón que se quiere extraer por separado con `.group(1)`.
- Prefijo `r"..."` (raw string): evita que Python interprete las barras invertidas del patrón antes de pasárselo al motor de regex.

`re.search()` siempre devuelve **strings** — hay que convertir explícitamente con `int(...)` o `float(...)` antes de usar los valores en cálculos.

### Función completa

```python
def hacer_ping(ip):
    resultado = subprocess.run(
        ["ping", "-c", "1", ip],
        capture_output=True,
        text=True
    )

    if resultado.returncode != 0:
        return {"ip": ip, "activo": False}

    texto = resultado.stdout
    ttl = re.search(r"ttl=(\d+)", texto)
    tiempo = re.search(r"tiempo=(\d+\.\d+)", texto)

    return {
        "ip": ip,
        "activo": True,
        "ttl": int(ttl.group(1)),
        "tiempo_ms": float(tiempo.group(1))
    }
```

## Timeout configurable

El comportamiento por defecto de `ping` (esperar el timeout que decida el sistema operativo) no es controlable desde el código. Se agrega el flag `-W <segundos>` para definir explícitamente cuánto esperar una respuesta por paquete antes de darse por vencido.

Nota: `-W` (mayúscula) es el timeout de espera **por paquete individual**; `-w` (minúscula) es un **deadline total** para todo el comando. Con `-c 1` se comportan parecido, pero son conceptualmente distintos — importa la diferencia si se manda más de un paquete.

Se agregó como parámetro de la función, con valor por defecto, para poder ajustarlo según el contexto (LAN rápida vs. host remoto) sin hardcodear el valor:

```python
def hacer_ping(ip, timeout=1):
    resultado = subprocess.run(
        ["ping", "-c", "4", "-W", str(timeout), ip],
        capture_output=True,
        text=True
    )
```

El parámetro se guarda como número (no como string) y se convierte con `str(timeout)` solo en el momento de armarlo dentro de la lista — así queda disponible como número real si se necesita para cálculos en otra parte del código.

## Packet loss (pérdida de paquetes)

Con un solo paquete (`-c 1`) el porcentaje de pérdida solo puede ser 0% o 100% — no aporta información real. Se cambió `-c` de `1` a `4` para que el cálculo tenga sentido (algún paquete puede perderse sin que los otros se pierdan también).

`ping` ya calcula el porcentaje de pérdida y lo expone en la línea de resumen, junto con el promedio (`avg`) de latencia de todos los paquetes enviados:

```
4 paquetes transmitidos, 4 recibidos, 0% packet loss, time 3063ms
rtt min/avg/max/mdev = 0.024/0.033/0.040/0.006 ms
```

Regex usados:

```python
tiempo = re.search(r"rtt min/avg/max/mdev = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)", texto)
perdida = re.search(r"(\d+)% packet loss", texto)
```

- `tiempo`: 4 grupos de captura separados, uno por cada valor (min, avg, max, mdev) — `.group(2)` da el promedio, que es el valor de interés.
- `perdida`: el número queda **antes** del texto de ancla (`% packet loss`), a diferencia de `ttl=(\d+)` donde el ancla iba antes del número.

### Por qué el TTL no necesita este mismo tratamiento

Con 4 paquetes, `ttl=(\d+)` con `re.search()` solo captura el TTL del **primer** paquete (`re.search` se detiene en la primera coincidencia, a diferencia de `re.findall()` que devuelve todas). Esto es una simplificación aceptable: el TTL depende de la cantidad de saltos de router que atraviesa el paquete, y esa cantidad no cambia entre paquetes de la misma sesión de ping — se confirmó empíricamente que los 4 TTL de una misma sesión son idénticos entre sí, mientras que la latencia sí varía naturalmente paquete a paquete.

Se probó también `re.findall()` para capturar los 4 TTL como lista, pero se descartó para esta función: `findall()` devuelve una lista de strings, no un objeto Match, por lo que no tiene `.group()` — hay que indexarla directamente (`lista[0]`). Se dejó como concepto para explorar más adelante, cuando haya un caso real que necesite todas las coincidencias, no solo la primera.

### Función completa (Fase 2 cerrada)

```python
def hacer_ping(ip, timeout=1):
    resultado = subprocess.run(
        ["ping", "-c", "4", "-W", str(timeout), ip],
        capture_output=True,
        text=True
    )

    if resultado.returncode != 0:
        return {"ip": ip, "activo": False}

    texto = resultado.stdout
    ttl = re.search(r"ttl=(\d+)", texto)
    tiempo = re.search(r"rtt min/avg/max/mdev = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)", texto)
    perdida = re.search(r"(\d+)% packet loss", texto)

    return {
        "ip": ip,
        "activo": True,
        "ttl": int(ttl.group(1)),
        "tiempo_ms": float(tiempo.group(2)),
        "perdida": float(perdida.group(1))
    }
```

---

## Primera versión de "Discover active hosts"

Usando `ipaddress.ip_network(...).hosts()` (ya visto en Fase 1) combinado con `hacer_ping()`, se puede recorrer una red completa y quedarse solo con los hosts que responden:

```python
import ipaddress

red = ipaddress.ip_network("192.168.1.0/24")

for host in red.hosts():
    ip_texto = str(host)
    resultado_ping = hacer_ping(ip_texto)

    if resultado_ping["activo"] == True:
        print(resultado_ping)
```

Detalle importante: `.hosts()` devuelve objetos `IPv4Address`, no strings — hay que convertir cada uno con `str(host)` antes de pasarlo a `hacer_ping()`, que espera un string para poder armar la lista de `subprocess.run()`.

### Medición real de performance (problema detectado)

Prueba con un rango chico (`192.168.1.0/28`, 14 hosts posibles): **~56 segundos** para completar el escaneo, de los cuales solo 2 hosts estaban activos (el resto, timeouts).

Extrapolando a una red `/24` completa (254 hosts): **~17 minutos estimados** para un solo escaneo secuencial. Esto es inutilizable en la práctica, sobre todo pensando en el monitoreo continuo planteado para fases futuras (Fase 6).

**Causa**: el escaneo actual es **secuencial** — cada `hacer_ping()` espera a que termine el anterior antes de arrancar el siguiente, y cada host inactivo cuesta varios segundos de timeout (4 paquetes × timeout cada uno).

**Próximo paso**: introducir concurrencia (`threading`, `asyncio`, o `concurrent.futures`) para ejecutar múltiples pings en simultáneo, en vez de uno por uno.

Para resolver esto se necesita ejecutar múltiples pings **al mismo tiempo** en vez de uno por uno. Conceptos a estudiar en la próxima sesión:

- `threading`
- `asyncio`
- `concurrent.futures`
- Qué es un thread, diferencia entre paralelismo y concurrencia, el GIL de Python.

---

## Dudas / pendientes

- **Pendiente**: verificar la cadena de saltos del caso TTL 63 con `traceroute`/`tracepath`.
- **Pendiente**: implementar versión con raw sockets (`socket`) más adelante — requiere permisos root, mayor control y aprendizaje.
- **Pendiente**: concurrencia para el escaneo de red completo (próxima sesión).