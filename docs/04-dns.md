# Fase 4 — DNS

Conceptos de networking aprendidos y aplicados en esta fase del proyecto NetGuard.

---

## DNS (Domain Name System)

Las máquinas se identifican y rutean por **IP**, pero los humanos recuerdan mejor **nombres** (`google.com`). DNS es el sistema de traducción entre ambos: dado un nombre, devuelve la IP real detrás de ese nombre.

Proceso típico: la máquina consulta a un servidor DNS (puerto **53**, ya visto en Fase 3 como well-known port) "¿cuál es la IP de este dominio?", recibe la IP como respuesta, y recién ahí abre la conexión real (TCP, típicamente) hacia esa IP.

## Tipos de registro DNS

- **A**: nombre → dirección **IPv4**. El más básico y común.
- **AAAA**: nombre → dirección **IPv6** (el nombre viene de que IPv6 es 4 veces más larga en bits que IPv4 — de ahí las 4 "A").
- **CNAME** (Canonical Name): un nombre que es alias de otro nombre (ej. `www.dominio.com` → `dominio.com`), que a su vez se resuelve con su propio registro A.
- **MX** (Mail Exchange): indica a qué servidor mandar el correo de ese dominio. Incluye un número de **prioridad**: **cuanto más bajo, mayor prioridad** (se intenta primero) — mismo tipo de convención que aparece en otras áreas de networking (ej. métricas de rutas), donde número bajo = preferido, no al revés de lo que la intuición sugeriría.
- **NS** (Name Server): indica qué servidores DNS son responsables de resolver las consultas de ese dominio.
- **TXT**: campo de texto libre, usado para verificación de dominio, políticas anti-spam (SPF), etc. — sin estructura fija como los demás.

## Reverse DNS

Camino inverso al DNS normal: dado una **IP**, devuelve el **nombre de dominio** asociado (si existe). Útil para IPs descubiertas en escaneos de red, para ver si tienen un nombre "amigable" configurado.

---

## Herramienta elegida: `dig` vía `subprocess`

Opciones evaluadas:

1. **`socket.gethostbyname()`**: simple, sin dependencias, pero muy limitado — solo un registro A, no permite consultar otros tipos.
2. **`subprocess` + `dig`** (elegida para esta fase): reutiliza el patrón ya dominado de fases anteriores (`ip -j addr`, `ping`). Permite ver la estructura real del protocolo DNS en la salida de texto (QUESTION SECTION, ANSWER SECTION, TTL, etc.), coherente con la filosofía del proyecto de entender el protocolo antes de usar abstracciones. Puede consultar cualquier tipo de registro.
3. **`dnspython`** (librería externa): estándar profesional para DNS en Python, salida ya estructurada sin parsear texto. Descartada por ahora — queda como mejora futura para cuando el proyecto necesite mayor robustez (ej. Fase 8, FastAPI), priorizando en esta etapa ver el protocolo crudo antes de abstraerlo.

## Exploración con `dig` en terminal

```bash
dig google.com
```

Salida relevante:

```
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 40533
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; QUESTION SECTION:
;google.com.            IN    A

;; ANSWER SECTION:
google.com.        80    IN    A    142.251.129.142
```

- `status: NOERROR`: la consulta se resolvió bien. Un dominio inexistente da `NXDOMAIN`.
- `google.com.` (con punto final): notación técnica de un FQDN (fully qualified domain name) — representa la raíz del sistema DNS.
- `IN`: clase de la consulta ("Internet", casi siempre presente).
- El número antes de `IN A` (`80` en este ejemplo) es el **TTL del registro DNS**: cuántos **segundos** puede cachearse esa respuesta antes de volver a consultar. Distinto del TTL de ICMP (Fase 2), que contaba saltos de router — mismo nombre de campo, concepto completamente distinto según el protocolo.

### Ejemplo con registro MX

```bash
dig google.com MX
```

```
;; ANSWER SECTION:
google.com.    300    IN    MX    10 smtp.google.com.
```

La respuesta no es una IP, es un **nombre de servidor** (`smtp.google.com.`), coherente con el propósito de MX. El `10` antes del nombre es la **prioridad** — número más bajo, mayor preferencia (ver sección de tipos de registro arriba).

---

## Implementación: `consultar_dns()`

```python
def consultar_dns(dominio):
    resultado = subprocess.run(
        ["dig", dominio],
        capture_output=True,
        text=True
    )

    texto = resultado.stdout
    ip_encontrada = re.search(r"A\s+(\d+\.\d+\.\d+\.\d+)", texto)

    if ip_encontrada == None:
        return {"dominio": dominio, "ip": None}
    else:
        return {
            "dominio": dominio,
            "ip": ip_encontrada.group(1)
        }
```

### Regex para extraer la IP

```python
r"A\s+(\d+\.\d+\.\d+\.\d+)"
```

- `\d+\.\d+\.\d+\.\d+`: 4 bloques de "uno o más dígitos", separados por puntos literales (`\.`) — estructura de una IPv4. Cada bloque usa un solo `\d+` (no repetido varias veces — `\d+` ya cubre cualquier cantidad de dígitos por sí solo).
- `\s+` (nuevo): "uno o más espacios en blanco" (espacio, tab, salto de línea) — necesario porque la cantidad de espacios entre `A` y la IP varía según el largo del nombre de dominio, no se puede usar una cantidad fija.
- `A\s+` como ancla: evita que el regex capture el primer número-con-puntos que aparezca en cualquier parte del texto (hay varias secciones en la salida de `dig` con estructura numérica similar) — ancla la búsqueda específicamente a la línea de respuesta del registro A.

### Manejo del caso "dominio no encontrado"

Si `dig` no encuentra el dominio (o el registro no existe), `re.search()` no encuentra ningún match y devuelve `None` — **no** lanza ninguna excepción (a diferencia de `socket.timeout` en Fase 3, que sí generaba una excepción explícita). Por eso acá el manejo es con un `if ip_encontrada == None:` explícito, en vez de `try/except`.

Intentar `None.group(1)` directamente generaría `AttributeError: 'NoneType' object has no attribute 'group'` — el chequeo de `None` tiene que hacerse **sobre el objeto Match en sí**, nunca intentando ya acceder a `.group(1)` dentro de la condición (eso rompería exactamente en el caso que se quiere evitar).

Ambas ramas del `if/else` devuelven las mismas claves (`"dominio"`, `"ip"`), con `"ip": None` en el caso de fallo — mismo patrón de consistencia usado en `escanear_puerto()` (mismas claves en los 3 estados posibles).

### Pruebas realizadas

- `consultar_dns("google.com")` → `{"dominio": "google.com", "ip": "142.251.128.46"}`
- `consultar_dns("googleaksjdhkajhdkajhdkajhdkahd.com")` (dominio inexistente) → `{"dominio": "...", "ip": None}`, sin romper el programa.

---

## Dudas / pendientes

- **Pendiente**: agregar soporte para elegir el tipo de registro a consultar (A, AAAA, MX, NS, TXT, CNAME) — actualmente la función solo consulta el registro A por defecto.
- **Pendiente**: implementar Reverse DNS (IP → nombre).
- **Pendiente**: considerar migrar a `dnspython` en una fase más avanzada del proyecto, para mayor robustez que el parseo de texto de `dig`.
- **Pendiente**: distinguir explícitamente entre "dominio no existe" (NXDOMAIN) y otros posibles errores de `dig` (timeout de red, servidor DNS no disponible, etc.) — actualmente todos los casos sin match de IP se tratan igual.