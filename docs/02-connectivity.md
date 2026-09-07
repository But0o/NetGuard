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

Probada con:

- `192.168.1.1` (gateway real, activo) → `{"ip": "192.168.1.1", "activo": True, "ttl": 63, "tiempo_ms": 51.0}`
- `192.168.1.100` (IP sin dispositivo conocido) → `{"ip": "192.168.1.100", "activo": False}`

---

## Problema detectado: escaneo secuencial es lento

El objetivo de esta fase (y el ítem pendiente de Fase 1, "Discover active hosts") es escanear **todas** las IPs posibles de una red (ej. 254 en un `/24`), no solo una IP puntual.

`ipaddress.ip_network("192.168.1.0/24").hosts()` da todas las IPs utilizables de una red (sin contar dirección de red ni broadcast).

Sin embargo, llamar a `hacer_ping()` de forma **secuencial** (una IP por vez, esperando a que cada una termine) sería muy lento: cada ping puede tardar desde ~50ms (host activo) hasta varios segundos (timeout de host inactivo), y en una red doméstica típica la mayoría de las 254 IPs no tienen ningún dispositivo real — el escaneo completo podría tardar varios minutos.

## Próximo paso: concurrencia

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
