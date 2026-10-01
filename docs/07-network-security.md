# Fase 7 — Network Security

Conceptos de networking y seguridad aprendidos y aplicados en esta fase del proyecto NetGuard.

---

## Motivación

El roadmap de Fase 7 (según el README del repo) incluye: Connection monitoring, Port scan detection, Suspicious activity rules, Security events, Basic IDS concepts.

Gran parte de la infraestructura necesaria ya existe gracias a Fases 5 y 6: histórico de escaneos, detección de cambios (hosts nuevos/desaparecidos, cambios de estado de puertos). La diferencia central entre Fase 6 (Monitoring) y Fase 7 (Security) no es tanto el código en sí, sino el **criterio**: no solo "¿qué cambió?", sino "¿qué cambió de una forma que debería generar una alerta?".

---

## Suspicious activity rules: puertos que se abren

### Razonamiento de priorización

De los tipos de cambio ya detectables (hosts nuevos/desaparecidos, cambios de estado de puertos), se identificó que el cambio más indicativo de actividad sospechosa es específicamente **un puerto que pasa de Cerrado a Abierto** — no el caso inverso (Abierto → Cerrado, que generalmente indica que algo dejó de estar disponible, un problema de disponibilidad más que de seguridad, no necesariamente un ataque).

Dentro de ese cambio, se identificó un nivel de severidad adicional: si el puerto que se abre es uno de los **puertos sensibles** (protocolos viejos e inseguros, ya estudiados en Fase 6 con el caso del código `11`/EAGAIN): **21 (FTP)** y **23 (Telnet)**. Estos protocolos transmiten credenciales sin cifrar y suelen estar cerrados o filtrados por defecto en equipos modernos — que aparezcan abiertos "de la nada" es una señal más fuerte que un puerto común como el 443 (HTTPS, seguro por diseño).

### Implementación: dos niveles de alerta

```python
puertos_sensibles = {21, 23}

for ip in ips_comunes:
    host_viejo = buscar_host(ip, inventario_viejo)
    host_nuevo = buscar_host(ip, inventario_nuevo)

    for puerto_viejo in host_viejo["puertos"]:
        puerto_nuevo = buscar_puerto(puerto_viejo["puerto"], host_nuevo["puertos"])

        if puerto_viejo['estado'] == "Cerrado" and puerto_nuevo['estado'] == "Abierto":
            if puerto_nuevo['puerto'] in puertos_sensibles:
                print(f"🔴 ALERTA CRÍTICA: puerto sensible {puerto_nuevo['puerto']} se abrió en {ip}")
            else:
                print(f"🟡 Alerta: puerto {puerto_nuevo['puerto']} se abrió en {ip}")
```

Reutiliza directamente `buscar_host()` y `buscar_puerto()` de Fase 6, con una condición más específica que el `!=` genérico usado ahí (que detectaba cualquier cambio de estado, no solo la dirección Cerrado→Abierto).

`puertos_sensibles` como `set` literal (`{21, 23}`) en vez de `set([21, 23])` — forma más directa cuando los elementos ya se conocen de antemano.

### Pruebas realizadas

Modificación manual de JSON para simular dos casos (mismo método de verificación usado en Fase 6):

```
🟡 Alerta: puerto 443 se abrió en 192.168.1.1
🔴 ALERTA CRÍTICA: puerto sensible 23 se abrió en 192.168.1.1
```

Confirmado: ambos niveles de severidad se disparan correctamente según corresponda.

---

## Dudas / pendientes

- **Pendiente**: Connection monitoring — ya cubierto en gran parte por el pipeline de Fase 5/6, evaluar si hace falta algo adicional específico de seguridad (ej. conexiones hacia IPs externas sospechosas, no solo hosts internos).
- **Pendiente**: Port scan detection — detectar si la propia máquina está siendo escaneada (ángulo inverso al resto del proyecto, que siempre escanea hacia afuera).
- **Pendiente**: Security events — persistir estas alertas en su propio registro, distinguible del inventario normal (no solo imprimir en pantalla).
- **Pendiente**: Basic IDS concepts — documentar la relación conceptual entre lo construido y un IDS real.
- **Pendiente**: ampliar `puertos_sensibles` con otros protocolos inseguros si corresponde (ej. 3389 RDP, otros según se investigue).