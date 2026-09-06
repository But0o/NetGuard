# Fase 1 — Network Discovery

Conceptos de networking aprendidos y aplicados en esta fase del proyecto NetGuard.

---

## Direcciones IP (IPv4)

Una dirección IP identifica de forma única a un dispositivo dentro de una red, permitiendo que otros dispositivos lo encuentren y le envíen datos.

Una IPv4 se compone de **4 octetos** (bytes) separados por puntos, cada uno con un valor entre 0 y 255:

```
192.168.1.10
```

En binario, cada octeto son 8 bits:

```
11000000.10101000.00000001.00001010
   192   .   168   .    1   .   10
```

## Red vs. Host

Toda IP se divide conceptualmente en dos partes:

- **Parte de red**: identifica a qué red pertenece el dispositivo.
- **Parte de host**: identifica al dispositivo específico dentro de esa red.

Dos dispositivos con la misma parte de red pueden comunicarse directamente, sin pasar por un router.

## Máscara de subred

Define dónde termina la parte de red y dónde empieza la parte de host, marcando con `1` los bits de red y con `0` los bits de host.

Ejemplo:

```
IP:      192.168.1.10
Máscara: 255.255.255.0
Binario: 11111111.11111111.11111111.00000000
```

Los bits en `1` siempre están agrupados desde la izquierda, en un bloque continuo — nunca salteados.

## CIDR

Notación abreviada de la máscara, indicando la cantidad de bits en `1`.

```
192.168.1.10/24  ≡  192.168.1.10 con máscara 255.255.255.0
```

### Cómo calcular una máscara a partir del CIDR

1. Repartir los bits de red entre los 4 octetos (8 bits cada uno).
2. Si un octeto queda completo en bits de red → `255`.
3. Si un octeto queda completo en bits de host → `0`.
4. Si el corte cae **dentro** de un octeto (ej. `/26`, `/28`), prender esa cantidad de bits desde la izquierda y calcular su valor decimal sumando las potencias de 2 correspondientes (128, 64, 32, 16, 8, 4, 2, 1).

Ejemplos trabajados:

| CIDR | Máscara decimal | Octetos de red |
|------|------------------|-----------------|
| /8   | 255.0.0.0        | 1 completo |
| /16  | 255.255.0.0      | 2 completos |
| /24  | 255.255.255.0    | 3 completos |
| /26  | 255.255.255.192  | 3 completos + 2 bits |
| /28  | 255.255.255.240  | 3 completos + 4 bits |

## Rangos de IP privadas (RFC 1918)

Reservados para uso interno — nunca aparecen como IPs públicas en internet. Cada rango está pensado para una escala distinta de organización:

| Rango | Tamaño | Rango completo | Uso típico |
|-------|--------|-----------------|------------|
| `10.0.0.0/8` | 1 octeto de red | `10.0.0.0` – `10.255.255.255` | Organizaciones muy grandes (+16M direcciones) |
| `172.16.0.0/12` | Corte a mitad del 2do octeto | `172.16.0.0` – `172.31.255.255` | Organizaciones medianas (~1M direcciones) |
| `192.168.0.0/16` | 2 octetos de red | `192.168.0.0` – `192.168.255.255` | Redes chicas / hogareñas (65K direcciones) |

### Por qué `172.16.0.0/12` abarca más de lo que parece

`/12` no cae en un límite de octeto — cae en el medio del **segundo** octeto (8 bits del primer octeto + 4 bits del segundo). Igual que con los ejercicios de `/26` y `/28` (pero ahí el corte caía en el 4to octeto), acá hay que separar el segundo octeto en dos mitades de 4 bits:

```
Segundo octeto de 172.16.0.0 → 16 → binario 00010000
Bits de red (los primeros 4):  0001
Bits de host (los últimos 4):  0000
```

- Con los bits de host en `0000` → segundo octeto = **16** → inicio del rango.
- Con los bits de host en `1111` → segundo octeto = **31** → fin del rango.

Por eso `172.16.0.0/12` no es solo `172.16.x.x` — cubre los 16 bloques `/16` desde `172.16.x.x` hasta `172.31.x.x`.

`192.168.0.0/16`, en cambio, cae justo en un límite de octeto (2 octetos completos), así que su rango real coincide con la forma "simplificada" en la que se lo suele mencionar.

### Por qué existen 3 tamaños distintos

No es una cuestión de velocidad de búsqueda (encontrar un host en una red no es una búsqueda secuencial — un paquete va directo a su destino, como una carta con dirección completa). La razón real es:

1. **Uso eficiente del espacio de direcciones**: reservar un `/8` para 5 dispositivos desperdicia direcciones sin ningún beneficio.
2. **Organización y subnetting**: usar un rango del tamaño adecuado deja margen para dividir la red en subredes más chicas y lógicas más adelante (ej. separar servidores de dispositivos IoT). Si se ocupa todo el espacio de entrada sin estructura, se pierde esa flexibilidad.
3. **Tráfico de broadcast**: ciertos tipos de tráfico (broadcast, ARP — pendiente de profundizar) se envían a todos los hosts posibles de una red; una red innecesariamente grande genera más de este tráfico sin necesidad real.

