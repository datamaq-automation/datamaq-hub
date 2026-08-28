# Especificación Técnica: Horarios de Docencia y Declaraciones Juradas

## 1. Identificación y Propósito
- **ID:** `SPEC-DOC-001`
- **Módulo:** `horarios_docencia`
- **Capa DDD:** `domain/horarios_docencia`, `application/`, `adapters/`, `infrastructure/`
- **Consumidores:** Asistente AI (OpenClaw), API REST Datamaq Hub, Portal Docente.
- **Objetivo:** Auditar declaraciones juradas de cargos escolares de la DGCyE PBA, detectar incompatibilidades estatutarias, superposiciones horarias y tiempos de traslado, gestionar designaciones temporales con CRUD completo y proyectar clases al calendario corporativo.

---

## 2. Invariantes y Reglas Estatutarias
1. **Normalización Unificada de CUIT:** Todo CUIT se procesa y almacena normalizado a 11 dígitos numéricos sin guiones.
2. **Topes Estatutarios PBA:**
   - Máximo de módulos semanales: **30 módulos** de base (hasta 36 permitidos en advertencia).
   - Máximo de cargos de base: **2 cargos**.
   - Módulos por bloque: Relación estándar de **60 minutos por módulo** en secundaria técnica/superior. Bloques con desviaciones generan advertencia informativa (`DESVIO_DURACION_MODULO`).
3. **Discriminación de Severidad:**
   - **Crítico / Incompatible (`es_compatible = False`):** Superposiciones horarias exactas entre escuelas o dentro del mismo establecimiento.
   - **Advertencia (`es_compatible = True, tiene_advertencias = True`):** Tiempos de traslado reducidos (< 20 min entre escuelas distintas), exceso de módulos o desvío de duración de módulos. Los excesos globales no imputan cargos específicos (`cargos_involucrados = ()`).
4. **Vigencias Temporales y Designaciones Abiertas:**
   - `fecha_hasta = None` indica designación activa/abierta. Las proyecciones a calendario se acotan al intervalo solicitado y emiten aviso de renovación o sincronización periódica.

---

## 3. Endpoints HTTP

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/horarios-docencia/validar` | Auditoría ad-hoc de compatibilidad de declaración jurada |
| `GET` | `/api/v1/horarios-docencia/designaciones` | Listar designaciones con filtros (`cuit`, `vigentes_al`, `establecimiento`, `distrito`, `limit`, `offset`) |
| `GET` | `/api/v1/horarios-docencia/designaciones/{id}` | Obtener ficha completa de una designación |
| `POST` | `/api/v1/horarios-docencia/designaciones` | Registrar nueva designación con auditoría de compatibilidad inmediata |
| `PUT` | `/api/v1/horarios-docencia/designaciones/{id}` | Actualización completa de designación |
| `PATCH` | `/api/v1/horarios-docencia/designaciones/{id}` | Modificación parcial de designación |
| `DELETE` | `/api/v1/horarios-docencia/designaciones/{id}` | Eliminación física permanente de designación |
| `POST` | `/api/v1/horarios-docencia/designaciones/{id}/cesar` | Sellar cese administrativo (`fecha_hasta`, `motivo_cese`) |
| `GET` | `/api/v1/horarios-docencia/docentes/{cuit}/vigentes` | Consultar cargos vigentes en una fecha y su compatibilidad |
| `GET` | `/api/v1/horarios-docencia/docentes/{cuit}/historial` | Cronología histórica completa de designaciones |
| `POST` | `/api/v1/calendario/docencia/sincronizar` | Proyectar clases como eventos de calendario (`incluir_eventos=False` por defecto) |
| `GET` | `/api/v1/calendario/docencia/agenda` | Consultar agenda unificada escolar/personal con `limit` configurable |
