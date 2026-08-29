# Especificación: Analizador de Oportunidades B2B en Correos Entrantes + Alertas Telegram

> **Módulo:** Datamaq Hub — Detección semántica de oportunidades industriales B2B.
> **Capa:** DDD temático sobre el subdominio `mail` existente (lectura IMAP ya resuelta).
> **Rige:** `AGENTS.md` (pureza de capas, imports absolutos `from src...`, `__init__.py` en 0 bytes, Conventional Commits).
> **Documentación viva relacionada:** `docs/mail_openclaw_integration.md`, `specs/mail_reader.md`.

---

## 1. Objetivo y Contexto

Construir el analizador semántico/determinístico que, ante correos entrantes en `info@datamaq.com.ar`, detecte oportunidades comerciales industriales (RFQs, telemetría, calidad de energía, grupos automotrices JTEKT / Toyota), las puntúe de 0 a 100, y notifique por Telegram con enriquecimiento de badges, evitando duplicados mediante `ApiCachePort` y auto-registrando el contacto en Roundcube cuando se solicite.

**El motor de análisis es 100% determinístico (cero LLM):** evaluación de palabras clave técnicas, dominios corporativos, firmas y grupos industriales en Python puro de dominio.

**Límites de alcance (fuera de esta spec):**
- La lectura IMAP/Gmail/OAuth ya existe (`MailReaderPort`, `imap_mail_gateway.py`, `gmail_api_gateway.py`, `cached_mail_reader_gateway.py`). No se modifica.
- El envío HTTP a Telegram de leads ya existe (`TelegramLeadNotifierGateway`). El nuevo gateway **no** reutiliza ese class concreto de leads (semántica distinta): es un gateway nuevo dedicado a oportunidades de correo.
- No se implementa interfaz OpenAI: el scoring es determinístico por diseño.

---

## 2. Dominio & Puertos (capa de dominio, 100% puro)

### 2.1 Value Objects y Enums — `src/domain/mail/value_objects.py` (amplíar)

```python
from enum import Enum


class CategoriaEmail(str, Enum):
    """Clasificación semántica determinística del correo entrante."""
    OPORTUNIDAD_COMERCIAL = "OPORTUNIDAD_COMERCIAL"
    DOCENCIA_OFICIAL = "DOCENCIA_OFICIAL"
    PROVEEDOR_FACTURACION = "PROVEEDOR_FACTURACION"
    SPAM_NEWSLETTER = "SPAM_NEWSLETTER"
    GENERAL_INFORMATIVO = "GENERAL_INFORMATIVO"


class NivelPrioridad(str, Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAJA = "BAJA"
```

### 2.2 Entidades — `src/domain/mail/entities.py` (amplíar)

```python
@dataclass(frozen=True)
class EntidadesDetectadas:
    empresa: str | None = None
    contacto_nombre: str | None = None
    contacto_cargo: str | None = None
    tipo_proyecto: str | None = None
    ubicacion_planta: str | None = None
    telefonos: list[str] = field(default_factory=list[str])


@dataclass(frozen=True)
class AnalisisEmail:
    uid: str
    categoria: CategoriaEmail
    prioridad: NivelPrioridad
    score: int                     # 0 a 100
    resumen_ejecutivo: str
    accion_sugerida: str
    entidades: EntidadesDetectadas
    requiere_alerta: bool
    cuenta: str = ""
```

### 2.3 Puerto — `src/domain/mail/ports.py` (amplíar)

```python
class MailNotifierPort(Protocol):
    """Dispacha alertas de oportunidad de correo a canales externos (Telegram)."""
    def notificar_oportunidad_email(self, analisis: AnalisisEmail, email: EmailDetail) -> bool:
        """Retorna True si la notificación fue entregada con éxito."""
        ...
```

### 2.4 Servicio de Dominio Puro — `src/domain/mail/services.py` (amplíar)

`EmailOpportunityAnalyzerService`:

```
analyzar(detail: EmailDetail, cuenta: str = "") -> AnalisisEmail
```

Rules determinísticas (restringidas al cuerpo + asunto + remitente, lowercase, normalizadas):

