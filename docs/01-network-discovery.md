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

## Dudas abiertas

- Revisar la diferencia entre el rango "clásico" (`172.16.0.0/16`, `192.168.0.0/24`) y el rango real reservado por RFC 1918 (`172.16.0.0/12`, `192.168.0.0/16`).
- Entender por qué existen distintos tamaños de red privada y cuándo se usa cada uno.