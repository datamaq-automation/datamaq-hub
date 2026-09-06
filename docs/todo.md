# Tareas Pendientes (TODO) — Datamaq Hub

> **Ámbito:** Registro vivo de backlog técnico, tareas de despliegue y plan de acción para la estrategia de inserción laboral en Vaca Muerta y el hub analítico.  
> **Estado:** Documento SSOT de seguimiento de tareas pendientes.

---

## 🎯 Plan de Acción: Inserción Laboral Vaca Muerta (Camino Crítico)

### Fase 1: Alistamiento de Activos y Perfil Digital (Semana 1)
- [ ] **A1 (Crítica) — Actualización de Perfil de LinkedIn:**
  - [ ] Configurar ubicación pública en `Provincia de Neuquén, Argentina` (o `Añelo, Neuquén`).
  - [ ] Cargar titular optimizado para SEO y selectores de planta (*Senior Electrical Maintenance & Reliability | MT 13.2 kV, CCM & VFDs | APM, IoT & Python*).
  - [ ] Actualizar sección *Acerca de* con reenmarcado semántico (*Semantic Reframing* de analítica al servicio del Uptime).
  - [ ] Cargar y validar la matriz de 20 aptitudes clave (Media Tensión, VFD, CCM, CBM, LOTO, etc.).
  - [ ] Configurar preferencias privadas de empleo (*Open to Work* para reclutadores) con disponibilidad rotacional (14x7, 10x5).
- [ ] **A2 (Crítica) — Confección de CV Adaptado a Formato ATS Petrolero:**
  - [ ] Redactar versión resumida (1 página) orientada a consultoras boutique y supervisores técnicos de campo.
  - [ ] Redactar versión extendida (2 páginas) orientada a sistemas ATS de grandes operadoras (con keywords exhaustivas de maniobras MT, marcas VFD, normas NFPA 70E/AEA y telemetría).
- [ ] **A3 (Completada) — Setup y Verificación de CRM Datamaq Hub:**
  - [x] Verificación de base relacional MySQL en VPS y réplica SQLite local (`data/busqueda_laboral.db`).
  - [x] Pruebas de scripts CLI de gestión (`scripts/gestionar_empleo_db.py`, `scripts/buscar_empleo_vaca_muerta.py`).

---

### Fase 2: Prospección Multicanal y Tracción en la Cuenca (Semanas 1–3)
- [ ] **B1 — Activación de Consultoras Boutique Locales de Neuquén:**
  - [ ] Enviar CV y carta de presentación a *Patagonia Resources* (Neuquén Capital).
  - [ ] Enviar postulación espontánea a *Vincular Consultora* (Neuquén / Añelo).
  - [ ] Registrar perfil en *SI-RH Soluciones Integrales* (Base física en Añelo).
  - [ ] Contactar selectores técnicos en *SHR Search & Human Resources* y *Petrol Human*.
- [ ] **B2 (Crítica) — Alta en Portales ATS Corporativos de Operadoras:**
  - [ ] Cargar perfil completo en **YPF Talent / Instituto Vaca Muerta** (`oportunidades.ypf.com`).
  - [ ] Registrar CV en **Techint Careers (Tecpetrol)** (`careers.techint.com`) para Fortín de Piedra.
  - [ ] Crear cuenta en el portal de empleo de **Pan American Energy (PAE)**.
  - [ ] Completar registro en el portal de talento de **Vista Energy**.
  - [ ] Alta en contratistas mayores de servicios (Pecom Energía, AESA, SLB, Halliburton).
- [ ] **B3 (Sub-crítica, Holgura = 1d) — Mapeo de Hiring Managers en LinkedIn:**
  - [ ] Identificar 15 a 20 perfiles de Superintendentes de Mantenimiento, Jefes de Base y Supervisores E&I operando en Añelo y Neuquén.
- [ ] **B4 (Sub-crítica, Holgura = 1d) — Campaña Outbound de Contacto Directo:**
  - [ ] Enviar mensajes InMail directos y personalizados con pitch técnico de Uptime y mantenimiento de activos rotantes (3 a 5 envíos diarios).

---

### Fase 3: Postulaciones Formales y Seguimiento en CRM (Semanas 2–4)
- [ ] **C1 (Crítica) — Postulaciones a Vacantes Activas en ATS:**
  - [ ] Aplicar formalmente a las búsquedas abiertas que superen el 70% de afinidad en el scoring.
- [ ] **C2 (Crítica) — Seguimiento Sistemático en CRM (`scripts/gestionar_empleo_db.py`):**
  - [ ] Registrar cada contacto, postulación e interacción con fechas de próximo seguimiento.
  - [ ] Ejecutar auditoría periódica del pipeline (`python scripts/gestionar_empleo_db.py stats`).
  - [ ] Sincronizar avances con el VPS (`bash scripts/sync_busqueda_laboral_vps.sh push`).

---

### Fase 4: Entrevistas y Acreditaciones de Campo (Semanas 4–6)
- [ ] **D1 (Crítica) — Screening Telefónico con RRHH:**
  - [ ] Ratificar disponibilidad inmediata para diagramas rotacionales (14x7, 10x5) o base en Añelo/Neuquén.
  - [ ] Alinear pretensiones económicas conforme a bandas salariales de convenio petrolero (CCT 644/12 o fuera de convenio).
- [ ] **D2 (Crítica) — Entrevista Técnica con Jefatura de Mantenimiento:**
  - [ ] Defensa práctica de maniobras MT 13.2kV, comisionado de VFDs (ABB/Siemens), CCM y aplicación de telemetría/CBM.
- [ ] **D3 (Crítica) — Examen Médico Preocupacional O&G:**
  - [ ] Gestión y realización de batería médica de ley para tareas en yacimiento/meseta y turnos rotativos.

---

### Fase 5: Cierre, Negociación e Inducción (Semanas 6–7)
- [ ] **E1 (Crítica) — Propuesta Económica Formal y Cierre:**
  - [ ] Evaluación de paquete integral (básico, vianda, desarraigo, rotación y cobertura médica).
- [ ] **E2 (Crítica) — Onboarding, Inducción de Seguridad y Despliegue:**
  - [ ] Curso de Inducción Básica de Seguridad en Cuenca Neuquina (HSE).
  - [ ] Asignación de EPP ignífugo y traslado a base operativa / yacimiento.

---

## 💻 Backlog Técnico y Arquitectura de Software

### Dominio Empleo y Planificación
- [ ] **Motor Dinámico de Cálculo PERT-CPM (`scripts/calcular_pert_cpm.py`):**
  - [ ] Definir esquema de red en `data/pert/camino_critico_vaca_muerta.yaml`.
  - [ ] Implementar algoritmo Forward/Backward Pass para cálculo de ES, EF, LS, LF, holguras y varianza en Python.
  - [ ] Generador automático de gráficos Mermaid y tablas actualizadas en Markdown.
- [ ] **Inyección Completa de `YamlPerfilGateway`:**
  - [ ] Inyectar el repositorio de perfiles en `BuscarOfertasVacaMuertaUseCase` para soportar múltiples archivos YAML de perfil de búsqueda desde la API REST (`--perfil=apm_confiabilidad`).
- [ ] **Nuevos Gateways de Portales Petroleros:**
  - [ ] Gateway para portal de empleo de **Pecom Energía** (Hiring Room API).
  - [ ] Gateway para portal de empleo de **AESA** (A-Evangelista S.A.).