| Señal | Peso (score) | Palabras clave (fast-ascii match, substring case-insensitive) |
| :--- | :--- | :--- |
| Proyecto/Telemetría industrial | +40 | `automatizacion`, `bajada de datos`, `lineas de inyeccion`, `inyectoras`, `plc`, `scada`, `telemetria`, `tiempos de ciclo`, `reunion en planta`, `evaluando proveedores`, `cotizacion`, `rfq` |
| Calidad de energía | +40 | `factor de potencia`, `cos fi`, `cos phi`, `multa edenor`, `recargo edenor`, `banco de capacitores`, `compensacion reactiva` |
| Dominio corporativo no-freemail | +15 | regex: `@([a-z0-9-]+\.)*(com\.ar|onmicrosoft\.com|jtekt|toyota|ford|volkswagen)\b` y cualquier dominio corporativo no freemail |
| Grupo automotriz conocido | +10 | `jtekt`, `toyota boshoku`, `denso`, `faurecia` → agrega sufijo `(GRUPO)` al nombre de empresa |
| Rol comprador (firma) | +15 | `buyer`, `comprador`, `jefe de mantenimiento`, `jefe de planta`, `gerente de produccion` |
| Documentación de contacto (teléfono) | +5 | regex de numeros de 10+ digitos |

**Clasificación de categoría:**
- Si match de proyecto/energía **y** (dominio corporativo o rol comprador) → `OPORTUNIDAD_COMERCIAL`.
- Si match docencia oficial (SAD, Jefatura de Inspección, ABC, "designacion") → `DOCENCIA_OFICIAL`.
- Si match facturación/proveedor (`factura`, `presupuesto proveedor`, `orden de compra proveedor`) → `PROVEEDOR_FACTURACION`.
- Si `@unsubscribe` o fuentes newsletter (`newsletter`, `mailchimp`, `hubspot`, `bulk`) → `SPAM_NEWSLETTER`.
- Si el score sumado >= threshold de oportunidad (`>= 40` con dominio corporativo) → `OPORTUNIDAD_COMERCIAL`
- Si no encaja → `GENERAL_INFORMATIVO`.

**Score final:** clamp(0, 100). `requiere_alerta = categoria == OPORTUNIDAD_COMERCIAL and score >= 40`.

**Prioridad:** `ALTA` (score >= 70), `MEDIA` (score >= 40), `BAJA` (< 40).

**Detalles de mapeo:**
- `empresa`: si hay dominio corporativo conocido (ej. `jtekt.*`), extraer nombre legible de grupo automotriz. Si dominio no-freemail desconocido, usar la parte local del remitente o el dominio. Ejemplo documentado: `JTEKT AUTOMOTIVE ARGENTINA (Toyota Group)`.
- `contacto_nombre`: primer token de la parte nombre del remitente cuando esté disponible, o primer token de `contacto_cargo` de la firma.
- `tipo_proyecto`: primera señal de proyecto encontrada (ej. `Telemetría de Inyectoras`, `Bajada de Datos`, `Factor de Potencia`).
- `resumen_ejecutivo`: texto en español, máx 300 chars, describe las señales detectadas.
- `accion_sugerida`: texto en español, máx 200 chars (ej. `Responder proponiendo franja horaria para visita técnica presencial en planta.`).

Firmas y números de contacto se detectan por regex sobre el cuerpo (últimos ~600 chars del cuerpo + líneas de `Móvil|Tel|Cel|Phone|Tec:|\+54`).

---

## 3. Casos de Uso & DTOs (capa de aplicación)

### 3.1 DTOs — `src/application/dtos/mail_dto.py` (amplíar)

- `EntidadesDetectadasDTO` (Pydantic v2)
- `AnalisisEmailDTO` (Pydantic v2): *uid, categoria (CategoriaEmail domain), prioridad (NivelPrioridad domain), score, resumen_ejecutivo, accion_sugerida, entidades, requiere_alerta, cuenta*
- `ScanMailRequestDTO`: *cuenta (str="datamaq"), carpeta (str="INBOX"), limit (int=10), forzar_notificacion (bool=False), auto_registrar_contacto (bool=False)*
- `ScanMailResponseDTO`: *total_escaneados, total_oportunidades, alertas_enviadas, contactos_registrados, analisis: list[AnalisisEmailDTO]*

### 3.2 Caso de Uso — `src/application/use_cases/analizar_correos_entrantes.py`

`AnalizarCorreosEntrantesUseCase`:

