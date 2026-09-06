# Búsqueda Laboral en Vaca Muerta — Datamaq Hub

## 1. Visión y Fundamento Estratégico

El objetivo de este subsistema es la ingesta, normalización, filtrado territorial por cuenca y scoring de afinidad profesional de oportunidades laborales orientadas a **Vaca Muerta** (cuenca neuquina / Río Negro) y la industria de Oil & Gas.

### Diagnóstico del Canal Digital en el Sector Extractivo
De acuerdo con los estudios de mercado laboral digital basados en la Clasificación Industrial Internacional Uniforme (CIIU):
- **Marginalidad de los portales masivos:** El sector 4 (minería, canteras y extracción de hidrocarburos) representa apenas entre el **0.1% y el 0.3%** del volumen total de anuncios en portales de empleo web masivos (e.g. ZonaJobs, Computrabajo, Bumeran).
- **Inviabilidad de los agregadores tradicionales:** Utilizar portales generalistas no resulta una estrategia eficaz para la inserción en el rubro extractivo.
- **Estrategia adoptada en Datamaq Hub:** 
  1. Conexión directa a los sistemas ATS propietarios (*Applicant Tracking Systems* como SAP SuccessFactors / Taleo) de las grandes operadoras (**YPF, Tecpetrol, Pan American Energy, Vista Energy**).
  2. Ponderación hacia perfiles híbridos que articulan conocimiento de activos físicos (mantenimiento electromecánico, instrumentación, variadores VFD, media tensión) con análisis de datos / telemetría IoT / IA (Asset Performance Management - APM).
  3. Ejecución estrictamente **manual y bajo demanda**, respetando los tiempos de consulta del usuario sin procesos en segundo plano ni envíos desatendidos.

---

## 2. Arquitectura de Dominio (`src/domain/empleo/`)

- **Entidades (`entities.py`):**
  - `OfertaLaboral`: Inmutable (`@dataclass(frozen=True)`). ID, título, empresa, ubicación, descripción, URL de postulación, fecha de publicación, fuente, modalidad, tags, score de afinidad, nivel de afinidad y requisitos.
  - `PerfilProfesional`: Título deseado, palabras clave prioritarias, palabras clave secundarias, ubicaciones preferidas y modalidades admitidas.
  - `ResultadoBusquedaEmpleo`: Agregado que consolida las ofertas calificadas, total encontradas, fuentes consultadas y timestamp.
  - `obtener_perfil_agustin_bustos()`: Factoría del perfil objetivo de Agustín Leonardo Bustos según su trayectoria técnica: Especialista en Confiabilidad Operacional y APM, mantenimiento electromecánico, instrumentación, VFD, celdas 13.2kV, CCM, telemetría IoT, Python, Machine Learning y docencia técnica superior.

- **Value Objects (`value_objects.py`):**
  - `ModalidadTrabajo`: `PRESENCIAL`, `REMOTO`, `HIBRIDO`, `ROTACIONAL_YACIMIENTO`, `INDEFINIDO`.
  - `FuenteOferta`: `YPF`, `TECPETROL`, `PAE`, `VISTA`, `LINKEDIN`, `GENERICO`.
  - `NivelAfinidad`: `ALTA` (>= 70%), `MEDIA` (>= 45%), `BAJA` (>= 20%), `NULA` (< 20%).
  - `UbicacionCuenca`: Reconocimiento semántico y geográfico de localidades clave de Vaca Muerta: Añelo, Neuquén, Rincón de los Sauces, Plaza Huincul, Cutral Co, Catriel, Allen, Cipolletti, San Patricio del Chañar, etc.

