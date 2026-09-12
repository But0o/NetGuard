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

## Tipo de registro configurable

La función inicial solo consultaba registros A (hardcodeado). Se agregó un parámetro `tipo="A"` para elegir qué tipo de registro consultar, con A como comportamiento por defecto (retrocompatible con las llamadas anteriores).

### Diccionario de patrones por tipo de registro

Cada tipo de registro tiene una forma de respuesta distinta en la salida de `dig`, por lo que se usa un diccionario que mapea tipo → su propio patrón regex, siguiendo el mismo criterio que `servicios` en Fase 3 (datos fijos, definidos a nivel de módulo, no dentro de la función — se crean una sola vez, no en cada llamada):

```python
patrones = {
    "A": r"\bA\b[ \t]+(\d+\.\d+\.\d+\.\d+)",
    "AAAA": r"\bAAAA\b[ \t]+(\S+)",
    "MX": r"\bMX\b[ \t]+\d+[ \t]+(\S+)",
    "NS": r"\bNS\b[ \t]+(\S+)",
    "CNAME": r"\bCNAME\b[ \t]+(\S+)",
    "TXT": r"\bTXT\b[ \t]+\"(.+)\""
}
```

### Símbolos regex nuevos usados

- `\S` (S mayúscula): opuesto a `\s` — "cualquier carácter que NO sea espacio en blanco". Usado para capturar nombres de dominio (`smtp.google.com.`) sin depender de su longitud o estructura interna.
- `\b`: "límite de palabra" — marca la frontera entre un carácter de palabra (letras, números, `_`) y uno que no lo es (espacio, puntuación), sin consumir ningún carácter. No representa nada en el texto, solo valida una posición.
- `[ \t]+`: clase de caracteres personalizada — "uno o más, cada uno espacio o tab", explícitamente **sin incluir saltos de línea** (a diferencia de `\s+`, que sí los incluye).
- `.` (punto solo, sin escapar): "cualquier carácter". Usado en `TXT` como `(.+)` para capturar contenido con espacios internos, entre comillas literales (`\"`).

### Bug 1: coincidencias parciales dentro de otras palabras

Patrón inicial de NS: `r"NS\s+(\S+)"`. Devolvía `";;"` en vez del nombre real del servidor.

**Causa**: sin `\b`, el patrón encuentra la secuencia de letras "NS" en **cualquier posición del texto**, incluso dentro de otra palabra que las contenga — por ejemplo, `ANSWER` contiene la secuencia `N-S` en su interior (`A-N-S-W-E-R`). El regex encontraba esa coincidencia accidental antes de llegar a la línea de respuesta real.

**Solución**: `\bNS\b` — exige que "NS" sea una palabra completa, con límites de palabra antes y después, excluyendo coincidencias dentro de otras palabras.

Este riesgo es mayor cuanto más corto es el nombre del tipo — `"A"` es el caso más extremo (aparece dentro de `ANSWER`, `AUTHORITY`, `ADDITIONAL`, etc.), por lo que se aplicó `\b` a los 6 patrones de forma preventiva, no solo a los que fallaban en las pruebas realizadas.

### Bug 2: `\s+` cruza saltos de línea

Aun con `\b` agregado, NS seguía devolviendo `";;"`.

**Causa**: `\s` (espacio en blanco) **incluye el salto de línea** (`\n`), no solo espacios y tabs. El texto de `dig` tiene múltiples líneas — la palabra `NS` aparece primero en la `QUESTION SECTION` (`;google.com.  IN  NS`, sin nada más en esa línea), y el patrón `\s+` podía "cruzar" el salto de línea y la línea en blanco siguiente, llegando hasta el inicio de la próxima sección (`;;`) y capturando eso en vez de la respuesta real.

Por qué el patrón de `"A"` no mostraba este problema pese al mismo riesgo: su grupo de captura exige explícitamente forma de IP (`\d+\.\d+\.\d+\.\d+`), así que aunque el regex "saltara" hasta `;;`, esa coincidencia no tiene forma de IP y se descarta automáticamente, forzando al motor de regex a seguir buscando más abajo hasta la respuesta real. El patrón de NS, en cambio, usaba `\S+` — lo suficientemente permisivo como para aceptar `;;` sin problema, dándose por satisfecho ahí.

**Solución**: reemplazar `\s+` por `[ \t]+` en los 6 patrones — permite espacios y tabs dentro de la misma línea, pero nunca cruza a la línea siguiente.

### Manejo de tipo de registro no soportado

Antes de ejecutar `dig`, se valida que el `tipo` pedido tenga un patrón definido en el diccionario — evita ejecutar la consulta y, más importante, evita un `TypeError` al pasarle `None` como patrón a `re.search()` (distinto de cuando `re.search()` no encuentra un match dentro del texto, que sí devuelve `None` de forma controlada — acá el problema sería que el patrón en sí no existe):