```
__init__(mail_reader: MailReaderPort,
         analyzer: EmailOpportunityAnalyzerService,
         notifier: MailNotifierPort,
         cache: ApiCachePort,
         contacts_repo: ContactsRepositoryPort | None = None,
         tarea_repo: TareaRepositoryPort | None = None)
```

`execute(request: ScanMailRequestDTO) -> ScanMailResponseDTO`:
1. `mail_reader.list_messages(...)` para obtener resúmenes no leídos/recientes de `cuenta`/`carpeta`, hasta `limit`.
2. Por cada correo: `mail_reader.get_message_by_uid(...)` → `EmailDetail` → `analyzer.analizar(detail, cuenta)`.
3. Si `analisis.requiere_alerta` (y no `forzar_notificacion=False`):
   - Clave de deduplicación: `mail:alerted:{cuenta}:{uid}`.
   - `cache.get(clave)` → si hay valor vigente, **omitir** (contar como `omitido_por_cache`, no enviar).
   - Si miss (o `forzar_notificacion=True`): `notifier.notificar_oportunidad_email(analisis, detail)`.
     - Si éxito (`True`): `cache.set(clave, valor={"alertado": True}, ttl_seconds=30*24*3600)`; `alertas_enviadas += 1`.
   - Auto-registro si `contacts_repo` presente y `auto_registrar_contacto=True` y `analisis.entidades.contacto_nombre` disponible:
     - Construir `Contact` (ver `src/domain/contacts/entities.py`) con nombre, email, empresa, cargo, telefonos.
     - `contacts_repo.create_contact(contact, account=cuenta)`; `contactos_registrados += 1`.
   - Tarea si `tarea_repo` presente:
     - Construir `Tarea` con `titulo="📞 Responder a {contacto} - {empresa}"`, prioridad según `analisis.prioridad`, id_referencia=`mail:{uid}`.
     - `tarea_repo.guardar(tarea)`.

`analizar_single(uid, cuenta, carpeta="INBOX") -> AnalisisEmailDTO`:
- Obtener detalle de un solo `uid`, ejecutar analyzer, NO notificar, retornar DTO (para endpoint `GET /analizar/{uid}`).

---

## 4. Matriz de Pruebas (RED Suite)

### `tests/unit/test_email_opportunity_analyzer.py`

| # | Escenario Gherkin | Entrada (síntesis) | Resultado esperado |
| :-- | :-- | :-- | :-- |
| 1 | Dado un correo de Sol Gurzalé (JTEKT/Toyota) con "Bajada de datos de líneas de inyección" y "evaluando proveedores", firma "Buyer" | cuerpo de ejemplo | `OPORTUNIDAD_COMERCIAL`, `ALTA`, `score>=85`, `empresa="JTEKT AUTOMOTIVE ARGENTINA (Toyota Group)"`, `contacto_cargo="Buyer"`, `tipo_proyecto` no vacío |
| 2 | Dado correo factor de potencia + multa Edenor T3 | cuerpo | `OPORTUNIDAD_COMERCIAL`, `ALTA`, `score>=70` |
| 3 | Dado newsletter/spam con `unsubscribe` | cuerpo | `SPAM_NEWSLETTER`, `BAJA`, `requiere_alerta=False` |
| 4 | Dado aviso bancario genérico | cuerpo | `GENERAL_INFORMATIVO` (o no `OPORTUNIDAD_COMERCIAL`), `requiere_alerta=False` |
| 5 | Dado correo de SAD/ABC/Jefatura de Inspección con "designación" | cuerpo | `DOCENCIA_OFICIAL`, `requiere_alerta=False` |
| 6 | Umbrales: score 69→`MEDIA`, 70→`ALTA`, 39→`BAJA` | cuerpos sintéticos | verifica prioridades |

### `tests/unit/test_analizar_correos_use_case.py`

| # | Escenario | Mocks | Resultado |
| :-- | :-- | :-- | :-- |
| 7 | Primera pasada con 1 oportunidad | FakeMailReader (devuelve 2, 1 oportunidad), FakeMailNotifier, FakeCache | `alertas_enviadas=1`, `notificador.veces_notificado=1` |
| 8 | Segunda pasada (cache poblado) | mismo FakeCache con clave vigente | `alertas_enviadas=0`, `notificador.veces_notificado=0` (deduplicación) |
| 9 | `auto_registrar_contacto=True` | FakeContactsGateway | `contactos_registrados=1`, `contacts_repo.creados==1` |
| 10 | `forzar_notificacion=True` | mismo FakeCache con clave vigente | `alertas_enviadas=1` (bypass cache) |