- **Servicios de Dominio (`services.py`):**
  - `FiltroVacaMuertaService`: Verifica pertinencia geográfica o semántica industrial (upstream, wellsite, fractura, perforación, pozos, yacimientos, gas y petróleo).
  - `ScoringOfertasService`: Algoritmo de scoring realista y saturado:
    - **Título (hasta 35 pts):** Coincidencia con tokens fuertes del rol deseado (umbral de saturación de 2 términos clave).
    - **Keywords Prioritarias (hasta 35 pts):** Mayor ponderación en título (x2) que en cuerpo (x1). Saturación con impacto significativo.
    - **Keywords Secundarias (hasta 15 pts):** Tecnologías complementarias (Python, IA, compresores, celdas, LOTO, HSE).
    - **Ubicación Preferida (hasta 10 pts):** Coincidencia con la cuenca neuquina.
    - **Modalidad Admitida (hasta 5 pts):** Preferencia rotacional de campamento / yacimiento o presencial.

- **Puertos (`ports.py`):**
  - `PortalEmpleoPort`: Protocolo para consultar ofertas en fuentes externas.
  - `OfertasCachePort`: Protocolo para persistencia temporal con TTL.
  - `OportunidadesRepositoryPort`: Protocolo para persistencia relacional y auditoría del ciclo de vida de postulaciones e interacciones (`guardar`, `obtener_por_id`, `listar`, `actualizar_estado`, `eliminar`, `registrar_interaccion`, `listar_interacciones`).
  - `PerfilProfesionalRepositoryPort`: Protocolo para cargar perfiles profesionales desde almacenamiento persistente o configuración YAML (`obtener_perfil`).

- **Tracking y CRM de Postulaciones (`entities.py` y `value_objects.py`):**
  - `OportunidadLaboral`: Entidad inmutable que representa una oportunidad en el pipeline de selección. Campos: `id`, `titulo`, `empresa`, `fuente`, `url`, `ubicacion`, `modalidad`, `score_afinidad`, `nivel_afinidad`, `requisitos`, `salario_estimado`, `estado`, `notas`, `fecha_publicacion`, `fecha_deteccion`, `fecha_postulacion`, `fecha_actualizacion`.
  - `InteraccionPostulacion`: Registro de auditoría para cada punto de contacto (`id`, `oportunidad_id`, `tipo`, `fecha`, `contacto`, `canal`, `notas`, `proxima_accion`, `fecha_proxima_accion`).
  - `EstadoOportunidad`: Enum con estados: `DETECTADA`, `POSTULADA`, `EN_PROCESO`, `ENTREVISTA`, `DESCARTADA`, `FINALIZADA`.
  - `TipoInteraccion`: Enum con hitos de contacto: `POSTULACION`, `CONTACTO_LINKEDIN`, `ENTREVISTA_RRHH`, `ENTREVISTA_TECNICA`, `TEST_TECNICO`, `FEEDBACK`, `SEGUIMIENTO`, `OTRO`.

- **Excepciones (`exceptions.py`):**
  - `EmpleoDomainException`, `PortalEmpleoError`, `PerfilInvalidoError`, `OfertaNoEncontradaError`, `OportunidadNoEncontradaError`, `PerfilNoEncontradoError`.

---

## 3. Capa de Aplicación (`src/application/`)

- **DTOs (`dtos/empleo_dtos.py`):**
  - `BuscarOfertasQueryDTO`: Parámetros de consulta (palabras clave, ubicación, solo_vaca_muerta, min_score_afinidad, perfil opcional).
  - `PerfilProfesionalDTO`: Representación serializable del perfil profesional.
  - `OfertaLaboralDTO` y `ResultadoBusquedaDTO`.
  - `OportunidadLaboralDTO`, `InteraccionPostulacionDTO`, `CrearOportunidadDTO`, `ActualizarEstadoOportunidadDTO`, `RegistrarInteraccionDTO`, `ListarOportunidadesFilterDTO`.
