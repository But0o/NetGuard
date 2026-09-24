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

- **Pendiente**: agregar latencia y packet loss al inventario guardado — actualmente `escanear_host()` no persiste esos datos de `hacer_ping()`, solo el estado `activo`. Necesario antes de poder comparar esas métricas en el tiempo. Evaluado y decidido posponer: no es prioritario, ya que no aporta aprendizaje nuevo, solo evita descartar un dato ya calculado.
- **Pendiente**: comparación por MAC en vez de por IP, para detectar el caso de un mismo dispositivo con IP reasignada por DHCP (la IP cambia, pero el dispositivo físico es el mismo).
- **Pendiente**: automatizar la generación de escaneos repetidos a intervalos (cron, loop con sleep, o scheduler) — una vez que la comparación esté más completa.
- **Pendiente**: revisar el warning `SyntaxWarning: "\d" is an invalid escape sequence` — sigue apareciendo, indica que hay un patrón regex sin el prefijo `r` (raw string) en algún lugar del archivo (línea 50 según el traceback).