### `tests/unit/test_telegram_mail_notifier_gateway.py`

| # | Escenario | Resultado |
| :-- | :-- | :-- |
| 11 | Gateway sin token/chat_id configurado → no-op `False` | `False`, no excepción |
| 12 | Con token/chat (mock de `requests.post`) → éxito → `True`, payload incluye `chat_id`, `text` con badges `OPORTUNIDAD`, score y el resumen | payload JSON correcto |
| 13 | `requests` lanza error de red → retorna `False` | False sin propagar |

### `tests/integration/test_mail_routes.py` (amplíar)

| # | Escenario |
| :-- | :-- |
| 14 | `GET /api/v1/mail/analizar/{uid}` con un UID (mock inyectado) → 200, `score`/`categoria` presentes |
| 15 | `POST /api/v1/mail/analizar/scan` → 200, `ScanMailResponseDTO` shape |

---

## 5. Adaptadores & Infraestructura

### 5.1 Gateway Telegram — `src/adapters/gateways/telegram_mail_notifier_gateway.py`

- `class TelegramMailNotifierGateway(MailNotifierPort)`.
- `__init__(bot_token: str | None = None, chat_id: str | None = None)`.
- Sin token/chat → log + retorna `False`.
- Construye mensaje Markdown con: emoji `🚨 NUEVA OPORTUNIDAD B2B ENTRANTE`, `🏢 Empresa`, `👤 Contacto`, `✉️ Email`, `🎯 Asunto`, `📊 Prioridad (badge + score/100)`, `🏷️ Tipo`, `💡 Resumen`, `⚡ Acción Recomendada`, `📅 Fecha`.
- POST `https://api.telegram.org/bot{token}/sendMessage` con `parse_mode="Markdown"`. Errores de red → log + `False`.
- Badge prioridad: `ALTA`→🟢, `MEDIA`→🟡, `BAJA`→⚪.

### 5.2 Controlador — `src/adapters/controllers/mail_controller.py` (amplíar)

- `scan_and_notify_important_emails(request: ScanMailRequestDTO) -> ScanMailResponseDTO`.
- `analyze_single_email(uid: str, cuenta: str, carpeta: str = "INBOX") -> AnalisisEmailDTO`.
- Constructor acepta caso de uso opcional (DI en `dependencies.py`).

### 5.3 Rutas FastAPI — `src/infrastructure/fastapi/routes/mail_routes.py` (amplíar)

- `POST /api/v1/mail/analizar/scan`: body `ScanMailRequestDTO` → `ScanMailResponseDTO`.
- `GET /api/v1/mail/analizar/{uid}`: query `cuenta`, `carpeta` → `AnalisisEmailDTO`.
- Inyección vía `get_configured_mail_controller` (dependencies) que ahora arma el `AnalizarCorreosEntrantesUseCase` con `TelegramMailNotifierGateway` (bot/chat settings), `ApiCacheGateway`, y opcionalmente `ContactsRepositoryPort`/`TareaRepositoryPort`.

### 5.4 Script Watchdog — `scripts/mail_watchdog.py`

- CLI `argparse`: `--account datamaq`, `--carpeta INBOX`, `--limit 10`, `--dry-run`, `--auto-contact`.
- Instancia el caso de uso con gateways reales y ejecuta scan; imprime resumen. `--dry-run` no notifica (solo calcula).
- Correr desde raíz: `PYTHONPATH=. ./venv/bin/python scripts/mail_watchdog.py ...`.
- No incluir credenciales: lee de settings pydantic (`get_settings()`) o `.env`.

---

## 6. Criterios del Gauntlet (Cobertura ≥ 85%)

```
./scripts/verify_architecture.py
ruff check . && ruff format --check .
pyright
pytest tests/test_empty_inits.py
pytest -n auto -q tests/
pytest --cov=src --cov-fail-under=85 -q
```

Regla Anti-Mimetismo: el nuevo código debe respetar pureza de capas incluso si algún archivo legado no lo hiciera. Los `__init__.py` permanecen en 0 bytes. No usar `# type: ignore`, `# noqa`, `cast(Any, ...)`, ni `@pytest.mark.skip`.