- **Mappers (`mappers/empleo_mapper.py`):** Mapeo bidireccional entre dominio y DTOs Pydantic v2.
- **Casos de Uso (`use_cases/empleo/`):**
  - `BuscarOfertasVacaMuertaUseCase`: Orquesta secuencial/concurrentemente los portales inyectados con tolerancia a fallos individual, aplica filtro de cuenca, scoring saturado según el perfil (por defecto el perfil de Agustín Bustos) y ordena descendentemente por score.
  - `gestionar_oportunidades_use_cases.py`: Casos de uso de gestión del pipeline relacional:
    - `GuardarOportunidadUseCase`: Persiste o actualiza oportunidades en base de datos.
    - `ListarOportunidadesUseCase`: Consulta oportunidades filtrando por estado o empresa.
    - `ObtenerOportunidadUseCase`: Recupera una oportunidad por ID con sus notas.
    - `ActualizarEstadoOportunidadUseCase`: Transición de estado (`POSTULADA`, `ENTREVISTA`, etc.).
    - `EliminarOportunidadUseCase`: Eliminación física de registros.
    - `RegistrarInteraccionUseCase`: Agrega eventos de auditoría (InMail, llamado, entrevista).
    - `ListarInteraccionesUseCase`: Historial cronológico de interacciones de una vacante.

---

## 4. Adaptadores (`src/adapters/`)

- **Gateways (`gateways/empleo/`):**
  - `YpfTalentGateway`: Conexión al portal y API SuccessFactors de YPF.
  - `TecpetrolTalentGateway`: Conexión al portal y API de carreras del Grupo Techint / Tecpetrol (Fortín de Piedra).
  - `PaeTalentGateway`: Conexión al portal de Pan American Energy (PAE).
  - `VistaTalentGateway`: Conexión a la API y portal de Vista Energy.
  - `MemoryOfertasCacheGateway`: Caché en memoria con TTL para evitar rate limiting o bloqueos por consultas repetitivas.
  - `SqlOportunidadesGateway`: Implementación de `OportunidadesRepositoryPort` mediante SQLAlchemy con soporte dual para SQLite (local) y MySQL (VPS).
  - `YamlPerfilGateway`: Implementación de `PerfilProfesionalRepositoryPort` que carga y parsea archivos YAML desde `data/perfiles/` con caché en memoria y validación tipada estricta.
- **Controlador (`controllers/empleo_controller.py`):** Controlador puro y agnóstico de transporte con métodos para búsqueda, listado, creación, actualización de estado y registro de interacciones.
- **Inyección de Dependencias (`controllers/dependencies.py`):** Factorías `@lru_cache` `get_empleo_controller()` y `get_oportunidades_repository()` proveyendo el repositorio configurado.
- **Presentador (`presenters/error_presenter.py`):** Mapeo estandarizado de `EmpleoDomainException` a códigos HTTP y JSON unificados.

---

## 5. Infraestructura y Modos de Consumo (`src/infrastructure/` y `scripts/`)

- **Modelos SQLAlchemy (`infrastructure/sqlalchemy/models/empleo_models.py`):**
  - `OportunidadLaboralModel` e `InteraccionPostulacionModel` mapeando tablas `oportunidades_laborales` e `interacciones_laborales`.
- **FastAPI (`routes/empleo_routes.py`):**
  - `GET /api/v1/empleo/vaca-muerta`: Consulta rápida por query params.
  - `POST /api/v1/empleo/vaca-muerta`: Consulta avanzada con perfil ad-hoc en JSON.
  - `GET /api/v1/empleo/oportunidades`: Listado filtrable de oportunidades registradas.
  - `POST /api/v1/empleo/oportunidades`: Registro de nueva oportunidad.
  - `PATCH /api/v1/empleo/oportunidades/{id}/estado`: Cambio de estado en pipeline.
  - `POST /api/v1/empleo/oportunidades/{id}/interacciones`: Registro de interacción.
- **Herramientas de Terminal y Automatización:**
  - `scripts/buscar_empleo_vaca_muerta.py`: Búsqueda interactiva CLI bajo demanda con opción de persistencia automática en base de datos (`--guardar`).
  - `scripts/gestionar_empleo_db.py`: CLI de administración tipo CRM (`listar`, `ver`, `actualizar`, `interactuar`, `stats`).
  - `scripts/procesar_mails_empleo.py`: Ingesta desde alertas de correo electrónico en casillas IMAP.
  - `scripts/run_mail_job_watchdog.sh`: Script watchdog para ingesta periódica controlada.
  - `scripts/sync_busqueda_laboral_vps.sh`: Sincronización bidireccional (`pull`/`push`) entre VPS MySQL y SQLite local.
