# Fase 6 — Monitoring

Conceptos de networking y Python aprendidos y aplicados en esta fase del proyecto NetGuard.

---

## Motivación

Fase 5 dejó la capacidad de guardar un inventario en JSON, un archivo por escaneo. Monitoring construye sobre esa base: no se trata de medir cosas nuevas (latencia y packet loss ya se calculan desde Fase 2), sino de **observar cambios a lo largo del tiempo**, comparando distintas "fotos" (archivos de inventario) entre sí.

Se decidió empezar por aprender a **comparar** inventarios existentes antes de automatizar la generación de más escaneos — tiene más sentido dominar el análisis antes de generar grandes volúmenes de datos para analizar.

---

## Comparación de inventarios: hosts nuevos y desaparecidos

### El problema

Dadas dos listas de hosts (de dos archivos de inventario distintos), determinar: qué IPs aparecen en el escaneo nuevo pero no en el viejo (nuevos), y qué IPs estaban en el viejo pero ya no en el nuevo (desaparecidos).

### Herramienta: `set` y la resta de conjuntos

Un `set` es una colección sin duplicados, con operaciones matemáticas de conjuntos ya construidas — la relevante acá es la **diferencia** (`-`): "qué elementos están en un set pero no en el otro".

```python
ips_viejo = {"192.168.1.1", "192.168.1.5", "192.168.1.10"}
ips_nuevo = {"192.168.1.1", "192.168.1.10", "192.168.1.20"}

nuevos = ips_nuevo - ips_viejo         # {"192.168.1.20"}
desaparecidos = ips_viejo - ips_nuevo  # {"192.168.1.5"}
```

### Leyendo un archivo JSON: `json.load()`

Distinto de `json.loads()` (que parsea un string ya en memoria) y `json.dump()` (que escribe datos a un archivo), `json.load(archivo)` **lee** un archivo ya abierto y devuelve los datos de Python directamente — no recibe datos como argumento, los produce como resultado.

```python
def leer_inventario(ruta):
    with open(ruta, "r") as archivo:
        datos = json.load(archivo)
    return datos
```

### Extrayendo las IPs con list comprehension

```python
ips_viejas = set([dato["ip"] for dato in inventario_viejo])
ips_nuevas = set([dato["ip"] for dato in inventario_nuevo])
```

`[dato["ip"] for dato in inventario_viejo]` es la forma compacta (list comprehension) del patrón `for` + `.append()` usado en el resto del proyecto — produce la lista de IPs, que después se envuelve en `set(...)` para poder usar la resta de conjuntos.

---

## Validación: ¿son escaneos de la misma red?

### El problema real encontrado

Al comparar un escaneo de la red doméstica (`192.168.1.x`) contra uno de la red de la facultad (`10.255.x.x`), el resultado mostró que **todos** los hosts "desaparecieron" y aparecieron 2 "nuevos" — dato técnicamente correcto pero **sin sentido real**: no es que los dispositivos se hayan desconectado, es que se compararon dos redes completamente distintas. Se decidió agregar una validación para detectar y avisar este caso, en vez de mostrar datos que parecen alarmantes pero no lo son.

### Estrategia: comparar los primeros 3 octetos de una IP de referencia de cada set

```python
ip_referencia_vieja = next(iter(ips_viejas))
octetos_viejo = ip_referencia_vieja.split(".")[:3]

ip_referencia_nueva = next(iter(ips_nuevas))
octetos_nuevo = ip_referencia_nueva.split(".")[:3]

if octetos_viejo == octetos_nuevo:
    print("Esta es la comparacion de la red")
    print(nuevos)
    print(desaparecidas)
else:
    print("Se reviso la red y los logs que desea comparar son en redes distintas")
```

Herramientas usadas:

- `next(iter(mi_set))`: un `set` no tiene orden garantizado ni se indexa como una lista (`mi_set[0]` no funciona) — `next(iter(...))` extrae un elemento cualquiera del set, útil cuando solo se necesita "una muestra" para verificar algo, no un elemento específico.
- `.split(".")`: parte un string en una lista, usando el carácter dado como separador — `"192.168.1.83".split(".")` da `["192", "168", "1", "83"]`.
- Slicing `lista[:3]`: toma los primeros 3 elementos de una lista (índices 0, 1, 2) — `lista[:N]` siempre da los primeros N elementos, sin incluir el índice N.
- Comparación directa de listas con `==`: dos listas son iguales si tienen los mismos elementos en el mismo orden — no hace falta comparar elemento por elemento a mano.

### Decisión de diseño: no mostrar datos irrelevantes en el caso de redes distintas

En la rama de "redes distintas", se decidió **no imprimir** `nuevos` ni `desaparecidas` — esos sets no representan cambios reales de la red cuando las redes comparadas son distintas, y mostrarlos podría generar una alarma falsa (ej. "desaparecieron 5 hosts") si alguien no presta atención al mensaje de aviso previo. Solo se muestra el aviso, sin datos que inducirían a una conclusión incorrecta.

---

## Comparación de puertos entre hosts presentes en ambos escaneos

### El problema

Un host puede seguir activo en ambos escaneos y aun así tener un cambio relevante: un puerto que estaba cerrado ahora aparece abierto (o viceversa) — señal potencial de un servicio nuevo, relevante como base para detección de comportamiento sospechoso en Fase 7.

### Paso 1: encontrar qué IPs están en ambos escaneos — intersección de sets

Además de la diferencia (`-`, usada para nuevos/desaparecidos), los sets tienen la operación **intersección** (`&`): los elementos presentes en ambos conjuntos a la vez.

```python
ips_comunes = ips_nuevas & ips_viejas
```

### Paso 2: buscar el diccionario completo de un host por IP

```python
def buscar_host(ip, inventario):
    host_encontrado = None

    for encontrado in inventario:
        if encontrado["ip"] == ip:
            host_encontrado = encontrado

    return host_encontrado
```

Mismo patrón que `buscar_mac()` (Fase 5), pero devolviendo el diccionario completo del host en vez de un campo puntual — necesario porque después hace falta acceder a `"puertos"`.

### Paso 3: buscar un puerto específico por número, sin depender del orden de la lista

Comparar `host_viejo["puertos"][0]` contra `host_nuevo["puertos"][0]` a ciegas no es seguro: nada garantiza que la posición 0 de una lista corresponda al mismo número de puerto que la posición 0 de la otra (aunque en la práctica, con una lista fija de puertos comunes, probablemente coincida — no es una garantía real).

```python
def buscar_puerto(numero_puerto, lista_puerto):
    puerto_encontrado = None

    for encontrado in lista_puerto:
        if encontrado["puerto"] == numero_puerto:
            puerto_encontrado = encontrado

    return puerto_encontrado
```

### Loop completo: comparar estado de cada puerto, host por host

```python
for ip in ips_comunes:
    host_viejo = buscar_host(ip, inventario_viejo)
    host_nuevo = buscar_host(ip, inventario_nuevo)

    for puerto_viejo in host_viejo["puertos"]:
        puerto_nuevo = buscar_puerto(puerto_viejo["puerto"], host_nuevo["puertos"])

        if puerto_viejo["estado"] != puerto_nuevo["estado"]:
            print(f"Puerto {puerto_nuevo['puerto']} de {ip} cambió de {puerto_viejo['estado']} a {puerto_nuevo['estado']}")
```

El campo relevante a comparar es específicamente `"estado"` (Abierto/Cerrado/No Determinado) — no `"puerto"` (que por construcción siempre coincide, ya que `buscar_puerto()` busca justamente ese número) ni `"codigo"`/`"servicio"` (derivados, no informativos por sí solos de un cambio).

