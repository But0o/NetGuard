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

## Rangos de IP privadas

Reservados para uso interno — nunca aparecen como IPs públicas en internet:

- `10.0.0.0/8`
- `172.16.0.0/16` (a confirmar: el rango RFC 1918 real es `172.16.0.0/12`, más amplio — ver "Dudas abiertas")
- `192.168.0.0/24` (a confirmar: el rango RFC 1918 real es `192.168.0.0/16` — ver "Dudas abiertas")

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

---

## Dudas abiertas

- Revisar la diferencia entre el rango "clásico" (`172.16.0.0/16`, `192.168.0.0/24`) y el rango real reservado por RFC 1918 (`172.16.0.0/12`, `192.168.0.0/16`).
- Entender por qué existen distintos tamaños de red privada y cuándo se usa cada uno.
- **Pendiente**: manejo de errores en el script de interfaces — revisar `resultado.returncode` y `resultado.stderr` por si el comando `ip` falla o no existe en el sistema, en vez de asumir que siempre funciona.