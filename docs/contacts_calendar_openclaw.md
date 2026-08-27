# Guía de Integración: Contactos y Calendario para OpenClaw

Esta guía describe cómo el agente de inteligencia artificial **OpenClaw** y otros servicios interactúan con los módulos de **Contactos** y **Calendario** de **Datamaq Hub** a través de la interfaz REST local (`http://127.0.0.1:8013`).

---

## 1. Topología y Sincronización con Roundcube Webmail

Datamaq Hub interactúa de forma directa con las tablas de MySQL en el servidor VPS:
- Libreta de direcciones: tabla `roundcube.contacts`.
- Calendarios y eventos: tablas `roundcube.calendars` y `roundcube.events`.

Cualquier cambio realizado por OpenClaw se refleja al instante en el Webmail de los usuarios (`openclaw@datamaq.com.ar`, `agustin@datamaq.com.ar`, etc.).

---

## 2. Libreta de Contactos (`/api/v1/contactos`)

### Buscar y listar contactos
```bash
# Búsqueda por texto libre
curl -sS "http://127.0.0.1:8013/api/v1/contactos?q=Agustin"

# Paginación
curl -sS "http://127.0.0.1:8013/api/v1/contactos?limit=20&offset=0"
```

### Crear un nuevo contacto
```bash
curl -sS -X POST http://127.0.0.1:8013/api/v1/contactos \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Esteban Morales",
    "email": "esteban@cliente.com",
    "telefono": "+54 11 4444-5555",
    "organizacion": "Industrias Morales S.A.",
    "notas": "Contacto de planta zona norte"
  }'
```

---

## 3. Calendario y Eventos (`/api/v1/calendario`)

### Obtener próximos eventos (Briefing diario para OpenClaw)
```bash
curl -sS "http://127.0.0.1:8013/api/v1/calendario/proximos?dias=7"
```

### Verificar disponibilidad para una fecha
```bash
curl -sS "http://127.0.0.1:8013/api/v1/calendario/disponibilidad?fecha=2026-08-28&duracion_minutos=45"
```

### Agendar una reunión o evento
```bash
curl -sS -X POST http://127.0.0.1:8013/api/v1/calendario/eventos \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Reunión de Telemetría con Cliente",
    "inicio": "2026-08-28T15:00:00",
    "fin": "2026-08-28T16:00:00",
    "ubicacion": "Google Meet",
    "descripcion": "Demostración de telemetría IoT",
    "asistentes": ["agustin@datamaq.com.ar", "cliente@empresa.com"]
  }'
```

---

## 4. Agenda Docente Integrada en Calendario (`/api/v1/calendario/docencia`)

Permite a OpenClaw proyectar automáticamente los horarios de clase de las designaciones docentes en el calendario corporativo y consultar la agenda unificada.

### Sincronizar clases docentes en el calendario
```bash
curl -sS -X POST http://127.0.0.1:8013/api/v1/calendario/docencia/sincronizar \
  -H "Content-Type: application/json" \
  -d '{
    "cuit": "20365283921",
    "fecha_desde": "2026-09-01",
    "fecha_hasta": "2026-09-30",
    "limpiar_previos": true
  }'
```

### Consultar agenda unificada de clases
```bash
curl -sS "http://127.0.0.1:8013/api/v1/calendario/docencia/agenda?cuit=20365283921&fecha_desde=2026-09-01&fecha_hasta=2026-09-07"
```