### Prueba: modificación manual de un JSON para verificar la detección

Con dos escaneos reales de la misma red, sin cambios entre sí, el loop no imprimió nada — resultado esperado pero no concluyente por sí solo (podría deberse a que no hubo cambios, o a un bug que nunca dispara el `if`).

Para confirmar que la detección realmente funciona, se modificó a mano el campo `"estado"` de un puerto en uno de los archivos JSON, simulando un cambio real. Resultado:

```
Puerto 443 de 192.168.1.1 cambió de Cerrado a Abierto
```

Confirmado: la comparación detecta correctamente un cambio de estado cuando existe.

---

## Dudas / pendientes

---

## Latencia y packet loss en el inventario

Se agregaron los campos `tiempo_ms` y `perdida` al resultado de `escanear_host()`, extrayéndolos de `resultado_ping` (ya calculados por `hacer_ping()` desde Fase 2, pero descartados hasta ahora al construir el inventario). Ambas ramas del return (`activo: True` / `False`) incluyen las mismas claves, manteniendo la consistencia ya aplicada al resto de los campos.

```python
return {
    "ip": ip,
    "mac": mac,
    "hostname": resultado_dns["dominio"],
    "activo": True,
    "puertos": resultados_puertos,
    "timestamp": str_timestamp,
    "tiempo_ms": resultado_ping["tiempo_ms"],
    "perdida": resultado_ping["perdida"],
}
```

Con esto, el inventario ya tiene la base de datos necesaria para poder construir historial de latencia y packet loss (comparando estos valores entre varios escaneos), pendiente de implementar.

## Alias de shell para ejecutar el escaneo

Se creó un alias permanente en fish para simplificar la ejecución manual del pipeline mientras no existe una interfaz:

```fish
alias netguard-scan="python3 /home/b0o/Proyectos/NetGuard/scripts/run_scan.py"
funcsave netguard-scan
```

`funcsave` guarda el alias en la configuración de fish (`~/.config/fish/config.fish`) de forma permanente, disponible en cualquier terminal nueva, sin necesidad de editar el archivo manualmente.

---

## Availability monitoring (uptime)

### El problema

A diferencia de comparar 2 escaneos, uptime requiere analizar una **serie completa** de escaneos históricos y calcular, para un host puntual, qué porcentaje de esos escaneos lo encontraron activo.

### Listando todos los archivos de logs/: `os.listdir()`

```python
archivos = os.listdir("logs")

rutas_completas = []
for nombre_archivo in archivos:
    rutas_completas.append(os.path.join("logs/", nombre_archivo))
```

`os.listdir(carpeta)` devuelve una lista de nombres (strings) de todo lo que hay en esa carpeta — no rutas completas, hay que combinarlas con `os.path.join()`.

### Leyendo todos los inventarios

```python
inventario = []
for archivo in rutas_completas:
    inventario.append(leer_inventario(archivo))
```

`inventario` queda como una lista de listas: cada elemento es el contenido completo de un archivo de escaneo (una lista de hosts).

### Calculando el porcentaje de disponibilidad

```python
veces_activo = 0

for escaneo in inventario:
    resultado_busqueda = buscar_host(ip_buscar, escaneo)
    if resultado_busqueda is not None and resultado_busqueda["activo"] == True:
        veces_activo += 1

porcentaje_uptime = (veces_activo / len(inventario)) * 100
```

`buscar_host()` (Fase 6, comparación de puertos) devuelve `None` si la IP no aparece en ese escaneo — condición combinada con `and` (evaluación de cortocircuito: si `resultado_busqueda is not None` es `False`, Python no llega a evaluar `resultado_busqueda["activo"]`, evitando el error de acceder a una clave de `None`).

### Bug de interpretación: uptime mezclando redes distintas

Primera prueba, con una IP de la red doméstica (`192.168.1.1`): **18.18%** — resultado sorprendentemente bajo.