## Gateway

El gateway (puerta de enlace) es el dispositivo — normalmente el router — al que un host le envía los paquetes destinados a **otra red**.

Lógica de decisión al enviar un paquete:

1. Comparar la parte de red de la IP destino con la parte de red propia (usando la máscara).
2. Si coinciden → mismo segmento de red → envío directo.
3. Si no coinciden → destino en otra red → se envía al gateway, que sabe cómo rutearlo.

El gateway siempre está dentro del mismo rango de red que el host, porque debe ser alcanzable directamente.

## Interfaces de red

Punto de conexión de la máquina a una red. Puede ser física (Wi-Fi, Ethernet) o virtual (VPN, contenedores, etc.). Una misma máquina puede tener varias interfaces simultáneas, cada una con su propia IP y configuración.

**Loopback**: interfaz virtual especial con IP fija `127.0.0.1` (rango `127.0.0.0/8`), usada por la máquina para comunicarse consigo misma (ej. probar un servidor local). No conecta a ninguna red externa.

---

## Obtención de datos reales: `subprocess`

Para que NetGuard lea el estado real de la red (en vez de datos hardcodeados), se usa el módulo `subprocess` para ejecutar comandos del sistema operativo desde Python y capturar su resultado.

Comando usado: `ip -j addr` (el flag `-j` devuelve la salida en formato JSON, fácil de parsear).

```python
import subprocess

resultado = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True)
```

Puntos clave:

- El comando se pasa como **lista** de argumentos (`["ip", "-j", "addr"]`), no como un único string. Esta es la forma segura de usar `subprocess`.
- `capture_output=True`: evita que la salida del comando se imprima directo en la terminal: la guarda en el objeto devuelto.
- `text=True`: devuelve la salida como string de texto, no como bytes.
- Todo proceso de Linux tiene 3 canales estándar: **stdin** (entrada), **stdout** (salida normal) y **stderr** (salida de errores), separados entre sí. `resultado.stdout` contiene la salida normal del comando (el JSON); `resultado.stderr` contendría un mensaje de error si lo hubiera.

### Alternativas consideradas

- `os.system()`: más simple pero no permite capturar la salida fácilmente.
- `subprocess.Popen()`: versión de más bajo nivel, útil si se necesita leer la salida mientras el proceso todavía corre. `subprocess.run()` está construido sobre `Popen` y alcanza para este caso de uso.

### Nota de seguridad (Cybersecurity)

`subprocess.run()` con una lista de argumentos fijos es seguro. Existe la variante `shell=True` (ejecutar el comando como string a través de una shell), que es **peligrosa** si alguna parte del comando proviene de input externo (usuario, red, archivo) — abre la puerta a **command injection**. No aplica todavía porque el comando es fijo, pero hay que tenerlo en cuenta cuando el proyecto incorpore inputs externos (por ejemplo, que el usuario elija qué host o rango escanear).

## Cálculo de la red: `ipaddress`

Tener una IP y un CIDR por separado (ej. `192.168.1.202` + `24`) **no es lo mismo** que conocer la red a la que pertenece esa IP. La red se obtiene "apagando" (poniendo en 0) los bits de host de la IP, dejando intactos los bits de red — es decir, aplicando la máscara.

Se usa el módulo built-in `ipaddress` para hacer este cálculo, en vez de programarlo a mano con operaciones binarias (más propenso a errores):

```python
import ipaddress

interfaz = ipaddress.ip_interface("192.168.1.202/24")
interfaz.network   # IPv4Network('192.168.1.0/24') → la red calculada
interfaz.ip         # IPv4Address('192.168.1.202') → la IP puntual, sin CIDR
interfaz.netmask    # IPv4Address('255.255.255.0') → la máscara en formato decimal
```

Puntos clave:

- `ip_interface()` recibe un string `"IP/CIDR"`.
- `.network` devuelve la dirección de red (un rango, por eso incluye el `/CIDR`).
- `.ip` devuelve solo la IP puntual (un host individual no tiene CIDR propio).
- Los objetos que devuelve `ipaddress` (`IPv4Network`, `IPv4Address`) **no son serializables a JSON directamente** — hay que convertirlos con `str(...)` antes de guardarlos o imprimirlos como parte de una estructura que después se vaya a persistir.

Verificado a mano con un caso de corte no alineado a octeto (`192.168.1.100/28` → red `192.168.1.96/28`), coincidiendo el cálculo manual (binario) con el resultado de la librería.

### Alternativas consideradas

- Calcular la red a mano con operaciones binarias (AND lógico entre IP y máscara) — es lo que `ipaddress` hace internamente, pero reimplementarlo es innecesario y más propenso a bugs.
- `netaddr` (librería externa) — más features, pero `ipaddress` (built-in) alcanza para este caso de uso.

---