```python
patron_elegido = patrones.get(tipo, None)

if patron_elegido == None:
    return {"dominio": dominio, "ip": None, "error": "Tipo de registro no soportado"}
```

### Función completa final

```python
patrones = {
    "A": r"\bA\b[ \t]+(\d+\.\d+\.\d+\.\d+)",
    "AAAA": r"\bAAAA\b[ \t]+(\S+)",
    "MX": r"\bMX\b[ \t]+\d+[ \t]+(\S+)",
    "NS": r"\bNS\b[ \t]+(\S+)",
    "CNAME": r"\bCNAME\b[ \t]+(\S+)",
    "TXT": r"\bTXT\b[ \t]+\"(.+)\""
}

def consultar_dns(dominio, tipo="A"):
    patron_elegido = patrones.get(tipo, None)

    if patron_elegido == None:
        return {"dominio": dominio, "ip": None, "error": "Tipo de registro no soportado"}

    resultado = subprocess.run(
        ["dig", dominio, tipo],
        capture_output=True,
        text=True
    )

    texto = resultado.stdout
    ip_encontrada = re.search(patron_elegido, texto)

    if ip_encontrada == None:
        return {"dominio": dominio, "ip": None}
    else:
        return {
            "dominio": dominio,
            "ip": ip_encontrada.group(1)
        }
```

### Pruebas finales realizadas

- `consultar_dns("google.com")` (default, A) → IP real
- `consultar_dns("google.com", "A")` → mismo resultado
- `consultar_dns("google.com", "MX")` → `"smtp.google.com."`
- `consultar_dns("google.com", "NS")` → `"ns3.google.com."` (corregido tras los 2 bugs)
- `consultar_dns("google.com", "PTR")` (no soportado) → `{"ip": None, "error": "Tipo de registro no soportado"}`, sin romper

---

## Reverse DNS

Dado una IP, devuelve el nombre de dominio asociado. No es un mecanismo separado — internamente sigue siendo una consulta al registro **PTR**, usando el flag `-x` de `dig` en vez de pasar un dominio y tipo por separado:

```bash
dig -x 8.8.8.8
```

```
;; QUESTION SECTION:
;8.8.8.8.in-addr.arpa.        IN    PTR

;; ANSWER SECTION:
8.8.8.8.in-addr.arpa.    25350    IN    PTR    dns.google.
```

### Cómo funciona `in-addr.arpa` (dato conceptual, no requiere implementación manual)

Reverse DNS reutiliza la infraestructura de nombres normal de DNS: la IP se invierte octeto por octeto y se le agrega el sufijo especial `.in-addr.arpa` (ej. `192.168.1.1` → `1.1.168.192.in-addr.arpa`), tratando la IP invertida como si fuera un nombre de dominio más. El flag `-x` de `dig` hace esta conversión automáticamente — no hace falta implementarla a mano.

### Función `reverse_dns()`

```python
def reverse_dns(ip):
    resultado = subprocess.run(["dig", "-x", ip], capture_output=True, text=True)
    texto = resultado.stdout
    nombre_encontrado = re.search(r"\bPTR\b[ \t]+(\S+)", texto)

    if nombre_encontrado == None:
        return {"ip": ip, "dominio": None}
    else:
        return {
            "ip": ip,
            "dominio": nombre_encontrado.group(1)
        }
```

Mismo patrón consistente que `consultar_dns()` (subprocess → regex con `\b` + `[ \t]+` + grupo de captura → chequeo explícito de `None`), con los roles de `ip` y `dominio` invertidos respecto a la función original (acá `ip` es el input, `dominio` es el resultado).

### Pruebas realizadas

- `reverse_dns("8.8.8.8")` → `{"ip": "8.8.8.8", "dominio": "dns.google."}`
- `reverse_dns("192.168.1.1")` (router doméstico) → `{"ip": "192.168.1.1", "dominio": "_gateway."}` — nombre genérico, probablemente asignado automáticamente por el propio router/DHCP, no un nombre público de internet. Confirma que reverse DNS también funciona en direcciones de red local, no solo IPs públicas.

---

## Dudas / pendientes

- **Pendiente**: considerar migrar a `dnspython` en una fase más avanzada del proyecto, para mayor robustez que el parseo de texto de `dig`.
- **Pendiente**: distinguir explícitamente entre "dominio no existe" (NXDOMAIN) y otros posibles errores de `dig` (timeout de red, servidor DNS no disponible, etc.) — actualmente todos los casos sin match de IP se tratan igual.