**Causa**: el timer de systemd estuvo corriendo escaneos mientras se cambiaba de red (casa → facultad → otra red con `192.168.0.x`) — la mayoría de los archivos de `logs/` correspondían a redes donde esa IP ni siquiera existía. El cálculo no distingue "host no respondió" de "host no pertenece a esta red" — trata ambos casos igual (cuenta como no activo).

Segunda prueba, con la IP más frecuente en los logs (`192.168.0.1`): **63.6%** — resultado mucho más consistente con la realidad.

**Limitación conocida, pendiente de resolver**: el uptime debería calcularse solo dentro de escaneos de la misma red (mismo criterio de validación ya usado para nuevos/desaparecidos y comparación de puertos), filtrando antes de contar, en vez de mezclar redes distintas en el mismo cálculo.

---

## Latency history y Packet loss history

Mismo patrón que uptime, en el mismo loop (una sola pasada calcula las 3 métricas):

```python
veces_activo = 0
sumar_tiempo_ms = 0
sumar_perdida = 0

for escaneo in inventario:
    resultado_busqueda = buscar_host(ip_buscar, escaneo)
    if resultado_busqueda is not None and resultado_busqueda["activo"] == True:
        veces_activo += 1
        sumar_tiempo_ms += resultado_busqueda.get("tiempo_ms", 0)
        sumar_perdida += resultado_busqueda.get("perdida", 0)

porcentaje_uptime = (veces_activo / len(inventario)) * 100
promedio_tiempo_ms = sumar_tiempo_ms / veces_activo
promedio_perdida = sumar_perdida / veces_activo
```

### Bug: `KeyError` con registros históricos anteriores al cambio

Al sumar `resultado_busqueda["tiempo_ms"]` con acceso directo, se obtuvo `KeyError: 'tiempo_ms'`. Causa: los archivos de `logs/` generados **antes** de agregar esos campos a `escanear_host()` (incluyendo los que generó el timer de systemd corriendo automáticamente durante la noche) no tienen esas claves — fueron guardados con una versión anterior de la función.

**Solución**: `resultado_busqueda.get("tiempo_ms", 0)` / `resultado_busqueda.get("perdida", 0)` en vez de acceso directo — mismo patrón usado repetidas veces en el proyecto (`servicios.get(...)`, `arp.get("lladdr", None)`) para tolerar datos con forma inconsistente entre versiones.

**Por qué `0` y no `None` como default**: el valor se usa en una suma acumulativa (`sumar_tiempo_ms += ...`); sumar `None` a un número genera `TypeError`. `0` es el único valor que no altera el resultado de una suma ("no aporta nada").

**Limitación conocida de esta aproximación**: un registro histórico sin el campo cuenta como si hubiera aportado `0` a la suma, aunque en realidad su valor real es simplemente desconocido (no fue medido en ese momento) — distinto de haber medido genuinamente `0` de latencia o pérdida. El promedio final queda levemente distorsionado hacia abajo cuando hay registros viejos mezclados con nuevos. Aceptable como aproximación inicial, documentado para revisar si se vuelve significativo con más historial.

### Prueba real

Con `192.168.0.1` (la IP más frecuente en el histórico de `logs/`):

```
Uptime: 66.67%
Latencia promedio: 2.61 ms
Packet loss promedio: 0.0%
```

---

## Fase 6 — Estado final

- [x] Historical data
- [x] Event logging
- [x] Availability monitoring
- [x] Latency history
- [x] Packet loss history

Fase 6 completa.

---

## Automatización: escaneos repetidos con systemd timers

### Por qué systemd timers en vez de cron

`cron` no estaba instalado en el sistema (CachyOS/Arch no lo incluye por defecto). En vez de instalarlo, se optó por **systemd timers**, el mecanismo nativo de programación de tareas en distribuciones basadas en systemd — más alineado con el objetivo de aprender Linux en profundidad.

### Dos archivos, separación de responsabilidades

A diferencia de `cron` (una sola línea con horario + comando), systemd timers usa dos archivos con roles distintos, en `~/.config/systemd/user/`:

- **`.service`**: define **qué** ejecutar.
- **`.timer`**: define **cuándo** ejecutarlo.

Ambos archivos comparten el mismo nombre base (solo cambia la extensión) — systemd los asocia automáticamente por convención de nombre.

### `netguard-scan.service`

```ini
[Unit]
Description=Escaneo de red NetGuard

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/b0o/Proyectos/NetGuard/scripts/run_scan.py
```

`Type=oneshot` indica que la tarea se ejecuta una vez y termina (no queda corriendo indefinidamente) — coincide con cómo funciona `run_scan.py`. Se usan **rutas absolutas completas** tanto para el ejecutable de Python (`which python3`) como para el script — necesario porque systemd no carga la configuración de shell del usuario (no sabe "desde dónde" se ejecutaría normalmente un comando en una terminal interactiva).

### `netguard-scan.timer`

```ini
[Unit]
Description=Timer para escaneo de red NetGuard cada 20 minutos

[Timer]
OnBootSec=1min
OnUnitActiveSec=20min

[Install]
WantedBy=timers.target
```

- `OnBootSec=1min`: la primera ejecución ocurre 1 minuto después de activar el timer (evita ejecutar en el instante exacto de activación).
- `OnUnitActiveSec=20min`: repite cada 20 minutos después de la ejecución anterior — equivalente a `*/20 * * * *` en sintaxis cron.
- `WantedBy=timers.target`: necesario para que el timer se integre correctamente al arranque normal de timers del usuario.

### Activación

```bash
systemctl --user daemon-reload
systemctl --user enable netguard-scan.timer
systemctl --user start netguard-scan.timer
```

`daemon-reload` hace que systemd relea la configuración; `enable` hace que el timer persista entre sesiones; `start` lo activa inmediatamente.

### Verificación

```bash
systemctl --user status netguard-scan.timer
systemctl --user list-timers
```

El campo `Trigger`/`NEXT` mostró inicialmente `n/a` — se resolvió solo, tras unos segundos, una vez que systemd terminó de calcular la próxima ejecución (no era un error de configuración, solo timing de la consulta).

Confirmado funcionando: próxima ejecución calculada correctamente a los 20 minutos de la activación.

### Para revisar ejecuciones pasadas

```bash
journalctl --user -u netguard-scan.service
```

Muestra la salida (print()) de cada ejecución del servicio — útil para diagnosticar fallos silenciosos sin tener que esperar y mirar manualmente.

### Introducción a vim

Primer uso de vim para crear los archivos de configuración. Conceptos mínimos:

- Modo normal (por defecto al abrir): las teclas son comandos, no escriben texto.
- `i`: entra a modo inserción, para escribir texto normalmente.
- `Esc`: vuelve a modo normal.
- `:wq` (en modo normal): guarda y sale.
- `:q!` (en modo normal): sale sin guardar, descartando cambios.

- **Resuelto**: el warning `SyntaxWarning: "\d" is an invalid escape sequence` no era un bug en el código en sí — el bloque completo de funciones (`hacer_ping`, `consultar_dns`, etc.) estaba deliberadamente comentado con triple comilla (`"""..."""`) para poder trabajar solo en la lógica de comparación de inventarios sin correr el escaneo completo cada vez. Dentro de un string de triple comilla sin prefijo `r`, el `r` de un raw string interno (como `r"ttl=(\d+)"`) no tiene efecto real — Python igual analiza el contenido como texto y advierte sobre la secuencia de escape. El código nunca se ejecutaba (estaba efectivamente desactivado), así que el warning era inofensivo. Se resolvió cambiando a comentarios línea por línea con `#`, que Python ignora por completo sin ningún análisis de sintaxis interno.